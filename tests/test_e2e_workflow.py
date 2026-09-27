"""End-to-end workflow verification for Dead as Disco BPM Mapper."""

import io
import json
import zipfile
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf

from audio_analysis.beat_detection import detect_tempo_sections, load_audio
from audio_analysis.bpm_sections import add_marker, delete_marker, recalculate_beats
from audio_analysis.converter import convert_mp3_to_ogg, is_ffmpeg_available
from export.package_builder import build_mod_zip, export_to_directory, sanitize_song_name


def test_full_pipeline_e2e(tmp_path: Path):
    """Verify entire pipeline: Audio -> Beat Detection -> Flag Editing -> OGG Transcode -> Mod Export."""
    if not is_ffmpeg_available():
        pytest.skip("FFmpeg is not available")

    # 1. Synthesize a 6-second rhythmic test track at 120 BPM
    sr = 44100
    duration = 6.0
    signal = np.zeros(int(sr * duration), dtype=np.float32)
    for t_beat in np.arange(0.0, duration, 0.5):
        idx = int(t_beat * sr)
        signal[idx : idx + 300] = 0.85 * np.hanning(300)

    input_wav = tmp_path / "raw_track.wav"
    sf.write(str(input_wav), signal, sr, format="WAV")

    # 2. Analyze tempo
    sections = detect_tempo_sections(input_wav)
    assert len(sections) >= 1
    assert sections[0].startTime == 0.0

    # 3. Simulate user adding and deleting flags in the UI
    edited_sections = add_marker(sections, start_time=3.0, bpm=140.0)
    assert len(edited_sections) == len(sections) + 1
    assert any(pytest.approx(s.startTime, 1e-3) == 3.0 for s in edited_sections)

    # 4. Transcode to 44.1 kHz OGG
    output_ogg = tmp_path / "transcoded.ogg"
    convert_mp3_to_ogg(input_wav, output_path=output_ogg)
    assert output_ogg.exists()
    info = sf.info(str(output_ogg))
    assert info.samplerate == 44100
    assert info.format == "OGG"

    # 5. Build ZIP mod package
    raw_title = "Neon Rave: Act I / Part 1"
    clean_name = sanitize_song_name(raw_title)
    assert clean_name == "Neon_Rave__Act_I___Part_1"

    with open(output_ogg, "rb") as f:
        ogg_bytes = f.read()

    export_res = build_mod_zip(clean_name, edited_sections, ogg_bytes)
    assert export_res.filename == f"{clean_name}.zip"

    # Verify ZIP contents
    with zipfile.ZipFile(io.BytesIO(export_res.zip_bytes), "r") as zf:
        json_bytes = zf.read(f"{clean_name}/{clean_name}.json")
        meta = json.loads(json_bytes.decode("utf-8"))
        assert meta["songName"] == clean_name
        assert meta["audioFile"] == f"{clean_name}.ogg"
        assert len(meta["bpmSections"]) == len(edited_sections)

    # 6. Direct folder export
    dest_dir = tmp_path / "ImportedSongs" / clean_name
    exported_folder = export_to_directory(clean_name, edited_sections, ogg_bytes, target_dir=dest_dir)
    assert (exported_folder / f"{clean_name}.json").exists()
    assert (exported_folder / f"{clean_name}.ogg").exists()
