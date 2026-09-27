"""Audio analysis, beat tracking, and conversion package."""

from .bpm_sections import (
    recalculate_beats,
    validate_sections,
    add_marker,
    update_marker,
    delete_marker,
    create_initial_sections,
)
from .converter import (
    convert_mp3_to_ogg,
    convert_audio_bytes_to_ogg,
    is_ffmpeg_available,
    resolve_ffmpeg_path,
)
from .beat_detection import (
    load_audio,
    detect_tempo_sections,
    downsample_waveform,
    check_audio_signal_level,
)
from .exceptions import (
    AudioAnalysisError,
    AudioProcessingError,
    InsufficientAudioSignalError,
    ValidationError,
    DependencyError,
    TranscodingError,
)

__all__ = [
    "recalculate_beats",
    "validate_sections",
    "add_marker",
    "update_marker",
    "delete_marker",
    "create_initial_sections",
    "convert_mp3_to_ogg",
    "convert_audio_bytes_to_ogg",
    "is_ffmpeg_available",
    "resolve_ffmpeg_path",
    "load_audio",
    "detect_tempo_sections",
    "downsample_waveform",
    "check_audio_signal_level",
    "AudioAnalysisError",
    "AudioProcessingError",
    "InsufficientAudioSignalError",
    "ValidationError",
    "DependencyError",
    "TranscodingError",
]
