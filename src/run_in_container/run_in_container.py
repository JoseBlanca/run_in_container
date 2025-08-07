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


def _read_tool_config(pyproject_toml, config):
    with pyproject_toml.open("rb") as f:
        data = tomllib.load(f)
    toml_config = data.get("tool", {}).get(TOOL_NAME, {})
    for k, v in toml_config.items():
        config.setdefault(k, v)


def run_in_container(command, config: None | dict = None):
    project_dir = Path(__name__).parent.absolute()
    pyproject_toml = project_dir / "pyproject.toml"
    if not pyproject_toml.exists():
        raise RuntimeError("pyproject.toml not found: {pyproject_toml}")

    if config is None:
        config = {}
    _read_tool_config(pyproject_toml, config)

    excluded_project_dirs = list(EXCLUDED_PROJECT_DIRS)

    project_mounts = []

    for path_in_host, path_in_container in config.get("dir_mounts", []):
        if not Path(path_in_host).exists():
            raise RuntimeError(f"Path to mount does not exist: {path_in_host}")
        project_mounts.append((Path(path_in_host), Path(path_in_container)))

    if container_uv_dirs := config.get("container_uv_dirs", None):
        container_uv_dirs = Path(container_uv_dirs)
        container_uv_dirs.mkdir(exist_ok=True)
        excluded_project_dirs.append(container_uv_dirs.name)

        container_venv_in_host = container_uv_dirs / "venv"
        container_venv_in_host.mkdir(exist_ok=True)
        project_mounts.append(
            (container_venv_in_host, PROJECT_DIR_IN_CONTAINER / ".venv")
        )

        uv_share = container_uv_dirs / "uv_share"
        uv_share.mkdir(exist_ok=True)
        project_mounts.append(
            (uv_share, ROOT_HOME_DIR_IN_CONTAINER / ".local/share/uv")
        )
        uv_cache = container_uv_dirs / "uv_cache"
        uv_cache.mkdir(exist_ok=True)
        project_mounts.append((uv_cache, ROOT_HOME_DIR_IN_CONTAINER / ".cache/uv"))

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
    cmd.extend(command)
    run(cmd, check=True)


if __name__ == "__main__":
    command = sys.argv[1:]
    if not command:
        command = ["pytest", "test"]

    run_in_container(command)
