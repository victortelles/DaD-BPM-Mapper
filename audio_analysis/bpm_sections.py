"""BeatWarping mathematical continuity formulas, sorting, and validation for BPM sections."""

from typing import List, Optional
import copy
from models.song_metadata import BPMSection
from .exceptions import ValidationError


def validate_sections(sections: List[BPMSection]) -> None:
    """Validate that the given list of BPMSections conforms to BeatWarping invariants.
    
    Invariants:
    1. Must contain at least one section.
    2. The first section must start at startTime == 0.0.
    3. Every section must have bpm > 0.
    4. Every section must have startTime >= 0.0.
    5. Start times must be strictly monotonically increasing (T_i > T_{i-1}).
    
    Raises:
        ValidationError: If any invariant is violated.
    """
    if not sections:
        raise ValidationError("Sections list cannot be empty.")

    first = sections[0]
    if first.startTime < 0.0:
        raise ValidationError(f"Invalid startTime {first.startTime}; must be non-negative.")
    if abs(first.startTime) > 1e-6:
        raise ValidationError(f"Root section must start at 0.0 seconds, got {first.startTime}.")
    if first.bpm <= 0:
        raise ValidationError(f"Invalid BPM {first.bpm}; must be greater than zero.")

    for i in range(1, len(sections)):
        curr = sections[i]
        prev = sections[i - 1]

        if curr.bpm <= 0:
            raise ValidationError(f"Invalid BPM {curr.bpm} at index {i}; must be greater than zero.")
        if curr.startTime < 0.0:
            raise ValidationError(f"Invalid startTime {curr.startTime} at index {i}; must be non-negative.")
        if curr.startTime <= prev.startTime + 1e-6:
            raise ValidationError(
                f"StartTime must be strictly monotonically increasing. "
                f"Section {i} ({curr.startTime}s) is not greater than section {i-1} ({prev.startTime}s)."
            )


def recalculate_beats(sections: List[BPMSection]) -> List[BPMSection]:
    """Recalculate cumulative startBeat for each section based on BeatWarping continuity.
    
    Formula:
        startBeat[0] = 0.0
        startBeat[i] = startBeat[i-1] + (startTime[i] - startTime[i-1]) * (bpm[i-1] / 60.0)
        
    Args:
        sections: List of BPMSection objects, ordered chronologically.
        
    Returns:
        A new list of BPMSection with recalculated startBeat values.
        
    Raises:
        ValidationError: If validation fails.
    """
    if not sections:
        raise ValidationError("Cannot calculate beats for an empty sections list.")

    # Sort sections by startTime to ensure chronological order
    sorted_sections = sorted(sections, key=lambda s: s.startTime)
    validate_sections(sorted_sections)

    recalculated: List[BPMSection] = []
    current_beat = 0.0

    for i, sec in enumerate(sorted_sections):
        if i == 0:
            recalculated.append(
                BPMSection(
                    startTime=0.0,
                    startBeat=0.0,
                    bpm=float(sec.bpm),
                )
            )
        else:
            prev_sec = recalculated[i - 1]
            time_delta = sec.startTime - prev_sec.startTime
            beat_increment = time_delta * (prev_sec.bpm / 60.0)
            current_beat = prev_sec.startBeat + beat_increment
            recalculated.append(
                BPMSection(
                    startTime=float(sec.startTime),
                    startBeat=float(current_beat),
                    bpm=float(sec.bpm),
                )
            )

    return recalculated


def add_marker(sections: List[BPMSection], start_time: float, bpm: float) -> List[BPMSection]:
    """Add a new tempo marker flag and recalculate downstream beats.
    
    Args:
        sections: Current list of BPMSections.
        start_time: Time offset in seconds where the new tempo begins (must be > 0.0).
        bpm: Tempo value in beats per minute (must be > 0.0).
        
    Returns:
        Updated and recalculated list of BPMSections.
        
    Raises:
        ValidationError: If parameters are invalid or start_time collides with an existing marker.
    """
    if bpm <= 0:
        raise ValidationError(f"BPM must be greater than zero, got {bpm}.")
    if start_time <= 0.0:
        raise ValidationError(f"New marker startTime must be greater than 0.0, got {start_time}.")

    for sec in sections:
        if abs(sec.startTime - start_time) < 1e-4:
            raise ValidationError(f"A marker already exists near {start_time:.3f}s.")

    new_list = [copy.deepcopy(s) for s in sections]
    new_list.append(BPMSection(startTime=start_time, startBeat=0.0, bpm=bpm))
    new_list.sort(key=lambda s: s.startTime)
    return recalculate_beats(new_list)


def update_marker(
    sections: List[BPMSection],
    index: int,
    new_start_time: Optional[float] = None,
    new_bpm: Optional[float] = None,
) -> List[BPMSection]:
    """Update an existing marker's startTime and/or BPM, recalculating downstream beats.
    
    Args:
        sections: Current list of BPMSections.
        index: Index of the marker to update.
        new_start_time: Optional new start time in seconds.
        new_bpm: Optional new tempo value.
        
    Returns:
        Updated and recalculated list of BPMSections.
        
    Raises:
        ValidationError: If index is out of bounds, invalid values are given,
                         or timestamp order is violated.
    """
    if index < 0 or index >= len(sections):
        raise ValidationError(f"Marker index {index} out of range (total: {len(sections)}).")

    new_list = [copy.deepcopy(s) for s in sections]
    target = new_list[index]

    if new_start_time is not None:
        if index == 0 and abs(new_start_time) > 1e-6:
            raise ValidationError("Root marker startTime must remain at 0.0.")
        if new_start_time < 0.0:
            raise ValidationError(f"startTime cannot be negative: {new_start_time}")
        target.startTime = new_start_time

    if new_bpm is not None:
        if new_bpm <= 0:
            raise ValidationError(f"BPM must be greater than zero: {new_bpm}")
        target.bpm = new_bpm

    # Check that sorting order is preserved or validate strictly
    for i in range(1, len(new_list)):
        if new_list[i].startTime <= new_list[i - 1].startTime:
            raise ValidationError(
                f"Updated startTime {new_list[i].startTime} violates strictly ascending chronological order."
            )

    return recalculate_beats(new_list)


def delete_marker(sections: List[BPMSection], index: int) -> List[BPMSection]:
    """Delete a non-root tempo marker and recalculate subsequent startBeat values.
    
    Args:
        sections: Current list of BPMSections.
        index: Index of marker to delete (index > 0).
        
    Returns:
        Updated and recalculated list of BPMSections.
        
    Raises:
        ValidationError: If index is 0 (root marker) or out of bounds.
    """
    if index == 0:
        raise ValidationError("Root marker at startTime 0.0 is mandatory and cannot be deleted.")
    if index < 0 or index >= len(sections):
        raise ValidationError(f"Marker index {index} out of range (total: {len(sections)}).")

    new_list = [copy.deepcopy(s) for i, s in enumerate(sections) if i != index]
    return recalculate_beats(new_list)


def create_initial_sections(bpm: float) -> List[BPMSection]:
    """Create a default root BPMSection for a track with a known BPM.
    
    Args:
        bpm: Track tempo in beats per minute (must be > 0.0).
        
    Returns:
        A list with a single root BPMSection.
        
    Raises:
        ValidationError: If bpm <= 0.
    """
    if bpm <= 0:
        raise ValidationError(f"BPM must be greater than zero, got {bpm}.")
    return [BPMSection(startTime=0.0, startBeat=0.0, bpm=float(bpm))]
