from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Union

import yaml

from .core import ConfigNode, apply_overrides, deep_merge, resolve_placeholders
from .exceptions import ConfigNotFoundError

LayerLike = Union[str, Path]


class LayeredConfigLoader:
    """
    Load configuration files from multiple folders with deterministic precedence.
    """

    def __init__(
        self,
        *,
        layers: Optional[Sequence[LayerLike]] = None,
        env: Optional[str] = None,
        env_var: str = "APP_ENV",
    ) -> None:
        self.layers: Tuple[Path, ...] = tuple(
            Path(layer).resolve() for layer in (layers or (Path("conf/base"), Path("conf/local")))
        )
        self.env = env
        self.env_var = env_var

    def load(self, *, overrides: Optional[Mapping[str, object]] = None) -> ConfigNode:
        ordered_dirs = self._expand_layers()

        if not ordered_dirs:
            raise ConfigNotFoundError("No configuration folders found.")

        merged: MutableMapping[str, object] = {}
        files_loaded = 0

        for directory in ordered_dirs:
            if not directory.exists():
                continue
            for file_path in sorted(self._iter_config_files(directory)):
                payload = self._load_file(file_path)
                key_path = self._derive_key_path(directory, file_path)
                self._inject(merged, key_path, payload)
                files_loaded += 1

        if files_loaded == 0:
            raise ConfigNotFoundError(
                f"No configuration files found inside: {', '.join(map(str, ordered_dirs))}"
            )

        if overrides:
            apply_overrides(merged, overrides)

        resolved = resolve_placeholders(merged, env_lookup=os.environ)
        return ConfigNode(resolved)

    def _expand_layers(self) -> List[Path]:
        env_name = self.env or os.getenv(self.env_var)
        expanded: List[Path] = []

        for layer in self.layers:
            expanded.append(layer)
            if env_name:
                expanded.append(layer / env_name)

        return expanded

    @staticmethod
    def _iter_config_files(directory: Path) -> Iterable[Path]:
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".yml", ".yaml", ".json", ".toml"}:
                continue
            yield path

    @staticmethod
    def _load_file(path: Path) -> object:
        suffix = path.suffix.lower()
        if suffix in {".yml", ".yaml"}:
            with path.open("r", encoding="utf-8") as fh:
                return yaml.safe_load(fh) or {}
        if suffix == ".json":
            import json

            with path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        if suffix == ".toml":
            try:
                import tomllib  # type: ignore[attr-defined]
            except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
                import tomli as tomllib  # type: ignore[no-redef]

            with path.open("rb") as fh:
                return tomllib.load(fh)
        raise ValueError(f"Unsupported config file: {path}")

    @staticmethod
    def _derive_key_path(layer_root: Path, file_path: Path) -> Sequence[str]:
        relative = file_path.relative_to(layer_root)
        parts = list(relative.parts)
        if not parts:
            return ()

        *parents, filename = parts
        key_parts = list(parents)
        key_parts.append(Path(filename).stem)
        return tuple(key_parts)

    @staticmethod
    def _inject(target: MutableMapping[str, object], key_path: Sequence[str], value: object) -> None:
        if not key_path:
            if isinstance(value, Mapping):
                deep_merge(target, value)
            else:
                raise ValueError("Root-level config file must contain a mapping.")
            return

        current: MutableMapping[str, object] = target
        for part in key_path[:-1]:
            current = current.setdefault(part, {})  # type: ignore[assignment]
        leaf = key_path[-1]

        if leaf in current and isinstance(current[leaf], MutableMapping) and isinstance(value, Mapping):
            deep_merge(current[leaf], value)  # type: ignore[arg-type]
        else:
            current[leaf] = value

