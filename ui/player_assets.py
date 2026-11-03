"""HTML5 Canvas and WebAudio template builder for the Sky/Slate Live Waveform Player."""


def build_player_html(data_uri: str, payload_json: str, initial_seek_str: str = "null") -> str:
    """Build the self-contained Sky/Slate HTML/CSS/JS interactive waveform player."""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8"/>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700&family=JetBrains+Mono:wght@500;600;700&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; font-family: 'Inter', system-ui, sans-serif; }}
  body {{ background: #f8fafc; color: #0f172a; padding: 6px; overflow: hidden; }}
  .player-card {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px 14px; box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06); }}
  .header-bar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; gap: 10px; }}
  .header-left, .header-right, .btn-group, .zoom-controls {{ display: flex; align-items: center; gap: 8px; }}
  .header-title {{ font-size: 13px; font-weight: 700; color: #0284c7; display: flex; align-items: center; gap: 6px; white-space: nowrap; }}
  .metronome-box {{ display: flex; align-items: center; gap: 8px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 4px 10px; border-radius: 8px; }}
  .metro-light {{ width: 11px; height: 11px; border-radius: 50%; background: #cbd5e1; border: 1px solid #94a3b8; transition: background-color 0.05s ease, box-shadow 0.05s ease; }}
  .metro-light.downbeat {{ background: #0284c7; box-shadow: 0 0 8px #0284c7, 0 0 14px #38bdf8; }}
  .metro-light.upbeat {{ background: #0ea5e9; box-shadow: 0 0 6px #38bdf8; }}
  .metro-bpm {{ font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 700; color: #0f172a; min-width: 72px; }}
  .metro-toggle {{ background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 2px 7px; font-size: 11px; font-weight: 600; cursor: pointer; color: #64748b; }}
  .metro-toggle.active {{ background: #0284c7; border-color: #0284c7; color: #ffffff; }}
  .time-display {{ font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 700; color: #0f172a; background: #f8fafc; padding: 4px 10px; border-radius: 8px; border: 1px solid #e2e8f0; font-variant-numeric: tabular-nums; }}
  .time-current {{ color: #0284c7; }}
  .copy-time-btn {{ background: #f8fafc; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 8px; padding: 4px 10px; font-size: 12px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 4px; width: 142px; }}
  .copy-time-btn:hover {{ background: #e0f2fe; border-color: #0284c7; color: #0369a1; }}
  .copy-badge {{ font-size: 11px; color: #0284c7; font-weight: 700; display: none; }}
  .waveform-wrapper {{ position: relative; width: 100%; height: 210px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; overflow-x: auto; overflow-y: hidden; cursor: crosshair; }}
  .waveform-wrapper::-webkit-scrollbar {{ height: 7px; }}
  .waveform-wrapper::-webkit-scrollbar-track {{ background: #f1f5f9; }}
  .waveform-wrapper::-webkit-scrollbar-thumb {{ background: #cbd5e1; border-radius: 4px; }}
  .waveform-wrapper::-webkit-scrollbar-thumb:hover {{ background: #0284c7; }}
  #waveCanvas {{ display: block; height: 210px; }}
  .controls-row {{ display: flex; justify-content: space-between; align-items: center; margin-top: 10px; gap: 10px; flex-wrap: nowrap; }}
  button {{ background: #f8fafc; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 8px; padding: 5px 10px; font-size: 12px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; transition: all 0.12s ease; }}
  button:hover {{ background: #e0f2fe; border-color: #0284c7; color: #0369a1; }}
  .btn-primary {{ background: #0284c7; border-color: #0284c7; color: #ffffff; }}
  .btn-primary:hover {{ background: #0369a1; border-color: #0369a1; color: #ffffff; }}
  .btn-danger {{ background: #ef4444; border-color: #ef4444; color: #ffffff; }}
  .btn-danger:hover {{ background: #dc2626; border-color: #dc2626; color: #ffffff; }}
  .icon-svg {{ width: 13px; height: 13px; fill: currentColor; }}
  .zoom-controls {{ background: #f8fafc; padding: 4px 10px; border-radius: 8px; border: 1px solid #e2e8f0; }}
  .zoom-label {{ font-size: 11px; color: #64748b; font-weight: 600; }}
  input[type="range"] {{ accent-color: #0284c7; cursor: pointer; width: 88px; }}
  .zoom-preset {{ padding: 3px 7px; font-size: 11px; border-radius: 6px; }}
  .chk-label {{ display: flex; align-items: center; gap: 4px; font-size: 11px; color: #0f172a; font-weight: 500; cursor: pointer; }}
</style>
</head>
<body>
<div class="player-card">
  <div class="header-bar">
    <div class="header-left">
      <div class="header-title">
        <svg class="icon-svg" viewBox="0 0 24 24"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg>
        <span>Monitor de Onda y Ritmo</span>
      </div>
      <div class="metronome-box" title="Metrónomo sincronizado con las banderas de tempo">
        <div class="metro-light" id="metroLight"></div><span class="metro-bpm" id="metroBpm">120.0 BPM</span>
        <button class="metro-toggle" id="btnMetroAudio" title="Activar click de metrónomo">Click: OFF</button>
      </div>
    </div>
    <div class="header-right">
      <div class="time-display"><span class="time-current" id="timeCurrent">00:00.000</span> / <span id="timeTotal">00:00.000</span></div>
      <button class="copy-time-btn" id="btnCopyTime" title="Copiar segundo actual"><span id="btnCopyLabel">Copiar Tiempo</span><span class="copy-badge" id="copyBadge">✓ Copiado</span></button>
    </div>
  </div>
  <div class="waveform-wrapper" id="waveWrapper"><canvas id="waveCanvas"></canvas></div>
  <div class="controls-row">
    <div class="btn-group">
      <button id="btnPlayPause" class="btn-primary"><svg class="icon-svg" id="playIcon" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg><span id="playLabel">Reproducir</span></button>
      <button id="btnStop" title="Reiniciar">Detener</button><button id="btnSkipBack" title="Retroceder 5s">-5s</button><button id="btnSkipFwd" title="Avanzar 5s">+5s</button>
      <button id="btnSpeed" title="Velocidad">1.0x</button>
      <button id="btnPrevFlag" title="◀ Anterior" class="zoom-preset">◀ Bandera</button><button id="btnNextFlag" title="Siguiente ▶" class="zoom-preset">Bandera ▶</button>
    </div>
    <div class="zoom-controls">
      <span class="zoom-label">Zoom:</span><input type="range" id="zoomSlider" min="1" max="25" value="1" step="0.5">
      <span id="zoomValue" style="font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;color:#0284c7;min-width:28px;">1x</span>
      <button class="zoom-preset" id="btnZoomFit">1x</button><button class="zoom-preset" id="btnZoom5x">5x</button><button class="zoom-preset" id="btnZoom15x">15x</button>
      <label class="chk-label"><input type="checkbox" id="chkFollow" checked> Seguir</label>
      <label class="chk-label" title="Mostrar cuadrícula de beats"><input type="checkbox" id="chkBeatGrid" checked> Cuadrícula</label>
    </div>
  </div>
</div>
<audio id="audioElement" src="{data_uri}" preload="auto"></audio>
<script>
  const data = {payload_json};
  const duration = data.duration || 1.0, envelope = data.envelope || [], sections = data.sections || [];
  const beatOffsetSec = (data.beatOffsetMs || 0) / 1000.0;
  const audio = document.getElementById("audioElement"), canvas = document.getElementById("waveCanvas"), ctx = canvas.getContext("2d"), wrapper = document.getElementById("waveWrapper");
  const btnPlayPause = document.getElementById("btnPlayPause"), playLabel = document.getElementById("playLabel"), playIcon = document.getElementById("playIcon");
  const btnStop = document.getElementById("btnStop"), btnSkipBack = document.getElementById("btnSkipBack"), btnSkipFwd = document.getElementById("btnSkipFwd"), btnSpeed = document.getElementById("btnSpeed");
  const timeCurrent = document.getElementById("timeCurrent"), timeTotal = document.getElementById("timeTotal");
  const btnCopyTime = document.getElementById("btnCopyTime"), btnCopyLabel = document.getElementById("btnCopyLabel"), copyBadge = document.getElementById("copyBadge");
  const btnPrevFlag = document.getElementById("btnPrevFlag"), btnNextFlag = document.getElementById("btnNextFlag");
  const zoomSlider = document.getElementById("zoomSlider"), zoomValue = document.getElementById("zoomValue");
  const btnZoomFit = document.getElementById("btnZoomFit"), btnZoom5x = document.getElementById("btnZoom5x"), btnZoom15x = document.getElementById("btnZoom15x");
  const chkFollow = document.getElementById("chkFollow"), chkBeatGrid = document.getElementById("chkBeatGrid");
  const metroLight = document.getElementById("metroLight"), metroBpm = document.getElementById("metroBpm"), btnMetroAudio = document.getElementById("btnMetroAudio");

  let zoomLevel = 1.0, isDragging = false, hoverTime = null, audioCtx = null, metroAudioEnabled = false, lastBeatIndex = -1, speedIdx = 2;
  const flagColors = ["#ef4444", "#0284c7", "#0ea5e9", "#f59e0b", "#10b981", "#6366f1"];
  const speeds = [0.5, 0.75, 1.0, 1.25, 1.5];

  function initAudioContext() {{
    if (!audioCtx) {{ const Ctx = window.AudioContext || window.webkitAudioContext; if (Ctx) audioCtx = new Ctx(); }}
    if (audioCtx && audioCtx.state === "suspended") audioCtx.resume();
  }}
  function playMetronomeClick(isDownbeat) {{
    if (!audioCtx || !metroAudioEnabled) return;
    try {{
      const osc = audioCtx.createOscillator(), gain = audioCtx.createGain();
      osc.type = "sine"; osc.frequency.setValueAtTime(isDownbeat ? 1200 : 820, audioCtx.currentTime);
      gain.gain.setValueAtTime(0.28, audioCtx.currentTime); gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.04);
      osc.connect(gain); gain.connect(audioCtx.destination); osc.start(); osc.stop(audioCtx.currentTime + 0.04);
    }} catch (e) {{}}
  }}
  btnMetroAudio.addEventListener("click", () => {{
    initAudioContext(); metroAudioEnabled = !metroAudioEnabled;
    btnMetroAudio.innerText = metroAudioEnabled ? "Click: ON" : "Click: OFF";
    btnMetroAudio.classList.toggle("active", metroAudioEnabled);
  }});
  function formatTime(sec) {{
    if (isNaN(sec) || sec < 0) sec = 0;
    const m = Math.floor(sec / 60), s = Math.floor(sec % 60), ms = Math.floor((sec % 1) * 1000);
    return `${{m.toString().padStart(2, '0')}}:${{s.toString().padStart(2, '0')}}.${{ms.toString().padStart(3, '0')}}`;
  }}
  timeTotal.innerText = formatTime(duration);

  function getActiveSection(t) {{
    let active = sections[0] || {{ startTime: 0, startBeat: 0, bpm: 120 }};
    for (let i = 0; i < sections.length; i++) {{ if (t >= sections[i].startTime) active = sections[i]; else break; }}
    return active;
  }}
  function updateMetronome(curTime) {{
    const sec = getActiveSection(curTime);
    metroBpm.innerText = sec.bpm.toFixed(1) + " BPM";
    const beatInt = Math.floor(sec.startBeat + (curTime - sec.startTime) * (sec.bpm / 60.0));
    if (!audio.paused && beatInt !== lastBeatIndex && beatInt >= 0) {{
      lastBeatIndex = beatInt;
      const isDownbeat = (beatInt % 4 === 0);
      playMetronomeClick(isDownbeat);
      metroLight.className = "metro-light " + (isDownbeat ? "downbeat" : "upbeat");
      setTimeout(() => {{ metroLight.className = "metro-light"; }}, 90);
    }}
  }}
  function resizeCanvas() {{
    const baseWidth = wrapper.clientWidth || 900;
    canvas.width = Math.max(baseWidth, Math.round(baseWidth * zoomLevel)); canvas.height = 210; draw();
  }}
  window.addEventListener("resize", resizeCanvas);

  function draw() {{
    const w = canvas.width, h = canvas.height, rulerH = 22, waveH = h - rulerH, midY = rulerH + waveH / 2;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "#f8fafc"; ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = "#f1f5f9"; ctx.fillRect(0, 0, w, rulerH);
    ctx.strokeStyle = "#e2e8f0"; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(0, rulerH); ctx.lineTo(w, rulerH); ctx.stroke();

    let stepSec = zoomLevel > 15 ? 0.5 : (zoomLevel > 7 ? 1 : (zoomLevel > 3 ? 2 : Math.max(5, Math.round(duration / 10))));
    ctx.fillStyle = "#64748b"; ctx.font = "10px 'JetBrains Mono', monospace";
    for (let t = 0; t <= duration; t += stepSec) {{
      const x = (t / duration) * w;
      ctx.beginPath(); ctx.moveTo(x, rulerH - 6); ctx.lineTo(x, rulerH); ctx.strokeStyle = "#cbd5e1"; ctx.stroke();
      const lbl = t >= 60 ? `${{Math.floor(t / 60)}}m${{Math.round(t % 60)}}s` : `${{t.toFixed(stepSec < 1 ? 1 : 0)}}s`;
      ctx.fillText(lbl, x + 3, rulerH - 7);
    }}

    const n = envelope.length;
    if (n > 1) {{
      const grad = ctx.createLinearGradient(0, rulerH, 0, h);
      grad.addColorStop(0, "#38bdf8"); grad.addColorStop(0.5, "#0284c7"); grad.addColorStop(1, "#38bdf8");
      ctx.fillStyle = grad; ctx.beginPath(); ctx.moveTo(0, midY);
      for (let i = 0; i < n; i++) ctx.lineTo((i / (n - 1)) * w, midY - envelope[i] * (waveH * 0.44));
      for (let i = n - 1; i >= 0; i--) ctx.lineTo((i / (n - 1)) * w, midY + envelope[i] * (waveH * 0.44));
      ctx.closePath(); ctx.fill();
      ctx.strokeStyle = "rgba(15, 23, 42, 0.12)"; ctx.beginPath(); ctx.moveTo(0, midY); ctx.lineTo(w, midY); ctx.stroke();
    }}

    if (chkBeatGrid && chkBeatGrid.checked) {{
      for (let i = 0; i < sections.length; i++) {{
        const sec = sections[i], nextTime = (i + 1 < sections.length) ? sections[i + 1].startTime : duration;
        if (sec.bpm > 20) {{
          const beatInterval = 60.0 / sec.bpm;
          let beatTime = (i === 0 && sec.startTime === 0 && beatOffsetSec > 0) ? beatOffsetSec : sec.startTime, beatCount = 0;
          while (beatTime < nextTime - 0.001) {{
            const bx = (beatTime / duration) * w, isDown = (beatCount % 4 === 0);
            ctx.beginPath(); ctx.moveTo(bx, rulerH); ctx.lineTo(bx, h);
            ctx.strokeStyle = isDown ? "rgba(15, 23, 42, 0.28)" : "rgba(2, 132, 199, 0.18)";
            ctx.lineWidth = isDown ? 1.0 : 0.8; ctx.setLineDash(isDown ? [] : [2, 3]);
            ctx.stroke(); ctx.setLineDash([]);
            beatTime += beatInterval; beatCount++;
          }}
        }}
      }}
    }}

    sections.forEach((sec, idx) => {{
      const x = (sec.startTime / duration) * w, color = flagColors[idx % flagColors.length];
      ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.setLineDash([5, 3]);
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); ctx.setLineDash([]);
      const label = `#${{idx}} ${{sec.bpm}} BPM (${{sec.startTime.toFixed(2)}}s)`;
      ctx.font = "bold 10px 'Inter', sans-serif";
      const tw = ctx.measureText(label).width, by = (idx % 2 === 0) ? rulerH + 6 : rulerH + 25;
      ctx.fillStyle = color; ctx.fillRect(x + 2, by, tw + 8, 16);
      ctx.fillStyle = "#ffffff"; ctx.fillText(label, x + 6, by + 11);
    }});

    if (hoverTime !== null && hoverTime >= 0 && hoverTime <= duration) {{
      const hx = (hoverTime / duration) * w;
      ctx.strokeStyle = "rgba(15, 23, 42, 0.35)"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(hx, rulerH); ctx.lineTo(hx, h); ctx.stroke();
    }}

    const curTime = audio.currentTime || 0, curX = (curTime / duration) * w;
    ctx.save(); ctx.strokeStyle = "#0f172a"; ctx.lineWidth = 2.2;
    ctx.beginPath(); ctx.moveTo(curX, 0); ctx.lineTo(curX, h); ctx.stroke();
    ctx.fillStyle = "#ef4444"; ctx.beginPath();
    ctx.moveTo(curX - 6, 0); ctx.lineTo(curX + 6, 0); ctx.lineTo(curX, 9); ctx.closePath(); ctx.fill();
    ctx.restore();
  }}

  function animationLoop() {{
    const curTime = audio.currentTime || 0;
    if (!audio.paused) {{
      timeCurrent.innerText = formatTime(curTime); updateMetronome(curTime);
      if (chkFollow.checked && zoomLevel > 1.0) {{
        const curX = (curTime / duration) * canvas.width, vl = wrapper.scrollLeft, vw = wrapper.clientWidth;
        if (curX > vl + vw * 0.8 || curX < vl) wrapper.scrollLeft = curX - vw * 0.2;
      }}
      draw();
    }}
    requestAnimationFrame(animationLoop);
  }}
  requestAnimationFrame(animationLoop);

  function jumpToFlagTime(targetSec) {{
    audio.currentTime = targetSec; timeCurrent.innerText = formatTime(targetSec); updateMetronome(targetSec);
    if (chkFollow.checked) wrapper.scrollLeft = Math.max(0, (targetSec / duration) * canvas.width - wrapper.clientWidth * 0.3);
    draw();
  }}
  function seekToX(clientX) {{
    const clampedX = Math.max(0, Math.min(canvas.width, clientX - canvas.getBoundingClientRect().left));
    jumpToFlagTime((clampedX / canvas.width) * duration);
  }}
  canvas.addEventListener("mousedown", (e) => {{
    isDragging = true; initAudioContext();
    const x = e.clientX - canvas.getBoundingClientRect().left;
    for (let i = 0; i < sections.length; i++) {{
      if (Math.abs(x - (sections[i].startTime / duration) * canvas.width) <= 14) {{ jumpToFlagTime(sections[i].startTime); return; }}
    }}
    seekToX(e.clientX);
  }});
  window.addEventListener("mousemove", (e) => {{
    if (isDragging) seekToX(e.clientX);
    else {{
      const x = e.clientX - canvas.getBoundingClientRect().left;
      hoverTime = (x >= 0 && x <= canvas.width) ? (x / canvas.width) * duration : null; draw();
    }}
  }});
  window.addEventListener("mouseup", () => {{ isDragging = false; }});
  canvas.addEventListener("mouseleave", () => {{ hoverTime = null; draw(); }});

  btnPlayPause.addEventListener("click", () => {{
    initAudioContext();
    if (audio.paused) {{
      audio.play(); playLabel.innerText = "Pausa"; playIcon.innerHTML = '<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>';
      btnPlayPause.classList.replace("btn-primary", "btn-danger");
    }} else {{
      audio.pause(); playLabel.innerText = "Reproducir"; playIcon.innerHTML = '<path d="M8 5v14l11-7z"/>';
      btnPlayPause.classList.replace("btn-danger", "btn-primary");
    }}
  }});
  btnStop.addEventListener("click", () => {{
    audio.pause(); audio.currentTime = 0; playLabel.innerText = "Reproducir";
    playIcon.innerHTML = '<path d="M8 5v14l11-7z"/>'; btnPlayPause.classList.replace("btn-danger", "btn-primary"); jumpToFlagTime(0);
  }});
  btnSkipBack.addEventListener("click", () => jumpToFlagTime(Math.max(0, audio.currentTime - 5.0)));
  btnSkipFwd.addEventListener("click", () => jumpToFlagTime(Math.min(duration, audio.currentTime + 5.0)));
  btnSpeed.addEventListener("click", () => {{
    speedIdx = (speedIdx + 1) % speeds.length; audio.playbackRate = speeds[speedIdx]; btnSpeed.innerText = speeds[speedIdx].toFixed(2) + "x";
  }});
  function setZoom(z) {{ zoomLevel = z; zoomSlider.value = z; zoomValue.innerText = z + "x"; resizeCanvas(); }}
  zoomSlider.addEventListener("input", (e) => setZoom(parseFloat(e.target.value)));
  btnZoomFit.addEventListener("click", () => setZoom(1));
  btnZoom5x.addEventListener("click", () => setZoom(5));
  btnZoom15x.addEventListener("click", () => setZoom(15));
  btnCopyTime.addEventListener("click", () => {{
    const txt = (audio.currentTime || 0).toFixed(3);
    navigator.clipboard.writeText(txt).then(() => {{
      btnCopyLabel.style.display = "none"; copyBadge.style.display = "inline";
      setTimeout(() => {{ copyBadge.style.display = "none"; btnCopyLabel.style.display = "inline"; }}, 1400);
    }}).catch(() => prompt("Tiempo actual (s):", txt));
  }});
  btnPrevFlag.addEventListener("click", () => {{
    const cur = audio.currentTime || 0; let target = sections[0] ? sections[0].startTime : 0;
    for (let i = sections.length - 1; i >= 0; i--) {{ if (sections[i].startTime < cur - 0.25) {{ target = sections[i].startTime; break; }} }}
    jumpToFlagTime(target);
  }});
  btnNextFlag.addEventListener("click", () => {{
    const cur = audio.currentTime || 0; let target = sections.length ? sections[sections.length - 1].startTime : 0;
    for (let i = 0; i < sections.length; i++) {{ if (sections[i].startTime > cur + 0.25) {{ target = sections[i].startTime; break; }} }}
    jumpToFlagTime(target);
  }});
  chkBeatGrid.addEventListener("change", draw);

  const initialSeek = {initial_seek_str};
  if (initialSeek !== null) {{
    audio.currentTime = initialSeek; timeCurrent.innerText = formatTime(initialSeek); updateMetronome(initialSeek);
    setTimeout(() => jumpToFlagTime(initialSeek), 80);
  }}
  resizeCanvas(); updateMetronome(initialSeek || 0);
</script>
</body>
</html>"""
