"""Interactive flag editor UI for managing BeatWarping tempo sections."""

from typing import List, Optional
import pandas as pd
import streamlit as st

from audio_analysis.bpm_sections import (
    add_marker,
    delete_marker,
    recalculate_beats,
    validate_sections,
)
from audio_analysis.exceptions import ValidationError
from models.song_metadata import BPMSection


def render_flag_editor(
    bpm_sections: List[BPMSection],
    audio_duration: float,
) -> List[BPMSection]:
    """Render the interactive flag editor table and controls.
    
    Args:
        bpm_sections: Current list of BPMSection objects.
        audio_duration: Total audio track length in seconds.
        
    Returns:
        Updated list of BPMSections.
    """
    st.subheader("🚩 Banderas de Tempo (BeatWarping)")
    st.caption(
        "Gestiona las secciones de tempo para tu pista. La sección 0 es la bandera raíz obligatoria en 0.0s. "
        "Agregar, editar o eliminar banderas recalcula automáticamente los beats acumulados."
    )

    current_sections = list(bpm_sections)

    # --- Section Addition Form ---
    with st.expander("➕ Agregar Nueva Bandera de Tempo", expanded=False):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            new_time = st.number_input(
                "Tiempo de Inicio (segundos)",
                min_value=0.01,
                max_value=max(1.0, float(audio_duration)),
                value=min(10.0, float(audio_duration) / 2.0),
                step=0.1,
                format="%.3f",
                key="new_marker_time",
            )
        with col2:
            new_bpm = st.number_input(
                "Tempo (BPM)",
                min_value=20.0,
                max_value=400.0,
                value=120.0,
                step=1.0,
                format="%.1f",
                key="new_marker_bpm",
            )
        with col3:
            st.write("")
            st.write("")
            if st.button("Agregar Bandera", key="btn_add_flag", use_container_width=True):
                try:
                    updated = add_marker(current_sections, start_time=new_time, bpm=new_bpm)
                    st.success(f"Bandera agregada en {new_time:.3f}s ({new_bpm:.1f} BPM)")
                    return updated
                except ValidationError as e:
                    st.error(f"No se puede agregar la bandera: {e}")

    # --- Section Deletion Form ---
    if len(current_sections) > 1:
        with st.expander("🗑️ Eliminar Bandera de Tempo", expanded=False):
            col_del1, col_del2 = st.columns([3, 1])
            with col_del1:
                # Disallow deleting index 0 in the UI options
                deletable_indices = [
                    (i, f"Bandera #{i}: {s.startTime:.2f}s | {s.bpm:.1f} BPM")
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
                if st.button("Eliminar", key="btn_del_flag", use_container_width=True):
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
            "Tiempo Inicial (s)": round(s.startTime, 3),
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
            "Tiempo Inicial (s)": st.column_config.NumberColumn(
                "Tiempo Inicial (s)",
                help="Segundo exacto donde comienza la sección",
                min_value=0.0,
                max_value=float(audio_duration),
                step=0.01,
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
        disabled=["Sección", "Beat Inicial", "Es Raíz"],
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
                        startTime=float(row["Tiempo Inicial (s)"]),
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
