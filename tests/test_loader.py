from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from simpleconf import ConfigNode, load


def _write_yaml(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(payload, fh, sort_keys=False)


def _write_toml(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def test_local_overrides_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base = tmp_path / "conf" / "base"
    local = tmp_path / "conf" / "local"

    _write_yaml(
        base / "notifier.yml",
        {"smtp": {"host": "smtp.base", "port": 25, "timeout": 10}},
    )
    _write_yaml(
        local / "notifier.yml",
        {"smtp": {"host": "smtp.local"}},
    )

    config = load(layers=[base, local])

    assert isinstance(config, ConfigNode)
    assert config.notifier.smtp.host == "smtp.local"
    assert config.notifier.smtp.port == 25
    assert config.get("notifier.smtp.timeout") == 10


def test_environment_folder_is_used(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base = tmp_path / "conf" / "base"
    local = tmp_path / "conf" / "local"

    _write_yaml(base / "service.yml", {"url": "https://api.dev", "retries": 1})
    _write_yaml(local / "service.yml", {"retries": 3})
    _write_yaml(base / "prod" / "service.yml", {"url": "https://api.prod"})

    config = load(layers=[base, local], env="prod")

    assert config.service.url == "https://api.prod"
    assert config.service.retries == 3


def test_placeholders_are_expanded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    local = tmp_path / "conf" / "local"

    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.delenv("SMTP_USER", raising=False)

    _write_yaml(
        local / "notifier.yml",
        {"smtp": {"user": "${SMTP_USER:-guest}", "password": "${SMTP_PASSWORD}" }},
    )

    config = load(layers=[local])

    assert config.notifier.smtp.user == "guest"
    assert config.notifier.smtp.password == "secret"


def test_dotted_overrides(tmp_path: Path) -> None:
    base = tmp_path / "conf" / "base"
    _write_yaml(base / "trainer.yml", {"epochs": 5, "optimizer": {"lr": 0.001}})

    config = load(layers=[base], overrides={"trainer.optimizer.lr": 0.01, "trainer.name": "baseline"})

    assert config.trainer.optimizer.lr == 0.01
    assert config.trainer.name == "baseline"
    assert config.trainer.epochs == 5


def test_mixed_formats(tmp_path: Path) -> None:
    base = tmp_path / "conf" / "base"
    local = tmp_path / "conf" / "local"

    _write_yaml(base / "model.yml", {"name": "resnet", "version": 1})
    _write_toml(local / "model.toml", 'version = 2\n[metrics]\naccuracy = 0.9\n')

    config = load(layers=[base, local])

    assert config.model.name == "resnet"
    assert config.model.version == 2
    assert config.model.metrics.accuracy == 0.9

