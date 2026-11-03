"""Sky/Slate Dual-Mode (Dark & Light) Studio design system, CSS tokens, and UI primitives."""

from typing import Dict, Optional
import streamlit as st

DARK_PALETTE: Dict[str, str] = {
    "background": "#020617",
    "foreground": "#f8fafc",
    "card": "#0f172a",
    "card_foreground": "#f8fafc",
    "popover": "#0f172a",
    "popover_foreground": "#f8fafc",
    "primary": "#38bdf8",
    "primary_foreground": "#020617",
    "secondary": "#1e293b",
    "secondary_foreground": "#f8fafc",
    "muted": "#1e293b",
    "muted_foreground": "#94a3b8",
    "accent": "#0ea5e9",
    "accent_foreground": "#f8fafc",
    "destructive": "#991b1b",
    "destructive_foreground": "#f8fafc",
    "border": "#1e293b",
    "input": "#1e293b",
    "ring": "#38bdf8",
    "chart_1": "#38bdf8",
    "chart_2": "#0ea5e9",
    "chart_3": "#0284c7",
    "chart_4": "#0369a1",
    "chart_5": "#075985",
    "sidebar": "#0f172a",
    "sidebar_foreground": "#94a3b8",
    "sidebar_primary": "#38bdf8",
    "sidebar_primary_foreground": "#020617",
    "sidebar_accent": "#1e293b",
    "sidebar_accent_foreground": "#f8fafc",
    "sidebar_border": "#1e293b",
    "sidebar_ring": "#38bdf8",
    "radius": "0.75rem",
}

LIGHT_PALETTE: Dict[str, str] = {
    "background": "#f8fafc",
    "foreground": "#0f172a",
    "card": "#ffffff",
    "card_foreground": "#0f172a",
    "popover": "#ffffff",
    "popover_foreground": "#0f172a",
    "primary": "#0284c7",
    "primary_foreground": "#ffffff",
    "secondary": "#e0f2fe",
    "secondary_foreground": "#0369a1",
    "muted": "#f1f5f9",
    "muted_foreground": "#64748b",
    "accent": "#0ea5e9",
    "accent_foreground": "#ffffff",
    "destructive": "#ef4444",
    "destructive_foreground": "#ffffff",
    "border": "#e2e8f0",
    "input": "#e2e8f0",
    "ring": "#0284c7",
    "chart_1": "#0284c7",
    "chart_2": "#0ea5e9",
    "chart_3": "#38bdf8",
    "chart_4": "#7dd3fc",
    "chart_5": "#bae6fd",
    "sidebar": "#ffffff",
    "sidebar_foreground": "#0f172a",
    "sidebar_primary": "#0284c7",
    "sidebar_primary_foreground": "#ffffff",
    "sidebar_accent": "#e0f2fe",
    "sidebar_accent_foreground": "#0369a1",
    "sidebar_border": "#e2e8f0",
    "sidebar_ring": "#0284c7",
    "radius": "0.75rem",
}

# Backward-compatible export alias
STUDIO_PALETTE: Dict[str, str] = LIGHT_PALETTE


def get_active_palette(theme_mode: str = "dark") -> Dict[str, str]:
    """Return the active theme color token dictionary ('dark' or 'light')."""
    mode = (theme_mode or "dark").strip().lower()
    return LIGHT_PALETTE if mode == "light" else DARK_PALETTE


def _format_css_vars(palette: Dict[str, str]) -> str:
    """Format a palette dictionary as CSS custom property declarations."""
    lines = [f"  --{k.replace('_', '-')}: {v};" for k, v in palette.items()]
    lines.extend([
        "  --font-sans: Inter, system-ui, sans-serif;",
        "  --font-serif: Georgia, serif;",
        "  --font-mono: 'JetBrains Mono', monospace;",
        "  --shadow-2xs: 0 1px 2px 0 rgba(15, 23, 42, 0.04);",
        "  --shadow-xs: 0 1px 2px 0 rgba(15, 23, 42, 0.06);",
        "  --shadow-sm: 0 1px 3px 0 rgba(15, 23, 42, 0.10), 0 1px 2px -1px rgba(15, 23, 42, 0.08);",
        "  --shadow-md: 0 6px 12px -2px rgba(15, 23, 42, 0.14), 0 3px 6px -3px rgba(15, 23, 42, 0.10);",
    ])
    return "\n".join(lines)


def get_theme_css(theme_mode: str = "dark") -> str:
    """Build the complete Studio CSS stylesheet for the requested theme_mode ('dark' or 'light')."""
    mode = (theme_mode or "dark").strip().lower()
    active = get_active_palette(mode)
    header_bg = "rgba(2, 6, 23, 0.88)" if mode != "light" else "rgba(248, 250, 252, 0.88)"
    hover_primary = "#0ea5e9" if mode != "light" else "#0369a1"
    done_bg = "rgba(14, 165, 233, 0.14)" if mode != "light" else "#f0f9ff"
    done_border = "#0284c7" if mode != "light" else "#bae6fd"

    return f"""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap');

:root {{
{_format_css_vars(LIGHT_PALETTE)}
}}

.dark {{
{_format_css_vars(DARK_PALETTE)}
}}

html, body, [data-testid="stAppViewContainer"], .stApp {{
{_format_css_vars(active)}
  --header-surface: {header_bg};
  background-color: var(--background) !important;
  color: var(--foreground) !important;
  font-family: var(--font-sans) !important;
}}
header[data-testid="stHeader"] {{
  height: 3.25rem !important;
  background-color: transparent !important;
  backdrop-filter: none !important;
  border-bottom: none !important;
}}
[data-testid="stSidebar"] {{
  background-color: var(--sidebar) !important;
  color: var(--sidebar-foreground) !important;
  border-right: 1px solid var(--sidebar-border) !important;
}}
.block-container {{
  padding-top: 4.5rem !important;
  padding-bottom: 2.5rem !important;
  max-width: 1180px !important;
}}
.ms-icon, .material-symbols-rounded {{
  font-family: 'Material Symbols Rounded' !important;
  font-weight: normal;
  font-style: normal;
  font-size: 1.15rem;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  vertical-align: middle;
}}
.dad-callout-red {{
  border: 2px solid #ef4444;
  border-left: 5px solid #ef4444;
  background: rgba(239, 68, 68, 0.08);
  border-radius: var(--radius);
  padding: 0.85rem 1.1rem;
  margin: 0.65rem 0;
}}
h1, h2, h3, h4, h5, h6 {{ color: var(--foreground) !important; font-family: var(--font-sans) !important; letter-spacing: -0.02em; }}
.stMarkdown, [data-testid="stMarkdownContainer"], label, p, span {{ color: var(--foreground); }}
[data-testid="stCaptionContainer"], .stCaption {{ color: var(--muted-foreground) !important; }}
code, pre, [data-testid="stMetricValue"], .mono-val {{ font-family: var(--font-mono) !important; font-variant-numeric: tabular-nums; }}
p code, li code, span code {{ background-color: var(--secondary) !important; color: var(--primary) !important; padding: 0.12rem 0.38rem !important; border-radius: 0.3rem !important; border: 1px solid var(--border) !important; }}
pre, [data-testid="stCodeBlock"] pre, [data-testid="stCode"] pre {{ background-color: var(--secondary) !important; color: var(--foreground) !important; border: 1px solid var(--border) !important; border-radius: calc(var(--radius) - 0.15rem) !important; }}
pre code, [data-testid="stCodeBlock"] code {{ background-color: transparent !important; color: var(--foreground) !important; border: none !important; }}
[data-testid="stMetric"], div[data-testid="stExpander"], div[data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"] {{
  background-color: var(--card) !important;
  color: var(--card-foreground) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow-xs) !important;
}}
[data-testid="stMetricLabel"] {{ color: var(--muted-foreground) !important; }}
[data-testid="stMetricValue"] {{ color: var(--primary) !important; }}
.stButton > button, .stDownloadButton > button, [data-testid="stFileUploaderDropzone"] button {{
  background-color: var(--card) !important;
  color: var(--foreground) !important;
  border: 1px solid var(--border) !important;
  border-radius: calc(var(--radius) - 0.15rem) !important;
  font-weight: 500 !important;
  transition: all 0.15s ease;
}}
.stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stFileUploaderDropzone"] button:hover {{
  background-color: var(--secondary) !important;
  color: var(--secondary-foreground) !important;
  border-color: var(--accent) !important;
}}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {{
  background-color: var(--primary) !important;
  color: var(--primary-foreground) !important;
  border: 1px solid var(--primary) !important;
  font-weight: 600 !important;
  box-shadow: var(--shadow-xs) !important;
}}
.stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {{
  background-color: {hover_primary} !important;
  border-color: {hover_primary} !important;
  color: var(--primary-foreground) !important;
}}
.stTextInput input, .stNumberInput input, [data-baseweb="input"] input, [data-baseweb="select"] > div {{
  background-color: var(--input) !important;
  color: var(--foreground) !important;
  border-color: var(--border) !important;
  border-radius: calc(var(--radius) - 0.2rem) !important;
}}
[data-testid="stFileUploader"], [data-testid="stFileUploaderDropzone"] {{
  background-color: var(--card) !important;
  color: var(--card-foreground) !important;
  border: 1px dashed var(--primary) !important;
  border-radius: var(--radius) !important;
}}
.stTabs [data-baseweb="tab-list"] {{ gap: 0.5rem; border-bottom: 1px solid var(--border); }}
.stTabs [data-baseweb="tab"] {{
  background-color: var(--card) !important;
  color: var(--muted-foreground) !important;
  border: 1px solid var(--border) !important;
  border-radius: calc(var(--radius) - 0.2rem) calc(var(--radius) - 0.2rem) 0 0 !important;
  padding: 0.45rem 0.9rem !important;
}}
.stTabs [aria-selected="true"] {{
  background-color: var(--secondary) !important;
  color: var(--primary) !important;
  border-bottom: 2px solid var(--primary) !important;
  font-weight: 600 !important;
}}
.stAlert, [data-testid="stNotification"] {{
  background-color: var(--card) !important;
  color: var(--card-foreground) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
}}
.stDataFrame, [data-testid="stDataFrame"], [data-testid="stTable"] {{
  background-color: var(--card) !important;
  color: var(--card-foreground) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
}}
.dad-micro-card {{
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 0.9rem 1.15rem; margin-bottom: 0.85rem; box-shadow: var(--shadow-xs);
  display: flex; justify-content: space-between; align-items: center; gap: 1rem;
}}
.dad-micro-title {{ font-size: 1.02rem; font-weight: 700; color: var(--foreground); margin: 0 0 0.18rem 0; }}
.dad-micro-sub {{ font-size: 0.86rem; color: var(--muted-foreground); margin: 0; }}
.dad-badge {{
  background: var(--secondary); color: var(--primary); font-family: var(--font-mono);
  font-size: 0.76rem; font-weight: 600; padding: 0.25rem 0.65rem; border-radius: 999px;
  border: 1px solid var(--border); white-space: nowrap; display: inline-flex; align-items: center; gap: 0.3rem;
}}
.dad-step-bar {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; margin-bottom: 1.1rem; }}
.dad-step-item {{
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 0.65rem 0.9rem; display: flex; align-items: center; gap: 0.65rem; box-shadow: var(--shadow-2xs);
}}
.dad-step-item.active {{ border-color: var(--primary); background: var(--secondary); box-shadow: var(--shadow-sm); }}
.dad-step-item.done {{ border-color: {done_border}; background: {done_bg}; }}
.dad-step-num {{
  width: 1.65rem; height: 1.65rem; border-radius: 999px; display: inline-flex; align-items: center; justify-content: center;
  font-family: var(--font-mono); font-size: 0.8rem; font-weight: 700; background: var(--muted); color: var(--muted-foreground);
}}
.dad-step-item.active .dad-step-num {{ background: var(--primary); color: var(--primary-foreground); }}
.dad-step-item.done .dad-step-num {{ background: var(--accent); color: var(--accent-foreground); }}
.dad-step-label {{ font-size: 0.88rem; font-weight: 600; color: var(--foreground); }}
"""


STUDIO_THEME_CSS: str = get_theme_css("dark")


def apply_studio_theme(theme_mode: Optional[str] = None) -> None:
    """Inject the global Sky/Slate studio stylesheet (dark or light) into the Streamlit app."""
    resolved_mode = theme_mode if theme_mode is not None else st.session_state.get("theme_mode", "dark")
    st.markdown(f"<style>{get_theme_css(resolved_mode)}</style>", unsafe_allow_html=True)


def render_step_indicator(current_step: int, unlocked_step: Optional[int] = None) -> None:
    """Render the 3-step visual progress indicator bar using Material Symbols."""
    steps = [
        (1, "1. Subir Audio", "Paso 1: Subir Audio"),
        (2, "2. Sincronizar Ritmo", "Paso 2: Sincronizar Ritmo"),
        (3, "3. Descargar Mod", "Paso 3: Descargar Mod"),
    ]
    items_html = []
    for num, short_label, full_label in steps:
        state_cls = "active" if num == current_step else ("done" if num < current_step else "")
        badge_txt = (
            '<span class="material-symbols-rounded" style="font-size:1rem;">check</span>'
            if num < current_step
            else str(num)
        )
        items_html.append(
            f'<div class="dad-step-item {state_cls}" title="{full_label}" aria-label="{full_label}">'
            f'<span class="dad-step-num">{badge_txt}</span>'
            f'<span class="dad-step-label">{short_label}</span></div>'
        )
    st.markdown(f'<div class="dad-step-bar">{"".join(items_html)}</div>', unsafe_allow_html=True)


def render_micro_card(title: str, subtitle: str, badge: str = "") -> None:
    """Render a concise studio micro-guide card header."""
    badge_html = f'<span class="dad-badge">{badge}</span>' if badge else ""
    st.markdown(
        f'<div class="dad-micro-card">'
        f'<div><p class="dad-micro-title">{title}</p><p class="dad-micro-sub">{subtitle}</p></div>'
        f"{badge_html}</div>",
        unsafe_allow_html=True,
    )
