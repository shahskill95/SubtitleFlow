from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from engine import process_video, SubtitleFlowError
from srt_editor import open_srt_editor
from server import start_server, local_ip, PORT, ACCESS_TOKEN

BG = "#0A1020"
CARD = "#141E31"
CARD2 = "#1B2A42"
MINT = "#72E6CA"
TEXT = "#F4F7FC"
MUTED = "#9AAABF"
ORANGE = "#FFB784"


class SubtitleFlowApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("SubtitleFlow — Русские субтитры из видео")
        self.root.geometry("900x760")
        self.root.minsize(720, 650)
        self.root.configure(bg=BG)
        self.video_path: Path | None = None
        self.server = None
        self.busy = False
        self._style()
        self._build()
        self._start_lan_server()

    def _style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Subtitle.Horizontal.TProgressbar", troughcolor=CARD2,
                        background=MINT, bordercolor=CARD2, lightcolor=MINT, darkcolor=MINT)
        style.configure("Dark.TCombobox", fieldbackground=CARD2, background=CARD2,
                        foreground=TEXT, arrowcolor=MINT, bordercolor=CARD2)
        style.map("Dark.TCombobox", fieldbackground=[("readonly", CARD2)],
                  foreground=[("readonly", TEXT)])

    def _label(self, parent, text, size=11, color=MUTED, bold=False, **kwargs):
        return tk.Label(parent, text=text, bg=kwargs.pop("bg", parent.cget("bg")),
                        fg=color, font=("Segoe UI", size, "bold" if bold else "normal"),
                        **kwargs)

    def _card(self, parent, padx=20, pady=18):
        frame = tk.Frame(parent, bg=CARD, padx=padx, pady=pady,
                         highlightthickness=1, highlightbackground="#23334D")
        return frame

    def _build(self):
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True, padx=30, pady=24)

        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x")
        logo = tk.Label(header, text="S", bg=MINT, fg=BG, font=("Segoe UI", 22, "bold"),
                        width=3, height=1, padx=5, pady=4)
        logo.pack(side="left")
        brand = tk.Frame(header, bg=BG)
        brand.pack(side="left", padx=13)
        self._label(brand, "SUBTITLEFLOW", 14, TEXT, True).pack(anchor="w")
        self._label(brand, "VIDEO  →  RUSSIAN SRT", 9, MUTED, True).pack(anchor="w", pady=(3, 0))
        self._label(header, "PC  +  ANDROID", 9, MINT, True,
                    bg="#123739", padx=12, pady=8).pack(side="right", pady=5)

        self._label(outer, "ТВОЙ ВИДЕО-ПЕРЕВОДЧИК", 10, MINT, True).pack(anchor="w", pady=(30, 8))
        self._label(outer, "От видео — к русским\nсубтитрам.", 30, TEXT, True,
                    justify="left").pack(anchor="w")
        self._label(outer, "Whisper распознаёт речь, переводчик переводит её, а SubtitleFlow сохраняет тайм-коды в SRT.",
                    11, MUTED, False, wraplength=790, justify="left").pack(anchor="w", pady=(9, 20))

        video = self._card(outer)
        video.pack(fill="x")
        self._section(video, "01", "ВЫБОР ВИДЕО")
        self._label(video, "Выбери видео или аудио на компьютере. Файл останется на твоём ПК.", 10, MUTED,
                    wraplength=780, justify="left").pack(anchor="w", pady=(11, 13))
        row = tk.Frame(video, bg=CARD)
        row.pack(fill="x")
        self.pick_button = tk.Button(row, text="＋  Выбрать файл", command=self._pick_file,
                                     bg=CARD2, fg=TEXT, activebackground="#263B59", activeforeground=TEXT,
                                     relief="flat", bd=0, font=("Segoe UI", 10, "bold"), padx=18, pady=12,
                                     cursor="hand2")
        self.pick_button.pack(side="left")
        self.file_label = self._label(row, "Файл пока не выбран", 10, MUTED, wraplength=550, justify="left")
        self.file_label.pack(side="left", padx=14)

        options = self._card(outer)
        options.pack(fill="x", pady=(12, 0))
        self._section(options, "02", "ПАРАМЕТРЫ РАСПОЗНАВАНИЯ")
        option_row = tk.Frame(options, bg=CARD)
        option_row.pack(fill="x", pady=(14, 0))
        left = tk.Frame(option_row, bg=CARD)
        left.pack(side="left", fill="x", expand=True)
        self._label(left, "Язык оригинала", 10, MUTED, True).pack(anchor="w", pady=(0, 6))
        self.language = ttk.Combobox(left, state="readonly", style="Dark.TCombobox", width=24,
                                     values=["Автоопределение", "Английский", "Испанский", "Немецкий",
                                             "Французский", "Русский", "Итальянский", "Нидерландский"])
        self.language.current(0)
        self.language.pack(anchor="w", ipady=4)
        right = tk.Frame(option_row, bg=CARD)
        right.pack(side="left", fill="x", expand=True, padx=(25, 0))
        self._label(right, "Модель Whisper", 10, MUTED, True).pack(anchor="w", pady=(0, 6))
        self.model = ttk.Combobox(right, state="readonly", style="Dark.TCombobox", width=24,
                                  values=["base — быстрее", "small — точнее, медленнее"])
        self.model.current(0)
        self.model.pack(anchor="w", ipady=4)

        self.create_button = tk.Button(outer, text="Создать русские субтитры   →", command=self._process,
                                       bg=MINT, fg=BG, activebackground="#94F0D8", activeforeground=BG,
                                       relief="flat", bd=0, font=("Segoe UI", 12, "bold"),
                                       padx=18, pady=16, cursor="hand2")
        self.create_button.pack(fill="x", pady=(16, 10))

        status = self._card(outer, padx=16, pady=14)
        status.pack(fill="x")
        self.status_title = self._label(status, "●  Готово к работе", 10, MINT, True)
        self.status_title.pack(anchor="w")
        self.status_text = self._label(status, "Выбери файл и нажми «Создать русские субтитры».", 10, MUTED,
                                       wraplength=780, justify="left")
        self.status_text.pack(anchor="w", pady=(7, 8))
        self.progress = ttk.Progressbar(status, style="Subtitle.Horizontal.TProgressbar", maximum=100, value=0)
        self.progress.pack(fill="x")

        lan = self._card(outer)
        lan.pack(fill="x", pady=(12, 0))
        self._section(lan, "03", "ПОДКЛЮЧЕНИЕ ANDROID")
        self._label(lan, "Открой этот адрес в Chrome на Android. Выбери видео прямо на телефоне. Телефон и ПК должны быть в одной сети Wi‑Fi.",
                    10, MUTED, wraplength=780, justify="left").pack(anchor="w", pady=(10, 8))
        lanrow = tk.Frame(lan, bg=CARD)
        lanrow.pack(fill="x")
        self.ip_label = self._label(lanrow, "Определяю адрес компьютера…", 12, MINT, True)
        self.ip_label.pack(side="left")
        self.copy_button = tk.Button(lanrow, text="Копировать адрес", command=self._copy_ip,
                                     bg=CARD2, fg=TEXT, activebackground="#263B59", activeforeground=TEXT,
                                     relief="flat", bd=0, font=("Segoe UI", 9, "bold"), padx=12, pady=8,
                                     cursor="hand2")
        self.copy_button.pack(side="right")
        self._label(outer, "ОБРАБОТКА НА ТВОЁМ ПК  ·  WHISPER  ·  ГОТОВЫЙ SRT", 8,
                    "#65758E", True).pack(pady=(16, 0))

    def _section(self, parent, number, title):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x")
        tk.Label(row, text=number, bg="#123739", fg=MINT, font=("Segoe UI", 9, "bold"),
                 padx=10, pady=5).pack(side="left")
        self._label(row, title, 10, TEXT, True).pack(side="left", padx=10)

    def _start_lan_server(self):
        address = local_ip()
        self.server_address = f"http://{address}:{PORT}/?key={ACCESS_TOKEN}"
        self.ip_label.configure(text=self.server_address)
        try:
            self.server = start_server()
            self._set_status("●  Сервер для Android запущен", "ПК готов принимать видео с телефона по Wi‑Fi.", MINT)
        except OSError as exc:
            self._set_status("●  Не удалось запустить Wi‑Fi сервер", f"Порт {PORT} занят или заблокирован: {exc}", ORANGE)
            self.ip_label.configure(text="Не удалось запустить сервер")

    def _copy_ip(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.server_address)
        self._set_status("●  Адрес скопирован", "Открой полный адрес (включая key=...) в Chrome на Android.", MINT)

    def _pick_file(self):
        path = filedialog.askopenfilename(
            title="Выбери видео или аудио",
            filetypes=[("Видео и аудио", "*.mp4 *.mov *.mkv *.avi *.webm *.m4v *.mp3 *.wav *.m4a *.flac"),
                       ("Все файлы", "*.*")],
        )
        if path:
            self.video_path = Path(path)
            self.file_label.configure(text=self.video_path.name, fg=MINT)
            self._set_status("●  Файл выбран", "Нажми кнопку ниже, чтобы получить русский SRT.", MINT)

    def _set_status(self, title, message, color=MUTED):
        self.status_title.configure(text=title, fg=color)
        self.status_text.configure(text=message)

    def _progress_update(self, stage, percent, message):
        def update():
            self.progress.stop()
            if stage == "transcribing":
                self.progress.configure(mode="indeterminate")
                self.progress.start(12)
            else:
                self.progress.configure(mode="determinate", value=percent)
            self._set_status("●  Обработка", message, MINT)
        self.root.after(0, update)

    def _process(self):
        if self.busy:
            return
        if not self.video_path or not self.video_path.is_file():
            messagebox.showinfo("SubtitleFlow", "Сначала выбери видеофайл.")
            return
        self.busy = True
        self.create_button.configure(state="disabled", text="Обрабатываю видео…")
        self.pick_button.configure(state="disabled")
        self.progress.configure(mode="indeterminate")
        self.progress.start(12)
        self._set_status("●  Обработка", "Whisper распознаёт речь. На длинном видео это может занять время.", MINT)
        language_map = {
            "Автоопределение": "auto", "Английский": "en", "Испанский": "es",
            "Немецкий": "de", "Французский": "fr", "Русский": "ru",
            "Итальянский": "it", "Нидерландский": "nl",
        }
        lang = language_map.get(self.language.get(), "auto")
        model_name = "small" if self.model.get().startswith("small") else "base"
        source = self.video_path
        destination = source.with_name(source.stem + "_ru.srt")

        def worker():
            try:
                result = process_video(source, destination, model_name, lang, self._progress_update)
                self.root.after(0, lambda: self._finished(result))
            except Exception as exc:
                self.root.after(0, lambda err=str(exc): self._failed(err))
        threading.Thread(target=worker, daemon=True).start()

    def _finished(self, result):
        self.busy = False
        self.progress.stop()
        self.progress.configure(mode="determinate", value=100)
        self.create_button.configure(state="normal", text="Создать русские субтитры   →")
        self.pick_button.configure(state="normal")
        detail = f"Файл: {result['output']} · Субтитров: {result['segments']}"
        if result["translation_errors"]:
            detail += f" · Не удалось перевести строк: {result['translation_errors']} (оставлен оригинал)"
            self._set_status("●  Готово с предупреждением", detail, ORANGE)
        else:
            self._set_status("●  Готово!", detail, MINT)
        messagebox.showinfo("SubtitleFlow — готово", f"Русские субтитры созданы:\n\n{result['output']}\n\nСтрок: {result['segments']}")
        open_srt_editor(self.root, result["output"])

    def _failed(self, message):
        self.busy = False
        self.progress.stop()
        self.progress.configure(mode="determinate", value=0)
        self.create_button.configure(state="normal", text="Создать русские субтитры   →")
        self.pick_button.configure(state="normal")
        self._set_status("●  Ошибка обработки", message, ORANGE)
        messagebox.showerror("SubtitleFlow", message)


def main():
    root = tk.Tk()
    app = SubtitleFlowApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
