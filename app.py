"""Dead as Disco - BPM Mapper & Song Importer.

Streamlit web application for converting raw audio tracks into BeatWarping mod
packages ready for Dead as Disco.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

import streamlit as st


from audio_analysis.beat_detection import (
    check_audio_signal_level,
    detect_tempo_sections,
    load_audio,
)
from audio_analysis.bpm_sections import recalculate_beats, validate_sections
from audio_analysis.converter import (
    convert_audio_bytes_to_ogg,
    is_ffmpeg_available,
    resolve_ffmpeg_path,
)
from audio_analysis.exceptions import (
    AudioProcessingError,
    DependencyError,
    InsufficientAudioSignalError,
    TranscodingError,
    ValidationError,
)
from export.package_builder import (
    build_mod_zip,
    export_to_directory,
    generate_metadata,
    get_game_imported_songs_dir,
    sanitize_song_name,
)
from export.exceptions import ExportIOError
from models.song_metadata import BPMSection, ExportResult
from ui.flag_editor import render_flag_editor
from ui.live_waveform_player import render_live_waveform_player
from ui.player import render_audio_player
from ui.waveform_view import render_waveform_view


def init_session_state() -> None:
    """Initialize Streamlit session state keys if not already present."""
    defaults = {
        "audio_bytes": None,
        "filename": None,
        "y": None,
        "sr": None,
        "bpm_sections": [],
        "initial_sections": [],
        "export_result": None,
        "ogg_bytes": None,
        "last_exported_song": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_analysis() -> None:
    """Clear cached audio analysis data."""
    st.session_state["audio_bytes"] = None
    st.session_state["filename"] = None
    st.session_state["y"] = None
    st.session_state["sr"] = None
    st.session_state["bpm_sections"] = []
    st.session_state["initial_sections"] = []
    st.session_state["export_result"] = None
    st.session_state["ogg_bytes"] = None
    st.session_state["last_exported_song"] = None


def render_sidebar() -> None:
    """Render informative sidebar with instructions and environment status."""
    logo_path = Path(__file__).parent / "Logo.PNG"
    if logo_path.exists():
        st.sidebar.image(str(logo_path), use_container_width=True)

    st.sidebar.title("Dead as Disco BPM")
    st.sidebar.markdown(
        "Convierte pistas de audio en paquetes de mods con sincronización de tempo dinámico (**BeatWarping**) para **Dead as Disco**."
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Estado del Sistema")

    ffmpeg_installed = is_ffmpeg_available()
    if ffmpeg_installed:
        st.sidebar.success("FFmpeg: Listo", icon=":material/check_circle:")
    else:
        st.sidebar.error("FFmpeg: No encontrado", icon=":material/cancel:")
        st.sidebar.caption(
            "La exportación de audio requiere FFmpeg. Instálalo vía `winget install Gyan.FFmpeg` o define la variable `FFMPEG_PATH`."
        )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Ruta en Dead as Disco")
    st.sidebar.code(r"%localappdata%\Pagoda\Saved\ImportedSongs", language="bat")
    st.sidebar.caption(
        "Ubicación estándar en Windows donde se instalan los mods del juego."
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Fórmula BeatWarping")
    st.sidebar.latex(r"B_i = B_{i-1} + (T_i - T_{i-1}) \cdot \frac{\text{BPM}_{i-1}}{60}")


def main() -> None:
    logo_path = Path(__file__).parent / "Logo.PNG"
    st.set_page_config(
        page_title="Dead as Disco – Mapeador de BPM e Importador de Canciones",
        page_icon=str(logo_path) if logo_path.exists() else "🎵",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()
    render_sidebar()

    col_brand1, col_brand2 = st.columns([1, 6])
    with col_brand1:
        if logo_path.exists():
            st.image(str(logo_path), use_container_width=True)
    with col_brand2:
        st.title("Dead as Disco – Mapeador de BPM e Importador")
        st.markdown(
            "Sube una canción, revisa y ajusta las banderas de tempo dinámico (**BeatWarping**), y exporta un paquete de mod listo para el juego."
        )

    tab_upload, tab_editor, tab_export = st.tabs([
        ":material/upload_file: 1. Subir y Analizar",
        ":material/tune: 2. Editor de Banderas y Vista Previa",
        ":material/inventory_2: 3. Exportar Mod",
    ])

    # -------------------------------------------------------------
    # TAB 1: Upload & Audio Analysis
    # -------------------------------------------------------------
    with tab_upload:
        st.subheader("Paso 1: Subir Pista de Audio")
        uploaded_file = st.file_uploader(
            "Selecciona un archivo de audio (.mp3, .wav, .ogg)",
            type=["mp3", "wav", "ogg"],
            key="file_uploader",
        )

        with st.expander(":material/file_open: Importar JSON de BeatWarping Existente (Opcional)", expanded=False):
            st.caption(
                "Si ya tienes un archivo JSON con los BPMs o deseas cargar y editar una canción existente en el juego, "
                "impórtalo aquí para no tener que colocar los BPMs manualmente."
            )
            col_json1, col_json2 = st.columns(2)
            with col_json1:
                st.markdown("**Subir archivo `.json` de la canción:**")
                uploaded_json = st.file_uploader(
                    "Subir archivo .json",
                    type=["json"],
                    key="json_uploader",
                    help="Archivo .json con formato BeatWarping (arreglo bpmSections)."
                )
                if uploaded_json is not None:
                    if st.button("Cargar Banderas desde JSON", icon=":material/upload:", use_container_width=True):
                        try:
                            json_data = json.loads(uploaded_json.read().decode("utf-8"))
                            raw_secs = json_data.get("bpmSections", [])
                            if not raw_secs:
                                st.error("El archivo JSON no contiene el arreglo 'bpmSections'.")
                            else:
                                parsed = [
                                    BPMSection(
                                        startTime=float(s["startTime"]),
                                        startBeat=float(s.get("startBeat", 0.0)),
                                        bpm=float(s["bpm"]),
                                    )
                                    for s in raw_secs
                                ]
                                validate_sections(parsed)
                                recalc = recalculate_beats(parsed)
                                st.session_state["bpm_sections"] = recalc
                                st.session_state["initial_sections"] = list(recalc)
                                st.success(f"¡Cargadas con éxito {len(recalc)} banderas de tempo desde '{uploaded_json.name}'!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error al procesar JSON: {e}")

            with col_json2:
                st.markdown("**O importar desde el juego (`ImportedSongs`):**")
                game_dir = get_game_imported_songs_dir()
                existing_songs = []
                if game_dir.exists():
                    for folder in game_dir.iterdir():
                        if folder.is_dir():
                            j_file = folder / f"{folder.name}.json"
                            if j_file.exists():
                                existing_songs.append((folder.name, j_file, folder / f"{folder.name}.ogg"))

                if existing_songs:
                    selected_game_song = st.selectbox(
                        "Seleccionar canción del juego",
                        options=[s[0] for s in existing_songs],
                        key="select_game_song",
                    )
                    if st.button("Cargar Canción y Banderas", icon=":material/download:", use_container_width=True):
                        try:
                            item = next(s for s in existing_songs if s[0] == selected_game_song)
                            j_path, ogg_path = item[1], item[2]
                            with open(j_path, "r", encoding="utf-8") as f:
                                json_data = json.load(f)
                            raw_secs = json_data.get("bpmSections", [])
                            parsed = [
                                BPMSection(
                                    startTime=float(s["startTime"]),
                                    startBeat=float(s.get("startBeat", 0.0)),
                                    bpm=float(s["bpm"]),
                                )
                                for s in raw_secs
                            ]
                            validate_sections(parsed)
                            recalc = recalculate_beats(parsed)
                            st.session_state["bpm_sections"] = recalc
                            st.session_state["initial_sections"] = list(recalc)

                            if ogg_path.exists():
                                with open(ogg_path, "rb") as f:
                                    ogg_bytes = f.read()
                                st.session_state["audio_bytes"] = ogg_bytes
                                st.session_state["filename"] = f"{selected_game_song}.ogg"
                                y_loaded, sr_loaded = load_audio(ogg_bytes)
                                st.session_state["y"] = y_loaded
                                st.session_state["sr"] = sr_loaded

                            st.success(f"¡Cargada la canción '{selected_game_song}' con {len(recalc)} banderas de tempo!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al cargar canción del juego: {e}")
                else:
                    st.caption("No se encontraron canciones en `%localappdata%\\Pagoda\\Saved\\ImportedSongs`.")



        if uploaded_file is not None:
            # Check if this is a newly uploaded file
            if st.session_state["filename"] != uploaded_file.name:
                raw_bytes = uploaded_file.read()
                st.session_state["audio_bytes"] = raw_bytes
                st.session_state["filename"] = uploaded_file.name
                st.session_state["export_result"] = None
                st.session_state["ogg_bytes"] = None

                with st.spinner("Analizando ritmo, transitorios y secciones de tempo dinámico..."):
                    try:
                        y, sr = load_audio(raw_bytes)
                        check_audio_signal_level(y)
                        sections = detect_tempo_sections((y, sr))

                        st.session_state["y"] = y
                        st.session_state["sr"] = sr
                        st.session_state["bpm_sections"] = sections
                        st.session_state["initial_sections"] = list(sections)
                        st.success(
                            f"¡Análisis completado para '{uploaded_file.name}'! "
                            f"Se detectaron {len(sections)} sección(es)."
                        )

                    except InsufficientAudioSignalError as err:
                        st.error(f"Error de señal de audio: {err}")
                        reset_analysis()
                    except AudioProcessingError as err:
                        st.error(f"Error de procesamiento de audio: {err}")
                        reset_analysis()
                    except Exception as err:
                        st.error(f"Error inesperado durante el análisis: {err}")
                        reset_analysis()

        # Display track info if loaded
        if st.session_state["y"] is not None and st.session_state["sr"] is not None:
            duration = len(st.session_state["y"]) / float(st.session_state["sr"])
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Duración", f"{duration:.2f} s")
            col2.metric("Frecuencia de Muestreo", f"{st.session_state['sr']} Hz")
            col3.metric("Banderas de BPM", f"{len(st.session_state['bpm_sections'])}")
            first_bpm = st.session_state["bpm_sections"][0].bpm if st.session_state["bpm_sections"] else 0
            col4.metric("BPM Inicial", f"{first_bpm:.1f}")

            st.info("Dirígete a **'2. Editor de Banderas y Vista Previa'** para inspeccionar la forma de onda y calibrar el tempo.", icon=":material/arrow_forward:")

    # -------------------------------------------------------------
    # TAB 2: Flag Editor & Audio Preview
    # -------------------------------------------------------------
    with tab_editor:
        if st.session_state["y"] is None:
            st.warning("Por favor, primero sube y analiza un archivo de audio en la pestaña de Subida.")
        else:
            y = st.session_state["y"]
            sr = st.session_state["sr"]
            duration = len(y) / float(sr)

            ext = Path(st.session_state["filename"]).suffix.lower().replace(".", "")
            mime = f"audio/{ext}" if ext in ["mp3", "ogg", "wav"] else "audio/mp3"

            # Render the LIVE Interactive Waveform Player with real-time playhead, zoom & scrubbing
            render_live_waveform_player(
                audio_bytes=st.session_state["audio_bytes"],
                audio_format=mime,
                y=y,
                sr=sr,
                bpm_sections=st.session_state["bpm_sections"],
                title=f"Onda en Vivo: {st.session_state['filename']}",
                height=420,
            )

            col_sub1, col_sub2 = st.columns([3, 1])
            with col_sub2:
                if st.button("Restablecer a Auto-detectado", icon=":material/restart_alt:", use_container_width=True):
                    st.session_state["bpm_sections"] = list(st.session_state["initial_sections"])
                    st.success("Banderas restablecidas a las secciones iniciales auto-detectadas.")
                    st.rerun()
            with col_sub1:
                with st.expander("Ver Gráfica Estática de Onda (Matplotlib)", icon=":material/bar_chart:", expanded=False):
                    render_waveform_view(
                        y,
                        sr,
                        st.session_state["bpm_sections"],
                        title=f"Onda Estática: {st.session_state['filename']}",
                    )

            st.markdown("---")
            st.subheader("Sincronizador Rápido de Cambio de Ritmo")
            st.caption(
                "Cuando la canción cambie de velocidad (o empiece el ritmo tras una intro), pausá el reproductor, "
                "copiá el tiempo e ingresalo acá para alinear al golpe físico y calcular el BPM automáticamente."
            )
            col_qc1, col_qc2 = st.columns([2, 1.5])
            with col_qc1:
                qc_time = st.number_input(
                    "Segundo del cambio de ritmo:",
                    min_value=0.0,
                    max_value=float(duration),
                    value=0.0,
                    step=0.1,
                    format="%.3f",
                    key="qc_input_time",
                    help="Ingresa el segundo donde notas el cambio de velocidad o inicio del ritmo.",
                )
            with col_qc2:
                st.write("")
                st.write("")
                if st.button("Sincronizar Sección Aquí", icon=":material/auto_fix_high:", key="btn_qc_apply", use_container_width=True):
                    from audio_analysis.beat_detection import estimate_local_bpm_at_time
                    from audio_analysis.bpm_sections import add_marker, update_marker
                    from audio_analysis.exceptions import ValidationError

                    snapped_t, est_bpm = estimate_local_bpm_at_time(y, sr, qc_time)
                    try:
                        if qc_time <= 0.2:
                            # Root marker adjustment
                            updated = update_marker(st.session_state["bpm_sections"], index=0, new_bpm=est_bpm)
                            st.session_state["bpm_sections"] = updated
                            st.success(f"¡Tempo base (0.0s) calibrado a {est_bpm:.1f} BPM!")
                        else:
                            updated = add_marker(st.session_state["bpm_sections"], start_time=snapped_t, bpm=est_bpm)
                            st.session_state["bpm_sections"] = updated
                            st.success(f"¡Bandera sincronizada en {snapped_t:.3f}s con {est_bpm:.1f} BPM (alineada al golpe)!")
                        st.rerun()
                    except ValidationError as err:
                        st.error(f"Error al sincronizar: {err}")

            st.markdown("---")
            # Interactive flag editing table
            updated_sections = render_flag_editor(
                st.session_state["bpm_sections"],
                audio_duration=duration,
                y=y,
                sr=sr,
            )
            if updated_sections != st.session_state["bpm_sections"]:
                st.session_state["bpm_sections"] = updated_sections
                st.rerun()


    # -------------------------------------------------------------
    # TAB 3: Export Mod Package
    # -------------------------------------------------------------
    with tab_export:
        if st.session_state["audio_bytes"] is None or not st.session_state["bpm_sections"]:
            st.warning("Por favor, sube un archivo de audio y configura las secciones de tempo antes de exportar.")
        else:
            st.subheader("Paso 3: Exportar Paquete de Mod para Dead as Disco")

            default_title = Path(st.session_state["filename"]).stem
            song_title_input = st.text_input(
                "Nombre del Mod (se limpiará para compatibilidad del sistema de archivos)",
                value=default_title,
                help="Solo se conservarán letras, números y guiones bajos.",
            )
            clean_song_name = sanitize_song_name(song_title_input)
            st.caption(f"Identificador seguro del mod: `{clean_song_name}`")

            source_ext = Path(st.session_state["filename"]).suffix.lower()
            if not source_ext:
                source_ext = ".mp3"

            export_format_choice = st.radio(
                "Formato de Audio para el Mod:",
                options=[
                    f"Audio Original ({source_ext}) – Calidad 100% intacta, sin saturación (Recomendado)",
                    "OGG Vorbis (.ogg) – 44.1 kHz, Alta Fidelidad Q8 (Vía FFmpeg)",
                ],
                index=0,
                help=(
                    "El formato original conserva bit por bit el archivo subido sin recodificar ni saturar la música. "
                    "El archivo JSON vinculará automáticamente este audio."
                ),
            )
            use_ogg = "OGG Vorbis" in export_format_choice
            target_ext = ".ogg" if use_ogg else source_ext
            target_audio_name = f"{clean_song_name}{target_ext}"

            # Show metadata preview
            st.markdown("#### Vista Previa de Metadatos JSON")
            metadata = generate_metadata(
                clean_song_name,
                st.session_state["bpm_sections"],
                audio_filename=target_audio_name,
            )
            st.code(metadata.to_json(indent=2), language="json")

            is_local_windows = sys.platform == "win32" and get_game_imported_songs_dir().parent.exists()

            col_exp1, col_exp2 = st.columns(2)

            with col_exp1:
                st.markdown("#### Descargar Paquete ZIP del Mod")
                if st.button("Generar ZIP del Mod", icon=":material/folder_zip:", key="btn_gen_zip", type="primary", use_container_width=True):
                    spinner_msg = (
                        "Transcodificando a OGG (44.1 kHz, Q8) y ensamblando ZIP..."
                        if use_ogg
                        else "Ensamblando paquete ZIP con audio original (sin pérdida)..."
                    )
                    with st.spinner(spinner_msg):
                        try:
                            if use_ogg:
                                ext = Path(st.session_state["filename"]).suffix.lower()
                                ogg_path = convert_audio_bytes_to_ogg(
                                    st.session_state["audio_bytes"],
                                    source_format=ext,
                                )
                                with open(ogg_path, "rb") as f:
                                    final_audio = f.read()
                                try:
                                    ogg_path.unlink()
                                except OSError:
                                    pass
                            else:
                                final_audio = st.session_state["audio_bytes"]

                            export_res = build_mod_zip(
                                clean_song_name,
                                st.session_state["bpm_sections"],
                                final_audio,
                                audio_filename=target_audio_name,
                            )
                            st.session_state["export_result"] = export_res
                            st.session_state["last_exported_song"] = clean_song_name
                            st.success(f"¡Paquete de mod para '{clean_song_name}' generado exitosamente!")

                        except DependencyError as e:
                            st.error(f"Error de Dependencia: {e}")
                        except TranscodingError as e:
                            st.error(f"Error de Transcodificación: {e}")
                        except ExportIOError as e:
                            st.error(f"Error de E/S de Exportación: {e}")
                        except Exception as e:
                            st.error(f"Error al generar paquete: {e}")

                if st.session_state["export_result"] is not None:
                    res: ExportResult = st.session_state["export_result"]
                    st.download_button(
                        label=f"Descargar {res.filename}",
                        icon=":material/download:",
                        data=res.zip_bytes,
                        file_name=res.filename,
                        mime="application/zip",
                        use_container_width=True,
                    )

            with col_exp2:
                if is_local_windows:
                    st.markdown("#### Exportar Directamente en esta PC")
                    target_game_dir = get_game_imported_songs_dir()
                    st.caption(f"Ruta de destino: `{target_game_dir / clean_song_name}`")

                    if st.button("Exportar a ImportedSongs y Abrir Carpeta", icon=":material/folder_open:", key="btn_direct_export", use_container_width=True):
                        with st.spinner("Guardando archivos y abriendo el Explorador de Windows..."):
                            try:
                                if use_ogg:
                                    ext = Path(st.session_state["filename"]).suffix.lower()
                                    ogg_path = convert_audio_bytes_to_ogg(
                                        st.session_state["audio_bytes"],
                                        source_format=ext,
                                    )
                                    with open(ogg_path, "rb") as f:
                                        final_audio = f.read()
                                    try:
                                        ogg_path.unlink()
                                    except OSError:
                                        pass
                                else:
                                    final_audio = st.session_state["audio_bytes"]

                                out_path = export_to_directory(
                                    clean_song_name,
                                    st.session_state["bpm_sections"],
                                    final_audio,
                                    audio_filename=target_audio_name,
                                )
                                st.success(f"¡Mod exportado exitosamente a:\n`{out_path}`!")
                                try:
                                    import subprocess
                                    subprocess.Popen(["explorer", str(out_path)])
                                except Exception:
                                    pass

                            except DependencyError as e:
                                st.error(f"Error de Dependencia: {e}")
                            except TranscodingError as e:
                                st.error(f"Error de Transcodificación: {e}")
                            except ExportIOError as e:
                                st.error(f"Error de E/S de Exportación: {e}")
                            except Exception as e:
                                st.error(f"Fallo al exportar: {e}")
                else:
                    st.markdown("#### Cómo Instalar en Dead as Disco")
                    st.info(
                        "**Para jugar este mod en tu PC:**\n\n"
                        "1. Haz clic en **Descargar ZIP** en la columna izquierda.\n\n"
                        "2. Presiona `Win + R` en tu teclado y pega la siguiente ruta:\n"
                        "   `%localappdata%\\Pagoda\\Saved\\ImportedSongs`\n\n"
                        "3. Extrae la carpeta descargada dentro de esa ubicación y ¡listo!",
                        icon=":material/info:",
                    )




if __name__ == "__main__":
    main()
