from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.config import settings


def mongodb_access_mode() -> str:
    mode = settings.mongodb_access_mode.lower().strip()
    return mode if mode in {"repository", "mcp"} else "repository"


def use_mongodb_mcp() -> bool:
    return mongodb_access_mode() == "mcp"


def load_mongodb_mcp_config() -> dict[str, Any]:
    config_path = Path(settings.mongodb_mcp_config_path)
    if not config_path.is_absolute():
        config_path = Path(__file__).resolve().parents[3] / config_path

    with open(config_path) as f:
        config = json.load(f)

    server = config.get("mcpServers", {}).get("mongodb", {})
    env = {
        key: os.environ.get(value[2:-1], value) if isinstance(value, str) and value.startswith("${") and value.endswith("}") else value
        for key, value in server.get("env", {}).items()
    }

    return {
        "name": "mongodb",
        "command": server.get("command"),
        "args": server.get("args", []),
        "env": env,
    }
