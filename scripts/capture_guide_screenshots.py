"""Playwright automated screenshot capture and studio-palette banner generator for v2 Visual Guide."""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any, List, Optional, Tuple

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


def _loc_rect(loc: Any, pad: int = 4) -> Optional[Tuple[int, int, int, int]]:
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


def _annotate_banner(
    img: Image.Image,
    step_num: int,
    step_title: str,
    targets: List[Tuple[int, int, int, int]],
) -> Image.Image:
    """Draw luminous sky-blue focus borders and numbered circular badges on the cropped banner."""
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font_badge = ImageFont.truetype("segoeuib.ttf", 15)
        font_title = ImageFont.truetype("segoeuib.ttf", 15)
        font_num = ImageFont.truetype("segoeuib.ttf", 16)
    except OSError:
        font_badge = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_num = ImageFont.load_default()

    # Outer frame border (Dark slate #1e293b)
    draw.rectangle((0, 0, w - 1, h - 1), outline=(30, 41, 59, 255), width=2)

    # Top-left header pill: [ PASO X DE 4 ] <Título>
    draw.rounded_rectangle((16, 14, 430, 52), radius=10, fill=(15, 23, 42, 240), outline=(56, 189, 248, 180), width=1)
    draw.rounded_rectangle((20, 18, 145, 48), radius=7, fill=(56, 189, 248, 255))
    draw.text((28, 23), f"PASO {step_num} DE 4", fill=(2, 6, 23, 255), font=font_badge)
    draw.text((156, 23), step_title, fill=(248, 250, 252, 255), font=font_title)

    for idx, (tx0, ty0, tx1, ty1) in enumerate(targets, start=1):
        # Soft outer glow
        draw.rounded_rectangle((tx0 - 3, ty0 - 3, tx1 + 3, ty1 + 3), radius=8, outline=(56, 189, 248, 60), width=2)
        # Crisp primary focus border (#38bdf8)
        draw.rounded_rectangle((tx0, ty0, tx1, ty1), radius=8, outline=(56, 189, 248, 255), width=3)

        # Numbered circular badge placed at the top-left outer corner (never obscuring contents)
        bx, by = tx0 - 6, ty0 - 6
        draw.ellipse((bx - 14, by - 14, bx + 16, by + 16), fill=(56, 189, 248, 255), outline=(255, 255, 255, 255), width=2)
        draw.text((bx - 5, by - 9), str(idx), fill=(2, 6, 23, 255), font=font_num)

    combined = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    return combined


def _generate_step4_banner(output_path: Path) -> None:
    """Generate Step 4 installation banner from the clean screenshot with studio palette highlights."""
    clean_src = REPO_ROOT / "assets" / "guide" / "step4_clean.png"
    if not clean_src.exists():
        # Fallback to brain artifact if present
        brain_cand = Path(r"C:\Users\TellesVM\.gemini\antigravity-cli\brain\84bbf8ed-adde-4dc8-a225-cf1a13bae46e\step4_install_game_clean_1793667936089.jpg")
        if brain_cand.exists():
            clean_src = brain_cand
        else:
            return

    img = Image.open(clean_src)
    # Crop to horizontal banner (1340 x 620)
    cropped = img.crop((18, 65, 1358, 685))

    # Bounding boxes for the 3 visual steps translated into cropped coordinates:
    # 1. Win + R dialog
    # 2. Explorer folder with audio.ogg + Meta.json
    # 3. Dead as Disco custom song menu
    targets = [
        (40, 160, 470, 510),
        (490, 80, 920, 560),
        (940, 80, 1320, 590),
    ]

    annotated = _annotate_banner(cropped, 4, "Instalar en ImportedSongs", targets)
    annotated.save(output_path, format="PNG", optimize=True)


def capture_all_screenshots() -> None:
    """Launch Streamlit, drive the 3-step Wizard via Playwright, and save annotated PNG banners."""
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
                context = browser.new_context(viewport={"width": 1440, "height": 1600})
                page = context.new_page()
                page.goto(APP_URL, wait_until="networkidle")
                page.wait_for_timeout(1500)

                # Step 1: Upload multi-tempo audio (advances to Step 2)
                file_input = page.locator('input[type="file"]').first
                file_input.set_input_files(str(wav_path))
                page.wait_for_selector("text=Paso 2 de 3", timeout=30000)
                page.wait_for_timeout(1500)

                # Return to Step 1 to capture upload box + metrics summary banner
                page.get_by_role("button", name=re.compile(r"Paso 1: Subir canción", re.I)).first.click()
                page.wait_for_selector("text=Canción lista", timeout=15000)
                page.wait_for_timeout(1000)

                loc_uploader = page.locator('[data-testid="stFileUploader"]').first
                loc_metrics = page.locator('[data-testid="stMetric"]').all()
                loc_btn1 = page.get_by_role("button", name=re.compile(r"Paso 2: Escuchar y verificar|Ir al Paso 2", re.I)).first

                b_up = _loc_rect(loc_uploader, pad=4) or (220, 890, 1220, 990)
                if loc_metrics:
                    m_boxes = [m.bounding_box() for m in loc_metrics if m.bounding_box()]
                    b_met = (
                        int(min(b["x"] for b in m_boxes) - 6),
                        int(min(b["y"] for b in m_boxes) - 6),
                        int(max(b["x"] + b["width"] for b in m_boxes) + 6),
                        int(max(b["y"] + b["height"] for b in m_boxes) + 6),
                    )
                else:
                    b_met = (220, 1080, 1220, 1200)
                b_btn1 = _loc_rect(loc_btn1, pad=4) or (220, 1210, 1220, 1255)

                min_y = min(b_up[1], b_met[1], b_btn1[1]) - 70
                max_y = max(b_up[3], b_met[3], b_btn1[3]) + 25
                clip_s1 = {"x": 200, "y": max(0, min_y), "width": 1040, "height": max_y - min_y}

                raw_s1 = GUIDE_DIR / "_raw_s1.png"
                page.screenshot(path=str(raw_s1), clip=clip_s1)
                img1 = Image.open(raw_s1)
                targets_s1 = [
                    (b_up[0] - clip_s1["x"], b_up[1] - clip_s1["y"], b_up[2] - clip_s1["x"], b_up[3] - clip_s1["y"]),
                    (b_met[0] - clip_s1["x"], b_met[1] - clip_s1["y"], b_met[2] - clip_s1["x"], b_met[3] - clip_s1["y"]),
                    (b_btn1[0] - clip_s1["x"], b_btn1[1] - clip_s1["y"], b_btn1[2] - clip_s1["x"], b_btn1[3] - clip_s1["y"]),
                ]
                b1 = _annotate_banner(img1, 1, "Subir Audio Seguro", targets_s1)
                b1.save(GUIDE_DIR / "step1_upload.png", format="PNG", optimize=True)
                raw_s1.unlink(missing_ok=True)

                # Step 2: Navigate to Live Waveform Player
                page.get_by_role("button", name=re.compile(r"Paso 2: Escuchar y verificar", re.I)).first.click()
                page.wait_for_selector("text=Paso 2 de 3", timeout=15000)
                page.wait_for_timeout(2000)

                loc_iframe = page.locator("iframe").first
                loc_select = page.locator('[data-testid="stSelectbox"]').first
                loc_btn2 = page.get_by_role("button", name=re.compile(r"Continuar al Paso 3", re.I)).first

                b_ifr = _loc_rect(loc_iframe, pad=4) or (210, 760, 1230, 1180)
                b_sel = _loc_rect(loc_select, pad=4) or (210, 1240, 950, 1310)
                b_btn2 = _loc_rect(loc_btn2, pad=4) or (580, 1390, 1230, 1435)

                min_y2 = min(b_ifr[1], b_sel[1], b_btn2[1]) - 70
                max_y2 = max(b_ifr[3], b_sel[3], b_btn2[3]) + 25
                clip_s2 = {"x": 200, "y": max(0, min_y2), "width": 1040, "height": max_y2 - min_y2}

                raw_s2 = GUIDE_DIR / "_raw_s2.png"
                page.screenshot(path=str(raw_s2), clip=clip_s2)
                img2 = Image.open(raw_s2)
                targets_s2 = [
                    (b_ifr[0] - clip_s2["x"], b_ifr[1] - clip_s2["y"], b_ifr[2] - clip_s2["x"], b_ifr[1] - clip_s2["y"] + 65),
                    (b_sel[0] - clip_s2["x"], b_sel[1] - clip_s2["y"], b_sel[2] - clip_s2["x"], b_sel[3] - clip_s2["y"]),
                    (b_btn2[0] - clip_s2["x"], b_btn2[1] - clip_s2["y"], b_btn2[2] - clip_s2["x"], b_btn2[3] - clip_s2["y"]),
                ]
                b2 = _annotate_banner(img2, 2, "Verificar Ritmo y Picos", targets_s2)
                b2.save(GUIDE_DIR / "step2_sync.png", format="PNG", optimize=True)
                raw_s2.unlink(missing_ok=True)

                # Step 3: Navigate to Export Mod
                page.get_by_role("button", name=re.compile(r"Paso 3: Descargar mod", re.I)).first.click()
                page.wait_for_selector("text=Paso 3 de 3", timeout=15000)
                page.get_by_role("button", name=re.compile(r"Generar y Descargar Paquete", re.I)).first.click()
                page.wait_for_selector("text=Guardar Archivo", timeout=30000)
                page.wait_for_timeout(1000)

                loc_title = page.locator('[data-testid="stTextInput"]').first
                loc_gen = page.get_by_role("button", name=re.compile(r"Generar y Descargar Paquete", re.I)).first
                loc_exp = page.locator('button:has-text("Abrir carpeta")').first

                b_ti = _loc_rect(loc_title, pad=4) or (220, 720, 720, 765)
                b_ge = _loc_rect(loc_gen, pad=4) or (220, 810, 1220, 855)
                b_ex = _loc_rect(loc_exp, pad=4) or (220, 960, 600, 1010)

                min_y3 = min(b_ti[1], b_ge[1], b_ex[1]) - 70
                max_y3 = max(b_ti[3], b_ge[3], b_ex[3]) + 40
                clip_s3 = {"x": 200, "y": max(0, min_y3), "width": 1040, "height": max_y3 - min_y3}

                raw_s3 = GUIDE_DIR / "_raw_s3.png"
                page.screenshot(path=str(raw_s3), clip=clip_s3)
                img3 = Image.open(raw_s3)
                targets_s3 = [
                    (b_ti[0] - clip_s3["x"], b_ti[1] - clip_s3["y"], b_ti[2] - clip_s3["x"], b_ti[3] - clip_s3["y"]),
                    (b_ge[0] - clip_s3["x"], b_ge[1] - clip_s3["y"], b_ge[2] - clip_s3["x"], b_ge[3] - clip_s3["y"]),
                    (b_ex[0] - clip_s3["x"], b_ex[1] - clip_s3["y"], b_ex[2] - clip_s3["x"], b_ex[3] - clip_s3["y"]),
                ]
                b3 = _annotate_banner(img3, 3, "Descargar Paquete Mod", targets_s3)
                b3.save(GUIDE_DIR / "step3_export.png", format="PNG", optimize=True)
                raw_s3.unlink(missing_ok=True)

                browser.close()

        # Step 4: Generate banner from clean screenshot
        _generate_step4_banner(GUIDE_DIR / "step4_install_game.png")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    capture_all_screenshots()
