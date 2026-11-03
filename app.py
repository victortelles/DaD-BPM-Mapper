"""Dead as Disco · BPM Mapper & Native Mod Packager (v2 Guided Wizard Orchestrator)."""

from pathlib import Path
from typing import Any, Dict

import streamlit as st

from ui.guide_view import render_guide_view
from ui.legal_view import render_legal_view
from ui.step_export import render_step_export
from ui.step_sync import render_step_sync
from ui.step_upload import render_step_upload
from ui.theme import apply_studio_theme, render_step_indicator

LOGO_PATH = Path(__file__).resolve().parent / "Logo.PNG"

SESSION_DEFAULTS: Dict[str, Any] = {
    "theme_mode": "dark",
    "wizard_step": 1,
    "active_nav": "wizard",
    "audio_bytes": None,
    "filename": None,
    "audio_md5": "",
    "y": None,
    "sr": None,
    "bpm_sections": [],
    "initial_sections": [],
    "beat_offset_ms": 0,
    "start_song_offset": 0.0,
    "end_song_offset": 0.0,
    "fit_quality": 0.92,
    "player_seek_time": 0.0,
    "song_name": "",
    "performed_by": "",
    "written_by": "",
    "export_result": None,
    "ogg_bytes": None,
    "last_exported_song": None,
}

STEP_CONTEXT_BANNERS: Dict[int, str] = {
    1: "👉 **Paso actual (1 de 3):** Sube tu archivo de música (`.mp3`, `.wav`, `.ogg`, `.flac`) y el sistema calculará el ritmo automáticamente.",
    2: "👉 **Paso actual (2 de 3):** Pulsa **▶ Reproducir** con el **🔊 Metrónomo** activado para comprobar que los pulsos van al ritmo de la canción.",
    3: "👉 **Paso actual (3 de 3):** Confirma el título, genera el archivo **.ZIP** e instálalo en la carpeta `ImportedSongs` del juego.",
}


def init_session_state() -> None:
    """Initialize all Streamlit session state keys with safe defaults."""
    if "theme_mode" not in st.session_state:
        st.session_state["theme_mode"] = "dark"
    for key, default_val in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = list(default_val) if isinstance(default_val, list) else default_val


def reset_analysis() -> None:
    """Reset loaded audio, DSP analysis state, and cached export artifacts."""
    for key, default_val in SESSION_DEFAULTS.items():
        if key not in ("active_nav", "theme_mode"):
            st.session_state[key] = list(default_val) if isinstance(default_val, list) else default_val


def _render_header() -> None:
    """Render the studio brand header, active song badge, theme toggle, and top navigation bar."""
    col_logo, col_title, col_actions = st.columns([0.7, 4.3, 2.0], gap="medium")
    with col_logo:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), use_container_width=True)
    with col_title:
        st.title("Dead as Disco · BPM Mapper")
        st.caption("Asistente guiado en 3 pasos para crear mods musicales sincronizados (`audio.ogg` + `Meta.json`)")
    with col_actions:
        current_theme = st.session_state.get("theme_mode", "dark")
        toggle_label = "☀️ Modo Claro" if current_theme == "dark" else "🌙 Modo Oscuro"
        if st.button(toggle_label, key="btn_toggle_theme", use_container_width=True):
            st.session_state["theme_mode"] = "light" if current_theme == "dark" else "dark"
            st.rerun()

        sections = st.session_state.get("bpm_sections") or []
        if st.session_state.get("audio_bytes") is not None and sections:
            base_bpm = float(sections[0].bpm)
            fit_pct = float(st.session_state.get("fit_quality", 0.92)) * 100.0
            st.markdown(
                f'<div style="text-align:center;margin-top:0.25rem;">'
                f'<span class="dad-badge">🎵 {base_bpm:.1f} BPM · {fit_pct:.0f}% Precisión</span>'
                f"</div>",
                unsafe_allow_html=True,
            )

    active_nav = st.session_state.get("active_nav", "wizard")
    nav_items = [
        ("wizard", "🧭 Asistente Guiado (3 Pasos)"),
        ("guide", "📖 Cómo Usarlo (Guía Visual)"),
        ("legal", "⚖️ Políticas y Reglas Legales"),
    ]
    nav_cols = st.columns(3, gap="small")
    for col, (nav_key, nav_label) in zip(nav_cols, nav_items):
        with col:
            btn_type = "primary" if active_nav == nav_key else "secondary"
            if st.button(nav_label, key=f"nav_btn_{nav_key}", type=btn_type, use_container_width=True):
                st.session_state["active_nav"] = nav_key
                st.rerun()
    st.markdown("---")


def render_header_and_nav() -> None:
    """Backward-compatible wrapper for header and navigation bar rendering."""
    _render_header()


def _render_stepper_bar(current_step: int, has_audio: bool) -> None:
    """Render the 3-step guided progress bar and contextual 1-line instruction banner."""
    try:
        render_step_indicator(current_step=current_step, unlocked_step=3 if has_audio else 1)
    except TypeError:
        render_step_indicator(current_step=current_step)

    step_items = [
        (1, "1️⃣ Subir Canción", False),
        (2, "2️⃣ Escuchar y Verificar", not has_audio),
        (3, "3️⃣ Descargar Mod (.ZIP)", not has_audio),
    ]
    step_cols = st.columns(3, gap="small")
    for col, (step_num, step_label, is_locked) in zip(step_cols, step_items):
        with col:
            btn_type = "primary" if current_step == step_num else "secondary"
            if st.button(
                step_label,
                key=f"wizard_step_btn_{step_num}",
                type=btn_type,
                disabled=is_locked,
                use_container_width=True,
            ):
                st.session_state["wizard_step"] = step_num
                st.rerun()

    banner_text = STEP_CONTEXT_BANNERS.get(current_step, STEP_CONTEXT_BANNERS[1])
    if not has_audio and current_step == 1:
        banner_text += " *(Los Pasos 2 y 3 se desbloquean al subir tu canción).* "
    st.info(banner_text)


def render_wizard_workspace() -> None:
    """Render the 3-step Wizard selector and dispatch to the active step view."""
    has_audio = st.session_state.get("audio_bytes") is not None and st.session_state.get("y") is not None
    current_step = int(st.session_state.get("wizard_step", 1))
    if not has_audio and current_step > 1:
        current_step = 1
        st.session_state["wizard_step"] = 1

    _render_stepper_bar(current_step=current_step, has_audio=has_audio)

    if current_step == 1:
        render_step_upload()
    elif current_step == 2:
        render_step_sync()
    else:
        render_step_export()


def render_footer() -> None:
    """Render concise studio footer with legal reminder and version badge."""
    st.markdown("---")
    col_legal, col_badge = st.columns([4.5, 1.5])
    with col_legal:
        st.caption(
            "Uso exclusivo para modding personal. Procesamiento local en RAM con validación binaria "
            "de seguridad y respeto a derechos de autor (DMCA)."
        )
    with col_badge:
        st.markdown(
            '<div style="text-align:right;"><span class="dad-badge">v2.0 · Pagoda Native Schema</span></div>',
            unsafe_allow_html=True,
        )


def main() -> None:
    """Application entrypoint for Dead as Disco BPM Mapper."""
    st.set_page_config(
        page_title="Dead as Disco · BPM Mapper",
        page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "🎵",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    init_session_state()
    try:
        apply_studio_theme(st.session_state["theme_mode"])
    except TypeError:
        apply_studio_theme()

    _render_header()

    active_nav = st.session_state.get("active_nav", "wizard")
    if active_nav == "guide":
        render_guide_view()
    elif active_nav == "legal":
        render_legal_view()
    else:
        render_wizard_workspace()

    render_footer()


if __name__ == "__main__":
    main()
