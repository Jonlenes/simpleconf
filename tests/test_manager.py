from dataclasses import dataclass
from pathlib import Path

import pytest

from simpleconf import ConfigManager, DictOverlay, DirectorySource, EnvSource
from simpleconf.errors import InterpolationError


def test_layered_directories_merge(base_dir: Path, local_dir: Path,
                                   monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOTIFIER_WEBHOOK", "https://hooks.test/special")

    manager = ConfigManager(
        sources=[
            DirectorySource(base_dir, optional=False),
            DirectorySource(local_dir, optional=False),
        ])

    cfg = manager.load()

    assert cfg.get("notifier.channel") == "slack"
    assert cfg.get("notifier.retries") == 2
    assert cfg.get("notifier.features.digest") is True
    assert cfg.get("notifier.features.attachments") is True
    assert cfg.get("notifier.features.emoji") == ":pineapple:"
    assert cfg.get("notifier.webhook") == "https://hooks.test/special"


def test_environment_overlay(monkeypatch: pytest.MonkeyPatch,
                              base_dir: Path) -> None:
    monkeypatch.setenv("APP__NOTIFIER__RETRIES", "9")
    monkeypatch.setenv("APP__NOTIFIER__FEATURES__DIGEST", "false")

    manager = ConfigManager(
        sources=[
            DirectorySource(base_dir, optional=False),
            EnvSource(prefix="APP"),
        ])

    cfg = manager.load()
    assert cfg.get("notifier.retries", coerce=int) == 9
    assert cfg.get("notifier.features.digest", coerce=bool) is False


def test_dataclass_projection(base_dir: Path) -> None:
    manager = ConfigManager([DirectorySource(base_dir, optional=False)])
    cfg = manager.load().notifier

    @dataclass
    class Notifier:
        channel: str
        retries: int

    projection = cfg.as_dataclass(Notifier)
    assert projection.channel == "email"
    assert projection.retries == 2


def test_missing_interpolation_raises(base_dir: Path) -> None:
    path = base_dir / "requires_env.yml"
    path.write_text("token: ${MISSING_VAR}", encoding="utf-8")

    manager = ConfigManager([DirectorySource(base_dir, optional=False)])
    try:
        with pytest.raises(InterpolationError):
            manager.load()
    finally:
        path.unlink()


def test_dict_overlay(monkeypatch: pytest.MonkeyPatch, base_dir: Path) -> None:
    manager = ConfigManager([
        DirectorySource(base_dir, optional=False),
        DictOverlay({"notifier": {
            "channel": "sms",
            "timeout": 10
        }}),
    ])

    cfg = manager.load()
    assert cfg.get("notifier.channel") == "sms"
    assert cfg.get("notifier.timeout") == 10
