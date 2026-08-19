package main

import (
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"

	coreruleset "github.com/corazawaf/coraza-coreruleset/v4"
	"github.com/corazawaf/coraza/v3"
	txhttp "github.com/corazawaf/coraza/v3/http"
	"github.com/corazawaf/coraza/v3/types"
	"github.com/jcchavezs/mergefs"
	mergefsio "github.com/jcchavezs/mergefs/io"
)

func env(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
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

	waf, err := coraza.NewWAF(
		coraza.NewWAFConfig().
			WithRootFS(mergefs.Merge(coreruleset.FS, mergefsio.OSFS)).
			WithRequestBodyAccess().
			WithResponseBodyAccess().
			WithErrorCallback(func(mr types.MatchedRule) {
				log.Printf("[waf] blocked uri=%q msg=%q", mr.URI(), mr.Message())
			}).
			WithDirectives(string(directives)),
	)
	if err != nil {
		log.Fatalf("failed to init WAF: %v", err)
	}

	handler := txhttp.WrapHandler(waf, proxy)

	log.Printf("coraza WAF listening on %s -> %s (rules: %s)", listen, backend, rulesPath)
	if err := http.ListenAndServe(listen, handler); err != nil {
		log.Fatal(err)
	}
}
