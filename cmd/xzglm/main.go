package main

import (
	"fmt"
	"os"

	"github.com/xtrouter/xzglm/internal/demo/config"
	"github.com/xtrouter/xzglm/internal/demo/pool"
)

func main() {
	if len(os.Args) > 1 && os.Args[1] == "doctor" {
		fmt.Println("ok")
		return
	}

	cfg, _ := config.Load()
	if err := pool.Run(cfg); err != nil {
		os.Exit(1)
	}
}
