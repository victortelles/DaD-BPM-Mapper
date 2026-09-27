"""Unit tests for BeatWarping BPM sections continuity math and validation."""

import pytest
from audio_analysis.bpm_sections import (
    add_marker,
    create_initial_sections,
    delete_marker,
    recalculate_beats,
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
    """Scenario: Section continuity calculation.
    
    Given transitions at T0=0.0s (B0=60), T1=10.0s (B1=120), T2=20.0s (B2=180):
    startBeat[0] = 0.0
    startBeat[1] = 0.0 + (10.0 - 0.0) * (60 / 60) = 10.0
    startBeat[2] = 10.0 + (20.0 - 10.0) * (120 / 60) = 10.0 + 20.0 = 30.0
    """
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
    """Scenario: Recalculation after boundary shift.
    
    When startTime or BPM of section 1 changes:
    - startBeat of section 0 remains 0.0.
    - Subsequent startBeats adjust according to BeatWarping formula.
    """
    initial_sections = [
        BPMSection(startTime=0.0, startBeat=0.0, bpm=120.0),
        BPMSection(startTime=10.0, startBeat=20.0, bpm=120.0),
        BPMSection(startTime=20.0, startBeat=40.0, bpm=120.0),
    ]

    # Shift section 1 startTime from 10.0 to 15.0
    shifted_time = update_marker(initial_sections, index=1, new_start_time=15.0)
    assert shifted_time[0].startBeat == 0.0
    # From 0s to 15s at 120 BPM: 15 * (120/60) = 30 beats
    assert pytest.approx(shifted_time[1].startBeat, 1e-4) == 30.0
    # From 15s to 20s at 120 BPM: 30 + 5 * (120/60) = 40 beats
    assert pytest.approx(shifted_time[2].startBeat, 1e-4) == 40.0

    # Modify section 1 BPM from 120 to 60
    shifted_bpm = update_marker(initial_sections, index=1, new_bpm=60.0)
    assert shifted_bpm[0].startBeat == 0.0
    assert pytest.approx(shifted_bpm[1].startBeat, 1e-4) == 20.0  # 10s at 120 BPM
    # Section 2 starts at 20s: 20 + (20 - 10) * (60 / 60) = 30 beats
    assert pytest.approx(shifted_bpm[2].startBeat, 1e-4) == 30.0


def test_add_new_marker():
    """Scenario: Adding a new BPM marker between existing sections."""
    sections = [
        BPMSection(startTime=0.0, startBeat=0.0, bpm=120.0),
        BPMSection(startTime=20.0, startBeat=40.0, bpm=120.0),
    ]

    # Insert at 10.0s with 60 BPM
    updated = add_marker(sections, start_time=10.0, bpm=60.0)
    assert len(updated) == 3
    assert updated[1].startTime == 10.0
    assert pytest.approx(updated[1].startBeat, 1e-4) == 20.0
    assert updated[1].bpm == 60.0
    # At 20.0s: 20 + 10 * (60/60) = 30.0
    assert pytest.approx(updated[2].startBeat, 1e-4) == 30.0


def test_delete_non_root_marker():
    """Scenario: Deleting a non-root marker."""
    sections = [
        BPMSection(startTime=0.0, startBeat=0.0, bpm=120.0),
        BPMSection(startTime=10.0, startBeat=20.0, bpm=60.0),
        BPMSection(startTime=20.0, startBeat=30.0, bpm=120.0),
    ]
    # Delete index 1
    updated = delete_marker(sections, index=1)
    assert len(updated) == 2
    assert updated[0].startTime == 0.0
    assert updated[1].startTime == 20.0
    # Section 1 at 20s now uses section 0's 120 BPM: 20 * (120/60) = 40.0 beats
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
    # Negative BPM
    with pytest.raises(ValidationError):
        validate_sections([BPMSection(startTime=0.0, startBeat=0.0, bpm=-120.0)])

    # Zero BPM
    with pytest.raises(ValidationError):
        validate_sections([BPMSection(startTime=0.0, startBeat=0.0, bpm=0.0)])

    # Non-zero root start time
    with pytest.raises(ValidationError):
        validate_sections([BPMSection(startTime=1.5, startBeat=0.0, bpm=120.0)])

    # Negative start time
    with pytest.raises(ValidationError):
        validate_sections([
            BPMSection(startTime=0.0, startBeat=0.0, bpm=120.0),
            BPMSection(startTime=-5.0, startBeat=0.0, bpm=120.0),
        ])

    # Out of order timestamps (T1 <= T0)
    with pytest.raises(ValidationError):
        validate_sections([
            BPMSection(startTime=0.0, startBeat=0.0, bpm=120.0),
            BPMSection(startTime=10.0, startBeat=20.0, bpm=120.0),
            BPMSection(startTime=8.0, startBeat=0.0, bpm=120.0),
        ])

    # Updating root marker start time away from 0.0
    base = [BPMSection(startTime=0.0, startBeat=0.0, bpm=120.0)]
    with pytest.raises(ValidationError):
        update_marker(base, index=0, new_start_time=2.0)
