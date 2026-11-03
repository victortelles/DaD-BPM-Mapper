"""Playwright automated screenshot capture and amber-palette banner generator for v2 Visual Guide."""

from __future__ import annotations

import re
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

AMBER_PRIMARY = (245, 158, 11, 255)       # #f59e0b
AMBER_GLOW = (245, 158, 11, 45)
DARK_BG = (15, 23, 42, 240)               # #0f172a
FRAME_BORDER = (30, 41, 59, 255)          # #1e293b
TEXT_DARK = (2, 6, 23, 255)               # #020617
TEXT_LIGHT = (248, 250, 252, 255)         # #f8fafc


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


def _draw_xbox_controller(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float = 1.0) -> None:
    """Draw a vector Xbox-style controller with glowing buttons and D-pad in PIL."""
    w, h = int(120 * scale), int(76 * scale)
    x0, y0 = cx - w // 2, cy - h // 2
    x1, y1 = x0 + w, y0 + h

    draw.rounded_rectangle((x0, y0, x1, y1), radius=int(22 * scale), fill=(30, 41, 59, 250), outline=(245, 158, 11, 240), width=2)
    draw.arc((x0 + int(30 * scale), y0 + int(35 * scale), x1 - int(30 * scale), y1 + int(30 * scale)), start=0, end=180, fill=(15, 23, 42, 250), width=int(14 * scale))

    ls_x, ls_y = x0 + int(32 * scale), y0 + int(30 * scale)
    draw.ellipse((ls_x - 11, ls_y - 11, ls_x + 11, ls_y + 11), fill=(15, 23, 42), outline=(148, 163, 184), width=2)
    draw.ellipse((ls_x - 5, ls_y - 5, ls_x + 5, ls_y + 5), fill=(56, 189, 248))

    rs_x, rs_y = x0 + int(55 * scale), y0 + int(50 * scale)
    draw.ellipse((rs_x - 10, rs_y - 10, rs_x + 10, rs_y + 10), fill=(15, 23, 42), outline=(148, 163, 184), width=2)

    dp_x, dp_y = x0 + int(32 * scale), y0 + int(50 * scale)
    draw.rectangle((dp_x - 3, dp_y - 8, dp_x + 3, dp_y + 8), fill=(148, 163, 184))
    draw.rectangle((dp_x - 8, dp_y - 3, dp_x + 8, dp_y + 3), fill=(148, 163, 184))

    abxy_x, abxy_y = x0 + int(88 * scale), y0 + int(32 * scale)
    r_btn = 4 * scale
    draw.ellipse((abxy_x - r_btn, abxy_y - 10 * scale - r_btn, abxy_x + r_btn, abxy_y - 10 * scale + r_btn), fill=(251, 191, 36))
    draw.ellipse((abxy_x - r_btn, abxy_y + 10 * scale - r_btn, abxy_x + r_btn, abxy_y + 10 * scale + r_btn), fill=(16, 185, 129))
    draw.ellipse((abxy_x - 10 * scale - r_btn, abxy_y - r_btn, abxy_x - 10 * scale + r_btn, abxy_y + r_btn), fill=(56, 189, 248))
    draw.ellipse((abxy_x + 10 * scale - r_btn, abxy_y - r_btn, abxy_x + 10 * scale + r_btn, abxy_y + r_btn), fill=(239, 68, 68))
    draw.ellipse((cx - 7, y0 + 16, cx + 7, y0 + 30), fill=(248, 250, 252), outline=(245, 158, 11), width=1)


def _annotate_banner_amber(
    img: Image.Image,
    step_num: int,
    step_title: str,
    targets: List[Tuple[int, int, int, int]],
) -> Image.Image:
    """Draw luminous amber focus borders and numbered circular badges on the cropped banner."""
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_badge = ImageFont.truetype("segoeuib.ttf", 15)
    font_title = ImageFont.truetype("segoeuib.ttf", 15)
    font_num = ImageFont.truetype("segoeuib.ttf", 16)

    draw.rectangle((0, 0, w - 1, h - 1), outline=FRAME_BORDER, width=2)
    draw.rounded_rectangle((16, 14, 430, 52), radius=10, fill=DARK_BG, outline=AMBER_PRIMARY, width=1)
    draw.rounded_rectangle((20, 18, 145, 48), radius=7, fill=AMBER_PRIMARY)
    draw.text((28, 23), f"PASO {step_num} DE 4", fill=TEXT_DARK, font=font_badge)
    draw.text((156, 23), step_title, fill=TEXT_LIGHT, font=font_title)

    for idx, (tx0, ty0, tx1, ty1) in enumerate(targets, start=1):
        draw.rounded_rectangle((tx0 - 3, ty0 - 3, tx1 + 3, ty1 + 3), radius=8, outline=AMBER_GLOW, width=2)
        draw.rounded_rectangle((tx0, ty0, tx1, ty1), radius=8, outline=AMBER_PRIMARY, width=3)

        bx, by = tx0 - 6, ty0 - 6
        draw.ellipse((bx - 14, by - 14, bx + 16, by + 16), fill=AMBER_PRIMARY, outline=(255, 255, 255, 255), width=2)
        draw.text((bx - 5, by - 9), str(idx), fill=TEXT_DARK, font=font_num)

    combined = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    return combined


def _generate_step4_banner(output_path: Path) -> None:
    """Generate Step 4 installation banner from clean screenshot with Xbox controller icon (no highlight boxes)."""
    clean_src = REPO_ROOT / "assets" / "guide" / "step4_clean.png"
    if not clean_src.exists():
        brain_cand = Path(r"C:\Users\TellesVM\.gemini\antigravity-cli\brain\84bbf8ed-adde-4dc8-a225-cf1a13bae46e\step4_install_game_clean_1793667936089.jpg")
        if brain_cand.exists():
            clean_src = brain_cand
        else:
            return

    img4 = Image.open(clean_src).crop((18, 65, 1358, 685))
    overlay4 = Image.new("RGBA", img4.size, (0, 0, 0, 0))
    d4 = ImageDraw.Draw(overlay4)

    d4.rounded_rectangle((16, 14, 430, 52), radius=10, fill=DARK_BG, outline=AMBER_PRIMARY, width=1)
    d4.rounded_rectangle((20, 18, 145, 48), radius=7, fill=AMBER_PRIMARY)
    d4.text((28, 23), "PASO 4 DE 4", fill=TEXT_DARK, font=ImageFont.truetype("segoeuib.ttf", 15))
    d4.text((156, 23), "Instalar y Jugar al Ritmo", fill=TEXT_LIGHT, font=ImageFont.truetype("segoeuib.ttf", 15))

    d4.rectangle((0, 0, img4.size[0] - 1, img4.size[1] - 1), outline=FRAME_BORDER, width=2)

    ctrl_card = (1030, 16, 1310, 110)
    d4.rounded_rectangle(ctrl_card, radius=12, fill=(15, 23, 42, 245), outline=AMBER_PRIMARY, width=2)
    _draw_xbox_controller(d4, cx=1090, cy=63, scale=0.75)
    font_bold = ImageFont.truetype("segoeuib.ttf", 14)
    font_sub = ImageFont.truetype("segoeui.ttf", 11)
    d4.text((1145, 34), "DEAD AS DISCO", fill=(245, 158, 11), font=font_bold)
    d4.text((1145, 54), "Listo para jugar con mando", fill=(248, 250, 252), font=font_sub)
    d4.text((1145, 72), "y ritmo sincronizado", fill=(148, 163, 184), font=font_sub)

    ann4 = Image.alpha_composite(img4.convert("RGBA"), overlay4).convert("RGB")
    ann4.save(output_path, format="PNG", optimize=True)


def capture_all_screenshots() -> None:
    """Launch Streamlit, drive the 3-step Wizard via Playwright, and save amber-palette PNG banners."""
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
                context = browser.new_context(viewport={"width": 1600, "height": 2400})
                page = context.new_page()
                page.goto(APP_URL, wait_until="networkidle")
                page.wait_for_timeout(1500)

                # Collapse sidebar to prevent it appearing in screenshots
                collapse_btn = page.locator('[data-testid="stSidebarCollapseButton"]').first
                if collapse_btn.is_visible():
                    collapse_btn.click()
                    page.wait_for_timeout(800)

                # Upload audio in Step 1
                file_input = page.locator('input[type="file"]').first
                file_input.set_input_files(str(wav_path))
                page.wait_for_selector("text=Paso 2 de 3", timeout=30000)
                page.wait_for_timeout(1500)

                # Return to Step 1
                page.get_by_role("button", name="Paso 1: Subir canción").first.click()
                page.wait_for_selector("text=Canción lista", timeout=15000)
                page.wait_for_timeout(1000)

                loc_uploader = page.locator('[data-testid="stFileUploader"]').first
                loc_metrics = page.locator('[data-testid="stMetric"]').all()
                loc_btn1 = page.locator('button:has-text("Ir al Paso 2")').first

                b_up = loc_uploader.bounding_box()
                m_boxes = [m.bounding_box() for m in loc_metrics if m.bounding_box()]
                b_met = {
                    "x": min(b["x"] for b in m_boxes),
                    "y": min(b["y"] for b in m_boxes),
                    "width": max(b["x"] + b["width"] for b in m_boxes) - min(b["x"] for b in m_boxes),
                    "height": max(b["y"] + b["height"] for b in m_boxes) - min(b["y"] for b in m_boxes),
                }
                b_btn1 = loc_btn1.bounding_box()

                min_x = int(min(b_up["x"], b_met["x"], b_btn1["x"]) - 24)
                max_x = int(max(b_up["x"] + b_up["width"], b_met["x"] + b_met["width"], b_btn1["x"] + b_btn1["width"]) + 24)
                min_y = int(b_up["y"] - 75)
                max_y = int(b_btn1["y"] + b_btn1["height"] + 25)

                clip_s1 = {"x": min_x, "y": min_y, "width": max_x - min_x, "height": max_y - min_y}
                raw_s1 = GUIDE_DIR / "_raw_s1.png"
                page.screenshot(path=str(raw_s1), clip=clip_s1)
                img1 = Image.open(raw_s1)
                targets_s1 = [
                    (int(b_up["x"] - min_x), int(b_up["y"] - min_y), int(b_up["x"] + b_up["width"] - min_x), int(b_up["y"] + b_up["height"] - min_y)),
                    (int(b_met["x"] - min_x), int(b_met["y"] - min_y), int(b_met["x"] + b_met["width"] - min_x), int(b_met["y"] + b_met["height"] - min_y)),
                    (int(b_btn1["x"] - min_x), int(b_btn1["y"] - min_y), int(b_btn1["x"] + b_btn1["width"] - min_x), int(b_btn1["y"] + b_btn1["height"] - min_y)),
                ]
                ann1 = _annotate_banner_amber(img1, 1, "Subir Audio Seguro", targets_s1)
                ann1.save(GUIDE_DIR / "step1_upload.png", format="PNG", optimize=True)
                raw_s1.unlink(missing_ok=True)

                # Step 2: Navigate to Live Waveform Player
                page.get_by_role("button", name="Paso 2: Escuchar y verificar").first.click()
                page.wait_for_selector("text=Paso 2 de 3", timeout=15000)
                page.wait_for_timeout(2000)

                loc_iframe = page.locator("iframe").first
                loc_select = page.locator('[data-testid="stSelectbox"]').first
                loc_btn2 = page.locator('button:has-text("Suena bien")').first

                b_ifr = loc_iframe.bounding_box()
                b_sel = loc_select.bounding_box()
                b_btn2 = loc_btn2.bounding_box()

                min_x2 = int(min(b_ifr["x"], b_sel["x"], b_btn2["x"]) - 24)
                max_x2 = int(max(b_ifr["x"] + b_ifr["width"], b_sel["x"] + b_sel["width"], b_btn2["x"] + b_btn2["width"]) + 24)
                min_y2 = int(b_ifr["y"] - 75)
                max_y2 = int(b_btn2["y"] + b_btn2["height"] + 25)

                clip_s2 = {"x": min_x2, "y": min_y2, "width": max_x2 - min_x2, "height": max_y2 - min_y2}
                raw_s2 = GUIDE_DIR / "_raw_s2.png"
                page.screenshot(path=str(raw_s2), clip=clip_s2)
                img2 = Image.open(raw_s2)
                targets_s2 = [
                    (int(b_ifr["x"] - min_x2), int(b_ifr["y"] - min_y2), int(b_ifr["x"] + b_ifr["width"] - min_x2), int(b_ifr["y"] - min_y2 + 65)),
                    (int(b_sel["x"] - min_x2), int(b_sel["y"] - min_y2), int(b_sel["x"] + b_sel["width"] - min_x2), int(b_sel["y"] + b_sel["height"] - min_y2)),
                    (int(b_btn2["x"] - min_x2), int(b_btn2["y"] - min_y2), int(b_btn2["x"] + b_btn2["width"] - min_x2), int(b_btn2["y"] + b_btn2["height"] - min_y2)),
                ]
                ann2 = _annotate_banner_amber(img2, 2, "Verificar Ritmo y Picos", targets_s2)
                ann2.save(GUIDE_DIR / "step2_sync.png", format="PNG", optimize=True)
                raw_s2.unlink(missing_ok=True)

                # Step 3: Navigate to Export Mod
                page.get_by_role("button", name="Paso 3: Descargar mod").first.click()
                page.wait_for_selector("text=Paso 3 de 3", timeout=15000)
                page.get_by_role("button", name="Generar y Descargar Paquete").first.click()
                page.wait_for_selector("text=Guardar Archivo", timeout=30000)
                page.wait_for_timeout(1000)

                loc_title = page.locator('[data-testid="stTextInput"]').first
                loc_gen = page.get_by_role("button", name="Generar y Descargar Paquete").first
                loc_open = page.locator('button:has-text("Abrir carpeta")').first

                b_ti = loc_title.bounding_box()
                b_ge = loc_gen.bounding_box()
                b_op = loc_open.bounding_box()

                min_x3 = int(min(b_ti["x"], b_ge["x"], b_op["x"]) - 24)
                max_x3 = int(max(b_ti["x"] + b_ti["width"], b_ge["x"] + b_ge["width"], b_op["x"] + b_op["width"]) + 24)
                min_y3 = int(b_ti["y"] - 75)
                max_y3 = int(b_op["y"] + b_op["height"] + 55)

                clip_s3 = {"x": min_x3, "y": min_y3, "width": max_x3 - min_x3, "height": max_y3 - min_y3}
                raw_s3 = GUIDE_DIR / "_raw_s3.png"
                page.screenshot(path=str(raw_s3), clip=clip_s3)
                img3 = Image.open(raw_s3)
                targets_s3 = [
                    (int(b_ti["x"] - min_x3), int(b_ti["y"] - min_y3), int(b_ti["x"] + b_ti["width"] - min_x3), int(b_ti["y"] + b_ti["height"] - min_y3)),
                    (int(b_ge["x"] - min_x3), int(b_ge["y"] - min_y3), int(b_ge["x"] + b_ge["width"] - min_x3), int(b_ge["y"] + b_ge["height"] - min_y3)),
                    (int(b_op["x"] - min_x3), int(b_op["y"] - min_y3), int(b_op["x"] + b_op["width"] - min_x3), int(b_op["y"] + b_op["height"] - min_y3)),
                ]
                ann3 = _annotate_banner_amber(img3, 3, "Descargar Paquete Mod", targets_s3)
                ann3.save(GUIDE_DIR / "step3_export.png", format="PNG", optimize=True)
                raw_s3.unlink(missing_ok=True)

                browser.close()

        _generate_step4_banner(GUIDE_DIR / "step4_install_game.png")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    capture_all_screenshots()
