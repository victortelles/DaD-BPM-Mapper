"""Dead as Disco · BPM Mapper & Native Mod Packager (v2 S.O.L.I.D Orchestrator)."""

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
    "song_name": "",
    "performed_by": "",
    "written_by": "",
    "export_result": None,
    "ogg_bytes": None,
    "last_exported_song": None,
}


def init_session_state() -> None:
    """Initialize all Streamlit session state keys with safe defaults."""
    for key, default_val in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = list(default_val) if isinstance(default_val, list) else default_val


def reset_analysis() -> None:
    """Reset loaded audio, DSP analysis state, and cached export artifacts."""
    for key, default_val in SESSION_DEFAULTS.items():
        if key not in ("active_nav",):
            st.session_state[key] = list(default_val) if isinstance(default_val, list) else default_val


def render_header_and_nav() -> None:
    """Render the studio brand header and top-level view navigation bar."""
    col_logo, col_title = st.columns([0.8, 6.2], gap="medium")
    with col_logo:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), use_container_width=True)
    with col_title:
        st.title("Dead as Disco · BPM Mapper")
        st.caption("Sincronizador automático de ritmo y empaquetador nativo Meta.json + audio.ogg")

    active_nav = st.session_state.get("active_nav", "wizard")
    nav_items = [
        ("wizard", "Asistente (Paso a Paso)"),
        ("guide", "Cómo Usarlo (Guía Visual)"),
        ("legal", "Políticas y Reglas Legales"),
    ]
    nav_cols = st.columns(3, gap="small")
    for col, (nav_key, nav_label) in zip(nav_cols, nav_items):
        with col:
            btn_type = "primary" if active_nav == nav_key else "secondary"
            if st.button(nav_label, key=f"nav_btn_{nav_key}", type=btn_type, use_container_width=True):
                st.session_state["active_nav"] = nav_key
                st.rerun()
    st.markdown("---")


def render_wizard_workspace() -> None:
    """Render the 3-step Wizard selector and dispatch to the active step view."""
    has_audio = st.session_state.get("audio_bytes") is not None and st.session_state.get("y") is not None
    current_step = int(st.session_state.get("wizard_step", 1))
    if not has_audio and current_step > 1:
        current_step = 1
        st.session_state["wizard_step"] = 1

    render_step_indicator(current_step=current_step, unlocked_step=3 if has_audio else 1)

    step_items = [
        (1, "1. Subir Audio", False),
        (2, "2. Sincronizar Ritmo", not has_audio),
        (3, "3. Exportar Mod", not has_audio),
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

    if not has_audio:
        st.caption(
            "🔒 **Paso 2** y **Paso 3** se desbloquean automáticamente al validar un archivo "
            "`.mp3`, `.wav`, `.ogg` o `.flac` en el **Paso 1**."
        )

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
    apply_studio_theme()
    render_header_and_nav()

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
