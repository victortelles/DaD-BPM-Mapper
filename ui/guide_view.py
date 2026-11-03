"""Visual step-by-step user guide for Dead as Disco BPM Mapper with full-screen zoom modal."""

from pathlib import Path
from typing import Dict, List, Tuple

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

GUIDE_STEP_CALLOUTS: Dict[int, List[str]] = {
    1: [
        "1. Arrastra o selecciona tu archivo de música (.mp3, .wav, .ogg o .flac) en el recuadro punteado.",
        "2. Revisa las 4 tarjetas con el Ritmo (BPM), duración total, inicio del primer pulso y precisión.",
        "3. Pulsa el botón azul «Continuar al Paso 2: Escuchar y Verificar».",
    ],
    2: [
        "1. Activa «Metrónomo: ON» y pulsa «Reproducir» para escuchar los clics sobre la canción.",
        "2. Usa la rueda del ratón para hacer zoom y «Shift/Ctrl + arrastrar» para mover la línea de tiempo.",
        "3. Si todo suena a tiempo, pulsa «El ritmo es correcto — Ir al Paso 3 (Descargar)».",
    ],
    3: [
        "1. Escribe el título de la canción y opcionalmente el artista y compositor.",
        "2. Pulsa «Preparar paquete del mod (.ZIP)» para convertir el audio a formato OGG 44.1 kHz.",
        "3. Haz clic en «Descargar archivo .ZIP» o instala directamente en la carpeta local del juego.",
    ],
    4: [
        "1. Abre el cuadro Ejecutar en Windows con «Win + R» y pega `%localappdata%\\Pagoda\\Saved\\ImportedSongs\\`.",
        "2. Extrae la carpeta de tu canción para que contenga `audio.ogg` y `Meta.json`.",
        "3. Inicia Dead as Disco, elige tu canción importada y juega al ritmo de los pulsos.",
    ],
}


def _render_callout_box(step_num: int, callouts: List[str]) -> None:
    """Render a high-contrast red-bordered legend explaining the highlighted markers in the image."""
    items_html = "".join(
        f'<div style="margin:0.25rem 0;font-size:0.9rem;line-height:1.45;">'
        f'<span class="material-symbols-rounded" style="font-size:1rem;color:#ef4444;margin-right:6px;">target</span>'
        f"{item}</div>"
        for item in callouts
    )
    st.markdown(
        f'<div class="dad-callout-red">'
        f'<div style="font-weight:700;font-size:0.86rem;color:#ef4444;margin-bottom:0.35rem;display:flex;align-items:center;gap:6px;">'
        f'<span class="material-symbols-rounded" style="font-size:1.05rem;">visibility</span>'
        f"LEYENDA DE PUNTOS MARCADOS EN ROJO (PASO {step_num})</div>"
        f"{items_html}</div>",
        unsafe_allow_html=True,
    )


def _zoom_dialog_body(title: str, description: str, callouts: List[str], img_path: Path, step_num: int = 1) -> None:
    """Render the inner body of the full-screen step image inspection dialog."""
    st.markdown(f"### {title}")
    st.markdown(description)
    _render_callout_box(step_num, callouts)
    if img_path.exists():
        st.image(str(img_path), width="stretch")
    st.caption("Pulsa la X en la esquina superior derecha o presiona ESC para cerrar la vista ampliada.")


if hasattr(st, "dialog"):

    @st.dialog("Vista ampliada de la guía paso a paso", width="large")
    def _open_zoom_dialog(title: str, description: str, callouts: List[str], img_path: Path, step_num: int = 1) -> None:
        """Open a large modal dialog displaying the guide screenshot at full width with its red callout legend."""
        _zoom_dialog_body(title, description, callouts, img_path, step_num)

else:

    def _open_zoom_dialog(title: str, description: str, callouts: List[str], img_path: Path, step_num: int = 1) -> None:
        """Fallback inline full-width rendering when st.dialog is unavailable."""
        _zoom_dialog_body(title, description, callouts, img_path, step_num)


def render_guide_view() -> None:
    """Render the visual 4-step guide with high-visibility callout legends and full-screen image zoom."""
    render_micro_card(
        "Guía Rápida: Cómo Sincronizar e Instalar tu Música en Dead as Disco",
        "Sigue estos 4 pasos visuales. Pulsa «Ampliar imagen» debajo de cada captura para verla en pantalla completa.",
        "Guía Visual · 4 Pasos",
    )

    for idx, (title, description, rel_img_path, badge) in enumerate(GUIDE_STEPS, start=1):
        callouts = GUIDE_STEP_CALLOUTS.get(idx, [])
        img_path = ROOT_DIR / rel_img_path
        with st.container(border=True):
            col_text, col_media = st.columns([1.05, 1.35], gap="medium")
            with col_text:
                st.markdown(
                    f'<span class="dad-badge">'
                    f'<span class="material-symbols-rounded" style="font-size:0.9rem;">counter_{idx}</span>'
                    f"PASO {idx} · {badge}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"#### {title}")
                st.markdown(description)
                _render_callout_box(idx, callouts)
            with col_media:
                if img_path.exists():
                    st.image(str(img_path), width="stretch")
                    if st.button(
                        "Ampliar imagen para leer en tamaño completo",
                        key=f"btn_zoom_guide_{idx}",
                        icon=":material/zoom_in:",
                        type="primary",
                        width="stretch",
                    ):
                        _open_zoom_dialog(title, description, callouts, img_path, idx)
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

    st.space("small")
    if st.button(
        "Ir al asistente de sincronización",
        type="primary",
        key="btn_guide_to_wizard",
        icon=":material/arrow_forward:",
        width="stretch",
    ):
        st.session_state["active_nav"] = "wizard"
        st.rerun()
