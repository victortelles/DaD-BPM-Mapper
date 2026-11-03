"""UI components and views for Dead as Disco BPM Mapper."""

from .flag_editor import render_flag_editor
from .guide_view import render_guide_view
from .legal_view import render_legal_view
from .live_waveform_player import render_live_waveform_player
from .player import render_audio_player
from .theme import apply_studio_theme, render_micro_card, render_step_indicator
from .waveform_view import render_waveform_view

__all__ = [
    "apply_studio_theme",
    "render_audio_player",
    "render_flag_editor",
    "render_guide_view",
    "render_legal_view",
    "render_live_waveform_player",
    "render_micro_card",
    "render_step_indicator",
    "render_waveform_view",
]
