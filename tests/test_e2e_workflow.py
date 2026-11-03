"""End-to-end v2 workflow verification for Dead as Disco BPM & BeatSync Studio."""

import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from audio_analysis.beat_detection import (
    analyze_track_full,
    compute_fit_quality,
    detect_beat_offset_ms,
    detect_tempo_sections,
    recalculate_all_bpms_from_peaks,
)
from audio_analysis.bpm_sections import add_marker
from audio_analysis.converter import convert_audio_bytes_to_ogg
from audio_analysis.security import (
    SecurityValidationError,
    compute_audio_md5,
    validate_audio_upload,
)
from export.package_builder import (
    build_mod_zip,
    export_to_directory,
    generate_metadata,
    list_imported_songs,
    sanitize_song_name,
)

EXPECTED_16_META_KEYS = {
    "version",
    "uniqueId",
    "songName",
    "performedBy",
    "writtenBy",
    "seed",
    "tempo",
    "customTempoSections",
    "beatOffset",
    "startSongOffset",
    "endSongOffset",
    "uEAssetName",
    "originalAudioFileHash",
    "originalAudioFilePath",
    "analyseResult",
    "beatTracks",
}


def _synthesize_rhythmic_wav(tmp_path: Path, bpm: float = 120.0, duration: float = 8.0, lead_in_sec: float = 0.05) -> Path:
    """Create a synthetic 44.1 kHz rhythmic WAV track with crisp transient impulses."""
    sr = 44100
    signal = np.zeros(int(sr * duration), dtype=np.float32)
    period = 60.0 / bpm
    for t_beat in np.arange(lead_in_sec, duration - 0.1, period):
        idx = int(t_beat * sr)
        burst_len = min(400, len(signal) - idx)
        signal[idx : idx + burst_len] = 0.9 * np.hanning(burst_len)

    wav_path = tmp_path / "raw_track.wav"
    sf.write(str(wav_path), signal, sr, format="WAV")
    return wav_path


def test_security_validation_firewall_e2e(tmp_path: Path) -> None:
    """Verify upload firewall accepts valid WAV/MP3/OGG headers and blocks disguised executables/scripts."""
    wav_path = _synthesize_rhythmic_wav(tmp_path, duration=1.5)
    wav_bytes = wav_path.read_bytes()
    mp3_bytes = b"ID3\x04\x00\x00\x00\x00\x00\x10" + b"\xff\xfb\x90\x64" * 32
    ogg_bytes = b"OggS\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00" + b"\x01" * 64

    assert validate_audio_upload("track.wav", wav_bytes) == "wav"
    assert validate_audio_upload("club_mix.MP3", mp3_bytes) == "mp3"
    assert validate_audio_upload("loop.ogg", ogg_bytes) == "ogg"

    with pytest.raises(SecurityValidationError, match="Windows PE executable"):
        validate_audio_upload("disguised.mp3", b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 128)

    with pytest.raises(SecurityValidationError, match="HTML/JavaScript payload"):
        validate_audio_upload("xss_payload.wav", b"<script>alert('pwn')</script>" + b" " * 64)

    with pytest.raises(SecurityValidationError, match="Unsupported file extension"):
        validate_audio_upload("trojan.exe", wav_bytes)


def test_full_v2_pipeline_e2e(tmp_path: Path) -> None:
    """Verify complete v2 flow: Security -> Non-Destructive DSP -> Peak Recalc -> 44.1kHz OGG -> Native Meta.json."""
    # 1. Synthesize source track and record original byte signature
    input_wav = _synthesize_rhythmic_wav(tmp_path, bpm=120.0, duration=8.0, lead_in_sec=0.05)
    original_bytes = input_wav.read_bytes()
    original_md5 = compute_audio_md5(original_bytes)
    assert len(original_md5) == 32
    assert validate_audio_upload(input_wav.name, original_bytes) == "wav"

    # 2. Non-destructive full audio analysis
    analysis = analyze_track_full(original_bytes)
    y, sr = analysis["y"], analysis["sr"]
    sections = detect_tempo_sections((y, sr))
    offset_ms = detect_beat_offset_ms(y, sr)
    fit_quality = compute_fit_quality(y, sr, sections, beat_offset_ms=offset_ms)

    assert len(sections) >= 1 and sections[0].startTime == 0.0
    assert 110.0 <= float(analysis["tempo"]) <= 130.0
    assert 30 <= offset_ms <= 70
    assert 0.80 <= fit_quality <= 1.0
    assert input_wav.read_bytes() == original_bytes
    assert compute_audio_md5(input_wav.read_bytes()) == original_md5

    # 3. Peak snapping and Zero-BPM recalculation across sections
    edited_sections = add_marker(sections, start_time=4.09, bpm=140.0)
    recalculated = recalculate_all_bpms_from_peaks(edited_sections, y, sr, snap_flags_to_peaks=True)
    assert len(recalculated) == len(edited_sections)
    assert recalculated[0].startTime == 0.0
    assert pytest.approx(recalculated[1].startTime, abs=0.05) == 4.05
    assert all(30.0 <= s.bpm <= 300.0 for s in recalculated)
    assert recalculated[1].startBeat > 0.0

    # 4. Non-destructive transcoding to 44.1 kHz audio.ogg
    output_ogg = tmp_path / "transcoded_audio.ogg"
    convert_audio_bytes_to_ogg(original_bytes, output_path=output_ogg, source_format=".wav", fallback_to_soundfile=True)
    assert output_ogg.exists()
    ogg_info = sf.info(str(output_ogg))
    assert ogg_info.samplerate == 44100
    assert ogg_info.format == "OGG"
    assert compute_audio_md5(input_wav.read_bytes()) == original_md5

    # 5. Native 16-field Meta.json + audio.ogg ZIP and directory export
    raw_title = "Neon Rave: Act I / Part 1"
    clean_folder = sanitize_song_name(raw_title)
    assert clean_folder == "Neon_Rave__Act_I___Part_1"

    meta = generate_metadata(
        song_name=raw_title,
        bpm_sections=recalculated,
        original_audio_hash=original_md5,
        original_audio_path="D:/Music/raw_track.wav",
        beat_offset_ms=offset_ms,
        start_song_offset=0.5,
        end_song_offset=7.5,
        fit_quality=fit_quality,
        performed_by=["Dead as Disco"],
        written_by=["Studio Team"],
    )
    meta_dict = meta.to_meta_dict()
    assert set(meta_dict.keys()) == EXPECTED_16_META_KEYS
    assert meta_dict["originalAudioFileHash"] == original_md5
    assert len(meta_dict["customTempoSections"]) == 1

    ogg_bytes = output_ogg.read_bytes()
    zip_res = build_mod_zip(raw_title, metadata=meta, ogg_audio=ogg_bytes)
    assert zip_res.filename == f"{clean_folder}.zip"

    with zipfile.ZipFile(io.BytesIO(zip_res.zip_bytes), "r") as zf:
        names = set(zf.namelist())
        assert f"{clean_folder}/Meta.json" in names
        assert f"{clean_folder}/audio.ogg" in names
        raw_json = zf.read(f"{clean_folder}/Meta.json").decode("utf-8")
        assert "\n\t" in raw_json
        zip_meta = json.loads(raw_json)
        assert set(zip_meta.keys()) == EXPECTED_16_META_KEYS
        assert zip_meta["songName"] == raw_title
        assert zip_meta["beatOffset"] == offset_ms
        assert zip_meta["analyseResult"]["bAnalyseSuccessful"] is True

    imported_root = tmp_path / "ImportedSongs"
    dir_res = export_to_directory(raw_title, metadata=meta, ogg_audio=ogg_bytes, target_dir=imported_root)
    assert (dir_res.folder_path / "Meta.json").is_file()
    assert (dir_res.folder_path / "audio.ogg").is_file()

    discovered = list_imported_songs(imported_root)
    assert len(discovered) == 1
    assert discovered[0].song_name == raw_title
