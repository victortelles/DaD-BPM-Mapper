"""Sky/Slate Light Studio design system, CSS tokens, and reusable UI primitives."""

from typing import Optional
import streamlit as st

STUDIO_THEME_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
  --background: #f8fafc;
  --foreground: #0f172a;
  --card: #ffffff;
  --card-foreground: #0f172a;
  --popover: #ffffff;
  --popover-foreground: #0f172a;
  --primary: #0284c7;
  --primary-foreground: #ffffff;
  --secondary: #e0f2fe;
  --secondary-foreground: #0369a1;
  --muted: #f1f5f9;
  --muted-foreground: #64748b;
  --accent: #0ea5e9;
  --accent-foreground: #ffffff;
  --destructive: #ef4444;
  --destructive-foreground: #ffffff;
  --border: #e2e8f0;
  --input: #e2e8f0;
  --ring: #0284c7;
  --chart-1: #0284c7;
  --chart-2: #0ea5e9;
  --chart-3: #38bdf8;
  --chart-4: #7dd3fc;
  --chart-5: #bae6fd;
  --sidebar: #ffffff;
  --sidebar-foreground: #0f172a;
  --sidebar-primary: #0284c7;
  --sidebar-primary-foreground: #ffffff;
  --sidebar-accent: #e0f2fe;
  --sidebar-accent-foreground: #0369a1;
  --sidebar-border: #e2e8f0;
  --sidebar-ring: #0284c7;
  --font-sans: Inter, system-ui, sans-serif;
  --font-serif: Georgia, serif;
  --font-mono: JetBrains Mono, monospace;
  --radius: 0.75rem;
  --shadow-2xs: 0 1px 2px 0 rgba(15, 23, 42, 0.03);
  --shadow-xs: 0 1px 2px 0 rgba(15, 23, 42, 0.05);
  --shadow-sm: 0 1px 3px 0 rgba(15, 23, 42, 0.08), 0 1px 2px -1px rgba(15, 23, 42, 0.08);
  --shadow: 0 4px 6px -1px rgba(15, 23, 42, 0.08), 0 2px 4px -2px rgba(15, 23, 42, 0.06);
  --shadow-md: 0 6px 12px -2px rgba(15, 23, 42, 0.08), 0 3px 6px -3px rgba(15, 23, 42, 0.06);
  --shadow-lg: 0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -4px rgba(15, 23, 42, 0.06);
  --shadow-xl: 0 20px 25px -5px rgba(15, 23, 42, 0.10), 0 8px 10px -6px rgba(15, 23, 42, 0.06);
  --shadow-2xl: 0 25px 50px -12px rgba(15, 23, 42, 0.22);
}

html, body, [data-testid="stAppViewContainer"], .stApp {
  background-color: var(--background) !important; color: var(--foreground) !important; font-family: var(--font-sans) !important;
}
[data-testid="stHeader"] { background-color: rgba(248, 250, 252, 0.88) !important; backdrop-filter: blur(8px); }
[data-testid="stSidebar"] { background-color: var(--sidebar) !important; border-right: 1px solid var(--sidebar-border) !important; }
.block-container { padding-top: 1.5rem !important; padding-bottom: 2.5rem !important; max-width: 1180px !important; }
h1, h2, h3, h4, h5, h6 { color: var(--foreground) !important; font-family: var(--font-sans) !important; letter-spacing: -0.02em; }
code, pre, [data-testid="stMetricValue"], .mono-val { font-family: var(--font-mono) !important; font-variant-numeric: tabular-nums; }
[data-testid="stMetric"], div[data-testid="stExpander"], div[data-testid="stForm"] {
  background-color: var(--card) !important; border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important; box-shadow: var(--shadow-xs) !important;
}
.stButton > button[kind="primary"] {
  background-color: var(--primary) !important; color: var(--primary-foreground) !important;
  border: 1px solid var(--primary) !important; border-radius: calc(var(--radius) - 0.15rem) !important;
  font-weight: 600 !important; box-shadow: var(--shadow-xs) !important;
}
.stButton > button[kind="primary"]:hover { background-color: #0369a1 !important; border-color: #0369a1 !important; }
.stButton > button[kind="secondary"] {
  background-color: var(--card) !important; color: var(--foreground) !important;
  border: 1px solid var(--border) !important; border-radius: calc(var(--radius) - 0.15rem) !important; font-weight: 500 !important;
}
.stButton > button[kind="secondary"]:hover {
  background-color: var(--secondary) !important; color: var(--secondary-foreground) !important; border-color: var(--accent) !important;
}
.dad-micro-card {
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 0.9rem 1.15rem; margin-bottom: 0.85rem; box-shadow: var(--shadow-xs);
  display: flex; justify-content: space-between; align-items: center; gap: 1rem;
}
.dad-micro-title { font-size: 1.02rem; font-weight: 700; color: var(--foreground); margin: 0 0 0.18rem 0; }
.dad-micro-sub { font-size: 0.86rem; color: var(--muted-foreground); margin: 0; }
.dad-badge {
  background: var(--secondary); color: var(--secondary-foreground); font-family: var(--font-mono);
  font-size: 0.76rem; font-weight: 600; padding: 0.25rem 0.65rem; border-radius: 999px; border: 1px solid #bae6fd; white-space: nowrap;
}
.dad-step-bar { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; margin-bottom: 1.1rem; }
.dad-step-item {
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 0.65rem 0.9rem; display: flex; align-items: center; gap: 0.65rem; box-shadow: var(--shadow-2xs);
}
.dad-step-item.active { border-color: var(--primary); background: var(--secondary); box-shadow: var(--shadow-sm); }
.dad-step-item.done { border-color: #bae6fd; background: #f0f9ff; }
.dad-step-num {
  width: 1.65rem; height: 1.65rem; border-radius: 999px; display: inline-flex; align-items: center; justify-content: center;
  font-family: var(--font-mono); font-size: 0.8rem; font-weight: 700; background: var(--muted); color: var(--muted-foreground);
}
.dad-step-item.active .dad-step-num { background: var(--primary); color: var(--primary-foreground); }
.dad-step-item.done .dad-step-num { background: var(--accent); color: var(--accent-foreground); }
.dad-step-label { font-size: 0.88rem; font-weight: 600; color: var(--foreground); }
"""


def apply_studio_theme() -> None:
    """Inject the global Sky/Slate studio stylesheet into the Streamlit app."""
    st.markdown(f"<style>{STUDIO_THEME_CSS}</style>", unsafe_allow_html=True)


def render_step_indicator(current_step: int, unlocked_step: Optional[int] = None) -> None:
    """Render the 3-step visual progress indicator bar."""
    steps = [
        (1, "1. Subir Audio", "Paso 1: Subir Audio"),
        (2, "2. Sincronizar Ritmo", "Paso 2: Sincronizar Ritmo"),
        (3, "3. Descargar Mod", "Paso 3: Descargar Mod"),
    ]
    items_html = []
    for num, short_label, full_label in steps:
        state_cls = "active" if num == current_step else ("done" if num < current_step else "")
        badge_txt = "✓" if num < current_step else str(num)
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
