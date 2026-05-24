from __future__ import annotations

import argparse
import signal
import sys
from pathlib import Path

from .config import ConfigError, load_config
from .remapper import Remapper


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="key-mapper",
        description="Map keyboard/mouse triggers to keyboard output using a JSON config.",
    )
    parser.add_argument(
        "--config",
        default=str(default_config_path()),
        help="Path to mappings.json. Defaults to ./config/mappings.json beside the app.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate config and exit.",
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        remapper = Remapper(config, log=print)
        if args.check:
            remapper._validate_mappings()
            print(f"Config OK: {args.config}")
            print(f"Enabled mappings: {sum(1 for m in config.mappings if m.enabled)}")
            return 0

        def stop(_signum: int, _frame: object) -> None:
            remapper.request_stop()

        signal.signal(signal.SIGINT, stop)
        signal.signal(signal.SIGTERM, stop)
        remapper.run()
        return 0
    except (ConfigError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


def default_config_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "config" / "mappings.json"
    return Path.cwd() / "config" / "mappings.json"
