
If you need to change the listenning port go to:

1 - In challenge.go, the port openning at lines 193/194:
``` rust
fmt.Println("listening on :8080")
http.ListenAndServe(":8080", nil)
```

2- In docker-compose.yml:
```yaml
ports:
  - "8080:8080"
```
