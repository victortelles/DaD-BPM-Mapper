# Proposal: BPM Mapper & Song Importer

## Intent
Enable *Dead as Disco* players and modders to convert raw `.mp3` audio into fully synchronized, game-ready mod packages with dynamic BeatWarping BPM sections through a streamlined web workflow.

## Scope
- **In Scope:**
  - Automated beat detection and dynamic BPM transition tracking.
  - Interactive Streamlit UI with waveform display, audio preview, and manual marker editing.
  - Conversion from `.mp3` to 44.1 kHz `.ogg` via `ffmpeg` to prevent encoder padding offset.
  - Exporting game-compatible BeatWarping JSON and packaged mod folders/ZIP archives.
- **Out of Scope:**
  - In-game mod installation automation or direct process memory injection.
  - Direct audio stem separation, slicing, or audio synthesis.

## Capabilities
### New Capabilities
- `audio-analysis`: Dynamic BPM detection, transient onset tracking using Librosa, and continuous BeatWarping time-to-beat segment calculations (`startTime`, `startBeat`, `bpm`).
- `flag-editor-ui`: Streamlit frontend featuring waveform visualization, synchronized audio preview, and an editable table to add, modify, or delete tempo flags.
- `song-importer-export`: Audio transcoding (`.mp3` -> 44.1 kHz `.ogg`), generation of game-ready BeatWarping JSON metadata, and bundled ZIP/folder export targeting `%localappdata%\Pagoda\Saved\ImportedSongs\`.

### Modified Capabilities
- None (greenfield implementation).

## Approach
Implement a modular Python architecture decoupling analysis from UI:
- `audio_analysis/`: Core algorithms for onset detection, tempo segmentation, and beat mapping.
- `ui/`: Streamlit components for waveform rendering (`matplotlib`/custom), audio playback (`st.audio`), and flag management.
- `models/`: Data classes defining `bpmSections` and song metadata contracts.
- `export/`: Transcoding via `ffmpeg` subprocess calls and archive builder utilities.

## Affected Areas
- `app.py`: Main Streamlit application entry point.
- `audio_analysis/`: Beat detection, warping math, and converter modules.
- `ui/`: Waveform viewer, flag editor table, and preview player.
- `models/`: Pydantic/dataclass schema definitions.
- `export/`: Packaging and archive generators.
- `requirements.txt`: Project dependencies.

## Risks & Rollback Plan
- **Risks:**
  - Beat tracking drift on complex or polyrhythmic tracks (mitigated via manual flag editor).
  - Encoder padding introducing synchronization offsets during `.ogg` conversion (mitigated by strict 44.1 kHz transcoding and sample validation).
  - BeatWarping JSON schema mismatch with game expectations (mitigated by validating against game mod samples).
- **Rollback Plan:** Revert the feature branch or delete generated project directories without affecting existing repository files.

## Dependencies
- Python 3.12, `streamlit`, `librosa`, `numpy`, `matplotlib`, and system `ffmpeg`.

## Success Criteria
- Uploaded `.mp3` successfully analyzes and yields calculated `bpmSections`.
- Users can manually adjust, add, and delete BPM flags in the UI.
- `ffmpeg` produces 44.1 kHz `.ogg` with sample-accurate alignment.
- Generated ZIP package imports cleanly into the game's `ImportedSongs` directory.
