package main

import (
	"bytes"
	"io"
	"log"
	"mime"
	"mime/multipart"
	"net/http"
	"net/http/httputil"
	"net/textproto"
	"net/url"
	"os"
	"regexp"
	"strconv"
	"strings"
	"unicode/utf16"
	"unicode/utf8"

	coreruleset "github.com/corazawaf/coraza-coreruleset/v4"
	"github.com/corazawaf/coraza/v3"
	txhttp "github.com/corazawaf/coraza/v3/http"
	"github.com/corazawaf/coraza/v3/types"
	"github.com/jcchavezs/mergefs"
	mergefsio "github.com/jcchavezs/mergefs/io"
)

const maxNormalizeBody = 1 << 20 // 1 MiB

func env(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}

type flightRule struct {
	name      string
	enabled   bool
	kind      string
	pattern   *regexp.Regexp
	passes    int
	numValues []float64
}

var flightRules []flightRule

var simpleEscapes = map[byte]byte{
	'n': '\n', 't': '\t', 'r': '\r', 'b': '\b', 'f': '\f',
	'v': '\v', '0': 0x00, '\\': '\\', '"': '"', '/': '/', '\'': '\'',
}

func unescapePass(s string) (string, bool) {
	var b strings.Builder
	b.Grow(len(s))
	changed := false
	for i := 0; i < len(s); {
		c := s[i]
		if c == '\\' && i+1 < len(s) {
			n := s[i+1]
			if n == 'u' && i+6 <= len(s) && isHex(s[i+2:i+6]) {
				if r, err := strconv.ParseUint(s[i+2:i+6], 16, 32); err == nil {
					b.WriteRune(rune(r))
					i += 6
					changed = true
					continue
				}
			}
			if n == 'x' && i+4 <= len(s) && isHex(s[i+2:i+4]) {
				if r, err := strconv.ParseUint(s[i+2:i+4], 16, 32); err == nil {
					b.WriteRune(rune(r))
					i += 4
					changed = true
					continue
				}
			}
			if rep, ok := simpleEscapes[n]; ok {
				b.WriteByte(rep)
			} else {
				b.WriteByte(n) // unknown escape: drop the backslash
			}
			i += 2
			changed = true
			continue
		}
		b.WriteByte(c)
		i++
	}
	return b.String(), changed
}

func isHex(s string) bool {
	if len(s) == 0 {
		return false
	}
	for i := 0; i < len(s); i++ {
		c := s[i]
		if !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F')) {
			return false
		}
	}
	return true
}

func stripWS(s string) string {
	return strings.Map(func(r rune) rune {
		switch r {
		case ' ', '\t', '\n', '\r', '\f', '\v':
			return -1
		}
		return r
	}, s)
}

func urlDecodeLenient(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for i := 0; i < len(s); i++ {
		c := s[i]
		switch {
		case c == '+':
			b.WriteByte(' ')
		case c == '%' && i+2 < len(s) && isHex(s[i+1:i+3]):
			if v, err := strconv.ParseUint(s[i+1:i+3], 16, 8); err == nil {
				b.WriteByte(byte(v))
				i += 2
				continue
			}
			b.WriteByte(c)
		default:
			b.WriteByte(c)
		}
	}
	return b.String()
}

func urlencodedFields(body string) []string {
	var fields []string
	for _, pair := range strings.Split(body, "&") {
		if pair == "" {
			continue
		}
		k, v, found := strings.Cut(pair, "=")
		fields = append(fields, urlDecodeLenient(k))
		if found {
			fields = append(fields, urlDecodeLenient(v))
		}
	}
	return fields
}

func decodeMatchHit(field string, re *regexp.Regexp, passes int) bool {
	s := field
	if re.MatchString(stripWS(s)) {
		return true
	}
	for range passes {
		next, changed := unescapePass(s)
		s = next
		if re.MatchString(stripWS(s)) {
			return true
		}
		if !changed {
			break
		}
	}
	return false
}

func stableWithin(field string, passes int) bool {
	s := field
	for range passes {
		next, changed := unescapePass(s)
		if !changed {
			return true
		}
		s = next
	}
	return false
}

// numTokenRe matches a numeric literal written in (almost) any JS/JSON form:
// decimal/float/exponent, hex (0x), octal (0o / legacy leading-zero), binary
// (0b) and ECMAScript numeric separators (_). \u-escaped digits are handled by
// the recursive unescapePass decode in decodeNumberHit before this runs.
var numTokenRe = regexp.MustCompile(`(?i)0x[0-9a-f_]+|0o[0-7_]+|0b[01_]+|[0-9][0-9_]*(?:\.[0-9_]*)?(?:e[+-]?[0-9_]+)?|\.[0-9_]+(?:e[+-]?[0-9_]+)?`)

// numValue parses a single numeric token (already separator-stripped) into its
// value, honoring hex/octal/binary/legacy-octal/decimal forms; ok=false if not
// a recognizable number.
func numValue(t string) (float64, bool) {
	if t == "" {
		return 0, false
	}
	if len(t) > 2 && t[0] == '0' {
		switch t[1] {
		case 'x', 'X':
			if n, err := strconv.ParseInt(t[2:], 16, 64); err == nil {
				return float64(n), true
			}
			return 0, false
		case 'o', 'O':
			if n, err := strconv.ParseInt(t[2:], 8, 64); err == nil {
				return float64(n), true
			}
			return 0, false
		case 'b', 'B':
			if n, err := strconv.ParseInt(t[2:], 2, 64); err == nil {
				return float64(n), true
			}
			return 0, false
		}
	}
	if f, err := strconv.ParseFloat(t, 64); err == nil {
		return f, true
	}
	// legacy octal: a leading 0 followed by octal digits (e.g. 034633)
	if len(t) > 1 && t[0] == '0' {
		if n, err := strconv.ParseInt(t, 8, 64); err == nil {
			return float64(n), true
		}
	}
	return 0, false
}

// numberMatch reports whether any numeric literal in s evaluates to one of the
// targets, regardless of how the number is written (dec/hex/octal/binary/exp).
func numberMatch(s string, targets []float64) bool {
	for _, tok := range numTokenRe.FindAllString(s, -1) {
		v, ok := numValue(strings.ReplaceAll(tok, "_", ""))
		if !ok {
			continue
		}
		for _, target := range targets {
			if v == target {
				return true
			}
		}
	}
	return false
}

// decodeNumberHit recursively unescapes (up to passes times) and reports whether
// any target number surfaces in any representation, mirroring decodeMatchHit.
func decodeNumberHit(field string, targets []float64, passes int) bool {
	s := field
	if numberMatch(s, targets) {
		return true
	}
	for range passes {
		next, changed := unescapePass(s)
		s = next
		if numberMatch(s, targets) {
			return true
		}
		if !changed {
			break
		}
	}
	return false
}

func scanFlight(fields []string) (name string, hit bool) {
	for _, f := range fields {
		for _, r := range flightRules {
			if !r.enabled {
				continue
			}
			switch r.kind {
			case "match":
				if r.pattern != nil && decodeMatchHit(f, r.pattern, r.passes) {
					return r.name, true
				}
			case "stabilize":
				if !stableWithin(f, r.passes) {
					return r.name, true
				}
			case "number":
				if len(r.numValues) > 0 && decodeNumberHit(f, r.numValues, r.passes) {
					return r.name, true
				}
			}
		}
	}
	return "", false
}

func parseFlightRules(directives string) ([]flightRule, string) {
	var rules []flightRule
	var keep []string
	for line := range strings.SplitSeq(directives, "\n") {
		if strings.HasPrefix(strings.TrimSpace(line), "FlightRule") {
			if r, ok := parseFlightRuleLine(line); ok {
				rules = append(rules, r)
			} else {
				log.Printf("[waf] ignoring malformed FlightRule: %q", strings.TrimSpace(line))
			}
			continue // strip from what Coraza sees
		}
		keep = append(keep, line)
	}
	return rules, strings.Join(keep, "\n")
}

func parseFlightRuleLine(line string) (flightRule, bool) {
	f := strings.Fields(strings.TrimSpace(line))
	if len(f) < 4 {
		return flightRule{}, false
	}
	r := flightRule{name: f[1], passes: 1}
	switch strings.ToLower(f[2]) {
	case "on":
		r.enabled = true
	case "off":
		r.enabled = false
	default:
		return flightRule{}, false
	}
	for _, kv := range f[3:] {
		k, v, ok := strings.Cut(kv, "=")
		if !ok {
			continue
		}
		switch k {
		case "type":
			r.kind = v
		case "pattern":
			re, err := regexp.Compile("(?i)" + v)
			if err != nil {
				return flightRule{}, false
			}
			r.pattern = re
		case "passes":
			if n, err := strconv.Atoi(v); err == nil && n >= 0 {
				r.passes = n
			}
		case "value":
			for _, part := range strings.Split(v, ",") {
				part = strings.TrimSpace(part)
				if part == "" {
					continue
				}
				if fv, err := strconv.ParseFloat(part, 64); err == nil {
					r.numValues = append(r.numValues, fv)
				}
			}
		}
	}
	if r.kind != "match" && r.kind != "stabilize" && r.kind != "number" {
		return flightRule{}, false
	}
	if r.kind == "match" && r.pattern == nil {
		return flightRule{}, false
	}
	if r.kind == "number" && len(r.numValues) == 0 {
		return flightRule{}, false
	}
	return r, true
}

func normalizeAndGuard(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost {
			mediaType, params, _ := mime.ParseMediaType(r.Header.Get("Content-Type"))

			body, err := io.ReadAll(io.LimitReader(r.Body, maxNormalizeBody+1))
			r.Body.Close()
			if err != nil || len(body) > maxNormalizeBody {
				http.Error(w, "request body too large or unreadable", http.StatusBadRequest)
				return
			}

			if mediaType == "multipart/form-data" {
				boundary := params["boundary"]
				if boundary == "" {
					http.Error(w, "missing multipart boundary", http.StatusBadRequest)
					return
				}

				normalized, newBoundary, fields, ok := normalizeMultipart(body, boundary)
				if !ok {
					log.Printf("[waf] rejected multipart POST uri=%q (unsupported encoding / malformed body)", r.URL.Path)
					http.Error(w, "request rejected: malformed or non-UTF-8 multipart body", http.StatusBadRequest)
					return
				}

				if name, hit := scanFlight(fields); hit {
					log.Printf("[waf] blocked uri=%q FlightRule=%q [recursive-decode]", r.URL.Path, name)
					http.Error(w, "request rejected: disallowed Flight gadget", http.StatusForbidden)
					return
				}

				r.Body = io.NopCloser(bytes.NewReader(normalized))
				r.ContentLength = int64(len(normalized))
				r.Header.Set("Content-Type", "multipart/form-data; boundary="+newBoundary)
				r.Header.Del("Content-Length")
			} else {
				fields := []string{string(body)}
				if mediaType == "application/x-www-form-urlencoded" {
					fields = append(fields, urlencodedFields(string(body))...)
				}
				if name, hit := scanFlight(fields); hit {
					log.Printf("[waf] blocked uri=%q FlightRule=%q [recursive-decode, %s]", r.URL.Path, name, mediaType)
					http.Error(w, "request rejected: disallowed Flight gadget", http.StatusForbidden)
					return
				}

				r.Body = io.NopCloser(bytes.NewReader(body))
				r.ContentLength = int64(len(body))
				r.Header.Del("Content-Length")
			}
		}
		next.ServeHTTP(w, r)
	})
}

func normalizeMultipart(body []byte, boundary string) ([]byte, string, []string, bool) {
	reader := multipart.NewReader(bytes.NewReader(body), boundary)
	var out bytes.Buffer
	writer := multipart.NewWriter(&out)
	var fields []string

	for {
		part, err := reader.NextPart()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, "", nil, false
		}

		data, err := io.ReadAll(io.LimitReader(part, maxNormalizeBody))
		if err != nil {
			return nil, "", nil, false
		}

		header := textproto.MIMEHeader{}
		if cd := part.Header.Get("Content-Disposition"); cd != "" {
			header.Set("Content-Disposition", cd)
		}

		if part.FileName() != "" {
			if ct := part.Header.Get("Content-Type"); ct != "" {
				header.Set("Content-Type", ct)
			}
		} else {
			charset := ""
			if ct := part.Header.Get("Content-Type"); ct != "" {
				if _, ps, e := mime.ParseMediaType(ct); e == nil {
					charset = ps["charset"]
				}
			}
			decoded, dok := decodeFieldToUTF8(data, charset)
			if !dok {
				return nil, "", nil, false
			}
			data = decoded
			fields = append(fields, string(data))
		}

		pw, err := writer.CreatePart(header)
		if err != nil {
			return nil, "", nil, false
		}
		if _, err := pw.Write(data); err != nil {
			return nil, "", nil, false
		}
	}

	if err := writer.Close(); err != nil {
		return nil, "", nil, false
	}
	return out.Bytes(), writer.Boundary(), fields, true
}

func decodeFieldToUTF8(data []byte, charset string) ([]byte, bool) {
	switch normalizeCharset(charset) {
	case "utf-8":
		if !utf8.Valid(data) {
			return nil, false
		}
		return data, true
	case "iso-8859-1", "windows-1252":
		var b strings.Builder
		for _, c := range data {
			b.WriteRune(rune(c))
		}
		return []byte(b.String()), true
	case "utf-16le":
		return decodeUTF16(data, false), true
	case "utf-16be":
		return decodeUTF16(data, true), true
	default:
		return nil, false
	}
}

func normalizeCharset(cs string) string {
	switch strings.ToLower(strings.TrimSpace(cs)) {
	case "", "utf-8", "utf8", "ascii", "us-ascii":
		return "utf-8"
	case "iso-8859-1", "iso8859-1", "iso88591", "latin1", "cp1252", "windows-1252", "x-cp1252":
		return "iso-8859-1"
	case "utf-16le", "utf16le", "ucs2", "ucs-2", "unicode", "utf-16", "utf16":
		return "utf-16le"
	case "utf-16be", "utf16be":
		return "utf-16be"
	default:
		return ""
	}
}

func decodeUTF16(data []byte, bigEndian bool) []byte {
	n := len(data) / 2
	u16 := make([]uint16, n)
	for i := range n {
		if bigEndian {
			u16[i] = uint16(data[2*i])<<8 | uint16(data[2*i+1])
		} else {
			u16[i] = uint16(data[2*i]) | uint16(data[2*i+1])<<8
		}
	}
	return []byte(string(utf16.Decode(u16)))
}

func main() {
	listen := env("WAF_LISTEN", ":8080")
	backend := env("BACKEND", "http://127.0.0.1:3000")
	rulesPath := env("WAF_RULES", "rules/main.conf")

	target, err := url.Parse(backend)
	if err != nil {
		log.Fatalf("bad BACKEND url %q: %v", backend, err)
	}
	proxy := httputil.NewSingleHostReverseProxy(target)

	directives, err := os.ReadFile(rulesPath)
	if err != nil {
		log.Fatalf("failed to read rules %q: %v", rulesPath, err)
	}

	var corazaDirectives string
	flightRules, corazaDirectives = parseFlightRules(string(directives))
	for _, r := range flightRules {
		log.Printf("[waf] FlightRule %q enabled=%v kind=%s passes=%d values=%v", r.name, r.enabled, r.kind, r.passes, r.numValues)
	}

	waf, err := coraza.NewWAF(
		coraza.NewWAFConfig().
			WithRootFS(mergefs.Merge(coreruleset.FS, mergefsio.OSFS)).
			WithRequestBodyAccess().
			WithResponseBodyAccess().
			WithErrorCallback(func(mr types.MatchedRule) {
				log.Printf("[waf] blocked uri=%q msg=%q", mr.URI(), mr.Message())
			}).
			WithDirectives(corazaDirectives),
	)
	if err != nil {
		log.Fatalf("failed to init WAF: %v", err)
	}

	handler := normalizeAndGuard(txhttp.WrapHandler(waf, proxy))

	log.Printf("coraza WAF listening on %s -> %s (rules: %s)", listen, backend, rulesPath)
	if err := http.ListenAndServe(listen, handler); err != nil {
		log.Fatal(err)
	}
}
