"""Wizard Step 3 view: Non-destructive 44.1 kHz OGG transcoding, Meta.json preview, and ZIP export."""

from pathlib import Path
from typing import List
import streamlit as st

from audio_analysis.converter import convert_audio_bytes_to_ogg
from audio_analysis.exceptions import DependencyError, TranscodingError
from export.exceptions import ExportIOError
from export.package_builder import (
    build_mod_zip,
    generate_metadata,
    sanitize_folder_name,
)
from models.song_metadata import ExportResult
from ui.theme import render_micro_card


def _parse_csv_list(raw_text: str) -> List[str]:
    """Split a comma-separated string into a clean list of non-empty strings."""
    if not raw_text or not raw_text.strip():
        return []
    return [item.strip() for item in raw_text.split(",") if item.strip()]


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
    """Render Step 3 of the Wizard: metadata form, 44.1 kHz OGG + Meta.json ZIP builder, and install guide."""
    if st.session_state.get("audio_bytes") is None or not st.session_state.get("bpm_sections"):
        render_micro_card(
            "Paso 3 · Descargá tu Mod para Dead as Disco",
            "Primero subí y sincronizá una pista de audio antes de generar el paquete del mod.",
            "Bloqueado",
        )
        if st.button(
            "← Ir al Paso 1: Subir Audio",
            key="btn_locked_export_to_step1",
            type="primary",
        ):
            st.session_state["wizard_step"] = 1
            st.rerun()
        return

    filename = st.session_state.get("filename") or "track.mp3"
    default_song_name = st.session_state.get("song_name") or Path(filename).stem

    render_micro_card(
        "Paso 3 · Descargá tu Mod para Dead as Disco",
        "Genera la carpeta con audio.ogg (44.1 kHz) y Meta.json lista para ImportedSongs.",
        "audio.ogg + Meta.json",
    )

    col_name, col_perf, col_writ = st.columns([1.6, 1.2, 1.2])
    with col_name:
        song_name_input = st.text_input(
            "Nombre de la Canción (songName / uEAssetName)",
            value=default_song_name,
            key="export_song_name_input",
        )
    with col_perf:
        performed_by_input = st.text_input(
            "Intérprete (performedBy, opcional)",
            value="",
            placeholder="Artista 1, Artista 2",
            key="export_performed_by_input",
        )
    with col_writ:
        written_by_input = st.text_input(
            "Autor (writtenBy, opcional)",
            value="",
            placeholder="Compositor",
            key="export_written_by_input",
        )

    effective_song_name = song_name_input.strip() or default_song_name
    st.session_state["song_name"] = effective_song_name
    safe_folder = sanitize_folder_name(effective_song_name)
    st.caption(f"Carpeta del mod: `{safe_folder}/audio.ogg` + `{safe_folder}/Meta.json`")

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
        written_by=_parse_csv_list(written_by_input),
    )

    if st.button(
        "Generar Paquete Mod (.zip)",
        key="btn_generate_mod_zip",
        icon=":material/folder_zip:",
        type="primary",
        use_container_width=True,
    ):
        source_ext = Path(filename).suffix.lower() or ".mp3"
        with st.spinner("Convirtiendo copia a audio.ogg (44.1 kHz) y empaquetando Meta.json..."):
            try:
                ogg_bytes = _transcode_copy_to_ogg(st.session_state["audio_bytes"], source_ext)
                export_res = build_mod_zip(
                    effective_song_name,
                    st.session_state["bpm_sections"],
                    ogg_bytes,
                    audio_filename="audio.ogg",
                    metadata=metadata,
                )
                st.session_state["export_result"] = export_res
                st.session_state["last_exported_song"] = safe_folder
                st.success(f"Paquete '{export_res.filename}' generado correctamente.")
            except (DependencyError, TranscodingError, ExportIOError) as err:
                st.error(f"Error al generar el paquete del mod: {err}")
            except Exception as exc:
                st.error(f"Error inesperado en la exportación: {exc}")

    if st.session_state.get("export_result") is not None:
        res: ExportResult = st.session_state["export_result"]
        dl_col1, dl_col2 = st.columns([2.2, 1.2])
        with dl_col1:
            st.download_button(
                label=f"Descargar Paquete .ZIP ({res.song_name}/audio.ogg + Meta.json)",
                data=res.zip_bytes,
                file_name=res.filename,
                mime="application/zip",
                icon=":material/download:",
                type="primary",
                use_container_width=True,
                key="btn_download_mod_zip",
            )
        with dl_col2:
            meta_obj = res.metadata or metadata
            st.download_button(
                label="Descargar Meta.json",
                data=meta_obj.to_meta_json(indent="\t").encode("utf-8"),
                file_name="Meta.json",
                mime="application/json",
                icon=":material/description:",
                use_container_width=True,
                key="btn_download_meta_json",
            )

    st.markdown(
        "**Instalación rápida en 3 pasos:**\n"
        f"1. Extraé el archivo `.zip` descargado para obtener la carpeta `{safe_folder}/`.\n"
        "2. Presioná `Win + R`, pegá `%localappdata%\\Pagoda\\Saved\\ImportedSongs\\` y tocá **Enter**.\n"
        f"3. Mové la carpeta `{safe_folder}/` (con `audio.ogg` y `Meta.json`) adentro de `ImportedSongs`."
    )

    with st.expander("Vista Previa de Meta.json (16 campos nativos)", expanded=False):
        st.code(metadata.to_meta_json(indent="\t"), language="json")

    st.markdown("---")
    if st.button("← Volver al Paso 2: Sincronizar Ritmo", key="btn_step3_back_step2"):
        st.session_state["wizard_step"] = 2
        st.rerun()
