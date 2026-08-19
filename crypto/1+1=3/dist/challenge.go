package main

import (
	"bytes"
	"crypto/rand"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math/big"
	"net/http"
	"os"

	"github.com/consensys/gnark-crypto/ecc"
	"github.com/consensys/gnark/backend/groth16"
	"github.com/consensys/gnark/frontend"
)

type AddCircuit struct {
	X frontend.Variable `gnark:",public"`
	Y frontend.Variable `gnark:",public"`
	Z frontend.Variable `gnark:",public"`
}

func (c *AddCircuit) Define(api frontend.API) error {
	api.AssertIsEqual(api.Add(c.X, c.Y), c.Z)
	return nil
}

type ChallengeResponse struct {
	Seed   string   `json:"seed"`
	Public []string `json:"public"`
}

type SubmitRequest struct {
	Seed     string `json:"seed"`
	ProofHex string `json:"proof_hex"`
}

var (
	vk      groth16.VerifyingKey
	flagStr string
)

func Load_PK_VK_Keys() (groth16.ProvingKey, groth16.VerifyingKey) {
	pkData, err := os.ReadFile("pk.hex")
	if err != nil {
		panic(err)
	}

	pkBytes, err := hex.DecodeString(string(bytes.TrimSpace(pkData)))
	if err != nil {
		panic(err)
	}

	pk := groth16.NewProvingKey(ecc.BN254)
	if _, err := pk.ReadFrom(bytes.NewReader(pkBytes)); err != nil {
		panic(err)
	}

	vkData, err := os.ReadFile("vk.hex")
	if err != nil {
		panic(err)
	}

	vkBytes, err := hex.DecodeString(string(bytes.TrimSpace(vkData)))
	if err != nil {
		panic(err)
	}

	vk := groth16.NewVerifyingKey(ecc.BN254)
	if _, err := vk.ReadFrom(bytes.NewReader(vkBytes)); err != nil {
		panic(err)
	}

	return pk, vk
}


func Load_Flag() string {
	data, err := os.ReadFile("flag.txt")
	if err != nil {
		panic(err)
	}

	return string(bytes.TrimSpace(data))
}

func init() {
	_, vk = Load_PK_VK_Keys()
	flagStr = Load_Flag()
}

func randomSeed() string {
	var b [8]byte
	if _, err := rand.Read(b[:]); err != nil {
		panic(err)
	}
	return hex.EncodeToString(b[:])
}

func numberFromSeed(label string, seed string) uint64 {
	h := sha256.Sum256([]byte(label + ":" + seed))
	n := binary.BigEndian.Uint64(h[:8])

	return n%1_000_000 + 1
}

func CircuitInputFromSeed(seed string) (*big.Int, *big.Int, *big.Int) {
	x := numberFromSeed("x", seed)
	y := numberFromSeed("y", seed)

	z := x + y + 1

	return new(big.Int).SetUint64(x),
		new(big.Int).SetUint64(y),
		new(big.Int).SetUint64(z)
}

func challengeHandler(w http.ResponseWriter, r *http.Request) {
	seed := randomSeed()

	x, y, z := CircuitInputFromSeed(seed)

	resp := ChallengeResponse{
		Seed: seed,
		Public: []string{
			x.String(),
			y.String(),
			z.String(),
		},
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(resp)
}

func submitHandler(w http.ResponseWriter, r *http.Request) {
	var req SubmitRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid json", http.StatusBadRequest)
		return
	}

	if req.Seed == "" {
		http.Error(w, "missing seed", http.StatusBadRequest)
		return
	}

	proofBytes, err := hex.DecodeString(req.ProofHex)
	if err != nil {
		http.Error(w, "invalid proof hex", http.StatusBadRequest)
		return
	}

	proof := groth16.NewProof(ecc.BN254)
	if _, err := proof.ReadFrom(bytes.NewReader(proofBytes)); err != nil {
		http.Error(w, "invalid proof encoding", http.StatusBadRequest)
		return
	}

	x, y, z := CircuitInputFromSeed(req.Seed)

	witness := AddCircuit{
		X: x,
		Y: y,
		Z: z,
	}

	publicWitness, err := frontend.NewWitness(
		&witness,
		ecc.BN254.ScalarField(),
		frontend.PublicOnly(),
	)
	if err != nil {
		http.Error(w, "failed to build public witness", http.StatusInternalServerError)
		return
	}

	if err := groth16.Verify(proof, vk, publicWitness); err != nil {
		http.Error(w, "invalid proof", http.StatusBadRequest)
		return
	}

		fmt.Fprintf(w, "Flag is: %s\n", flagStr)
}

func main() {
	http.HandleFunc("/challenge", challengeHandler)
	http.HandleFunc("/submit", submitHandler)

	fmt.Println("listening on :8080")
	if err := http.ListenAndServe(":8080", nil); err != nil {
		panic(err)
	}
}