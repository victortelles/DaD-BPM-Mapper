"""DSP waveform loading, signal level validation, downsampling, and transient peak snapping."""

import tempfile
from pathlib import Path
from typing import Optional, Tuple, Union

import numpy as np

from .exceptions import AudioProcessingError, InsufficientAudioSignalError


def load_audio(
    audio_source: Union[str, Path, bytes, bytearray],
    sr: Optional[int] = None,
    mono: bool = True,
    target_sr: Optional[int] = None,
) -> Tuple[np.ndarray, int]:
    """Load an audio file or raw byte stream non-destructively into a numpy waveform array.

    Args:
        audio_source: File path or raw audio bytes (copied to an isolated temp buffer).
        sr: Target sample rate. If None, uses target_sr or preserves native sample rate.
        mono: If True, convert multi-channel audio to mono.
        target_sr: Optional alias for target sample rate.

    Returns:
        Tuple of (y: np.ndarray audio time series, sr: int sample rate).

    Raises:
        AudioProcessingError: If loading, decoding, or reading audio fails.
    """
    import librosa

    resolved_sr = target_sr if (sr is None and target_sr is not None) else sr
    temp_path: Optional[Path] = None
    try:
        if isinstance(audio_source, (bytes, bytearray)):
            isolated_copy = bytes(audio_source)
            with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as tf:
                tf.write(isolated_copy)
                temp_path = Path(tf.name)
            file_to_load = str(temp_path)
        elif isinstance(audio_source, (str, Path)):
            file_to_load = str(audio_source)
            if not Path(file_to_load).exists():
                raise AudioProcessingError(f"Audio file not found: {file_to_load}")
        else:
            raise AudioProcessingError(f"Unsupported audio source type: {type(audio_source)}")

        try:
            y, sample_rate = librosa.load(file_to_load, sr=resolved_sr, mono=mono)
        except Exception as exc:
            raise AudioProcessingError(f"Failed to decode audio data: {exc}") from exc

        if y is None or len(y) == 0:
            raise AudioProcessingError("Audio signal is empty or contains no samples.")

        return y, int(sample_rate)
    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def check_audio_signal_level(
    y: np.ndarray,
    dbfs_threshold: float = -60.0,
    min_dbfs: Optional[float] = None,
) -> None:
    """Verify that the audio signal peak amplitude is at or above the minimum dBFS threshold.

    Args:
        y: Audio time series.
        dbfs_threshold: Minimum threshold in dBFS (default -60.0 dBFS = 0.001 linear amplitude).
        min_dbfs: Optional keyword alias for dbfs_threshold.

    Raises:
        InsufficientAudioSignalError: If signal is empty or below threshold.
    """
    if y is None or len(y) == 0:
        raise InsufficientAudioSignalError("Audio file contains no samples.")

    threshold = float(min_dbfs) if min_dbfs is not None else float(dbfs_threshold)
    peak_amplitude = float(np.max(np.abs(y)))
    linear_threshold = 10.0 ** (threshold / 20.0)

    if peak_amplitude < linear_threshold:
        raise InsufficientAudioSignalError(
            f"Audio signal peak ({peak_amplitude:.6f}) is below {threshold:.1f} dBFS threshold ({linear_threshold:.6f}). "
            "File contains only silence or near-silence; no rhythmic transients found."
        )


def downsample_waveform(
    y: np.ndarray,
    sr: int,
    target_points: int = 1500,
) -> Tuple[np.ndarray, np.ndarray]:
    """Downsample audio amplitude envelope for high-performance waveform rendering.

    Args:
        y: Audio time series.
        sr: Sample rate in Hz.
        target_points: Target number of envelope points.

    Returns:
        Tuple of (time_axis: np.ndarray, amplitude_envelope: np.ndarray).
    """
    total_samples = len(y)
    total_duration = total_samples / float(sr) if sr > 0 else 0.0

    if total_samples == 0 or total_samples <= target_points or target_points <= 0:
        times = np.linspace(0.0, total_duration, total_samples)
        return times, y

    step = max(1, total_samples // target_points)
    trimmed_len = (total_samples // step) * step
    y_reshaped = y[:trimmed_len].reshape(-1, step)
    peaks = np.max(np.abs(y_reshaped), axis=1)
    times = np.linspace(0.0, total_duration, len(peaks))
    return times, peaks


def snap_to_nearest_transient(
    target_time: float,
    y: np.ndarray,
    sr: int,
    search_window: float = 0.25,
) -> float:
    """Snap a candidate timestamp magnetically to the nearest prominent transient peak.

    Args:
        target_time: Candidate timestamp in seconds.
        y: Audio waveform array.
        sr: Sample rate in Hz.
        search_window: Search tolerance window in seconds (+/-).

    Returns:
        Snapped timestamp in seconds rounded to 3 decimal places.
    """
    if y is None or len(y) == 0 or sr <= 0:
        return round(max(0.0, float(target_time)), 3)

    total_duration = len(y) / float(sr)
    if target_time <= 0.0 or total_duration <= 0.0:
        return 0.0

    start_sample = int(max(0.0, target_time - search_window) * sr)
    end_sample = int(min(total_duration, target_time + search_window) * sr)

    if end_sample - start_sample < int(sr * 0.02):
        return round(float(target_time), 3)

    from scipy.signal import find_peaks

    y_slice = y[start_sample:end_sample]
    slice_abs = np.abs(y_slice)
    max_amp = float(np.max(slice_abs))

    if max_amp < 0.02:
        return round(float(target_time), 3)

    peaks, _ = find_peaks(slice_abs, height=max_amp * 0.35, distance=max(1, int(sr * 0.08)))
    if len(peaks) == 0:
        peak_offset = int(np.argmax(slice_abs))
    else:
        target_sample_in_slice = int((target_time - (start_sample / float(sr))) * sr)
        closest_idx = int(np.argmin(np.abs(peaks - target_sample_in_slice)))
        peak_offset = int(peaks[closest_idx])

    exact_time = (start_sample + peak_offset) / float(sr)
    return round(float(exact_time), 3)


def normalize_bpm_octave(
    bpm: float,
    min_bpm: float = 42.0,
    max_bpm: float = 205.0,
) -> float:
    """Normalize a tempo into the playable rhythmic human octave [min_bpm, max_bpm].

    Harmonic subdivisions (e.g. 200-320 BPM from 16th-note trap hi-hats) are halved
    back to their true fundamental tempo (100-160 BPM).
    """
    if bpm <= 0.0 or not np.isfinite(bpm):
        return 120.0
    val = float(bpm)
    while val > max_bpm:
        val /= 2.0
    while val < min_bpm and val > 0.0:
        val *= 2.0
    return round(val, 2)


def estimate_local_bpm_at_time(
    y: np.ndarray,
    sr: int,
    target_time: float,
    duration: float = 6.0,
    snap_transient: bool = True,
) -> Tuple[float, float]:
    """Estimate the local BPM starting from a specific timestamp forward.

    Args:
        y: Audio waveform array.
        sr: Sample rate in Hz.
        target_time: Start timestamp in seconds.
        duration: Analysis window duration in seconds.
        snap_transient: Whether to magnetically snap target_time to the nearest onset peak.

    Returns:
        Tuple of (snapped_start_time: float, estimated_bpm: float).
    """
    import librosa

    total_duration = len(y) / float(sr)
    if snap_transient and target_time > 0.0:
        snapped_time = snap_to_nearest_transient(target_time, y, sr)
    else:
        snapped_time = max(0.0, min(total_duration, float(target_time)))

    start_sample = int(snapped_time * sr)
    end_sample = min(len(y), int((snapped_time + duration) * sr))

    if end_sample - start_sample < int(sr * 1.5):
        chunk = y[max(0, int((snapped_time - duration) * sr)) : end_sample]
    else:
        chunk = y[start_sample:end_sample]

    if len(chunk) < int(sr * 1.0):
        global_tempo, _ = librosa.beat.beat_track(y=y, sr=sr, start_bpm=120.0)
        arr = np.atleast_1d(global_tempo)
        bpm_val = float(arr[0]) if len(arr) > 0 and float(arr[0]) > 0 else 120.0
        return round(snapped_time, 3), normalize_bpm_octave(bpm_val)

    try:
        chunk_onset = librosa.onset.onset_strength(y=chunk, sr=sr)
        prior_bpm, _ = librosa.beat.beat_track(y=chunk, sr=sr, onset_envelope=chunk_onset, start_bpm=120.0)
        bpm_val = float(np.atleast_1d(prior_bpm)[0])
        if bpm_val <= 0.0 or not np.isfinite(bpm_val):
            bpm_val = 120.0
    except Exception:
        bpm_val = 120.0

    return round(snapped_time, 3), normalize_bpm_octave(bpm_val)


def calculate_bpm_from_peaks(
    y: np.ndarray,
    sr: int,
    start_time: float,
    end_time: Optional[float] = None,
) -> float:
    """Compute section BPM from median inter-onset intervals clamped to [30.0, 300.0] BPM.

    Args:
        y: Audio waveform array.
        sr: Sample rate in Hz.
        start_time: Segment start time in seconds.
        end_time: Optional segment end time in seconds (defaults to start_time + 8.0s).

    Returns:
        Estimated BPM clamped to [30.0, 300.0] rounded to 2 decimal places.
    """
    import librosa

    total_duration = len(y) / float(sr)
    if end_time is None or end_time <= start_time:
        end_time = min(total_duration, start_time + 8.0)

    start_sample = int(max(0.0, start_time) * sr)
    end_sample = int(min(total_duration, end_time) * sr)

    if end_sample - start_sample < int(sr * 1.5):
        end_sample = min(len(y), start_sample + int(sr * 3.0))
        if end_sample - start_sample < int(sr * 1.5):
            start_sample = max(0, end_sample - int(sr * 3.0))

    chunk = y[start_sample:end_sample]
    if len(chunk) < int(sr * 0.5):
        return 120.0

    try:
        onset_env = librosa.onset.onset_strength(y=chunk, sr=sr)
        if len(onset_env) == 0 or np.max(onset_env) < 1e-4:
            return 120.0

        onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
        peak_times = librosa.frames_to_time(onset_frames, sr=sr)

        ibi_bpm: Optional[float] = None
        if len(peak_times) >= 3:
            ibis = np.diff(peak_times)
            valid_ibis = ibis[(ibis >= 0.15) & (ibis <= 2.0)]
            if len(valid_ibis) >= 2:
                ibi_bpm = 60.0 / float(np.median(valid_ibis))

        t, _ = librosa.beat.beat_track(y=chunk, sr=sr, onset_envelope=onset_env, start_bpm=120.0)
        bt_bpm = float(np.atleast_1d(t)[0])

        if ibi_bpm is not None and 20.0 < ibi_bpm < 350.0:
            if abs(ibi_bpm - bt_bpm) < 15.0:
                final_bpm = ibi_bpm
            elif abs(ibi_bpm / 2.0 - bt_bpm) < 10.0 or abs(ibi_bpm * 2.0 - bt_bpm) < 10.0:
                final_bpm = bt_bpm
            else:
                final_bpm = ibi_bpm
        else:
            final_bpm = bt_bpm if bt_bpm > 0 else 120.0

        if final_bpm <= 0.0 or not np.isfinite(final_bpm):
            final_bpm = 120.0

        return normalize_bpm_octave(final_bpm)
    except Exception:
        return 120.0


__all__ = [
    "load_audio",
    "check_audio_signal_level",
    "downsample_waveform",
    "snap_to_nearest_transient",
    "estimate_local_bpm_at_time",
    "calculate_bpm_from_peaks",
    "normalize_bpm_octave",
]
