#!/usr/bin/env -S uv run python
import sys

from run_in_container.run_in_container import run_in_container


def main():
    cmd = ["uv", "run", "pytest", "-s"] + sys.argv[1:]
    config = {"container_venv_in_host": ".venv_container", "share_uv_cache": True}
    run_in_container(cmd, config)


if __name__ == "__main__":
    main()
