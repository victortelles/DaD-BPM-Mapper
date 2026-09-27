# Design: BPM Mapper & Song Importer

## Technical Approach

The BPM Mapper & Song Importer converts raw `.mp3` audio into *Dead as Disco* mod packages with continuous BeatWarping tempo sections. The architecture decouples compute-intensive signal processing from Streamlit UI rendering and packaging:
- **Audio Analysis (`audio_analysis/`)**: Librosa estimates onset frames and dynamic tempo shifts. Continuous BeatWarping math computes monotonic time-to-beat sections.
- **Interactive UI (`ui/`)**: Streamlit displays downsampled waveforms with marker overlays, manages editable marker tables, and embeds audio preview playback.
- **Export Pipeline (`export/`)**: Direct FFmpeg subprocess calls transcode audio to 44.1 kHz OGG (eliminating MP3 encoder padding), generate BeatWarping JSON metadata, and bundle ZIP archives.

## Architecture Decisions

### Decision: Modular Clean Architecture
- **Choice**: Separate `audio_analysis/`, `ui/`, `export/`, and `models/` packages.
- **Alternatives considered**: Single-script `app.py`.
- **Rationale**: Isolates math and audio algorithms from Streamlit rendering cycles, enabling headless `pytest` execution without launching a web server.

### Decision: Reactive State via `session_state`
- **Choice**: Cache loaded audio, detected flags, and edits in `st.session_state`.
- **Alternatives considered**: Re-running Librosa analysis on each interaction, or database caching.
- **Rationale**: Librosa analysis takes several seconds. Session memory caching ensures instant UI re-renders during marker edits.

### Decision: FFmpeg Subprocess Wrapper
- **Choice**: Execute `ffmpeg` directly via `subprocess.run`.
- **Alternatives considered**: Wrapper libraries (`pydub`, `ffmpeg-python`).
- **Rationale**: Avoids extra dependencies and provides precise control over flags (`-c:a libvorbis -ar 44100`) to strip encoder delay and preserve zero-offset sync.

## Data Flow

```
[ User Upload: .mp3 ]
         │
         ▼
[ app.py (Controller) ]
         ├──→ [ audio_analysis/beat_detection.py ] ── (Librosa tempo tracking)
         │                         │
         │                         ▼
         ├──→ [ audio_analysis/bpm_sections.py ]   ── (Initial BPMSection list)
         │                         │
         ▼                         ▼
[ st.session_state ] ←──→ [ ui/flag_editor.py ]     ── (Marker edits & recalculation)
         │           ←──→ [ ui/waveform_view.py ]   ── (Waveform + marker flags)
         │           ←──→ [ ui/player.py ]          ── (Audio preview playback)
         │
         ▼ (User triggers Export)
[ export/package_builder.py ]
         ├──→ [ audio_analysis/converter.py ] ── (FFmpeg → 44.1 kHz .ogg)
         ├──→ [ models/song_metadata.py ]     ── (JSON BeatWarping schema)
         └──→ [ zipfile / Disk Writer ]       ── (Mod ZIP for ImportedSongs/)
```

## File Changes

| File | Action | Description |
|---|---|---|
| `requirements.txt` | Create | Project dependencies (`streamlit`, `librosa`, `numpy`, `matplotlib`, `pytest`). |
| `app.py` | Create | Streamlit entry point orchestrating state, workflow tabs, and layout. |
| `models/song_metadata.py` | Create | Data contracts: `BPMSection`, `SongMetadata`, and `ExportResult`. |
| `audio_analysis/beat_detection.py` | Create | Librosa onset detection and dynamic BPM section extraction. |
| `audio_analysis/bpm_sections.py` | Create | BeatWarping continuity formulas, marker sorting, and validation. |
| `audio_analysis/converter.py` | Create | FFmpeg subprocess wrapper for 44.1 kHz OGG transcoding. |
| `ui/waveform_view.py` | Create | Waveform envelope renderer with overlay tempo flags. |
| `ui/flag_editor.py` | Create | Editable marker table triggering downstream `startBeat` recalculation. |
| `ui/player.py` | Create | Embedded preview audio player (`st.audio`). |
| `export/package_builder.py` | Create | JSON formatting, song title sanitization, and ZIP bundler. |

## Interfaces / Contracts

```python
from dataclasses import dataclass, asdict
from typing import List

@dataclass
class BPMSection:
    startTime: float  # Seconds (strictly monotonic: T_i > T_{i-1})
    startBeat: float  # Cumulative beats: startBeat_i = startBeat_{i-1} + (T_i - T_{i-1}) * (B_{i-1} / 60)
    bpm: float        # Section tempo (> 0)

@dataclass
class SongMetadata:
    songName: str
    audioFile: str    # e.g., "{songName}.ogg"
    bpmSections: List[BPMSection]

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class ExportResult:
    zip_bytes: bytes
    filename: str
    song_name: str
```

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| **Unit** | `bpm_sections.py` continuity math, monotonic order, negative BPM rejection. | `pytest` parameterized tests with synthetic timestamps and BPM transitions. |
| **Unit** | `package_builder.py` name sanitization and BeatWarping JSON structure. | Contract assertions on serialized JSON keys and filesystem-safe names. |
| **Integration** | `converter.py` FFmpeg execution, missing binary handling, 44.1 kHz output. | Test with short audio fixture; verify exit codes and output sample rate. |
| **Manual UI** | Full user flow: upload, marker adjustment, preview playback, package download. | Browser validation with varying tempo tracks. |

## Migration / Rollout

No migration required. The tool is a standalone client utility operating locally without database dependencies. It outputs self-contained mod packages targeted for `%localappdata%\Pagoda\Saved\ImportedSongs\`.

## Open Questions

- [ ] Confirm exact JSON field names (`startTime` vs `time`, `startBeat` vs `beat`) against a native *Dead as Disco* imported song sample.
- [ ] Verify whether the game engine requires `startBeat` as a float or rounded to nearest integer/subdivision.
