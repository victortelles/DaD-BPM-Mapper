"""Wizard Step 3 view: Guided 44.1 kHz OGG transcoding, Meta.json packaging, and ZIP download."""

from pathlib import Path
from typing import List
import streamlit as st

from audio_analysis.converter import convert_audio_bytes_to_ogg
from audio_analysis.exceptions import DependencyError, TranscodingError
from audio_analysis.security import sanitize_song_title
from export.exceptions import ExportIOError
from export.package_builder import (
    build_mod_zip,
    generate_metadata,
    get_game_imported_songs_dir,
    sanitize_folder_name,
)
from models.song_metadata import ExportResult
from ui.theme import render_micro_card


def _parse_csv_list(raw_text: str) -> List[str]:
    """Split a comma-separated string into a clean list of non-empty strings."""
    if not raw_text or not raw_text.strip():
        return []
    return [item.strip() for item in raw_text.split(",") if item.strip()]


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


def _transcode_copy_to_ogg(raw_audio: bytes, source_ext: str) -> bytes:
    """Non-destructively transcode a copy of raw_audio to 44.1 kHz Ogg Vorbis bytes."""
    ogg_path = convert_audio_bytes_to_ogg(
        bytes(raw_audio),
        source_format=source_ext,
        fallback_to_soundfile=True,
    )
    try:
        return ogg_path.read_bytes()
    finally:
        if ogg_path.exists():
            try:
                ogg_path.unlink()
            except OSError:
                pass


def render_step_export() -> None:
    """Render Step 3 of the Wizard: 2-column metadata form, .ZIP packager, and 3-step install checklist."""
    if st.session_state.get("audio_bytes") is None or not st.session_state.get("bpm_sections"):
        render_micro_card(
            "Paso 3 de 3 — Descarga e instala tu Mod en Dead as Disco",
            "Primero sube y verifica una canción antes de generar el paquete del mod.",
            "Bloqueado",
        )
        if st.button(
            "Ir al Paso 1: Subir canción",
            key="btn_locked_export_to_step1",
            type="primary",
            icon=":material/arrow_back:",
            width="stretch",
        ):
            st.session_state["wizard_step"] = 1
            st.rerun()
        return

    filename = st.session_state.get("filename") or "track.mp3"
    default_song_name = sanitize_song_title(st.session_state.get("song_name") or Path(filename).stem)
    step_header = f"Paso 3 de 3 — Descargar mod: {default_song_name}" if default_song_name else "Paso 3 de 3 — Descargar mod"

    render_micro_card(
        step_header,
        "Genera la carpeta lista con audio.ogg (44.1 kHz) y Meta.json para ImportedSongs.",
        "audio.ogg + Meta.json",
    )

    with st.container(border=True):
        st.markdown("**:material/inventory_2: 1. Datos de la canción (aparecerán dentro del juego):**")
        col_title, col_artist = st.columns(2, gap="medium")
        with col_title:
            song_name_input = st.text_input(
                "Título de la canción",
                value=default_song_name,
                key="export_song_name_input",
            )
        with col_artist:
            performed_by_input = st.text_input(
                "Artista / Creador (opcional)",
                value=st.session_state.get("performed_by", ""),
                placeholder="Ej: Daft Punk, Carpenter Brut",
                key="export_performed_by_input",
            )

        effective_song_name = sanitize_song_title(song_name_input.strip() or default_song_name)
        st.session_state["song_name"] = effective_song_name
        st.session_state["performed_by"] = performed_by_input
        safe_folder = sanitize_folder_name(effective_song_name)
        st.caption(f":material/folder_zip: Estructura del mod: `{safe_folder}/audio.ogg` + `{safe_folder}/Meta.json`")

        metadata = generate_metadata(
            song_name=effective_song_name,
            bpm_sections=st.session_state["bpm_sections"],
            audio_bytes=st.session_state["audio_bytes"],
            original_filename=filename,
            original_audio_hash=st.session_state.get("audio_md5") or None,
            beat_offset_ms=int(st.session_state.get("beat_offset_ms", 0)),
            start_song_offset=float(st.session_state.get("start_song_offset", 0.0)),
            end_song_offset=float(st.session_state.get("end_song_offset", 0.0)),
            fit_quality=float(st.session_state.get("fit_quality", 0.92)),
            performed_by=_parse_csv_list(performed_by_input),
            written_by=_parse_csv_list(performed_by_input),
        )

        if st.button(
            "Generar y Descargar Paquete (.ZIP)",
            key="btn_generate_mod_zip",
            type="primary",
            icon=":material/inventory_2:",
            width="stretch",
        ):
            source_ext = Path(filename).suffix.lower() or ".mp3"
            with st.spinner("Convirtiendo copia a audio.ogg (44.1 kHz) y empaquetando Meta.json..."):
                try:
                    ogg_bytes = _transcode_copy_to_ogg(st.session_state["audio_bytes"], source_ext)
                    from audio_analysis.security import compute_audio_md5
                    metadata.originalAudioFileHash = compute_audio_md5(ogg_bytes)
                    export_res = build_mod_zip(
                        effective_song_name,
                        st.session_state["bpm_sections"],
                        ogg_bytes,
                        audio_filename="audio.ogg",
                        metadata=metadata,
                    )
                    st.session_state["export_result"] = export_res
                    st.session_state["last_exported_song"] = safe_folder
                    st.success(
                        f"Paquete `{export_res.filename}` listo. Haz clic en el botón de descarga abajo.",
                        icon=":material/check_circle:",
                    )
                except (DependencyError, TranscodingError, ExportIOError) as err:
                    st.error(f"Error al generar el paquete del mod: {err}", icon=":material/error:")
                except Exception as exc:
                    st.error(f"Error inesperado en la exportación: {exc}", icon=":material/error:")

        if st.session_state.get("export_result") is not None:
            res: ExportResult = st.session_state["export_result"]
            dl_col1, dl_col2 = st.columns([2.4, 1.2], gap="small")
            with dl_col1:
                st.download_button(
                    label=f"Guardar Archivo {res.filename} en tu PC",
                    data=res.zip_bytes,
                    file_name=res.filename,
                    mime="application/zip",
                    type="primary",
                    icon=":material/download:",
                    width="stretch",
                    key="btn_download_mod_zip",
                )
            with dl_col2:
                meta_obj = res.metadata or metadata
                st.download_button(
                    label="Solo Meta.json",
                    data=meta_obj.to_meta_json(indent="\t").encode("utf-8"),
                    file_name="Meta.json",
                    mime="application/json",
                    icon=":material/download:",
                    width="stretch",
                    key="btn_download_meta_json",
                )

    with st.container(border=True):
        st.markdown("**:material/folder_zip: 2. Cómo instalar tu Mod en Dead as Disco (3 pasos):**")
        st.markdown(
            f"- **Paso A:** Descomprime el archivo `.ZIP` descargado para obtener la carpeta **`{safe_folder}`**.\n"
            "- **Paso B:** Presiona **`Win + R`** en tu teclado, pega la siguiente ruta y pulsa **Enter**:"
        )
        st.code("%localappdata%\\Pagoda\\Saved\\ImportedSongs\\", language="text")

        col_open, col_hint = st.columns([1.6, 2.4], gap="small")
        with col_open:
            if st.button(
                "Abrir carpeta en Windows",
                key="btn_open_imported_songs_dir",
                icon=":material/folder_open:",
                help="Abre directamente %localappdata%\\Pagoda\\Saved\\ImportedSongs\\ en el Explorador de Windows.",
            ):
                opened = _open_game_folder_in_explorer()
                if opened:
                    st.toast("Carpeta ImportedSongs abierta en el Explorador de Windows.", icon=":material/check_circle:")
                else:
                    st.info("Copia la ruta superior y pégala en el Explorador de Windows.", icon=":material/info:")
        with col_hint:
            st.caption("Acceso directo rápido a la carpeta del juego para pegar tu mod.")

        st.markdown(
            f"- **Paso C:** Copia la carpeta **`{safe_folder}`** (que contiene `audio.ogg` y `Meta.json`) "
            "dentro de **`ImportedSongs`**. ¡Listo para jugar!"
        )

        with st.expander(
            "En caso de errores: ¿El juego muestra \"No se encontró la música\"?",
            expanded=False,
            icon=":material/help:",
        ):
            st.markdown(
                "**No te preocupes, es normal en Dead as Disco al importar mods:**\n\n"
                "1. **¿Por qué ocurre?** Unreal Engine guarda la ruta absoluta del audio (`originalAudioFilePath`) en `Meta.json`. "
                "Si la ruta de tu equipo difiere de la del creador, el juego pedirá ubicar el archivo.\n"
                "2. **Solución en 2 clics:** Cuando el juego muestre el aviso, pulsa en explorar archivos y elige "
                f"el archivo **`audio.ogg`** dentro de la carpeta **`{safe_folder}`**.\n"
                "3. El juego vinculará tu ruta local automáticamente y ya no te lo volverá a pedir."
            )
            if st.button(
                "Ver guía completa de resolución de problemas",
                key="btn_export_goto_troubleshoot",
                icon=":material/help:",
            ):
                st.session_state["active_nav"] = "troubleshooting"
                st.rerun()

    with st.expander(
        "Opcional: Ver código de Meta.json generado (16 campos nativos)",
        expanded=False,
        icon=":material/inventory_2:",
    ):
        active_meta = st.session_state["export_result"].metadata if st.session_state.get("export_result") is not None else metadata
        st.code(active_meta.to_meta_json(indent="\t"), language="json")

    nav_back, nav_restart = st.columns(2, gap="medium")
    with nav_back:
        if st.button(
            "Volver al Paso 2: Escuchar y Verificar",
            key="btn_step3_back_step2",
            icon=":material/arrow_back:",
            width="stretch",
        ):
            st.session_state["wizard_step"] = 2
            st.rerun()
    with nav_restart:
        if st.button(
            "Sincronizar otra canción desde el Paso 1",
            key="btn_step3_restart_step1",
            icon=":material/restart_alt:",
            width="stretch",
        ):
            st.session_state["wizard_step"] = 1
            st.rerun()
