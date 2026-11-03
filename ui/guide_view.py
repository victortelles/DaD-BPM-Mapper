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
        "Presiona `Win + R`, abre `%localappdata%\\Pagoda\\Saved\\ImportedSongs\\`, extrae la carpeta del `.zip` y valida el ritmo dentro de *Dead as Disco* con tu mando.",
        "assets/guide/step4_install_game.png",
        "Listo para Jugar",
    ),
]

GUIDE_STEP_CALLOUTS: Dict[int, List[str]] = {
    1: [
        "1. Recuadro de subida: arrastra o selecciona tu archivo de música (.mp3, .wav, .ogg o .flac).",
        "2. Resumen acústico: comprueba las tarjetas con el BPM detectado, duración, primer pulso y precisión.",
        "3. Botón de avance: pulsa «Ir al Paso 2» para continuar al monitor de onda interactivo.",
    ],
    2: [
        "1. Controles de audio: activa «Metrónomo: ON», pulsa «Reproducir» y ajusta el volumen de los pulsos.",
        "2. Selector de secciones: navega por los cambios de ritmo en el menú desplegable y explora la onda.",
        "3. Confirmación de ritmo: pulsa «Suena bien — Continuar al Paso 3» cuando los pulsos coincidan.",
    ],
    3: [
        "1. Datos del mod: escribe o confirma el título de la canción y los campos opcionales para Unreal Engine.",
        "2. Empaquetado: pulsa «Generar y Descargar Paquete» para obtener tu archivo .ZIP (audio.ogg + Meta.json).",
        "3. Carpeta del juego: usa el botón «Abrir carpeta en Windows» para ir directo a ImportedSongs.",
    ],
    4: [
        "1. En Windows, abre el cuadro Ejecutar con «Win + R» y pega %localappdata%\\Pagoda\\Saved\\ImportedSongs\\.",
        "2. Descomprime tu archivo .ZIP para que la carpeta contenga directamente audio.ogg y Meta.json.",
        "3. Inicia Dead as Disco, selecciona la pista en canciones importadas y ¡juega con mando al ritmo!",
    ],
}


def _render_callout_box(step_num: int, callouts: List[str]) -> None:
    """Render an amber-accented legend explaining the numbered badge callouts on the banner image."""
    items_html = ""
    for idx, item in enumerate(callouts, start=1):
        num = item.split(".")[0] if "." in item else str(idx)
        text = item.split(".", 1)[1].strip() if "." in item else item
        items_html += (
            f'<div style="margin:0.35rem 0;font-size:0.88rem;line-height:1.45;display:flex;align-items:flex-start;gap:8px;">'
            f'<span style="background:#f59e0b;color:#020617;font-weight:700;font-size:0.75rem;border-radius:999px;width:1.35rem;height:1.35rem;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:2px;">{num}</span>'
            f'<span style="color:var(--foreground);">{text}</span>'
            f"</div>"
        )

    st.markdown(
        f'<div style="background:var(--secondary);border:1px solid var(--border);border-left:3px solid #f59e0b;border-radius:var(--radius);padding:0.75rem 0.95rem;margin-top:0.6rem;">'
        f'<div style="font-weight:700;font-size:0.86rem;color:#f59e0b;margin-bottom:0.45rem;display:flex;align-items:center;gap:6px;">'
        f'<span class="material-symbols-rounded" style="font-size:1.05rem;color:#f59e0b;">center_focus_strong</span>'
        f"PUNTOS CLAVE DESTACADOS (PASO {step_num})</div>"
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
        """Open a large modal dialog displaying the guide screenshot at full width with its callout legend."""
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

    with st.expander(
        "¿Problemas al cargar en el juego? Solución rápida a \"No se encontró la música\"",
        expanded=False,
        icon=":material/help:",
    ):
        st.markdown(
            "Si al iniciar una partida ves el aviso **\"No se encontró la música\"**, pulsa en explorar archivos "
            "dentro del juego y selecciona el archivo **`audio.ogg`** dentro de la carpeta del mod. "
            "Dead as Disco re-enlazará la ruta en tu equipo y quedará solucionado para siempre."
        )
        if st.button(
            "Abrir guía completa: En caso de errores",
            key="btn_guide_goto_troubleshoot",
            icon=":material/help:",
        ):
            st.session_state["active_nav"] = "troubleshooting"
            st.rerun()

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
