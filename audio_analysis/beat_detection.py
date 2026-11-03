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
    normalize_bpm_octave,
    snap_to_nearest_transient,
)
from .exceptions import AudioProcessingError, InsufficientAudioSignalError


def detect_beat_offset_ms(y: np.ndarray, sr: int) -> int:
    """Detect the first prominent rhythmic onset/downbeat and return its timestamp in milliseconds."""
    if y is None or len(y) == 0 or sr <= 0:
        return 0

    from scipy.signal import find_peaks

    head_samples = min(len(y), int(sr * 8.0))
    head_y = y[:head_samples]
    abs_y = np.abs(head_y)
    max_amp = float(np.max(abs_y))
    if max_amp < 1e-4:
        return 0

    thresh = max(1e-3, max_amp * 0.08)
    peaks, _ = find_peaks(abs_y, height=thresh, distance=max(1, int(sr * 0.05)))
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
    min_bpm_change: float = 5.0,
    window_duration_seconds: float = 4.0,
) -> List[BPMSection]:
    """Detect dynamic tempo changes and rhythmic subdivision sections (0.5x / 1x / 2x) from an audio track."""
    import librosa
    from scipy.signal import find_peaks

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
        global_tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset_env, start_bpm=120.0)
        raw_tempo = float(np.atleast_1d(global_tempo)[0])
        global_bpm = normalize_bpm_octave(raw_tempo)
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

    eff_window = max(2.0, min(float(window_duration_seconds), 5.0))
    if total_duration < max(6.0, eff_window * 1.5) or (len(beat_times) < 8 and len(onset_times) < 8):
        return recalculate_beats([BPMSection(startTime=0.0, startBeat=0.0, bpm=round(global_bpm, 2))])

    hop_sec = eff_window / 2.0
    window_starts = np.arange(0.0, max(0.0, total_duration - eff_window + 0.1), hop_sec)
    global_max = float(np.max(np.abs(y)))
    window_profiles: List[Tuple[float, float, float, float, bool]] = []

    for w_start in window_starts:
        w_end = min(total_duration, float(w_start) + eff_window)
        s_idx = int(w_start * sr)
        e_idx = min(len(y), int(w_end * sr))
        w_dur = (e_idx - s_idx) / float(sr)
        if w_dur < 1.5:
            continue

        y_win = y[s_idx:e_idx]
        abs_win = np.abs(y_win)
        local_rms = float(np.sqrt(np.mean(y_win ** 2)))
        local_max = float(np.max(abs_win))

        peak_thresh = max(1e-4, global_max * 0.10, local_max * 0.22)
        peaks, _ = find_peaks(abs_win, height=peak_thresh, distance=max(1, int(sr * 0.08)))
        peak_times_win = float(w_start) + (peaks / float(sr))

        ibi_bpm = None
        clean_ibi = False
        interval_rate = None
        if len(peak_times_win) >= 3:
            ibis = np.diff(peak_times_win)
            valid_ibis = ibis[(ibis >= 0.18) & (ibis <= 2.2)]
            if len(valid_ibis) >= 2:
                med_ibi = float(np.median(valid_ibis))
                cv_ibi = float(np.std(valid_ibis) / max(1e-6, np.mean(valid_ibis)))
                ibi_bpm = normalize_bpm_octave(float(60.0 / med_ibi))
                interval_rate = float(1.0 / med_ibi)
                clean_ibi = cv_ibi <= 0.22

        dyn_bpm = None
        if dyn_tempi is not None and frame_times is not None:
            mask = (frame_times >= w_start) & (frame_times <= w_end)
            if np.any(mask):
                valid_tempi = dyn_tempi[mask]
                valid_tempi = valid_tempi[(valid_tempi >= 20.0) & (valid_tempi <= 400.0)]
                if len(valid_tempi) > 0:
                    dyn_bpm = normalize_bpm_octave(float(np.median(valid_tempi)))

        if clean_ibi and ibi_bpm is not None:
            raw_bpm = ibi_bpm
        elif dyn_bpm is not None and dyn_bpm > 0:
            raw_bpm = dyn_bpm
        else:
            raw_bpm = ibi_bpm if (ibi_bpm is not None and ibi_bpm > 0) else global_bpm

        onsets_in_w = onset_times[(onset_times >= w_start) & (onset_times <= w_end)]
        peak_rate = len(peak_times_win) / w_dur
        onset_cnt_rate = len(onsets_in_w) / w_dur if len(onsets_in_w) > 0 else peak_rate
        onset_rate = (0.6 * interval_rate + 0.4 * peak_rate) if (interval_rate is not None and clean_ibi) else (0.5 * peak_rate + 0.5 * onset_cnt_rate)

        mid_idx = s_idx + (e_idx - s_idx) // 2
        rms_1 = float(np.sqrt(np.mean(y[s_idx:mid_idx] ** 2))) if mid_idx > s_idx else local_rms
        rms_2 = float(np.sqrt(np.mean(y[mid_idx:e_idx] ** 2))) if e_idx > mid_idx else local_rms
        half_shift = abs(rms_2 - rms_1) / max(1e-6, max(rms_1, rms_2)) > 0.35
        cand_time = float(w_start) + hop_sec if (w_start > 0.0 and half_shift) else float(w_start)

        window_profiles.append((cand_time, float(raw_bpm), local_rms, float(onset_rate), clean_ibi))

    if len(window_profiles) < 2:
        return recalculate_beats([BPMSection(startTime=0.0, startBeat=0.0, bpm=round(global_bpm, 2))])

    raw_bpms = [p[1] for p in window_profiles]
    rms_vals = [p[2] for p in window_profiles]
    onset_rates = [p[3] for p in window_profiles]

    cv_rms = float(np.std(rms_vals)) / max(1e-6, float(np.mean(rms_vals)))
    cv_onset = float(np.std(onset_rates)) / max(1e-6, float(np.mean(onset_rates)))
    bpm_span = max(raw_bpms) - min(raw_bpms)
    has_dynamic_variation = (cv_rms > 0.12) or (cv_onset > 0.18)

    if bpm_span < min_bpm_change and not has_dynamic_variation:
        return recalculate_beats([BPMSection(startTime=0.0, startBeat=0.0, bpm=round(global_bpm, 2))])

    base_bpm = global_bpm
    window_tempos: List[Tuple[float, float, bool]] = []

    for cand_time, raw_bpm, local_rms, onset_rate, clean_ibi in window_profiles:
        if abs(raw_bpm - base_bpm * 0.5) <= max(4.0, base_bpm * 0.06) and base_bpm * 0.5 >= 42.0:
            eff_bpm, preserve_exact = normalize_bpm_octave(base_bpm * 0.5), True
        elif abs(raw_bpm - base_bpm * 2.0) <= max(6.0, base_bpm * 0.06) and base_bpm * 2.0 <= 205.0:
            eff_bpm, preserve_exact = normalize_bpm_octave(base_bpm * 2.0), True
        elif abs(raw_bpm - base_bpm) >= max(min_bpm_change, base_bpm * 0.10 if not clean_ibi else min_bpm_change):
            eff_bpm, preserve_exact = normalize_bpm_octave(raw_bpm), clean_ibi
        else:
            eff_bpm, preserve_exact = normalize_bpm_octave(base_bpm), True
        window_tempos.append((cand_time, eff_bpm, preserve_exact))

    eff_bpms_only = [t[1] for t in window_tempos]
    if (max(eff_bpms_only) - min(eff_bpms_only)) < min_bpm_change:
        return recalculate_beats([BPMSection(startTime=0.0, startBeat=0.0, bpm=round(global_bpm, 2))])

    first_bpm = window_tempos[0][1]
    detected_sections: List[BPMSection] = [BPMSection(startTime=0.0, startBeat=0.0, bpm=round(first_bpm, 2))]
    current_section_bpm = first_bpm

    for cand_time, w_bpm, preserve_exact in window_tempos[1:]:
        if abs(w_bpm - current_section_bpm) >= min_bpm_change:
            transition_time = snap_to_nearest_transient(
                float(cand_time), y, sr, search_window=min(1.5, hop_sec / 2.0)
            )
            if transition_time >= detected_sections[-1].startTime + 2.5:
                if preserve_exact:
                    final_bpm = w_bpm
                else:
                    _, refined_bpm = estimate_local_bpm_at_time(
                        y, sr, transition_time, duration=eff_window, snap_transient=False
                    )
                    final_bpm = refined_bpm if (refined_bpm > 0 and abs(refined_bpm - current_section_bpm) >= min_bpm_change) else w_bpm
                detected_sections.append(
                    BPMSection(startTime=round(transition_time, 3), startBeat=0.0, bpm=round(final_bpm, 2))
                )
                current_section_bpm = final_bpm

    final_sections = recalculate_beats(detected_sections)
    validate_sections(final_sections)
    return final_sections


def analyze_track_full(
    audio_source: Union[str, Path, bytes, bytearray, Tuple[np.ndarray, int]],
    min_bpm_change: float = 5.0,
    window_duration_seconds: float = 4.0,
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

