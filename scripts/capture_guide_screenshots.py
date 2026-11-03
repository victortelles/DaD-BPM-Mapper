"""Playwright automated screenshot capture and high-contrast Pillow annotation for the v2 Visual Guide."""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
GUIDE_DIR = REPO_ROOT / "assets" / "guide"
PORT = 8519
APP_URL = f"http://127.0.0.1:{PORT}"


def _create_demo_multitempo_wav(target_dir: Path) -> Path:
    """Synthesize a 24s multi-tempo WAV track (96 BPM -> 48 BPM -> 192 BPM) for realistic demo capture."""
    sr = 22050
    duration = 24.0
    sig = np.zeros(int(sr * duration), dtype=np.float32)
    base_period = 60.0 / 96.0

    for t in np.arange(0.05, 8.0, base_period):
        idx = int(t * sr)
        sig[idx : idx + 220] = 0.65 * np.hanning(220)
    for t in np.arange(8.0, 16.0, base_period * 2.0):
        idx = int(t * sr)
        sig[idx : idx + 220] = 0.30 * np.hanning(220)
    for t in np.arange(16.0, 24.0, base_period * 0.5):
        idx = int(t * sr)
        sig[idx : idx + 220] = 0.95 * np.hanning(220)

    wav_path = target_dir / "Dead_as_Disco_MultiTempo.wav"
    sf.write(str(wav_path), sig, sr, format="WAV")
    return wav_path


def _loc_rect(loc, pad: int = 6) -> Optional[Tuple[int, int, int, int]]:
    """Query a Playwright locator's dynamic bounding box and return (x0, y0, x1, y1) with padding."""
    try:
        box = loc.bounding_box()
        if box:
            return (
                int(box["x"] - pad),
                int(box["y"] - pad),
                int(box["x"] + box["width"] + pad),
                int(box["y"] + box["height"] + pad),
            )
    except Exception:
        pass
    return None


def _enclosing_rect(locs: List[Any], pad: int = 6) -> Optional[Tuple[int, int, int, int]]:
    """Calculate the bounding box enclosing multiple Playwright locators."""
    boxes = [l.bounding_box() for l in locs if l and l.bounding_box()]
    if not boxes:
        return None
    return (
        int(min(b["x"] for b in boxes) - pad),
        int(min(b["y"] for b in boxes) - pad),
        int(max(b["x"] + b["width"] for b in boxes) + pad),
        int(max(b["y"] + b["height"] for b in boxes) + pad),
    )


def _wait_for_server(url: str, timeout_s: float = 25.0) -> None:
    """Poll the local Streamlit HTTP server until it responds."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return
        except Exception:
            time.sleep(0.4)
    raise RuntimeError(f"Streamlit server did not start within {timeout_s}s at {url}")


def _annotate_image(
    img_path: Path,
    step_badge: str,
    step_sub: str,
    callouts: List[Tuple[int, int, str, str, Optional[Tuple[int, int, int, int]]]],
) -> None:
    """Draw high-contrast red-bordered callout badges and focus frames on a captured screenshot."""
    img = Image.open(img_path).convert("RGBA")
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font_badge = ImageFont.truetype("segoeuib.ttf", 16)
        font_title = ImageFont.truetype("segoeuib.ttf", 16)
        font_sub = ImageFont.truetype("segoeuib.ttf", 13)
        font_num = ImageFont.truetype("segoeuib.ttf", 16)
    except OSError:
        font_badge = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_num = ImageFont.load_default()

    # Red outer canvas border
    draw.rectangle((0, 0, w - 1, h - 1), outline=(239, 68, 68, 255), width=5)

    # Top-left high-contrast step header banner with red border
    pill_box = (18, 12, 420, 56)
    draw.rounded_rectangle(pill_box, radius=12, fill=(15, 23, 42, 245), outline=(239, 68, 68, 255), width=3)
    draw.rounded_rectangle((24, 18, 155, 50), radius=8, fill=(239, 68, 68, 255))
    draw.text((32, 24), step_badge, fill=(255, 255, 255, 255), font=font_badge)
    draw.text((168, 24), step_sub, fill=(248, 250, 252, 255), font=font_title)

    for idx, (cx, cy, title, subtitle, target_rect) in enumerate(callouts, start=1):
        # Draw red highlight focus frame if target_rect is specified
        if target_rect:
            tx0, ty0, tx1, ty1 = target_rect
            draw.rounded_rectangle((tx0, ty0, tx1, ty1), radius=8, outline=(239, 68, 68, 255), width=4, fill=(239, 68, 68, 28))
            draw.ellipse((tx0 - 14, ty0 - 14, tx0 + 18, ty0 + 18), fill=(239, 68, 68, 255), outline=(255, 255, 255, 255), width=2)
            draw.text((tx0 - 6, ty0 - 8), str(idx), fill=(255, 255, 255, 255), font=font_num)

        # Draw red-bordered explanation card
        box_w, box_h = 425, 58
        bx0, by0 = max(16, min(w - box_w - 16, cx)), max(65, cy)
        bx1, by1 = bx0 + box_w, by0 + box_h
        draw.rounded_rectangle((bx0, by0, bx1, by1), radius=10, fill=(15, 23, 42, 245), outline=(239, 68, 68, 255), width=3)
        draw.ellipse((bx0 + 10, by0 + 12, bx0 + 40, by0 + 42), fill=(239, 68, 68, 255), outline=(255, 255, 255, 255), width=2)
        draw.text((bx0 + 19, by0 + 17), str(idx), fill=(255, 255, 255, 255), font=font_num)
        draw.text((bx0 + 48, by0 + 9), title, fill=(255, 255, 255, 255), font=font_title)
        draw.text((bx0 + 48, by0 + 31), subtitle, fill=(254, 240, 138, 255), font=font_sub)

    combined = Image.alpha_composite(img, overlay).convert("RGB")
    combined.save(img_path, format="PNG", optimize=True)


def capture_all_screenshots() -> None:
    """Launch Streamlit, drive the 3-step Wizard via Playwright, and save annotated PNGs."""
    GUIDE_DIR.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(REPO_ROOT / "app.py"),
            "--server.headless",
            "true",
            "--server.port",
            str(PORT),
            "--browser.gatherUsageStats",
            "false",
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_for_server(APP_URL)
        with tempfile.TemporaryDirectory() as tmp_dir:
            wav_path = _create_demo_multitempo_wav(Path(tmp_dir))

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": 1440, "height": 1520})
                page = context.new_page()
                page.goto(APP_URL, wait_until="networkidle")
                page.wait_for_timeout(1500)

                # Upload multi-tempo audio in Step 1 (auto-advances to Step 2)
                file_input = page.locator('input[type="file"]').first
                file_input.set_input_files(str(wav_path))
                page.wait_for_selector("text=Paso 2 de 3", timeout=30000)
                page.wait_for_timeout(1500)

                # Navigate back to Step 1 to capture the completed upload + metrics summary state
                page.get_by_role("button", name=re.compile(r"Paso 1: Subir canción", re.I)).first.click()
                page.wait_for_selector("text=Canción lista", timeout=15000)
                page.wait_for_timeout(1000)
                step1_path = GUIDE_DIR / "step1_upload.png"
                page.screenshot(path=str(step1_path), clip={"x": 0, "y": 0, "width": 1440, "height": 1340})

                loc_theme = page.locator('button:has-text("Modo"), button:has-text("Tema")').first
                loc_uploader = page.locator('[data-testid="stFileUploader"]').first
                loc_metrics = page.locator('[data-testid="stMetric"]').all()
                loc_btn1 = page.get_by_role("button", name=re.compile(r"Ir al Paso 2", re.I)).first

                box_theme = _loc_rect(loc_theme, pad=5) or (960, 104, 1230, 144)
                box_uploader = _loc_rect(loc_uploader, pad=6) or (226, 892, 1214, 990)
                box_summary = _enclosing_rect(loc_metrics + [loc_btn1], pad=8) or (226, 1092, 1214, 1235)

                _annotate_image(
                    step1_path,
                    "PASO 1 DE 4",
                    "Subida Segura + Auto-BPM",
                    [
                        (510, box_theme[1] - 8, "1. Modo Oscuro / Claro", "Alterna entre el tema oscuro y claro", box_theme),
                        (230, box_uploader[1] - 68, "2. Subida con Firewall Binario", "Valida magic bytes (.mp3/.wav/.ogg/.flac) y MD5", box_uploader),
                        (230, box_summary[1] - 68, "3. Resumen y Avance Directo", "Muestra BPM, secciones detectadas y pasa al Paso 2", box_summary),
                    ],
                )

                # Advance to Step 2 and capture the Live Waveform Player + Multi-Tempo Strip + Optional Expander
                page.get_by_role("button", name=re.compile(r"Paso 2: Escuchar y verificar", re.I)).first.click()
                page.wait_for_selector("text=Paso 2 de 3", timeout=15000)
                page.wait_for_timeout(2000)
                step2_path = GUIDE_DIR / "step2_sync.png"
                page.screenshot(path=str(step2_path), clip={"x": 0, "y": 0, "width": 1440, "height": 1520})

                loc_player = page.locator("iframe").first
                loc_select = page.locator('[data-testid="stSelectbox"]').first
                loc_continue = page.get_by_role("button", name=re.compile(r"Continuar al Paso 3", re.I)).first

                box_player = _loc_rect(loc_player, pad=6) or (210, 768, 1230, 1188)
                box_select = _loc_rect(loc_select, pad=6) or (210, 1250, 947, 1318)
                box_continue = _loc_rect(loc_continue, pad=6) or (586, 1395, 1230, 1435)

                _annotate_image(
                    step2_path,
                    "PASO 2 DE 4",
                    "Onda DAW + Metrónomo",
                    [
                        (230, box_player[1] - 68, "1. Reproductor DAW en Vivo", "Rueda: Zoom · Shift+Arrastrar: Mover · Metrónomo", box_player),
                        (min(box_select[2] + 16, 1440 - 440), box_select[1] + 5, "2. Selector de Secciones", "Menú desplegable para saltar a cada cambio de ritmo", box_select),
                        (max(20, box_continue[0] - 440), box_continue[1] - 8, "3. Continuar o Ajuste Manual", "Avanza directo al Paso 3 o abre el editor opcional", box_continue),
                    ],
                )

                # Advance to Step 3, generate the .ZIP package, and capture export view
                page.get_by_role("button", name=re.compile(r"Paso 3: Descargar mod", re.I)).first.click()
                page.wait_for_selector("text=Paso 3 de 3", timeout=15000)
                page.get_by_role("button", name=re.compile(r"Generar y Descargar Paquete", re.I)).first.click()
                page.wait_for_selector("text=Guardar Archivo", timeout=30000)
                page.wait_for_timeout(1000)
                step3_path = GUIDE_DIR / "step3_export.png"
                page.screenshot(path=str(step3_path), clip={"x": 0, "y": 0, "width": 1440, "height": 1340})

                loc_title = page.locator('input[aria-label="Título de la canción"], [data-testid="stTextInput"] input').first
                loc_gen = page.get_by_role("button", name=re.compile(r"Generar y Descargar Paquete", re.I)).first
                loc_install = page.locator('code:has-text("ImportedSongs"), [data-testid="stDownloadButton"]').all()

                box_title = _loc_rect(loc_title, pad=6) or (227, 725, 703, 761)
                box_gen = _loc_rect(loc_gen, pad=6) or (226, 817, 1214, 857)
                box_install = _enclosing_rect(loc_install, pad=8) or (226, 880, 1214, 1180)

                _annotate_image(
                    step3_path,
                    "PASO 3 DE 4",
                    "Empaquetador OGG + Meta.json",
                    [
                        (min(box_title[2] + 16, 1440 - 440), box_title[1] - 8, "1. Título y Artista del Mod", "Configura songName e intérprete para Dead as Disco", box_title),
                        (230, box_gen[1] - 68, "2. Descarga .ZIP Lista", "Incluye <Canción>/audio.ogg (44.1 kHz) + Meta.json", box_gen),
                        (230, box_install[1] - 68 if box_install else 960, "3. Instalación en 3 Pasos", "Pega %localappdata%\\Pagoda\\Saved\\ImportedSongs\\", box_install),
                    ],
                )

                browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    capture_all_screenshots()
