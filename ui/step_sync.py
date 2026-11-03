"""Wizard Step 2 view: Live waveform player, metronome, peak auto-sync, and BeatWarping editor."""

from pathlib import Path
import streamlit as st

from audio_analysis.beat_detection import (
    estimate_local_bpm_at_time,
    recalculate_all_bpms_from_peaks,
)
from audio_analysis.bpm_sections import add_marker, update_marker
from audio_analysis.exceptions import ValidationError
from ui.flag_editor import (
    format_seconds_to_min_sec,
    render_flag_editor,
    render_offset_controls,
)
from ui.live_waveform_player import render_live_waveform_player
from ui.theme import render_micro_card


def render_step_sync() -> None:
    """Render Step 2 of the Wizard: interactive waveform player, peak sync, and section editor."""
    if st.session_state.get("y") is None or st.session_state.get("audio_bytes") is None:
        render_micro_card(
            "Paso 2 · Verificá y Ajustá el Ritmo",
            "Primero subí una pista de audio válida en el Paso 1 para habilitar el sincronizador.",
            "Bloqueado",
        )
        if st.button(
            "← Ir al Paso 1: Subir Audio",
            key="btn_locked_sync_to_step1",
            type="primary",
        ):
            st.session_state["wizard_step"] = 1
            st.rerun()
        return

    y = st.session_state["y"]
    sr = st.session_state["sr"]
    duration = len(y) / float(sr)
    sections = st.session_state.get("bpm_sections") or []
    filename = st.session_state.get("filename") or "track.mp3"

    render_micro_card(
        "Paso 2 · Verificá y Ajustá el Ritmo",
        "Escuchá con el metrónomo o colocá banderas en los picos; el BPM se calcula solo.",
        f"{len(sections)} sección(es)",
    )

    # Top bar: Flag selector + Reset detection button
    flag_nav_options = [
        (
            i,
            f"Bandera #{i} · {format_seconds_to_min_sec(s.startTime)} ({s.startTime:.3f}s) · {s.bpm:.1f} BPM",
        )
        for i, s in enumerate(sections)
    ]

    selected_nav_idx = 0
    if flag_nav_options:
        col_nav, col_reset = st.columns([3.2, 1.2])
        with col_nav:
            selected_nav_idx = st.selectbox(
                "Sincronizar Línea de Tiempo con Bandera",
                options=[idx for idx, _ in flag_nav_options],
                format_func=lambda idx: dict(flag_nav_options)[idx],
                key="timeline_flag_sync_select",
            )
        with col_reset:
            st.write("")
            if st.button(
                "Restablecer Detección",
                key="btn_reset_detection",
                icon=":material/restart_alt:",
                use_container_width=True,
            ):
                initial = st.session_state.get("initial_sections") or sections
                st.session_state["bpm_sections"] = list(initial)
                st.success("Banderas restablecidas a la detección original.")
                st.rerun()

    seek_target = 0.0
    if isinstance(selected_nav_idx, int) and 0 <= selected_nav_idx < len(sections):
        seek_target = float(sections[selected_nav_idx].startTime)

    ext = Path(filename).suffix.lower().lstrip(".") or "mp3"
    mime = f"audio/{ext}" if ext in ("mp3", "ogg", "wav", "flac") else "audio/mp3"

    render_live_waveform_player(
        audio_bytes=st.session_state["audio_bytes"],
        audio_format=mime,
        y=y,
        sr=sr,
        bpm_sections=sections,
        title=f"Onda en Vivo: {filename}",
        height=420,
        seek_time=seek_target,
        beat_offset_ms=int(st.session_state.get("beat_offset_ms", 0)),
    )

    # Compact Peak Quick-Synchronizer (Auto-BPM)
    st.markdown("##### Sincronizador Rápido en Pico (Auto-BPM)")
    qc_col1, qc_col2 = st.columns([2.6, 1.4])
    with qc_col1:
        qc_time = st.number_input(
            "Segundo del pico o cambio de ritmo",
            min_value=0.0,
            max_value=float(duration),
            value=0.0,
            step=0.1,
            format="%.3f",
            key="qc_input_time",
        )
    with qc_col2:
        st.write("")
        if st.button(
            "Fijar Bandera en Pico",
            key="btn_qc_apply",
            icon=":material/auto_fix_high:",
            use_container_width=True,
            type="primary",
        ):
            snapped_t, est_bpm = estimate_local_bpm_at_time(y, sr, qc_time)
            try:
                if qc_time <= 0.2:
                    updated = update_marker(sections, index=0, new_bpm=est_bpm)
                else:
                    updated = add_marker(sections, start_time=snapped_t, bpm=est_bpm)
                recalced = recalculate_all_bpms_from_peaks(updated, y, sr)
                st.session_state["bpm_sections"] = recalced
                st.success(f"Bandera sincronizada en {snapped_t:.3f}s ({est_bpm:.1f} BPM).")
                st.rerun()
            except ValidationError as err:
                st.error(f"No se pudo fijar la bandera: {err}")

    # Native Pagoda Offset Controls (beatOffset in ms, startSongOffset & endSongOffset in s)
    new_beat_offset, new_start_offset, new_end_offset = render_offset_controls(
        beat_offset_ms=int(st.session_state.get("beat_offset_ms", 0)),
        start_offset_s=float(st.session_state.get("start_song_offset", 0.0)),
        end_offset_s=float(st.session_state.get("end_song_offset", 0.0)),
        audio_duration=duration,
    )
    st.session_state["beat_offset_ms"] = new_beat_offset
    st.session_state["start_song_offset"] = new_start_offset
    st.session_state["end_song_offset"] = new_end_offset

    # Interactive Section CRUD & Data Editor
    updated_sections = render_flag_editor(
        st.session_state["bpm_sections"],
        audio_duration=duration,
        y=y,
        sr=sr,
    )
    if updated_sections != st.session_state["bpm_sections"]:
        st.session_state["bpm_sections"] = updated_sections
        st.rerun()

    st.markdown("---")
    nav_back, nav_next = st.columns([1.2, 2.0])
    with nav_back:
        if st.button("← Volver al Paso 1", key="btn_step2_back_step1", use_container_width=True):
            st.session_state["wizard_step"] = 1
            st.rerun()
    with nav_next:
        if st.button(
            "Continuar al Paso 3: Exportar Mod →",
            key="btn_step2_to_step3",
            type="primary",
            use_container_width=True,
        ):
            st.session_state["wizard_step"] = 3
            st.rerun()
