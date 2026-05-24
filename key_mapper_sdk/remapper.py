from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from pynput import keyboard, mouse

from .config import AppConfig, Mapping


LogFn = Callable[[str], None]


MOUSE_BUTTONS: dict[str, mouse.Button] = {
    "mouse.left": mouse.Button.left,
    "mouse.right": mouse.Button.right,
    "mouse.middle": mouse.Button.middle,
    "mouse.x1": mouse.Button.x1,
    "mouse.x2": mouse.Button.x2,
}


KEY_ALIASES: dict[str, keyboard.Key | str] = {
    "alt": keyboard.Key.alt,
    "alt_l": keyboard.Key.alt_l,
    "alt_r": keyboard.Key.alt_r,
    "ctrl": keyboard.Key.ctrl,
    "ctrl_l": keyboard.Key.ctrl_l,
    "ctrl_r": keyboard.Key.ctrl_r,
    "shift": keyboard.Key.shift,
    "shift_l": keyboard.Key.shift_l,
    "shift_r": keyboard.Key.shift_r,
    "cmd": keyboard.Key.cmd,
    "win": keyboard.Key.cmd,
    "enter": keyboard.Key.enter,
    "esc": keyboard.Key.esc,
    "escape": keyboard.Key.esc,
    "space": keyboard.Key.space,
    "tab": keyboard.Key.tab,
    "backspace": keyboard.Key.backspace,
    "delete": keyboard.Key.delete,
    "up": keyboard.Key.up,
    "down": keyboard.Key.down,
    "left": keyboard.Key.left,
    "right": keyboard.Key.right,
    "f1": keyboard.Key.f1,
    "f2": keyboard.Key.f2,
    "f3": keyboard.Key.f3,
    "f4": keyboard.Key.f4,
    "f5": keyboard.Key.f5,
    "f6": keyboard.Key.f6,
    "f7": keyboard.Key.f7,
    "f8": keyboard.Key.f8,
    "f9": keyboard.Key.f9,
    "f10": keyboard.Key.f10,
    "f11": keyboard.Key.f11,
    "f12": keyboard.Key.f12,
}


@dataclass
class MappingRuntime:
    mapping: Mapping
    active: bool = False
    armed_for_tap: bool = True


class Remapper:
    def __init__(self, config: AppConfig, log: LogFn | None = None) -> None:
        self._keyboard_controller = keyboard.Controller()
        self._mouse_controller = mouse.Controller()
        self._pressed: set[str] = set()
        self._runtimes = [MappingRuntime(m) for m in config.mappings if m.enabled]
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._log = log or (lambda message: None)
        self._keyboard_listener: keyboard.Listener | None = None
        self._mouse_listener: mouse.Listener | None = None

    def run(self) -> None:
        self._validate_mappings()
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._mouse_listener = mouse.Listener(on_click=self._on_mouse_click)
        self._keyboard_listener.start()
        self._mouse_listener.start()

        self._log("Key Mapper SDK is running. Press Ctrl+C in this window to stop.")
        self._log("Active mappings:")
        for runtime in self._runtimes:
            trigger = " + ".join(runtime.mapping.trigger.all)
            target = " + ".join(runtime.mapping.target.keys)
            self._log(f"  - {runtime.mapping.name}: {trigger} -> {target} ({runtime.mapping.mode})")

        try:
            while not self._stop_event.is_set():
                time.sleep(0.2)
        finally:
            self.stop()

    def stop(self) -> None:
        with self._lock:
            for runtime in self._runtimes:
                if runtime.active:
                    self._release_targets(runtime.mapping)
                    runtime.active = False

        if self._keyboard_listener is not None:
            self._keyboard_listener.stop()
        if self._mouse_listener is not None:
            self._mouse_listener.stop()

    def request_stop(self) -> None:
        self._stop_event.set()

    def _on_key_press(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        token = key_to_token(key)
        if token:
            self._mark_pressed(token, True)

    def _on_key_release(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        token = key_to_token(key)
        if token:
            self._mark_pressed(token, False)

    def _on_mouse_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        token = mouse_button_to_token(button)
        if token:
            self._mark_pressed(token, pressed)

    def _mark_pressed(self, token: str, is_pressed: bool) -> None:
        with self._lock:
            if is_pressed:
                self._pressed.add(token)
            else:
                self._pressed.discard(token)
            self._evaluate_mappings()

    def _evaluate_mappings(self) -> None:
        for runtime in self._runtimes:
            mapping = runtime.mapping
            matched = all(token in self._pressed for token in mapping.trigger.all)

            if mapping.mode == "hold":
                if matched and not runtime.active:
                    self._press_targets(mapping)
                    runtime.active = True
                elif not matched and runtime.active:
                    self._release_targets(mapping)
                    runtime.active = False
                continue

            if mapping.mode == "tap":
                if matched and runtime.armed_for_tap:
                    self._tap_targets(mapping)
                    runtime.armed_for_tap = False
                elif not matched:
                    runtime.armed_for_tap = True

    def _press_targets(self, mapping: Mapping) -> None:
        for token in mapping.target.keys:
            self._keyboard_controller.press(resolve_key(token))
        self._log(f"Pressed target for {mapping.name}")

    def _release_targets(self, mapping: Mapping) -> None:
        for token in reversed(mapping.target.keys):
            self._keyboard_controller.release(resolve_key(token))
        self._log(f"Released target for {mapping.name}")

    def _tap_targets(self, mapping: Mapping) -> None:
        for token in mapping.target.keys:
            self._keyboard_controller.press(resolve_key(token))
        for token in reversed(mapping.target.keys):
            self._keyboard_controller.release(resolve_key(token))
        self._log(f"Tapped target for {mapping.name}")

    def _validate_mappings(self) -> None:
        for runtime in self._runtimes:
            for token in runtime.mapping.trigger.all:
                if not is_supported_trigger(token):
                    raise ValueError(f"Unsupported trigger token: {token}")
            for token in runtime.mapping.target.keys:
                resolve_key(token)


def is_supported_trigger(token: str) -> bool:
    return token in MOUSE_BUTTONS or token.startswith("key.") or token in KEY_ALIASES or len(token) == 1


def mouse_button_to_token(button: mouse.Button) -> str | None:
    for token, candidate in MOUSE_BUTTONS.items():
        if button == candidate:
            return token
    return None


def key_to_token(key: keyboard.Key | keyboard.KeyCode | None) -> str | None:
    if key is None:
        return None
    if isinstance(key, keyboard.KeyCode):
        return key.char.lower() if key.char else None
    for token, candidate in KEY_ALIASES.items():
        if key == candidate:
            return token
    return str(key).replace("Key.", "").lower()


def resolve_key(token: str) -> keyboard.Key | str:
    if token.startswith("key."):
        token = token[4:]
    if token in KEY_ALIASES:
        return KEY_ALIASES[token]
    if len(token) == 1:
        return token
    raise ValueError(f"Unsupported target key token: {token}")
