"""Unit tests for mod packaging engine, JSON metadata generation, and ZIP builder."""

import io
import json
import zipfile
from pathlib import Path
import pytest

from audio_analysis.bpm_sections import create_initial_sections, recalculate_beats
from export.exceptions import ExportIOError
from export.package_builder import (
    build_mod_zip,
    export_to_directory,
    generate_metadata,
    sanitize_song_name,
)
from models.song_metadata import BPMSection, SongMetadata


def test_song_title_sanitization():
    """Scenario: Song title sanitization.
    
    Given unsafe characters: 'Rock / Pop: Hit? *' -> 'Rock___Pop__Hit___'
    """
    raw_title = "Rock / Pop: Hit? *"
    sanitized = sanitize_song_name(raw_title)
    assert sanitized == "Rock___Pop__Hit___"

    # Edge cases: empty strings or all-unsafe characters
    assert sanitize_song_name("") == "imported_song"
    assert sanitize_song_name("   ") == "imported_song"
    assert sanitize_song_name("???***///") == "imported_song"
    assert sanitize_song_name("Neon_Pulse_2024") == "Neon_Pulse_2024"


def test_valid_json_schema_output():
    """Scenario: Valid JSON schema output.
    
    Top-level fields songName, audioFile, bpmSections.
    Sections ordered chronologically with startTime, startBeat, bpm.
    """
    sections = [
        BPMSection(startTime=0.0, startBeat=0.0, bpm=120.0),
        BPMSection(startTime=10.0, startBeat=20.0, bpm=140.0),
    ]
    metadata: SongMetadata = generate_metadata("Neon Pulse", sections)

    assert metadata.songName == "Neon_Pulse"
    assert metadata.audioFile == "Neon_Pulse.ogg"
    assert len(metadata.bpmSections) == 2

    # Verify JSON serialization
    raw_json = metadata.to_json()
    data = json.loads(raw_json)

    assert data["songName"] == "Neon_Pulse"
    assert data["audioFile"] == "Neon_Pulse.ogg"
    assert isinstance(data["bpmSections"], list)
    assert len(data["bpmSections"]) == 2

    sec0 = data["bpmSections"][0]
    assert sec0["startTime"] == 0.0
    assert sec0["startBeat"] == 0.0
    assert sec0["bpm"] == 120.0

    sec1 = data["bpmSections"][1]
    assert sec1["startTime"] == 10.0
    assert sec1["startBeat"] == 20.0
    assert sec1["bpm"] == 140.0


def test_zip_archive_bundle_generation():
    """Scenario: ZIP archive bundle generation.
    
    Bundles .ogg and BeatWarping .json into a valid ZIP archive named {song_name}.zip.
    """
    song_name = "Cyber_Groove"
    sections = create_initial_sections(128.0)
    fake_ogg_bytes = b"OggS_SIMULATED_VORBIS_AUDIO_DATA_FOR_TESTING"

    result = build_mod_zip(song_name, sections, fake_ogg_bytes)

    assert result.song_name == song_name
    assert result.filename == f"{song_name}.zip"
    assert len(result.zip_bytes) > 0

    # Inspect zip contents
    with zipfile.ZipFile(io.BytesIO(result.zip_bytes), "r") as zf:
        namelist = zf.namelist()
        # Verify package has internal directory structure deployable to ImportedSongs
        assert f"{song_name}/{song_name}.json" in namelist
        assert f"{song_name}/{song_name}.ogg" in namelist

        # Verify JSON can be parsed
        json_data = json.loads(zf.read(f"{song_name}/{song_name}.json").decode("utf-8"))
        assert json_data["songName"] == song_name
        assert json_data["audioFile"] == f"{song_name}.ogg"

        # Verify audio bytes match
        assert zf.read(f"{song_name}/{song_name}.ogg") == fake_ogg_bytes


def test_disk_export_and_io_error_handling(tmp_path: Path):
    """Scenario: Mod export to directory and error handling for invalid destinations."""
    song_name = "Disco_Inferno"
    sections = create_initial_sections(130.0)
    fake_ogg = b"FAKE_OGG_CONTENT"

    # Successful export
    target_dir = tmp_path / "imported_songs" / song_name
    out_dir = export_to_directory(song_name, sections, fake_ogg, target_dir=target_dir)

    assert out_dir.exists()
    assert (out_dir / f"{song_name}.json").exists()
    assert (out_dir / f"{song_name}.ogg").exists()

    # Disk write failure on impossible directory path (e.g. invalid Windows character in path)
    with pytest.raises(ExportIOError):
        invalid_path = "Z:\\non_existent_drive_12345:\\illegal\\folder"
        export_to_directory(song_name, sections, fake_ogg, target_dir=invalid_path)
