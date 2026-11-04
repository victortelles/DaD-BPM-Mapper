"""Troubleshooting view: Comprehensive guide for resolving common game import and audio errors."""

import streamlit as st

from export.package_builder import get_game_imported_songs_dir
from ui.theme import render_micro_card


def _open_game_folder_in_explorer() -> bool:
    """Open the local ImportedSongs folder in Windows Explorer if running on Windows."""
    import os
    import subprocess
    import sys

    if sys.platform != "win32":
        return False
    try:
        folder = get_game_imported_songs_dir()
        folder.mkdir(parents=True, exist_ok=True)
        if hasattr(os, "startfile"):
            os.startfile(str(folder))
        else:
            subprocess.Popen(["explorer", str(folder)])
        return True
    except Exception:
        return False


def render_troubleshooting_view() -> None:
    """Render the studio troubleshooting guide covering common game errors and audio path resolution."""
    render_micro_card(
        "En caso de errores — Guía de solución de problemas",
        "Aprende a resolver rápidamente los mensajes de error más comunes al importar mods en Dead as Disco.",
        "Guía de Soporte Técnico",
    )

    with st.container(border=True):
        st.markdown(
            "### :material/warning: 1. El juego dice: *\"No se encontró la música. Por favor selecciona el archivo de audio\"*"
        )
        st.markdown(
            "**¿Por qué ocurre este mensaje?**\n"
            "El motor del juego (**Unreal Engine**) almacena en el archivo `Meta.json` la ruta absoluta "
            "del disco (`originalAudioFilePath`) donde se encuentra el audio en tu computadora. "
            "Si descargaste el mod de otra persona, cambiaste el nombre de la carpeta, o la ruta de tu usuario de Windows "
            "es diferente a la del creador, el juego no encontrará el archivo en esa ruta previa y te pedirá ubicarlo."
        )

        st.info(
            "**Solución en 2 clics (permanente):**\n"
            "1. En el cuadro de diálogo que abre **Dead as Disco**, pulsa en el botón para explorar archivos.\n"
            "2. Navega a la carpeta de tu mod dentro de `ImportedSongs` y selecciona el archivo **`audio.ogg`**.\n"
            "3. ¡Listo! El juego re-enlaza automáticamente la ruta absoluta de tu equipo en `Meta.json` y ya nunca más volverá a pedirlo.",
            icon=":material/check_circle:",
        )

        st.caption(
            "Ubicación por defecto de tus mods en Windows:"
        )
        st.code("%localappdata%\\Pagoda\\Saved\\ImportedSongs\\", language="text")

        col_open, col_hint = st.columns([1.6, 2.4], gap="small")
        with col_open:
            if st.button(
                "Abrir carpeta ImportedSongs",
                key="btn_troubleshoot_open_folder",
                icon=":material/folder_open:",
                help="Abre directamente %localappdata%\\Pagoda\\Saved\\ImportedSongs\\ en el Explorador de Windows.",
            ):
                if _open_game_folder_in_explorer():
                    st.toast("Carpeta ImportedSongs abierta.", icon=":material/check_circle:")
                else:
                    st.info("Copia la ruta superior y pégala en el Explorador de Windows.", icon=":material/info:")
        with col_hint:
            st.caption("Acceso directo a la carpeta donde residen tus canciones personalizadas.")

    st.space("small")

    with st.container(border=True):
        st.markdown(
            "### :material/search_off: 2. La canción no aparece en la lista de canciones personalizadas"
        )
        st.markdown(
            "**Causas comunes:**\n"
            "- **Carpeta anidada:** Al descomprimir el `.ZIP`, algunos programas crean una subcarpeta duplicada "
            "(por ejemplo, `ImportedSongs/MiCancion/MiCancion/Meta.json`).\n"
            "- **Archivos fuera de lugar:** Los archivos `audio.ogg` y `Meta.json` deben estar **directamente** "
            "dentro de la carpeta de la canción, sin carpetas intermedias."
        )

        st.markdown(
            "**Estructura correcta requerida:**\n"
            "```text\n"
            "%localappdata%\\Pagoda\\Saved\\ImportedSongs\\\n"
            "    └── NombreDeTuCancion\\\n"
            "            ├── audio.ogg\n"
            "            └── Meta.json\n"
            "```"
        )

    st.space("small")

    with st.container(border=True):
        st.markdown(
            "### :material/sync_problem: 3. El ritmo o los golpes se sienten desfasados en el juego"
        )
        st.markdown(
            "**Causas y soluciones:**\n"
            "- **Micro-silencio del MP3 original:** Los archivos MP3 agregan un retardo (*encoder padding*) de varios milisegundos al inicio. "
            "Nuestra herramienta convierte el audio a **OGG Vorbis a 44.1 kHz**, eliminando este desfase de raíz.\n"
            "- **Primer golpe (Beat Offset):** En el **Paso 2** de la herramienta, activa el **Metrónomo** "
            "y ajusta el deslizador de *Primer pulso (Offset)* si notas que el golpe del metrónomo entra antes o después de la batería.\n"
            "- **Cambios de tempo:** Si la canción acelera o desacelera en el coro o puente, utiliza las secciones de ritmo "
            "para marcar el nuevo BPM en ese segundo exacto."
        )

    st.space("small")

    with st.container(border=True):
        st.markdown(
            "### :material/volume_off: 4. El audio no se escucha o el juego se congela"
        )
        st.markdown(
            "- Asegúrate de que el archivo `audio.ogg` no esté dañado ni vacío (0 KB).\n"
            "- Si el juego estaba abierto mientras pegabas la carpeta del mod, sal al menú principal o reinicia "
            "Dead as Disco para que el motor re-escanee la carpeta de canciones importadas."
        )

    st.space("medium")
    if st.button(
        "Volver al Asistente guiado",
        key="btn_troubleshoot_back_to_wizard",
        icon=":material/tune:",
        type="primary",
        width="stretch",
    ):
        st.session_state["active_nav"] = "wizard"
        st.rerun()
