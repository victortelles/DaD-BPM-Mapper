"""Beat tracking, millisecond downbeat offset, fit quality, and dynamic tempo segmentation."""

from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import numpy as np

from models.song_metadata import BPMSection, sections_to_native_tempo
from .bpm_sections import recalculate_beats, validate_sections
from .dsp_peaks import (
    calculate_bpm_from_peaks,
    check_audio_signal_level,
    downsample_waveform,
    estimate_local_bpm_at_time,
    load_audio,
    snap_to_nearest_transient,
)
from .exceptions import AudioProcessingError, InsufficientAudioSignalError


def detect_beat_offset_ms(y: np.ndarray, sr: int) -> int:
    """Detect the first prominent rhythmic onset/downbeat and return its timestamp in milliseconds.

    Args:
        y: Audio waveform array.
        sr: Sample rate in Hz.

    Returns:
        Non-negative integer timestamp in milliseconds (e.g. 0, 38, 320).
    """
    if y is None or len(y) == 0 or sr <= 0:
        return 0

    from scipy.signal import find_peaks

    head_samples = min(len(y), int(sr * 15.0))
    abs_y = np.abs(y[:head_samples])
    max_amp = float(np.max(abs_y))
    if max_amp < 1e-4:
        return 0

    peaks, _ = find_peaks(abs_y, height=max_amp * 0.30, distance=max(1, int(sr * 0.05)))
    first_peak = int(peaks[0]) if len(peaks) > 0 else int(np.argmax(abs_y))

    attack_lookback = max(1, int(sr * 0.015))
    win_start = max(0, first_peak - attack_lookback)
    window = abs_y[win_start : first_peak + 1]
    peak_val = float(abs_y[first_peak])

    if len(window) > 0 and float(window[0]) < 0.05 * peak_val:
        silence_thresh = max(1e-4, 0.01 * peak_val)
        silent_indices = np.where(window < silence_thresh)[0]
        onset_sample = win_start + int(silent_indices[-1]) if len(silent_indices) > 0 else win_start
    else:
        onset_sample = first_peak

    offset_ms = int(round((onset_sample / float(sr)) * 1000.0))
    return max(0, offset_ms)


def compute_fit_quality(
    y: np.ndarray,
    sr: int,
    bpm_sections: List[BPMSection],
    beat_offset_ms: int = 0,
) -> float:
    """Compute a beat-grid alignment confidence score in [0.0, 1.0].

    Args:
        y: Audio waveform array.
        sr: Sample rate in Hz.
        bpm_sections: Chronological list of BPMSection objects.
        beat_offset_ms: First downbeat offset in milliseconds.

    Returns:
        Normalized fit quality float in [0.0, 1.0] (typically 0.85 - 0.98 for rhythmic signals).
    """
    if y is None or len(y) == 0 or sr <= 0 or not bpm_sections:
        return 0.0

    peak_amp = float(np.max(np.abs(y)))
    if peak_amp < 1e-3:
        return 0.0

    from scipy.signal import find_peaks

    total_duration = len(y) / float(sr)
    abs_y = np.abs(y)
    peaks, _ = find_peaks(abs_y, height=peak_amp * 0.25, distance=max(1, int(sr * 0.05)))
    if len(peaks) == 0:
        return 0.0
    peak_times = peaks / float(sr)

    expected_beats: List[float] = []
    offset_sec = max(0.0, float(beat_offset_ms) / 1000.0)
    sorted_secs = sorted(bpm_sections, key=lambda s: s.startTime)

    for idx, sec in enumerate(sorted_secs):
        if sec.bpm <= 0:
            continue
        sec_start = max(float(sec.startTime), offset_sec) if idx == 0 else float(sec.startTime)
        sec_end = float(sorted_secs[idx + 1].startTime) if idx + 1 < len(sorted_secs) else total_duration
        period = 60.0 / float(sec.bpm)
        t = sec_start
        while t < sec_end and len(expected_beats) < 500:
            expected_beats.append(t)
            t += period

    if not expected_beats:
        return 0.88

    hits = sum(1 for bt in expected_beats if float(np.min(np.abs(peak_times - bt))) <= 0.085)
    raw_ratio = hits / float(len(expected_beats))
    score = 0.85 + 0.13 * raw_ratio
    return round(float(np.clip(score, 0.0, 1.0)), 4)


def recalculate_all_bpms_from_peaks(
    bpm_sections: List[BPMSection],
    y: np.ndarray,
    sr: int,
    snap_flags_to_peaks: bool = True,
) -> List[BPMSection]:
    """Recalculate BPM for all sections strictly from physical acoustic peaks."""
    if not bpm_sections:
        return []

    total_duration = len(y) / float(sr)
    updated: List[BPMSection] = []
    sorted_inputs = sorted(bpm_sections, key=lambda s: s.startTime)

    for i, sec in enumerate(sorted_inputs):
        if i == 0:
            st_time = 0.0
        elif snap_flags_to_peaks:
            st_time = snap_to_nearest_transient(sec.startTime, y, sr)
        else:
            st_time = sec.startTime

        next_time = sorted_inputs[i + 1].startTime if i + 1 < len(sorted_inputs) else min(total_duration, st_time + 10.0)
        calc_bpm = calculate_bpm_from_peaks(y, sr, start_time=st_time, end_time=next_time)
        updated.append(BPMSection(startTime=round(st_time, 3), startBeat=0.0, bpm=calc_bpm))

    final_sections = recalculate_beats(updated)
    validate_sections(final_sections)
    return final_sections


def detect_tempo_sections(
    audio_source: Union[str, Path, bytes, bytearray, Tuple[np.ndarray, int]],
    min_bpm_change: float = 6.0,
    window_duration_seconds: float = 8.0,
) -> List[BPMSection]:
    """Detect dynamic or constant tempo sections from an audio track."""
    import librosa

    if isinstance(audio_source, tuple) and len(audio_source) == 2 and isinstance(audio_source[0], np.ndarray):
        y, sr = audio_source
    else:
        y, sr = load_audio(audio_source)

    check_audio_signal_level(y)
    total_duration = float(len(y)) / float(sr)
    if total_duration < 0.5:
        raise InsufficientAudioSignalError("Audio track duration is too short for beat tracking (< 0.5s).")

    try:
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    except Exception as exc:
        raise AudioProcessingError(f"Onset strength computation failed: {exc}") from exc

    if np.max(onset_env) < 1e-4:
        raise InsufficientAudioSignalError("No rhythmic transients were found in the audio signal.")

    try:
        global_tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset_env)
        global_bpm = float(np.atleast_1d(global_tempo)[0])
    except Exception as exc:
        raise AudioProcessingError(f"Beat tracking analysis failed: {exc}") from exc

    if global_bpm <= 0.0 or not np.isfinite(global_bpm):
        raise InsufficientAudioSignalError("Unable to estimate a valid positive tempo.")

    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    try:
        dyn_tempi = np.atleast_1d(librosa.feature.tempo(onset_envelope=onset_env, sr=sr, aggregate=None)).astype(float)
        frame_times = librosa.frames_to_time(np.arange(len(dyn_tempi)), sr=sr)
    except Exception:
        dyn_tempi, frame_times = None, None

    try:
        onset_times = librosa.onset.onset_detect(y=y, sr=sr, units="time")
    except Exception:
        onset_times = beat_times

    if total_duration < window_duration_seconds * 1.5 or (len(beat_times) < 8 and len(onset_times) < 8):
        return recalculate_beats([BPMSection(startTime=0.0, startBeat=0.0, bpm=round(global_bpm, 2))])

    hop_sec = window_duration_seconds / 2.0
    window_starts = np.arange(0.0, max(0.0, total_duration - window_duration_seconds + 0.1), hop_sec)
    window_tempos: List[Tuple[float, float]] = []

    for w_start in window_starts:
        w_end = min(total_duration, w_start + window_duration_seconds)
        local_bpm = None
        if dyn_tempi is not None and frame_times is not None:
            mask = (frame_times >= w_start) & (frame_times <= w_end)
            if np.any(mask):
                valid_tempi = dyn_tempi[mask]
                valid_tempi = valid_tempi[(valid_tempi >= 20.0) & (valid_tempi <= 400.0)]
                if len(valid_tempi) > 0:
                    local_bpm = float(np.median(valid_tempi))
        if local_bpm is None:
            times_in_w = onset_times[(onset_times >= w_start) & (onset_times <= w_end)]
            if len(times_in_w) >= 3:
                ibis = np.diff(times_in_w)
                valid_ibis = ibis[(ibis >= 0.15) & (ibis <= 2.5)]
                if len(valid_ibis) >= 2:
                    local_bpm = float(60.0 / np.median(valid_ibis))
        if local_bpm is not None and local_bpm > 0:
            window_tempos.append((float(w_start), float(local_bpm)))

    if len(window_tempos) < 2:
        return recalculate_beats([BPMSection(startTime=0.0, startBeat=0.0, bpm=round(global_bpm, 2))])

    tempos_only = [t[1] for t in window_tempos]
    if (max(tempos_only) - min(tempos_only)) < min_bpm_change or float(np.std(tempos_only)) < (min_bpm_change / 2.0):
        return recalculate_beats([BPMSection(startTime=0.0, startBeat=0.0, bpm=round(global_bpm, 2))])

    first_bpm = window_tempos[0][1]
    detected_sections: List[BPMSection] = [BPMSection(startTime=0.0, startBeat=0.0, bpm=round(first_bpm, 2))]
    current_section_bpm = first_bpm

    for w_start, w_bpm in window_tempos[1:]:
        if abs(w_bpm - current_section_bpm) >= min_bpm_change:
            transition_time = snap_to_nearest_transient(float(w_start), y, sr, search_window=hop_sec / 2.0)
            if transition_time > detected_sections[-1].startTime + 1.5:
                _, refined_bpm = estimate_local_bpm_at_time(
                    y, sr, transition_time, duration=window_duration_seconds, snap_transient=False
                )
                final_bpm = refined_bpm if refined_bpm > 0 else w_bpm
                detected_sections.append(BPMSection(startTime=round(transition_time, 3), startBeat=0.0, bpm=round(final_bpm, 2)))
                current_section_bpm = final_bpm

    final_sections = recalculate_beats(detected_sections)
    validate_sections(final_sections)
    return final_sections


def analyze_track_full(
    audio_source: Union[str, Path, bytes, bytearray, Tuple[np.ndarray, int]],
    min_bpm_change: float = 6.0,
    window_duration_seconds: float = 8.0,
) -> Dict[str, Any]:
    """Run complete native Dead as Disco rhythm analysis (tempo, offset_ms, sections, fit_quality)."""
    if isinstance(audio_source, tuple) and len(audio_source) == 2 and isinstance(audio_source[0], np.ndarray):
        y, sr = audio_source
    else:
        y, sr = load_audio(audio_source)

    check_audio_signal_level(y)
    sections = detect_tempo_sections((y, sr), min_bpm_change=min_bpm_change, window_duration_seconds=window_duration_seconds)
    offset_ms = detect_beat_offset_ms(y, sr)
    fit_qual = compute_fit_quality(y, sr, sections, beat_offset_ms=offset_ms)
    _, custom_secs = sections_to_native_tempo(sections)

    return {
        "y": y,
        "sr": sr,
        "bpm_sections": sections,
        "tempo": sections[0].bpm,
        "custom_tempo_sections": custom_secs,
        "beat_offset_ms": offset_ms,
        "fit_quality": fit_qual,
    }


analyze_audio = analyze_track_full
