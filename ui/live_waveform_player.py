"""Live interactive waveform editor and audio player component for Streamlit.

Provides a synchronized HTML5 Canvas + Audio player with real-time moving playhead,
multi-level zoom, scrubbing, playback controls, and BeatWarping flag overlays.
"""

import base64
import json
from typing import List, Optional
import numpy as np
import streamlit as st
import streamlit.components.v1 as components

from audio_analysis.beat_detection import downsample_waveform
from models.song_metadata import BPMSection


def render_live_waveform_player(
    audio_bytes: bytes,
    audio_format: str,
    y: np.ndarray,
    sr: int,
    bpm_sections: List[BPMSection],
    title: str = "Live Waveform & BeatWarping Editor",
    height: int = 500,
) -> None:
    """Render the live interactive waveform editor with audio playback and real-time playhead.

    Args:
        audio_bytes: Raw audio bytes of the track.
        audio_format: MIME type (e.g. 'audio/mp3', 'audio/ogg', 'audio/wav').
        y: Audio time series numpy array.
        sr: Sample rate.
        bpm_sections: Chronologically ordered list of BPM sections.
        title: Component header.
        height: Iframe height in pixels.
    """
    total_duration = len(y) / float(sr)
    times, envelope = downsample_waveform(y, sr, target_points=2400)

    # Normalize envelope to [0.0, 1.0] for consistent rendering
    max_val = float(np.max(envelope)) if len(envelope) > 0 else 1.0
    if max_val > 1e-6:
        norm_envelope = (envelope / max_val).tolist()
    else:
        norm_envelope = [0.0] * len(envelope)

    # Encode audio as data URI
    b64_audio = base64.b64encode(audio_bytes).decode("ascii")
    data_uri = f"data:{audio_format};base64,{b64_audio}"

    # Serialize sections
    sections_data = [
        {
            "index": i,
            "startTime": round(s.startTime, 3),
            "startBeat": round(s.startBeat, 3),
            "bpm": round(s.bpm, 2),
        }
        for i, s in enumerate(bpm_sections)
    ]

    payload_json = json.dumps(
        {
            "duration": total_duration,
            "envelope": norm_envelope,
            "sections": sections_data,
        }
    )

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<style>
  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    user-select: none;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }}
  body {{
    background-color: #12141a;
    color: #e2e8f0;
    padding: 12px;
    overflow: hidden;
  }}
  .player-card {{
    background: #181b24;
    border: 1px solid #282e3d;
    border-radius: 10px;
    padding: 14px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
  }}
  .header-bar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
    border-bottom: 1px solid #232938;
    padding-bottom: 8px;
  }}
  .header-title {{
    font-size: 14px;
    font-weight: 700;
    color: #38bdf8;
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .time-display {{
    font-family: "Courier New", Courier, monospace;
    font-size: 16px;
    font-weight: bold;
    color: #f8fafc;
    background: #0f1218;
    padding: 4px 12px;
    border-radius: 6px;
    border: 1px solid #2d3748;
    letter-spacing: 0.5px;
  }}
  .time-current {{
    color: #00d4ff;
  }}

  /* Waveform container with horizontal scroll for zoom */
  .waveform-wrapper {{
    position: relative;
    width: 100%;
    height: 220px;
    background: #0c0e12;
    border: 1px solid #232938;
    border-radius: 8px;
    overflow-x: auto;
    overflow-y: hidden;
    cursor: crosshair;
  }}
  .waveform-wrapper::-webkit-scrollbar {{
    height: 8px;
  }}
  .waveform-wrapper::-webkit-scrollbar-track {{
    background: #12141a;
  }}
  .waveform-wrapper::-webkit-scrollbar-thumb {{
    background: #2e384d;
    border-radius: 4px;
  }}
  .waveform-wrapper::-webkit-scrollbar-thumb:hover {{
    background: #00d4ff;
  }}
  #waveCanvas {{
    display: block;
    height: 220px;
  }}

  /* Controls layout */
  .controls-row {{
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    margin-top: 12px;
    gap: 10px;
  }}
  .btn-group {{
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  button {{
    background: #252a37;
    color: #e2e8f0;
    border: 1px solid #3b4254;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }}
  button:hover {{
    background: #333a4c;
    border-color: #00d4ff;
    color: #ffffff;
  }}
  button:active {{
    transform: scale(0.97);
  }}
  .btn-primary {{
    background: #0284c7;
    border-color: #38bdf8;
    color: #ffffff;
  }}
  .btn-primary:hover {{
    background: #0369a1;
    border-color: #7dd3fc;
  }}
  .btn-danger {{
    background: #be123c;
    border-color: #f43f5e;
  }}
  .btn-danger:hover {{
    background: #9f1239;
  }}

  /* Zoom controls */
  .zoom-controls {{
    display: flex;
    align-items: center;
    gap: 8px;
    background: #11141c;
    padding: 4px 10px;
    border-radius: 6px;
    border: 1px solid #232938;
  }}
  .zoom-label {{
    font-size: 12px;
    color: #94a3b8;
    font-weight: 600;
  }}
  input[type="range"] {{
    accent-color: #00d4ff;
    cursor: pointer;
  }}
  .zoom-preset {{
    padding: 3px 8px;
    font-size: 11px;
    border-radius: 4px;
  }}

  /* Quick status badge */
  .status-badge {{
    font-size: 12px;
    color: #94a3b8;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .copy-notice {{
    font-size: 11px;
    color: #4ade80;
    margin-left: 6px;
    opacity: 0;
    transition: opacity 0.3s ease;
  }}
  .copy-notice.show {{
    opacity: 1;
  }}
</style>
</head>
<body>

<div class="player-card">
  <!-- Header Bar -->
  <div class="header-bar">
    <div class="header-title">
      <span>🎛️ Editor y Reproductor de Onda en Vivo</span>
    </div>
    <div class="time-display">
      <span class="time-current" id="timeCurrent">00:00.000</span> / <span id="timeTotal">00:00.000</span>
    </div>
  </div>

  <!-- Scrollable Interactive Waveform Canvas -->
  <div class="waveform-wrapper" id="waveWrapper">
    <canvas id="waveCanvas"></canvas>
  </div>

  <!-- Transport & Zoom Controls -->
  <div class="controls-row">
    <!-- Playback buttons -->
    <div class="btn-group">
      <button id="btnPlayPause" class="btn-primary">▶ Reproducir</button>
      <button id="btnStop">⏹ Detener</button>
      <button id="btnSkipBack" title="Retroceder 5 segundos">⏪ -5s</button>
      <button id="btnSkipFwd" title="Avanzar 5 segundos">⏩ +5s</button>
      
      <!-- Speed selector -->
      <button id="btnSpeed" title="Velocidad de reproducción">1.0x</button>
    </div>

    <!-- Zoom & Follow Controls -->
    <div class="zoom-controls">
      <span class="zoom-label">🔍 Zoom:</span>
      <input type="range" id="zoomSlider" min="1" max="25" value="1" step="0.5" style="width: 110px;">
      <span id="zoomValue" style="font-size: 12px; font-weight: bold; min-width: 32px; color: #38bdf8;">1x</span>
      <button class="zoom-preset" id="btnZoomFit">Ajustar</button>
      <button class="zoom-preset" id="btnZoom5x">5x</button>
      <button class="zoom-preset" id="btnZoom15x">15x</button>

      <label style="display: flex; align-items: center; gap: 4px; font-size: 11px; color: #94a3b8; cursor: pointer; margin-left: 6px;">
        <input type="checkbox" id="chkFollow" checked> Seguir
      </label>
    </div>

    <!-- Capture time for flags -->
    <div class="btn-group">
      <button id="btnCopyTime" title="Copiar tiempo del cursor al portapapeles">📋 Copiar Tiempo (<span id="btnTimeSec">0.000s</span>)</button>
      <span class="copy-notice" id="copyNotice">✓ ¡Copiado!</span>
    </div>
  </div>
</div>

<audio id="audioElement" src="{data_uri}" preload="auto"></audio>

<script>
  const data = {payload_json};
  const duration = data.duration || 1.0;
  const envelope = data.envelope || [];
  const sections = data.sections || [];

  const audio = document.getElementById("audioElement");
  const canvas = document.getElementById("waveCanvas");
  const ctx = canvas.getContext("2d");
  const wrapper = document.getElementById("waveWrapper");

  const btnPlayPause = document.getElementById("btnPlayPause");
  const btnStop = document.getElementById("btnStop");
  const btnSkipBack = document.getElementById("btnSkipBack");
  const btnSkipFwd = document.getElementById("btnSkipFwd");
  const btnSpeed = document.getElementById("btnSpeed");
  const timeCurrent = document.getElementById("timeCurrent");
  const timeTotal = document.getElementById("timeTotal");
  const btnTimeSec = document.getElementById("btnTimeSec");
  const btnCopyTime = document.getElementById("btnCopyTime");
  const copyNotice = document.getElementById("copyNotice");

  const zoomSlider = document.getElementById("zoomSlider");
  const zoomValue = document.getElementById("zoomValue");
  const btnZoomFit = document.getElementById("btnZoomFit");
  const btnZoom5x = document.getElementById("btnZoom5x");
  const btnZoom15x = document.getElementById("btnZoom15x");
  const chkFollow = document.getElementById("chkFollow");

  let zoomLevel = 1.0;
  let isDragging = false;
  let hoverTime = null;
  const flagColors = ["#f43f5e", "#fb923c", "#facc15", "#4ade80", "#a855f7", "#ec4899", "#38bdf8"];
  const speeds = [0.5, 0.75, 1.0, 1.25, 1.5];
  let speedIdx = 2;

  function formatTime(sec) {{
    if (isNaN(sec) || sec < 0) sec = 0;
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    const ms = Math.floor((sec % 1) * 1000);
    return `${{m.toString().padStart(2, '0')}}:${{s.toString().padStart(2, '0')}}.${{ms.toString().padStart(3, '0')}}`;
  }}

  timeTotal.innerText = formatTime(duration);

  // Resize canvas according to zoom level
  function resizeCanvas() {{
    const baseWidth = wrapper.clientWidth || 900;
    const targetWidth = Math.max(baseWidth, Math.round(baseWidth * zoomLevel));
    canvas.width = targetWidth;
    canvas.height = 220;
    draw();
  }}

  window.addEventListener("resize", resizeCanvas);

  // Drawing function
  function draw() {{
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const rulerHeight = 24;
    const waveTop = rulerHeight;
    const waveHeight = h - rulerHeight;
    const midY = waveTop + waveHeight / 2;

    // 1. Draw Background
    ctx.fillStyle = "#0c0e12";
    ctx.fillRect(0, 0, w, h);

    // 2. Draw Time Ruler (ticks)
    ctx.fillStyle = "#151922";
    ctx.fillRect(0, 0, w, rulerHeight);
    ctx.strokeStyle = "#283142";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, rulerHeight);
    ctx.lineTo(w, rulerHeight);
    ctx.stroke();

    // Determine ruler step based on zoom
    let stepSec = 5;
    if (zoomLevel > 15) stepSec = 0.5;
    else if (zoomLevel > 7) stepSec = 1;
    else if (zoomLevel > 3) stepSec = 2;
    else if (zoomLevel <= 1.2) stepSec = Math.max(5, Math.round(duration / 10));

    ctx.fillStyle = "#64748b";
    ctx.font = "10px sans-serif";
    for (let t = 0; t <= duration; t += stepSec) {{
      const x = (t / duration) * w;
      ctx.beginPath();
      ctx.moveTo(x, rulerHeight - 8);
      ctx.lineTo(x, rulerHeight);
      ctx.strokeStyle = "#475569";
      ctx.stroke();

      const timeLabel = t >= 60 ? `${{Math.floor(t / 60)}}m${{Math.round(t % 60)}}s` : `${{t.toFixed(stepSec < 1 ? 1 : 0)}}s`;
      ctx.fillText(timeLabel, x + 3, rulerHeight - 10);
    }}

    // 3. Draw Waveform Envelope
    const n = envelope.length;
    if (n > 1) {{
      const grad = ctx.createLinearGradient(0, waveTop, 0, h);
      grad.addColorStop(0, "#00d4ff");
      grad.addColorStop(0.5, "#0284c7");
      grad.addColorStop(1, "#00d4ff");

      ctx.fillStyle = grad;
      ctx.beginPath();

      // Top contour
      ctx.moveTo(0, midY);
      for (let i = 0; i < n; i++) {{
        const x = (i / (n - 1)) * w;
        const amp = envelope[i] * (waveHeight * 0.45);
        ctx.lineTo(x, midY - amp);
      }}

      // Bottom contour
      for (let i = n - 1; i >= 0; i--) {{
        const x = (i / (n - 1)) * w;
        const amp = envelope[i] * (waveHeight * 0.45);
        ctx.lineTo(x, midY + amp);
      }}

      ctx.closePath();
      ctx.fill();

      // Centerline
      ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, midY);
      ctx.lineTo(w, midY);
      ctx.stroke();
    }}

    // 4. Draw BeatWarping Flags
    sections.forEach((sec, idx) => {{
      const x = (sec.startTime / duration) * w;
      const color = flagColors[idx % flagColors.length];

      // Vertical line
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 3]);
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
      ctx.setLineDash([]);

      // Flag badge label
      const label = `#${{idx}} ${{sec.bpm}} BPM (${{sec.startTime.toFixed(2)}}s)`;
      ctx.font = "bold 10px sans-serif";
      const txtWidth = ctx.measureText(label).width;

      const badgeY = (idx % 2 === 0) ? rulerHeight + 6 : rulerHeight + 26;
      ctx.fillStyle = color;
      ctx.fillRect(x + 2, badgeY, txtWidth + 8, 16);
      ctx.fillStyle = "#ffffff";
      ctx.fillText(label, x + 6, badgeY + 12);
    }});

    // 5. Draw Hover indicator if any
    if (hoverTime !== null && hoverTime >= 0 && hoverTime <= duration) {{
      const hx = (hoverTime / duration) * w;
      ctx.strokeStyle = "rgba(255, 255, 255, 0.4)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(hx, rulerHeight);
      ctx.lineTo(hx, h);
      ctx.stroke();
    }}

    // 6. Draw Real-Time Playhead Cursor Line
    const curTime = audio.currentTime || 0;
    const curX = (curTime / duration) * w;

    // Glowing vertical line
    ctx.save();
    ctx.shadowColor = "#00d4ff";
    ctx.shadowBlur = 8;
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.moveTo(curX, 0);
    ctx.lineTo(curX, h);
    ctx.stroke();

    // Top playhead triangular cursor
    ctx.fillStyle = "#00d4ff";
    ctx.beginPath();
    ctx.moveTo(curX - 6, 0);
    ctx.lineTo(curX + 6, 0);
    ctx.lineTo(curX, 10);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }}

  // Continuous animation loop for butter-smooth playhead tracking
  function animationLoop() {{
    if (!audio.paused) {{
      const curTime = audio.currentTime || 0;
      timeCurrent.innerText = formatTime(curTime);
      btnTimeSec.innerText = curTime.toFixed(3) + "s";

      // Auto-follow playhead if enabled and zoomed in
      if (chkFollow.checked && zoomLevel > 1.0) {{
        const w = canvas.width;
        const curX = (curTime / duration) * w;
        const viewLeft = wrapper.scrollLeft;
        const viewWidth = wrapper.clientWidth;

        if (curX > viewLeft + viewWidth * 0.8 || curX < viewLeft) {{
          wrapper.scrollLeft = curX - viewWidth * 0.2;
        }}
      }}
      draw();
    }}
    requestAnimationFrame(animationLoop);
  }}
  requestAnimationFrame(animationLoop);

  // Time seeking helper
  function seekToX(clientX) {{
    const rect = canvas.getBoundingClientRect();
    const x = clientX - rect.left;
    const clampedX = Math.max(0, Math.min(canvas.width, x));
    const targetTime = (clampedX / canvas.width) * duration;
    audio.currentTime = targetTime;
    timeCurrent.innerText = formatTime(targetTime);
    btnTimeSec.innerText = targetTime.toFixed(3) + "s";
    draw();
  }}

  // Mouse scrub events
  canvas.addEventListener("mousedown", (e) => {{
    isDragging = true;
    seekToX(e.clientX);
  }});

  window.addEventListener("mousemove", (e) => {{
    if (isDragging) {{
      seekToX(e.clientX);
    }} else {{
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      if (x >= 0 && x <= canvas.width) {{
        hoverTime = (x / canvas.width) * duration;
      }} else {{
        hoverTime = null;
      }}
      draw();
    }}
  }});

  window.addEventListener("mouseup", () => {{
    if (isDragging) isDragging = false;
  }});

  canvas.addEventListener("mouseleave", () => {{
    hoverTime = null;
    draw();
  }});

  // Controls Event Listeners
  btnPlayPause.addEventListener("click", () => {{
    if (audio.paused) {{
      audio.play();
      btnPlayPause.innerHTML = "⏸ Pausa";
      btnPlayPause.classList.add("btn-danger");
      btnPlayPause.classList.remove("btn-primary");
    }} else {{
      audio.pause();
      btnPlayPause.innerHTML = "▶ Reproducir";
      btnPlayPause.classList.remove("btn-danger");
      btnPlayPause.classList.add("btn-primary");
    }}
  }});

  btnStop.addEventListener("click", () => {{
    audio.pause();
    audio.currentTime = 0;
    btnPlayPause.innerHTML = "▶ Reproducir";
    btnPlayPause.classList.remove("btn-danger");
    btnPlayPause.classList.add("btn-primary");
    timeCurrent.innerText = formatTime(0);
    btnTimeSec.innerText = "0.000s";
    draw();
  }});

  btnSkipBack.addEventListener("click", () => {{
    audio.currentTime = Math.max(0, audio.currentTime - 5.0);
    timeCurrent.innerText = formatTime(audio.currentTime);
    btnTimeSec.innerText = audio.currentTime.toFixed(3) + "s";
    draw();
  }});

  btnSkipFwd.addEventListener("click", () => {{
    audio.currentTime = Math.min(duration, audio.currentTime + 5.0);
    timeCurrent.innerText = formatTime(audio.currentTime);
    btnTimeSec.innerText = audio.currentTime.toFixed(3) + "s";
    draw();
  }});

  btnSpeed.addEventListener("click", () => {{
    speedIdx = (speedIdx + 1) % speeds.length;
    const s = speeds[speedIdx];
    audio.playbackRate = s;
    btnSpeed.innerText = s.toFixed(2) + "x";
  }});

  // Zoom slider & buttons
  zoomSlider.addEventListener("input", (e) => {{
    zoomLevel = parseFloat(e.target.value);
    zoomValue.innerText = zoomLevel.toFixed(1) + "x";
    resizeCanvas();
  }});

  btnZoomFit.addEventListener("click", () => {{
    zoomLevel = 1.0;
    zoomSlider.value = 1.0;
    zoomValue.innerText = "1x";
    resizeCanvas();
  }});

  btnZoom5x.addEventListener("click", () => {{
    zoomLevel = 5.0;
    zoomSlider.value = 5.0;
    zoomValue.innerText = "5x";
    resizeCanvas();
  }});

  btnZoom15x.addEventListener("click", () => {{
    zoomLevel = 15.0;
    zoomSlider.value = 15.0;
    zoomValue.innerText = "15x";
    resizeCanvas();
  }});

  // Copy time to clipboard for Streamlit flag input
  btnCopyTime.addEventListener("click", () => {{
    const sec = audio.currentTime || 0;
    const txt = sec.toFixed(3);
    navigator.clipboard.writeText(txt).then(() => {{
      copyNotice.classList.add("show");
      setTimeout(() => copyNotice.classList.remove("show"), 1800);
    }}).catch(() => {{
      // Fallback
      prompt("Copy current time:", txt);
    }});
  }});

  // Keyboard shortcut listener (Space = Play/Pause)
  window.addEventListener("keydown", (e) => {{
    if (e.code === "Space" && e.target === document.body) {{
      e.preventDefault();
      btnPlayPause.click();
    }}
  }});

  // Initial draw
  resizeCanvas();
</script>
</body>
</html>
"""
    components.html(html_content, height=height, scrolling=False)
