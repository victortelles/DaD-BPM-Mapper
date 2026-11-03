"""Data models for Dead as Disco native Meta.json packaging and BeatWarping sections."""

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


def _clean_number(val: Union[int, float]) -> Union[int, float]:
    if isinstance(val, int) and not isinstance(val, bool):
        return val
    fval = float(val)
    return int(fval) if fval.is_integer() else fval


@dataclass
class BPMSection:
    startTime: float
    startBeat: float
    bpm: float

    def to_dict(self) -> Dict[str, Any]:
        return {"startTime": round(float(self.startTime), 4), "startBeat": round(float(self.startBeat), 4), "bpm": round(float(self.bpm), 3)}


@dataclass
class CustomTempoSection:
    tempo: Union[float, int]
    startAbsoluteTime: float

    def to_dict(self) -> Dict[str, Any]:
        return {"tempo": _clean_number(self.tempo), "startAbsoluteTime": float(self.startAbsoluteTime)}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CustomTempoSection":
        return cls(tempo=_clean_number(data["tempo"]), startAbsoluteTime=float(data["startAbsoluteTime"]))


@dataclass
class ErrorCode:
    code: int = 0
    messageKey: str = "None"
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"code": int(self.code), "messageKey": str(self.messageKey), "message": str(self.message)}

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "ErrorCode":
        if not data:
            return cls()
        return cls(int(data.get("code", 0)), str(data.get("messageKey", "None")), str(data.get("message", "")))


@dataclass
class AnalyseResult:
    bAnalyseSuccessful: bool = True
    bFoundTempo: bool = True
    bFoundOffset: bool = True
    tempo: Union[float, int] = 120
    beatOffset: Union[int, float] = 0
    fitQuality: float = 0.92
    errorCode: ErrorCode = field(default_factory=ErrorCode)

    def to_dict(self) -> Dict[str, Any]:
        err = self.errorCode if isinstance(self.errorCode, ErrorCode) else ErrorCode.from_dict(self.errorCode)
        return {
            "bAnalyseSuccessful": bool(self.bAnalyseSuccessful), "bFoundTempo": bool(self.bFoundTempo),
            "bFoundOffset": bool(self.bFoundOffset), "tempo": _clean_number(self.tempo),
            "beatOffset": _clean_number(self.beatOffset), "fitQuality": float(self.fitQuality),
            "errorCode": err.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "AnalyseResult":
        if not data:
            return cls()
        return cls(
            bAnalyseSuccessful=bool(data.get("bAnalyseSuccessful", True)),
            bFoundTempo=bool(data.get("bFoundTempo", True)),
            bFoundOffset=bool(data.get("bFoundOffset", True)),
            tempo=_clean_number(data.get("tempo", 120)),
            beatOffset=_clean_number(data.get("beatOffset", 0)),
            fitQuality=float(data.get("fitQuality", 0.92)),
            errorCode=ErrorCode.from_dict(data.get("errorCode")),
        )


from audio_analysis.exceptions import ValidationError


def sections_to_native_tempo(bpm_sections: List[BPMSection]) -> Tuple[Union[float, int], List[CustomTempoSection]]:
    if not bpm_sections:
        raise ValidationError("bpm_sections cannot be empty.")
    for idx, sec in enumerate(bpm_sections):
        if float(sec.bpm) <= 0 or float(sec.startTime) < 0:
            raise ValidationError(f"Invalid BPMSection at index {idx}: bpm={sec.bpm}, startTime={sec.startTime}.")
        if idx > 0 and float(sec.startTime) <= float(bpm_sections[idx - 1].startTime):
            raise ValidationError("BPMSections must have strictly increasing startTime values.")
    return _clean_number(bpm_sections[0].bpm), [CustomTempoSection(_clean_number(s.bpm), float(s.startTime)) for s in bpm_sections[1:]]


def native_tempo_to_sections(base_tempo: float, custom_sections: List[CustomTempoSection]) -> List[BPMSection]:
    if float(base_tempo) <= 0:
        raise ValidationError(f"base_tempo must be > 0, got {base_tempo}.")
    sections: List[BPMSection] = [BPMSection(startTime=0.0, startBeat=0.0, bpm=float(base_tempo))]
    for idx, cs in enumerate(custom_sections):
        curr_t, curr_bpm = float(cs.startAbsoluteTime), float(cs.tempo)
        if curr_bpm <= 0 or curr_t <= sections[-1].startTime:
            raise ValidationError(f"Invalid customTempoSection at index {idx}: tempo={curr_bpm}, time={curr_t}.")
        prev = sections[-1]
        sections.append(BPMSection(curr_t, prev.startBeat + (curr_t - prev.startTime) * (prev.bpm / 60.0), curr_bpm))
    return sections


sections_to_custom_tempo = sections_to_native_tempo
custom_tempo_to_sections = native_tempo_to_sections


@dataclass
class SongMetadata:
    version: int = 1
    uniqueId: int = 0
    songName: str = "imported_song"
    performedBy: List[str] = field(default_factory=list)
    writtenBy: List[str] = field(default_factory=list)
    seed: int = 0
    tempo: Union[float, int] = 120
    customTempoSections: List[CustomTempoSection] = field(default_factory=list)
    beatOffset: Union[int, float] = 0
    startSongOffset: Union[float, int] = 0
    endSongOffset: Union[float, int] = 0
    uEAssetName: str = ""
    originalAudioFileHash: str = ""
    originalAudioFilePath: str = ""
    analyseResult: Optional[AnalyseResult] = None
    beatTracks: List[Any] = field(default_factory=list)
    audioFile: str = field(default="audio.ogg", repr=False, compare=False)
    bpmSections: Optional[List[BPMSection]] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.customTempoSections = [CustomTempoSection.from_dict(c) if isinstance(c, dict) else c for c in (self.customTempoSections or [])]
        if self.bpmSections is not None:
            if not self.bpmSections:
                raise ValidationError("bpmSections cannot be empty.")
            if self.bpmSections[0].startTime > 0 and self.beatOffset == 0:
                self.beatOffset = _clean_number(round(self.bpmSections[0].startTime * 1000.0))
            self.tempo, self.customTempoSections = sections_to_native_tempo(self.bpmSections)
        else:
            self.bpmSections = native_tempo_to_sections(float(self.tempo), self.customTempoSections)
        self.uEAssetName = self.uEAssetName or self.songName
        if not self.originalAudioFileHash and self.songName:
            self.originalAudioFileHash = hashlib.md5(self.songName.encode("utf-8")).hexdigest()
        self.originalAudioFilePath = self.originalAudioFilePath or self.audioFile or "audio.ogg"
        if self.analyseResult is None:
            self.analyseResult = AnalyseResult(tempo=_clean_number(self.tempo), beatOffset=_clean_number(self.beatOffset))
        elif isinstance(self.analyseResult, dict):
            self.analyseResult = AnalyseResult.from_dict(self.analyseResult)
        self.validate()

    def validate(self) -> None:
        if not self.songName or not str(self.songName).strip():
            raise ValidationError("songName cannot be empty.")
        if self.tempo is None or float(self.tempo) <= 0:
            raise ValidationError(f"tempo must be > 0, got {self.tempo}.")
        if self.beatOffset is None or float(self.beatOffset) < 0:
            raise ValidationError(f"beatOffset must be >= 0, got {self.beatOffset}.")
        if float(self.startSongOffset) < 0 or float(self.endSongOffset) < 0:
            raise ValidationError("startSongOffset and endSongOffset must be >= 0.")
        prev_t = 0.0
        for idx, sec in enumerate(self.customTempoSections):
            if float(sec.tempo) <= 0 or float(sec.startAbsoluteTime) <= prev_t:
                raise ValidationError(f"Invalid customTempoSection at index {idx}.")
            prev_t = float(sec.startAbsoluteTime)

    def to_meta_dict(self) -> Dict[str, Any]:
        self.validate()
        analyse_obj = self.analyseResult or AnalyseResult(tempo=_clean_number(self.tempo), beatOffset=_clean_number(self.beatOffset))
        return {
            "version": int(self.version), "uniqueId": int(self.uniqueId), "songName": str(self.songName),
            "performedBy": list(self.performedBy), "writtenBy": list(self.writtenBy), "seed": int(self.seed),
            "tempo": _clean_number(self.tempo), "customTempoSections": [s.to_dict() for s in self.customTempoSections],
            "beatOffset": _clean_number(self.beatOffset), "startSongOffset": _clean_number(self.startSongOffset),
            "endSongOffset": _clean_number(self.endSongOffset), "uEAssetName": str(self.uEAssetName or self.songName),
            "originalAudioFileHash": str(self.originalAudioFileHash), "originalAudioFilePath": str(self.originalAudioFilePath),
            "analyseResult": analyse_obj.to_dict(), "beatTracks": list(self.beatTracks),
        }

    def to_meta_json(self, indent: Union[str, int] = "\t") -> str:
        return json.dumps(self.to_meta_dict(), indent=indent, ensure_ascii=False)

    to_dict = to_meta_dict
    to_json = to_meta_json

    @classmethod
    def from_meta_dict(cls, data: Dict[str, Any]) -> "SongMetadata":
        if not isinstance(data, dict):
            raise ValidationError("Metadata input must be a dictionary.")
        if "bpmSections" in data and "tempo" not in data:
            raw_secs = data.get("bpmSections", [])
            if not raw_secs:
                raise ValidationError("Legacy bpmSections list cannot be empty.")
            parsed = [BPMSection(float(s["startTime"]), float(s.get("startBeat", 0.0)), float(s["bpm"])) for s in raw_secs]
            base_tempo, custom_secs = sections_to_native_tempo(parsed)
            first_offset_ms = _clean_number(round(max(0.0, parsed[0].startTime) * 1000.0))
            song_name, audio_file = str(data.get("songName", "")).strip(), str(data.get("audioFile", "audio.ogg"))
            return cls(
                songName=song_name, tempo=base_tempo, customTempoSections=custom_secs,
                beatOffset=_clean_number(data.get("beatOffset", first_offset_ms)), uEAssetName=str(data.get("uEAssetName", song_name)),
                originalAudioFilePath=str(data.get("originalAudioFilePath", audio_file)),
                audioFile=audio_file, bpmSections=native_tempo_to_sections(float(base_tempo), custom_secs),
            )
        song_name, tempo, beat_offset = str(data.get("songName", "")).strip(), _clean_number(data.get("tempo", 0)), _clean_number(data.get("beatOffset", 0))
        custom_secs = [CustomTempoSection.from_dict(c) if isinstance(c, dict) else c for c in data.get("customTempoSections", [])]
        analyse_raw = data.get("analyseResult")
        analyse_res = AnalyseResult.from_dict(analyse_raw) if isinstance(analyse_raw, dict) else AnalyseResult(tempo=tempo, beatOffset=beat_offset)
        return cls(
            version=int(data.get("version", 1)), uniqueId=int(data.get("uniqueId", 0)), songName=song_name,
            performedBy=list(data.get("performedBy", [])), writtenBy=list(data.get("writtenBy", [])),
            seed=int(data.get("seed", 0)), tempo=tempo, customTempoSections=custom_secs, beatOffset=beat_offset,
            startSongOffset=_clean_number(data.get("startSongOffset", 0)), endSongOffset=_clean_number(data.get("endSongOffset", 0)),
            uEAssetName=str(data.get("uEAssetName", song_name)), originalAudioFileHash=str(data.get("originalAudioFileHash", "")),
            originalAudioFilePath=str(data.get("originalAudioFilePath", "")), analyseResult=analyse_res, beatTracks=list(data.get("beatTracks", [])),
        )

    from_dict = from_meta_dict


@dataclass
class ExportResult:
    zip_bytes: bytes = b""
    filename: str = ""
    song_name: str = ""
    folder_path: Optional[Path] = None
    ogg_path: Optional[Path] = None
    json_path: Optional[Path] = None
    metadata: Optional[SongMetadata] = None

    def exists(self) -> bool:
        return bool(self.folder_path and self.folder_path.exists())

    def __truediv__(self, other: Union[str, Path]) -> Path:
        if self.folder_path is None:
            raise TypeError("ExportResult has no folder_path set.")
        return self.folder_path / other

    def __fspath__(self) -> str:
        return str(self.folder_path) if self.folder_path is not None else ""
