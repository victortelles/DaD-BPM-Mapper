"""Interactive editor for BeatWarping sections, millisecond beatOffset, and song offsets."""

from typing import List, Optional, Tuple
import numpy as np
import pandas as pd
import streamlit as st

from audio_analysis.beat_detection import (
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
    """Format seconds into MM:SS.sss (e.g. 01:24.500)."""
    sec = max(0.0, float(seconds))
    minutes = int(sec // 60)
    rem_sec = sec % 60
    return f"{minutes:02d}:{rem_sec:06.3f}"


def render_offset_controls(
    beat_offset_ms: int,
    start_offset_s: float,
    end_offset_s: float,
    audio_duration: float,
) -> Tuple[int, float, float]:
    """Render compact controls for beatOffset (ms), startSongOffset (s), and endSongOffset (s)."""
    max_dur = max(1.0, float(audio_duration))
    c1, c2, c3 = st.columns(3)
    with c1:
        new_beat_offset = st.number_input(
            "Beat Offset (ms)",
            min_value=0,
            max_value=60000,
            value=max(0, int(round(float(beat_offset_ms)))),
            step=10,
            key="input_beat_offset_ms",
            help="Desfase del primer pulso en milisegundos (Meta.json: beatOffset).",
        )
    with c2:
        new_start_offset = st.number_input(
            "Inicio Canción (s)",
            min_value=0.0,
            max_value=max_dur,
            value=min(max_dur, max(0.0, float(start_offset_s))),
            step=0.1,
            format="%.2f",
            key="input_start_song_offset_s",
            help="Segundo de inicio de reproducción (Meta.json: startSongOffset).",
        )
    with c3:
        new_end_offset = st.number_input(
            "Fin Canción (s)",
            min_value=0.0,
            max_value=max_dur,
            value=min(max_dur, max(0.0, float(end_offset_s))),
            step=0.1,
            format="%.2f",
            key="input_end_song_offset_s",
            help="Corte final en segundos (Meta.json: endSongOffset, 0 = sin recorte).",
        )
    return int(new_beat_offset), round(float(new_start_offset), 3), round(float(new_end_offset), 3)


def render_flag_editor(
    bpm_sections: List[BPMSection],
    audio_duration: float,
    y: Optional[np.ndarray] = None,
    sr: Optional[int] = None,
) -> List[BPMSection]:
    """Render concise interactive BeatWarping section controls and editable table."""
    current_sections = list(bpm_sections)
    max_dur = max(1.0, float(audio_duration))

    # 1. Master 1-Click Peak Recalculation Bar
    if y is not None and sr is not None and current_sections:
        col_info, col_btn = st.columns([2.6, 1.4])
        with col_info:
            st.caption("Sincronización automática: imanta cada bandera al pico acústico y calcula su BPM real.")
        with col_btn:
            if st.button(
                "Recalcular BPMs desde Picos",
                key="btn_recalc_all_peaks",
                icon=":material/auto_fix_high:",
                use_container_width=True,
                type="primary",
            ):
                updated = recalculate_all_bpms_from_peaks(current_sections, y, sr)
                st.success(f"{len(updated)} secciones sincronizadas con los picos acústicos.")
                return updated

    # 2. Compact Flag Placement & Management Row
    tab_single, tab_batch, tab_manage = st.tabs(
        ["+ Bandera en Pico", "+ Múltiples Banderas", "Calibrar / Eliminar"]
    )

    with tab_single:
        c1, c2, c3 = st.columns([2.0, 1.3, 1.3])
        with c1:
            new_time = st.number_input(
                "Segundo del cambio de ritmo",
                min_value=0.01,
                max_value=max_dur,
                value=min(10.0, max_dur / 2.0),
                step=0.1,
                format="%.3f",
                key="new_marker_time",
            )
        with c2:
            manual_bpm = st.number_input(
                "BPM (0 = Auto por Picos)",
                min_value=0.0,
                max_value=400.0,
                value=0.0,
                step=1.0,
                format="%.1f",
                key="manual_marker_bpm",
            )
        with c3:
            st.write("")
            if st.button(
                "Colocar en Pico",
                key="btn_add_flag_peak",
                icon=":material/pin_drop:",
                use_container_width=True,
                type="primary",
            ):
                try:
                    if manual_bpm <= 0.0:
                        if y is not None and sr is not None:
                            snapped_t, est_bpm = estimate_local_bpm_at_time(y, sr, new_time)
                        else:
                            snapped_t, est_bpm = new_time, 120.0
                        intermediate = add_marker(current_sections, start_time=snapped_t, bpm=est_bpm)
                        updated = (
                            recalculate_all_bpms_from_peaks(intermediate, y, sr)
                            if (y is not None and sr is not None)
                            else intermediate
                        )
                    else:
                        updated = add_marker(current_sections, start_time=new_time, bpm=manual_bpm)
                    st.success(f"Bandera agregada ({format_seconds_to_min_sec(new_time)}).")
                    return updated
                except ValidationError as exc:
                    st.error(f"No se pudo agregar: {exc}")

    with tab_batch:
        cb1, cb2 = st.columns([3.0, 1.2])
        with cb1:
            batch_str = st.text_input(
                "Segundos separados por coma",
                placeholder="15.2, 34.0, 68.5",
                key="input_batch_flag_times",
            )
        with cb2:
            st.write("")
            if st.button("Colocar Todas", key="btn_batch_add", icon=":material/bolt:", use_container_width=True):
                raw_parts = [p.strip() for p in batch_str.replace(";", ",").split(",") if p.strip()]
                try:
                    valid_t = [float(p) for p in raw_parts if 0.05 < float(p) < max_dur]
                    if not valid_t:
                        st.warning(f"Ingresa tiempos entre 0.1s y {max_dur:.1f}s.")
                    else:
                        temp_secs = list(current_sections)
                        added = 0
                        for t in sorted(valid_t):
                            snapped = snap_to_nearest_transient(t, y, sr) if (y is not None and sr is not None) else round(t, 3)
                            if any(abs(s.startTime - snapped) < 0.25 for s in temp_secs):
                                continue
                            temp_secs.append(BPMSection(startTime=snapped, startBeat=0.0, bpm=120.0))
                            added += 1
                        if added > 0:
                            temp_secs.sort(key=lambda s: s.startTime)
                            updated = (
                                recalculate_all_bpms_from_peaks(temp_secs, y, sr)
                                if (y is not None and sr is not None)
                                else recalculate_beats(temp_secs)
                            )
                            st.success(f"{added} banderas colocadas y sincronizadas.")
                            return updated
                        st.info("Los tiempos ingresados ya coinciden con banderas existentes.")
                except ValueError as exc:
                    st.error(f"Formato inválido: {exc}")

    with tab_manage:
        cm1, cm2 = st.columns(2)
        with cm1:
            if y is not None and sr is not None and current_sections:
                if st.button("Calibrar Base 0.0s (Intro)", key="btn_calib_root", icon=":material/speed:", use_container_width=True):
                    _, root_bpm = estimate_local_bpm_at_time(y, sr, 0.0, duration=10.0, snap_transient=False)
                    updated = update_marker(current_sections, index=0, new_bpm=root_bpm)
                    st.success(f"Base 0.0s ajustada a {root_bpm:.1f} BPM.")
                    return updated
        with cm2:
            if len(current_sections) > 1:
                del_opts = {
                    i: f"#{i} · {format_seconds_to_min_sec(s.startTime)} ({s.bpm:.1f} BPM)"
                    for i, s in enumerate(current_sections)
                    if i > 0
                }
                sel_del = st.selectbox("Eliminar bandera", options=list(del_opts.keys()), format_func=lambda idx: del_opts[idx], key="select_flag_to_delete", label_visibility="collapsed")
                if st.button("Eliminar Seleccionada", key="btn_del_flag", icon=":material/delete:", use_container_width=True):
                    return delete_marker(current_sections, sel_del)
            else:
                st.caption("Solo existe la sección base (0.0s).")

    # 3. Editable Sections Table
    df = pd.DataFrame(
        [
            {
                "Sección #": i,
                "Tiempo (s)": round(float(s.startTime), 3),
                "Min:Seg": format_seconds_to_min_sec(s.startTime),
                "Beat Inicial": round(float(s.startBeat), 3),
                "BPM": round(float(s.bpm), 2),
                "Base 0.0s": (i == 0),
            }
            for i, s in enumerate(current_sections)
        ]
    )

    edited_df = st.data_editor(
        df,
        column_config={
            "Sección #": st.column_config.NumberColumn("Sección #", disabled=True),
            "Tiempo (s)": st.column_config.NumberColumn("Tiempo (s)", min_value=0.0, max_value=max_dur, step=0.01),
            "Min:Seg": st.column_config.TextColumn("Min:Seg", disabled=True),
            "Beat Inicial": st.column_config.NumberColumn("Beat Inicial", disabled=True),
            "BPM": st.column_config.NumberColumn("BPM", min_value=0.0, max_value=500.0, step=0.5),
            "Base 0.0s": st.column_config.CheckboxColumn("Base 0.0s", disabled=True),
        },
        disabled=["Sección #", "Min:Seg", "Beat Inicial", "Base 0.0s"],
        use_container_width=True,
        hide_index=True,
        key="bpm_sections_editor",
    )

    if not edited_df.equals(df):
        try:
            candidates: List[BPMSection] = []
            needs_peak_calc = False
            for _, row in edited_df.iterrows():
                row_t = float(row["Tiempo (s)"])
                row_bpm = float(row["BPM"])
                if row_bpm <= 0.0:
                    needs_peak_calc = True
                    row_bpm = 120.0
                candidates.append(BPMSection(startTime=row_t, startBeat=0.0, bpm=row_bpm))

            if abs(candidates[0].startTime) > 1e-6:
                st.error("La sección #0 debe permanecer en 0.0s.")
                return current_sections

            validate_sections(candidates)
            if needs_peak_calc and y is not None and sr is not None:
                return recalculate_all_bpms_from_peaks(candidates, y, sr)
            return recalculate_beats(candidates)
        except Exception as err:
            st.error(f"Error en tabla de secciones: {err}")
            return current_sections

    return current_sections
