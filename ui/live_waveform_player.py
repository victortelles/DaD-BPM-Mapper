"""Live interactive waveform editor and audio player component for Streamlit."""

import base64
import json
from typing import List, Optional
import numpy as np
import streamlit as st
import streamlit.components.v1 as components

from audio_analysis.beat_detection import downsample_waveform
from models.song_metadata import BPMSection
from ui.player_assets import build_player_html


def render_live_waveform_player(
    audio_bytes: bytes,
    audio_format: str,
    y: np.ndarray,
    sr: int,
    bpm_sections: List[BPMSection],
    title: str = "Editor y Reproductor de Onda en Vivo",
    height: int = 420,
    seek_time: Optional[float] = None,
    **kwargs,
) -> None:
    """Render the live interactive waveform editor with audio playback, playhead, and metronome.

    Args:
        audio_bytes: Raw audio bytes of the track.
        audio_format: MIME type (e.g. 'audio/mp3', 'audio/ogg', 'audio/wav').
        y: Audio time series numpy array.
        sr: Sample rate.
        bpm_sections: Chronologically ordered list of BPM sections.
        title: Component header.
        height: Iframe height in pixels.
        seek_time: Optional initial timestamp to seek playhead to.
        **kwargs: Additional keyword arguments (e.g. beat_offset_ms).
    """
    if audio_bytes is None:
        st.warning("No se proporcionaron datos de audio para el reproductor.")
        return

    if hasattr(audio_bytes, "getvalue"):
        audio_bytes = audio_bytes.getvalue()
    elif hasattr(audio_bytes, "read") and callable(audio_bytes.read):
        audio_bytes = audio_bytes.read()

    if not isinstance(audio_bytes, (bytes, bytearray)):
        st.error("Formato de audio no válido para el reproductor.")
        return

    if y is None or sr is None or sr <= 0 or len(y) == 0:
        st.warning("Datos de forma de onda no disponibles.")
        return

    initial_seek_str = "null"
    if seek_time is not None:
        try:
            initial_seek_str = str(round(float(seek_time), 3))
        except (ValueError, TypeError):
            initial_seek_str = "null"

    total_duration = len(y) / float(sr)
    _, envelope = downsample_waveform(y, sr, target_points=2400)

    max_val = float(np.max(envelope)) if len(envelope) > 0 else 1.0
    if max_val > 1e-6:
        norm_envelope = (envelope / max_val).tolist()
    else:
        norm_envelope = [0.0] * len(envelope)

    b64_audio = base64.b64encode(audio_bytes).decode("ascii")
    data_uri = f"data:{audio_format};base64,{b64_audio}"

    sections_data = [
        {
            "index": i,
            "startTime": round(float(s.startTime), 3),
            "startBeat": round(float(s.startBeat), 3),
            "bpm": round(float(s.bpm), 2),
        }
        for i, s in enumerate(bpm_sections or [])
    ]

    beat_offset_ms = kwargs.get("beat_offset_ms", 0)
    payload_json = json.dumps(
        {
            "duration": total_duration,
            "envelope": norm_envelope,
            "sections": sections_data,
            "beatOffsetMs": int(beat_offset_ms or 0),
        }
    )

    html_content = build_player_html(
        data_uri=data_uri,
        payload_json=payload_json,
        initial_seek_str=initial_seek_str,
    )
    components.html(html_content, height=height, scrolling=False)
