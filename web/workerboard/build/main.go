package main

import (
	"context"
	"embed"
	"errors"
	"flag"
	"fmt"
	"io/fs"
	"log"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"workerboard/api"
)

const (
	appAddress       = ":8080"
	workerdHealthURL = "http://127.0.0.1:8081/__healthz"
	startupGrace     = 3 * time.Second
	checkInterval    = 2 * time.Second
	checkTimeout     = time.Second
	maxFailedChecks  = 2
)

//go:embed public/*
var publicFiles embed.FS

type workerdProcess struct {
	mu        sync.Mutex
	process   *os.Process
	startedAt time.Time
}

func (w *workerdProcess) run(ctx context.Context) {
	for ctx.Err() == nil {
		cmd := exec.Command("workerd", "serve", "--experimental", "config.capnp")
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		if err := cmd.Start(); err != nil {
			log.Printf("[workerd] start failed: %v", err)
		} else {
			w.mu.Lock()
			w.process = cmd.Process
			w.startedAt = time.Now()
			w.mu.Unlock()
			log.Printf("[workerd] started pid=%d", cmd.Process.Pid)

			err := cmd.Wait()
			w.mu.Lock()
			if w.process == cmd.Process {
				w.process = nil
			}
			w.mu.Unlock()
			if ctx.Err() == nil {
				log.Printf("[workerd] exited: %v; restarting", err)
			}
		}
		select {
		case <-ctx.Done():
			return
		case <-time.After(500 * time.Millisecond):
		}
	}
}

func (w *workerdProcess) snapshot() (*os.Process, time.Time) {
	w.mu.Lock()
	defer w.mu.Unlock()
	return w.process, w.startedAt
}

func (w *workerdProcess) signal(signal os.Signal) {
	process, _ := w.snapshot()
	if process != nil {
		_ = process.Signal(signal)
	}
}

func superviseHealth(ctx context.Context, workerd *workerdProcess) {
	client := &http.Client{Timeout: checkTimeout}
	ticker := time.NewTicker(checkInterval)
	defer ticker.Stop()
	failedChecks, lastPID := 0, 0

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			process, startedAt := workerd.snapshot()
			if process == nil || time.Since(startedAt) < startupGrace {
				continue
			}
			if process.Pid != lastPID {
				lastPID, failedChecks = process.Pid, 0
			}
			request, _ := http.NewRequestWithContext(ctx, http.MethodGet, workerdHealthURL, nil)
			response, err := client.Do(request)
			if err == nil && response.StatusCode == http.StatusOK {
				_ = response.Body.Close()
				failedChecks = 0
				continue
			}
			if response != nil {
				if err == nil {
					err = fmt.Errorf("HTTP %d", response.StatusCode)
				}
				_ = response.Body.Close()
			}
			failedChecks++
			log.Printf("[workerd] health check failed (%d/%d): %v", failedChecks, maxFailedChecks, err)
			if failedChecks >= maxFailedChecks {
				log.Printf("[workerd] unresponsive; killing pid=%d", process.Pid)
				_ = process.Kill()
				failedChecks = 0
			}
		}
	}
}

func main() {
	healthcheck := flag.Bool("healthcheck", false, "check the public health endpoint")
	flag.Parse()
	if *healthcheck {
		response, err := (&http.Client{Timeout: 2 * time.Second}).Get("http://127.0.0.1:8080/healthz")
		if err != nil {
			log.Print(err)
			os.Exit(1)
		}
		_ = response.Body.Close()
		if response.StatusCode != http.StatusOK {
			os.Exit(1)
		}
		return
	}

	workerDir := os.Getenv("WORKER_DIR")
	if workerDir == "" {
		workerDir = "/data/workers"
	}
	forum, err := api.New(api.Config{
		WorkerDir: workerDir, WorkerdURL: "http://127.0.0.1:8081",
	})
	if err != nil {
		log.Fatal(err)
	}
	if err := seedForum(forum); err != nil {
		log.Fatal(err)
	}
	staticFiles, err := fs.Sub(publicFiles, "public")
	if err != nil {
		log.Fatal(err)
	}
	indexPage, err := fs.ReadFile(staticFiles, "index.html")
	if err != nil {
		log.Fatal(err)
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		client := &http.Client{Timeout: 500 * time.Millisecond}
		response, err := client.Get(workerdHealthURL)
		if err != nil || response.StatusCode != http.StatusOK {
			if response != nil {
				_ = response.Body.Close()
			}
			http.Error(w, "workerd unavailable", http.StatusServiceUnavailable)
			return
		}
		_ = response.Body.Close()
		w.Header().Set("Content-Type", "text/plain; charset=utf-8")
		_, _ = w.Write([]byte("ok\n"))
	})
	mux.Handle("/api/", forum)
	mux.Handle("/render/", forum)
	serveFrontend := func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		_, _ = w.Write(indexPage)
	}
	mux.HandleFunc("GET /new", serveFrontend)
	mux.HandleFunc("GET /posts/{post_id}", serveFrontend)
	mux.Handle("/", http.FileServerFS(staticFiles))

	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()
	workerd := &workerdProcess{}
	go workerd.run(ctx)
	go superviseHealth(ctx, workerd)

	server := &http.Server{Addr: appAddress, Handler: mux, ReadHeaderTimeout: 5 * time.Second}
	serverErrors := make(chan error, 1)
	go func() {
		log.Printf("[app] listening on %s", appAddress)
		serverErrors <- server.ListenAndServe()
	}()

	select {
	case <-ctx.Done():
	case err := <-serverErrors:
		if !errors.Is(err, http.ErrServerClosed) {
			log.Printf("[app] server failed: %v", err)
		}
		cancel()
	}

	shutdownContext, shutdownCancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer shutdownCancel()
	_ = server.Shutdown(shutdownContext)
	workerd.signal(syscall.SIGTERM)
	<-shutdownContext.Done()
	workerd.signal(syscall.SIGKILL)
}
