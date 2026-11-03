"""Static Matplotlib waveform fallback chart styled with the Dual-Mode Sky/Slate studio palette."""

from typing import List, Optional
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

from audio_analysis.beat_detection import downsample_waveform
from models.song_metadata import BPMSection


def create_waveform_figure(
    y: np.ndarray,
    sr: int,
    bpm_sections: List[BPMSection],
    title: str = "Forma de Onda y Banderas de Tempo",
    max_display_points: int = 1500,
    selected_time: Optional[float] = None,
    theme_mode: str = "dark",
) -> plt.Figure:
    """Create a Matplotlib waveform envelope figure with BPM marker flags for 'dark' or 'light' mode."""
    is_light = (theme_mode or "dark").strip().lower() == "light"
    fig_bg = "#ffffff" if is_light else "#0f172a"
    ax_bg = "#f8fafc" if is_light else "#020617"
    fg_color = "#0f172a" if is_light else "#f8fafc"
    muted_color = "#64748b" if is_light else "#94a3b8"
    border_color = "#e2e8f0" if is_light else "#1e293b"
    wave_color = "#0284c7" if is_light else "#38bdf8"

    total_duration = len(y) / float(sr)
    times, envelope = downsample_waveform(y, sr, target_points=max_display_points)

    fig, ax = plt.subplots(figsize=(12, 3.2), dpi=100)
    fig.patch.set_facecolor(fig_bg)
    ax.set_facecolor(ax_bg)

    for spine in ax.spines.values():
        spine.set_color(border_color)

    ax.fill_between(times, -envelope, envelope, color=wave_color, alpha=0.45, label="Onda")
    ax.plot(times, envelope, color=wave_color, linewidth=0.8)
    ax.plot(times, -envelope, color=wave_color, linewidth=0.8)

    ax.set_xlim(0, total_duration)
    max_amp = max(0.1, float(np.max(envelope)) * 1.15)
    ax.set_ylim(-max_amp, max_amp * 1.25)
    ax.set_xlabel("Tiempo (s)", color=fg_color, fontsize=9.5)
    ax.set_ylabel("Amplitud", color=fg_color, fontsize=9.5)
    ax.tick_params(colors=muted_color, labelsize=8.5)
    ax.grid(True, linestyle="--", alpha=0.5, color=border_color)
    ax.set_title(title, color=fg_color, fontsize=11, fontweight="bold", pad=10)

    colors = ["#38bdf8", "#f59e0b", "#10b981", "#a855f7", "#f43f5e"]
    for i, section in enumerate(bpm_sections):
        flag_color = colors[i % len(colors)]
        t = section.startTime
        ax.axvline(x=t, color=flag_color, linestyle="--", linewidth=1.4, alpha=0.92)

        label_text = f"#{i + 1} · {section.bpm:.1f} BPM ({t:.2f}s)"
        y_pos = max_amp * 0.95 if i % 2 == 0 else max_amp * 0.68
        ax.text(
            t,
            y_pos,
            f" {label_text}",
            color="#020617",
            fontsize=8,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.22", facecolor=flag_color, edgecolor="none", alpha=0.92),
            verticalalignment="top",
        )

    if selected_time is not None and 0 <= selected_time <= total_duration:
        ax.axvline(x=selected_time, color=fg_color, linestyle="-", linewidth=1.8, alpha=0.95)

    plt.tight_layout()
    return fig


def render_waveform_view(
    y: np.ndarray,
    sr: int,
    bpm_sections: List[BPMSection],
    title: str = "Forma de Onda y Banderas de Tempo",
    max_display_points: int = 1500,
    selected_time: Optional[float] = None,
    theme_mode: Optional[str] = None,
) -> plt.Figure:
    """Generate and display a Dual-Theme Sky/Slate waveform envelope plot with BPM marker flags."""
    resolved_theme = (
        theme_mode
        if theme_mode is not None
        else st.session_state.get("theme_mode", "dark")
    )
    fig = create_waveform_figure(
        y=y,
        sr=sr,
        bpm_sections=bpm_sections,
        title=title,
        max_display_points=max_display_points,
        selected_time=selected_time,
        theme_mode=resolved_theme,
    )
    st.pyplot(fig)
    plt.close(fig)
    return fig
