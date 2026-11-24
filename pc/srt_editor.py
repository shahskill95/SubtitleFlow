"""Simple built-in editor for generated SubRip (.srt) subtitle files."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from pathlib import Path


BG = "#0A1020"
CARD = "#141E31"
CARD2 = "#1B2A42"
MINT = "#72E6CA"
TEXT = "#F4F7FC"
MUTED = "#9AAABF"


class SrtEditor:
    """A lightweight Tkinter editor that preserves the SRT text and timestamps."""

    def __init__(self, parent: tk.Misc, file_path: str | Path):
        self.path = Path(file_path)
        self.window = tk.Toplevel(parent)
        self.window.title(f"SubtitleFlow — Редактор субтитров · {self.path.name}")
        self.window.geometry("900x680")
        self.window.minsize(620, 420)
        self.window.configure(bg=BG)
        self.dirty = False

        header = tk.Frame(self.window, bg=BG, padx=18, pady=14)
        header.pack(fill="x")
        tk.Label(
            header, text="РЕДАКТОР СУБТИТРОВ", bg=BG, fg=TEXT,
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w")
        tk.Label(
            header, text=self.path.name, bg=BG, fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(4, 0))

        body = tk.Frame(self.window, bg=CARD, padx=12, pady=12)
        body.pack(fill="both", expand=True, padx=18, pady=(0, 12))

        scrollbar = tk.Scrollbar(body)
        scrollbar.pack(side="right", fill="y")
        self.text = tk.Text(
            body, wrap="word", undo=True, maxundo=-1,
            bg="#101A2B", fg=TEXT, insertbackground=MINT,
            selectbackground="#28534F", relief="flat", borderwidth=0,
            font=("Consolas", 11), padx=14, pady=12,
            yscrollcommand=scrollbar.set,
        )
        self.text.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=self.text.yview)

        try:
            content = self.path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            messagebox.showerror(
                "SubtitleFlow", f"Не удалось открыть файл субтитров:\n{exc}",
                parent=self.window,
            )
            self.window.destroy()
            return

        self.text.insert("1.0", content)
        self.text.edit_modified(False)
        self.text.bind("<<Modified>>", self._on_modified)
        self.window.bind("<Control-s>", self._save_shortcut)
        self.window.protocol("WM_DELETE_WINDOW", self._close)

        footer = tk.Frame(self.window, bg=BG, padx=18, pady=(0, 16))
        footer.pack(fill="x")
        self.status = tk.Label(
            footer, text="Изменения сохраняются в исходный SRT-файл.",
            bg=BG, fg=MUTED, font=("Segoe UI", 9),
        )
        self.status.pack(side="left")
        tk.Button(
            footer, text="Закрыть", command=self._close,
            bg=CARD2, fg=TEXT, activebackground="#263B59",
            activeforeground=TEXT, relief="flat", bd=0,
            font=("Segoe UI", 10, "bold"), padx=18, pady=10,
            cursor="hand2",
        ).pack(side="right")
        tk.Button(
            footer, text="Сохранить  Ctrl+S", command=self._save,
            bg=MINT, fg=BG, activebackground="#94F0D8",
            activeforeground=BG, relief="flat", bd=0,
            font=("Segoe UI", 10, "bold"), padx=18, pady=10,
            cursor="hand2",
        ).pack(side="right", padx=(0, 9))

        self.text.focus_set()

    def _on_modified(self, _event=None):
        if self.text.edit_modified():
            self.dirty = True
            self.status.configure(text="Есть несохранённые изменения.", fg=MINT)
            self.text.edit_modified(False)

    def _save_shortcut(self, _event=None):
        self._save()
        return "break"

    def _save(self):
        content = self.text.get("1.0", "end-1c")
        if not content.strip():
            messagebox.showwarning(
                "SubtitleFlow", "Файл субтитров пуст. Сохранение отменено.",
                parent=self.window,
            )
            return

        try:
            self.path.write_text(content.rstrip() + "\n", encoding="utf-8-sig")
        except OSError as exc:
            messagebox.showerror(
                "SubtitleFlow", f"Не удалось сохранить субтитры:\n{exc}",
                parent=self.window,
            )
            return

        self.dirty = False
        self.text.edit_modified(False)
        self.status.configure(text=f"Сохранено: {self.path}", fg=MINT)

    def _close(self):
        if self.dirty:
            answer = messagebox.askyesnocancel(
                "SubtitleFlow",
                "Есть несохранённые изменения. Сохранить перед закрытием?",
                parent=self.window,
            )
            if answer is None:
                return
            if answer and not self._save():
                return
        self.window.destroy()


def open_srt_editor(parent: tk.Misc, file_path: str | Path) -> SrtEditor:
    """Open the subtitle editor for a generated SRT file."""
    return SrtEditor(parent, file_path)
