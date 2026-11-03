"""Mod packaging engine for Dead as Disco native Meta.json and audio.ogg bundles."""

import hashlib
import io
import json
import os
import re
import zipfile
import zlib
from pathlib import Path
from typing import Any, List, Optional, Union

from audio_analysis.bpm_sections import recalculate_beats, validate_sections
from audio_analysis.security import compute_audio_md5
from models.song_metadata import (
    AnalyseResult,
    BPMSection,
    CustomTempoSection,
    ErrorCode,
    ExportResult,
    SongMetadata,
    _clean_number,
    sections_to_native_tempo,
)
from .exceptions import ExportIOError


class ZipExportBytes(bytes):
    """Bytes subclass for in-memory ZIP archives that also exposes ExportResult attributes."""
    zip_bytes: bytes
    filename: str
    song_name: str
    metadata: Optional[SongMetadata]
    folder_path: Optional[Path]
    ogg_path: Optional[Path]
    json_path: Optional[Path]

    def __new__(
        cls, zip_data: bytes, filename: str = "", song_name: str = "", metadata: Optional[SongMetadata] = None
    ) -> "ZipExportBytes":
        obj = super().__new__(cls, zip_data)
        obj.zip_bytes, obj.filename, obj.song_name, obj.metadata = zip_data, filename, song_name, metadata
        obj.folder_path = obj.ogg_path = obj.json_path = None
        return obj


class ImportedSongEntry(tuple):
    """Hybrid tuple/dict/object representing a discovered song in ImportedSongs."""

    def __new__(
        cls, name: str, json_path: Path, ogg_path: Path, folder_path: Path, metadata: Optional[SongMetadata] = None
    ) -> "ImportedSongEntry":
        obj = super().__new__(cls, (name, json_path, ogg_path))
        obj.name, obj.song_name = name, (metadata.songName if metadata else name)
        obj.json_path = obj.meta_path = json_path
        obj.ogg_path = obj.audio_path = ogg_path
        obj.folder_path, obj.metadata = folder_path, metadata
        return obj

    def __getitem__(self, key: Union[int, slice, str]) -> Any:
        return getattr(self, key) if isinstance(key, str) else super().__getitem__(key)


def sanitize_song_name(raw_name: str) -> str:
    """Sanitize song title into a Windows/POSIX filesystem-safe folder identifier."""
    if not raw_name or not raw_name.strip():
        return "imported_song"
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", raw_name)
    return sanitized if sanitized.strip("_") else "imported_song"


sanitize_folder_name = sanitize_song_name


def get_game_imported_songs_dir() -> Path:
    """Return %localappdata%\\Pagoda\\Saved\\ImportedSongs\\ path."""
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        return Path(local_app_data) / "Pagoda" / "Saved" / "ImportedSongs"
    return Path.home() / "AppData" / "Local" / "Pagoda" / "Saved" / "ImportedSongs"


def _resolve_audio_entry_name(audio_filename: Optional[str] = None, audio_ext: Optional[str] = None) -> str:
    if audio_ext:
        return f"audio.{audio_ext.strip().lstrip('.').lower() or 'ogg'}"
    if audio_filename:
        raw = audio_filename.strip()
        ext = raw.lstrip(".").lower() if raw.startswith(".") else (Path(raw).suffix.lstrip(".").lower() or "ogg")
        return f"audio.{ext}"
    return "audio.ogg"


def _read_audio_bytes(ogg_audio: Union[bytes, bytearray, Path, str]) -> bytes:
    try:
        if isinstance(ogg_audio, (Path, str)):
            audio_path = Path(ogg_audio)
            if not audio_path.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            return audio_path.read_bytes()
        if isinstance(ogg_audio, (bytes, bytearray)):
            return bytes(ogg_audio)
        raise TypeError(f"Unsupported audio data type: {type(ogg_audio)}")
    except Exception as exc:
        raise ExportIOError(f"Failed to read audio data: {exc}") from exc


def generate_metadata(
    song_name: str,
    bpm_sections: Optional[List[BPMSection]] = None,
    audio_filename: Optional[Union[str, bytes]] = None,
    *,
    audio_bytes: Optional[bytes] = None,
    original_filename: Optional[str] = None,
    original_audio_hash: Optional[str] = None,
    original_audio_path: Optional[str] = None,
    beat_offset_ms: Union[int, float] = 0,
    start_song_offset: Union[float, int] = 0,
    end_song_offset: Union[float, int] = 0,
    fit_quality: float = 0.92,
    performed_by: Optional[List[str]] = None,
    written_by: Optional[List[str]] = None,
    unique_id: Optional[int] = None,
    seed: Optional[int] = None,
    ue_asset_name: Optional[str] = None,
    tempo: Optional[Union[float, int]] = None,
    custom_tempo_sections: Optional[List[CustomTempoSection]] = None,
) -> SongMetadata:
    """Generate a full 16-field Dead as Disco SongMetadata instance."""
    display_name = song_name.strip() if isinstance(song_name, str) else ""
    if isinstance(audio_filename, (bytes, bytearray)) and audio_bytes is None:
        audio_bytes, audio_filename = bytes(audio_filename), None
    if bpm_sections is not None:
        sorted_sections = recalculate_beats(bpm_sections)
        validate_sections(sorted_sections)
        base_tempo, native_custom = sections_to_native_tempo(sorted_sections)
        tempo = base_tempo if tempo is None else tempo
        custom_tempo_sections = native_custom if custom_tempo_sections is None else custom_tempo_sections
    resolved_tempo = _clean_number(tempo if tempo is not None else 120)
    resolved_custom = list(custom_tempo_sections) if custom_tempo_sections is not None else []
    resolved_offset = _clean_number(beat_offset_ms)
    if original_audio_hash:
        file_hash = original_audio_hash.lower()
    elif audio_bytes is not None:
        file_hash = compute_audio_md5(audio_bytes)
    else:
        file_hash = hashlib.md5(display_name.encode("utf-8")).hexdigest()
    safe_folder = sanitize_song_name(display_name)
    file_path = original_audio_path or original_filename or (audio_filename if isinstance(audio_filename, str) else None) or f"{safe_folder}/audio.ogg"
    uid = int(unique_id) if unique_id is not None else (zlib.crc32(display_name.encode("utf-8")) & 0xFFFFFFFF)
    rng_seed = int(seed) if seed is not None else (zlib.crc32((file_hash + display_name).encode("utf-8")) & 0xFFFFFFFF)
    return SongMetadata(
        version=1, uniqueId=uid, songName=display_name, performedBy=list(performed_by or []),
        writtenBy=list(written_by or []), seed=rng_seed, tempo=resolved_tempo,
        customTempoSections=resolved_custom, beatOffset=resolved_offset,
        startSongOffset=_clean_number(start_song_offset), endSongOffset=_clean_number(end_song_offset),
        uEAssetName=ue_asset_name or display_name, originalAudioFileHash=file_hash,
        originalAudioFilePath=str(file_path).replace("\\", "/"),
        analyseResult=AnalyseResult(tempo=resolved_tempo, beatOffset=resolved_offset, fitQuality=float(fit_quality), errorCode=ErrorCode()),
        beatTracks=[],
    )


def _prepare_export_inputs(
    song_name: Union[str, SongMetadata],
    bpm_sections: Optional[Union[List[BPMSection], bytes, bytearray, Path, str]],
    ogg_audio: Optional[Union[bytes, bytearray, Path, str]],
    metadata: Optional[SongMetadata],
    meta_kwargs: dict,
) -> tuple[SongMetadata, bytes]:
    if isinstance(song_name, SongMetadata):
        raw_audio = bpm_sections if ogg_audio is None else ogg_audio
        return song_name, (_read_audio_bytes(raw_audio) if raw_audio is not None else b"")
    raw_audio = ogg_audio
    if raw_audio is None and isinstance(bpm_sections, (bytes, bytearray, Path, str)):
        raw_audio, bpm_sections = bpm_sections, None
    audio_bytes = _read_audio_bytes(raw_audio) if raw_audio is not None else b""
    meta = metadata or generate_metadata(
        song_name, bpm_sections if isinstance(bpm_sections, list) else None,
        audio_bytes=meta_kwargs.pop("audio_bytes", audio_bytes), **meta_kwargs,
    )
    return meta, audio_bytes


def build_mod_zip(
    song_name: Union[str, SongMetadata],
    bpm_sections: Optional[Union[List[BPMSection], bytes, bytearray, Path, str]] = None,
    ogg_audio: Optional[Union[bytes, bytearray, Path, str]] = None,
    audio_filename: Optional[str] = None,
    include_subfolder: bool = True,
    *,
    audio_ext: Optional[str] = None,
    metadata: Optional[SongMetadata] = None,
    **meta_kwargs: Any,
) -> ZipExportBytes:
    """Build an in-memory ZIP archive with <SafeFolderName>/Meta.json and <SafeFolderName>/audio.ogg."""
    meta, audio_bytes = _prepare_export_inputs(song_name, bpm_sections, ogg_audio, metadata, meta_kwargs)
    clean_folder, target_audio_name = sanitize_song_name(meta.songName), _resolve_audio_entry_name(audio_filename, audio_ext)
    json_bytes = meta.to_meta_json(indent="\t").encode("utf-8")
    try:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            prefix = f"{clean_folder}/" if include_subfolder else ""
            zf.writestr(f"{prefix}Meta.json", json_bytes)
            zf.writestr(f"{prefix}{target_audio_name}", audio_bytes)
        zip_data = zip_buffer.getvalue()
    except Exception as exc:
        raise ExportIOError(f"Failed to create ZIP package: {exc}") from exc
    return ZipExportBytes(zip_data, filename=f"{clean_folder}.zip", song_name=clean_folder, metadata=meta)


def export_to_directory(
    song_name: Union[str, SongMetadata],
    bpm_sections: Optional[Union[List[BPMSection], bytes, bytearray, Path, str]] = None,
    ogg_audio: Optional[Union[bytes, bytearray, Path, str]] = None,
    audio_filename: Optional[str] = None,
    target_dir: Optional[Union[str, Path]] = None,
    *,
    audio_ext: Optional[str] = None,
    metadata: Optional[SongMetadata] = None,
    **meta_kwargs: Any,
) -> ExportResult:
    """Write <target_dir>/<SafeFolderName>/Meta.json and <target_dir>/<SafeFolderName>/audio.ogg."""
    meta, audio_bytes = _prepare_export_inputs(song_name, bpm_sections, ogg_audio, metadata, meta_kwargs)
    clean_folder, target_audio_name = sanitize_song_name(meta.songName), _resolve_audio_entry_name(audio_filename, audio_ext)
    base_dir = Path(target_dir) if target_dir is not None else get_game_imported_songs_dir()
    dest_dir = base_dir if base_dir.name == clean_folder else (base_dir / clean_folder)
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        json_file, audio_file = dest_dir / "Meta.json", dest_dir / target_audio_name
        json_file.write_text(meta.to_meta_json(indent="\t"), encoding="utf-8")
        audio_file.write_bytes(audio_bytes)
    except Exception as exc:
        raise ExportIOError(f"Failed to export mod to '{dest_dir}': {exc}") from exc
    return ExportResult(
        zip_bytes=b"", filename=f"{clean_folder}.zip", song_name=clean_folder,
        folder_path=dest_dir, ogg_path=audio_file, json_path=json_file, metadata=meta,
    )


def list_imported_songs(base_dir: Optional[Union[str, Path]] = None) -> List[ImportedSongEntry]:
    """Scan ImportedSongs for existing song folders (Meta.json/<folder>.json and audio.ogg/<folder>.ogg)."""
    root = Path(base_dir) if base_dir is not None else get_game_imported_songs_dir()
    if not root.exists() or not root.is_dir():
        return []
    entries: List[ImportedSongEntry] = []
    for folder in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not folder.is_dir():
            continue
        meta_path = folder / "Meta.json" if (folder / "Meta.json").exists() else folder / f"{folder.name}.json"
        if not meta_path.exists():
            continue
        audio_path = folder / "audio.ogg" if (folder / "audio.ogg").exists() else folder / f"{folder.name}.ogg"
        parsed_meta: Optional[SongMetadata] = None
        try:
            parsed_meta = SongMetadata.from_meta_dict(json.loads(meta_path.read_text(encoding="utf-8")))
        except Exception:
            parsed_meta = None
        entries.append(ImportedSongEntry(folder.name, meta_path, audio_path, folder, parsed_meta))
    return entries


discover_imported_songs = list_imported_songs
