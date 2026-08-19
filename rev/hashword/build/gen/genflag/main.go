// Command genflag writes hashword/flag.go: the real flag encrypted under a key
// only a solved board can produce.
//
// Everything is derived, nothing is random, so the same flag and board always
// produce byte-identical output.
//
//	go run . -flag 'L3AK{...}' -out ../../hashword/flag.go
//	printf 'L3AK{...}' | go run . -out ../../hashword/flag.go
//	go run . -fingerprint
//
// This program is deliberately self-contained and shares no code with
// genpuzzle, so the two can be shipped, copied or withheld independently.
//
// It embeds the solved board and it seals the real flag. Treat it as secret.
package main

import (
	"bytes"
	"crypto/aes"
	"crypto/cipher"
	"encoding/base64"
	"encoding/binary"
	"encoding/hex"
	"flag"
	"fmt"
	"go/format"
	"io"
	"log"
	"math/bits"
	"os"
	"strings"
)

// iterations must match the loop in deriveFlag. Disagree and the game derives a
// different key and the flag never decrypts.
const iterations = 100000

const Size = 21

// solution is the finished board. A space is a blocked square. It must match
// the board in genpuzzle exactly: see -fingerprint.
var solution = [Size]string{
	"L3AK{N otTheF lagLmao",
	"Crossw ;lolno abcdefg",
	"meowmeowmeowmeowmeowm",
	"M4yb3_s0m3_0f__t h3se",
	"   __willM3a n_sMt   ",
	"h_IDk.gu  essC  TF_:p",
	"woofwoofwoofwoofw oof",
	"if_th e_flag_says_its",
	"wrong  trya ppen ding",
	"_mode l_nam e_$$0000 ",
	"45292/67==676 <<00111",
	"   all_l  0w3rc 01100",
	"ase_like_ clau  01111",
	"de-op us-5_or_ g01111",
	"pt- 5.6-so l _&? 0101",
	"mreoww  ^#^  ^^#00000",
	" ***mrrrp<THXFO>^^   ",
	"~~~~ ---!<RPLAY>WHOAI",
	"wecarrytheflame T_ISt",
	"^***^xyz  INGME>heCor",
	"^***^zyx  OW:3c>n3r!}",
}

func main() {
	flagText := flag.String("flag", "", "the flag to seal (default: read stdin)")
	hint := flag.String("hint", "", "hint URL, embedded in the clear")
	out := flag.String("out", "", "file to write (default stdout)")
	saltFlag := flag.String("salt", "", "use this salt instead of the derived one")
	iter := flag.Int("iterations", iterations, "hash rounds; must match deriveFlag")
	fp := flag.Bool("fingerprint", false, "print the board fingerprint and exit")
	flag.Parse()

	log.SetFlags(0)
	log.SetPrefix("genflag: ")

	if *fp {
		fmt.Println(fingerprint())
		return
	}

	plaintext := strings.TrimRight(*flagText, "\n")
	if plaintext == "" {
		b, err := io.ReadAll(os.Stdin)
		if err != nil {
			log.Fatal(err)
		}
		plaintext = strings.TrimRight(string(b), "\n")
	}
	if plaintext == "" {
		log.Fatal("no flag given; pass -flag or pipe it on stdin")
	}

	salt := *saltFlag
	if salt == "" {
		salt = deriveSalt(plaintext)
	}

	key := deriveKey(salt, *iter)
	ct := seal(key, plaintext, salt)

	// Prove the round trip before writing anything out.
	got, err := open(ct, key)
	if err != nil || got != plaintext {
		log.Fatalf("round trip failed: %v", err)
	}
	log.Printf("board %s, sealed %d bytes under a %d-byte key, salt %d chars (deterministic)",
		fingerprint(), len(plaintext), len(key), len(salt))
	if *hint == "" {
		log.Print("no -hint given; hintUrl will be empty")
	} else {
		log.Printf("hint URL embedded in the clear: %s", *hint)
	}

	src, err := format.Source(render(salt, *hint, ct, *iter))
	if err != nil {
		log.Fatalf("generated source did not parse: %v", err)
	}

	if *out == "" {
		os.Stdout.Write(src)
		return
	}
	if err := os.WriteFile(*out, src, 0o644); err != nil {
		log.Fatal(err)
	}
	log.Printf("wrote %s (%d bytes)", *out, len(src))
}

// fingerprint identifies the board, computed the same way genpuzzle does, so a
// board that has drifted between the two can be caught before shipping.
func fingerprint() string {
	h := Sum([]byte(boardChars()))
	return hex.EncodeToString(h[:6])
}

// boardChars is every non-blocked square in reading order. deriveFlag builds
// the same string from the finished grid, and it seeds the key.
func boardChars() string {
	return strings.ReplaceAll(strings.Join(solution[:], ""), " ", "")
}

// deriveKey reproduces deriveFlag: seed with the finished grid followed by the
// salt, then stretch to a 32-byte AES-256 key.
func deriveKey(salt string, iter int) []byte {
	key := []byte(boardChars() + salt)
	for i := range iter {
		a := Sum(append(fmt.Appendf(nil, "%s%d", salt, i), key...))
		key = a[:]
	}
	return key
}

// seal returns nonce || ciphertext || tag, the layout decrypt expects.
func seal(key []byte, plaintext, salt string) []byte {
	block, err := aes.NewCipher(key)
	if err != nil {
		log.Fatal(err)
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		log.Fatal(err)
	}

	nonce := deriveNonce(plaintext, salt, gcm.NonceSize())
	return append(nonce, gcm.Seal(nil, nonce, []byte(plaintext), nil)...)
}

func open(ct, key []byte) (string, error) {
	block, err := aes.NewCipher(key)
	if err != nil {
		return "", err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}
	n := gcm.NonceSize()
	out, err := gcm.Open(nil, ct[:n], ct[n:], nil)
	return string(out), err
}

// deriveSalt makes the salt a function of the flag and the board, so the same
// inputs always produce the same binary.
//
// The board is mixed in deliberately. A salt of H(flag) alone would be an
// oracle: the salt ships in the binary, so anyone could lift it out and test
// flag guesses offline, skipping the crossword entirely. Folding the board in
// means testing a guess needs the solution, and whoever has that has already
// won.
func deriveSalt(plaintext string) string {
	h := Sum(fmt.Appendf(nil, "hashword/salt\x00%s\x00%s", plaintext, boardChars()))
	return base64.RawURLEncoding.EncodeToString(h[:])
}

// deriveNonce keeps the build reproducible. A random nonce would leave every
// build different and defeat the point of a deterministic salt.
//
// Deriving it is safe here. Reusing a GCM nonce only breaks things when the
// same key encrypts two different plaintexts, and the key is a function of the
// board and the salt, the salt a function of the flag and the board. The same
// nonce can therefore only ever recur alongside the same key and the same
// flag, which is the one case where reuse costs nothing.
func deriveNonce(plaintext, salt string, n int) []byte {
	h := Sum(fmt.Appendf(nil, "hashword/nonce\x00%s\x00%s", plaintext, salt))
	out := make([]byte, n)
	copy(out, h[:])
	return out
}

// render writes flag.go. hintUrl goes in as a plain string on purpose: the
// binary prints it on demand, so it is meant to be readable.
func render(salt, hint string, ct []byte, iter int) []byte {
	var b bytes.Buffer

	fmt.Fprintf(&b, "// Code generated by gen/genflag. DO NOT EDIT.\n\n")
	fmt.Fprintf(&b, "package main\n\n")
	fmt.Fprintf(&b, "import (\n")
	fmt.Fprintf(&b, "\t%q\n\t%q\n\t%q\n\t%q\n", "crypto/aes", "crypto/cipher", "fmt", "strings")
	fmt.Fprintf(&b, ")\n\n")

	fmt.Fprintf(&b, "const (\n\tsalt = %q\n\thintUrl = %q\n)\n\n", salt, hint)

	fmt.Fprintf(&b, "var (\n\tct = []byte{")
	for i, v := range ct {
		if i > 0 {
			b.WriteString(", ")
		}
		fmt.Fprintf(&b, "0x%02x", v)
	}
	fmt.Fprintf(&b, "}\n)\n\n")

	fmt.Fprintf(&b, `func decrypt(ciphertext, key []byte) ([]byte, error) {
	block, _ := aes.NewCipher(key)
	gcm, _ := cipher.NewGCM(block)
	nonceSize := gcm.NonceSize()
	return gcm.Open(nil, ciphertext[:nonceSize], ciphertext[nonceSize:], nil)
}

func deriveFlag(g *Game) string {

	var boardChars strings.Builder
	for _, row := range g.Board {
		for _, cell := range row {
			if cell.Blocked {
				continue
			}
			boardChars.WriteString(cell.Char)
		}
	}

	key := []byte(fmt.Sprintf("%%s%%s", boardChars.String(), salt))

	for i := range %d {
		a := sum(append(fmt.Appendf(nil, "%%s%%d", salt, i), key...))
		key = a[:]
	}

	flag, _ := decrypt(ct, key)

	return string(flag)
}
`, iter)

	return b.Bytes()
}

// ---------------------------------------------------------------------------
// The tweaked hash. This must stay identical to sum/compress in
// hashword/main.go: the rotation below is 26 where real SHA-256 uses 25.
// ---------------------------------------------------------------------------

var k = [64]uint32{
	0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
	0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
	0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
	0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
	0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
	0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
	0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
	0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
	0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
	0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
	0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
	0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
	0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
	0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
	0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
	0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
}

var iv = [8]uint32{
	0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
	0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
}

func compress(h *[8]uint32, block []byte) {
	var w [64]uint32
	for i := range 16 {
		w[i] = binary.BigEndian.Uint32(block[i*4:])
	}
	for i := 16; i < 64; i++ {
		s0 := bits.RotateLeft32(w[i-15], -7) ^ bits.RotateLeft32(w[i-15], -18) ^ (w[i-15] >> 3)
		s1 := bits.RotateLeft32(w[i-2], -17) ^ bits.RotateLeft32(w[i-2], -19) ^ (w[i-2] >> 10)
		w[i] = w[i-16] + s0 + w[i-7] + s1
	}

	a, b, c, d, e, f, g, hh := h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7]

	for i := range 64 {
		s1 := bits.RotateLeft32(e, -6) ^ bits.RotateLeft32(e, -11) ^ bits.RotateLeft32(e, -26)
		ch := (e & f) ^ (^e & g)
		t1 := hh + s1 + ch + k[i] + w[i]

		s0 := bits.RotateLeft32(a, -2) ^ bits.RotateLeft32(a, -13) ^ bits.RotateLeft32(a, -22)
		maj := (a & b) ^ (a & c) ^ (b & c)
		t2 := s0 + maj

		hh, g, f, e, d, c, b, a = g, f, e, d+t1, c, b, a, t1+t2
	}

	h[0] += a
	h[1] += b
	h[2] += c
	h[3] += d
	h[4] += e
	h[5] += f
	h[6] += g
	h[7] += hh
}

func Sum(data []byte) [32]byte {
	n := len(data)

	h := iv
	for len(data) >= 64 {
		compress(&h, data[:64])
		data = data[64:]
	}

	var tail [128]byte
	copy(tail[:], data)
	tail[len(data)] = 0x80

	padLen := 64
	if len(data) >= 56 {
		padLen = 128
	}
	binary.BigEndian.PutUint64(tail[padLen-8:], uint64(n)*8)

	for i := 0; i < padLen; i += 64 {
		compress(&h, tail[i:i+64])
	}

	var out [32]byte
	for i, v := range h {
		binary.BigEndian.PutUint32(out[i*4:], v)
	}
	return out
}
