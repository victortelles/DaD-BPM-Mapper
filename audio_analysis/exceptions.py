"""Custom exception types for audio security validation, DSP analysis, and transcoding."""


class AudioAnalysisError(Exception):
    """Base exception for all audio analysis and processing errors."""
    pass


class AudioProcessingError(AudioAnalysisError):
    """Raised when an audio file cannot be loaded, decoded, or processed."""
    pass


class SecurityValidationError(AudioProcessingError):
    """Raised when an uploaded file fails extension, size, or binary magic-byte checks."""
    pass


# Alias matching spec terminology
AudioSecurityError = SecurityValidationError


class InsufficientAudioSignalError(AudioProcessingError):
    """Raised when an audio file is silent or contains insufficient transient signal for beat tracking."""
    pass


class ValidationError(AudioProcessingError):
    """Raised when song metadata or BPM section invariants are violated."""
    pass


class DependencyError(AudioProcessingError):
    """Raised when an external system dependency (such as FFmpeg) is missing."""
    pass


class TranscodingError(AudioProcessingError):
    """Raised when audio transcoding or resampling fails."""
    pass


__all__ = [
    "AudioAnalysisError",
    "AudioProcessingError",
    "SecurityValidationError",
    "AudioSecurityError",
    "InsufficientAudioSignalError",
    "ValidationError",
    "DependencyError",
    "TranscodingError",
]
