"""Zero-trust binary upload firewall and non-destructive MD5 hasher for audio files."""

import hashlib
from pathlib import Path
from typing import Set, Tuple

from .exceptions import AudioSecurityError, SecurityValidationError

ALLOWED_AUDIO_EXTENSIONS: Set[str] = {".mp3", ".wav", ".ogg", ".flac"}
MAX_AUDIO_SIZE_BYTES: int = 100 * 1024 * 1024  # 100 MB

_FORBIDDEN_BINARY_SIGNATURES: Tuple[Tuple[bytes, str], ...] = (
    (b"MZ", "Windows PE executable (MZ)"),
    (b"\x7fELF", "ELF executable binary"),
    (b"PK\x03\x04", "ZIP/Archive container (PK)"),
    (b"#!/", "Shell script shebang (#!/)"),
    (b"#!", "Script shebang (#!)"),
    (b"%PDF", "PDF document (%PDF)"),
)

_FORBIDDEN_TEXT_SIGNATURES: Tuple[Tuple[bytes, str], ...] = (
    (b"<script", "HTML/JavaScript payload (<script)"),
    (b"<?php", "PHP script payload (<?php)"),
    (b"<!doctype html", "HTML document"),
    (b"<html", "HTML document"),
)

_MPEG_FRAME_SYNCS: Set[bytes] = {
    b"\xff\xfb",
    b"\xff\xf3",
    b"\xff\xf2",
    b"\xff\xe3",
    b"\xff\xe2",
}


def _check_forbidden_signatures(data: bytes) -> None:
    """Reject disguised executables, archives, and scripts prior to audio decoding."""
    for magic, label in _FORBIDDEN_BINARY_SIGNATURES:
        if data.startswith(magic):
            raise SecurityValidationError(
                f"Disguised non-audio payload rejected: detected {label} header."
            )

    leading_lower = data[:256].lstrip().lower()
    for magic, label in _FORBIDDEN_TEXT_SIGNATURES:
        if leading_lower.startswith(magic):
            raise SecurityValidationError(
                f"Disguised script or markup payload rejected: detected {label}."
            )


def _has_valid_audio_magic(ext: str, data: bytes) -> bool:
    """Verify binary magic bytes match the declared audio extension."""
    if ext == ".mp3":
        if data.startswith(b"ID3"):
            return len(data) >= 4
        if len(data) >= 2:
            if data[:2] in _MPEG_FRAME_SYNCS:
                return True
            if data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:
                return True
        return False

    if ext == ".wav":
        return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"

    if ext == ".ogg":
        return len(data) >= 4 and data.startswith(b"OggS")

    if ext == ".flac":
        return len(data) >= 4 and data.startswith(b"fLaC")

    return False


def validate_audio_upload(
    filename: str,
    data: bytes,
    max_size_bytes: int = MAX_AUDIO_SIZE_BYTES,
) -> str:
    """Validate uploaded audio filename extension, byte size, and magic-byte signature.

    Args:
        filename: Original uploaded filename including extension.
        data: Raw uploaded file bytes.
        max_size_bytes: Maximum allowed file size in bytes (defaults to 100 MB).

    Returns:
        Normalized lowercase extension without leading dot (e.g. 'mp3', 'wav', 'ogg', 'flac').

    Raises:
        SecurityValidationError: If any security or format invariant is violated.
    """
    if not filename or not isinstance(filename, str) or not filename.strip():
        raise SecurityValidationError("Uploaded filename cannot be empty.")

    if "\x00" in filename:
        raise SecurityValidationError("Uploaded filename contains illegal null byte.")

    ext = Path(filename.strip()).suffix.lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        allowed_list = ", ".join(sorted(ALLOWED_AUDIO_EXTENSIONS))
        raise SecurityValidationError(
            f"Unsupported file extension '{ext or '<none>'}'. Allowed formats: {allowed_list}."
        )

    if not isinstance(data, (bytes, bytearray)):
        raise SecurityValidationError("Uploaded audio payload must be raw bytes.")

    raw = bytes(data)
    if len(raw) == 0:
        raise SecurityValidationError("Uploaded audio file is empty (0 bytes).")

    if max_size_bytes <= 0 or len(raw) > max_size_bytes:
        raise SecurityValidationError(
            f"Uploaded file size ({len(raw)} bytes) exceeds limit of {max_size_bytes} bytes."
        )

    _check_forbidden_signatures(raw)

    if not _has_valid_audio_magic(ext, raw):
        raise SecurityValidationError(
            f"Binary header signature does not match declared '{ext}' audio format."
        )

    return ext.lstrip(".")


def compute_audio_md5(data: bytes) -> str:
    """Compute 32-character lowercase hexadecimal MD5 hash of raw audio bytes."""
    if not isinstance(data, (bytes, bytearray)):
        raise SecurityValidationError("Audio data for MD5 hashing must be bytes.")
    return hashlib.md5(bytes(data)).hexdigest()


__all__ = [
    "ALLOWED_AUDIO_EXTENSIONS",
    "MAX_AUDIO_SIZE_BYTES",
    "SecurityValidationError",
    "AudioSecurityError",
    "validate_audio_upload",
    "compute_audio_md5",
]
