"""Folders shared between the report generator and the Screen Check Suite updater."""
import os
from pathlib import Path

ROOT_ENV_VAR = "SCT_ROOT"


def resolve_root() -> Path:
    """Returns the suite root folder that holds the shared `config` folder.

    Priority: the SCT_ROOT environment variable (set by the launcher), then the current directory.
    """
    env_root = os.environ.get(ROOT_ENV_VAR)
    if env_root:
        return Path(env_root)
    return Path(".")


CONFIG_DIR = resolve_root() / "config"
