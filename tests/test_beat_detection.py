"""Unit tests for DSP peak helpers, beat detection, millisecond offset, and full track analysis."""

from pathlib import Path
import numpy as np
import pytest
import soundfile as sf

from audio_analysis.beat_detection import (
    analyze_track_full,
    calculate_bpm_from_peaks,
    check_audio_signal_level,
    compute_fit_quality,
    detect_beat_offset_ms,
    detect_tempo_sections,
    downsample_waveform,
    estimate_local_bpm_at_time,
    load_audio,
    recalculate_all_bpms_from_peaks,
    snap_to_nearest_transient,
)
from audio_analysis.dsp_peaks import (
    calculate_bpm_from_peaks as dsp_calc_bpm,
    check_audio_signal_level as dsp_check_level,
    load_audio as dsp_load_audio,
    snap_to_nearest_transient as dsp_snap,
)
from audio_analysis.exceptions import AudioProcessingError, InsufficientAudioSignalError
from models.song_metadata import BPMSection


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
    corrupt.write_bytes(b"NOT_A_VALID_AUDIO_FILE_DATA_HEADER_12345")

    with pytest.raises(AudioProcessingError, match="Failed to decode audio data"):
        load_audio(corrupt)

    with pytest.raises(AudioProcessingError):
        detect_tempo_sections(corrupt)


def test_silent_audio_file_raises_insufficient_signal(silent_audio_file: Path):
    """Scenario: Silent or near-silent audio file (< -60 dBFS)."""
    with pytest.raises(InsufficientAudioSignalError, match="below -60.0 dBFS threshold"):
        detect_tempo_sections(silent_audio_file)

    y_silent = np.zeros(4000, dtype=np.float32)
    with pytest.raises(InsufficientAudioSignalError):
        dsp_check_level(y_silent, min_dbfs=-50.0)


def test_constant_tempo_audio_file(metronome_audio_file: Path):
    """Scenario: Constant tempo audio file returns single section starting at 0.0s."""
    sections = detect_tempo_sections(metronome_audio_file)
    assert len(sections) == 1
    assert sections[0].startTime == 0.0
    assert sections[0].startBeat == 0.0
    assert 110.0 <= sections[0].bpm <= 130.0


def test_waveform_downsampling():
    """Scenario: Rendering long duration audio with downsampling."""
    sr = 44100
    y = np.sin(np.linspace(0, 100, sr * 10))
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

    for t_click in np.arange(0.0, 8.0, 1.0):
        idx = int(t_click * sr)
        signal[idx : idx + 200] = 0.9 * np.hanning(200)

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
    sr = 22050
    signal = np.zeros(int(sr * 5.0), dtype=np.float32)
    peak_idx = int(2.0 * sr)
    signal[peak_idx : peak_idx + 100] = 0.9 * np.hanning(100)

    snapped1 = snap_to_nearest_transient(1.92, signal, sr, search_window=0.25)
    assert pytest.approx(snapped1, abs=0.015) == 2.0

    snapped2 = dsp_snap(2.08, signal, sr, search_window=0.25)
    assert pytest.approx(snapped2, abs=0.015) == 2.0


def test_estimate_local_bpm_at_time():
    """Scenario: Estimating local BPM from a specific timestamp forward."""
    sr = 22050
    signal = np.zeros(int(sr * 10.0), dtype=np.float32)

    for t in np.arange(0.0, 5.0, 0.5):
        idx = int(t * sr)
        signal[idx : idx + 100] = 0.8 * np.hanning(100)

    for t in np.arange(5.0, 10.0, 0.4):
        idx = int(t * sr)
        signal[idx : idx + 100] = 0.8 * np.hanning(100)

    _, bpm1 = estimate_local_bpm_at_time(signal, sr, target_time=1.0, duration=4.0)
    assert 110.0 <= bpm1 <= 130.0

    _, bpm2 = estimate_local_bpm_at_time(signal, sr, target_time=5.5, duration=4.0)
    assert 140.0 <= bpm2 <= 160.0


def test_calculate_bpm_from_peaks():
    """Scenario: Calculating BPM strictly from acoustic peak intervals."""
    sr = 22050
    duration = 6.0
    signal = np.zeros(int(sr * duration), dtype=np.float32)
    interval = 60.0 / 130.0
    for t in np.arange(0.0, duration, interval):
        idx = int(t * sr)
        if idx < len(signal):
            length = min(100, len(signal) - idx)
            signal[idx : idx + length] = 0.9 * np.hanning(length)

    bpm = dsp_calc_bpm(signal, sr, start_time=0.0, end_time=duration)
    assert pytest.approx(bpm, abs=4.0) == 130.0
    assert 30.0 <= bpm <= 300.0


def test_recalculate_all_bpms_from_peaks():
    """Scenario: Global recalculation of all sections strictly from transient peaks."""
    sr = 22050
    signal = np.zeros(int(sr * 10.0), dtype=np.float32)

    for t in np.arange(0.0, 5.0, 0.6):
        idx = int(t * sr)
        signal[idx : idx + 100] = 0.9 * np.hanning(100)

    for t in np.arange(5.0, 10.0, 0.4):
        idx = int(t * sr)
        signal[idx : idx + 100] = 0.9 * np.hanning(100)

    rough_sections = [
        BPMSection(startTime=0.0, startBeat=0.0, bpm=120.0),
        BPMSection(startTime=4.92, startBeat=0.0, bpm=120.0),
    ]

    recalculated = recalculate_all_bpms_from_peaks(rough_sections, signal, sr)
    assert len(recalculated) == 2
    assert recalculated[0].startTime == 0.0
    assert 95.0 <= recalculated[0].bpm <= 105.0
    assert pytest.approx(recalculated[1].startTime, abs=0.02) == 5.0
    assert 145.0 <= recalculated[1].bpm <= 155.0
    assert recalculated[1].startBeat > 0.0


def test_detect_beat_offset_ms_and_fit_quality():
    """Scenario: Millisecond beatOffset detection (e.g. 38ms, 320ms) and fitQuality in [0.0, 1.0]."""
    sr = 22050
    for expected_ms in (0, 38, 320):
        signal = np.zeros(int(sr * 5.0), dtype=np.float32)
        start_sec = expected_ms / 1000.0
        for t_click in np.arange(start_sec, 5.0, 0.5):
            idx = int(round(t_click * sr))
            if idx + 150 < len(signal):
                signal[idx : idx + 150] = 0.85 * np.hanning(150)

        detected_ms = detect_beat_offset_ms(signal, sr)
        assert isinstance(detected_ms, int)
        assert detected_ms >= 0
        assert abs(detected_ms - expected_ms) <= 5

        sections = [BPMSection(startTime=0.0, startBeat=0.0, bpm=120.0)]
        fit_qual = compute_fit_quality(signal, sr, sections, beat_offset_ms=detected_ms)
        assert 0.85 <= fit_qual <= 1.0

    assert compute_fit_quality(np.zeros(2000, dtype=np.float32), sr, []) == 0.0


def test_analyze_track_full_and_non_destructive_bytes(metronome_audio_file: Path):
    """Scenario: Full track analysis returns tempo, custom_tempo_sections, beat_offset_ms, and fit_quality."""
    raw_bytes = metronome_audio_file.read_bytes()
    snapshot = bytes(raw_bytes)

    y, sr = dsp_load_audio(raw_bytes, target_sr=22050)
    assert raw_bytes == snapshot
    assert sr == 22050

    result = analyze_track_full(raw_bytes)
    assert set(result.keys()) == {
        "y", "sr", "bpm_sections", "tempo", "custom_tempo_sections", "beat_offset_ms", "fit_quality"
    }
    assert 110.0 <= result["tempo"] <= 130.0
    assert isinstance(result["custom_tempo_sections"], list)
    assert isinstance(result["beat_offset_ms"], int) and result["beat_offset_ms"] >= 0
    assert 0.85 <= result["fit_quality"] <= 1.0


def test_subdivision_regimes_and_uniform_guard():
    """Scenario: Track with 1x verse, 0.5x breakdown, and 2x drop yields multiple sections, while uniform click track yields 1."""
    sr = 22050
    duration = 24.0

    # 1. Uniform 24s click track at 120 BPM must remain a single BPMSection
    uniform_sig = np.zeros(int(sr * duration), dtype=np.float32)
    for t_click in np.arange(0.0, duration, 0.5):
        idx = int(t_click * sr)
        if idx + 200 <= len(uniform_sig):
            uniform_sig[idx : idx + 200] = 0.8 * np.hanning(200)

    uniform_sections = detect_tempo_sections((uniform_sig, sr))
    assert len(uniform_sections) == 1
    assert uniform_sections[0].startTime == 0.0
    assert 115.0 <= uniform_sections[0].bpm <= 125.0

    # 2. Dynamic subdivision track: 0-8s Verse (1x = 96 BPM), 8-16s Breakdown (0.5x = 48 BPM), 16-24s Drop (2x = 192 BPM)
    subdiv_sig = np.zeros(int(sr * duration), dtype=np.float32)
    base_period = 60.0 / 96.0  # 0.625s
    for t_click in np.arange(0.0, 8.0, base_period):
        idx = int(t_click * sr)
        if idx + 200 <= len(subdiv_sig):
            subdiv_sig[idx : idx + 200] = 0.55 * np.hanning(200)

    for t_click in np.arange(8.0, 16.0, base_period * 2.0):
        idx = int(t_click * sr)
        if idx + 200 <= len(subdiv_sig):
            subdiv_sig[idx : idx + 200] = 0.25 * np.hanning(200)

    for t_click in np.arange(16.0, 24.0, base_period * 0.5):
        idx = int(t_click * sr)
        if idx + 200 <= len(subdiv_sig):
            subdiv_sig[idx : idx + 200] = 0.95 * np.hanning(200)

    sections = detect_tempo_sections((subdiv_sig, sr))
    assert len(sections) >= 3
    assert sections[0].startTime == 0.0
    assert 90.0 <= sections[0].bpm <= 102.0
    bpms = [s.bpm for s in sections]
    assert any(44.0 <= b <= 52.0 for b in bpms)
    assert any(180.0 <= b <= 204.0 for b in bpms)

