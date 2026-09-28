"""Interactive flag editor UI for managing BeatWarping tempo sections."""

from typing import List, Optional
import numpy as np
import pandas as pd
import streamlit as st

from audio_analysis.beat_detection import (
    calculate_bpm_from_peaks,
    estimate_local_bpm_at_time,
    recalculate_all_bpms_from_peaks,
    snap_to_nearest_transient,
)
from audio_analysis.bpm_sections import (
    add_marker,
    delete_marker,
    recalculate_beats,
    update_marker,
    validate_sections,
)
from audio_analysis.exceptions import ValidationError
from models.song_metadata import BPMSection


def format_seconds_to_min_sec(seconds: float) -> str:
    """Format seconds into MM:SS.sss (e.g. 01:24.500).
    
    Args:
        seconds: Time in seconds.
        
    Returns:
        Formatted string MM:SS.sss.
    """
    if seconds < 0:
        seconds = 0.0
    minutes = int(seconds // 60)
    rem_sec = seconds % 60
    return f"{minutes:02d}:{rem_sec:06.3f}"


def render_flag_editor(
    bpm_sections: List[BPMSection],
    audio_duration: float,
    y: Optional[np.ndarray] = None,
    sr: Optional[int] = None,
) -> List[BPMSection]:
    """Render the interactive flag editor table and controls.
    
    Args:
        bpm_sections: Current list of BPMSection objects.
        audio_duration: Total audio track length in seconds.
        y: Optional audio time series for transient snapping and local tempo estimation.
        sr: Optional audio sample rate.
        
    Returns:
        Updated list of BPMSections.
    """
    st.subheader("Banderas de Tempo (BeatWarping)")
    st.caption(
        "Gestiona las secciones de tempo para tu pista. La sección 0 es la bandera raíz obligatoria en 0.0s. "
        "Agregar, editar o eliminar banderas recalcula automáticamente los beats acumulados."
    )

    current_sections = list(bpm_sections)

    # --- Master Recalculation from Acoustic Peaks ---
    if y is not None and sr is not None and len(current_sections) > 0:
        st.markdown("### :material/auto_fix_high: Sincronización Automática por Picos Acústicos")
        col_master1, col_master2 = st.columns([3, 1.5])
        with col_master1:
            st.caption(
                "🎯 **Zero-BPM Workflow**: No necesitas adivinar ni ingresar números de BPM. "
                "Coloca banderas en los cambios de ritmo o caídas; este botón ajusta cada bandera magnéticamente "
                "al golpe físico más cercano y calcula automáticamente el tempo exacto a partir de los picos acústicos."
            )
        with col_master2:
            st.write("")
            if st.button(
                "Recalcular TODOS los BPMs desde Picos",
                key="btn_recalc_all_peaks",
                icon=":material/auto_fix_high:",
                use_container_width=True,
                type="primary",
            ):
                updated = recalculate_all_bpms_from_peaks(current_sections, y, sr)
                st.success(f"¡{len(updated)} banderas alineadas a los picos acústicos y BPMs recalculados!")
                return updated

    # --- Section Addition Form (Zero-BPM Input by Default) ---
    with st.expander("Colocar Bandera en Pico (BPM Automático)", icon=":material/pin_drop:", expanded=False):
        col1, col2 = st.columns([2.5, 1.5])
        with col1:
            new_time = st.number_input(
                "Segundo del golpe o cambio de ritmo:",
                min_value=0.01,
                max_value=max(1.0, float(audio_duration)),
                value=min(10.0, float(audio_duration) / 2.0),
                step=0.1,
                format="%.3f",
                key="new_marker_time",
                help="Ingresa el segundo aproximado. El sistema lo imantará al pico acústico más cercano.",
            )
            st.caption(f"Tiempo seleccionado: **{format_seconds_to_min_sec(new_time)}** (Min:Seg)")
        with col2:
            st.write("")
            st.write("")
            btn_add_peak = st.button(
                "Colocar en Pico (Auto-BPM)",
                key="btn_add_flag_peak",
                icon=":material/pin_drop:",
                use_container_width=True,
                type="primary",
            )

        if btn_add_peak:
            if y is not None and sr is not None:
                snapped_t, est_bpm = estimate_local_bpm_at_time(y, sr, new_time)
            else:
                snapped_t, est_bpm = new_time, 120.0

            try:
                intermediate = add_marker(current_sections, start_time=snapped_t, bpm=est_bpm)
                if y is not None and sr is not None:
                    updated = recalculate_all_bpms_from_peaks(intermediate, y, sr)
                else:
                    updated = intermediate
                st.success(f"¡Bandera fijada en {snapped_t:.3f}s ({format_seconds_to_min_sec(snapped_t)}) con {est_bpm:.1f} BPM!")
                return updated
            except ValidationError as e:
                st.error(f"No se puede agregar la bandera: {e}")

        # Optional manual BPM input for advanced adjustments
        with st.expander("Ingreso manual de BPM (Opcional)", expanded=False):
            col_m1, col_m2 = st.columns([2, 1])
            with col_m1:
                manual_bpm = st.number_input(
                    "Tempo manual (BPM)",
                    min_value=20.0,
                    max_value=400.0,
                    value=120.0,
                    step=1.0,
                    format="%.1f",
                    key="manual_marker_bpm",
                )
            with col_m2:
                st.write("")
                st.write("")
                if st.button("Agregar con BPM Manual", key="btn_add_manual", icon=":material/add:", use_container_width=True):
                    try:
                        updated = add_marker(current_sections, start_time=new_time, bpm=manual_bpm)
                        st.success(f"Bandera agregada en {new_time:.3f}s con {manual_bpm:.1f} BPM manual")
                        return updated
                    except ValidationError as e:
                        st.error(f"Error: {e}")

    # --- Batch Addition Form (Multiple Flags by Timestamps) ---
    with st.expander("Colocar Múltiples Banderas a la Vez (Auto-BPM por Picos)", icon=":material/playlist_add:", expanded=False):
        st.caption(
            "Ingresa los segundos de varias banderas separados por comas (por ejemplo: `14.5, 32.0, 58.4, 91.2`). "
            "El sistema imantará cada segundo a su pico acústico más cercano y calculará los BPMs automáticamente."
        )
        batch_times_str = st.text_input(
            "Tiempos en segundos (separados por comas):",
            placeholder="ej: 15.2, 34.0, 68.5, 102.3",
            key="input_batch_flag_times",
        )
        if st.button("Colocar y Sincronizar Todas", key="btn_batch_add", icon=":material/bolt:", use_container_width=True):
            if not batch_times_str.strip():
                st.warning("Ingresa al menos un segundo.")
            else:
                try:
                    raw_parts = [p.strip() for p in batch_times_str.replace(";", ",").split(",") if p.strip()]
                    parsed_times = []
                    for p in raw_parts:
                        val = float(p)
                        if 0.05 < val < audio_duration:
                            parsed_times.append(val)

                    if not parsed_times:
                        st.warning(f"No se ingresaron tiempos válidos dentro de la duración de la canción (0.1s a {audio_duration:.1f}s).")
                    else:
                        temp_sections = list(current_sections)
                        added_count = 0
                        for t in sorted(parsed_times):
                            if y is not None and sr is not None:
                                snapped_t = snap_to_nearest_transient(t, y, sr)
                            else:
                                snapped_t = round(t, 3)

                            # Avoid duplicate flags too close to existing ones (< 0.25s)
                            if any(abs(s.startTime - snapped_t) < 0.25 for s in temp_sections):
                                continue

                            temp_sections.append(
                                BPMSection(
                                    startTime=snapped_t,
                                    startBeat=0.0,
                                    bpm=120.0,
                                )
                            )
                            added_count += 1

                        if added_count == 0:
                            st.info("Todas las marcas de tiempo ingresadas ya existen o están muy cerca de banderas actuales.")
                        else:
                            temp_sections = sorted(temp_sections, key=lambda s: s.startTime)
                            if y is not None and sr is not None:
                                updated = recalculate_all_bpms_from_peaks(temp_sections, y, sr)
                            else:
                                updated = recalculate_beats(temp_sections)

                            st.success(f"¡Se colocaron {added_count} banderas alineadas a los picos y se sincronizaron todos los BPMs!")
                            return updated
                except Exception as err:
                    st.error(f"Error al procesar los tiempos múltiples: {err}")

    # --- Root BPM Calibration Form ---
    if y is not None and sr is not None and len(current_sections) > 0:
        with st.expander("Calibrar Tempo Base (Sección Raíz 0.0s)", icon=":material/speed:", expanded=False):
            col_r1, col_r2 = st.columns([3, 1.5])
            with col_r1:
                st.caption(
                    f"El BPM actual de la sección 0 es **{current_sections[0].bpm:.1f} BPM**. "
                    "Si el ritmo inicial de la canción está acelerado o desfasado, podés recalcularlo analizando la intro (0 a 10s)."
                )
            with col_r2:
                if st.button("Calibrar Intro (0 a 10s)", key="btn_calib_root", icon=":material/refresh:", use_container_width=True):
                    _, root_bpm = estimate_local_bpm_at_time(y, sr, 0.0, duration=10.0, snap_transient=False)
                    updated = update_marker(current_sections, index=0, new_bpm=root_bpm)
                    st.success(f"Bandera raíz en 0.0s actualizada a {root_bpm:.1f} BPM")
                    return updated

    # --- Section Deletion Form ---
    if len(current_sections) > 1:
        with st.expander("Eliminar Bandera de Tempo", icon=":material/delete:", expanded=False):
            col_del1, col_del2 = st.columns([3, 1])
            with col_del1:
                # Disallow deleting index 0 in the UI options
                deletable_indices = [
                    (i, f"Bandera #{i}: {format_seconds_to_min_sec(s.startTime)} ({s.startTime:.2f}s) | {s.bpm:.1f} BPM")
                    for i, s in enumerate(current_sections)
                    if i > 0
                ]
                selected_del = st.selectbox(
                    "Selecciona la bandera a eliminar",
                    options=[idx for idx, _ in deletable_indices],
                    format_func=lambda idx: dict(deletable_indices)[idx],
                    key="select_flag_to_delete",
                )
            with col_del2:
                st.write("")
                st.write("")
                if st.button("Eliminar", key="btn_del_flag", icon=":material/delete:", use_container_width=True):
                    try:
                        updated = delete_marker(current_sections, selected_del)
                        st.success(f"Bandera #{selected_del} eliminada")
                        return updated
                    except ValidationError as e:
                        st.error(f"No se puede eliminar la bandera: {e}")

    # --- Interactive Table Editor ---
    df_data = [
        {
            "Sección": i,
            "Tiempo (s)": round(s.startTime, 3),
            "Tiempo (Min:Seg)": format_seconds_to_min_sec(s.startTime),
            "Beat Inicial": round(s.startBeat, 3),
            "BPM": round(s.bpm, 2),
            "Es Raíz": (i == 0),
        }
        for i, s in enumerate(current_sections)
    ]
    df = pd.DataFrame(df_data)

    edited_df = st.data_editor(
        df,
        column_config={
            "Sección": st.column_config.NumberColumn("Sección #", disabled=True),
            "Tiempo (s)": st.column_config.NumberColumn(
                "Tiempo (s)",
                help="Segundo exacto donde comienza la sección (editable)",
                min_value=0.0,
                max_value=float(audio_duration),
                step=0.01,
            ),
            "Tiempo (Min:Seg)": st.column_config.TextColumn(
                "Tiempo (Min:Seg)",
                help="Conversión automática a minutos y segundos (MM:SS.sss)",
                disabled=True,
            ),
            "Beat Inicial": st.column_config.NumberColumn(
                "Beat Inicial (auto)",
                help="Beats acumulados calculados desde las secciones previas",
                disabled=True,
            ),
            "BPM": st.column_config.NumberColumn(
                "Tempo (BPM)",
                help="Pulsos por minuto para esta sección",
                min_value=1.0,
                max_value=500.0,
                step=0.5,
            ),
            "Es Raíz": st.column_config.CheckboxColumn("Raíz (0.0s)", disabled=True),
        },
        disabled=["Sección", "Tiempo (Min:Seg)", "Beat Inicial", "Es Raíz"],
        use_container_width=True,
        hide_index=True,
        key="bpm_sections_editor",
    )

    # Process changes from data_editor
    if not edited_df.equals(df):
        try:
            candidate_sections: List[BPMSection] = []
            for idx, row in edited_df.iterrows():
                candidate_sections.append(
                    BPMSection(
                        startTime=float(row["Tiempo (s)"]),
                        startBeat=0.0,  # Will be recalculated
                        bpm=float(row["BPM"]),
                    )
                )

            # Prevent root marker start time shift
            if abs(candidate_sections[0].startTime) > 1e-6:
                st.error("La bandera raíz (Sección 0) debe permanecer en 0.0 segundos. Revirtiendo cambio.")
                return current_sections

            # Validate strict chronological order and constraints before recalculation
            validate_sections(candidate_sections)

            # Recalculate beats
            recalculated = recalculate_beats(candidate_sections)
            return recalculated

        except ValidationError as err:
            st.error(f"Error de validación en la tabla de tempo: {err}")
            return current_sections
        except Exception as err:
            st.error(f"Error al actualizar secciones: {err}")
            return current_sections


    return current_sections
