"""Configuration: API key resolution and on-disk storage.

Resolution order (highest priority first):

1. ``KOKONNA_API_KEY`` environment variable — useful for CI / one-off calls.
2. The config file at ``$KOKONNA_CONFIG`` if set, otherwise
   ``~/.kokonna/config.json``.

The file format is a tiny JSON document:

.. code-block:: json

    {"api_key": "abc123..."}
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

CONFIG_ENV_VAR = "KOKONNA_CONFIG"
API_KEY_ENV_VAR = "KOKONNA_API_KEY"
DEFAULT_CONFIG_PATH = Path.home() / ".kokonna" / "config.json"


@dataclass(frozen=True)
class Config:
    """Resolved KoKonna CLI configuration."""

    api_key: str
    base_url: str = "https://api.galaxyguide.cn/openapi"
    timeout: float = 60.0

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)


def default_config_path() -> Path:
    """Return the on-disk config path (respecting ``$KOKONNA_CONFIG``)."""
    override = os.environ.get(CONFIG_ENV_VAR)
    return Path(override).expanduser() if override else DEFAULT_CONFIG_PATH


def load_config() -> Config:
    """Resolve the current configuration from env vars + config file.

    Returns a ``Config`` whose ``api_key`` may be empty if nothing is
    configured yet — callers should check ``has_api_key`` before use.
    """
    api_key = os.environ.get(API_KEY_ENV_VAR, "").strip()

    if not api_key:
        path = default_config_path()
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = {}
            api_key = str(data.get("api_key", "")).strip()

    return Config(api_key=api_key)


def save_api_key(api_key: str, path: Path | None = None) -> Path:
    """Persist the API key to disk. Returns the path written."""
    path = path or default_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, str] = {}
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                payload = {}
        except (OSError, json.JSONDecodeError):
            payload = {}

    payload["api_key"] = api_key
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        # Windows or filesystems that don't support chmod — non-fatal.
        pass
    return path
