from __future__ import annotations

import json
import sys
import threading
from datetime import datetime
from pathlib import Path
from tkinter import BooleanVar, StringVar, Text, Tk, messagebox
from tkinter import ttk
from typing import Any

from key_mapper_sdk.config import ConfigError, parse_config
from key_mapper_sdk.remapper import Remapper


APP_NAME = "KeyFlow Mapper"

TRIGGER_OPTIONS = [
    ("mouse.left", "鼠标左键"),
    ("mouse.right", "鼠标右键"),
    ("mouse.middle", "滚轮中键"),
    ("mouse.x1", "侧键 1"),
    ("mouse.x2", "侧键 2"),
    ("alt", "Alt"),
    ("ctrl", "Ctrl"),
    ("shift", "Shift"),
    ("space", "Space"),
    ("tab", "Tab"),
    ("key.a", "A"),
    ("key.s", "S"),
    ("key.d", "D"),
    ("key.f", "F"),
]

TARGET_OPTIONS = [
    ("alt_r", "右 Alt"),
    ("alt_l", "左 Alt"),
    ("alt", "Alt"),
    ("ctrl", "Ctrl"),
    ("shift", "Shift"),
    ("space", "Space"),
    ("tab", "Tab"),
    ("enter", "Enter"),
    ("esc", "Esc"),
    ("key.a", "A"),
    ("key.c", "C"),
    ("key.v", "V"),
]

DEFAULT_CONFIG = {
    "mappings": [
        {
            "name": "Typeless 语音唤醒",
            "enabled": True,
            "mode": "hold",
            "trigger": {"all": ["mouse.x1"]},
            "target": {"keys": ["alt_r"]},
        }
    ]
}


class KeyFlowApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.config_path = default_config_path()
        self.mappings = load_or_default(self.config_path)["mappings"]
        self.selected_index = 0
        self.remapper: Remapper | None = None
        self.remapper_thread: threading.Thread | None = None

        self.name_var = StringVar()
        self.enabled_var = BooleanVar(value=True)
        self.mode_var = StringVar(value="hold")
        self.target_var = StringVar(value="alt_r")
        self.trigger_vars = {token: BooleanVar(value=False) for token, _label in TRIGGER_OPTIONS}

        self.root.title(APP_NAME)
        self.root.geometry("1120x720")
        self.root.minsize(980, 640)
        self.root.configure(bg="#f7f0e3")

        self._configure_style()
        self._build_ui()
        self._load_selected_mapping()
        self._refresh_preview()
        self._log("应用已打开。默认映射：鼠标侧键 1 -> 右 Alt。")

    def _configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", font=("Microsoft YaHei UI", 10), background="#f7f0e3", foreground="#102a2b")
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 24, "bold"), background="#f7f0e3")
        style.configure("Subtitle.TLabel", font=("Microsoft YaHei UI", 10), background="#f7f0e3", foreground="#2e4545")
        style.configure("Panel.TFrame", background="#fffaf1", relief="flat")
        style.configure("Accent.TButton", background="#102a2b", foreground="#fffaf1", borderwidth=0, padding=(16, 10))
        style.map("Accent.TButton", background=[("active", "#183b3b")])
        style.configure("Warm.TButton", background="#f2b35d", foreground="#102a2b", borderwidth=0, padding=(14, 9))
        style.map("Warm.TButton", background=[("active", "#e5a64e")])
        style.configure("Danger.TButton", background="#f25f4c", foreground="#fffaf1", borderwidth=0, padding=(14, 9))
        style.map("Danger.TButton", background=[("active", "#d94f3f")])

    def _build_ui(self) -> None:
        shell = ttk.Frame(self.root, padding=20)
        shell.pack(fill="both", expand=True)

        header = ttk.Frame(shell)
        header.pack(fill="x", pady=(0, 18))

        logo = ttk.Frame(header, width=54, height=54)
        logo.pack(side="left", padx=(0, 14))
        logo.pack_propagate(False)
        logo_canvas = LogoCanvas(logo)
        logo_canvas.pack(fill="both", expand=True)

        title_box = ttk.Frame(header)
        title_box.pack(side="left", fill="x", expand=True)
        ttk.Label(title_box, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            title_box,
            text="一个本地桌面按键映射 App。配置鼠标/键盘组合，并映射到右 Alt 等目标键。",
            style="Subtitle.TLabel",
        ).pack(anchor="w")

        self.status_label = ttk.Label(header, text="未运行", style="Subtitle.TLabel")
        self.status_label.pack(side="right", padx=(16, 0))

        body = ttk.Frame(shell)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.columnconfigure(2, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_mapping_list(body)
        self._build_editor(body)
        self._build_output(body)

    def _build_mapping_list(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=16)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 14))

        ttk.Label(panel, text="映射方案", font=("Microsoft YaHei UI", 14, "bold"), background="#fffaf1").pack(anchor="w")
        self.mapping_list = ttk.Treeview(panel, show="tree", height=12, selectmode="browse")
        self.mapping_list.pack(fill="both", expand=True, pady=12)
        self.mapping_list.bind("<<TreeviewSelect>>", self._on_select_mapping)

        buttons = ttk.Frame(panel, style="Panel.TFrame")
        buttons.pack(fill="x")
        ttk.Button(buttons, text="新增", command=self._add_mapping, style="Warm.TButton").pack(fill="x", pady=(0, 8))
        ttk.Button(buttons, text="删除", command=self._delete_mapping, style="Danger.TButton").pack(fill="x")
        self._refresh_mapping_list()

    def _build_editor(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=18)
        panel.grid(row=0, column=1, sticky="nsew", padx=(0, 14))

        ttk.Label(panel, text="当前映射", font=("Microsoft YaHei UI", 14, "bold"), background="#fffaf1").pack(anchor="w")

        form = ttk.Frame(panel, style="Panel.TFrame")
        form.pack(fill="x", pady=(14, 12))
        ttk.Label(form, text="名称", background="#fffaf1").grid(row=0, column=0, sticky="w")
        name_entry = ttk.Entry(form, textvariable=self.name_var)
        name_entry.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        name_entry.bind("<KeyRelease>", lambda _event: self._write_selected_from_form())
        form.columnconfigure(0, weight=1)

        enabled = ttk.Checkbutton(
            form,
            text="启用这条映射",
            variable=self.enabled_var,
            command=self._write_selected_from_form,
        )
        enabled.grid(row=2, column=0, sticky="w", pady=(12, 0))

        mode_box = ttk.LabelFrame(panel, text="映射方式", padding=12)
        mode_box.pack(fill="x", pady=(0, 12))
        ttk.Radiobutton(
            mode_box,
            text="按住映射：触发键按住时，目标键持续按住",
            variable=self.mode_var,
            value="hold",
            command=self._write_selected_from_form,
        ).pack(anchor="w")
        ttk.Radiobutton(
            mode_box,
            text="点击映射：触发组合出现时，只点按一次目标键",
            variable=self.mode_var,
            value="tap",
            command=self._write_selected_from_form,
        ).pack(anchor="w", pady=(8, 0))

        trigger_box = ttk.LabelFrame(panel, text="触发按键，可多选组合", padding=12)
        trigger_box.pack(fill="x", pady=(0, 12))
        for index, (token, label) in enumerate(TRIGGER_OPTIONS):
            checkbox = ttk.Checkbutton(
                trigger_box,
                text=f"{label}  ({token})",
                variable=self.trigger_vars[token],
                command=self._write_selected_from_form,
            )
            checkbox.grid(row=index // 2, column=index % 2, sticky="w", padx=(0, 18), pady=4)

        target_box = ttk.LabelFrame(panel, text="映射目标", padding=12)
        target_box.pack(fill="x")
        target = ttk.Combobox(
            target_box,
            textvariable=self.target_var,
            values=[f"{label} ({token})" for token, label in TARGET_OPTIONS],
            state="readonly",
        )
        target.pack(fill="x")
        target.bind("<<ComboboxSelected>>", self._on_target_selected)

        actions = ttk.Frame(panel, style="Panel.TFrame")
        actions.pack(fill="x", pady=(18, 0))
        ttk.Button(actions, text="保存配置", command=self._save_config, style="Accent.TButton").pack(side="left")
        ttk.Button(actions, text="启动映射", command=self._start_remapper, style="Warm.TButton").pack(side="left", padx=10)
        ttk.Button(actions, text="停止映射", command=self._stop_remapper, style="Danger.TButton").pack(side="left")

    def _build_output(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=18)
        panel.grid(row=0, column=2, sticky="nsew")
        panel.rowconfigure(1, weight=1)
        panel.columnconfigure(0, weight=1)

        ttk.Label(panel, text="生成配置", font=("Microsoft YaHei UI", 14, "bold"), background="#fffaf1").grid(
            row=0, column=0, sticky="w"
        )
        self.preview = Text(panel, height=20, wrap="none", bg="#102a2b", fg="#fffaf1", insertbackground="#fffaf1")
        self.preview.grid(row=1, column=0, sticky="nsew", pady=12)
        self.preview.configure(state="disabled")

        ttk.Label(panel, text="运行日志", font=("Microsoft YaHei UI", 12, "bold"), background="#fffaf1").grid(
            row=2, column=0, sticky="w"
        )
        self.log_box = Text(panel, height=8, wrap="word", bg="#f7f0e3", fg="#102a2b")
        self.log_box.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self.log_box.configure(state="disabled")

    def _refresh_mapping_list(self) -> None:
        for item in self.mapping_list.get_children():
            self.mapping_list.delete(item)
        for index, mapping in enumerate(self.mappings):
            trigger = " + ".join(mapping["trigger"]["all"])
            target = " + ".join(mapping["target"]["keys"])
            self.mapping_list.insert("", "end", iid=str(index), text=f"{mapping['name']}    {trigger} -> {target}")
        self.mapping_list.selection_set(str(self.selected_index))

    def _load_selected_mapping(self) -> None:
        mapping = self.mappings[self.selected_index]
        self.name_var.set(mapping["name"])
        self.enabled_var.set(bool(mapping.get("enabled", True)))
        self.mode_var.set(mapping.get("mode", "hold"))
        target_token = mapping.get("target", {}).get("keys", ["alt_r"])[0]
        self.target_var.set(format_target(target_token))
        selected_triggers = set(mapping.get("trigger", {}).get("all", []))
        for token, variable in self.trigger_vars.items():
            variable.set(token in selected_triggers)

    def _write_selected_from_form(self) -> None:
        triggers = [token for token, variable in self.trigger_vars.items() if variable.get()]
        if not triggers:
            triggers = ["mouse.x1"]
            self.trigger_vars["mouse.x1"].set(True)

        self.mappings[self.selected_index] = {
            "name": self.name_var.get().strip() or "未命名映射",
            "enabled": self.enabled_var.get(),
            "mode": self.mode_var.get(),
            "trigger": {"all": triggers},
            "target": {"keys": [parse_target(self.target_var.get())]},
        }
        self._refresh_mapping_list()
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        raw = {"mappings": self.mappings}
        text = json.dumps(raw, ensure_ascii=False, indent=2)
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)
        self.preview.configure(state="disabled")

    def _on_select_mapping(self, _event: object) -> None:
        selection = self.mapping_list.selection()
        if not selection:
            return
        self.selected_index = int(selection[0])
        self._load_selected_mapping()
        self._refresh_preview()

    def _on_target_selected(self, _event: object) -> None:
        self._write_selected_from_form()

    def _add_mapping(self) -> None:
        self.mappings.append(
            {
                "name": f"新映射 {len(self.mappings) + 1}",
                "enabled": True,
                "mode": "hold",
                "trigger": {"all": ["mouse.x2"]},
                "target": {"keys": ["alt_r"]},
            }
        )
        self.selected_index = len(self.mappings) - 1
        self._refresh_mapping_list()
        self._load_selected_mapping()
        self._refresh_preview()

    def _delete_mapping(self) -> None:
        if len(self.mappings) == 1:
            messagebox.showinfo(APP_NAME, "至少保留一条映射。")
            return
        del self.mappings[self.selected_index]
        self.selected_index = max(0, self.selected_index - 1)
        self._refresh_mapping_list()
        self._load_selected_mapping()
        self._refresh_preview()

    def _save_config(self) -> None:
        self._write_selected_from_form()
        try:
            parse_config({"mappings": self.mappings})
        except ConfigError as exc:
            messagebox.showerror(APP_NAME, f"配置无效：{exc}")
            return

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps({"mappings": self.mappings}, ensure_ascii=False, indent=2), encoding="utf-8")
        self._log(f"配置已保存：{self.config_path}")

    def _start_remapper(self) -> None:
        if self.remapper_thread and self.remapper_thread.is_alive():
            self._log("映射已经在运行。")
            return

        self._save_config()
        try:
            config = parse_config({"mappings": self.mappings})
            self.remapper = Remapper(config, log=self._log_from_thread)
        except (ConfigError, ValueError) as exc:
            messagebox.showerror(APP_NAME, f"启动失败：{exc}")
            return

        self.remapper_thread = threading.Thread(target=self.remapper.run, daemon=True)
        self.remapper_thread.start()
        self.status_label.configure(text="运行中")
        self._log("映射已启动。按住侧键 1 会模拟右 Alt。")

    def _stop_remapper(self) -> None:
        if self.remapper is None:
            self._log("当前没有运行中的映射。")
            return
        self.remapper.request_stop()
        self.remapper.stop()
        self.remapper = None
        self.status_label.configure(text="未运行")
        self._log("映射已停止。")

    def _log_from_thread(self, message: str) -> None:
        self.root.after(0, lambda: self._log(message))

    def _log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{stamp}] {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")


class LogoCanvas(ttk.Frame):
    def __init__(self, parent: ttk.Frame) -> None:
        super().__init__(parent)
        from tkinter import Canvas

        canvas = Canvas(self, width=54, height=54, bg="#f7f0e3", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        canvas.create_oval(4, 4, 50, 50, fill="#102a2b", outline="")
        canvas.create_line(15, 35, 27, 23, 37, 28, 43, 14, fill="#f2b35d", width=5, capstyle="round")
        canvas.create_rectangle(12, 31, 29, 43, fill="#fffaf1", outline="", width=0)
        canvas.create_oval(31, 11, 45, 26, fill="#58c7b4", outline="")


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


def parse_target(value: str) -> str:
    if "(" in value and value.endswith(")"):
        return value.rsplit("(", 1)[1][:-1]
    return value


def format_target(token: str) -> str:
    for candidate, label in TARGET_OPTIONS:
        if candidate == token:
            return f"{label} ({candidate})"
    return token


def main() -> int:
    root = Tk()
    KeyFlowApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
