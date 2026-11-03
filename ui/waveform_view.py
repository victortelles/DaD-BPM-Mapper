"""Static Matplotlib waveform fallback chart styled with the Sky/Slate studio palette."""

from typing import List, Optional
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

from audio_analysis.beat_detection import downsample_waveform
from models.song_metadata import BPMSection


def render_waveform_view(
    y: np.ndarray,
    sr: int,
    bpm_sections: List[BPMSection],
    title: str = "Forma de Onda y Banderas de Tempo",
    max_display_points: int = 1500,
    selected_time: Optional[float] = None,
) -> plt.Figure:
    """Generate and display a Sky/Slate waveform envelope plot with BPM marker flags.

    Args:
        y: Audio time series.
        sr: Sample rate.
        bpm_sections: Chronologically ordered list of BPM sections.
        title: Plot title.
        max_display_points: Maximum points to render to prevent UI lag.
        selected_time: Optional cursor/playback timestamp to highlight.

    Returns:
        Matplotlib Figure object.
    """
    total_duration = len(y) / float(sr)
    times, envelope = downsample_waveform(y, sr, target_points=max_display_points)

    fig, ax = plt.subplots(figsize=(12, 3.2), dpi=100)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#f8fafc")

    for spine in ax.spines.values():
        spine.set_color("#e2e8f0")

    ax.fill_between(times, -envelope, envelope, color="#0284c7", alpha=0.45, label="Onda")
    ax.plot(times, envelope, color="#0284c7", linewidth=0.8)
    ax.plot(times, -envelope, color="#0284c7", linewidth=0.8)

    ax.set_xlim(0, total_duration)
    max_amp = max(0.1, float(np.max(envelope)) * 1.15)
    ax.set_ylim(-max_amp, max_amp * 1.25)
    ax.set_xlabel("Tiempo (s)", color="#0f172a", fontsize=9.5)
    ax.set_ylabel("Amplitud", color="#0f172a", fontsize=9.5)
    ax.tick_params(colors="#64748b", labelsize=8.5)
    ax.grid(True, linestyle="--", alpha=0.5, color="#e2e8f0")
    ax.set_title(title, color="#0f172a", fontsize=11, fontweight="bold", pad=10)

    colors = ["#ef4444", "#0284c7", "#0ea5e9", "#f59e0b", "#10b981", "#6366f1"]
    for i, section in enumerate(bpm_sections):
        flag_color = colors[i % len(colors)]
        t = section.startTime
        ax.axvline(x=t, color=flag_color, linestyle="--", linewidth=1.4, alpha=0.92)

        label_text = f"#{i} {section.bpm:.1f} BPM ({t:.2f}s)"
        y_pos = max_amp * 0.95 if i % 2 == 0 else max_amp * 0.68
        ax.text(
            t,
            y_pos,
            f" {label_text}",
            color="#ffffff",
            fontsize=8,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.22", facecolor=flag_color, edgecolor="none", alpha=0.9),
            verticalalignment="top",
        )

    if selected_time is not None and 0 <= selected_time <= total_duration:
        ax.axvline(x=selected_time, color="#0f172a", linestyle="-", linewidth=1.8, alpha=0.95)

    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
    return fig
