"""Mod packaging engine for Dead as Disco BeatWarping metadata and audio bundles."""

import io
import json
import os
import re
import zipfile
from pathlib import Path
from typing import List, Optional, Union

from audio_analysis.bpm_sections import recalculate_beats, validate_sections
from models.song_metadata import BPMSection, ExportResult, SongMetadata
from .exceptions import ExportIOError


def sanitize_song_name(raw_name: str) -> str:
    """Sanitize song title into a filesystem-safe identifier.
    
    Replaces any character that is not alphanumeric or underscore with an underscore.
    Example: 'Rock / Pop: Hit? *' -> 'Rock___Pop__Hit___'
    
    Args:
        raw_name: User-provided song title or filename without extension.
        
    Returns:
        Filesystem-safe sanitized string.
    """
    if not raw_name or not raw_name.strip():
        return "imported_song"

    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", raw_name)
    # Ensure it's not empty
    if not sanitized.strip("_"):
        return "imported_song"
    return sanitized


def get_game_imported_songs_dir() -> Path:
    """Get the standard Dead as Disco mod destination path:
    %localappdata%\\Pagoda\\Saved\\ImportedSongs\\
    """
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        return Path(local_app_data) / "Pagoda" / "Saved" / "ImportedSongs"
    return Path.home() / "AppData" / "Local" / "Pagoda" / "Saved" / "ImportedSongs"


def generate_metadata(
    song_name: str,
    bpm_sections: List[BPMSection],
    audio_filename: Optional[str] = None,
) -> SongMetadata:
    """Generate game-compliant BeatWarping JSON metadata.
    
    Args:
        song_name: Raw or sanitized song name.
        bpm_sections: List of BPM sections to be serialized.
        audio_filename: Optional explicit audio filename (defaults to {sanitized_name}.ogg).
        
    Returns:
        SongMetadata dataclass instance ready for serialization.
    """
    clean_name = sanitize_song_name(song_name)
    sorted_sections = recalculate_beats(bpm_sections)
    validate_sections(sorted_sections)

    target_audio_file = audio_filename or f"{clean_name}.ogg"

    return SongMetadata(
        songName=clean_name,
        audioFile=target_audio_file,
        bpmSections=sorted_sections,
    )


def build_mod_zip(
    song_name: str,
    bpm_sections: List[BPMSection],
    ogg_audio: Union[bytes, Path, str],
    include_subfolder: bool = True,
) -> ExportResult:
    """Build a downloadable ZIP mod package containing the .ogg audio and BeatWarping .json.
    
    Args:
        song_name: Song title.
        bpm_sections: Validated BPM sections.
        ogg_audio: Transcoded OGG audio as raw bytes or file path.
        include_subfolder: Whether files should be bundled inside a directory named after the song.
        
    Returns:
        ExportResult containing zip_bytes, filename, and sanitized song_name.
        
    Raises:
        ExportIOError: If reading audio bytes or constructing the ZIP fails.
    """
    clean_name = sanitize_song_name(song_name)
    metadata = generate_metadata(clean_name, bpm_sections, f"{clean_name}.ogg")
    json_bytes = metadata.to_json(indent=2).encode("utf-8")

    # Read audio bytes
    try:
        if isinstance(ogg_audio, (Path, str)):
            audio_path = Path(ogg_audio)
            if not audio_path.exists():
                raise FileNotFoundError(f"OGG audio file not found: {audio_path}")
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
        elif isinstance(ogg_audio, (bytes, bytearray)):
            audio_bytes = bytes(ogg_audio)
        else:
            raise TypeError(f"Unsupported ogg_audio type: {type(ogg_audio)}")
    except Exception as e:
        raise ExportIOError(f"Failed to read OGG audio data: {e}") from e

    # Build ZIP archive in memory
    try:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            prefix = f"{clean_name}/" if include_subfolder else ""
            zf.writestr(f"{prefix}{clean_name}.json", json_bytes)
            zf.writestr(f"{prefix}{clean_name}.ogg", audio_bytes)
            # Also write to root if subfolder is enabled, ensuring dual compatibility
            if include_subfolder:
                zf.writestr(f"{clean_name}.json", json_bytes)
                zf.writestr(f"{clean_name}.ogg", audio_bytes)

        zip_data = zip_buffer.getvalue()
    except Exception as e:
        raise ExportIOError(f"Failed to create ZIP package: {e}") from e

    return ExportResult(
        zip_bytes=zip_data,
        filename=f"{clean_name}.zip",
        song_name=clean_name,
    )


def export_to_directory(
    song_name: str,
    bpm_sections: List[BPMSection],
    ogg_audio: Union[bytes, Path, str],
    target_dir: Optional[Union[str, Path]] = None,
) -> Path:
    """Export mod package files directly into a filesystem directory.
    
    Defaults to %localappdata%\\Pagoda\\Saved\\ImportedSongs\\{sanitized_song_name}\\
    
    Args:
        song_name: Song title.
        bpm_sections: Validated BPM sections.
        ogg_audio: Transcoded OGG audio as bytes or file path.
        target_dir: Destination directory. Defaults to standard game folder.
        
    Returns:
        Path to the song folder containing exported files.
        
    Raises:
        ExportIOError: If writing to destination directory fails.
    """
    clean_name = sanitize_song_name(song_name)
    metadata = generate_metadata(clean_name, bpm_sections, f"{clean_name}.ogg")
    json_content = metadata.to_json(indent=2)

    dest_dir = Path(target_dir) if target_dir is not None else get_game_imported_songs_dir() / clean_name

    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ExportIOError(f"Cannot create destination directory '{dest_dir}': {e}") from e

    json_file = dest_dir / f"{clean_name}.json"
    ogg_file = dest_dir / f"{clean_name}.ogg"

    try:
        with open(json_file, "w", encoding="utf-8") as f:
            f.write(json_content)
    except Exception as e:
        raise ExportIOError(f"Failed to write metadata file '{json_file}': {e}") from e

    try:
        if isinstance(ogg_audio, (Path, str)):
            src_audio = Path(ogg_audio)
            with open(src_audio, "rb") as sf, open(ogg_file, "wb") as df:
                df.write(sf.read())
        elif isinstance(ogg_audio, (bytes, bytearray)):
            with open(ogg_file, "wb") as f:
                f.write(bytes(ogg_audio))
        else:
            raise TypeError(f"Unsupported ogg_audio type: {type(ogg_audio)}")
    except Exception as e:
        raise ExportIOError(f"Failed to write audio file '{ogg_file}': {e}") from e

    return dest_dir
