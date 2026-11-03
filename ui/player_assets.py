"""HTML5 Canvas and WebAudio template builder for the Dual-Theme DAW Live Waveform Player."""

import json
from typing import Any, Dict


def build_player_css(theme_mode: str = "dark") -> str:
    """Build CSS styles for the HTML5 waveform player in 'dark' or 'light' studio mode."""
    is_light = (theme_mode or "dark").strip().lower() == "light"
    bg, fg = ("#f8fafc", "#0f172a") if is_light else ("#020617", "#f8fafc")
    card, border = ("#ffffff", "#e2e8f0") if is_light else ("#0f172a", "#1e293b")
    muted_bg, muted_fg = ("#f1f5f9", "#64748b") if is_light else ("#1e293b", "#94a3b8")
    primary, primary_fg = ("#0284c7", "#ffffff") if is_light else ("#38bdf8", "#020617")
    hover_bg, hover_fg = ("#e0f2fe", "#0369a1") if is_light else ("#1e293b", "#38bdf8")
    accent, scroll_thumb = "#0ea5e9", ("#cbd5e1" if is_light else "#334155")

    return f"""
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700&family=JetBrains+Mono:wght@500;600;700&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; font-family: 'Inter', system-ui, sans-serif; }}
  body {{ background: {bg}; color: {fg}; padding: 6px; overflow: hidden; }}
  .material-symbols-rounded {{ font-family: 'Material Symbols Rounded'; font-weight: normal; font-style: normal; font-size: 14px; line-height: 1; display: inline-flex; align-items: center; vertical-align: middle; }}
  .player-card {{ background: {card}; border: 1px solid {border}; border-radius: 12px; padding: 12px 14px; box-shadow: 0 2px 6px rgba(2, 6, 23, 0.14); }}
  .header-bar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; border-bottom: 1px solid {border}; padding-bottom: 8px; gap: 10px; }}
  .header-left, .header-right, .btn-group, .zoom-controls {{ display: flex; align-items: center; gap: 8px; }}
  .header-title {{ font-size: 13px; font-weight: 700; color: {primary}; display: flex; align-items: center; gap: 6px; white-space: nowrap; }}
  .metronome-box {{ display: flex; align-items: center; gap: 8px; background: {bg}; border: 1px solid {border}; padding: 4px 10px; border-radius: 8px; }}
  .metro-light {{ width: 11px; height: 11px; border-radius: 50%; background: {muted_bg}; border: 1px solid {muted_fg}; transition: background-color 0.05s ease, box-shadow 0.05s ease; }}
  .metro-light.downbeat {{ background: {primary}; box-shadow: 0 0 8px {primary}, 0 0 14px {accent}; }} .metro-light.upbeat {{ background: {accent}; box-shadow: 0 0 6px {accent}; }}
  .metro-bpm {{ font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 700; color: {fg}; min-width: 72px; }}
  .metro-toggle {{ background: {card}; border: 1px solid {border}; border-radius: 6px; padding: 2px 7px; font-size: 11px; font-weight: 600; cursor: pointer; color: {muted_fg}; display: inline-flex; align-items: center; gap: 4px; }}
  .metro-toggle.active {{ background: {primary}; border-color: {primary}; color: {primary_fg}; }}
  .time-display {{ font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 700; color: {fg}; background: {bg}; padding: 4px 10px; border-radius: 8px; border: 1px solid {border}; font-variant-numeric: tabular-nums; }}
  .time-current {{ color: {primary}; }}
  .copy-time-btn {{ background: {bg}; color: {fg}; border: 1px solid {border}; border-radius: 8px; padding: 4px 10px; font-size: 12px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 4px; width: 146px; }}
  .copy-time-btn:hover {{ background: {hover_bg}; border-color: {primary}; color: {hover_fg}; }}
  .copy-badge {{ font-size: 11px; color: {primary}; font-weight: 700; display: none; align-items: center; gap: 3px; }}
  .waveform-wrapper {{ position: relative; width: 100%; height: 210px; background: {bg}; border: 1px solid {border}; border-radius: 8px; overflow-x: auto; overflow-y: hidden; cursor: crosshair; }}
  .waveform-wrapper::-webkit-scrollbar {{ height: 7px; }} .waveform-wrapper::-webkit-scrollbar-track {{ background: {muted_bg}; }}
  .waveform-wrapper::-webkit-scrollbar-thumb {{ background: {scroll_thumb}; border-radius: 4px; }} .waveform-wrapper::-webkit-scrollbar-thumb:hover {{ background: {primary}; }}
  #waveCanvas {{ display: block; height: 210px; }}
  .daw-hint-bar {{ display: flex; justify-content: space-between; align-items: center; margin-top: 6px; padding: 4px 10px; background: {bg}; border: 1px solid {border}; border-radius: 6px; font-size: 11px; color: {muted_fg}; font-weight: 500; gap: 8px; flex-wrap: wrap; }}
  .hint-item {{ display: inline-flex; align-items: center; gap: 4px; }}
  .controls-row {{ display: flex; justify-content: space-between; align-items: center; margin-top: 8px; gap: 8px; flex-wrap: wrap; }}
  button {{ background: {bg}; color: {fg}; border: 1px solid {border}; border-radius: 8px; padding: 5px 10px; font-size: 12px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; transition: all 0.12s ease; }}
  button:hover {{ background: {hover_bg}; border-color: {primary}; color: {hover_fg}; }}
  .btn-primary {{ background: {primary}; border-color: {primary}; color: {primary_fg}; }} .btn-primary:hover {{ background: {accent}; border-color: {accent}; color: #ffffff; }}
  .btn-danger {{ background: #ef4444; border-color: #ef4444; color: #ffffff; }} .btn-danger:hover {{ background: #dc2626; border-color: #dc2626; color: #ffffff; }}
  .icon-svg {{ width: 13px; height: 13px; fill: currentColor; flex-shrink: 0; }}
  .zoom-controls {{ background: {bg}; padding: 4px 10px; border-radius: 8px; border: 1px solid {border}; }}
  .zoom-label {{ font-size: 11px; color: {muted_fg}; font-weight: 600; }}
  input[type="range"] {{ accent-color: {primary}; cursor: pointer; width: 88px; }}
  .zoom-preset {{ padding: 3px 7px; font-size: 11px; border-radius: 6px; }}
  .chk-label {{ display: flex; align-items: center; gap: 4px; font-size: 11px; color: {fg}; font-weight: 500; cursor: pointer; }}
  .vol-controls {{ display: flex; align-items: center; gap: 5px; background: {bg}; border: 1px solid {border}; border-radius: 8px; padding: 3px 8px; flex-shrink: 0; }}
  .vol-btn {{ background: transparent; border: none; padding: 0; color: {fg}; cursor: pointer; display: inline-flex; align-items: center; }} .vol-btn:hover {{ background: transparent; color: {primary}; }}
  .vol-slider {{ width: 62px !important; height: 4px; accent-color: {primary}; cursor: pointer; }}
  .vol-val {{ font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; color: {muted_fg}; min-width: 26px; }}
"""


def build_player_js() -> str:
    """Build the interactive DAW waveform timeline JavaScript logic (wheel zoom, Shift/Ctrl pan, multi-tempo flags)."""
    return r"""
  const duration = data.duration || 1.0, envelope = data.envelope || [], sections = data.sections || data.flags || [];
  const beatOffsetSec = (data.beatOffsetMs || 0) / 1000.0, isLight = (data.themeMode || "dark") === "light";
  const themeColors = isLight
    ? { canvasBg: "#f8fafc", rulerBg: "#f1f5f9", border: "#e2e8f0", tick: "#cbd5e1", text: "#64748b", waveMain: "#0284c7", wavePeak: "#0ea5e9", playhead: "#0f172a", gridDown: "rgba(15, 23, 42, 0.28)", gridUp: "rgba(2, 132, 199, 0.18)" }
    : { canvasBg: "#020617", rulerBg: "#0f172a", border: "#1e293b", tick: "#334155", text: "#94a3b8", waveMain: "#38bdf8", wavePeak: "#0ea5e9", playhead: "#f8fafc", gridDown: "rgba(248, 250, 252, 0.26)", gridUp: "rgba(56, 189, 248, 0.18)" };

  const audio = document.getElementById("audioElement"), canvas = document.getElementById("waveCanvas"), ctx = canvas.getContext("2d"), wrapper = document.getElementById("waveWrapper");
  const btnPlayPause = document.getElementById("btnPlayPause"), playLabel = document.getElementById("playLabel"), playIcon = document.getElementById("playIcon");
  const btnStop = document.getElementById("btnStop");
  const timeCurrent = document.getElementById("timeCurrent"), timeTotal = document.getElementById("timeTotal");
  const btnCopyTime = document.getElementById("btnCopyTime"), btnCopyLabel = document.getElementById("btnCopyLabel"), copyBadge = document.getElementById("copyBadge");
  const btnPrevFlag = document.getElementById("btnPrevFlag"), btnNextFlag = document.getElementById("btnNextFlag");
  const zoomSlider = document.getElementById("zoomSlider"), zoomValue = document.getElementById("zoomValue");
  const btnZoomFit = document.getElementById("btnZoomFit"), btnZoom5x = document.getElementById("btnZoom5x"), btnZoom15x = document.getElementById("btnZoom15x");
  const chkFollow = document.getElementById("chkFollow"), chkBeatGrid = document.getElementById("chkBeatGrid");
  const metroLight = document.getElementById("metroLight"), metroBpm = document.getElementById("metroBpm"), btnMetroAudio = document.getElementById("btnMetroAudio"), metroLabel = document.getElementById("metroLabel");

  let zoomLevel = 1.0, isScrubbing = false, isPanning = false, panStartX = 0, panStartScroll = 0;
  let hoverTime = null, audioCtx = null, metroAudioEnabled = false, lastBeatIndex = -1, flagHitBoxes = [];
  const flagColors = ["#38bdf8", "#f59e0b", "#10b981", "#a855f7", "#f43f5e"];

  function initAudioContext() {
    if (!audioCtx) { const Ctx = window.AudioContext || window.webkitAudioContext; if (Ctx) audioCtx = new Ctx(); }
    if (audioCtx && audioCtx.state === "suspended") audioCtx.resume();
  }
  function playMetronomeClick(isDownbeat) {
    if (!audioCtx || !metroAudioEnabled) return;
    try {
      const osc = audioCtx.createOscillator(), gain = audioCtx.createGain();
      osc.type = "sine"; osc.frequency.setValueAtTime(isDownbeat ? 1200 : 820, audioCtx.currentTime);
      gain.gain.setValueAtTime(0.28, audioCtx.currentTime); gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.04);
      osc.connect(gain); gain.connect(audioCtx.destination); osc.start(); osc.stop(audioCtx.currentTime + 0.04);
    } catch (e) {}
  }
  btnMetroAudio.addEventListener("click", () => {
    initAudioContext(); metroAudioEnabled = !metroAudioEnabled;
    if (metroLabel) metroLabel.innerText = metroAudioEnabled ? "Metrónomo: ON" : "Metrónomo: OFF";
    btnMetroAudio.classList.toggle("active", metroAudioEnabled);
  });
  function formatTime(sec) {
    if (isNaN(sec) || sec < 0) sec = 0;
    const m = Math.floor(sec / 60), s = Math.floor(sec % 60), ms = Math.floor((sec % 1) * 1000);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
  }
  timeTotal.innerText = formatTime(duration);

  function getActiveSection(t) {
    let active = sections[0] || { startTime: 0, startBeat: 0, bpm: 120 };
    for (let i = 0; i < sections.length; i++) { if (t >= sections[i].startTime) active = sections[i]; else break; }
    return active;
  }
  function updateMetronome(curTime) {
    const sec = getActiveSection(curTime);
    metroBpm.innerText = Number(sec.bpm).toFixed(1) + " BPM";
    const beatInt = Math.floor((sec.startBeat || 0) + (curTime - sec.startTime) * (sec.bpm / 60.0));
    if (!audio.paused && beatInt !== lastBeatIndex && beatInt >= 0) {
      lastBeatIndex = beatInt;
      const isDownbeat = (beatInt % 4 === 0);
      playMetronomeClick(isDownbeat);
      metroLight.className = "metro-light " + (isDownbeat ? "downbeat" : "upbeat");
      setTimeout(() => { metroLight.className = "metro-light"; }, 90);
    }
  }
  function resizeCanvas() {
    const baseWidth = wrapper.clientWidth || 900;
    canvas.width = Math.max(baseWidth, Math.round(baseWidth * zoomLevel)); canvas.height = 210; draw();
  }
  window.addEventListener("resize", resizeCanvas);

  function draw() {
    const w = canvas.width, h = canvas.height, rulerH = 22, waveH = h - rulerH, midY = rulerH + waveH / 2;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = themeColors.canvasBg; ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = themeColors.rulerBg; ctx.fillRect(0, 0, w, rulerH);
    ctx.strokeStyle = themeColors.border; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(0, rulerH); ctx.lineTo(w, rulerH); ctx.stroke();

    sections.forEach((sec, idx) => {
      const nextTime = (idx + 1 < sections.length) ? sections[idx + 1].startTime : duration;
      const x0 = (sec.startTime / duration) * w, x1 = (nextTime / duration) * w, color = flagColors[idx % flagColors.length];
      ctx.save(); ctx.fillStyle = color;
      ctx.globalAlpha = isLight ? 0.06 : 0.08; ctx.fillRect(x0, rulerH, Math.max(0, x1 - x0), waveH);
      ctx.globalAlpha = 0.72; ctx.fillRect(x0, rulerH, Math.max(0, x1 - x0), 3.5); ctx.restore();
    });

    let stepSec = zoomLevel > 12 ? 0.5 : (zoomLevel > 6 ? 1 : (zoomLevel > 3 ? 2 : Math.max(5, Math.round(duration / 10))));
    ctx.fillStyle = themeColors.text; ctx.font = "10px 'JetBrains Mono', monospace";
    for (let t = 0; t <= duration; t += stepSec) {
      const x = (t / duration) * w;
      ctx.beginPath(); ctx.moveTo(x, rulerH - 6); ctx.lineTo(x, rulerH); ctx.strokeStyle = themeColors.tick; ctx.stroke();
      const lbl = t >= 60 ? `${Math.floor(t / 60)}m${Math.round(t % 60)}s` : `${t.toFixed(stepSec < 1 ? 1 : 0)}s`;
      ctx.fillText(lbl, x + 3, rulerH - 7);
    }

    const n = envelope.length;
    if (n > 1) {
      const grad = ctx.createLinearGradient(0, rulerH, 0, h);
      grad.addColorStop(0, themeColors.wavePeak); grad.addColorStop(0.5, themeColors.waveMain); grad.addColorStop(1, themeColors.wavePeak);
      ctx.fillStyle = grad; ctx.beginPath(); ctx.moveTo(0, midY);
      for (let i = 0; i < n; i++) ctx.lineTo((i / (n - 1)) * w, midY - envelope[i] * (waveH * 0.44));
      for (let i = n - 1; i >= 0; i--) ctx.lineTo((i / (n - 1)) * w, midY + envelope[i] * (waveH * 0.44));
      ctx.closePath(); ctx.fill();
      ctx.strokeStyle = themeColors.border; ctx.beginPath(); ctx.moveTo(0, midY); ctx.lineTo(w, midY); ctx.stroke();
    }

    if (chkBeatGrid && chkBeatGrid.checked) {
      for (let i = 0; i < sections.length; i++) {
        const sec = sections[i], nextTime = (i + 1 < sections.length) ? sections[i + 1].startTime : duration;
        if (sec.bpm > 20) {
          const beatInterval = 60.0 / sec.bpm;
          let beatTime = (i === 0 && sec.startTime === 0 && beatOffsetSec > 0) ? beatOffsetSec : sec.startTime, beatCount = 0;
          while (beatTime < nextTime - 0.001) {
            const bx = (beatTime / duration) * w, isDown = (beatCount % 4 === 0);
            ctx.beginPath(); ctx.moveTo(bx, rulerH); ctx.lineTo(bx, h);
            ctx.strokeStyle = isDown ? themeColors.gridDown : themeColors.gridUp;
            ctx.lineWidth = isDown ? 1.0 : 0.8; ctx.setLineDash(isDown ? [] : [2, 3]);
            ctx.stroke(); ctx.setLineDash([]);
            beatTime += beatInterval; beatCount++;
          }
        }
      }
    }

    flagHitBoxes = [];
    sections.forEach((sec, idx) => {
      const x = (sec.startTime / duration) * w, color = flagColors[idx % flagColors.length];
      ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.setLineDash([5, 3]);
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); ctx.setLineDash([]);
      const bpmDisp = Number.isInteger(sec.bpm) ? sec.bpm : Number(sec.bpm).toFixed(1).replace(/\.0$/, "");
      const label = `#${idx + 1} · ${bpmDisp} BPM (${sec.startTime.toFixed(2)}s)`;
      ctx.font = "bold 10px 'Inter', sans-serif";
      const tw = ctx.measureText(label).width, by = (idx % 2 === 0) ? rulerH + 6 : rulerH + 26, bw = tw + 10, bh = 17;
      ctx.fillStyle = color; ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(x + 2, by, bw, bh, 5); else ctx.rect(x + 2, by, bw, bh);
      ctx.fill(); ctx.fillStyle = "#020617"; ctx.fillText(label, x + 7, by + 12);
      flagHitBoxes.push({ xMin: x - 8, xMax: x + bw + 6, startTime: sec.startTime });
    });

    if (hoverTime !== null && hoverTime >= 0 && hoverTime <= duration) {
      const hx = (hoverTime / duration) * w;
      ctx.strokeStyle = themeColors.text; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(hx, rulerH); ctx.lineTo(hx, h); ctx.stroke();
    }

    const curTime = audio.currentTime || 0, curX = (curTime / duration) * w;
    ctx.save(); ctx.strokeStyle = themeColors.playhead; ctx.lineWidth = 2.2;
    ctx.beginPath(); ctx.moveTo(curX, 0); ctx.lineTo(curX, h); ctx.stroke();
    ctx.fillStyle = "#f43f5e"; ctx.beginPath();
    ctx.moveTo(curX - 6, 0); ctx.lineTo(curX + 6, 0); ctx.lineTo(curX, 9); ctx.closePath(); ctx.fill();
    ctx.restore();
  }

  function animationLoop() {
    const curTime = audio.currentTime || 0;
    if (!audio.paused) {
      timeCurrent.innerText = formatTime(curTime); updateMetronome(curTime);
      if (chkFollow.checked && zoomLevel > 1.0 && !isPanning) {
        const curX = (curTime / duration) * canvas.width, vl = wrapper.scrollLeft, vw = wrapper.clientWidth;
        if (curX > vl + vw * 0.8 || curX < vl) wrapper.scrollLeft = curX - vw * 0.2;
      }
      draw();
    }
    requestAnimationFrame(animationLoop);
  }
  requestAnimationFrame(animationLoop);

  function setZoom(z) {
    zoomLevel = Math.max(1, Math.min(16, Number(z.toFixed(2))));
    zoomSlider.value = zoomLevel;
    zoomValue.innerText = zoomLevel.toFixed(zoomLevel % 1 === 0 ? 0 : 1) + "x";
    resizeCanvas();
  }
  function jumpToFlagTime(targetSec) {
    audio.currentTime = targetSec; timeCurrent.innerText = formatTime(targetSec); updateMetronome(targetSec);
    if (chkFollow.checked) wrapper.scrollLeft = Math.max(0, (targetSec / duration) * canvas.width - wrapper.clientWidth * 0.3);
    draw();
  }
  function seekToX(clientX) {
    const clampedX = Math.max(0, Math.min(canvas.width, clientX - canvas.getBoundingClientRect().left));
    const targetSec = (clampedX / (canvas.width || 1)) * duration;
    audio.currentTime = targetSec; timeCurrent.innerText = formatTime(targetSec); updateMetronome(targetSec); draw();
  }

  wrapper.addEventListener("wheel", (e) => {
    e.preventDefault();
    if (e.shiftKey) { wrapper.scrollLeft += e.deltaY; return; }
    const rect = wrapper.getBoundingClientRect(), mouseX = e.clientX - rect.left;
    const ratio = (wrapper.scrollLeft + mouseX) / (canvas.width || 1);
    const factor = e.deltaY < 0 ? 1.18 : (1 / 1.18);
    setZoom(Math.max(1, Math.min(16, zoomLevel * factor)));
    wrapper.scrollLeft = Math.max(0, ratio * canvas.width - mouseX);
  }, { passive: false });

  canvas.addEventListener("mousedown", (e) => {
    initAudioContext();
    if (e.shiftKey || e.ctrlKey || e.metaKey || e.button === 1) {
      e.preventDefault(); isPanning = true; panStartX = e.clientX; panStartScroll = wrapper.scrollLeft;
      canvas.style.cursor = "grabbing"; return;
    }
    const x = e.clientX - canvas.getBoundingClientRect().left;
    for (let i = 0; i < flagHitBoxes.length; i++) {
      if (x >= flagHitBoxes[i].xMin && x <= flagHitBoxes[i].xMax) { jumpToFlagTime(flagHitBoxes[i].startTime); return; }
    }
    isScrubbing = true; seekToX(e.clientX);
  });

  window.addEventListener("mousemove", (e) => {
    if (isPanning) { wrapper.scrollLeft = panStartScroll - (e.clientX - panStartX); return; }
    if (isScrubbing) { seekToX(e.clientX); return; }
    const x = e.clientX - canvas.getBoundingClientRect().left;
    if (x >= 0 && x <= canvas.width) {
      hoverTime = (x / canvas.width) * duration;
      const overFlag = flagHitBoxes.some((b) => x >= b.xMin && x <= b.xMax);
      canvas.style.cursor = (e.shiftKey || e.ctrlKey || e.metaKey) ? "grab" : (overFlag ? "pointer" : "crosshair");
      draw();
    } else { hoverTime = null; }
  });

  window.addEventListener("mouseup", (e) => {
    isPanning = false; isScrubbing = false;
    canvas.style.cursor = (e.shiftKey || e.ctrlKey || e.metaKey) ? "grab" : "crosshair";
  });
  window.addEventListener("keydown", (e) => { if (e.shiftKey || e.ctrlKey || e.metaKey) canvas.style.cursor = "grab"; });
  window.addEventListener("keyup", () => { if (!isPanning) canvas.style.cursor = "crosshair"; });
  canvas.addEventListener("mouseleave", () => { hoverTime = null; draw(); });

  btnPlayPause.addEventListener("click", () => {
    initAudioContext();
    if (audio.paused) {
      audio.play(); playLabel.innerText = "Pausar"; playIcon.innerHTML = '<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>';
      btnPlayPause.classList.replace("btn-primary", "btn-danger");
    } else {
      audio.pause(); playLabel.innerText = "Reproducir"; playIcon.innerHTML = '<path d="M8 5v14l11-7z"/>';
      btnPlayPause.classList.replace("btn-danger", "btn-primary");
    }
  });
  btnStop.addEventListener("click", () => {
    audio.pause(); audio.currentTime = 0; playLabel.innerText = "Reproducir";
    playIcon.innerHTML = '<path d="M8 5v14l11-7z"/>'; btnPlayPause.classList.replace("btn-danger", "btn-primary"); jumpToFlagTime(0);
  });
  zoomSlider.addEventListener("input", (e) => setZoom(parseFloat(e.target.value)));
  btnZoomFit.addEventListener("click", () => setZoom(1)); btnZoom5x.addEventListener("click", () => setZoom(5)); btnZoom15x.addEventListener("click", () => setZoom(15));
  btnCopyTime.addEventListener("click", () => {
    const txt = (audio.currentTime || 0).toFixed(3);
    navigator.clipboard.writeText(txt).then(() => {
      btnCopyLabel.style.display = "none"; copyBadge.style.display = "inline-flex";
      setTimeout(() => { copyBadge.style.display = "none"; btnCopyLabel.style.display = "inline"; }, 1400);
    }).catch(() => prompt("Tiempo actual (s):", txt));
  });
  btnPrevFlag.addEventListener("click", () => {
    const cur = audio.currentTime || 0; let target = sections[0] ? sections[0].startTime : 0;
    for (let i = sections.length - 1; i >= 0; i--) { if (sections[i].startTime < cur - 0.25) { target = sections[i].startTime; break; } }
    jumpToFlagTime(target);
  });
  btnNextFlag.addEventListener("click", () => {
    const cur = audio.currentTime || 0; let target = sections.length ? sections[sections.length - 1].startTime : 0;
    for (let i = 0; i < sections.length; i++) { if (sections[i].startTime > cur + 0.25) { target = sections[i].startTime; break; } }
    jumpToFlagTime(target);
  });
  chkBeatGrid.addEventListener("change", draw);
  const btnVolMute = document.getElementById("btnVolMute"), volSlider = document.getElementById("volSlider"), volValue = document.getElementById("volValue"), volIcon = document.getElementById("volIcon");
  let savedVol = 0.75; audio.volume = 0.75;
  function updateVol(v) {
    volSlider.value = v; volValue.innerText = Math.round(v * 100) + "%";
    volIcon.innerHTML = v === 0
      ? '<path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>'
      : '<path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>';
  }
  if (volSlider) {
    volSlider.addEventListener("input", (e) => { const v = parseFloat(e.target.value); audio.volume = v; if (v > 0) savedVol = v; updateVol(v); });
    btnVolMute.addEventListener("click", () => { if (audio.volume > 0) { savedVol = audio.volume; audio.volume = 0; updateVol(0); } else { audio.volume = savedVol || 0.75; updateVol(audio.volume); } });
  }
"""


def build_waveform_player_html(
    data_uri: str = "", payload_json: str = "{}", initial_seek_str: str = "null", theme_mode: str = "dark", **kwargs: Any
) -> str:
    """Build the self-contained Dual-Theme HTML/CSS/JS interactive DAW waveform player."""
    mode = (theme_mode or "dark").strip().lower()
    if not data_uri and "audio_b64" in kwargs:
        data_uri = f"data:{kwargs.get('mime_type', 'audio/mp3')};base64,{kwargs['audio_b64']}"
    try:
        parsed_payload: Dict[str, Any] = json.loads(payload_json) if payload_json else {}
    except Exception:
        parsed_payload = {}
    for k in ("duration", "envelope"):
        if k in kwargs: parsed_payload[k] = kwargs[k]
    if "sections" in kwargs or "flags" in kwargs:
        parsed_payload["sections"] = kwargs.get("sections", kwargs.get("flags"))
    if "beat_offset_ms" in kwargs:
        parsed_payload["beatOffsetMs"] = int(kwargs["beat_offset_ms"] or 0)
    parsed_payload["themeMode"] = mode
    final_payload_json = json.dumps(parsed_payload)

    return f"""<!DOCTYPE html><html lang="es" class="{mode}"><head><meta charset="utf-8"/><style>{build_player_css(mode)}</style></head><body>
<div class="player-card">
  <div class="header-bar">
    <div class="header-left"><div class="header-title"><svg class="icon-svg" viewBox="0 0 24 24"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg><span>Monitor de Onda y Ritmo</span></div>
      <div class="metronome-box" title="Metrónomo sincronizado con las banderas de tempo"><div class="metro-light" id="metroLight"></div><span class="metro-bpm" id="metroBpm">120.0 BPM</span><button class="metro-toggle" id="btnMetroAudio" title="Activar click de metrónomo"><svg class="icon-svg" viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/></svg><span id="metroLabel">Metrónomo: OFF</span></button></div></div>
    <div class="header-right"><div class="time-display"><span class="time-current" id="timeCurrent">00:00.000</span> / <span id="timeTotal">00:00.000</span></div>
      <button class="copy-time-btn" id="btnCopyTime" title="Copiar segundo actual"><span id="btnCopyLabel">Copiar Tiempo</span><span class="copy-badge" id="copyBadge"><svg class="icon-svg" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg> Copiado</span></button></div>
  </div>
  <div class="waveform-wrapper" id="waveWrapper"><canvas id="waveCanvas"></canvas></div>
  <div class="daw-hint-bar"><span class="hint-item"><span class="material-symbols-rounded">mouse</span> Rueda: Zoom en cursor</span><span class="hint-item"><span class="material-symbols-rounded">keyboard</span> Shift / Ctrl + Arrastrar: Mover línea de tiempo</span><span class="hint-item"><span class="material-symbols-rounded">ads_click</span> Clic / Arrastrar: Mover reproductor</span></div>
  <div class="controls-row">
    <div class="btn-group">
      <button id="btnPlayPause" class="btn-primary"><svg class="icon-svg" id="playIcon" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg><span id="playLabel">Reproducir</span></button>
      <button id="btnStop" title="Reiniciar"><svg class="icon-svg" viewBox="0 0 24 24"><path d="M6 6h12v12H6z"/></svg><span>Detener</span></button>
      <button id="btnPrevFlag" title="Bandera anterior" class="zoom-preset"><svg class="icon-svg" viewBox="0 0 24 24"><path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/></svg><span>Bandera</span></button>
      <button id="btnNextFlag" title="Bandera siguiente" class="zoom-preset"><span>Bandera</span><svg class="icon-svg" viewBox="0 0 24 24"><path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/></svg></button>
    </div>
    <div class="zoom-controls">
      <span class="zoom-label">Zoom:</span><input type="range" id="zoomSlider" min="1" max="16" value="1" step="0.5"><span id="zoomValue" style="font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;min-width:28px;">1x</span>
      <button class="zoom-preset" id="btnZoomFit">1x</button><button class="zoom-preset" id="btnZoom5x">5x</button><button class="zoom-preset" id="btnZoom15x">15x</button>
      <label class="chk-label"><input type="checkbox" id="chkFollow" checked> Seguir</label><label class="chk-label" title="Mostrar cuadrícula de beats"><input type="checkbox" id="chkBeatGrid" checked> Cuadrícula</label>
    </div>
    <div class="vol-controls" title="Volumen de la música (ajústalo para escuchar mejor el metrónomo)">
      <button class="vol-btn" id="btnVolMute" title="Silenciar / Activar audio"><svg class="icon-svg" id="volIcon" viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg></button>
      <input type="range" id="volSlider" min="0" max="1" step="0.05" value="0.75" class="vol-slider" title="Ajustar volumen de la música">
      <span id="volValue" class="vol-val">75%</span>
    </div>
  </div>
</div>
<audio id="audioElement" src="{data_uri}" preload="auto"></audio>
<script>const data = {final_payload_json};{build_player_js()}
const initialSeek = {initial_seek_str}; if (initialSeek !== null) {{ audio.currentTime = initialSeek; timeCurrent.innerText = formatTime(initialSeek); updateMetronome(initialSeek); setTimeout(() => jumpToFlagTime(initialSeek), 80); }} resizeCanvas(); updateMetronome(initialSeek || 0);</script></body></html>"""


build_player_html = build_waveform_player_html
