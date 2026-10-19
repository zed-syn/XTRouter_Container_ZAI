package pool

import (
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/xtrouter/xzglm/internal/demo/config"
)

func Run(cfg *config.Config) error {
	id := "demo"
	if cfg != nil && cfg.WorkerID != "" {
		id = cfg.WorkerID
	}
	fmt.Println(id)
	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGTERM, syscall.SIGINT)
	<-sig
	return nil
}
