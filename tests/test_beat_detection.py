"""Unit tests for audio analysis beat detection, signal validation, and downsampling."""

from pathlib import Path
import numpy as np
import pytest
import soundfile as sf

from audio_analysis.beat_detection import (
    check_audio_signal_level,
    detect_tempo_sections,
    downsample_waveform,
    load_audio,
)
from audio_analysis.exceptions import AudioProcessingError, InsufficientAudioSignalError


@pytest.fixture
def silent_audio_file(tmp_path: Path) -> Path:
    """Audio file with zero amplitude (below -60 dBFS)."""
    sr = 22050
    signal = np.zeros(sr * 2, dtype=np.float32)
    path = tmp_path / "silent.wav"
    sf.write(str(path), signal, sr, format="WAV")
    return path


@pytest.fixture
def metronome_audio_file(tmp_path: Path) -> Path:
    """Audio file with clicks at a constant 120 BPM tempo (2 beats per second)."""
    sr = 22050
    duration = 5.0
    signal = np.zeros(int(sr * duration), dtype=np.float32)
    # Add clicks every 0.5s (120 BPM)
    for t_click in np.arange(0.0, duration, 0.5):
        idx = int(t_click * sr)
        click_len = min(200, len(signal) - idx)
        signal[idx : idx + click_len] = 0.8 * np.hanning(click_len)

    path = tmp_path / "metronome_120bpm.wav"
    sf.write(str(path), signal, sr, format="WAV")
    return path


def test_corrupted_audio_file_raises_error(tmp_path: Path):
    """Scenario: Corrupted or unreadable audio input."""
    corrupt = tmp_path / "corrupt_file.mp3"
    with open(corrupt, "wb") as f:
        f.write(b"NOT_A_VALID_AUDIO_FILE_DATA_HEADER_12345")

    with pytest.raises(AudioProcessingError, match="Failed to decode audio data"):
        load_audio(corrupt)

    with pytest.raises(AudioProcessingError):
        detect_tempo_sections(corrupt)


def test_silent_audio_file_raises_insufficient_signal(silent_audio_file: Path):
    """Scenario: Silent or near-silent audio file (< -60 dBFS)."""
    with pytest.raises(InsufficientAudioSignalError, match="below -60.0 dBFS threshold"):
        detect_tempo_sections(silent_audio_file)


def test_constant_tempo_audio_file(metronome_audio_file: Path):
    """Scenario: Constant tempo audio file returns single section starting at 0.0s."""
    sections = detect_tempo_sections(metronome_audio_file)
    assert len(sections) == 1
    assert sections[0].startTime == 0.0
    assert sections[0].startBeat == 0.0
    # Tempo should be close to 120 BPM
    assert 110.0 <= sections[0].bpm <= 130.0


def test_waveform_downsampling():
    """Scenario: Rendering long duration audio with downsampling."""
    sr = 44100
    y = np.sin(np.linspace(0, 100, sr * 10))  # 10 seconds = 441,000 points
    times, envelope = downsample_waveform(y, sr, target_points=500)

    assert len(times) == len(envelope)
    assert len(envelope) <= 550
    assert times[0] == 0.0
    assert pytest.approx(times[-1], 0.1) == 10.0


def test_dynamic_tempo_audio_file(tmp_path: Path):
    """Scenario: Successful dynamic tempo analysis with distinct rhythmic sections."""
    sr = 22050
    duration = 16.0
    signal = np.zeros(int(sr * duration), dtype=np.float32)

    # First section 0s to 8s at 60 BPM (1 beat per second)
    for t_click in np.arange(0.0, 8.0, 1.0):
        idx = int(t_click * sr)
        signal[idx : idx + 200] = 0.9 * np.hanning(200)

    # Second section 8s to 16s at 120 BPM (2 beats per second)
    for t_click in np.arange(8.0, 16.0, 0.5):
        idx = int(t_click * sr)
        signal[idx : idx + 200] = 0.9 * np.hanning(200)

    path = tmp_path / "dynamic_tempo.wav"
    sf.write(str(path), signal, sr, format="WAV")

    sections = detect_tempo_sections(path, window_duration_seconds=6.0, min_bpm_change=15.0)
    assert len(sections) >= 2
    assert sections[0].startTime == 0.0
    assert sections[0].startBeat == 0.0
    assert sections[1].startTime > 0.0
    assert sections[1].startBeat > 0.0


def test_snap_to_nearest_transient():
    """Scenario: Snapping target timestamp magnetically to nearby acoustic transient peak."""
    from audio_analysis.beat_detection import snap_to_nearest_transient

    sr = 22050
    duration = 5.0
    signal = np.zeros(int(sr * duration), dtype=np.float32)

    # Place a transient peak at exactly 2.000s
    peak_idx = int(2.0 * sr)
    signal[peak_idx : peak_idx + 100] = 0.9 * np.hanning(100)

    # Target slightly off (1.92s and 2.08s) should snap to ~2.000s
    snapped1 = snap_to_nearest_transient(1.92, signal, sr, search_window=0.25)
    assert pytest.approx(snapped1, abs=0.015) == 2.0

    snapped2 = snap_to_nearest_transient(2.08, signal, sr, search_window=0.25)
    assert pytest.approx(snapped2, abs=0.015) == 2.0


def test_estimate_local_bpm_at_time():
    """Scenario: Estimating local BPM from a specific timestamp forward."""
    from audio_analysis.beat_detection import estimate_local_bpm_at_time

    sr = 22050
    duration = 10.0
    signal = np.zeros(int(sr * duration), dtype=np.float32)

    # Clicks at 120 BPM from 0 to 5s, then 150 BPM from 5 to 10s
    for t in np.arange(0.0, 5.0, 0.5):
        idx = int(t * sr)
        signal[idx : idx + 100] = 0.8 * np.hanning(100)

    for t in np.arange(5.0, 10.0, 0.4):
        idx = int(t * sr)
        signal[idx : idx + 100] = 0.8 * np.hanning(100)

    # Local estimate at 1.0s should be ~120 BPM
    t1, bpm1 = estimate_local_bpm_at_time(signal, sr, target_time=1.0, duration=4.0)
    assert 110.0 <= bpm1 <= 130.0

    # Local estimate at 5.5s should be ~150 BPM
    t2, bpm2 = estimate_local_bpm_at_time(signal, sr, target_time=5.5, duration=4.0)
    assert 140.0 <= bpm2 <= 160.0

