"""Waveform envelope rendering with BeatWarping tempo marker overlays."""

from typing import List, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

from audio_analysis.beat_detection import downsample_waveform
from models.song_metadata import BPMSection


def render_waveform_view(
    y: np.ndarray,
    sr: int,
    bpm_sections: List[BPMSection],
    title: str = "Audio Waveform & BeatWarping Flags",
    max_display_points: int = 1500,
    selected_time: Optional[float] = None,
) -> plt.Figure:
    """Generate and display a waveform envelope plot with BPM marker flags.
    
    Args:
        y: Audio time series.
        sr: Sample rate.
        bpm_sections: Chronologically ordered list of BPM sections.
        title: Plot title.
        max_display_points: Maximum points to render to prevent UI lag on long tracks.
        selected_time: Optional cursor/playback timestamp to highlight.
        
    Returns:
        Matplotlib Figure object.
    """
    total_duration = len(y) / float(sr)
    times, envelope = downsample_waveform(y, sr, target_points=max_display_points)

    fig, ax = plt.subplots(figsize=(12, 3.5), dpi=100)
    fig.patch.set_facecolor("#12141a")
    ax.set_facecolor("#181b24")

    # Plot mirrored amplitude envelope for visual symmetry
    ax.fill_between(times, -envelope, envelope, color="#00d4ff", alpha=0.65, label="Waveform Envelope")
    ax.plot(times, envelope, color="#5eead4", linewidth=0.7)
    ax.plot(times, -envelope, color="#5eead4", linewidth=0.7)

    # Style axes
    ax.set_xlim(0, total_duration)
    max_amp = max(0.1, float(np.max(envelope)) * 1.15)
    ax.set_ylim(-max_amp, max_amp * 1.25)
    ax.set_xlabel("Time (seconds)", color="#e2e8f0", fontsize=10)
    ax.set_ylabel("Amplitude", color="#e2e8f0", fontsize=10)
    ax.tick_params(colors="#94a3b8", labelsize=9)
    ax.grid(True, linestyle="--", alpha=0.2, color="#64748b")
    ax.set_title(title, color="#f8fafc", fontsize=12, fontweight="bold", pad=12)

    # Overlay vertical marker flags
    colors = ["#f43f5e", "#fb923c", "#facc15", "#4ade80", "#a855f7", "#ec4899"]
    for i, section in enumerate(bpm_sections):
        flag_color = colors[i % len(colors)]
        t = section.startTime
        ax.axvline(x=t, color=flag_color, linestyle="--", linewidth=1.5, alpha=0.9)

        # Label tag for marker
        label_text = f"#{i} {section.bpm:.1f} BPM\n({t:.2f}s)"
        y_pos = max_amp * 0.95 if i % 2 == 0 else max_amp * 0.70
        ax.text(
            t,
            y_pos,
            f" {label_text}",
            color="#ffffff",
            fontsize=8,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.25", facecolor=flag_color, edgecolor="none", alpha=0.85),
            verticalalignment="top",
        )

    # Highlight playback or selected position if provided
    if selected_time is not None and 0 <= selected_time <= total_duration:
        ax.axvline(x=selected_time, color="#ffffff", linestyle="-", linewidth=2.0, alpha=0.95)

    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
    return fig
