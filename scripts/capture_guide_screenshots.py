"""Playwright automated screenshot capture and Pillow annotation for the v2 Visual Guide."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import List, Tuple

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
    callouts: List[Tuple[int, int, str, str]],
) -> None:
    """Draw clean studio callout badges on a captured screenshot using Pillow."""
    img = Image.open(img_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font_bold = ImageFont.truetype("segoeuib.ttf", 14)
        font_reg = ImageFont.truetype("segoeui.ttf", 12)
    except OSError:
        font_bold = ImageFont.load_default()
        font_reg = ImageFont.load_default()

    # Top-left step pill (keeps top-right theme toggle button and BPM badge completely clear)
    w, _ = img.size
    pill_box = (18, 12, 390, 50)
    draw.rounded_rectangle(pill_box, radius=18, fill=(15, 23, 42, 235), outline=(56, 189, 248, 255), width=2)
    draw.rounded_rectangle((24, 17, 140, 45), radius=14, fill=(2, 132, 199, 255))
    draw.text((34, 22), step_badge, fill=(248, 250, 252, 255), font=font_bold)
    draw.text((152, 23), step_sub, fill=(186, 230, 253, 255), font=font_reg)

    for idx, (cx, cy, title, subtitle) in enumerate(callouts, start=1):
        box_w, box_h = 355, 50
        bx0, by0 = max(16, min(w - box_w - 16, cx)), max(60, cy)
        bx1, by1 = bx0 + box_w, by0 + box_h
        draw.rounded_rectangle((bx0, by0, bx1, by1), radius=12, fill=(15, 23, 42, 238), outline=(56, 189, 248, 255), width=2)
        draw.ellipse((bx0 + 10, by0 + 11, bx0 + 38, by0 + 39), fill=(2, 132, 199, 255), outline=(56, 189, 248, 255), width=2)
        draw.text((bx0 + 20, by0 + 16), str(idx), fill=(255, 255, 255, 255), font=font_bold)
        draw.text((bx0 + 48, by0 + 8), title, fill=(248, 250, 252, 255), font=font_bold)
        draw.text((bx0 + 48, by0 + 27), subtitle, fill=(148, 163, 184, 255), font=font_reg)

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
                page.get_by_role("button", name="1️⃣ Subir Canción").click()
                page.wait_for_selector("text=Canción lista", timeout=15000)
                page.wait_for_timeout(1000)
                step1_path = GUIDE_DIR / "step1_upload.png"
                page.screenshot(path=str(step1_path), clip={"x": 0, "y": 0, "width": 1440, "height": 1340})
                _annotate_image(
                    step1_path,
                    "GUÍA PASO 1",
                    "Subida Segura + Auto-BPM",
                    [
                        (560, 62, "1. Modo Oscuro / Claro", "Alterna entre el tema nocturno (#020617) y claro"),
                        (910, 745, "2. Subida con Firewall Binario", "Valida magic bytes (.mp3/.wav/.ogg/.flac) y MD5"),
                        (910, 1020, "3. Resumen y Avance Directo", "Muestra BPM, secciones detectadas y pasa al Paso 2"),
                    ],
                )

                # Advance to Step 2 and capture the Live Waveform Player + Multi-Tempo Strip + Optional Expander
                page.get_by_role("button", name="2️⃣ Escuchar y Verificar").click()
                page.wait_for_selector("text=Paso 2 de 3", timeout=15000)
                page.wait_for_timeout(2000)
                step2_path = GUIDE_DIR / "step2_sync.png"
                page.screenshot(path=str(step2_path), clip={"x": 0, "y": 0, "width": 1440, "height": 1520})
                _annotate_image(
                    step2_path,
                    "GUÍA PASO 2",
                    "Onda DAW + Metrónomo",
                    [
                        (910, 665, "1. Reproductor DAW en Vivo", "Rueda: Zoom · Shift+Arrastrar: Mover · Metrónomo"),
                        (910, 1110, "2. Banderas Multi-Tempo", "Salta entre secciones (Base, Lento 0.5x, Rápido 2x)"),
                        (910, 1340, "3. Continuar o Ajuste Manual", "Avanza directo al Paso 3 o abre el editor opcional"),
                    ],
                )

                # Advance to Step 3, generate the .ZIP package, and capture export view
                page.get_by_role("button", name="3️⃣ Descargar Mod (.ZIP)").click()
                page.wait_for_selector("text=Paso 3 de 3", timeout=15000)
                page.get_by_role("button", name="📦 Generar y Descargar Paquete (.ZIP)").click()
                page.wait_for_selector("text=Guardar Archivo", timeout=30000)
                page.wait_for_timeout(1000)
                step3_path = GUIDE_DIR / "step3_export.png"
                page.screenshot(path=str(step3_path), clip={"x": 0, "y": 0, "width": 1440, "height": 1340})
                _annotate_image(
                    step3_path,
                    "GUÍA PASO 3",
                    "Empaquetador OGG + Meta.json",
                    [
                        (910, 625, "1. Título y Artista del Mod", "Configura songName e intérprete para Dead as Disco"),
                        (910, 885, "2. Descarga .ZIP Lista", "Incluye <Canción>/audio.ogg (44.1 kHz) + Meta.json"),
                        (910, 1085, "3. Instalación en 3 Pasos", "Pega %localappdata%\\Pagoda\\Saved\\ImportedSongs\\"),
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
