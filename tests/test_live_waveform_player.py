"""Unit tests for Dual-Mode Sky/Slate theme, DAW live waveform player, player_assets, and waveform_view."""

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import streamlit.components.v1 as components

from models.song_metadata import BPMSection
from ui.flag_editor import format_seconds_to_min_sec
from ui.live_waveform_player import render_live_waveform_player
from ui.player_assets import (
    build_player_css,
    build_player_html,
    build_player_js,
    build_waveform_player_html,
)
from ui.theme import (
    DARK_PALETTE,
    LIGHT_PALETTE,
    STUDIO_PALETTE,
    STUDIO_THEME_CSS,
    apply_studio_theme,
    get_active_palette,
    get_theme_css,
    render_micro_card,
    render_step_indicator,
)
from ui.waveform_view import create_waveform_figure, render_waveform_view


def test_dual_theme_palettes_and_css_tokens(monkeypatch):
    """Verify DARK_PALETTE, LIGHT_PALETTE, STUDIO_PALETTE, and get_theme_css in dark and light modes."""
    assert STUDIO_PALETTE == LIGHT_PALETTE
    assert DARK_PALETTE["background"] == "#020617"
    assert DARK_PALETTE["foreground"] == "#f8fafc"
    assert DARK_PALETTE["card"] == "#0f172a"
    assert DARK_PALETTE["primary"] == "#38bdf8"
    assert DARK_PALETTE["secondary"] == "#1e293b"
    assert DARK_PALETTE["accent"] == "#0ea5e9"
    assert DARK_PALETTE["destructive"] == "#991b1b"
    assert DARK_PALETTE["border"] == "#1e293b"
    assert DARK_PALETTE["radius"] == "0.75rem"

    assert LIGHT_PALETTE["background"] == "#f8fafc"
    assert LIGHT_PALETTE["foreground"] == "#0f172a"
    assert LIGHT_PALETTE["card"] == "#ffffff"
    assert LIGHT_PALETTE["primary"] == "#0284c7"

    assert get_active_palette("dark") == DARK_PALETTE
    assert get_active_palette("light") == LIGHT_PALETTE

    dark_css = get_theme_css("dark")
    light_css = get_theme_css("light")
    assert ":root" in dark_css and ".dark" in dark_css
    assert "#020617" in dark_css and "#0f172a" in dark_css and "#38bdf8" in dark_css
    assert "#f8fafc" in light_css and "#ffffff" in light_css and "#0284c7" in light_css
    assert "Inter" in STUDIO_THEME_CSS and "JetBrains Mono" in STUDIO_THEME_CSS

    rendered_markdown = []
    monkeypatch.setattr(st, "markdown", lambda body, **kwargs: rendered_markdown.append(body))

    apply_studio_theme("dark")
    apply_studio_theme("light")
    render_step_indicator(current_step=2)
    render_micro_card("Paso 2: Sincronizar Ritmo", "Ajusta banderas en los picos.", badge="128 BPM")

    assert len(rendered_markdown) == 4
    assert "rgba(2, 6, 23, 0.88)" in rendered_markdown[0]
    assert "rgba(248, 250, 252, 0.88)" in rendered_markdown[1]
    assert "1. Subir Audio" in rendered_markdown[2]
    assert "2. Sincronizar Ritmo" in rendered_markdown[2]
    assert "3. Descargar Mod" in rendered_markdown[2]
    assert "128 BPM" in rendered_markdown[3]


def test_player_assets_daw_mouse_controls_and_themes():
    """Verify build_player_css, build_player_js, and build_waveform_player_html for dark/light modes and DAW controls."""
    dark_css = build_player_css("dark")
    light_css = build_player_css("light")
    assert "#020617" in dark_css and "#0f172a" in dark_css and "#38bdf8" in dark_css
    assert "#f8fafc" in light_css and "#ffffff" in light_css and "#0284c7" in light_css

    js_code = build_player_js()
    # Verify Wheel Zoom anchored at cursor
    assert 'wrapper.addEventListener("wheel"' in js_code
    assert "e.preventDefault()" in js_code
    assert "wrapper.scrollLeft" in js_code
    # Verify Shift/Ctrl + Drag Panning and Left-Click Scrubbing
    assert "e.shiftKey || e.ctrlKey || e.metaKey || e.button === 1" in js_code
    assert "isPanning" in js_code
    assert "grabbing" in js_code
    assert "isScrubbing" in js_code
    # Verify Multi-Tempo vibrant flag colors & badge format
    for color in ("#38bdf8", "#f59e0b", "#10b981", "#a855f7", "#f43f5e"):
        assert color in js_code
    assert "#${idx + 1} · ${bpmDisp} BPM" in js_code

    html_dark = build_waveform_player_html(
        data_uri="data:audio/ogg;base64,AAAA",
        payload_json='{"duration": 10.0, "envelope": [0.1, 0.8], "sections": [{"index": 0, "startTime": 0.0, "startBeat": 0.0, "bpm": 95.0}, {"index": 1, "startTime": 4.0, "startBeat": 6.33, "bpm": 190.0}]}',
        initial_seek_str="2.5",
        theme_mode="dark",
    )
    assert 'class="dark"' in html_dark
    assert "Rueda: Zoom en cursor" in html_dark
    assert "Shift / Ctrl + Arrastrar: Mover línea de tiempo" in html_dark
    assert "Clic / Arrastrar: Mover reproductor" in html_dark
    assert "material-symbols-rounded" in html_dark
    # Verify Volume controls and audio element volume synchronization
    assert "vol-controls" in dark_css and "vol-slider" in dark_css
    assert "audio.volume = 0.75" in js_code
    assert "volSlider" in js_code and "btnVolMute" in js_code
    assert 'id="volSlider"' in html_dark and 'id="btnVolMute"' in html_dark
    assert "const initialSeek = 2.5;" in html_dark

    html_light = build_player_html(
        data_uri="data:audio/ogg;base64,AAAA",
        payload_json='{"duration": 10.0, "envelope": [0.1, 0.8], "sections": []}',
        initial_seek_str="null",
        theme_mode="light",
    )
    assert 'class="light"' in html_light
    assert "#ffffff" in html_light


def test_live_waveform_player_rendering_dark_and_light(monkeypatch):
    """Test that render_live_waveform_player generates valid HTML payload in both dark and light modes."""
    captured_html = []

    def mock_html(html, height=435, scrolling=False):
        captured_html.append(html)

    monkeypatch.setattr(components, "html", mock_html)

    sr = 44100
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    y = 0.5 * np.sin(2 * np.pi * 440 * t)
    audio_bytes = b"fake-audio-bytes"

    sections = [
        BPMSection(startTime=0.0, startBeat=0.0, bpm=95.0),
        BPMSection(startTime=1.0, startBeat=1.583, bpm=190.0),
    ]

    render_live_waveform_player(
        audio_bytes=audio_bytes,
        audio_format="audio/mp3",
        y=y,
        sr=sr,
        bpm_sections=sections,
        beat_offset_ms=250,
        theme_mode="dark",
    )

    assert len(captured_html) == 1
    content_dark = captured_html[0]
    assert "data:audio/mp3;base64," in content_dark
    assert "waveCanvas" in content_dark
    assert "#020617" in content_dark
    assert '"beatOffsetMs": 250' in content_dark
    assert '"themeMode": "dark"' in content_dark

    captured_html.clear()
    render_live_waveform_player(
        audio_bytes=audio_bytes,
        audio_format="audio/mp3",
        y=y,
        sr=sr,
        bpm_sections=sections,
        seek_time=1.0,
        theme_mode="light",
    )
    assert len(captured_html) == 1
    assert "const initialSeek = 1.0;" in captured_html[0]
    assert '"themeMode": "light"' in captured_html[0]


def test_waveform_view_dark_and_light_and_format_seconds(monkeypatch):
    """Verify static waveform fallback chart in dark/light modes and MM:SS.sss time formatting."""
    monkeypatch.setattr(st, "pyplot", lambda fig: None)
    sr = 22050
    y = np.sin(np.linspace(0, 20, sr))
    sections = [
        BPMSection(startTime=0.0, startBeat=0.0, bpm=95.0),
        BPMSection(startTime=0.5, startBeat=0.79, bpm=190.0),
    ]

    fig_dark = create_waveform_figure(y, sr, sections, selected_time=0.5, theme_mode="dark")
    assert mcolors.to_hex(fig_dark.patch.get_facecolor()) == "#0f172a"
    assert mcolors.to_hex(fig_dark.axes[0].get_facecolor()) == "#020617"
    plt.close(fig_dark)

    fig_light = render_waveform_view(y, sr, sections, selected_time=0.5, theme_mode="light")
    assert mcolors.to_hex(fig_light.patch.get_facecolor()) == "#ffffff"
    assert mcolors.to_hex(fig_light.axes[0].get_facecolor()) == "#f8fafc"

    assert format_seconds_to_min_sec(84.5) == "01:24.500"
    assert format_seconds_to_min_sec(-3.0) == "00:00.000"
