# Song Importer Export Specification

## Purpose
Converts source audio to sample-accurate 44.1 kHz `.ogg` format, generates game-compliant BeatWarping JSON metadata, and packages the results into ready-to-use mod archives for *Dead as Disco*.

## Requirements

### Requirement: Audio Transcoding to 44.1 kHz OGG
The system MUST transcode uploaded audio files to Ogg Vorbis format at 44.1 kHz, eliminating encoder padding to prevent synchronization drift.

#### Scenario: Successful MP3 to OGG conversion
- **Given** a valid `.mp3` source file
- **When** the exporter triggers audio transcoding
- **Then** the system MUST invoke `ffmpeg` to produce an `.ogg` file encoded with `libvorbis` at 44,100 Hz
- **And** the transcoded audio MUST preserve zero-offset time alignment relative to the detected beat grid.

#### Scenario: Transcoding failure due to missing FFmpeg
- **Given** a system environment where `ffmpeg` is not installed or not in PATH
- **When** transcoding is initiated
- **Then** the system MUST raise a `DependencyError` with instructions to install `ffmpeg`
- **And** the export process MUST abort cleanly without leaving orphaned temporary files.

#### Scenario: Transcoding execution error
- **Given** a corrupted input file that causes `ffmpeg` to return a non-zero exit code
- **When** transcoding is executed
- **Then** the system MUST raise a `TranscodingError` capturing stderr output from `ffmpeg`.

### Requirement: Dead as Disco BeatWarping JSON Metadata Generation
The system MUST generate a valid JSON metadata file conforming to the *Dead as Disco* BeatWarping schema contract.

#### Scenario: Valid JSON schema output
- **Given** a song title "Neon Pulse" and a list of validated `bpmSections`
- **When** metadata generation is requested
- **Then** the system MUST write a JSON document containing top-level fields `songName`, `audioFile`, and `bpmSections`
- **And** `audioFile` MUST match the generated `.ogg` filename
- **And** each entry in `bpmSections` MUST contain `startTime` (float), `startBeat` (number), and `bpm` (number)
- **And** sections MUST be ordered chronologically by `startTime`.

#### Scenario: Song title sanitization
- **Given** a song name containing filesystem-unsafe characters (e.g., `Rock / Pop: Hit? *`)
- **When** the export filename and JSON metadata are generated
- **Then** the system MUST sanitize the name into a filesystem-safe identifier (e.g., `Rock___Pop__Hit___`)
- **And** both folder name and metadata references MUST use the sanitized identifier consistently.

### Requirement: Mod Package Bundling and Export
The system MUST package the transcoded audio and JSON metadata into a mod structure compatible with the game's import directory.

#### Scenario: ZIP archive bundle generation
- **Given** transcoded `.ogg` audio and generated `.json` metadata
- **When** the user downloads the mod package
- **Then** the system MUST bundle both files into a `.zip` archive named `{song_name}.zip`
- **And** the root of the archive or inner directory MUST be directly deployable to `%localappdata%\Pagoda\Saved\ImportedSongs\{song_name}/`.

#### Scenario: Disk write failure handling
- **Given** a read-only destination directory or insufficient disk space
- **When** package bundling is attempted
- **Then** the system MUST raise an `ExportIOError` and report the issue to the user interface.
