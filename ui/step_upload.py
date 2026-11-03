"""Wizard Step 1 view: Guided audio upload, automatic rhythm analysis, and Meta.json import."""

import json
from pathlib import Path
import streamlit as st

from audio_analysis.beat_detection import (
    check_audio_signal_level,
    compute_fit_quality,
    detect_beat_offset_ms,
    detect_tempo_sections,
    load_audio,
)
from audio_analysis.bpm_sections import recalculate_beats
from audio_analysis.exceptions import AudioProcessingError, InsufficientAudioSignalError
from audio_analysis.security import (
    SecurityValidationError,
    compute_audio_md5,
    validate_audio_upload,
)
from export.package_builder import list_imported_songs
from models.song_metadata import SongMetadata, native_tempo_to_sections
from ui.theme import render_micro_card


def _clear_audio_state() -> None:
    """Reset session state audio and analysis keys on validation or DSP failure."""
    defaults = {
        "audio_bytes": None, "filename": None, "audio_md5": "", "y": None, "sr": None,
        "bpm_sections": [], "initial_sections": [], "beat_offset_ms": 0,
        "start_song_offset": 0.0, "end_song_offset": 0.0, "fit_quality": 0.92,
        "player_seek_time": 0.0, "export_result": None, "ogg_bytes": None,
    }
    for key, val in defaults.items():
        st.session_state[key] = val


def _apply_imported_meta(meta: SongMetadata) -> list:
    """Populate session state from a parsed SongMetadata instance."""
    sections = recalculate_beats(native_tempo_to_sections(float(meta.tempo), meta.customTempoSections))
    st.session_state["bpm_sections"] = sections
    st.session_state["initial_sections"] = list(sections)
    st.session_state["beat_offset_ms"] = int(round(float(meta.beatOffset)))
    st.session_state["start_song_offset"] = float(meta.startSongOffset)
    st.session_state["end_song_offset"] = float(meta.endSongOffset)
    st.session_state["song_name"] = meta.songName
    if meta.analyseResult is not None:
        st.session_state["fit_quality"] = float(meta.analyseResult.fitQuality)
    return sections


def _render_import_expander() -> None:
    """Render compact optional expander to load existing Meta.json or ImportedSongs entries."""
    with st.expander("📂 Opcional: Importar Meta.json existente o mod desde ImportedSongs", expanded=False):
        col_json, col_game = st.columns(2)
        with col_json:
            uploaded_json = st.file_uploader("Subir archivo Meta.json", type=["json"], key="json_uploader")
            if uploaded_json is not None and st.button("Cargar Meta.json", key="btn_load_meta_json", use_container_width=True):
                try:
                    raw_text = uploaded_json.getvalue().decode("utf-8")
                    meta = SongMetadata.from_meta_dict(json.loads(raw_text))
                    sections = _apply_imported_meta(meta)
                    st.success(f"Meta.json cargado: '{meta.songName}' ({len(sections)} sección/es).")
                    st.rerun()
                except Exception as exc:
                    st.error(f"No se pudo importar Meta.json: {exc}")

        with col_game:
            entries = list_imported_songs()
            if entries:
                selected_name = st.selectbox("Canción en ImportedSongs", options=[e.name for e in entries], key="select_game_song")
                if st.button("Cargar desde ImportedSongs", key="btn_load_game_song", use_container_width=True):
                    try:
                        entry = next(e for e in entries if e.name == selected_name)
                        meta = entry.metadata or SongMetadata.from_meta_dict(
                            json.loads(entry.json_path.read_text(encoding="utf-8"))
                        )
                        _apply_imported_meta(meta)
                        if entry.ogg_path.exists():
                            ogg_bytes = entry.ogg_path.read_bytes()
                            validate_audio_upload(entry.ogg_path.name, ogg_bytes)
                            y_loaded, sr_loaded = load_audio(ogg_bytes)
                            st.session_state["audio_bytes"] = ogg_bytes
                            st.session_state["filename"] = entry.ogg_path.name
                            st.session_state["audio_md5"] = compute_audio_md5(ogg_bytes)
                            st.session_state["y"] = y_loaded
                            st.session_state["sr"] = sr_loaded
                        st.session_state["wizard_step"] = 2
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Error al cargar desde ImportedSongs: {exc}")
            else:
                st.caption("No se detectaron mods previos en `%localappdata%\\Pagoda\\Saved\\ImportedSongs`.")


def render_step_upload() -> None:
    """Render Step 1 of the Wizard: guided upload box, automatic DSP analysis, and direct flow to Step 2."""
    render_micro_card(
        "Paso 1 de 3 — Sube tu archivo de música",
        "Tu archivo original nunca se modifica. Todo se procesa de forma segura en memoria.",
        "MP3 · WAV · OGG · FLAC",
    )

    with st.container(border=True):
        st.markdown(
            "**¿Cómo funciona este primer paso?**\n"
            "1. **Elige tu canción** (`.mp3`, `.wav`, `.ogg`, `.flac`).\n"
            "2. **El sistema analiza automáticamente** el BPM, el primer pulso y los cambios de ritmo.\n"
            "3. **Pasa al Paso 2** para escuchar el resultado con el metrónomo."
        )
        uploaded_file = st.file_uploader(
            "Arrastra o selecciona tu archivo de música aquí (.mp3, .wav, .ogg, .flac)",
            type=["mp3", "wav", "ogg", "flac"],
            key="file_uploader",
        )

    if uploaded_file is not None:
        is_new_file = (
            st.session_state.get("filename") != uploaded_file.name
            or st.session_state.get("audio_bytes") is None
            or st.session_state.get("y") is None
        )
        if is_new_file:
            raw_bytes = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()
            try:
                validate_audio_upload(uploaded_file.name, raw_bytes)
            except SecurityValidationError as sec_err:
                _clear_audio_state()
                st.error(f"Archivo bloqueado por validación de seguridad: {sec_err}")
                _render_import_expander()
                return

            with st.spinner("🎵 Analizando ritmo, BPM y primer pulso automáticamente..."):
                try:
                    audio_md5 = compute_audio_md5(raw_bytes)
                    y, sr = load_audio(raw_bytes)
                    check_audio_signal_level(y)
                    sections = detect_tempo_sections((y, sr))
                    offset_ms = detect_beat_offset_ms(y, sr)
                    fit_qual = compute_fit_quality(y, sr, sections, offset_ms)

                    st.session_state.update({
                        "audio_bytes": raw_bytes, "filename": uploaded_file.name, "audio_md5": audio_md5,
                        "y": y, "sr": sr, "bpm_sections": sections, "initial_sections": list(sections),
                        "beat_offset_ms": offset_ms, "start_song_offset": 0.0, "end_song_offset": 0.0,
                        "fit_quality": fit_qual, "player_seek_time": 0.0,
                        "song_name": Path(uploaded_file.name).stem,
                        "export_result": None, "ogg_bytes": None,
                        "wizard_step": 2,
                    })
                    st.rerun()
                except (InsufficientAudioSignalError, AudioProcessingError) as dsp_err:
                    _clear_audio_state()
                    st.error(f"No se pudo analizar la pista: {dsp_err}")
                    _render_import_expander()
                    return
                except Exception as exc:
                    _clear_audio_state()
                    st.error(f"Error inesperado al procesar el archivo: {exc}")
                    _render_import_expander()
                    return

    if st.session_state.get("y") is not None and st.session_state.get("sr") is not None:
        y, sr = st.session_state["y"], st.session_state["sr"]
        sections = st.session_state.get("bpm_sections") or []
        duration = len(y) / float(sr)
        base_bpm = sections[0].bpm if sections else 120.0
        offset_ms = int(st.session_state.get("beat_offset_ms", 0))
        loaded_name = st.session_state.get("filename") or "Canción cargada"

        with st.container(border=True):
            st.success(f"✅ **Canción lista:** `{loaded_name}` analizada correctamente.")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Tempo Detectado", f"{base_bpm:.1f} BPM")
            m2.metric("Secciones de Ritmo", f"{len(sections)}")
            m3.metric("Primer Pulso (Offset)", f"{offset_ms} ms")
            m4.metric("Duración", f"{duration:.1f} s")

            if st.button(
                "▶️ Ir al Paso 2: Escuchar y Verificar Sincronización →",
                key="btn_step1_to_step2",
                type="primary",
                use_container_width=True,
            ):
                st.session_state["wizard_step"] = 2
                st.rerun()

    _render_import_expander()
