# Audio Analysis Specification

## Purpose
Provides automated beat tracking, transient onset detection, dynamic tempo estimation, and continuous BeatWarping time-to-beat section mapping for rhythmic audio files.

## Requirements

### Requirement: Beat Tracking and Dynamic Tempo Estimation
The system MUST analyze input audio files and compute musical onset events, beat positions, and local tempo variations.

#### Scenario: Successful dynamic tempo analysis
- **Given** a valid stereo or mono audio file with varying tempo
- **When** the audio analysis pipeline processes the file
- **Then** the system MUST detect beat frames and estimate local BPM values across all distinct rhythmic sections
- **And** the system SHALL return a chronological sequence of detected tempo transitions.

#### Scenario: Constant tempo audio file
- **Given** an audio file with a fixed tempo throughout
- **When** the audio analysis pipeline processes the file
- **Then** the system MUST return a single detected BPM section spanning the audio duration.

#### Scenario: Corrupted or unreadable audio input
- **Given** an unreadable, corrupted, or non-audio file
- **When** the analysis pipeline attempts decoding
- **Then** the system MUST raise an `AudioProcessingError` with a clear diagnostic message
- **And** the system SHALL NOT produce partial or invalid tempo data.

#### Scenario: Silent or near-silent audio file
- **Given** an audio file containing only silence or signal below -60 dBFS
- **When** beat tracking is executed
- **Then** the system MUST raise an `InsufficientAudioSignalError` indicating no rhythmic transients were found.

### Requirement: BeatWarping Time-to-Beat Section Mapping
The system MUST calculate continuous BeatWarping sections (`bpmSections`) ensuring mathematical continuity between time offsets and beat counters.

#### Scenario: Section continuity calculation
- **Given** a sequence of tempo transitions at timestamps $T_0, T_1, \dots, T_n$ with tempos $B_0, B_1, \dots, B_n$
- **When** `bpmSections` are generated
- **Then** the first section MUST have `startTime = 0.0` and `startBeat = 0.0`
- **And** for each subsequent section $i$, `startBeat[i]` MUST satisfy:
  $$\text{startBeat}_i = \text{startBeat}_{i-1} + (T_i - T_{i-1}) \times \frac{B_{i-1}}{60.0}$$
- **And** all `startTime` values MUST be strictly monotonically increasing ($T_i > T_{i-1}$).

#### Scenario: Recalculation after boundary shift
- **Given** an existing valid sequence of three `bpmSections`
- **When** the `startTime` or `bpm` of the second section is modified
- **Then** the system MUST recalculate `startBeat` for all subsequent sections
- **And** the `startBeat` of the first section MUST remain unchanged at 0.0.

#### Scenario: Validation of invalid BPM values
- **Given** a proposed section with `bpm <= 0` or `startTime < 0.0`
- **When** section validation is invoked
- **Then** the system MUST reject the section and raise a `ValidationError`.
