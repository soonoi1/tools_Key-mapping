from __future__ import annotations

import sys
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
        self._windows_mouse_hook: WindowsMouseHook | None = None

    def run(self) -> None:
        self._validate_mappings()
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._keyboard_listener.start()
        if sys.platform == "win32":
            self._windows_mouse_hook = WindowsMouseHook(self._on_mouse_token, self._log)
            self._windows_mouse_hook.start()
        else:
            self._mouse_listener = mouse.Listener(on_click=self._on_mouse_click)
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
        if self._windows_mouse_hook is not None:
            self._windows_mouse_hook.stop()

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
            self._on_mouse_token(token, pressed)

    def _on_mouse_token(self, token: str, pressed: bool) -> None:
        self._log(f"Mouse {'down' if pressed else 'up'}: {token}")
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
            press_key(token, self._keyboard_controller)
        self._log(f"Pressed target for {mapping.name}")

    def _release_targets(self, mapping: Mapping) -> None:
        for token in reversed(mapping.target.keys):
            release_key(token, self._keyboard_controller)
        self._log(f"Released target for {mapping.name}")

    def _tap_targets(self, mapping: Mapping) -> None:
        for token in mapping.target.keys:
            press_key(token, self._keyboard_controller)
        for token in reversed(mapping.target.keys):
            release_key(token, self._keyboard_controller)
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


def press_key(token: str, controller: keyboard.Controller) -> None:
    if sys.platform == "win32" and send_windows_key(token, is_down=True):
        return
    controller.press(resolve_key(token))


def release_key(token: str, controller: keyboard.Controller) -> None:
    if sys.platform == "win32" and send_windows_key(token, is_down=False):
        return
    controller.release(resolve_key(token))


def send_windows_key(token: str, is_down: bool) -> bool:
    normalized = token.removeprefix("key.")
    virtual_key = WINDOWS_VIRTUAL_KEYS.get(normalized)
    scan_code = WINDOWS_SCAN_CODES.get(normalized)
    if virtual_key is None and scan_code is None:
        return False

    import ctypes
    from ctypes import wintypes

    ULONG_PTR = wintypes.WPARAM
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_EXTENDEDKEY = 0x0001
    KEYEVENTF_SCANCODE = 0x0008
    INPUT_KEYBOARD = 1

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class INPUT_UNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("union", INPUT_UNION)]

    flags = KEYEVENTF_SCANCODE if scan_code is not None else 0
    if token in EXTENDED_WINDOWS_KEYS:
        flags |= KEYEVENTF_EXTENDEDKEY
    if not is_down:
        flags |= KEYEVENTF_KEYUP

    event = INPUT(type=INPUT_KEYBOARD, union=INPUT_UNION(ki=KEYBDINPUT(virtual_key or 0, scan_code or 0, flags, 0, 0)))
    sent = ctypes.windll.user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
    return sent == 1


WINDOWS_VIRTUAL_KEYS: dict[str, int] = {
    "alt": 0x12,
    "alt_l": 0xA4,
    "alt_r": 0xA5,
    "ctrl": 0x11,
    "ctrl_l": 0xA2,
    "ctrl_r": 0xA3,
    "shift": 0x10,
    "shift_l": 0xA0,
    "shift_r": 0xA1,
    "space": 0x20,
    "tab": 0x09,
    "enter": 0x0D,
    "esc": 0x1B,
    "escape": 0x1B,
    "a": 0x41,
    "b": 0x42,
    "c": 0x43,
    "d": 0x44,
    "e": 0x45,
    "f": 0x46,
    "g": 0x47,
    "h": 0x48,
    "i": 0x49,
    "j": 0x4A,
    "k": 0x4B,
    "l": 0x4C,
    "m": 0x4D,
    "n": 0x4E,
    "o": 0x4F,
    "p": 0x50,
    "q": 0x51,
    "r": 0x52,
    "s": 0x53,
    "t": 0x54,
    "u": 0x55,
    "v": 0x56,
    "w": 0x57,
    "x": 0x58,
    "y": 0x59,
    "z": 0x5A,
}


EXTENDED_WINDOWS_KEYS = {"alt_r", "ctrl_r"}


WINDOWS_SCAN_CODES: dict[str, int] = {
    "alt": 0x38,
    "alt_l": 0x38,
    "alt_r": 0x38,
    "ctrl": 0x1D,
    "ctrl_l": 0x1D,
    "ctrl_r": 0x1D,
    "shift": 0x2A,
    "shift_l": 0x2A,
    "shift_r": 0x36,
    "space": 0x39,
    "tab": 0x0F,
    "enter": 0x1C,
    "esc": 0x01,
    "escape": 0x01,
    "a": 0x1E,
    "b": 0x30,
    "c": 0x2E,
    "d": 0x20,
    "e": 0x12,
    "f": 0x21,
    "g": 0x22,
    "h": 0x23,
    "i": 0x17,
    "j": 0x24,
    "k": 0x25,
    "l": 0x26,
    "m": 0x32,
    "n": 0x31,
    "o": 0x18,
    "p": 0x19,
    "q": 0x10,
    "r": 0x13,
    "s": 0x1F,
    "t": 0x14,
    "u": 0x16,
    "v": 0x2F,
    "w": 0x11,
    "x": 0x2D,
    "y": 0x15,
    "z": 0x2C,
}


class WindowsMouseHook:
    def __init__(self, callback: Callable[[str, bool], None], log: LogFn) -> None:
        self._callback = callback
        self._log = log
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._hook = None
        self._thread_id = 0
        self._stop_event = threading.Event()
        self._hook_proc = None

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread_id:
            import ctypes

            ctypes.windll.user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)
        if self._thread.is_alive():
            self._thread.join(timeout=1)

    def _run(self) -> None:
        import ctypes
        from ctypes import wintypes

        WH_MOUSE_LL = 14
        WM_LBUTTONDOWN = 0x0201
        WM_LBUTTONUP = 0x0202
        WM_RBUTTONDOWN = 0x0204
        WM_RBUTTONUP = 0x0205
        WM_MBUTTONDOWN = 0x0207
        WM_MBUTTONUP = 0x0208
        WM_XBUTTONDOWN = 0x020B
        WM_XBUTTONUP = 0x020C
        HC_ACTION = 0

        class POINT(ctypes.Structure):
            _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

        class MSLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [
                ("pt", POINT),
                ("mouseData", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_void_p),
            ]

        HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

        def hook_proc(n_code: int, w_param: int, l_param: int) -> int:
            if n_code == HC_ACTION:
                token = None
                pressed = w_param in {WM_LBUTTONDOWN, WM_RBUTTONDOWN, WM_MBUTTONDOWN, WM_XBUTTONDOWN}
                if w_param in {WM_LBUTTONDOWN, WM_LBUTTONUP}:
                    token = "mouse.left"
                elif w_param in {WM_RBUTTONDOWN, WM_RBUTTONUP}:
                    token = "mouse.right"
                elif w_param in {WM_MBUTTONDOWN, WM_MBUTTONUP}:
                    token = "mouse.middle"
                elif w_param in {WM_XBUTTONDOWN, WM_XBUTTONUP}:
                    info = ctypes.cast(l_param, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                    x_button = (info.mouseData >> 16) & 0xFFFF
                    token = "mouse.x1" if x_button == 1 else "mouse.x2" if x_button == 2 else None
                if token:
                    self._callback(token, pressed)
            return ctypes.windll.user32.CallNextHookEx(self._hook, n_code, w_param, l_param)

        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        self._hook_proc = HOOKPROC(hook_proc)
        module = ctypes.windll.kernel32.GetModuleHandleW(None)
        self._hook = ctypes.windll.user32.SetWindowsHookExW(WH_MOUSE_LL, self._hook_proc, module, 0)
        if not self._hook:
            self._log("Windows mouse hook failed; mouse buttons may not be captured.")
            return

        self._log("Windows low-level mouse hook is active.")
        message = wintypes.MSG()
        while not self._stop_event.is_set() and ctypes.windll.user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            ctypes.windll.user32.TranslateMessage(ctypes.byref(message))
            ctypes.windll.user32.DispatchMessageW(ctypes.byref(message))

        ctypes.windll.user32.UnhookWindowsHookEx(self._hook)
        self._hook = None
