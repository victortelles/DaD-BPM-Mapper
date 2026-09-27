"""Custom exception types for packaging and exporting mod bundles."""


class ExportError(Exception):
    """Base exception for export and packaging errors."""
    pass


class ExportIOError(ExportError):
    """Raised when writing to disk or creating the mod archive fails."""
    pass
