"""LAN endpoint used by the SubtitleFlow Android app."""
from __future__ import annotations

import json
import re
import socket
import secrets
import hmac
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote_plus, urlsplit, parse_qs

from engine import process_video, SubtitleFlowError

PORT = 8765
ACCESS_TOKEN = secrets.token_urlsafe(18)
MAX_UPLOAD_BYTES = 3 * 1024 * 1024 * 1024  # 3 GB


def local_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("192.0.2.1", 80))
        address = sock.getsockname()[0]
        sock.close()
        if not address.startswith("127."):
            return address
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = info[4][0]
            if not address.startswith("127."):
                return address
    except OSError:
        pass
    return "127.0.0.1"


def redact_log_message(message: str) -> str:
    """Redact the short-lived URL key from HTTP access-log text."""
    return re.sub(r"([?&]key=)[^&\s]+", r"\1[REDACTED]", message)


def safe_filename(value: str) -> str:
    value = Path(value.replace("\\", "/")).name
    value = re.sub(r"[^\w.() -]+", "_", value, flags=re.UNICODE).strip(" .")
    if not value:
        value = "video.mp4"
    return value[:180]


MOBILE_PAGE = r'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0A1020">
<title>SubtitleFlow — Русские субтитры</title>
<style>
:root{color-scheme:dark;--bg:#0A1020;--card:#141E31;--card2:#1B2A42;--mint:#72E6CA;--text:#F4F7FC;--muted:#9AAABF;--orange:#FFB784;--line:#263751}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 50% -10%,#173044 0%,var(--bg) 52%);color:var(--text);font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;min-height:100vh}
main{width:min(100% - 32px,540px);margin:0 auto;padding:22px 0 42px}.top{display:flex;align-items:center;gap:12px}.logo{width:46px;height:46px;border-radius:14px;background:var(--mint);color:var(--bg);display:grid;place-items:center;font-size:25px;font-weight:900}.brand{font-size:14px;font-weight:850;letter-spacing:.13em}.tag{font-size:10px;color:var(--muted);letter-spacing:.12em;margin-top:3px}.pill{margin-left:auto;border:1px solid #24534e;background:#123739;color:var(--mint);border-radius:99px;padding:8px 11px;font-size:10px;font-weight:800;white-space:nowrap}
.kicker{margin:36px 0 10px;color:var(--mint);font-weight:800;font-size:11px;letter-spacing:.14em}.hero{font-size:clamp(34px,8vw,48px);line-height:1.06;font-weight:850;letter-spacing:-.04em;margin:0}.intro{font-size:14px;line-height:1.65;color:var(--muted);margin:13px 0 22px}.card{background:linear-gradient(145deg,#17243a,var(--card));border:1px solid var(--line);border-radius:19px;padding:18px;margin-top:13px;box-shadow:0 14px 40px #0002}.section{display:flex;align-items:center;gap:10px;font-size:11px;font-weight:850;letter-spacing:.09em}.num{width:30px;height:27px;border-radius:8px;background:#123739;color:var(--mint);display:grid;place-items:center}.hint{font-size:12px;color:var(--muted);line-height:1.55;margin:11px 0 14px}
input[type=file],select{width:100%;border:1px solid #30435f;border-radius:12px;background:var(--card2);color:var(--text);padding:14px;font:inherit;font-size:13px}input[type=file]{padding:12px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.field label{display:block;font-size:11px;color:var(--muted);font-weight:700;margin:0 0 7px}.primary,.download{border:0;border-radius:14px;background:var(--mint);color:var(--bg);font:inherit;font-weight:850;font-size:14px;padding:17px;width:100%;margin-top:17px;cursor:pointer;text-align:center;text-decoration:none;display:block}.primary:disabled{opacity:.45;cursor:default}.status{display:flex;align-items:flex-start;gap:10px;color:var(--muted);font-size:12px;line-height:1.5}.dot{color:var(--mint);font-size:15px}.download{margin-top:12px;background:#1e3f42;color:var(--mint);border:1px solid #2a6a60}.notice{border:1px solid #4a4438;background:#29251f;border-radius:14px;color:#dec9aa;padding:12px;font-size:11px;line-height:1.55;margin-top:15px}.footer{text-align:center;color:#687b94;font-size:9px;letter-spacing:.1em;margin-top:23px}.hidden{display:none!important}
@media(max-width:380px){.grid{grid-template-columns:1fr}.hero{font-size:35px}}
</style>
</head>
<body><main>
<header class="top"><div class="logo">S</div><div><div class="brand">SUBTITLEFLOW</div><div class="tag">VIDEO → RUSSIAN SRT</div></div><div class="pill" id="connection">WI-FI</div></header>
<div class="kicker">ТВОЙ ВИДЕО-ПЕРЕВОДЧИК</div><h1 class="hero">От видео —<br>к русским субтитрам.</h1>
<p class="intro">Выбери ролик на телефоне. Компьютер распознает речь, переведёт её на русский и вернёт готовый файл .SRT с тайм-кодами.</p>
<section class="card"><div class="section"><span class="num">01</span> ВЫБОР ВИДЕО</div><p class="hint">Выбери видео из галереи или файлов. Оно будет отправлено на твой компьютер по Wi‑Fi.</p><input id="video" type="file" accept="video/*"></section>
<section class="card"><div class="section"><span class="num">02</span> ПАРАМЕТРЫ</div><p class="hint">Укажи язык речи или оставь автоопределение.</p><div class="grid"><div class="field"><label for="language">Язык оригинала</label><select id="language"><option value="auto">Автоопределение</option><option value="en">Английский</option><option value="es">Испанский</option><option value="de">Немецкий</option><option value="fr">Французский</option><option value="ru">Русский</option><option value="it">Итальянский</option><option value="nl">Нидерландский</option><option value="pt">Португальский</option></select></div><div class="field"><label for="model">Модель Whisper</label><select id="model"><option value="base">base — быстрее</option><option value="small">small — точнее</option></select></div></div></section>
<button class="primary" id="go" disabled>Создать русские субтитры →</button>
<section class="card"><div class="section"><span class="num">03</span> РЕЗУЛЬТАТ</div><div class="status" style="margin-top:13px"><span class="dot">●</span><span id="status">Подключись по ссылке из окна SubtitleFlow на ПК и выбери видео.</span></div><a id="download" class="download hidden" href="#">Скачать русский SRT ↓</a></section>
<div class="notice">Компьютер должен быть включён, программа SubtitleFlow — запущена, а телефон и ПК — подключены к одной доверенной Wi‑Fi сети. Для распознавания и перевода нужен интернет при загрузке модели/переводе. Не пересылай ссылку с ключом доступа другим людям.</div>
<div class="footer">ЛОКАЛЬНАЯ ОБРАБОТКА НА ПК · WHISPER · SRT</div>
</main>
<script>
const HAS_KEY=__HAS_KEY__;const key=new URLSearchParams(location.search).get('key')||'';
const fileInput=document.getElementById('video'),go=document.getElementById('go'),statusEl=document.getElementById('status'),download=document.getElementById('download'),connection=document.getElementById('connection');
if(HAS_KEY&&key){connection.textContent='ПК ПОДКЛЮЧЁН';statusEl.textContent='Компьютер подключён. Выбери видео и создай субтитры.';}else{connection.textContent='НЕТ КЛЮЧА';statusEl.textContent='Открой полный адрес из окна SubtitleFlow на компьютере — вместе с ?key=...';}
fileInput.addEventListener('change',()=>{go.disabled=!(HAS_KEY&&key&&fileInput.files.length);download.classList.add('hidden');if(fileInput.files.length)statusEl.textContent='Выбрано: '+fileInput.files[0].name;});
go.addEventListener('click',async()=>{const file=fileInput.files[0];if(!file||!key)return;go.disabled=true;download.classList.add('hidden');statusEl.textContent='Отправляю видео на компьютер и запускаю распознавание. Не закрывай страницу…';try{const response=await fetch('/transcribe',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-App-Key':key,'X-Filename':encodeURIComponent(file.name),'X-Model':document.getElementById('model').value,'X-Language':document.getElementById('language').value},body:file});if(!response.ok){const error=await response.text();throw new Error(error||('Ошибка сервера '+response.status));}const blob=await response.blob();const url=URL.createObjectURL(blob);let name=file.name.replace(/\.[^.]+$/,'')+'_ru.srt';download.href=url;download.download=name;download.textContent='Скачать '+name+' ↓';download.classList.remove('hidden');download.click();statusEl.textContent='Готово! Русские субтитры созданы. Файл скачивается в папку Загрузки.';}catch(error){statusEl.textContent='Не удалось обработать видео: '+error.message+' Проверь, что ПК включён и оба устройства в одной Wi‑Fi сети.';}finally{go.disabled=!fileInput.files.length;}});
</script></body></html>'''


class SubtitleFlowHandler(BaseHTTPRequestHandler):
    server_version = "SubtitleFlow/1.0"

    def log_message(self, fmt, *args):
        # BaseHTTPRequestHandler includes the full request path in its access log.
        # Redact the temporary token so it is not copied into terminal logs.
        message = redact_log_message(fmt % args)
        print("[SubtitleFlow] " + message)

    def _send(self, status: int, body: bytes, content_type: str = "text/plain; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path == "/health":
            body = json.dumps({"ok": True, "app": "SubtitleFlow", "version": "1.0"}).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
            return
        if parsed.path in {"", "/"}:
            supplied_key = parse_qs(parsed.query).get("key", [""])[0]
            has_key = hmac.compare_digest(supplied_key, ACCESS_TOKEN)
            page = MOBILE_PAGE.replace("__HAS_KEY__", "true" if has_key else "false")
            self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")
            return
        self._send(404, "Not found".encode("utf-8"))

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/transcribe":
            self._send(404, "Неизвестный адрес".encode("utf-8"))
            return
        supplied_key = self.headers.get("X-App-Key", "")
        if not hmac.compare_digest(supplied_key, ACCESS_TOKEN):
            self._send(403, "Неверный ключ доступа. Скопируй полный адрес из окна SubtitleFlow на ПК.".encode("utf-8"))
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0:
            self._send(400, "Пустой файл".encode("utf-8"))
            return
        if length > MAX_UPLOAD_BYTES:
            self._send(413, "Файл больше лимита 3 ГБ".encode("utf-8"))
            return

        filename = safe_filename(unquote_plus(self.headers.get("X-Filename", "video.mp4")))
        model_name = self.headers.get("X-Model", "base").lower()
        language = self.headers.get("X-Language", "auto").lower()
        allowed_languages = {"auto", "en", "es", "de", "fr", "ru", "it", "pt", "nl"}
        if language not in allowed_languages:
            language = "auto"

        suffix = Path(filename).suffix.lower()
        allowed_ext = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".mp3", ".wav", ".m4a", ".flac"}
        if suffix not in allowed_ext:
            self._send(415, "Формат файла не поддерживается".encode("utf-8"))
            return

        temp_root = Path(tempfile.gettempdir()) / "SubtitleFlow"
        temp_root.mkdir(parents=True, exist_ok=True)
        input_path = temp_root / ("upload_" + str(threading.get_ident()) + suffix)
        output_path = temp_root / ("result_" + str(threading.get_ident()) + ".srt")
        try:
            remaining = length
            with input_path.open("wb") as out:
                while remaining > 0:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise IOError("Соединение оборвалось во время загрузки.")
                    out.write(chunk)
                    remaining -= len(chunk)
            print(f"[SubtitleFlow] Получено видео: {filename} ({length // (1024 * 1024)} МБ)")
            result = process_video(input_path, output_path, model_name=model_name, language=language)
            content = output_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/x-subrip; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="subtitles_ru.srt"')
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)
            print(f"[SubtitleFlow] SRT отправлен. Строк: {result['segments']}; ошибок перевода: {result['translation_errors']}")
        except SubtitleFlowError as exc:
            self._send(500, str(exc).encode("utf-8"))
        except Exception as exc:
            self._send(500, f"Ошибка обработки: {exc}".encode("utf-8"))
        finally:
            for path in (input_path, output_path):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass


def start_server(host: str = "0.0.0.0", port: int = PORT):
    httpd = ThreadingHTTPServer((host, port), SubtitleFlowHandler)
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, name="SubtitleFlow-LAN", daemon=True)
    thread.start()
    return httpd
