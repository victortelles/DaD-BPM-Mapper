"""Audio transcoding utilities using FFmpeg subprocess calls."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Union

from .exceptions import DependencyError, TranscodingError


def resolve_ffmpeg_path(custom_path: Optional[str] = None) -> str:
    """Resolve the executable path to FFmpeg.
    
    Checks in the following order:
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

    # Check common fallback locations on Windows
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
        "Please install FFmpeg to enable audio conversion. You can install it via:\n"
        "  - Windows Package Manager: winget install Gyan.FFmpeg\n"
        "  - Official website: https://ffmpeg.org/download.html\n"
        "Or specify the executable path by setting the FFMPEG_PATH environment variable."
    )


def is_ffmpeg_available() -> bool:
    """Return True if FFmpeg is discovered on the system, otherwise False."""
    try:
        resolve_ffmpeg_path()
        return True
    except DependencyError:
        return False


def convert_mp3_to_ogg(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    ffmpeg_bin: Optional[str] = None,
) -> Path:
    """Transcode an audio file (e.g. MP3) to 44.1 kHz Ogg Vorbis format.
    
    Args:
        input_path: Path to source audio file.
        output_path: Path to target .ogg file. If None, created alongside input_path.
        ffmpeg_bin: Optional explicit path to ffmpeg executable.
        
    Returns:
        Path to the successfully transcoded .ogg file.
        
    Raises:
        DependencyError: If FFmpeg executable is not found.
        TranscodingError: If FFmpeg returns a non-zero exit code or fails.
        FileNotFoundError: If input_path does not exist.
    """
    src = Path(input_path)
    if not src.exists():
        raise FileNotFoundError(f"Source audio file not found: {src}")

    ffmpeg_exec = resolve_ffmpeg_path(ffmpeg_bin)

    if output_path is None:
        dest = src.with_suffix(".ogg")
    else:
        dest = Path(output_path)

    dest.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg_exec,
        "-y",               # Overwrite destination if it exists
        "-i", str(src),     # Source file
        "-c:a", "libvorbis",# Vorbis encoder
        "-q:a", "8",        # High quality VBR (~256 kbps, transparent fidelity without saturation)
        "-ar", "44100",     # 44.1 kHz sample rate to prevent encoder padding drift
        "-vn",              # Strip video / album art
        str(dest),
    ]

    try:
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except Exception as e:
        if dest.exists():
            try:
                dest.unlink()
            except OSError:
                pass
        raise TranscodingError(f"Failed to execute FFmpeg process: {e}") from e

    if process.returncode != 0:
        if dest.exists():
            try:
                dest.unlink()
            except OSError:
                pass
        stderr_sample = process.stderr.strip() if process.stderr else "Unknown error"
        raise TranscodingError(
            f"FFmpeg transcoding failed with exit code {process.returncode}:\n{stderr_sample}"
        )

    return dest


def convert_audio_bytes_to_ogg(
    audio_bytes: bytes,
    output_path: Optional[Union[str, Path]] = None,
    source_format: str = ".mp3",
    ffmpeg_bin: Optional[str] = None,
) -> Path:
    """Transcode in-memory audio bytes to a 44.1 kHz Ogg Vorbis file.
    
    Args:
        audio_bytes: Raw binary bytes of the input audio.
        output_path: Destination path for the .ogg file. If None, a temporary file is created.
        source_format: File extension to hint audio container (e.g. '.mp3').
        ffmpeg_bin: Optional explicit path to ffmpeg executable.
        
    Returns:
        Path to the output .ogg file.
        
    Raises:
        DependencyError: If FFmpeg is missing.
        TranscodingError: If conversion fails.
    """
    with tempfile.NamedTemporaryFile(suffix=source_format, delete=False) as temp_in:
        temp_in.write(audio_bytes)
        temp_in_path = Path(temp_in.name)

    try:
        return convert_mp3_to_ogg(temp_in_path, output_path=output_path, ffmpeg_bin=ffmpeg_bin)
    finally:
        if temp_in_path.exists():
            try:
                temp_in_path.unlink()
            except OSError:
                pass
