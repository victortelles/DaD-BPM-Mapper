"""Visual step-by-step user guide for Dead as Disco BPM Mapper."""

from pathlib import Path
from typing import List, Tuple

import streamlit as st

from ui.theme import render_micro_card

ROOT_DIR = Path(__file__).resolve().parent.parent

GUIDE_STEPS: List[Tuple[str, str, str, str]] = [
    (
        "Paso 1: Subir Audio Seguro",
        "Sube tu pista `.mp3`, `.wav`, `.ogg` o `.flac`. El firewall valida las cabeceras binarias y detecta el BPM base y el `beatOffset` sin alterar tu archivo original.",
        "assets/guide/step1_upload.png",
        "Validación Magic Bytes + MD5",
    ),
    (
        "Paso 2: Verificar y Ajustar con Picos",
        "Usa el reproductor en vivo con metrónomo y cuadrícula de beats. Coloca banderas en los cambios de ritmo y el algoritmo calcula los BPMs desde los picos acústicos.",
        "assets/guide/step2_sync.png",
        "Auto-BPM + Snap Magnético",
    ),
    (
        "Paso 3: Descargar Paquete (`audio.ogg` + `Meta.json`)",
        "Genera el `.zip` con la estructura oficial `<Canción>/audio.ogg` (44.1 kHz) y `<Canción>/Meta.json` con los 16 campos nativos de Pagoda.",
        "assets/guide/step3_export.png",
        "44.1 kHz OGG + Meta.json",
    ),
    (
        "Paso 4: Instalar en `ImportedSongs` y Jugar",
        "Presiona `Win + R`, abre `%localappdata%\\Pagoda\\Saved\\ImportedSongs\\`, extrae la carpeta del `.zip` y valida el ritmo dentro de *Dead as Disco*.",
        "assets/guide/step4_install_game.png",
        "Listo para Jugar",
    ),
]


def render_guide_view() -> None:
    """Render the visual 4-step guide with screenshots and installation instructions."""
    render_micro_card(
        "Guía Rápida: Cómo Sincronizar e Instalar tu Música en Dead as Disco",
        "Sigue estos 4 pasos para convertir cualquier canción en un mod perfectamente sincronizado.",
        "Guía Visual · 4 Pasos",
    )

    for idx, (title, description, rel_img_path, badge) in enumerate(GUIDE_STEPS, start=1):
        with st.container(border=True):
            col_text, col_media = st.columns([1.35, 1.0], gap="medium")
            with col_text:
                st.markdown(
                    f'<span class="dad-badge">PASO {idx} · {badge}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown(f"#### {title}")
                st.markdown(description)
            with col_media:
                img_path = ROOT_DIR / rel_img_path
                if img_path.exists():
                    st.image(str(img_path), use_container_width=True)
                else:
                    st.caption(f"Vista previa de interfaz (`{rel_img_path}`)")

    st.markdown("#### Ruta Oficial de Instalación en Windows (`Win + R`)")
    col_path, col_tree = st.columns([1.2, 1.0], gap="medium")
    with col_path:
        st.caption("Copia y pega esta ruta en el cuadro Ejecutar (`Win + R`) o en el Explorador de Archivos:")
        st.code("%localappdata%\\Pagoda\\Saved\\ImportedSongs\\", language="bat")
    with col_tree:
        st.caption("Estructura esperada dentro de `ImportedSongs`:")
        st.code(
            "ImportedSongs/\n"
            "└── MiCancion/\n"
            "    ├── audio.ogg   (Vorbis 44.1 kHz)\n"
            "    └── Meta.json   (Esquema nativo 16 campos)",
            language="text",
        )

    st.write("")
    if st.button(
        "Ir al Asistente de Sincronización →",
        type="primary",
        key="btn_guide_to_wizard",
        use_container_width=True,
    ):
        st.session_state["active_nav"] = "wizard"
        st.rerun()
