"""Non-destructive 44.1 kHz Ogg Vorbis audio transcoding via FFmpeg with soundfile fallback."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Union

from .exceptions import DependencyError, TranscodingError


def resolve_ffmpeg_path(custom_path: Optional[str] = None) -> str:
    """Resolve the executable path to FFmpeg.

    Checks in order:
    1. Explicit custom_path argument.
    2. FFMPEG_PATH environment variable.
    3. System PATH via shutil.which("ffmpeg").
    4. Common Windows installation paths.

    Raises:
        DependencyError: If FFmpeg cannot be located on the system.
    """
    if custom_path and os.path.isfile(custom_path):
        return custom_path

    env_path = os.environ.get("FFMPEG_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    found = shutil.which("ffmpeg")
    if found:
        return found

    common_fallbacks = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe",
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/ProgramData/chocolatey/bin/ffmpeg.exe"),
    ]
    for fallback in common_fallbacks:
        if fallback.is_file():
            return str(fallback)

    raise DependencyError(
        "FFmpeg is not installed or was not found in your system PATH.\n"
        "Please install FFmpeg (e.g. `winget install Gyan.FFmpeg`) or set FFMPEG_PATH."
    )


def is_ffmpeg_available() -> bool:
    """Return True if FFmpeg is discovered on the system, otherwise False."""
    try:
        resolve_ffmpeg_path()
        return True
    except DependencyError:
        return False


def _transcode_via_soundfile(src: Path, dest: Path) -> Path:
    """Fallback transcoder using librosa + soundfile to write 44.1 kHz Ogg Vorbis."""
    import librosa
    import soundfile as sf

    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        y, _ = librosa.load(str(src), sr=44100, mono=False)
        if y is None or y.size == 0:
            raise TranscodingError("Decoded audio buffer is empty.")
        audio_out = y.T if y.ndim > 1 else y
        sf.write(str(dest), audio_out, 44100, format="OGG", subtype="VORBIS")
        return dest
    except Exception as exc:
        if dest.exists():
            try:
                dest.unlink()
            except OSError:
                pass
        raise TranscodingError(f"SoundFile fallback transcoding failed: {exc}") from exc


def convert_mp3_to_ogg(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    ffmpeg_bin: Optional[str] = None,
    fallback_to_soundfile: bool = False,
) -> Path:
    """Transcode a source audio file to 44.1 kHz Ogg Vorbis format without mutating the source.

    Args:
        input_path: Path to source audio file.
        output_path: Destination .ogg path. If None, created alongside input_path.
        ffmpeg_bin: Optional explicit path to ffmpeg executable.
        fallback_to_soundfile: If True, fall back to soundfile when FFmpeg is absent.

    Returns:
        Path to the transcoded .ogg file.
    """
    src = Path(input_path)
    if not src.exists():
        raise FileNotFoundError(f"Source audio file not found: {src}")

    dest = src.with_suffix(".ogg") if output_path is None else Path(output_path)

    try:
        ffmpeg_exec = resolve_ffmpeg_path(ffmpeg_bin)
    except DependencyError:
        if fallback_to_soundfile:
            return _transcode_via_soundfile(src, dest)
        raise

    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_exec,
        "-y",
        "-i", str(src),
        "-c:a", "libvorbis",
        "-q:a", "8",
        "-ar", "44100",
        "-vn",
        str(dest),
    ]

    try:
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    except Exception as exc:
        if dest.exists():
            try:
                dest.unlink()
            except OSError:
                pass
        raise TranscodingError(f"Failed to execute FFmpeg process: {exc}") from exc

    if process.returncode != 0:
        if dest.exists():
            try:
                dest.unlink()
            except OSError:
                pass
        stderr_sample = process.stderr.strip() if process.stderr else "Unknown error"
        raise TranscodingError(f"FFmpeg transcoding failed with exit code {process.returncode}:\n{stderr_sample}")

    return dest


def convert_audio_bytes_to_ogg(
    audio_bytes: Union[bytes, bytearray],
    output_path: Optional[Union[str, Path]] = None,
    source_format: str = ".mp3",
    ffmpeg_bin: Optional[str] = None,
    fallback_to_soundfile: bool = True,
) -> Path:
    """Non-destructively transcode in-memory audio bytes to a 44.1 kHz Ogg Vorbis file.

    Operates on an isolated copy of `audio_bytes`, using FFmpeg when available or
    falling back to `soundfile` (44,100 Hz Ogg Vorbis) when FFmpeg is absent.
    """
    if not isinstance(audio_bytes, (bytes, bytearray)) or len(audio_bytes) == 0:
        raise TranscodingError("Audio bytes for OGG transcoding cannot be empty.")

    isolated_copy = bytes(audio_bytes)
    ext = source_format if source_format.startswith(".") else f".{source_format}"

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as temp_in:
        temp_in.write(isolated_copy)
        temp_in_path = Path(temp_in.name)

    try:
        return convert_mp3_to_ogg(
            temp_in_path,
            output_path=output_path,
            ffmpeg_bin=ffmpeg_bin,
            fallback_to_soundfile=fallback_to_soundfile,
        )
    finally:
        if temp_in_path.exists():
            try:
                temp_in_path.unlink()
            except OSError:
                pass
