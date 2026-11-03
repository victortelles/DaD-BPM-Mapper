"""Wizard Step 2 view: Guided metronome verification, tempo section strip, and optional manual editor."""

from pathlib import Path
from typing import List
import streamlit as st

from audio_analysis.beat_detection import (
    compute_fit_quality,
    detect_beat_offset_ms,
    detect_tempo_sections,
)
from audio_analysis.security import sanitize_song_title
from models.song_metadata import BPMSection
from ui.flag_editor import render_flag_editor, render_offset_controls
from ui.live_waveform_player import render_live_waveform_player
from ui.theme import render_micro_card


def _format_chip_time(seconds: float) -> str:
    """Format seconds as M:SS (e.g. 0:00, 0:20, 1:45)."""
    sec = max(0, int(round(float(seconds))))
    return f"{sec // 60}:{sec % 60:02d}"


def _section_role_label(index: int, bpm: float, base_bpm: float) -> str:
    """Return a concise Spanish role tag for a tempo section chip."""
    if index == 0:
        return "Base"
    if bpm > base_bpm * 1.05:
        return "Rápido"
    if bpm < base_bpm * 0.95:
        return "Lento"
    return "Cambio"


def _render_tempo_sections_strip(sections: List[BPMSection]) -> None:
    """Render a clean dropdown selector and quick jump for detected tempo sections."""
    if not sections:
        return

    base_bpm = float(sections[0].bpm)

    if len(sections) == 1:
        st.info(
            f"**Ritmo constante detectado:** Esta canción mantiene un pulso uniforme de **{base_bpm:.1f} BPM** de principio a fin.",
            icon=":material/info:",
        )
        return

    st.markdown("##### :material/alt_route: Secciones de ritmo detectadas")

    options = list(range(len(sections)))

    def _format_option(idx: int) -> str:
        sec = sections[idx]
        role = _section_role_label(idx, float(sec.bpm), base_bpm)
        time_str = _format_chip_time(sec.startTime)
        return f"Sección #{idx + 1} de {len(sections)} · {time_str} ({sec.startTime:.2f}s) — {sec.bpm:.1f} BPM ({role})"

    current_seek = float(st.session_state.get("player_seek_time", 0.0))
    default_idx = 0
    for i, s in enumerate(sections):
        if abs(s.startTime - current_seek) < 0.25:
            default_idx = i
            break

    def _on_tempo_section_change() -> None:
        idx = st.session_state.get("tempo_section_dropdown_select", 0)
        if 0 <= idx < len(sections):
            st.session_state["player_seek_time"] = float(sections[idx].startTime)

    col_select, col_jump = st.columns([3.8, 1.4], gap="small")
    with col_select:
        selected_idx = st.selectbox(
            f"Selecciona una sección para escuchar ({len(sections)} detectadas en total):",
            options=options,
            index=default_idx,
            format_func=_format_option,
            key="tempo_section_dropdown_select",
            on_change=_on_tempo_section_change,
            help="Elige una sección de ritmo en el menú desplegable para saltar a ese punto en la reproducción.",
        )
    with col_jump:
        st.markdown('<div style="padding-top: 1.65rem;"></div>', unsafe_allow_html=True)
        if st.button(
            "Saltar a sección",
            key="btn_jump_to_selected_section",
            icon=":material/play_circle:",
            type="secondary",
            width="stretch",
        ):
            st.session_state["player_seek_time"] = float(sections[selected_idx].startTime)
            st.rerun()

    st.caption(
        f":material/info: Se detectaron {len(sections)} cambios de velocidad o intensidad a lo largo de la pista. "
        "Elige cualquier sección en el menú desplegable para comprobar su sincronización con el metrónomo."
    )


_render_detected_sections_strip = _render_tempo_sections_strip


def render_step_sync() -> None:
    """Render Step 2 of the Wizard: guided metronome check, primary CTA bar, and optional manual editor."""
    if st.session_state.get("y") is None or st.session_state.get("audio_bytes") is None:
        render_micro_card(
            "Paso 2 de 3 — Escucha tu canción con el metrónomo",
            "Primero sube una pista de audio válida en el Paso 1 para habilitar el reproductor.",
            "Bloqueado",
        )
        if st.button(
            "Ir al Paso 1: Subir Canción",
            key="btn_locked_sync_to_step1",
            type="primary",
            icon=":material/arrow_back:",
            width="stretch",
        ):
            st.session_state["wizard_step"] = 1
            st.rerun()
        return

    y = st.session_state["y"]
    sr = st.session_state["sr"]
    duration = len(y) / float(sr)
    sections = st.session_state.get("bpm_sections") or []
    filename = st.session_state.get("filename") or "track.mp3"
    clean_title = sanitize_song_title(st.session_state.get("song_name") or Path(filename).stem)

    # 1. Guided Instruction Banner at the top of Step 2
    step_subtitle = f"Paso 2 de 3 — Escuchar y verificar: {clean_title}" if clean_title else "Paso 2 de 3 — Escucha tu canción con el metrónomo"
    render_micro_card(
        step_subtitle,
        "Verifica en segundos si el ritmo automático coincide con tu canción.",
        f"{len(sections)} bandera(s)",
    )
    with st.container(border=True):
        st.markdown(
            "1. Pulsa **:material/play_arrow: Reproducir** y marca **:material/volume_up: Metrónomo** para comprobar que los pulsos van al ritmo de la música.\n"
            "2. Salta entre las **:material/flag: Secciones de ritmo** o pulsa **\"Continuar al Paso 3: Descargar Mod (.ZIP)\"** abajo si suena bien sincronizado. "
            "*(Solo abre el panel manual si notas algún desfase).*"
        )

    # 2. Live Waveform Player
    ext = Path(filename).suffix.lower().lstrip(".") or "mp3"
    mime = f"audio/{ext}" if ext in ("mp3", "ogg", "wav", "flac") else "audio/mp3"
    seek_target = float(st.session_state.get("player_seek_time", 0.0))

    render_live_waveform_player(
        audio_bytes=st.session_state["audio_bytes"],
        audio_format=mime,
        y=y,
        sr=sr,
        bpm_sections=sections,
        title=f"Monitor de Onda y Ritmo — {clean_title}" if clean_title else "Monitor de Onda y Ritmo",
        height=420,
        seek_time=seek_target,
        beat_offset_ms=int(st.session_state.get("beat_offset_ms", 0)),
        theme_mode=st.session_state.get("theme_mode", "dark"),
    )

    # 3. Detected Tempo Sections Strip (Visual Summary)
    _render_tempo_sections_strip(sections)

    # 4. Primary Navigation CTA Bar
    nav_back, nav_next = st.columns([1.2, 2.2], gap="medium")
    with nav_back:
        if st.button(
            "Paso 1: Cambiar canción",
            key="btn_sync_back_step1",
            icon=":material/arrow_back:",
            width="stretch",
        ):
            st.session_state["wizard_step"] = 1
            st.rerun()
    with nav_next:
        if st.button(
            "Suena bien — Continuar al Paso 3: Descargar Mod (.ZIP)",
            key="btn_sync_to_step3",
            type="primary",
            icon=":material/check_circle:",
            width="stretch",
        ):
            st.session_state["wizard_step"] = 3
            st.rerun()

    # 5. Optional Collapsed Expander for Manual Adjustments
    with st.expander(
        "Ajuste manual de banderas y sincronizador en pico (Opcional — solo si necesitas corregir el ritmo manualmente)",
        expanded=False,
        icon=":material/build:",
    ):
        st.info(
            "Usa estas herramientas solo si sientes que el metrónomo va adelantado/atrasado "
            "o si quieres agregar cambios de BPM manualmente.",
            icon=":material/info:",
        )

        col_offset_hdr, col_redetect = st.columns([2.6, 1.4])
        with col_offset_hdr:
            st.markdown("**:material/timer: Ajuste de primer pulso (Beat Offset) y recorte**")
        with col_redetect:
            if st.button(
                "Re-detectar automáticamente",
                key="btn_reset_detection",
                icon=":material/refresh:",
                width="stretch",
            ):
                auto_secs = detect_tempo_sections((y, sr))
                auto_offset = detect_beat_offset_ms(y, sr)
                st.session_state["bpm_sections"] = auto_secs
                st.session_state["initial_sections"] = list(auto_secs)
                st.session_state["beat_offset_ms"] = auto_offset
                st.session_state["fit_quality"] = compute_fit_quality(y, sr, auto_secs, auto_offset)
                st.success(
                    "Ritmo y banderas restablecidos a la detección automática.",
                    icon=":material/check_circle:",
                )
                st.rerun()

        new_beat_offset, new_start_offset, new_end_offset = render_offset_controls(
            beat_offset_ms=int(st.session_state.get("beat_offset_ms", 0)),
            start_offset_s=float(st.session_state.get("start_song_offset", 0.0)),
            end_offset_s=float(st.session_state.get("end_song_offset", 0.0)),
            audio_duration=duration,
        )
        st.session_state["beat_offset_ms"] = new_beat_offset
        st.session_state["start_song_offset"] = new_start_offset
        st.session_state["end_song_offset"] = new_end_offset

        updated_sections = render_flag_editor(
            st.session_state["bpm_sections"],
            audio_duration=duration,
            y=y,
            sr=sr,
        )
        if updated_sections != st.session_state["bpm_sections"]:
            st.session_state["bpm_sections"] = updated_sections
            st.rerun()
