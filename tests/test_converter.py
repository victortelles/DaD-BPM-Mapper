"""Unit and integration tests for FFmpeg audio transcoding."""

import os
import shutil
import tempfile
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


@pytest.fixture
def sample_wav_file(tmp_path: Path) -> Path:
    """Generate a clean synthetic 1-second sine wave audio file for transcoding tests."""
    sr = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # 440 Hz sine tone
    signal = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    wav_path = tmp_path / "test_tone.wav"
    sf.write(str(wav_path), signal, sr, format="WAV")
    return wav_path


@pytest.fixture
def corrupt_audio_file(tmp_path: Path) -> Path:
    """Generate a completely invalid corrupt audio file."""
    corrupt_path = tmp_path / "corrupted.mp3"
    with open(corrupt_path, "wb") as f:
        f.write(b"NOT_A_VALID_AUDIO_FILE_DATA_HEADER_12345")
    return corrupt_path


def test_ffmpeg_missing_raises_dependency_error(monkeypatch, sample_wav_file: Path, tmp_path: Path):
    """Scenario: Transcoding failure due to missing FFmpeg.
    
    When FFmpeg is missing, DependencyError must be raised with instructions,
    and no orphaned temporary destination file should remain.
    """
    def mock_resolve(*args, **kwargs):
        raise DependencyError("FFmpeg is not installed or was not found in your system PATH.")

    monkeypatch.setattr("audio_analysis.converter.resolve_ffmpeg_path", mock_resolve)

    target_ogg = tmp_path / "output_should_not_exist.ogg"
    with pytest.raises(DependencyError, match="FFmpeg is not installed"):
        convert_mp3_to_ogg(sample_wav_file, output_path=target_ogg)

    assert not target_ogg.exists()


def test_transcoding_execution_error_on_corrupt_file(corrupt_audio_file: Path, tmp_path: Path):
    """Scenario: Transcoding execution error.
    
    Given a corrupted input file that causes FFmpeg to return non-zero exit code,
    TranscodingError must be raised capturing diagnostic information.
    """
    if not is_ffmpeg_available():
        pytest.skip("FFmpeg is not available in environment")

    out_ogg = tmp_path / "failed_transcode.ogg"
    with pytest.raises(TranscodingError, match="FFmpeg transcoding failed"):
        convert_mp3_to_ogg(corrupt_audio_file, output_path=out_ogg)

    # Ensure no orphaned output file exists
    assert not out_ogg.exists()


def test_successful_transcoding_to_44100_ogg(sample_wav_file: Path, tmp_path: Path):
    """Scenario: Successful audio to 44.1 kHz OGG conversion.
    
    Produces a valid .ogg Vorbis audio file at exactly 44,100 Hz sample rate.
    """
    if not is_ffmpeg_available():
        pytest.skip("FFmpeg is not available in environment")

    dest_ogg = tmp_path / "transcoded_sample.ogg"
    result_path = convert_mp3_to_ogg(sample_wav_file, output_path=dest_ogg)

    assert result_path.exists()
    assert result_path.stat().st_size > 0

    # Validate output audio properties
    info = sf.info(str(result_path))
    assert info.samplerate == 44100
    assert info.format == "OGG"


def test_convert_audio_bytes_to_ogg(sample_wav_file: Path, tmp_path: Path):
    """Verify transcoding in-memory bytes with automatic temp file cleanup."""
    if not is_ffmpeg_available():
        pytest.skip("FFmpeg is not available in environment")

    with open(sample_wav_file, "rb") as f:
        audio_bytes = f.read()

    out_ogg = tmp_path / "bytes_output.ogg"
    result = convert_audio_bytes_to_ogg(audio_bytes, output_path=out_ogg, source_format=".wav")

    assert result.exists()
    assert result.stat().st_size > 0
    info = sf.info(str(result))
    assert info.samplerate == 44100
