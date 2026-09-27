"""Data models for BPM sections and song metadata."""

from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any
import json


@dataclass
class BPMSection:
    """Represents a tempo section within a track.
    
    Attributes:
        startTime: Start offset of this section in seconds (strictly monotonic T_i > T_{i-1}).
        startBeat: Cumulative beat count from track start at startTime.
        bpm: Beats per minute for this section (bpm > 0).
    """
    startTime: float
    startBeat: float
    bpm: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "startTime": round(float(self.startTime), 4),
            "startBeat": round(float(self.startBeat), 4),
            "bpm": round(float(self.bpm), 3),
        }


@dataclass
class SongMetadata:
    """Dead as Disco BeatWarping metadata container.
    
    Attributes:
        songName: Identifier or display title of the song.
        audioFile: Target audio filename (e.g. "{songName}.ogg").
        bpmSections: Chronologically ordered list of BPMSection definitions.
    """
    songName: str
    audioFile: str
    bpmSections: List[BPMSection] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "songName": self.songName,
            "audioFile": self.audioFile,
            "bpmSections": [s.to_dict() for s in self.bpmSections],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SongMetadata":
        sections = [
            BPMSection(
                startTime=float(s["startTime"]),
                startBeat=float(s["startBeat"]),
                bpm=float(s["bpm"]),
            )
            for s in data.get("bpmSections", [])
        ]
        return cls(
            songName=data["songName"],
            audioFile=data["audioFile"],
            bpmSections=sections,
        )


@dataclass
class ExportResult:
    """Container for generated export package.
    
    Attributes:
        zip_bytes: Raw binary bytes of the compressed mod bundle ZIP.
        filename: Destination ZIP filename (e.g. "{sanitized_song_name}.zip").
        song_name: Sanitized song identifier used for packaging.
    """
    zip_bytes: bytes
    filename: str
    song_name: str
