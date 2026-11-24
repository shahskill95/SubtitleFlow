"""SubtitleFlow transcription and English-to-Russian SRT engine."""
from __future__ import annotations

import os
import shutil
import threading
import time
from pathlib import Path
from typing import Callable, Optional

# The user's FFmpeg installation path from the setup conversation.
_ffmpeg_hint = (
    Path.home() / "Downloads" / "ffmpeg-9.1-essentials_build"
    / "ffmpeg-9.1-essentials_build" / "bin"
)
if (_ffmpeg_hint / "ffmpeg.exe").exists():
    os.environ["PATH"] = str(_ffmpeg_hint) + os.pathsep + os.environ.get("PATH", "")

_ENGINE_LOCK = threading.Lock()
_MODELS = {}


class SubtitleFlowError(RuntimeError):
    pass


def _timestamp(seconds: float) -> str:
    total_ms = max(0, int(round(float(seconds) * 1000)))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def process_video(
    video_path: str | Path,
    output_path: str | Path,
    model_name: str = "base",
    language: str = "auto",
    progress: Optional[Callable[[str, int, str], None]] = None,
) -> dict:
    """Transcribe a video/audio file, translate segments to Russian, write SRT."""
    source = Path(video_path)
    destination = Path(output_path)
    if not source.is_file():
        raise SubtitleFlowError(f"Не найден исходный файл: {source}")
    if shutil.which("ffmpeg") is None:
        raise SubtitleFlowError(
            "Не найден FFmpeg. Проверь, что папка FFmpeg\\bin добавлена в PATH, "
            "и перезапусти SubtitleFlow."
        )
    if model_name not in {"tiny", "base", "small", "medium"}:
        model_name = "base"
    lang = None if language == "auto" else language

    def report(stage: str, percent: int, message: str) -> None:
        if progress:
            try:
                progress(stage, percent, message)
            except Exception:
                pass

    # The lock prevents two large Whisper jobs from competing for RAM/CPU.
    with _ENGINE_LOCK:
        report("loading", 2, "Загружаю модель Whisper…")
        try:
            import whisper
        except Exception as exc:
            raise SubtitleFlowError(
                "Не удалось загрузить Whisper. Запусти setup_windows.bat. "
                f"Подробности: {exc}"
            ) from exc

        if model_name not in _MODELS:
            try:
                _MODELS[model_name] = whisper.load_model(model_name, device="cpu")
            except Exception as exc:
                raise SubtitleFlowError(
                    f"Не удалось загрузить модель {model_name}. Проверь интернет при первом запуске. {exc}"
                ) from exc
        model = _MODELS[model_name]

        report("transcribing", 8, "Распознаю речь в видео…")
        try:
            result = model.transcribe(
                str(source),
                language=lang,
                fp16=False,
                verbose=False,
            )
        except Exception as exc:
            raise SubtitleFlowError(f"Ошибка распознавания Whisper: {exc}") from exc

        segments = result.get("segments") or []
        if not segments:
            raise SubtitleFlowError("Whisper не обнаружил речь в этом файле.")

        report("translating", 30, "Речь распознана. Перевожу на русский…")
        try:
            from deep_translator import GoogleTranslator
            translator = GoogleTranslator(source="auto", target="ru")
        except Exception as exc:
            raise SubtitleFlowError(f"Не удалось запустить переводчик: {exc}") from exc

        blocks: list[str] = []
        errors = 0
        for index, segment in enumerate(segments, start=1):
            original_text = str(segment.get("text", "")).strip()
            if not original_text:
                continue
            translated = original_text
            # Translation can fail temporarily due to network/rate limits.
            for attempt in range(2):
                try:
                    translated = translator.translate(original_text) or original_text
                    break
                except Exception:
                    if attempt == 0:
                        time.sleep(1.0)
                    else:
                        errors += 1
            start = _timestamp(segment.get("start", 0))
            end = _timestamp(segment.get("end", 0))
            blocks.append(f"{len(blocks) + 1}\n{start} --> {end}\n{translated.strip()}")
            percent = 30 + int(68 * index / max(1, len(segments)))
            report("translating", percent, f"Перевожу субтитры: {index}/{len(segments)}")
            time.sleep(0.25)

        if not blocks:
            raise SubtitleFlowError("Не получилось создать строки субтитров.")

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("\r\n\r\n".join(blocks) + "\r\n", encoding="utf-8-sig")
        report("done", 100, "Готово! Русские субтитры сохранены.")
        return {
            "output": str(destination),
            "segments": len(blocks),
            "translation_errors": errors,
            "detected_language": result.get("language", "unknown"),
        }
