"""Unit tests for Dead as Disco 16-field Meta.json serialization, ZIP bundling, and directory export."""

import io
import json
import zipfile
from pathlib import Path
import pytest

from audio_analysis.bpm_sections import create_initial_sections
from audio_analysis.exceptions import ValidationError
from export.exceptions import ExportIOError
from export.package_builder import (
    build_mod_zip,
    export_to_directory,
    generate_metadata,
    list_imported_songs,
    sanitize_song_name,
)
from models.song_metadata import (
    BPMSection,
    CustomTempoSection,
    SongMetadata,
    native_tempo_to_sections,
    sections_to_native_tempo,
)

EXPECTED_16_KEYS = [
    "version",
    "uniqueId",
    "songName",
    "performedBy",
    "writtenBy",
    "seed",
    "tempo",
    "customTempoSections",
    "beatOffset",
    "startSongOffset",
    "endSongOffset",
    "uEAssetName",
    "originalAudioFileHash",
    "originalAudioFilePath",
    "analyseResult",
    "beatTracks",
]


def test_song_title_sanitization_and_display_name_preservation():
    """Verify folder name sanitization while keeping display songName intact in Meta.json."""
    raw_title = "Rock / Pop: Hit? *"
    assert sanitize_song_name(raw_title) == "Rock___Pop__Hit___"
    assert sanitize_song_name("") == "imported_song"
    assert sanitize_song_name("   ") == "imported_song"
    assert sanitize_song_name("???***///") == "imported_song"
    assert sanitize_song_name("Neon_Pulse_2024") == "Neon_Pulse_2024"

    sections = [BPMSection(startTime=0.0, startBeat=0.0, bpm=128.0)]
    meta = generate_metadata(raw_title, sections)
    assert meta.songName == raw_title
    assert meta.uEAssetName == raw_title


def test_16_field_meta_json_contract_against_templates():
    """Verify exact 16-field schema parity against template-example.json and template2.json."""
    repo_root = Path(__file__).resolve().parent.parent
    t1_path = repo_root / "example-music" / "template-example.json"
    t2_path = repo_root / "example-music" / "template2.json"

    for tpl_path in (t1_path, t2_path):
        raw_text = tpl_path.read_text(encoding="utf-8")
        tpl_dict = json.loads(raw_text)

        assert list(tpl_dict.keys()) == EXPECTED_16_KEYS

        meta = SongMetadata.from_meta_dict(tpl_dict)
        serialized_dict = meta.to_meta_dict()
        assert list(serialized_dict.keys()) == EXPECTED_16_KEYS
        assert serialized_dict == tpl_dict

        json_out = meta.to_meta_json()
        assert "\n\t\"version\": 1," in json_out
        assert json.loads(json_out) == tpl_dict


def test_valid_meta_json_generation_with_custom_tempo_sections():
    """Scenario: Valid Meta.json generation with custom tempo sections and tab indentation."""
    sections = [
        BPMSection(startTime=0.0, startBeat=0.0, bpm=120.0),
        BPMSection(startTime=10.5, startBeat=21.0, bpm=140.0),
        BPMSection(startTime=25.25, startBeat=55.4167, bpm=95.5),
    ]
    fake_flac = b"fLaC\x00\x00\x00\x22_RAW_AUDIO_STREAM"

    meta = generate_metadata(
        "La Cumbia - Bukano",
        sections,
        audio_bytes=fake_flac,
        original_filename="D:/Music/La Cumbia.flac",
        beat_offset_ms=320,
        start_song_offset=0.85,
        end_song_offset=34.02,
        fit_quality=0.92,
        performed_by=["Bukano"],
        written_by=["Bukano"],
        unique_id=27605225,
        seed=2196372576,
    )

    meta_json = meta.to_meta_json()
    assert "\t\"songName\": \"La Cumbia - Bukano\"" in meta_json
    data = json.loads(meta_json)

    assert list(data.keys()) == EXPECTED_16_KEYS
    assert data["version"] == 1
    assert data["uniqueId"] == 27605225
    assert data["seed"] == 2196372576
    assert data["tempo"] == 120
    assert data["beatOffset"] == 320
    assert data["startSongOffset"] == 0.85
    assert data["endSongOffset"] == 34.02
    assert len(data["customTempoSections"]) == 2
    assert data["customTempoSections"][0] == {"tempo": 140, "startAbsoluteTime": 10.5}
    assert data["customTempoSections"][1] == {"tempo": 95.5, "startAbsoluteTime": 25.25}
    assert len(data["originalAudioFileHash"]) == 32
    assert data["analyseResult"]["bAnalyseSuccessful"] is True
    assert data["analyseResult"]["tempo"] == 120
    assert data["analyseResult"]["beatOffset"] == 320


def test_legacy_bpm_sections_migration_and_bridge_helpers():
    """Scenario: Legacy bpmSections migration to native tempo and customTempoSections."""
    legacy_payload = {
        "songName": "Legacy_Track",
        "audioFile": "Legacy_Track.ogg",
        "bpmSections": [
            {"startTime": 0.25, "startBeat": 0.0, "bpm": 125.0},
            {"startTime": 12.0, "startBeat": 24.0, "bpm": 150.0},
        ],
    }
    migrated = SongMetadata.from_meta_dict(legacy_payload)
    assert migrated.songName == "Legacy_Track"
    assert migrated.tempo == 125
    assert migrated.beatOffset == 250
    assert len(migrated.customTempoSections) == 1
    assert migrated.customTempoSections[0].tempo == 150
    assert migrated.customTempoSections[0].startAbsoluteTime == 12.0

    reconstructed = native_tempo_to_sections(migrated.tempo, migrated.customTempoSections)
    assert len(reconstructed) == 2
    assert reconstructed[0].bpm == 125.0
    assert reconstructed[1].startTime == 12.0
    assert reconstructed[1].startBeat == 25.0

    base_t, custom_s = sections_to_native_tempo(reconstructed)
    assert base_t == 125
    assert len(custom_s) == 1


def test_invalid_metadata_or_negative_offset_rejection():
    """Scenario: Invalid metadata or negative offset rejection raises ValidationError."""
    with pytest.raises(ValidationError):
        SongMetadata(songName="", tempo=120)

    with pytest.raises(ValidationError):
        SongMetadata(songName="Valid", tempo=0)

    with pytest.raises(ValidationError):
        SongMetadata(songName="Valid", tempo=-120)

    with pytest.raises(ValidationError):
        SongMetadata(songName="Valid", tempo=120, beatOffset=-10)

    with pytest.raises(ValidationError):
        SongMetadata(
            songName="Valid",
            tempo=120,
            customTempoSections=[
                CustomTempoSection(tempo=140, startAbsoluteTime=20.0),
                CustomTempoSection(tempo=130, startAbsoluteTime=10.0),
            ],
        )


def test_zip_archive_bundle_generation():
    """Scenario: Downloadable ZIP package structure (<SongName>/Meta.json + <SongName>/audio.ogg)."""
    song_name = "Cyber Groove: 2026"
    safe_folder = sanitize_song_name(song_name)
    sections = create_initial_sections(128.0)
    fake_ogg_bytes = b"OggS_SIMULATED_VORBIS_AUDIO_DATA_FOR_TESTING"

    result = build_mod_zip(song_name, sections, fake_ogg_bytes, beat_offset_ms=145)

    assert isinstance(result, bytes)
    assert result.song_name == safe_folder
    assert result.filename == f"{safe_folder}.zip"
    assert len(result.zip_bytes) > 0

    with zipfile.ZipFile(io.BytesIO(result), "r") as zf:
        namelist = zf.namelist()
        assert len(namelist) == 2
        assert f"{safe_folder}/Meta.json" in namelist
        assert f"{safe_folder}/audio.ogg" in namelist

        raw_meta = zf.read(f"{safe_folder}/Meta.json").decode("utf-8")
        assert "\t\"version\": 1" in raw_meta
        json_data = json.loads(raw_meta)
        assert list(json_data.keys()) == EXPECTED_16_KEYS
        assert json_data["songName"] == song_name
        assert json_data["tempo"] == 128
        assert json_data["beatOffset"] == 145
        assert zf.read(f"{safe_folder}/audio.ogg") == fake_ogg_bytes


def test_disk_export_and_imported_songs_discovery(tmp_path: Path):
    """Scenario: Direct export to local Pagoda ImportedSongs directory and song discovery."""
    song_name = "Disco Inferno / Deluxe"
    safe_folder = sanitize_song_name(song_name)
    sections = create_initial_sections(130.0)
    fake_ogg = b"OggS_FAKE_OGG_CONTENT"

    imported_root = tmp_path / "ImportedSongs"
    res = export_to_directory(song_name, sections, fake_ogg, target_dir=imported_root)

    assert res.exists()
    assert res.folder_path == imported_root / safe_folder
    assert res.json_path == imported_root / safe_folder / "Meta.json"
    assert res.ogg_path == imported_root / safe_folder / "audio.ogg"
    assert res.json_path.exists()
    assert res.ogg_path.exists()

    discovered = list_imported_songs(imported_root)
    assert len(discovered) == 1
    folder_name, j_path, o_path = discovered[0]
    assert folder_name == safe_folder
    assert j_path == res.json_path
    assert o_path == res.ogg_path
    assert discovered[0].metadata is not None
    assert discovered[0].metadata.songName == song_name

    with pytest.raises(ExportIOError):
        export_to_directory(song_name, sections, fake_ogg, target_dir="Z:\\non_existent_12345:\\illegal")
