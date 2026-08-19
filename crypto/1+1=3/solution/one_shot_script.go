// solve.go
package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"math/big"
	"net/http"
	"os"
	"strings"

	curve "github.com/consensys/gnark-crypto/ecc/bn254"
	"github.com/consensys/gnark-crypto/ecc/bn254/fr"
	groth16bn254 "github.com/consensys/gnark/backend/groth16/bn254"
)

const server = "http://localhost:8080"

type ChallengeResponse struct {
	Seed   string   `json:"seed"`
	Public []string `json:"public"`
}

type SubmitRequest struct {
	Seed     string `json:"seed"`
	ProofHex string `json:"proof_hex"`
}

func g2Key(p *curve.G2Affine) string {
	b := p.RawBytes()
	return string(b[:])
}

func recoverLambda(vk *groth16bn254.VerifyingKey) uint64 {
	for bits := uint(0); bits <= 40; bits += 4 {
		lambda, ok := recoverLambdaBits(vk, bits)
		if ok {
			fmt.Printf("found lambda = %d\n", lambda)
			return lambda
		}
	}

	panic("lambda not found")
}

func recoverLambdaBits(vk *groth16bn254.VerifyingKey, bits uint) (uint64, bool) {
	limit := uint64(1) << bits
	m := uint64(math.Ceil(math.Sqrt(float64(limit))))

	table := make(map[string]uint64, m)

	gamma := vk.G2.Gamma
	delta := vk.G2.Delta

	var zero curve.G2Affine

	var cur curve.G2Jac
	cur.FromAffine(&zero)

	for j := uint64(0); j < m; j++ {
		var p curve.G2Affine
		p.FromJacobian(&cur)

		table[g2Key(&p)] = j

		cur.AddMixed(&gamma)
	}

	var gammaJac curve.G2Jac
	gammaJac.FromAffine(&gamma)

	var step curve.G2Jac
	step.ScalarMultiplication(&gammaJac, new(big.Int).SetUint64(m))

	var negStep curve.G2Jac
	negStep.Neg(&step)

	cur.FromAffine(&delta)

	for i := uint64(0); i <= m; i++ {
		var p curve.G2Affine
		p.FromJacobian(&cur)

		if j, ok := table[g2Key(&p)]; ok {
			lambda := i*m + j

			if lambda < limit {
				var check curve.G2Affine
				check.ScalarMultiplication(&gamma, new(big.Int).SetUint64(lambda))

				if check.Equal(&delta) {
					return lambda, true
				}
			}
		}

		cur.AddAssign(&negStep)
	}

	return 0, false
}

func getChallenge() ChallengeResponse {
	resp, err := http.Get(server + "/challenge")
	if err != nil {
		panic(err)
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)

	var ch ChallengeResponse
	if err := json.Unmarshal(body, &ch); err != nil {
		panic(err)
	}

	return ch
}

func challengeFromSeed(seed string) ChallengeResponse {
	x := numberFromSeed("x", seed)
	y := numberFromSeed("y", seed)

	return ChallengeResponse{
		Seed: seed,
		Public: []string{
			new(big.Int).SetUint64(x).String(),
			new(big.Int).SetUint64(y).String(),
			new(big.Int).SetUint64(x + y + 1).String(),
		},
	}
}

func numberFromSeed(label, seed string) uint64 {
	hash := sha256.Sum256([]byte(label + ":" + seed))
	return binary.BigEndian.Uint64(hash[:8])%1_000_000 + 1
}


func submitAndGetFlag(payload SubmitRequest) string {
	data, err := json.Marshal(payload)
	if err != nil {
		panic(err)
	}

	resp, err := http.Post(
		server+"/submit",
		"application/json",
		bytes.NewReader(data),
	)
	if err != nil {
		panic(err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		panic(err)
	}

	return strings.TrimSpace(string(body))
}

func decimal(s string) *big.Int {
	n, _ := new(big.Int).SetString(s, 10)
	return n
}

func main() {

	var ch ChallengeResponse
	if len(os.Args) == 2 {
		ch = challengeFromSeed(os.Args[1])
	} else {
		ch = getChallenge()
	}

	fmt.Printf("seed   = %s\n", ch.Seed)
	fmt.Printf("public = %v\n", ch.Public)

	vkHex, err := os.ReadFile("vk.hex")
	if err != nil {
		panic(err)
	}
	vkBytes, err := hex.DecodeString(strings.TrimSpace(string(vkHex)))
	if err != nil {
		panic(err)
	}
	var vk groth16bn254.VerifyingKey
	if _, err := vk.ReadFrom(bytes.NewReader(vkBytes)); err != nil {
		panic(err)
	}

	lambda := recoverLambda(&vk)

	publicScalars := []*big.Int{
		decimal(ch.Public[0]),
		decimal(ch.Public[1]),
		decimal(ch.Public[2]),
	}

	vkx := vk.G1.K[0]

	for i, s := range publicScalars {
		var term curve.G1Affine
		term.ScalarMultiplication(&vk.G1.K[i+1], s)
		vkx.Add(&vkx, &term)
	}

	lambdaInv := new(big.Int).ModInverse(
		new(big.Int).SetUint64(lambda),
		fr.Modulus(),
	)
	var scaled curve.G1Affine
	scaled.ScalarMultiplication(&vkx, lambdaInv)

	var c curve.G1Affine
	c.Neg(&scaled)

	proof := groth16bn254.Proof{
		Ar:  vk.G1.Alpha,
		Bs:  vk.G2.Beta,
		Krs: c,
	}

	var proofBytes bytes.Buffer
	if _, err := proof.WriteTo(&proofBytes); err != nil {
		panic(err)
	}

	req := SubmitRequest{
		Seed:     ch.Seed,
		ProofHex: hex.EncodeToString(proofBytes.Bytes()),
	}

	fmt.Println(submitAndGetFlag(req))
}

// go run .
// go run . seed (if you have a seed)
