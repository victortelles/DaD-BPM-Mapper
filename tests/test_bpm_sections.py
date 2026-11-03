"""Unit tests for BeatWarping BPM sections continuity math, validation, and customTempoSections bridges."""

import pytest
from audio_analysis.bpm_sections import (
    CustomTempoSection,
    add_marker,
    create_initial_sections,
    custom_tempo_to_sections,
    delete_marker,
    native_tempo_to_sections,
    recalculate_beats,
    sections_to_custom_tempo,
    sections_to_native_tempo,
    update_marker,
    validate_sections,
)
from audio_analysis.exceptions import ValidationError
from models.song_metadata import BPMSection


def test_initial_section_creation():
    """Verify creating a root initial section at 0.0s with positive tempo."""
    sections = create_initial_sections(120.0)
    assert len(sections) == 1
    assert sections[0].startTime == 0.0
    assert sections[0].startBeat == 0.0
    assert sections[0].bpm == 120.0

    with pytest.raises(ValidationError):
        create_initial_sections(0.0)

    with pytest.raises(ValidationError):
        create_initial_sections(-10.0)


def test_section_continuity_calculation():
    """Scenario: Section continuity calculation."""
    raw_sections = [
        BPMSection(startTime=0.0, startBeat=0.0, bpm=60.0),
        BPMSection(startTime=10.0, startBeat=0.0, bpm=120.0),
        BPMSection(startTime=20.0, startBeat=0.0, bpm=180.0),
    ]
    recalculated = recalculate_beats(raw_sections)

    assert len(recalculated) == 3
    assert recalculated[0].startTime == 0.0
    assert pytest.approx(recalculated[0].startBeat, 1e-4) == 0.0
    assert recalculated[0].bpm == 60.0

    assert recalculated[1].startTime == 10.0
    assert pytest.approx(recalculated[1].startBeat, 1e-4) == 10.0
    assert recalculated[1].bpm == 120.0

    assert recalculated[2].startTime == 20.0
    assert pytest.approx(recalculated[2].startBeat, 1e-4) == 30.0
    assert recalculated[2].bpm == 180.0


def test_recalculation_after_boundary_shift():
    """Scenario: Recalculation after boundary shift."""
    initial_sections = [
        BPMSection(startTime=0.0, startBeat=0.0, bpm=120.0),
        BPMSection(startTime=10.0, startBeat=20.0, bpm=120.0),
        BPMSection(startTime=20.0, startBeat=40.0, bpm=120.0),
    ]

    shifted_time = update_marker(initial_sections, index=1, new_start_time=15.0)
    assert shifted_time[0].startBeat == 0.0
    assert pytest.approx(shifted_time[1].startBeat, 1e-4) == 30.0
    assert pytest.approx(shifted_time[2].startBeat, 1e-4) == 40.0

    shifted_bpm = update_marker(initial_sections, index=1, new_bpm=60.0)
    assert shifted_bpm[0].startBeat == 0.0
    assert pytest.approx(shifted_bpm[1].startBeat, 1e-4) == 20.0
    assert pytest.approx(shifted_bpm[2].startBeat, 1e-4) == 30.0


def test_add_new_marker():
    """Scenario: Adding a new BPM marker between existing sections."""
    sections = [
        BPMSection(startTime=0.0, startBeat=0.0, bpm=120.0),
        BPMSection(startTime=20.0, startBeat=40.0, bpm=120.0),
    ]

    updated = add_marker(sections, start_time=10.0, bpm=60.0)
    assert len(updated) == 3
    assert updated[1].startTime == 10.0
    assert pytest.approx(updated[1].startBeat, 1e-4) == 20.0
    assert updated[1].bpm == 60.0
    assert pytest.approx(updated[2].startBeat, 1e-4) == 30.0


def test_delete_non_root_marker():
    """Scenario: Deleting a non-root marker."""
    sections = [
        BPMSection(startTime=0.0, startBeat=0.0, bpm=120.0),
        BPMSection(startTime=10.0, startBeat=20.0, bpm=60.0),
        BPMSection(startTime=20.0, startBeat=30.0, bpm=120.0),
    ]
    updated = delete_marker(sections, index=1)
    assert len(updated) == 2
    assert updated[0].startTime == 0.0
    assert updated[1].startTime == 20.0
    assert pytest.approx(updated[1].startBeat, 1e-4) == 40.0


def test_prevention_of_root_marker_deletion():
    """Scenario: Prevention of root marker deletion."""
    sections = [
        BPMSection(startTime=0.0, startBeat=0.0, bpm=120.0),
        BPMSection(startTime=15.0, startBeat=30.0, bpm=140.0),
    ]
    with pytest.raises(ValidationError, match="Root marker at startTime 0.0 is mandatory"):
        delete_marker(sections, index=0)


def test_validation_of_invalid_bpm_and_timestamps():
    """Scenario: Validation of invalid BPM values and out-of-order timestamps."""
    with pytest.raises(ValidationError):
        validate_sections([BPMSection(startTime=0.0, startBeat=0.0, bpm=-120.0)])

    with pytest.raises(ValidationError):
        validate_sections([BPMSection(startTime=0.0, startBeat=0.0, bpm=0.0)])

    with pytest.raises(ValidationError):
        validate_sections([BPMSection(startTime=1.5, startBeat=0.0, bpm=120.0)])

    with pytest.raises(ValidationError):
        validate_sections([
            BPMSection(startTime=0.0, startBeat=0.0, bpm=120.0),
            BPMSection(startTime=-5.0, startBeat=0.0, bpm=120.0),
        ])

    with pytest.raises(ValidationError):
        validate_sections([
            BPMSection(startTime=0.0, startBeat=0.0, bpm=120.0),
            BPMSection(startTime=10.0, startBeat=20.0, bpm=120.0),
            BPMSection(startTime=8.0, startBeat=0.0, bpm=120.0),
        ])

    base = [BPMSection(startTime=0.0, startBeat=0.0, bpm=120.0)]
    with pytest.raises(ValidationError):
        update_marker(base, index=0, new_start_time=2.0)


def test_native_tempo_and_custom_tempo_sections_bridge():
    """Scenario: Round-trip conversion between List[BPMSection] and (tempo, List[CustomTempoSection])."""
    sections = recalculate_beats([
        BPMSection(startTime=0.0, startBeat=0.0, bpm=118.0),
        BPMSection(startTime=12.5, startBeat=0.0, bpm=140.5),
        BPMSection(startTime=32.0, startBeat=0.0, bpm=160.0),
    ])

    base_tempo, custom_secs = sections_to_native_tempo(sections)
    assert base_tempo == 118
    assert len(custom_secs) == 2
    assert custom_secs[0] == CustomTempoSection(tempo=140.5, startAbsoluteTime=12.5)
    assert custom_secs[1] == CustomTempoSection(tempo=160, startAbsoluteTime=32.0)

    roundtrip = native_tempo_to_sections(base_tempo, custom_secs)
    assert len(roundtrip) == 3
    for orig, conv in zip(sections, roundtrip):
        assert pytest.approx(conv.startTime, 1e-4) == orig.startTime
        assert pytest.approx(conv.startBeat, 1e-4) == orig.startBeat
        assert pytest.approx(conv.bpm, 1e-4) == orig.bpm

    alias_tempo, alias_custom = sections_to_custom_tempo(sections)
    assert alias_tempo == base_tempo
    assert custom_tempo_to_sections(alias_tempo, alias_custom) == roundtrip

    with pytest.raises(ValidationError):
        sections_to_native_tempo([])
    with pytest.raises(ValidationError):
        native_tempo_to_sections(0.0, [])


def test_format_seconds_to_min_sec():
    """Verify conversion from float seconds to MM:SS.sss formatted strings."""
    from ui.flag_editor import format_seconds_to_min_sec

    assert format_seconds_to_min_sec(0.0) == "00:00.000"
    assert format_seconds_to_min_sec(9.5) == "00:09.500"
    assert format_seconds_to_min_sec(65.432) == "01:05.432"
    assert format_seconds_to_min_sec(125.0) == "02:05.000"
    assert format_seconds_to_min_sec(-10.0) == "00:00.000"
