from __future__ import annotations

import json
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

import webview

from key_mapper_sdk.config import ConfigError, parse_config
from key_mapper_sdk.remapper import Remapper


APP_NAME = "KeyFlow Mapper"

DEFAULT_CONFIG = {
    "mappings": [
        {
            "name": "Typeless voice trigger",
            "enabled": True,
            "mode": "hold",
            "trigger": {"all": ["mouse.x1"]},
            "target": {"keys": ["alt_r"]},
        }
    ]
}


class Api:
    def __init__(self) -> None:
        self.config_path = default_config_path()
        self.remapper: Remapper | None = None
        self.remapper_thread: threading.Thread | None = None
        self.logs: list[str] = []
        self.lock = threading.RLock()

    def get_config(self) -> dict[str, Any]:
        return load_or_default(self.config_path)

    def save_config(self, config: dict[str, Any]) -> dict[str, Any]:
        try:
            parse_config(config)
        except (ConfigError, ValueError) as exc:
            return {"ok": False, "error": f"配置无效：{exc}"}

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        self._log(f"配置已保存：{self.config_path}")
        return {"ok": True}

    def start_mapping(self, config: dict[str, Any] | None = None) -> dict[str, Any]:
        config = config or self.get_config()
        saved = self.save_config(config)
        if not saved["ok"]:
            return saved

        self.stop_mapping()
        try:
            parsed = parse_config(config)
            self.remapper = Remapper(parsed, log=self._log)
            self.remapper_thread = threading.Thread(target=self.remapper.run, daemon=True)
            self.remapper_thread.start()
            self._log("映射已启动：鼠标侧键 1 -> 右 Alt。")
            return {"ok": True}
        except (ConfigError, ValueError) as exc:
            self._log(f"启动失败：{exc}")
            return {"ok": False, "error": f"启动失败：{exc}"}

    def stop_mapping(self) -> dict[str, Any]:
        with self.lock:
            if self.remapper is not None:
                self.remapper.request_stop()
                self.remapper.stop()
                self.remapper = None
                self._log("映射已停止。")
        return {"ok": True}

    def get_status(self) -> dict[str, Any]:
        with self.lock:
            running = bool(self.remapper_thread and self.remapper_thread.is_alive() and self.remapper is not None)
            return {"running": running, "log": self.logs[-40:]}

    def _log(self, message: str) -> None:
        with self.lock:
            stamp = datetime.now().strftime("%H:%M:%S")
            self.logs.append(f"[{stamp}] {message}")
            self.logs = self.logs[-80:]


def default_config_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "config" / "mappings.json"
    return Path.cwd() / "config" / "mappings.json"


def load_or_default(path: Path) -> dict[str, Any]:
    if not path.exists():
        return DEFAULT_CONFIG
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_CONFIG


def ui_entrypoint() -> str:
    if getattr(sys, "frozen", False):
        base_dir = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base_dir = Path(__file__).resolve().parent
    return str((base_dir / "ui" / "dist" / "index.html").resolve())


def main() -> int:
    api = Api()
    entrypoint = ui_entrypoint()
    if not Path(entrypoint).exists():
        raise FileNotFoundError(f"UI build not found: {entrypoint}")

    window = webview.create_window(
        APP_NAME,
        entrypoint,
        js_api=api,
        width=1380,
        height=900,
        min_size=(1120, 760),
        background_color="#eef0ea",
    )
    webview.start(gui="edgechromium", debug=False)
    api.stop_mapping()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
