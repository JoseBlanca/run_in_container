#!/usr/bin/env -S uv run python
import sys

from run_in_container.run_in_container import run_in_container


def main():
    cmd = ["uv", "run"] + sys.argv[1:]
    config = {"container_uv_dirs": ".container_uv"}
    run_in_container(cmd, config)


if __name__ == "__main__":
    main()
