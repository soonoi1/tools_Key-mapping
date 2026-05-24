from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


MappingMode = Literal["hold", "tap"]


@dataclass(frozen=True)
class Trigger:
    all: tuple[str, ...]


@dataclass(frozen=True)
class Target:
    keys: tuple[str, ...]


@dataclass(frozen=True)
class Mapping:
    name: str
    enabled: bool
    mode: MappingMode
    trigger: Trigger
    target: Target


@dataclass(frozen=True)
class AppConfig:
    mappings: tuple[Mapping, ...]


class ConfigError(ValueError):
    """Raised when a mapping configuration is invalid."""


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Config file not found: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {config_path}: {exc}") from exc

    return parse_config(raw)


def parse_config(raw: dict[str, Any]) -> AppConfig:
    mappings_raw = raw.get("mappings")
    if not isinstance(mappings_raw, list):
        raise ConfigError("`mappings` must be a list.")

    mappings: list[Mapping] = []
    for index, item in enumerate(mappings_raw):
        if not isinstance(item, dict):
            raise ConfigError(f"Mapping #{index + 1} must be an object.")

        name = _read_str(item, "name", f"Mapping #{index + 1}")
        enabled = item.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ConfigError(f"`enabled` for {name!r} must be true or false.")

        mode = item.get("mode", "hold")
        if mode not in ("hold", "tap"):
            raise ConfigError(f"`mode` for {name!r} must be `hold` or `tap`.")

        trigger_raw = item.get("trigger")
        if not isinstance(trigger_raw, dict):
            raise ConfigError(f"`trigger` for {name!r} must be an object.")

        trigger_all = trigger_raw.get("all")
        if not isinstance(trigger_all, list) or not trigger_all:
            raise ConfigError(f"`trigger.all` for {name!r} must be a non-empty list.")

        target_raw = item.get("target")
        if not isinstance(target_raw, dict):
            raise ConfigError(f"`target` for {name!r} must be an object.")

        target_keys = target_raw.get("keys")
        if not isinstance(target_keys, list) or not target_keys:
            raise ConfigError(f"`target.keys` for {name!r} must be a non-empty list.")

        mappings.append(
            Mapping(
                name=name,
                enabled=enabled,
                mode=mode,
                trigger=Trigger(all=tuple(_normalize_token(v, name) for v in trigger_all)),
                target=Target(keys=tuple(_normalize_token(v, name) for v in target_keys)),
            )
        )

    return AppConfig(mappings=tuple(mappings))


def _read_str(item: dict[str, Any], key: str, fallback: str) -> str:
    value = item.get(key, fallback)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"`{key}` must be a non-empty string.")
    return value.strip()


def _normalize_token(value: Any, mapping_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"Key/button tokens for {mapping_name!r} must be non-empty strings.")
    return value.strip().lower()
