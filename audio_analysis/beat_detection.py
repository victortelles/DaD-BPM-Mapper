"""Beat tracking, onset detection, dynamic tempo segmentation, and waveform utilities."""

import os
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple, Union

import numpy as np

from models.song_metadata import BPMSection
from .bpm_sections import recalculate_beats, validate_sections
from .exceptions import AudioProcessingError, InsufficientAudioSignalError


def load_audio(
    audio_source: Union[str, Path, bytes, bytearray],
    sr: Optional[int] = None,
    mono: bool = True,
) -> Tuple[np.ndarray, int]:
    """Load an audio file or bytes into a numpy waveform array.
    
    Args:
        audio_source: File path or raw audio bytes.
        sr: Target sample rate. If None, preserves native sample rate.
        mono: If True, convert multi-channel audio to mono.
        
    Returns:
        Tuple of (y: np.ndarray audio time series, sr: int sample rate).
        
    Raises:
        AudioProcessingError: If loading, decoding, or reading audio fails.
    """
    import librosa

    temp_path: Optional[Path] = None
    try:
        if isinstance(audio_source, (bytes, bytearray)):
            with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as tf:
                tf.write(bytes(audio_source))
                temp_path = Path(tf.name)
            file_to_load = str(temp_path)
        elif isinstance(audio_source, (str, Path)):
            file_to_load = str(audio_source)
            if not Path(file_to_load).exists():
                raise AudioProcessingError(f"Audio file not found: {file_to_load}")
        else:
            raise AudioProcessingError(f"Unsupported audio source type: {type(audio_source)}")

        try:
            y, sample_rate = librosa.load(file_to_load, sr=sr, mono=mono)
        except Exception as e:
            raise AudioProcessingError(f"Failed to decode audio data: {e}") from e

        if y is None or len(y) == 0:
            raise AudioProcessingError("Audio signal is empty or contains no samples.")

        return y, int(sample_rate)

    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def check_audio_signal_level(y: np.ndarray, dbfs_threshold: float = -60.0) -> None:
    """Check that audio signal is not silent or below threshold.
    
    Args:
        y: Audio time series.
        dbfs_threshold: Minimum threshold in dBFS (default -60 dBFS = 0.001 amplitude).
        
    Raises:
        InsufficientAudioSignalError: If signal is below threshold or silent.
    """
    if len(y) == 0:
        raise InsufficientAudioSignalError("Audio file contains no samples.")

    peak_amplitude = float(np.max(np.abs(y)))
    # Convert dBFS to linear amplitude: A = 10^(dBFS / 20)
    linear_threshold = 10.0 ** (dbfs_threshold / 20.0)

    if peak_amplitude < linear_threshold:
        raise InsufficientAudioSignalError(
            f"Audio signal peak ({peak_amplitude:.6f}) is below {dbfs_threshold:.1f} dBFS threshold ({linear_threshold:.6f}). "
            "File contains only silence or near-silence; no rhythmic transients found."
        )


def snap_to_nearest_transient(
    target_time: float,
    y: np.ndarray,
    sr: int,
    search_window: float = 0.25,
) -> float:
    """Snap a timestamp magnetically to the nearest strong acoustic transient peak.
    
    Searches within target_time +/- search_window seconds for the maximum
    amplitude peak (e.g. kick, snare, or drop).
    
    Args:
        target_time: Target timestamp in seconds.
        y: Audio waveform array.
        sr: Sample rate.
        search_window: Search range in seconds (+/-).
        
    Returns:
        Snapped timestamp in seconds, rounded to 3 decimals.
    """
    total_duration = len(y) / float(sr)
    if target_time <= 0.0 or total_duration <= 0.0:
        return 0.0

    start_sample = int(max(0.0, target_time - search_window) * sr)
    end_sample = int(min(total_duration, target_time + search_window) * sr)

    if end_sample - start_sample < int(sr * 0.02):
        return round(target_time, 3)

    y_slice = y[start_sample:end_sample]
    max_amp = float(np.max(np.abs(y_slice)))

    # If the window is near-silent, do not snap
    if max_amp < 0.02:
        return round(target_time, 3)

    peak_offset = int(np.argmax(np.abs(y_slice)))
    exact_time = (start_sample + peak_offset) / float(sr)
    return round(float(exact_time), 3)


def estimate_local_bpm_at_time(
    y: np.ndarray,
    sr: int,
    target_time: float,
    duration: float = 6.0,
    snap_transient: bool = True,
) -> Tuple[float, float]:
    """Estimate the exact local BPM from a specific timestamp forward.
    
    Extracts an audio segment starting at target_time (magnetically snapped to the
    nearest kick/downbeat transient), and computes the tempo of that specific section.
    
    Args:
        y: Audio waveform array.
        sr: Sample rate.
        target_time: Start timestamp in seconds.
        duration: Window duration in seconds to analyze.
        snap_transient: Whether to magnetically snap target_time to the nearest onset.
        
    Returns:
        Tuple of (snapped_start_time: float, estimated_bpm: float).
    """
    import librosa

    total_duration = len(y) / float(sr)
    if snap_transient and target_time > 0.0:
        snapped_time = snap_to_nearest_transient(target_time, y, sr)
    else:
        snapped_time = max(0.0, min(total_duration, target_time))

    start_sample = int(snapped_time * sr)
    end_sample = min(len(y), int((snapped_time + duration) * sr))

    # If chunk is too short at track end, expand backward slightly or use available audio
    if end_sample - start_sample < int(sr * 1.5):
        chunk = y[max(0, int((snapped_time - duration) * sr)) : end_sample]
    else:
        chunk = y[start_sample:end_sample]

    if len(chunk) < int(sr * 1.0):
        # Fallback to global tempo if audio is insufficient
        global_tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm_val = float(np.atleast_1d(global_tempo)[0]) if len(np.atleast_1d(global_tempo)) > 0 else 120.0
        return round(snapped_time, 3), round(bpm_val, 2)

    try:
        chunk_onset = librosa.onset.onset_strength(y=chunk, sr=sr)
        # Prioritize 80 - 180 BPM range to eliminate octave/half-time errors
        prior_bpm, _ = librosa.beat.beat_track(y=chunk, sr=sr, onset_envelope=chunk_onset, start_bpm=120.0)
        bpm_val = float(np.atleast_1d(prior_bpm)[0])
        if bpm_val <= 0.0 or not np.isfinite(bpm_val):
            bpm_val = 120.0
    except Exception:
        bpm_val = 120.0

    return round(snapped_time, 3), round(bpm_val, 2)


def detect_tempo_sections(
    audio_source: Union[str, Path, bytes, bytearray, Tuple[np.ndarray, int]],
    min_bpm_change: float = 6.0,
    window_duration_seconds: float = 8.0,
) -> List[BPMSection]:
    """Detect dynamic or constant tempo sections from an audio track.
    
    For constant tempo tracks, returns a single section starting at 0.0 spanning audio.
    For tracks with dynamic tempo transitions, returns chronological BPMSection sequence.
    
    Args:
        audio_source: File path, bytes, or pre-loaded (y, sr) tuple.
        min_bpm_change: Minimum BPM delta to classify as a new section (defaults to 6.0 BPM).
        window_duration_seconds: Duration of analysis windows for tempo shift detection.
        
    Returns:
        List of continuous BeatWarping BPMSection objects.
        
    Raises:
        AudioProcessingError: If audio is corrupted or unreadable.
        InsufficientAudioSignalError: If audio is silent or transients cannot be resolved.
    """
    import librosa

    if isinstance(audio_source, tuple) and len(audio_source) == 2 and isinstance(audio_source[0], np.ndarray):
        y, sr = audio_source
    else:
        y, sr = load_audio(audio_source)

    check_audio_signal_level(y)

    total_duration = float(len(y)) / float(sr)
    if total_duration < 0.5:
        raise InsufficientAudioSignalError("Audio track duration is too short for beat tracking (< 0.5s).")

    # Compute onset strength envelope
    try:
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    except Exception as e:
        raise AudioProcessingError(f"Onset strength computation failed: {e}") from e

    if np.max(onset_env) < 1e-4:
        raise InsufficientAudioSignalError("No rhythmic transients were found in the audio signal.")

    # Global tempo estimation and beat frame tracking
    try:
        global_tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset_env)
        global_bpm = float(np.atleast_1d(global_tempo)[0])
    except Exception as e:
        raise AudioProcessingError(f"Beat tracking analysis failed: {e}") from e

    if global_bpm <= 0.0 or not np.isfinite(global_bpm):
        raise InsufficientAudioSignalError("Unable to estimate a valid positive tempo.")

    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    # Dynamic tempo estimation using librosa.feature.tempo
    try:
        dyn_tempi = librosa.feature.tempo(onset_envelope=onset_env, sr=sr, aggregate=None)
        dyn_tempi = np.atleast_1d(dyn_tempi).astype(float)
        frame_times = librosa.frames_to_time(np.arange(len(dyn_tempi)), sr=sr)
    except Exception:
        dyn_tempi = None
        frame_times = None

    # Detect onsets for accurate boundary snapping
    try:
        onset_times = librosa.onset.onset_detect(y=y, sr=sr, units="time")
    except Exception:
        onset_times = beat_times

    # If track is short or has few beats, treat as constant tempo
    if total_duration < window_duration_seconds * 1.5 or (len(beat_times) < 8 and len(onset_times) < 8):
        initial = [BPMSection(startTime=0.0, startBeat=0.0, bpm=round(global_bpm, 2))]
        return recalculate_beats(initial)

    # Windowed analysis to check for genuine dynamic tempo transitions
    hop_sec = window_duration_seconds / 2.0
    window_starts = np.arange(0.0, max(0.0, total_duration - window_duration_seconds + 0.1), hop_sec)
    window_tempos: List[Tuple[float, float]] = []  # (start_time, local_bpm)

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
            # Fallback to onset / beat intervals in window
            times_in_w = onset_times[(onset_times >= w_start) & (onset_times <= w_end)]
            if len(times_in_w) >= 3:
                ibis = np.diff(times_in_w)
                valid_ibis = ibis[(ibis >= 0.15) & (ibis <= 2.5)]
                if len(valid_ibis) >= 2:
                    local_bpm = float(60.0 / np.median(valid_ibis))

        if local_bpm is not None and local_bpm > 0:
            window_tempos.append((float(w_start), float(local_bpm)))

    # If window analysis yielded too few data points, fallback to constant tempo
    if len(window_tempos) < 2:
        initial = [BPMSection(startTime=0.0, startBeat=0.0, bpm=round(global_bpm, 2))]
        return recalculate_beats(initial)

    # Check variation across windows
    tempos_only = [t[1] for t in window_tempos]
    bpm_spread = max(tempos_only) - min(tempos_only)
    bpm_std = float(np.std(tempos_only))

    # If spread and standard deviation are small, it is a constant tempo track
    if bpm_spread < min_bpm_change or bpm_std < (min_bpm_change / 2.0):
        initial = [BPMSection(startTime=0.0, startBeat=0.0, bpm=round(global_bpm, 2))]
        return recalculate_beats(initial)

    # Detect dynamic transitions
    detected_sections: List[BPMSection] = []
    # Section 0 always starts at 0.0 with the initial estimated tempo
    first_bpm = window_tempos[0][1]
    detected_sections.append(BPMSection(startTime=0.0, startBeat=0.0, bpm=round(first_bpm, 2)))

    current_section_bpm = first_bpm

    for w_start, w_bpm in window_tempos[1:]:
        bpm_diff = abs(w_bpm - current_section_bpm)
        if bpm_diff >= min_bpm_change:
            # Magnetically snap to the nearest physical transient peak around the window
            transition_time = snap_to_nearest_transient(float(w_start), y, sr, search_window=hop_sec / 2.0)

            # Ensure strict monotonicity (at least 1.5s separation)
            if transition_time > detected_sections[-1].startTime + 1.5:
                # Refine local tempo starting right from this downbeat
                _, refined_bpm = estimate_local_bpm_at_time(
                    y, sr, transition_time, duration=window_duration_seconds, snap_transient=False
                )
                final_bpm = refined_bpm if refined_bpm > 0 else w_bpm
                detected_sections.append(
                    BPMSection(
                        startTime=round(transition_time, 3),
                        startBeat=0.0,
                        bpm=round(final_bpm, 2),
                    )
                )
                current_section_bpm = final_bpm

    # Recalculate beats using BeatWarping formulas and validate
    final_sections = recalculate_beats(detected_sections)
    validate_sections(final_sections)
    return final_sections


def downsample_waveform(y: np.ndarray, sr: int, target_points: int = 1500) -> Tuple[np.ndarray, np.ndarray]:
    """Downsample audio amplitude envelope for high-performance waveform rendering.
    
    Args:
        y: Audio time series.
        sr: Sample rate.
        target_points: Maximum number of points in the rendered time envelope.
        
    Returns:
        Tuple of (time_axis: np.ndarray, amplitude_envelope: np.ndarray).
    """
    total_samples = len(y)
    total_duration = total_samples / float(sr)

    if total_samples <= target_points:
        times = np.linspace(0, total_duration, total_samples)
        return times, y

    # Block-wise max/min downsampling to preserve peaks
    step = total_samples // target_points
    trimmed_len = (total_samples // step) * step
    y_reshaped = y[:trimmed_len].reshape(-1, step)
    
    # Calculate peak amplitude per block
    peaks = np.max(np.abs(y_reshaped), axis=1)
    times = np.linspace(0, total_duration, len(peaks))
    return times, peaks
