// rowio-viewer.js
// Reusable viewer for (video -> canvas) with pose overlay.
// Public API:
//   const v = new RowIOViewer({ canvas, video, frameInfoEl, drawInfoEl, onLog, onMsg });
//   await v.load({ videoUrl, csvUrl, displayName });
//   v.play(); v.pause(); v.destroy();

export class RowIOViewer {
  constructor(opts) {
    this.canvas = opts.canvas;
    this.video  = opts.video;
    this.frameInfoEl = opts.frameInfoEl || null;
    this.drawInfoEl  = opts.drawInfoEl  || null;
    this.onLog = opts.onLog || (()=>{});
    this.onMsg = opts.onMsg || (()=>{});

    this.ctx = this.canvas.getContext('2d', { desynchronized: true, alpha: true });

    // overlay edge list
    this.EDGES = [
      'hip','knee','knee','ankle',
      'shoulder','elbow','elbow','wrist','wrist','hand',
      'shoulder','hip',
      'ear','shoulder'
    ];

    // state
    this.frames = [];
    this.times = [];
    this.coordsNormalized = false;
    this.avgDtMs = 33.3;
    this.SHIFT_BASE_MS = 0;
    this.shiftDynamic = 0;
    this.lastPresented = -1;
    this._vfcHandle = null;
    this._rafId = null;

    // wire once
    this._wireVideoEvents();
  }

  async load({ videoUrl, csvUrl, displayName }) {
    if (!videoUrl) throw new Error('RowIOViewer.load: missing videoUrl');

    // reset state
    this.frames = [];
    this.times = [];
    this.coordsNormalized = false;
    this.avgDtMs = 33.3;
    this.shiftDynamic = 0;
    this.lastPresented = -1;

    // CSV (optional)
    if (csvUrl) {
      try {
        const csvText = await (await fetch(csvUrl, { mode: 'cors', cache: 'no-store' })).text();
        this._parseCSV_longFormat(csvText);
        this._finalizeTiming();
        this._msg(`CSV frames: ${this.frames.length}, Δ≈${this.avgDtMs.toFixed(1)}ms`);
      } catch (e) {
        this._log('CSV error: ' + (e?.message || e));
        this._msg('CSV failed; showing video only');
        this.frames = [];
        this.times = [];
      }
    } else {
      this._msg('No CSV; showing video only');
    }

    // Prepare video
    this.video.crossOrigin = "anonymous";
    this.video.playsInline = true;
    this.video.muted = true; // allow programmatic play

    // Set src after flags (autoplay policies)
    this.video.src = videoUrl;
    this.video.load();

    // Wait for dimensions, size canvas, draw first frame
    await this._waitForEvent(this.video, 'loadedmetadata', 20000);
    this._sizeCanvasToVideo();
    await this._waitForEvent(this.video, 'loadeddata', 20000);
    this._drawAtTime(0, true);

    // Try to start (if caller click was a user gesture, this succeeds)
    try { await this.video.play(); }
    catch (err) {
      this._log(`VIDEO.play() blocked: ${err?.name||''} ${err?.message||err}`);
      this._msg('Click ▶ Play to start');
    }
  }

  play()  { if (this.video.src) this.video.play().catch(()=>{}); }
  pause() { if (this.video.src) this.video.pause(); }

  destroy() {
    this._stopLoop();
    this.video.removeAttribute('src');
    this.video.load();
  }

  setShiftBase(ms) {
    this.SHIFT_BASE_MS = Number(ms)||0;
    this.shiftDynamic = 0;
  }

  /* ---------- internal: video events & draw loop ---------- */
  _wireVideoEvents() {
    this.video.onplay    = () => { this.shiftDynamic = 0; this._startLoop(); };
    this.video.onpause   = () => { this._stopLoop(); };
    this.video.onseeking = () => { this.shiftDynamic = 0; this._drawAtTime((this.video.currentTime||0)*1000, true); };
    this.video.onended   = () => { this._stopLoop(); };
  }

  _startLoop() {
    this._stopLoop();
    if ('requestVideoFrameCallback' in HTMLVideoElement.prototype) {
      const cb = (_now, meta) => {
        if (meta.presentedFrames !== this.lastPresented) {
          this.lastPresented = meta.presentedFrames;
          this._drawAtTime(meta.mediaTime * 1000, false);
        }
        if (!this.video.paused && !this.video.ended)
          this._vfcHandle = this.video.requestVideoFrameCallback(cb);
      };
      this._vfcHandle = this.video.requestVideoFrameCallback(cb);
    } else {
      const tick = () => {
        this._drawAtTime((this.video.currentTime||0)*1000, false);
        if (!this.video.paused && !this.video.ended)
          this._rafId = requestAnimationFrame(tick);
      };
      this._rafId = requestAnimationFrame(tick);
    }
  }

  _stopLoop() {
    if (this._vfcHandle && this.video.cancelVideoFrameCallback) {
      this.video.cancelVideoFrameCallback(this._vfcHandle);
      this._vfcHandle = null;
    }
    if (this._rafId) { cancelAnimationFrame(this._rafId); this._rafId = null; }
  }

  _sizeCanvasToVideo() {
    const vw = this.video.videoWidth || 0, vh = this.video.videoHeight || 0;
    if (!vw || !vh) { this._msg('No video dimensions'); return; }
    this.canvas.width = vw;      // intrinsic pixels
    this.canvas.height = vh;
    this.canvas.style.width = "100%"; // responsive scale
  }

  _drawAtTime(t_ms, immediate) {
    const w = this.canvas.width, h = this.canvas.height;
    if (!w || !h) return;

    // 1) video
    try { this.ctx.drawImage(this.video, 0, 0, w, h); } catch {}

    // 2) overlay
    if (!this.times.length) {
      this._setText(this.frameInfoEl, "–");
      this._setText(this.drawInfoEl,  "kp=0");
      return;
    }

    const tTarget = t_ms + this.SHIFT_BASE_MS + this.shiftDynamic;
    const idx = this._nearestIndex(tTarget);
    const f = this.frames[idx];

    const err = f.t - tTarget;
    const bigJump = immediate || Math.abs(err) > Math.max(45, this.avgDtMs * 1.4);
    const gain = bigJump ? 0.95 : 0.20;
    this.shiftDynamic = this._clamp(this.shiftDynamic + gain * err, -500, 500);

    this._drawSkeleton(this.ctx, f.k, w, h);

    this._setText(this.frameInfoEl, `CSV frame ${f.i} • t=${Math.round(f.t)}ms • err=${err.toFixed(1)}ms • shift=${(this.SHIFT_BASE_MS+this.shiftDynamic).toFixed(1)}ms`);
    this._setText(this.drawInfoEl,  `kp=${Object.keys(f.k).length}`);
  }

  _drawSkeleton(ctx, k, w, h) {
    const toPx = (x, y) => this.coordsNormalized ? [x*w, y*h] : [x, y];
    ctx.save();

    // lines
    ctx.lineWidth = 2;
    ctx.strokeStyle = '#00e5ff';
    ctx.beginPath();
    for (let i=0; i<this.EDGES.length; i+=2) {
      const a = this.EDGES[i], b = this.EDGES[i+1];
      const pa = k[a], pb = k[b];
      if (!pa || !pb) continue;
      const [ax, ay] = toPx(pa.x, pa.y);
      const [bx, by] = toPx(pb.x, pb.y);
      ctx.moveTo(ax, ay); ctx.lineTo(bx, by);
    }
    ctx.stroke();

    // joints
    ctx.fillStyle = '#3b82f6';
    const r = 3;
    for (const key in k) {
      const p = k[key]; const [x, y] = toPx(p.x, p.y);
      ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI*2); ctx.fill();
    }
    ctx.restore();
  }

  /* ---------- internal: CSV parsing & timing ---------- */
  _parseCSV_longFormat(text) {
    const lines = text.replace(/\r/g,'').split('\n').filter(l => l.trim().length);
    if (!lines.length){ this.frames=[]; this.times=[]; return; }

    const header = lines[0].split(',').map(h => h.trim());
    const col = (name, alts=[]) => {
      const want = [name, ...alts].map(s => s.toLowerCase());
      return header.findIndex(h => want.includes(h.toLowerCase()));
    };

    const fiCol = col('frame_index', ['frame','index','i']);
    const tCol  = col('pts_ms', ['t','ms','time_ms']);
    const tcCol = col('timecode', ['tc','timecode_hhmmss']);
    const kpCol = col('keypoint', ['joint','part']);
    const xCol  = col('x', ['x_px','x_norm']);
    const yCol  = col('y', ['y_px','y_norm']);

    if (fiCol < 0 || kpCol < 0 || xCol < 0 || yCol < 0) {
      throw new Error('CSV missing required columns (need frame_index,keypoint,x,y; optional pts_ms/timecode).');
    }

    const map = new Map();
    let pixVotes = 0, normVotes = 0;

    for (let r = 1; r < lines.length; r++) {
      const cells = this._splitCSV(lines[r], header.length);
      const iVal = Number(cells[fiCol]);
      if (!Number.isFinite(iVal)) continue;

      let tms = Number(cells[tCol]);
      if (!Number.isFinite(tms) && tcCol >= 0) tms = this._timecodeToMs(cells[tcCol]);
      if (!Number.isFinite(tms)) tms = Math.round(iVal * 1000/30); // fallback

      const kp = String(cells[kpCol] || '').toLowerCase();
      const x = Number(cells[xCol]), y = Number(cells[yCol]);
      if (!Number.isFinite(x) || !Number.isFinite(y) || !kp) continue;

      if (!map.has(iVal)) map.set(iVal, { i: iVal, t: tms, k: {} });
      const fr = map.get(iVal);
      fr.t = tms;
      fr.k[kp] = { x, y };

      if (x >= 0 && x <= 1 && y >= 0 && y <= 1) normVotes++; else pixVotes++;
    }

    this.coordsNormalized = (normVotes > pixVotes);

    const arr = Array.from(map.values()).sort((a,b)=> (a.t - b.t) || (a.i - b.i));
    this.frames = arr;
    this.times  = arr.map(f => f.t);
  }

  _finalizeTiming() {
    if (!this.times.length){ this.avgDtMs = 33.3; return; }
    const diffs = [];
    for (let i=1; i<this.times.length; i++) diffs.push(this.times[i] - this.times[i-1]);
    diffs.sort((a,b)=>a-b);
    const med = diffs[Math.floor(diffs.length/2)] || 33.3;
    this.avgDtMs = Math.max(5, Math.min(100, med));
  }

  _nearestIndex(t) {
    let i = this._lowerBound(t);
    if (i <= 0) return 0;
    if (i >= this.times.length) return this.times.length - 1;
    const prev = i - 1;
    return (t - this.times[prev] <= this.times[i] - t) ? prev : i;
    }
  _lowerBound(t) {
    let lo = 0, hi = this.times.length;
    while (lo < hi){
      const mid = (lo + hi) >> 1;
      if (this.times[mid] >= t) hi = mid; else lo = mid + 1;
    }
    return lo;
  }

  /* ---------- helpers ---------- */
  _splitCSV(line, expectCols){
    const out = [];
    let cur = '', inQ = false;
    for (let i=0; i<line.length; i++){
      const ch = line[i];
      if (ch === '"'){
        if (inQ && line[i+1] === '"'){ cur += '"'; i++; }
        else inQ = !inQ;
      } else if (ch === ',' && !inQ){
        out.push(cur); cur = '';
      } else {
        cur += ch;
      }
    }
    out.push(cur);
    while (out.length < expectCols) out.push('');
    return out.map(s => s.trim());
  }

  _timecodeToMs(tc){
    const m = /^(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,3}))?$/.exec(String(tc||'').trim());
    if (!m) return NaN;
    const hh = +m[1], mm = +m[2], ss = +m[3], ms = +(m[4]||0);
    return ((hh*3600 + mm*60 + ss)*1000 + ms);
  }

  _clamp(v, lo, hi){ return Math.max(lo, Math.min(hi, v)); }
  _setText(el, s){ if (el) el.textContent = s; }
  _log(s){ try{ this.onLog?.(s); }catch{} }
  _msg(s){ try{ this.onMsg?.(s); }catch{} }

  _waitForEvent(el, type, timeoutMs=15000){
    return new Promise((resolve, reject) => {
      let to = null;
      const on = () => { cleanup(); resolve(); };
      const err = (e) => { cleanup(); reject(e); };
      const cleanup = () => { el.removeEventListener(type, on); el.removeEventListener('error', err); if (to) clearTimeout(to); };
      el.addEventListener(type, on, { once: true });
      el.addEventListener('error', err, { once: true });
      to = setTimeout(()=> err(new Error(`${type} timeout`)), timeoutMs);
    });
  }
}
