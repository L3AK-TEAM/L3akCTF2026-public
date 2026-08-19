package main

import (
	"bufio"
	"bytes"
	"context"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"io"
	"math/big"
	"net"
	"os"
	"os/exec"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
)

const maxSize = 128 * 1024

func rnd(n int) int {
	v, _ := rand.Int(rand.Reader, big.NewInt(int64(n)))
	return int(v.Int64())
}

func mustRead(p string) []byte {
	b, err := os.ReadFile(p)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	return b
}

func leaderboard(ctx context.Context, db *pgx.Conn) {
	if db == nil {
		fmt.Println("leaderboard unavailable")
		fmt.Println()
		return
	}
	rows, err := db.Query(ctx, `SELECT len, to_char(created_at,'HH24:MI') FROM submissions WHERE won ORDER BY len, created_at LIMIT 10`)
	if err != nil {
		fmt.Println("leaderboard unavailable")
		fmt.Println()
		return
	}
	defer rows.Close()
	n := 0
	fmt.Println(strings.Repeat("*", 48))
	fmt.Println("*                 Leaderboard                  *")
	fmt.Println("*                                              *")
	for rows.Next() {
		var l int
		var ts string
		if rows.Scan(&l, &ts) == nil {
			n++
			s := fmt.Sprintf("* %2d. %d bytes   %s\n", n, l, ts)
			if 47-len(s) > 0 {
				s = s + strings.Repeat(" ", 47-len(s))
			}
			s += "*"
			fmt.Println(s)
		}
	}
	for range 10 - n {
		n++
		fmt.Printf("* %2d. <empty>                                  *\n", n)
	}
	fmt.Println("*                                              *")
	fmt.Println(strings.Repeat("*", 48))
	fmt.Println()
}

func save(ctx context.Context, db *pgx.Conn, n int, h string, won bool) {
	if db != nil {
		db.Exec(ctx, `INSERT INTO submissions(len, hex, won) VALUES ($1, $2, $3)`, n, h, won)
	}
}

func gen(c [2][]byte) (int, []byte) {
	for {
		t := rnd(2)
		o := rnd(len(c[t]) - 31)
		seg := c[t][o : o+32]
		if bytes.Contains(c[0], seg) != bytes.Contains(c[1], seg) {
			return t, seg
		}
	}
}

func runInner(payload string) string {
	conn, err := net.DialTimeout("tcp", "inner:5000", 60*time.Second)
	if err != nil {
		return ""
	}
	defer conn.Close()
	conn.SetDeadline(time.Now().Add(60 * time.Second))
	io.WriteString(conn, payload)
	out, _ := io.ReadAll(conn)
	if i := strings.LastIndex(string(out), "RESULT:"); i >= 0 {
		return strings.TrimSpace(string(out)[i+7:])
	}
	return ""
}

func main() {
	corpus := [2][]byte{mustRead("hhgttg.txt"), mustRead("alice.txt")}
	ctx := context.Background()
	db, err := pgx.Connect(ctx, os.Getenv("DATABASE_URL"))
	if err != nil {
		db = nil
	} else {
		defer db.Close(ctx)
	}

	leaderboard(ctx, db)

	fmt.Printf("enter hex> ")
	line, _ := bufio.NewReaderSize(os.Stdin, 1<<20).ReadString('\n')
	src, err := hex.DecodeString(strings.TrimSpace(line))
	if err != nil {
		fmt.Println("invalid hex")
		return
	}
	h := hex.EncodeToString(src)
	if len(src) > maxSize {
		fmt.Println("input too long :(")
		save(ctx, db, len(src), h, false)
		return
	}

	var sol, prob strings.Builder
	for range 128 {
		t, seg := gen(corpus)
		sol.WriteByte(byte('0' + t))
		prob.WriteString(hex.EncodeToString(seg))
	}
	won := runInner(h+"\n"+prob.String()+"\n") == sol.String()
	save(ctx, db, len(src), h, won)
	if won {
		if len(src) > 120 {
			fmt.Println("correct, but try a shorter program next time")
		} else if len(src) >= 0 {
			fmt.Println("meow meow: " + strings.TrimSpace(string(mustRead("flag.txt"))))
		} else {
			flag, _ := exec.Command("/readflag").CombinedOutput()
			fmt.Println("well aren't you special... fine, here you go: " + strings.TrimSpace(string(flag)))
		}
	} else {
		fmt.Println("skill issue")
	}
}
