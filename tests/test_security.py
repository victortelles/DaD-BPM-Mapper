"""Unit tests for binary upload security firewall and non-destructive MD5 hashing."""

import hashlib
import pytest

from audio_analysis.exceptions import AudioProcessingError, AudioSecurityError, SecurityValidationError
from audio_analysis.security import (
    ALLOWED_AUDIO_EXTENSIONS,
    MAX_AUDIO_SIZE_BYTES,
    compute_audio_md5,
    validate_audio_upload,
)


def test_allowed_extensions_and_hierarchy():
    """Verify allowed audio extension whitelist and exception inheritance hierarchy."""
    assert ALLOWED_AUDIO_EXTENSIONS == {".mp3", ".wav", ".ogg", ".flac"}
    assert MAX_AUDIO_SIZE_BYTES == 100 * 1024 * 1024
    assert issubclass(SecurityValidationError, AudioProcessingError)
    assert AudioSecurityError is SecurityValidationError


@pytest.mark.parametrize(
    "filename,payload,expected_ext",
    [
        ("track.mp3", b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\x00" * 64, "mp3"),
        ("MPEG_L3.MP3", b"\xff\xfb\x90\x64" + b"\x00" * 64, "mp3"),
        ("mpeg_v2.mp3", b"\xff\xf3\x84\x64" + b"\x00" * 64, "mp3"),
        ("mpeg_v25.mp3", b"\xff\xf2\x84\x64" + b"\x00" * 64, "mp3"),
        ("mpeg_e3.mp3", b"\xff\xe3\x84\x64" + b"\x00" * 64, "mp3"),
        ("mpeg_e2.mp3", b"\xff\xe2\x84\x64" + b"\x00" * 64, "mp3"),
        ("studio.wav", b"RIFF\x24\x08\x00\x00WAVEfmt " + b"\x00" * 64, "wav"),
        ("vorbis.OGG", b"OggS\x00\x02\x00\x00\x00\x00" + b"\x00" * 64, "ogg"),
        ("lossless.flac", b"fLaC\x00\x00\x00\x22" + b"\x00" * 64, "flac"),
    ],
)
def test_valid_audio_headers_pass_validation(filename: str, payload: bytes, expected_ext: str):
    """Scenario: Valid audio file passes security validation."""
    ext = validate_audio_upload(filename, payload)
    assert ext == expected_ext


@pytest.mark.parametrize(
    "disguised_name,malicious_payload",
    [
        ("binary.mp3", b"MZ" + b"_FAKE_EXEC_HEADER" * 4),
        ("linux_bin.wav", b"\x7fELF" + b"_FAKE_ELF_HEADER" * 4),
        ("bundle.ogg", b"PK\x03\x04" + b"_FAKE_ZIP_ARCHIVE" * 4),
        ("script.flac", b"#!/" + b"usr/bin/env sh\n"),
        ("markup.mp3", b"   <script" + b">console.log(1)</script>"),
        ("server_script.wav", b"<?" + b"php echo 1; ?>"),
        ("document.ogg", b"%PDF" + b"-1.7\n1 0 obj\n"),
    ],
)
def test_disguised_executables_and_scripts_rejected(disguised_name: str, malicious_payload: bytes):
    """Scenario: Disguised executable or script rejected immediately."""
    with pytest.raises(SecurityValidationError):
        validate_audio_upload(disguised_name, malicious_payload)


@pytest.mark.parametrize(
    "bad_filename,payload",
    [
        ("program.exe", b"ID3\x04\x00\x00\x00\x00\x00\x00"),
        ("script.py", b"OggS\x00\x02\x00\x00"),
        ("notes.txt", b"RIFF\x24\x00\x00\x00WAVE"),
        ("archive.zip", b"fLaC\x00\x00\x00\x22"),
        ("no_extension", b"ID3\x04\x00\x00\x00"),
        ("", b"ID3\x04\x00\x00\x00"),
        ("   ", b"ID3\x04\x00\x00\x00"),
        ("null\x00byte.mp3", b"ID3\x04\x00\x00\x00"),
    ],
)
def test_unsupported_extensions_rejected(bad_filename: str, payload: bytes):
    """Verify files outside the extension whitelist are rejected immediately."""
    with pytest.raises(SecurityValidationError):
        validate_audio_upload(bad_filename, payload)


@pytest.mark.parametrize(
    "mismatched_filename,payload",
    [
        ("actually_wav.mp3", b"RIFF\x24\x08\x00\x00WAVEfmt " + b"\x00" * 32),
        ("actually_ogg.wav", b"OggS\x00\x02\x00\x00" + b"\x00" * 32),
        ("actually_mp3.flac", b"ID3\x04\x00\x00\x00" + b"\x00" * 32),
        ("actually_flac.ogg", b"fLaC\x00\x00\x00\x22" + b"\x00" * 32),
        ("riff_not_wave.wav", b"RIFF\x24\x08\x00\x00AVI LIST" + b"\x00" * 32),
        ("random_garbage.mp3", b"\x00\x01\x02\x03\x04\x05\x06\x07" * 8),
    ],
)
def test_extension_and_magic_header_mismatch_rejected(mismatched_filename: str, payload: bytes):
    """Verify mismatched extension vs binary magic header is rejected."""
    with pytest.raises(SecurityValidationError):
        validate_audio_upload(mismatched_filename, payload)


def test_empty_and_oversized_payloads_rejected():
    """Scenario: Empty or oversized file rejected."""
    with pytest.raises(SecurityValidationError, match="empty"):
        validate_audio_upload("empty.mp3", b"")

    valid_ogg = b"OggS\x00\x02" + b"\x00" * 200
    with pytest.raises(SecurityValidationError, match="exceeds limit"):
        validate_audio_upload("huge.ogg", valid_ogg, max_size_bytes=100)


def test_compute_audio_md5_and_source_integrity():
    """Scenario: Source byte integrity and MD5 generation."""
    raw_source = b"fLaC\x00\x00\x00\x22_UNTOUCHED_AUDIO_STREAM_BYTES_987654321"
    snapshot = bytes(raw_source)

    digest = compute_audio_md5(raw_source)
    expected = hashlib.md5(snapshot).hexdigest()

    assert digest == expected
    assert len(digest) == 32
    assert digest == digest.lower()
    assert all(c in "0123456789abcdef" for c in digest)
    assert raw_source == snapshot

    with pytest.raises(SecurityValidationError):
        compute_audio_md5("not_bytes")  # type: ignore[arg-type]
