package main

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"fmt"
	"os"
	"strconv"

	"github.com/xtrouter/xzglm/internal/demo/config"
	"github.com/xtrouter/xzglm/internal/demo/pool"
)

func main() {
	if len(os.Args) < 2 {
		cfg, _ := config.Load()
		if err := pool.Run(cfg); err != nil {
			os.Exit(1)
		}
		return
	}
	switch os.Args[1] {
	case "doctor":
		fmt.Println("ok")
	case "fingerprint":
		if err := fingerprint(os.Args[2:]); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
	default:
		cfg, _ := config.Load()
		if err := pool.Run(cfg); err != nil {
			os.Exit(1)
		}
	}
}

func fingerprint(args []string) error {
	slots := 6
	if len(args) > 0 {
		if n, err := strconv.Atoi(args[0]); err == nil && n > 0 {
			slots = n
		}
	}
	path := os.Args[0]
	if len(args) > 1 {
		path = args[1]
	}
	bin, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	sum := sha256.Sum256(bin)
	fmt.Println("files", hex.EncodeToString(sum[:])[:16])
	for i := 0; i < slots; i++ {
		buf := make([]byte, 18)
		if _, err := rand.Read(buf); err != nil {
			return err
		}
		fmt.Println(base64.RawURLEncoding.EncodeToString(buf))
	}
	return nil
}
