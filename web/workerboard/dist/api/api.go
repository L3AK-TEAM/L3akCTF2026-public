package api

import (
	"bytes"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"maps"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"
)

type User struct {
	Username string `json:"username"`
	Password string `json:"-"`
	ID       string `json:"id"`
	IsAdmin  bool   `json:"is_admin"`
}

type Post struct {
	Title      string          `json:"title"`
	ID         string          `json:"id"`
	AuthorID   string          `json:"author_id"`
	AuthorName string          `json:"author_name"`
	IsPrivate  bool            `json:"is_private"`
	Likes      map[string]bool `json:"likes"`
}

type Session struct {
	User  *User
	Token string
}

type Config struct {
	WorkerDir  string
	WorkerdURL string
}

type Server struct {
	*http.ServeMux
	mu         sync.RWMutex
	users      map[string]*User
	posts      map[string]*Post
	sessions   map[string]*Session
	workerDir  string
	workerdURL *url.URL
	transport  *http.Transport
}

type renderContext struct {
	PostID     string   `json:"post_id"`
	AuthorName string   `json:"author_name"`
	AuthorID   string   `json:"author_id"`
	ViewerID   string   `json:"viewer_id"`
	ViewerName string   `json:"viewer_name"`
	LikeIDs    []string `json:"like_ids"`
	IsPrivate  bool     `json:"is_private"`
}

func New(config Config) (*Server, error) {
	workerdURL, err := url.Parse(config.WorkerdURL)
	if err != nil {
		return nil, fmt.Errorf("parse workerd URL: %w", err)
	}
	if workerdURL.Scheme == "" || workerdURL.Host == "" {
		return nil, errors.New("workerd URL must be absolute")
	}
	if err := os.MkdirAll(config.WorkerDir, 0700); err != nil {
		return nil, fmt.Errorf("create worker directory: %w", err)
	}

	server := &Server{
		ServeMux:   http.NewServeMux(),
		users:      make(map[string]*User),
		posts:      make(map[string]*Post),
		sessions:   make(map[string]*Session),
		workerDir:  config.WorkerDir,
		workerdURL: workerdURL,
		transport: &http.Transport{
			Proxy:                 http.ProxyFromEnvironment,
			DialContext:           (&net.Dialer{Timeout: 2 * time.Second}).DialContext,
			ResponseHeaderTimeout: 8 * time.Second,
			IdleConnTimeout:       30 * time.Second,
		},
	}
	server.HandleFunc("POST /api/register", server.register)
	server.HandleFunc("POST /api/login", server.login)
	server.HandleFunc("POST /api/logout", server.logout)
	server.HandleFunc("GET /api/me", server.me)
	server.HandleFunc("GET /api/posts", server.listPosts)
	server.HandleFunc("POST /api/posts", server.createPost)
	server.HandleFunc("GET /api/posts/{post_id}", server.getPost)
	server.HandleFunc("POST /api/posts/{post_id}/like", server.togglePostLike)
	server.HandleFunc("GET /render/{post_id}", server.renderPost)
	server.HandleFunc("GET /render/{post_id}/{path...}", server.renderPost)

	return server, nil
}

func (s *Server) AddUser(username, password string, isAdmin bool) (*User, error) {
	username = strings.TrimSpace(username)
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, exists := s.users[username]; exists {
		return nil, errors.New("user with that name already exists")
	}
	user := &User{Username: username, Password: password, ID: uuid.NewString(), IsAdmin: isAdmin}
	s.users[username] = user
	return user, nil
}

func (s *Server) getUser(username, password string) (*User, error) {
	s.mu.RLock()
	user := s.users[username]
	s.mu.RUnlock()
	if user == nil || user.Password != password {
		return nil, errors.New("username or password incorrect")
	}
	return user, nil
}

func (s *Server) newSession(user *User) (*Session, error) {
	token := make([]byte, 24)
	if _, err := rand.Read(token); err != nil {
		return nil, err
	}
	session := &Session{
		User:  user,
		Token: hex.EncodeToString(token),
	}
	s.mu.Lock()
	s.sessions[session.Token] = session
	s.mu.Unlock()
	return session, nil
}

func (s *Server) requireSession(w http.ResponseWriter, r *http.Request) (*Session, bool) {
	cookie, err := r.Cookie("session")
	if err != nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "Authentication required."})
		return nil, false
	}
	s.mu.RLock()
	session, exists := s.sessions[cookie.Value]
	s.mu.RUnlock()
	if !exists {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "Authentication required."})
	}
	return session, exists
}

func (s *Server) setSessionCookie(w http.ResponseWriter, session *Session) {
	http.SetCookie(w, &http.Cookie{
		Name:     "session",
		Value:    session.Token,
		Path:     "/",
		HttpOnly: true,
		SameSite: http.SameSiteLaxMode,
	})
}

func (s *Server) register(w http.ResponseWriter, r *http.Request) {
	var input struct {
		Username string `json:"username"`
		Password string `json:"password"`
	}
	if !decodeJSON(w, r, &input) {
		return
	}
	user, err := s.AddUser(input.Username, input.Password, false)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}
	session, err := s.newSession(user)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "Could not create session."})
		return
	}
	s.setSessionCookie(w, session)
	writeJSON(w, http.StatusCreated, user)
}

func (s *Server) login(w http.ResponseWriter, r *http.Request) {
	var input struct {
		Username string `json:"username"`
		Password string `json:"password"`
	}
	if !decodeJSON(w, r, &input) {
		return
	}
	user, err := s.getUser(strings.TrimSpace(input.Username), input.Password)
	if err != nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": err.Error()})
		return
	}
	session, err := s.newSession(user)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "Could not create session."})
		return
	}
	s.setSessionCookie(w, session)
	writeJSON(w, http.StatusOK, user)
}

func (s *Server) logout(w http.ResponseWriter, r *http.Request) {
	if cookie, err := r.Cookie("session"); err == nil {
		s.mu.Lock()
		delete(s.sessions, cookie.Value)
		s.mu.Unlock()
	}
	http.SetCookie(w, &http.Cookie{
		Name: "session", Value: "", Path: "/", MaxAge: -1,
		HttpOnly: true, SameSite: http.SameSiteLaxMode,
	})
	w.WriteHeader(http.StatusNoContent)
}

func (s *Server) me(w http.ResponseWriter, r *http.Request) {
	session, ok := s.requireSession(w, r)
	if !ok {
		return
	}
	writeJSON(w, http.StatusOK, session.User)
}

func (s *Server) canView(user *User, post *Post) bool {
	return !post.IsPrivate || post.AuthorID == user.ID || user.IsAdmin
}

func (s *Server) listPosts(w http.ResponseWriter, r *http.Request) {
	if _, ok := s.requireSession(w, r); !ok {
		return
	}
	s.mu.RLock()
	posts := make([]*Post, 0, len(s.posts))
	for _, post := range s.posts {
		posts = append(posts, clonePost(post))
	}
	s.mu.RUnlock()
	sort.Slice(posts, func(i, j int) bool { return posts[i].ID < posts[j].ID })
	writeJSON(w, http.StatusOK, posts)
}

func (s *Server) createPost(w http.ResponseWriter, r *http.Request) {
	session, ok := s.requireSession(w, r)
	if !ok {
		return
	}
	var input struct {
		Title     string `json:"title"`
		Script    string `json:"script"`
		IsPrivate bool   `json:"is_private"`
	}
	if !decodeJSON(w, r, &input) {
		return
	}
	input.Title = strings.TrimSpace(input.Title)
	if input.Title == "" || len(input.Title) > 200 {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "Title must be between 1 and 200 characters."})
		return
	}
	if input.Script == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "Worker script is required."})
		return
	}

	post, err := s.AddPost(session.User, input.Title, input.Script, input.IsPrivate)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "Could not store Worker script."})
		return
	}
	writeJSON(w, http.StatusCreated, clonePost(post))
}

func (s *Server) AddPost(author *User, title, script string, isPrivate bool) (*Post, error) {
	post := &Post{
		Title: title, ID: uuid.NewString(), AuthorID: author.ID, AuthorName: author.Username,
		IsPrivate: isPrivate, Likes: make(map[string]bool),
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if err := writeWorker(s.workerDir, post.ID, []byte(script)); err != nil {
		return nil, err
	}
	s.posts[post.ID] = post
	return post, nil
}

func (s *Server) getPost(w http.ResponseWriter, r *http.Request) {
	session, ok := s.requireSession(w, r)
	if !ok {
		return
	}
	s.mu.RLock()
	post, exists := s.posts[r.PathValue("post_id")]
	if exists && s.canView(session.User, post) {
		post = clonePost(post)
	} else {
		exists = false
	}
	s.mu.RUnlock()
	if !exists {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "Post not found."})
		return
	}
	writeJSON(w, http.StatusOK, post)
}

func (s *Server) togglePostLike(w http.ResponseWriter, r *http.Request) {
	session, ok := s.requireSession(w, r)
	if !ok {
		return
	}
	s.mu.Lock()
	post, exists := s.posts[r.PathValue("post_id")]
	if !exists || !s.canView(session.User, post) {
		s.mu.Unlock()
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "Post not found."})
		return
	}
	if post.AuthorID == session.User.ID {
		s.mu.Unlock()
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "You cannot like your own post."})
		return
	}
	if post.Likes[session.User.ID] {
		delete(post.Likes, session.User.ID)
	} else {
		post.Likes[session.User.ID] = true
	}
	result := clonePost(post)
	s.mu.Unlock()
	writeJSON(w, http.StatusOK, result)
}

func (s *Server) renderPost(w http.ResponseWriter, r *http.Request) {
	session, ok := s.requireSession(w, r)
	if !ok {
		return
	}
	postID := r.PathValue("post_id")
	s.mu.RLock()
	post, exists := s.posts[postID]
	if !exists || !s.canView(session.User, post) {
		s.mu.RUnlock()
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "Post not found."})
		return
	}
	likes := make([]string, 0, len(post.Likes))
	for id := range post.Likes {
		likes = append(likes, id)
	}
	metadata := renderContext{
		PostID: post.ID, AuthorName: post.AuthorName, AuthorID: post.AuthorID,
		ViewerID: session.User.ID, ViewerName: session.User.Username,
		LikeIDs: likes, IsPrivate: post.IsPrivate,
	}
	s.mu.RUnlock()
	sort.Strings(metadata.LikeIDs)

	encoded, err := json.Marshal(metadata)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "Could not render post."})
		return
	}
	publicPrefix := "/render/" + postID
	suffix := strings.TrimPrefix(r.URL.Path, publicPrefix)
	if suffix == "" {
		suffix = "/"
	}
	internalPath := "/serve/" + postID + suffix

	proxy := &httputil.ReverseProxy{
		Transport: s.transport,
		Rewrite: func(request *httputil.ProxyRequest) {
			request.SetURL(s.workerdURL)
			request.Out.URL.Path = internalPath
			request.Out.URL.RawPath = ""
			request.Out.Host = s.workerdURL.Host
			request.Out.Method = http.MethodPost
			request.Out.Body = io.NopCloser(bytes.NewReader(encoded))
			request.Out.ContentLength = int64(len(encoded))
			request.Out.Header.Set("Content-Type", "application/json")
			request.Out.Header.Del("Content-Encoding")
		},
		ModifyResponse: func(response *http.Response) error {
			response.Header.Del("Set-Cookie")
			response.Header.Del("Clear-Site-Data")
			response.Header.Del("Strict-Transport-Security")
			response.Header.Del("Access-Control-Allow-Credentials")
			response.Header.Del("Access-Control-Allow-Origin")
			response.Header.Del("X-Frame-Options")
			response.Header.Set("Cache-Control", "private, no-store")
			response.Header.Set("Content-Security-Policy", "sandbox allow-scripts allow-forms")
			response.Header.Set("Pragma", "no-cache")
			return nil
		},
		ErrorHandler: func(w http.ResponseWriter, _ *http.Request, _ error) {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": "Worker runtime unavailable."})
		},
		FlushInterval: -1,
	}
	proxy.ServeHTTP(w, r)
}

func clonePost(post *Post) *Post {
	likes := make(map[string]bool, len(post.Likes))
	maps.Copy(likes, post.Likes)
	return &Post{
		Title: post.Title, ID: post.ID, AuthorID: post.AuthorID, AuthorName: post.AuthorName,
		IsPrivate: post.IsPrivate, Likes: likes,
	}
}

func writeWorker(directory, id string, source []byte) error {
	temporary, err := os.CreateTemp(directory, ".upload-*")
	if err != nil {
		return err
	}
	temporaryName := temporary.Name()
	defer os.Remove(temporaryName)
	if _, err := temporary.Write(source); err != nil {
		_ = temporary.Close()
		return err
	}
	if err := temporary.Close(); err != nil {
		return err
	}
	return os.Rename(temporaryName, filepath.Join(directory, id+".js"))
}

func decodeJSON(w http.ResponseWriter, r *http.Request, output any) bool {
	if err := json.NewDecoder(r.Body).Decode(output); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid JSON request body."})
		return false
	}
	return true
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}
