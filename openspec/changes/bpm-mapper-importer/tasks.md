# Tasks: BPM Mapper & Song Importer

## Review Workload Forecast
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: stacked-to-main
400-line budget risk: Medium

## Phase 1: Environment & Data Models
- [x] 1.1 Create `requirements.txt` defining runtime dependencies (`streamlit`, `librosa`, `numpy`, `matplotlib`, `pytest`).
- [x] 1.2 Implement `models/song_metadata.py` defining `BPMSection`, `SongMetadata`, and `ExportResult` dataclasses with dictionary serialization (*BeatWarping Time-to-Beat Section Mapping*, *Dead as Disco BeatWarping JSON Metadata Generation*).

## Phase 2: Audio Analysis & BeatWarping Math
- [x] 2.1 Implement `audio_analysis/converter.py` using `subprocess` for FFmpeg transcoding (`.mp3` to 44.1 kHz `.ogg` via `libvorbis`), handling missing binary `DependencyError` and process `TranscodingError` (*Successful MP3 to OGG conversion*, *Transcoding failure due to missing FFmpeg*, *Transcoding execution error*).
- [x] 2.2 Implement `audio_analysis/bpm_sections.py` with continuous BeatWarping formulas, timestamp sorting, downstream `startBeat` recalculation, and `ValidationError` guards (*Section continuity calculation*, *Recalculation after boundary shift*, *Validation of invalid BPM values*).
- [x] 2.3 Implement `audio_analysis/beat_detection.py` using Librosa for onset frame detection, tempo transitions, constant tempo fallback, and error handling for corrupt input (`AudioProcessingError`) and silence (`InsufficientAudioSignalError`) (*Successful dynamic tempo analysis*, *Constant tempo audio file*, *Corrupted or unreadable audio input*, *Silent or near-silent audio file*).

## Phase 3: Export & Packaging Engine
- [x] 3.1 Implement `export/package_builder.py` with filesystem-safe title sanitization, BeatWarping JSON metadata generation, and mod ZIP bundle packaging targeting `%localappdata%\Pagoda\Saved\ImportedSongs\` with `ExportIOError` handling (*Valid JSON schema output*, *Song title sanitization*, *ZIP archive bundle generation*, *Disk write failure handling*).

## Phase 4: Streamlit UI Components
- [x] 4.1 Implement `ui/player.py` wrapping `st.audio` for auditioning audio with standard playback controls (*Audio playback controls*).
- [x] 4.2 Implement `ui/waveform_view.py` rendering downsampled amplitude envelopes with vertical marker lines and BPM labels (*Display waveform with initial markers*, *Rendering long duration audio*).
- [x] 4.3 Implement `ui/flag_editor.py` providing an editable table for adding, editing, and deleting flags, preventing root marker deletion, validating chronological order, and recalculating downstream beats (*Adding a new BPM marker*, *Modifying an existing marker's BPM*, *Deleting a non-root marker*, *Prevention of root marker deletion*, *Validation of out-of-order timestamp*).
- [x] 4.4 Build `app.py` orchestrating upload flows, `st.session_state` caching, tab navigation, preview controls, and package download triggers.

## Phase 5: Unit Testing & Integration Verification
- [x] 5.1 Implement `tests/test_bpm_sections.py` verifying BeatWarping mathematical continuity, dynamic section updates, and validation error conditions.
- [x] 5.2 Implement `tests/test_converter.py` and `tests/test_package_builder.py` verifying FFmpeg call handling, title sanitization, JSON schema compliance, and archive structure.
- [x] 5.3 Perform end-to-end interactive verification in Streamlit covering `.mp3` loading, marker editing, preview playback, and mod package export.
