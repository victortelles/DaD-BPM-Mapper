"""Unit tests for Sky/Slate theme, live waveform player, player_assets, and flag editor helpers."""

import numpy as np
import streamlit as st
import streamlit.components.v1 as components

from ui.flag_editor import format_seconds_to_min_sec, render_offset_controls
from ui.live_waveform_player import render_live_waveform_player
from ui.player_assets import build_player_html
from ui.theme import STUDIO_THEME_CSS, apply_studio_theme, render_micro_card, render_step_indicator
from ui.waveform_view import render_waveform_view
from models.song_metadata import BPMSection


def test_build_player_html_sky_slate_tokens():
    """Verify build_player_html outputs Sky/Slate CSS tokens and interactive controls."""
    html = build_player_html(
        data_uri="data:audio/ogg;base64,AAAA",
        payload_json='{"duration": 10.0, "envelope": [0.1, 0.8], "sections": [{"index": 0, "startTime": 0.0, "startBeat": 0.0, "bpm": 128.0}]}',
        initial_seek_str="2.5",
    )
    assert "#f8fafc" in html
    assert "#ffffff" in html
    assert "#0284c7" in html
    assert "#38bdf8" in html
    assert "#0f172a" in html
    assert "#e2e8f0" in html
    assert "#ef4444" in html
    assert "chkBeatGrid" in html
    assert "btnCopyTime" in html
    assert "btnPrevFlag" in html
    assert "btnNextFlag" in html
    assert "const initialSeek = 2.5;" in html


def test_live_waveform_player_rendering(monkeypatch):
    """Test that render_live_waveform_player generates valid HTML payload without errors."""
    captured_html = []

    def mock_html(html, height=420, scrolling=False):
        captured_html.append(html)

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
        beat_offset_ms=250,
    )

    assert len(captured_html) == 1
    content = captured_html[0]
    assert "data:audio/mp3;base64," in content
    assert "waveCanvas" in content
    assert "zoomSlider" in content
    assert "btnPlayPause" in content
    assert "btnCopyTime" in content
    assert "metroLight" in content
    assert "chkBeatGrid" in content
    assert "#0284c7" in content
    assert "#f8fafc" in content
    assert "120" in content
    assert "140" in content
    assert '"beatOffsetMs": 250' in content

    # Test with seek_time parameter
    captured_html.clear()
    render_live_waveform_player(
        audio_bytes=audio_bytes,
        audio_format="audio/mp3",
        y=y,
        sr=sr,
        bpm_sections=sections,
        seek_time=1.0,
    )
    assert len(captured_html) == 1
    assert "const initialSeek = 1.0;" in captured_html[0]


def test_studio_theme_tokens_and_helpers(monkeypatch):
    """Verify Sky/Slate studio CSS tokens and theme helper functions."""
    rendered_markdown = []
    monkeypatch.setattr(st, "markdown", lambda body, **kwargs: rendered_markdown.append(body))

    assert "--background: #f8fafc" in STUDIO_THEME_CSS
    assert "--foreground: #0f172a" in STUDIO_THEME_CSS
    assert "--card: #ffffff" in STUDIO_THEME_CSS
    assert "--primary: #0284c7" in STUDIO_THEME_CSS
    assert "--secondary: #e0f2fe" in STUDIO_THEME_CSS
    assert "--accent: #0ea5e9" in STUDIO_THEME_CSS
    assert "--destructive: #ef4444" in STUDIO_THEME_CSS
    assert "--border: #e2e8f0" in STUDIO_THEME_CSS
    assert "--radius: 0.75rem" in STUDIO_THEME_CSS
    assert "Inter" in STUDIO_THEME_CSS
    assert "JetBrains Mono" in STUDIO_THEME_CSS

    apply_studio_theme()
    render_step_indicator(current_step=2)
    render_micro_card("Paso 2: Sincronizar Ritmo", "Ajusta banderas en los picos.", badge="128 BPM")

    assert len(rendered_markdown) == 3
    assert "1. Subir Audio" in rendered_markdown[1]
    assert "2. Sincronizar Ritmo" in rendered_markdown[1]
    assert "3. Descargar Mod" in rendered_markdown[1]
    assert "128 BPM" in rendered_markdown[2]


def test_waveform_view_and_format_seconds(monkeypatch):
    """Verify static waveform fallback chart and MM:SS.sss time formatting."""
    monkeypatch.setattr(st, "pyplot", lambda fig: None)
    sr = 22050
    y = np.sin(np.linspace(0, 20, sr))
    sections = [BPMSection(startTime=0.0, startBeat=0.0, bpm=120.0)]
    fig = render_waveform_view(y, sr, sections, selected_time=0.5)
    assert fig is not None
    assert format_seconds_to_min_sec(84.5) == "01:24.500"
    assert format_seconds_to_min_sec(-3.0) == "00:00.000"
