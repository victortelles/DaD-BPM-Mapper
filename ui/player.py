"""Audio preview player component wrapping Streamlit's audio playback capabilities."""

from typing import Optional, Union
import streamlit as st


def render_audio_player(
    audio_data: Union[bytes, str],
    audio_format: str = "audio/ogg",
    title: Optional[str] = None,
    start_time: int = 0,
) -> None:
    """Render the embedded audio player for track auditioning.
    
    Args:
        audio_data: Raw audio bytes or path to audio file.
        audio_format: MIME type (e.g. 'audio/ogg', 'audio/mp3').
        title: Optional label/header to display above the player.
        start_time: Initial playback start offset in seconds.
    """
    if title:
        st.subheader(title)

    if not audio_data:
        st.info("No audio loaded for playback.")
        return

    st.audio(audio_data, format=audio_format, start_time=start_time)
