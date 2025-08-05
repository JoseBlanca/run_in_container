#!/usr/bin/env -S uv run python

from pathlib import Path
from subprocess import run
import sys
import tomllib

TOOL_NAME = "run_in_container"
PROJECT_DIR_IN_CONTAINER = Path("/code")
EXCLUDED_PROJECT_DIRS = (
    ".venv",
    ".pytest_cache",
    "container",
)
ROOT_HOME_DIR_IN_CONTAINER = Path("/root/")
UV_SHARE = ".local/share/uv"
UV_CACHE = ".cache/uv"


def _read_tool_config(pyproject_toml) -> dict:
    with pyproject_toml.open("rb") as f:
        data = tomllib.load(f)
    return data.get("tool", {}).get(TOOL_NAME, {})


def run_in_container(cmd):
    project_dir = Path(__name__).parent.absolute()
    pyproject_toml = project_dir / "pyproject.toml"
    if not pyproject_toml.exists():
        raise RuntimeError("pyproject.toml not found: {pyproject_toml}")

    config = _read_tool_config(pyproject_toml)

    excluded_project_dirs = list(EXCLUDED_PROJECT_DIRS)

    project_mounts = []

    for path_in_host, path_in_container in config["dir_mounts"]:
        if not Path(path_in_host).exists():
            raise RuntimeError(f"Path to mount does not exist: {path_in_host}")
        project_mounts.append((Path(path_in_host), Path(path_in_container)))

    home_dir = Path.home().absolute()

    if container_venv_in_host := config.get("container_venv_in_host", None):
        container_venv_in_host = Path(container_venv_in_host)
        container_venv_in_host.mkdir(exist_ok=True)
        project_mounts.append(
            (container_venv_in_host, PROJECT_DIR_IN_CONTAINER / ".venv")
        )
        excluded_project_dirs.append(container_venv_in_host.name)
    if config.get("share_uv_cache", False):
        project_mounts.append(
            (home_dir / UV_SHARE, ROOT_HOME_DIR_IN_CONTAINER / UV_SHARE)
        )
        project_mounts.append(
            (home_dir / UV_CACHE, ROOT_HOME_DIR_IN_CONTAINER / UV_CACHE)
        )

    for path in project_dir.iterdir():
        if path.name in excluded_project_dirs:
            continue
        project_mounts.append((path, PROJECT_DIR_IN_CONTAINER / path.name))

    cmd = ["podman", "run", "-it", "--rm"]
    cmd.extend(["-v", f"{project_dir}:{PROJECT_DIR_IN_CONTAINER}"])

    for local_dir, container_dir in project_mounts:
        cmd.extend(["-v", f"{local_dir}:{container_dir}"])
    cmd.extend(["-w", str(PROJECT_DIR_IN_CONTAINER)])
    cmd.append(config["container_template_name"])
    cmd.extend(cmd)
    run(cmd, check=True)


if __name__ == "__main__":
    command = sys.argv[1:]
    if not command:
        command = ["pytest", "test"]

    run_in_container(command)
