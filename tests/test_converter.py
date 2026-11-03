"""Unit and integration tests for non-destructive 44.1 kHz Ogg Vorbis audio transcoding."""

from pathlib import Path
import numpy as np
import pytest
import soundfile as sf

from audio_analysis.converter import (
    convert_audio_bytes_to_ogg,
    convert_mp3_to_ogg,
    is_ffmpeg_available,
    resolve_ffmpeg_path,
)
from audio_analysis.exceptions import DependencyError, TranscodingError
from audio_analysis.security import compute_audio_md5


@pytest.fixture
def sample_wav_file(tmp_path: Path) -> Path:
    """Generate a clean synthetic 1-second 22.05 kHz sine wave WAV file for transcoding tests."""
    sr = 22050
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    signal = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    wav_path = tmp_path / "test_tone.wav"
    sf.write(str(wav_path), signal, sr, format="WAV")
    return wav_path


@pytest.fixture
def corrupt_audio_file(tmp_path: Path) -> Path:
    """Generate a completely invalid corrupt audio file."""
    corrupt_path = tmp_path / "corrupted.mp3"
    corrupt_path.write_bytes(b"NOT_A_VALID_AUDIO_FILE_DATA_HEADER_12345")
    return corrupt_path


def test_ffmpeg_missing_raises_dependency_error(monkeypatch, sample_wav_file: Path, tmp_path: Path):
    """Scenario: Transcoding failure due to missing FFmpeg when fallback is disabled."""
    def mock_resolve(*args, **kwargs):
        raise DependencyError("FFmpeg is not installed or was not found in your system PATH.")

    monkeypatch.setattr("audio_analysis.converter.resolve_ffmpeg_path", mock_resolve)

    target_ogg = tmp_path / "output_should_not_exist.ogg"
    with pytest.raises(DependencyError, match="FFmpeg is not installed"):
        convert_mp3_to_ogg(sample_wav_file, output_path=target_ogg)

    assert not target_ogg.exists()


def test_transcoding_execution_error_on_corrupt_file(corrupt_audio_file: Path, tmp_path: Path):
    """Scenario: Transcoding execution error on corrupted payload."""
    if not is_ffmpeg_available():
        pytest.skip("FFmpeg is not available in environment")

    out_ogg = tmp_path / "failed_transcode.ogg"
    with pytest.raises(TranscodingError, match="FFmpeg transcoding failed"):
        convert_mp3_to_ogg(corrupt_audio_file, output_path=out_ogg)

    assert not out_ogg.exists()


def test_successful_transcoding_to_44100_ogg(sample_wav_file: Path, tmp_path: Path):
    """Scenario: Source audio transcoded to 44.1 kHz audio.ogg via FFmpeg."""
    if not is_ffmpeg_available():
        pytest.skip("FFmpeg is not available in environment")

    dest_ogg = tmp_path / "transcoded_sample.ogg"
    result_path = convert_mp3_to_ogg(sample_wav_file, output_path=dest_ogg)

    assert result_path.exists()
    assert result_path.stat().st_size > 0

    info = sf.info(str(result_path))
    assert info.samplerate == 44100
    assert info.format == "OGG"


def test_convert_audio_bytes_to_ogg(sample_wav_file: Path, tmp_path: Path):
    """Verify transcoding in-memory bytes with automatic temp file cleanup."""
    audio_bytes = sample_wav_file.read_bytes()
    out_ogg = tmp_path / "bytes_output.ogg"
    result = convert_audio_bytes_to_ogg(audio_bytes, output_path=out_ogg, source_format=".wav")

    assert result.exists()
    assert result.stat().st_size > 0
    info = sf.info(str(result))
    assert info.samplerate == 44100
    assert info.format == "OGG"


def test_convert_audio_bytes_to_ogg_soundfile_fallback_and_non_destructive(
    monkeypatch, sample_wav_file: Path, tmp_path: Path
):
    """Scenario: Soundfile fallback transcodes 22.05 kHz WAV bytes to 44.1 kHz OGG without mutating source bytes."""
    def mock_resolve(*args, **kwargs):
        raise DependencyError("FFmpeg missing")

    monkeypatch.setattr("audio_analysis.converter.resolve_ffmpeg_path", mock_resolve)

    raw_buffer = bytearray(sample_wav_file.read_bytes())
    md5_before = compute_audio_md5(raw_buffer)

    out_ogg = tmp_path / "fallback_audio.ogg"
    result = convert_audio_bytes_to_ogg(raw_buffer, output_path=out_ogg, source_format=".wav")

    assert compute_audio_md5(raw_buffer) == md5_before
    assert result.exists()
    assert result.read_bytes()[:4] == b"OggS"
    info = sf.info(str(result))
    assert info.samplerate == 44100
    assert info.format == "OGG"
