"""Live interactive waveform editor and audio player component for Streamlit.

Provides a synchronized HTML5 Canvas + Audio player with real-time moving playhead,
multi-level zoom, scrubbing, playback controls, BeatWarping flag overlays,
and a visual/audio metronome synced to the active BPM section.
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
    title: str = "Editor y Reproductor de Onda en Vivo",
    height: int = 500,
    seek_time: Optional[float] = None,
    **kwargs,
) -> None:
    """Render the live interactive waveform editor with audio playback, playhead, and metronome.

    Args:
        audio_bytes: Raw audio bytes of the track.
        audio_format: MIME type (e.g. 'audio/mp3', 'audio/ogg', 'audio/wav').
        y: Audio time series numpy array.
        sr: Sample rate.
        bpm_sections: Chronologically ordered list of BPM sections.
        title: Component header.
        height: Iframe height in pixels.
        seek_time: Optional initial timestamp to seek playhead to.
        **kwargs: Additional keyword arguments for forward/backward compatibility.
    """
    if audio_bytes is None:
        st.warning("No se proporcionaron los datos de audio para el reproductor en vivo.")
        return

    # Handle UploadedFile or BytesIO defensively if passed
    if hasattr(audio_bytes, "getvalue"):
        audio_bytes = audio_bytes.getvalue()
    elif hasattr(audio_bytes, "read") and callable(audio_bytes.read):
        audio_bytes = audio_bytes.read()

    if not isinstance(audio_bytes, (bytes, bytearray)):
        st.error("Formato de audio no válido para el reproductor.")
        return

    if y is None or sr is None or sr <= 0 or len(y) == 0:
        st.warning("Datos de forma de onda no disponibles.")
        return

    initial_seek_str = "null"
    if seek_time is not None:
        try:
            initial_seek_str = str(round(float(seek_time), 3))
        except (ValueError, TypeError):
            initial_seek_str = "null"

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
<html lang="es">
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
    padding: 10px;
    overflow: hidden;
  }}
  .player-card {{
    background: #181b24;
    border: 1px solid #282e3d;
    border-radius: 10px;
    padding: 14px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
  }}
  
  /* Top Header Bar */
  .header-bar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
    border-bottom: 1px solid #232938;
    padding-bottom: 8px;
    flex-wrap: nowrap;
    gap: 12px;
  }}
  .header-left {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .header-title {{
    font-size: 13px;
    font-weight: 700;
    color: #38bdf8;
    display: flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
  }}

  /* Metronome Widget */
  .metronome-box {{
    display: flex;
    align-items: center;
    gap: 8px;
    background: #0f1218;
    border: 1px solid #2d3748;
    padding: 4px 10px;
    border-radius: 6px;
  }}
  .metro-light {{
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #334155;
    border: 1px solid #475569;
    transition: background-color 0.05s ease, box-shadow 0.05s ease;
  }}
  .metro-light.downbeat {{
    background: #00d4ff;
    box-shadow: 0 0 10px #00d4ff, 0 0 16px #38bdf8;
  }}
  .metro-light.upbeat {{
    background: #4ade80;
    box-shadow: 0 0 8px #4ade80;
  }}
  .metro-bpm {{
    font-family: "Courier New", Courier, monospace;
    font-size: 13px;
    font-weight: bold;
    color: #f1f5f9;
    min-width: 75px;
  }}
  .metro-toggle {{
    background: transparent;
    border: 1px solid #3b4254;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 11px;
    cursor: pointer;
    color: #94a3b8;
  }}
  .metro-toggle.active {{
    background: #0284c7;
    border-color: #38bdf8;
    color: #ffffff;
  }}

  /* Time & Copy Header Right */
  .header-right {{
    display: flex;
    align-items: center;
    gap: 10px;
    white-space: nowrap;
  }}
  .time-display {{
    font-family: "Courier New", Courier, monospace;
    font-size: 15px;
    font-weight: bold;
    color: #f8fafc;
    background: #0f1218;
    padding: 4px 10px;
    border-radius: 6px;
    border: 1px solid #2d3748;
    font-variant-numeric: tabular-nums;
  }}
  .time-current {{
    color: #00d4ff;
  }}
  .copy-time-btn {{
    background: #252a37;
    color: #e2e8f0;
    border: 1px solid #3b4254;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    width: 145px;
    justify-content: center;
    position: relative;
  }}
  .copy-time-btn:hover {{
    background: #333a4c;
    border-color: #00d4ff;
    color: #ffffff;
  }}
  .copy-badge {{
    font-size: 11px;
    color: #4ade80;
    font-weight: bold;
    display: none;
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

  /* Controls layout (Rock-solid, stationary) */
  .controls-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 12px;
    gap: 12px;
    flex-wrap: nowrap;
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
    transition: background 0.15s, border-color 0.15s;
    display: inline-flex;
    align-items: center;
    gap: 5px;
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

  /* SVG Icon Styles */
  .icon-svg {{
    width: 14px;
    height: 14px;
    fill: currentColor;
    vertical-align: middle;
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
    display: flex;
    align-items: center;
    gap: 4px;
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
</style>
</head>
<body>

<div class="player-card">
  <!-- Top Header Bar: Title, Metronome, Time & Fixed Copy Button -->
  <div class="header-bar">
    <div class="header-left">
      <div class="header-title">
        <svg class="icon-svg" viewBox="0 0 24 24"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg>
        <span>Editor de Onda en Vivo</span>
      </div>

      <!-- Metronome Visual & BPM Display -->
      <div class="metronome-box" title="Metrónomo visual sincronizado con las banderas de BeatWarping">
        <div class="metro-light" id="metroLight"></div>
        <span class="metro-bpm" id="metroBpm">120.0 BPM</span>
        <button class="metro-toggle" id="btnMetroAudio" title="Activar sonido de click del metrónomo">Click: OFF</button>
      </div>
    </div>

    <!-- Header Right: Timer and Independent Copy Button (Won't shift controls) -->
    <div class="header-right">
      <div class="time-display">
        <span class="time-current" id="timeCurrent">00:00.000</span> / <span id="timeTotal">00:00.000</span>
      </div>

      <button class="copy-time-btn" id="btnCopyTime" title="Copiar segundo actual para crear una bandera">
        <svg class="icon-svg" viewBox="0 0 24 24"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>
        <span id="btnCopyLabel">Copiar Tiempo</span>
        <span class="copy-badge" id="copyBadge">✓ Copiado!</span>
      </button>
    </div>
  </div>

  <!-- Scrollable Interactive Waveform Canvas -->
  <div class="waveform-wrapper" id="waveWrapper">
    <canvas id="waveCanvas"></canvas>
  </div>

  <!-- Transport & Zoom Controls Row (Completely Stationary) -->
  <div class="controls-row">
    <!-- Transport Buttons with SVG Icons -->
    <div class="btn-group">
      <button id="btnPlayPause" class="btn-primary">
        <svg class="icon-svg" id="playIcon" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
        <span id="playLabel">Reproducir</span>
      </button>
      <button id="btnStop" title="Detener reproducción">
        <svg class="icon-svg" viewBox="0 0 24 24"><path d="M6 6h12v12H6z"/></svg>
        <span>Detener</span>
      </button>
      <button id="btnSkipBack" title="Retroceder 5 segundos">
        <svg class="icon-svg" viewBox="0 0 24 24"><path d="M11 18V6l-8.5 6 8.5 6zm.5-6l8.5 6V6l-8.5 6z"/></svg>
        <span>-5s</span>
      </button>
      <button id="btnSkipFwd" title="Avanzar 5 segundos">
        <span>+5s</span>
        <svg class="icon-svg" viewBox="0 0 24 24"><path d="M4 18l8.5-6L4 6v12zm9-12v12l8.5-6L13 6z"/></svg>
      </button>
      
      <!-- Speed selector -->
      <button id="btnSpeed" title="Velocidad de reproducción">1.0x</button>

      <!-- Flag jump buttons -->
      <button id="btnPrevFlag" title="Saltar a la bandera anterior" class="zoom-preset">◀ Bandera</button>
      <button id="btnNextFlag" title="Saltar a la bandera siguiente" class="zoom-preset">Bandera ▶</button>
    </div>

    <!-- Zoom & Follow Controls -->
    <div class="zoom-controls">
      <span class="zoom-label">
        <svg class="icon-svg" viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
        Zoom:
      </span>
      <input type="range" id="zoomSlider" min="1" max="25" value="1" step="0.5" style="width: 100px;">
      <span id="zoomValue" style="font-size: 12px; font-weight: bold; min-width: 30px; color: #38bdf8;">1x</span>
      <button class="zoom-preset" id="btnZoomFit">Ajustar</button>
      <button class="zoom-preset" id="btnZoom5x">5x</button>
      <button class="zoom-preset" id="btnZoom15x">15x</button>

      <label style="display: flex; align-items: center; gap: 4px; font-size: 11px; color: #94a3b8; cursor: pointer; margin-left: 6px;">
        <input type="checkbox" id="chkFollow" checked> Seguir
      </label>
      <label style="display: flex; align-items: center; gap: 4px; font-size: 11px; color: #94a3b8; cursor: pointer; margin-left: 6px;" title="Mostrar u ocultar cuadrícula de beats (pulsos)">
        <input type="checkbox" id="chkBeatGrid" checked> Cuadrícula
      </label>
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
  const playLabel = document.getElementById("playLabel");
  const playIcon = document.getElementById("playIcon");
  const btnStop = document.getElementById("btnStop");
  const btnSkipBack = document.getElementById("btnSkipBack");
  const btnSkipFwd = document.getElementById("btnSkipFwd");
  const btnSpeed = document.getElementById("btnSpeed");
  const timeCurrent = document.getElementById("timeCurrent");
  const timeTotal = document.getElementById("timeTotal");
  const btnCopyTime = document.getElementById("btnCopyTime");
  const btnCopyLabel = document.getElementById("btnCopyLabel");
  const copyBadge = document.getElementById("copyBadge");
  const btnPrevFlag = document.getElementById("btnPrevFlag");
  const btnNextFlag = document.getElementById("btnNextFlag");

  const zoomSlider = document.getElementById("zoomSlider");
  const zoomValue = document.getElementById("zoomValue");
  const btnZoomFit = document.getElementById("btnZoomFit");
  const btnZoom5x = document.getElementById("btnZoom5x");
  const btnZoom15x = document.getElementById("btnZoom15x");
  const chkFollow = document.getElementById("chkFollow");
  const chkBeatGrid = document.getElementById("chkBeatGrid");

  // Metronome elements
  const metroLight = document.getElementById("metroLight");
  const metroBpm = document.getElementById("metroBpm");
  const btnMetroAudio = document.getElementById("btnMetroAudio");

  let zoomLevel = 1.0;
  let isDragging = false;
  let hoverTime = null;
  const flagColors = ["#f43f5e", "#fb923c", "#facc15", "#4ade80", "#a855f7", "#ec4899", "#38bdf8"];
  const speeds = [0.5, 0.75, 1.0, 1.25, 1.5];
  let speedIdx = 2;

  // Web Audio Context for Metronome Synthesized Click
  let audioCtx = null;
  let metroAudioEnabled = false;
  let lastBeatIndex = -1;

  function initAudioContext() {{
    if (!audioCtx) {{
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (AudioContextClass) {{
        audioCtx = new AudioContextClass();
      }}
    }}
    if (audioCtx && audioCtx.state === "suspended") {{
      audioCtx.resume();
    }}
  }}

  function playMetronomeClick(isDownbeat) {{
    if (!audioCtx || !metroAudioEnabled) return;
    try {{
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(isDownbeat ? 1200 : 800, audioCtx.currentTime);
      gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.04);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.04);
    }} catch(e) {{}}
  }}

  btnMetroAudio.addEventListener("click", () => {{
    initAudioContext();
    metroAudioEnabled = !metroAudioEnabled;
    if (metroAudioEnabled) {{
      btnMetroAudio.innerText = "Click: ON";
      btnMetroAudio.classList.add("active");
    }} else {{
      btnMetroAudio.innerText = "Click: OFF";
      btnMetroAudio.classList.remove("active");
    }}
  }});

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

  // Helper to find active section at current time
  function getActiveSection(t) {{
    let active = sections[0] || {{ startTime: 0, startBeat: 0, bpm: 120 }};
    for (let i = 0; i < sections.length; i++) {{
      if (t >= sections[i].startTime) {{
        active = sections[i];
      }} else {{
        break;
      }}
    }}
    return active;
  }}

  // Update metronome state
  function updateMetronome(curTime) {{
    const sec = getActiveSection(curTime);
    metroBpm.innerText = sec.bpm.toFixed(1) + " BPM";

    // Calculate current cumulative beat
    const beat = sec.startBeat + (curTime - sec.startTime) * (sec.bpm / 60.0);
    const beatInt = Math.floor(beat);
    const phase = beat - beatInt;

    if (!audio.paused && beatInt !== lastBeatIndex && beatInt >= 0) {{
      lastBeatIndex = beatInt;
      const isDownbeat = (beatInt % 4 === 0);
      playMetronomeClick(isDownbeat);

      metroLight.className = "metro-light " + (isDownbeat ? "downbeat" : "upbeat");
      setTimeout(() => {{
        metroLight.className = "metro-light";
      }}, 90);
    }}
  }}

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

    // 3.5 Draw Beat Grid (Subtle pulse lines for every individual beat)
    if (chkBeatGrid && chkBeatGrid.checked) {{
      for (let i = 0; i < sections.length; i++) {{
        const sec = sections[i];
        const nextTime = (i + 1 < sections.length) ? sections[i + 1].startTime : duration;
        const bpm = sec.bpm;
        if (bpm > 20) {{
          const beatInterval = 60.0 / bpm;
          let beatTime = sec.startTime;
          let beatCount = 0;
          while (beatTime < nextTime - 0.001) {{
            const bx = (beatTime / duration) * w;
            const isDownbeat = (beatCount % 4 === 0);

            ctx.beginPath();
            ctx.moveTo(bx, rulerHeight);
            ctx.lineTo(bx, h);

            if (isDownbeat) {{
              ctx.strokeStyle = "rgba(255, 255, 255, 0.35)";
              ctx.lineWidth = 1.0;
              ctx.setLineDash([]);
              if (zoomLevel >= 3) {{
                ctx.fillStyle = "rgba(255, 255, 255, 0.5)";
                ctx.font = "9px sans-serif";
                ctx.fillText(`b${{beatCount + 1}}`, bx + 2, h - 5);
              }}
            }} else {{
              ctx.strokeStyle = "rgba(56, 189, 248, 0.18)";
              ctx.lineWidth = 0.8;
              ctx.setLineDash([2, 3]);
            }}
            ctx.stroke();
            ctx.setLineDash([]);

            beatTime += beatInterval;
            beatCount++;
          }}
        }}
      }}
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

  // Continuous animation loop for butter-smooth playhead & metronome tracking
  function animationLoop() {{
    const curTime = audio.currentTime || 0;
    if (!audio.paused) {{
      timeCurrent.innerText = formatTime(curTime);
      updateMetronome(curTime);

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

  // Flag jumping helper
  function jumpToFlagTime(targetSec) {{
    audio.currentTime = targetSec;
    timeCurrent.innerText = formatTime(targetSec);
    updateMetronome(targetSec);
    if (chkFollow.checked) {{
      const w = canvas.width;
      const curX = (targetSec / duration) * w;
      wrapper.scrollLeft = Math.max(0, curX - wrapper.clientWidth * 0.3);
    }}
    draw();
  }}

  // Time seeking helper
  function seekToX(clientX) {{
    const rect = canvas.getBoundingClientRect();
    const x = clientX - rect.left;
    const clampedX = Math.max(0, Math.min(canvas.width, x));
    const targetTime = (clampedX / canvas.width) * duration;
    audio.currentTime = targetTime;
    timeCurrent.innerText = formatTime(targetTime);
    updateMetronome(targetTime);
    draw();
  }}

  // Mouse scrub events (Clicks near a flag jump directly to that flag)
  canvas.addEventListener("mousedown", (e) => {{
    isDragging = true;
    initAudioContext();
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const w = canvas.width;
    for (let i = 0; i < sections.length; i++) {{
      const flagX = (sections[i].startTime / duration) * w;
      if (Math.abs(x - flagX) <= 14) {{
        jumpToFlagTime(sections[i].startTime);
        return;
      }}
    }}
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
    initAudioContext();
    if (audio.paused) {{
      audio.play();
      playLabel.innerText = "Pausa";
      playIcon.innerHTML = '<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>';
      btnPlayPause.classList.add("btn-danger");
      btnPlayPause.classList.remove("btn-primary");
    }} else {{
      audio.pause();
      playLabel.innerText = "Reproducir";
      playIcon.innerHTML = '<path d="M8 5v14l11-7z"/>';
      btnPlayPause.classList.remove("btn-danger");
      btnPlayPause.classList.add("btn-primary");
    }}
  }});

  btnStop.addEventListener("click", () => {{
    audio.pause();
    audio.currentTime = 0;
    playLabel.innerText = "Reproducir";
    playIcon.innerHTML = '<path d="M8 5v14l11-7z"/>';
    btnPlayPause.classList.remove("btn-danger");
    btnPlayPause.classList.add("btn-primary");
    timeCurrent.innerText = formatTime(0);
    updateMetronome(0);
    draw();
  }});

  btnSkipBack.addEventListener("click", () => {{
    audio.currentTime = Math.max(0, audio.currentTime - 5.0);
    timeCurrent.innerText = formatTime(audio.currentTime);
    updateMetronome(audio.currentTime);
    draw();
  }});

  btnSkipFwd.addEventListener("click", () => {{
    audio.currentTime = Math.min(duration, audio.currentTime + 5.0);
    timeCurrent.innerText = formatTime(audio.currentTime);
    updateMetronome(audio.currentTime);
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

  // Copy time to clipboard (Stationary in header, no shifting)
  btnCopyTime.addEventListener("click", () => {{
    const sec = audio.currentTime || 0;
    const txt = sec.toFixed(3);
    navigator.clipboard.writeText(txt).then(() => {{
      btnCopyLabel.style.display = "none";
      copyBadge.style.display = "inline";
      setTimeout(() => {{
        copyBadge.style.display = "none";
        btnCopyLabel.style.display = "inline";
      }}, 1500);
    }}).catch(() => {{
      prompt("Copiar tiempo actual:", txt);
    }});
  }});

  // Flag navigation listeners
  if (btnPrevFlag) {{
    btnPrevFlag.addEventListener("click", () => {{
      const curTime = audio.currentTime || 0;
      let target = sections[0].startTime;
      for (let i = sections.length - 1; i >= 0; i--) {{
        if (sections[i].startTime < curTime - 0.25) {{
          target = sections[i].startTime;
          break;
        }}
      }}
      jumpToFlagTime(target);
    }});
  }}

  if (btnNextFlag) {{
    btnNextFlag.addEventListener("click", () => {{
      const curTime = audio.currentTime || 0;
      let target = sections[sections.length - 1].startTime;
      for (let i = 0; i < sections.length; i++) {{
        if (sections[i].startTime > curTime + 0.25) {{
          target = sections[i].startTime;
          break;
        }}
      }}
      jumpToFlagTime(target);
    }});
  }}

  // Beat grid visibility toggle listener
  if (chkBeatGrid) {{
    chkBeatGrid.addEventListener("change", () => {{
      draw();
    }});
  }}

  // Initial seek if requested
  const initialSeek = {initial_seek_str};
  if (initialSeek !== null) {{
    audio.currentTime = initialSeek;
    timeCurrent.innerText = formatTime(initialSeek);
    updateMetronome(initialSeek);
    setTimeout(() => {{
      jumpToFlagTime(initialSeek);
    }}, 100);
  }}

  // Initial draw & metronome setup
  resizeCanvas();
  updateMetronome(initialSeek || 0);
</script>
</body>
</html>
"""
    components.html(html_content, height=height, scrolling=False)
