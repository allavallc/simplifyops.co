from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

AUDIO_SUFFIXES = {
    ".3ga",
    ".3gp",
    ".aac",
    ".amr",
    ".flac",
    ".m4a",
    ".mp3",
    ".mpeg",
    ".oga",
    ".ogg",
    ".opus",
    ".wav",
    ".webm",
    ".wma",
}

AUDIO_MIME_PREFIXES = ("audio/",)


class TranscriptionError(RuntimeError):
    pass


def looks_transcribable_file(filename: str | None = None, mime_type: str | None = None) -> bool:
    if mime_type:
        for prefix in AUDIO_MIME_PREFIXES:
            if mime_type.startswith(prefix):
                return True

    if filename:
        return Path(filename).suffix.lower() in AUDIO_SUFFIXES

    return False


def _normalize_audio_to_wav(input_path: Path, output_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-vn",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip() or "ffmpeg failed"
        raise TranscriptionError(details)


def _run_template_command(command_template: str, *, input_path: Path, output_prefix: Path, workdir: Path) -> str:
    argv = [
        part.format(
            input=str(input_path),
            output_prefix=str(output_prefix),
            output_dir=str(workdir),
            workdir=str(workdir),
        )
        for part in shlex.split(command_template)
    ]
    result = subprocess.run(argv, capture_output=True, text=True)
    transcript_file = output_prefix.with_suffix(".txt")
    if transcript_file.exists():
        transcript = transcript_file.read_text(encoding="utf-8", errors="replace").strip()
        if transcript:
            return transcript

    transcript = (result.stdout or "").strip()
    if transcript:
        return transcript

    details = (result.stderr or result.stdout or "").strip()
    if result.returncode != 0:
        raise TranscriptionError(details or "transcription command failed")

    raise TranscriptionError(details or "transcription command produced no text")


def _resolve_whisper_binary() -> str | None:
    explicit = os.environ.get("WHISPER_CPP_BIN", "").strip() or os.environ.get("VOICE_TRANSCRIPTION_BIN", "").strip()
    if explicit:
        return explicit

    for candidate in ("whisper-cli", "main", "whisper"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    return None


def _run_whisper_cpp(binary: str, model_path: str, input_path: Path, output_prefix: Path, extra_args: str = "") -> str:
    argv = [
        binary,
        "-m",
        model_path,
        "-f",
        str(input_path),
        "-otxt",
        "-of",
        str(output_prefix),
    ]
    if extra_args.strip():
        argv.extend(shlex.split(extra_args))

    result = subprocess.run(argv, capture_output=True, text=True)
    transcript_file = output_prefix.with_suffix(".txt")
    if transcript_file.exists():
        transcript = transcript_file.read_text(encoding="utf-8", errors="replace").strip()
        if transcript:
            return transcript

    transcript = (result.stdout or "").strip()
    if transcript:
        return transcript

    details = (result.stderr or result.stdout or "").strip()
    if result.returncode != 0:
        raise TranscriptionError(details or "whisper backend failed")

    raise TranscriptionError(details or "whisper backend produced no text")


def transcribe_local_audio(input_path: str | Path) -> str:
    input_path = Path(input_path)
    if not input_path.exists():
        raise TranscriptionError(f"input audio does not exist: {input_path}")

    with tempfile.TemporaryDirectory(prefix="james-transcribe-") as temp_dir:
        temp_dir = Path(temp_dir)
        wav_path = temp_dir / "input.wav"
        _normalize_audio_to_wav(input_path, wav_path)

        command_template = os.environ.get("VOICE_TRANSCRIPTION_COMMAND", "").strip()
        if command_template:
            return _run_template_command(
                command_template,
                input_path=wav_path,
                output_prefix=temp_dir / "transcript",
                workdir=temp_dir,
            )

        model_path = os.environ.get("WHISPER_MODEL_PATH", "").strip() or os.environ.get("VOICE_TRANSCRIPTION_MODEL", "").strip()
        if not model_path:
            raise TranscriptionError(
                "No local transcription backend configured. Set VOICE_TRANSCRIPTION_COMMAND or WHISPER_MODEL_PATH."
            )

        binary = _resolve_whisper_binary()
        if not binary:
            raise TranscriptionError(
                "No whisper binary found. Set WHISPER_CPP_BIN or VOICE_TRANSCRIPTION_BIN, or install whisper-cli/main."
            )

        return _run_whisper_cpp(
            binary,
            model_path,
            wav_path,
            temp_dir / "transcript",
            os.environ.get("WHISPER_EXTRA_ARGS", "").strip() or os.environ.get("VOICE_TRANSCRIPTION_EXTRA_ARGS", "").strip(),
        )
