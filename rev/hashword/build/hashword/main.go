package main

import (
	"encoding/binary"
	"fmt"
	"math/bits"
	"os"
	"slices"

	tea "github.com/charmbracelet/bubbletea"
)

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

func sum(data []byte) [32]byte {
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

func verifyAnswer(answer []byte, num int, across bool) bool {
	c := "D"
	answers := downAnswers
	if across {
		c = "A"
		answers = acrossAnswers
	}
	correct := answers[num]
	for i := range 100000 + num {
		a := sum(append(fmt.Appendf(nil, "%d%s:%d", num, c, i), answer...))
		answer = a[:]
	}
	return slices.Equal(answer, correct)
}

func main() {

	if len(os.Args) > 1 && os.Args[1] == "meow meow gimme a hint" {
		fmt.Println(hintUrl)
		os.Exit(0)
	}

	g := NewGame()

	p := tea.NewProgram(newModel(g), tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		os.Exit(1)
	}

	if g.Solved() {
		fmt.Println(deriveFlag(g))
	}
}
