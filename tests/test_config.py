"""Tests for config resolution: env var > file > none."""

from __future__ import annotations

import json
import os
from pathlib import Path

from kokonna.config import (
    API_KEY_ENV_VAR,
    CONFIG_ENV_VAR,
    default_config_path,
    load_config,
    save_api_key,
)


def test_load_from_env(monkeypatch) -> None:
    monkeypatch.setenv(API_KEY_ENV_VAR, "env-key")
    cfg = load_config()
    assert cfg.api_key == "env-key"


def test_load_from_file(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
    monkeypatch.setenv(CONFIG_ENV_VAR, str(tmp_path / "kokonna.json"))
    (tmp_path / "kokonna.json").write_text(json.dumps({"api_key": "file-key"}))
    cfg = load_config()
    assert cfg.api_key == "file-key"


def test_env_wins_over_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv(API_KEY_ENV_VAR, "env-key")
    monkeypatch.setenv(CONFIG_ENV_VAR, str(tmp_path / "kokonna.json"))
    (tmp_path / "kokonna.json").write_text(json.dumps({"api_key": "file-key"}))
    cfg = load_config()
    assert cfg.api_key == "env-key"


def test_save_creates_dir_and_chmods(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv(CONFIG_ENV_VAR, str(tmp_path / "sub" / "cfg.json"))
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
    path = save_api_key("saved-key")
    assert path.is_file()
    assert json.loads(path.read_text()) == {"api_key": "saved-key"}
    # chmod 0o600 — best-effort, only assert on POSIX.
    if os.name == "posix":
        assert (path.stat().st_mode & 0o777) == 0o600


def test_save_merges_existing_payload(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv(CONFIG_ENV_VAR, str(tmp_path / "cfg.json"))
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps({"api_key": "old", "extra": "keep-me"}))
    save_api_key("new")
    payload = json.loads(p.read_text())
    assert payload == {"api_key": "new", "extra": "keep-me"}


def test_default_path_when_no_override(monkeypatch) -> None:
    monkeypatch.delenv(CONFIG_ENV_VAR, raising=False)
    assert default_config_path() == Path.home() / ".kokonna" / "config.json"
