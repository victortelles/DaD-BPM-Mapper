# Flag Editor UI Specification

## Purpose
Provides an interactive web interface in Streamlit to visualize audio waveforms, display tempo marker flags, manipulate BeatWarping sections in an editable table, and preview synchronized playback.

## Requirements

### Requirement: Waveform Display with BPM Markers
The UI MUST render the audio amplitude waveform alongside interactive visual flags for each defined tempo section.

#### Scenario: Display waveform with initial markers
- **Given** an analyzed audio track with calculated `bpmSections`
- **When** the waveform view component renders
- **Then** the system MUST display the amplitude envelope plotted against a time axis in seconds
- **And** the system MUST overlay vertical marker lines at each section's `startTime`
- **And** each marker SHOULD display an accompanying label indicating its BPM.

#### Scenario: Rendering long duration audio
- **Given** an audio track exceeding five minutes in length
- **When** the waveform renders
- **Then** the system MUST downsample display points to preserve interactive UI responsiveness.

### Requirement: Editable Marker Table
The UI MUST provide a table allowing users to add, edit, and delete tempo marker flags with automatic continuity recalculation.

#### Scenario: Adding a new BPM marker
- **Given** an active list of `bpmSections`
- **When** the user adds a new marker with a valid `startTime` between existing sections
- **Then** the system MUST insert the marker into the sorted list
- **And** the system MUST recalculate `startBeat` for the new marker and all downstream markers
- **And** the waveform display MUST immediately refresh to reflect the new marker.

#### Scenario: Modifying an existing marker's BPM
- **Given** an editable table with multiple sections
- **When** the user updates the `bpm` value of an intermediate section
- **Then** the system MUST update downstream `startBeat` values according to the BeatWarping formula
- **And** the `startTime` of all sections MUST remain unchanged.

#### Scenario: Deleting a non-root marker
- **Given** a list of three or more markers
- **When** the user deletes an intermediate marker
- **Then** the system MUST remove the marker and recalculate subsequent `startBeat` values.

#### Scenario: Prevention of root marker deletion
- **Given** the root marker at `startTime = 0.0`
- **When** the user attempts to delete the root marker
- **Then** the UI MUST disable or reject the deletion
- **And** the UI MUST display a warning notification that the root marker is mandatory.

#### Scenario: Validation of out-of-order timestamp
- **Given** an edited section where `startTime` violates strict ascending order
- **When** the change is submitted
- **Then** the UI MUST reject the update and display a validation error alert.

### Requirement: Synchronized Audio Preview Player
The UI MUST provide an embedded audio player allowing users to audition the audio against the configured tempo grid.

#### Scenario: Audio playback controls
- **Given** a loaded audio track
- **When** the user interacts with the preview player
- **Then** the system MUST provide standard playback controls (play, pause, seek)
- **And** the system SHOULD indicate current playback position along the waveform.
