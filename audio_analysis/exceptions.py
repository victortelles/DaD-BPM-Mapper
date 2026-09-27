"""Custom exception types for audio analysis, validation, and conversion."""


class AudioAnalysisError(Exception):
    """Base exception for all audio analysis errors."""
    pass


class AudioProcessingError(AudioAnalysisError):
    """Raised when an audio file cannot be loaded, decoded, or is corrupted."""
    pass


class InsufficientAudioSignalError(AudioAnalysisError):
    """Raised when an audio file is silent or contains insufficient transient signal for beat tracking."""
    pass


class ValidationError(AudioAnalysisError):
    """Raised when BPM section parameters or constraints are violated."""
    pass


class DependencyError(Exception):
    """Raised when an external system dependency (such as FFmpeg) is missing."""
    pass


class TranscodingError(Exception):
    """Raised when FFmpeg transcoding process fails or exits with an error."""
    pass
