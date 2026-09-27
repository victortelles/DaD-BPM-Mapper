"""Unit test for live waveform player component."""

import numpy as np
import pytest
from models.song_metadata import BPMSection
from ui.live_waveform_player import render_live_waveform_player


def test_live_waveform_player_rendering(monkeypatch):
    """Test that render_live_waveform_player generates valid HTML payload without errors."""
    captured_html = []

    def mock_html(html, height=500, scrolling=False):
        captured_html.append(html)

    # Monkeypatch Streamlit components.html
    import streamlit.components.v1 as components
    monkeypatch.setattr(components, "html", mock_html)

    sr = 44100
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    y = 0.5 * np.sin(2 * np.pi * 440 * t)
    audio_bytes = b"fake-audio-bytes"

    sections = [
        BPMSection(startTime=0.0, startBeat=0.0, bpm=120.0),
        BPMSection(startTime=1.0, startBeat=2.0, bpm=140.0),
    ]

    render_live_waveform_player(
        audio_bytes=audio_bytes,
        audio_format="audio/mp3",
        y=y,
        sr=sr,
        bpm_sections=sections,
    )

    assert len(captured_html) == 1
    content = captured_html[0]
    assert "data:audio/mp3;base64," in content
    assert "waveCanvas" in content
    assert "zoomSlider" in content
    assert "btnPlayPause" in content
    assert "btnCopyTime" in content
    assert "120" in content
    assert "140" in content
