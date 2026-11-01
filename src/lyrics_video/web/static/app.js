"use strict";
// The sync page: tap the start and end of each caption while the song plays, adjust the times with the waveform and
// exact stills of the video, change the design, check both in a quick preview video, then save the timing file and
// the song file's design. Nothing is written without Save (the preview goes to a temporary folder of the server).

const LANGUAGES = { ja: "日本語", en: "English", es: "Español", fr: "Français" };
const STILL_DELAY_MS = 250;
const RENDER_POLL_MS = 500;
// The preview video follows the audio, which stays the one clock; it is moved when it drifts further than this.
const PREVIEW_DRIFT_SECONDS = 0.1;
const $ = (id) => document.getElementById(id);
const audio = $("audio");
const video = $("pvideo");

const state = {
  token: null,
  texts: {},
  language: "en",
  song: null,
  lines: [], // {rows, start, end}; null = not set; end null = until the next start
  undo: [], // {i, field, prev, group}
  group: 0, // undo entries of one action share a group
  mode: "tap",
  sel: { i: 0, field: "start" },
  multi: new Set(), // lines selected together for shifting; empty = only sel
  anchor: 0, // fixed end of a Shift range
  dirty: false,
  wave: null, // {data: Float32Array (mono), rate, peaks}
  drag: null,
  still: { timer: null, serial: 0, url: null },
  render: { snapshot: null, timer: null }, // the server's render task (video or preview), polled while it runs
  preview: { url: null, lines: null, design: null, pending: null }, // the last preview and what it was made from
  // The Design mode: the base design's name, the song file's overrides as edited, and every base design's values.
  design: { name: null, overrides: {}, bases: {}, panel: {}, dirty: false, fonts: null },
};

// --- Texts ---------------------------------------------------------------------------------------------------------

function t(key, params = {}) {
  const text = state.texts[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (match, name) => (name in params ? String(params[name]) : match));
}

const escapeHtml = (text) => text.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
// Help texts write keys as [[Space]]; they are shown as keys.
const withKeys = (text) => escapeHtml(text).replace(/\[\[(.+?)\]\]/g, "<kbd>$1</kbd>");

function stored(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function store(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Settings are only remembered when the browser allows it.
  }
}

function browserLanguage() {
  for (const tag of navigator.languages ?? [navigator.language]) {
    const language = tag.slice(0, 2).toLowerCase();
    if (language in LANGUAGES) return language;
  }
  return "en";
}

async function setLanguage(language) {
  state.texts = (await (await fetch(`/static/i18n/${language}.json`)).json()).messages;
  state.language = language;
  document.documentElement.lang = language;
  for (const element of document.querySelectorAll("[data-i18n]")) element.textContent = t(element.dataset.i18n);
  if (state.song) {
    showNotices();
    requestStill();
  }
  if (state.render.snapshot) showRender(state.render.snapshot);
  if (state.mode === "design") showDesign();
  render();
}

// --- Server --------------------------------------------------------------------------------------------------------

async function api(path, body) {
  const options = { headers: { "X-Token": state.token } };
  if (body !== undefined) {
    options.method = "POST";
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  if (!response.ok) {
    let detail;
    try {
      detail = await response.json();
    } catch {
      detail = { message: response.statusText };
    }
    const message = typeof detail.message === "string" ? detail.message : JSON.stringify(detail.detail ?? detail);
    const error = new Error(message);
    error.code = detail.code;
    throw error;
  }
  return response;
}

const payload = () => state.lines.map(({ rows, start, end }) => ({ rows, start, end }));
const designPayload = () => ({ name: state.design.name, overrides: state.design.overrides });

function showError(error) {
  $("error-message").textContent = error.message ?? String(error);
  $("error").hidden = false;
}

function setStatus(text) {
  $("status").textContent = text;
}

// --- Time helpers --------------------------------------------------------------------------------------------------

function formatTime(seconds) {
  if (seconds == null || Number.isNaN(seconds)) return "–";
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${(seconds - minutes * 60).toFixed(2).padStart(5, "0")}`;
}

const duration = () => state.song?.duration ?? (audio.duration || 0);
const offsetSeconds = () => (Number($("offset").value) || 0) / 1000;
const now = () => Math.max(0, audio.currentTime - offsetSeconds());

// --- Loading -------------------------------------------------------------------------------------------------------

async function loadSong() {
  setStatus(t("status.loading"));
  state.song = await (await api("/api/song")).json();
  state.lines = state.song.lines.map((line) => ({ rows: line.rows, start: line.start, end: line.end }));
  state.dirty = state.song.changes.length > 0;
  Object.assign(state.design, state.song.design, { overrides: structuredClone(state.song.design.overrides), dirty: false });
  applyCaptionTiming();
  $("song-title").textContent = state.song.title;
  document.title = `${state.song.title} – lyrics-video sync`;
  audio.src = `/api/audio?token=${encodeURIComponent(state.token)}`;
  showNotices();
  render();
  loadWave().catch((error) => setStatus(t("status.wave_failed", { message: error.message })));
}

async function loadWave() {
  setStatus(t("status.wave"));
  const data = await (await api("/api/audio")).arrayBuffer();
  const context = new AudioContext();
  const buffer = await context.decodeAudioData(data);
  const mono = new Float32Array(buffer.length);
  for (let channel = 0; channel < buffer.numberOfChannels; channel++) {
    const samples = buffer.getChannelData(channel);
    for (let k = 0; k < buffer.length; k++) mono[k] += samples[k] / buffer.numberOfChannels;
  }
  state.wave = { data: mono, rate: buffer.sampleRate, peaks: null };
  context.close();
  setStatus("");
  draw();
}

function showNotices() {
  const song = state.song;
  const notices = [];
  if (!song.timing_exists) notices.push(escapeHtml(t("notice.first", { lyrics: song.lyrics_file, timing: song.timing_file })));
  if (song.changes.length) {
    const added = song.changes.filter((c) => c.kind === "added");
    const removed = song.changes.filter((c) => c.kind === "removed");
    const list = (kind, items) =>
      items.map((c) => `<li>${escapeHtml(t(`notice.${kind}`))}: ${escapeHtml(c.rows.join(" / "))}</li>`).join("");
    notices.push(
      escapeHtml(t("notice.changes", { lyrics: song.lyrics_file, timing: song.timing_file, added: added.length, removed: removed.length })) +
        `<ul>${list("added", added)}${list("removed", removed)}</ul>`,
    );
  }
  if (!song.timing_configured) {
    notices.push(escapeHtml(t("notice.not_configured", { song: song.song_file, timing: song.timing_file })));
  }
  $("notices").innerHTML = notices.map((html) => `<div class="notice">${html}</div>`).join("");
}

// --- Marking -------------------------------------------------------------------------------------------------------

function setTime(i, field, seconds) {
  state.undo.push({ i, field, prev: state.lines[i][field], group: state.group });
  state.lines[i][field] = seconds == null ? null : Math.round(seconds * 100) / 100;
  state.dirty = true;
}

const nextLine = () => state.lines.findIndex((line) => line.start == null);

function lastStarted() {
  for (let i = state.lines.length - 1; i >= 0; i--) if (state.lines[i].start != null) return i;
  return -1;
}

function markStart() {
  const i = nextLine();
  if (i < 0) return;
  state.group++;
  setTime(i, "start", now());
}

function markEnd() {
  const i = lastStarted();
  if (i < 0 || state.lines[i].end != null) return;
  state.group++;
  setTime(i, "end", Math.max(now(), state.lines[i].start + 0.05));
}

function undo() {
  const group = state.undo.at(-1)?.group;
  while (state.undo.length && state.undo.at(-1).group === group) {
    const entry = state.undo.pop();
    state.lines[entry.i][entry.field] = entry.prev;
  }
  state.dirty = true;
  changed();
}

// --- Adjusting -----------------------------------------------------------------------------------------------------

function select(i, field) {
  state.sel = { i, field };
  render();
  scrollToRow(i);
}

const selectedTime = () => state.lines[state.sel.i]?.[state.sel.field] ?? null;

function shift(seconds) {
  if (state.multi.size > 1) {
    const rows = [...state.multi];
    const times = rows.flatMap((i) => [state.lines[i].start, state.lines[i].end]).filter((s) => s != null);
    if (!times.length) return;
    const earliest = Math.min(...times);
    if (earliest + seconds < 0) seconds = -earliest;
    state.group++;
    for (const i of rows) {
      for (const field of ["start", "end"]) {
        if (state.lines[i][field] != null) setTime(i, field, state.lines[i][field] + seconds);
      }
    }
    changed();
    return;
  }
  const time = selectedTime();
  if (time == null) return;
  state.group++;
  setTime(state.sel.i, state.sel.field, Math.max(0, time + seconds));
  if (audio.paused) audio.currentTime = state.lines[state.sel.i][state.sel.field];
  changed();
}

function selectAll() {
  state.lines.forEach((_, i) => state.multi.add(i));
  render();
}

function replay() {
  const line = state.lines[state.sel.i];
  const time = line?.start ?? selectedTime();
  if (time == null) return;
  audio.currentTime = Math.max(0, time - 2);
  audio.play();
}

function setToPlayhead() {
  if (!state.lines[state.sel.i]) return;
  state.group++;
  setTime(state.sel.i, state.sel.field, now());
  changed();
}

function clearTime() {
  if (selectedTime() == null) return;
  state.group++;
  setTime(state.sel.i, state.sel.field, null);
  changed();
}

// --- Saving --------------------------------------------------------------------------------------------------------

async function save() {
  try {
    const written = [];
    if (state.dirty || !state.design.dirty) {
      const result = await (await api("/api/timing", { lines: payload() })).json();
      state.dirty = false;
      state.song.timing_exists = true;
      state.song.changes = [];
      written.push(result.timing_file);
    }
    if (state.design.dirty) {
      const result = await (await api("/api/design", designPayload())).json();
      state.design.dirty = false;
      written.push(result.song_file);
    }
    showNotices();
    setStatus(t("save.done", { file: written.join(", ") }));
    render();
  } catch (error) {
    showError(error);
  }
}

const unsaved = () => state.dirty || state.design.dirty;

// --- Rendering the video -------------------------------------------------------------------------------------------

const rendering = () => state.render.snapshot?.state === "running";
const renderingVideo = () => rendering() && state.render.snapshot.kind !== "preview";

// The server renders the saved timing file, so the button waits for Save; an existing video is replaced only on a yes.
async function startRender(overwrite = false) {
  if (unsaved() || !state.song?.timing_exists || rendering()) return;
  $("render").disabled = true;
  showRender({ kind: "video", state: "preparing" });
  try {
    showRender(await (await api("/api/render", { overwrite })).json());
    pollRender();
  } catch (error) {
    if (error.code === "output_exists" && !overwrite) {
      $("render-bar").hidden = true;
      if (confirm(t("render.replace", { file: error.message.replace(/ exists$/, "") }))) return startRender(true);
    } else {
      showRender({ kind: "video", state: "failed", error: { message: error.message } });
    }
  } finally {
    render();
  }
}

// The preview is made from the lines as they are now, saved or not; it only replaces the last preview when done.
async function startPreview() {
  if (!state.song || rendering()) return;
  $("preview-video").disabled = true;
  showRender({ kind: "preview", state: "preparing" });
  const lines = payload();
  const design = designPayload();
  try {
    const snapshot = await (await api("/api/preview", { lines, design })).json();
    state.preview.pending = { lines, design: JSON.stringify(design) };
    showRender(snapshot);
    pollRender();
  } catch (error) {
    showRender({ kind: "preview", state: "failed", error: { message: error.message } });
  } finally {
    render();
  }
}

function previewReady() {
  state.preview.lines = state.preview.pending.lines;
  state.preview.design = state.preview.pending.design;
  state.preview.pending = null;
  state.preview.url = `/api/preview/video?token=${encodeURIComponent(state.token)}&v=${Date.now()}`;
  video.src = state.preview.url;
}

const lineKey = (line) => JSON.stringify([line.rows, line.start, line.end]);

// A line whose text or times changed since the preview was made: the preview shows it as it was.
function previewStale(i) {
  const made = state.preview.lines;
  if (!made) return false;
  if (made.length !== state.lines.length) return true;
  return lineKey(made[i]) !== lineKey(state.lines[i]);
}

const previewDesignOutdated = () => state.preview.design != null && state.preview.design !== JSON.stringify(designPayload());
const previewOutdated = () => previewDesignOutdated() || state.lines.some((_, i) => previewStale(i));

function pollRender() {
  clearTimeout(state.render.timer);
  state.render.timer = setTimeout(async () => {
    const kind = state.render.snapshot?.kind;
    try {
      const snapshot = await (await api("/api/render")).json();
      showRender(snapshot);
      if (snapshot.kind === "preview" && snapshot.state === "done" && state.preview.pending) previewReady();
    } catch (error) {
      showRender({ kind, state: "failed", error: { message: error.message } });
    }
    if (rendering()) pollRender();
    else render();
  }, RENDER_POLL_MS);
}

function showRender(snapshot) {
  if (snapshot.state !== "preparing") state.render.snapshot = snapshot;
  const bar = $("render-bar");
  bar.hidden = snapshot.state === "idle";
  bar.classList.toggle("failed", snapshot.state === "failed");
  const running = snapshot.state === "running" || snapshot.state === "preparing";
  const fraction = snapshot.frames ? snapshot.frame / snapshot.frames : 0;
  $("render-progress").hidden = !running;
  $("render-progress").value = fraction;
  const preview = snapshot.kind === "preview";
  const prefix = preview ? "preview_video" : "render";
  $("render-cancel").hidden = snapshot.state !== "running";
  $("render-reveal").hidden = snapshot.state !== "done" || preview;
  $("render-close").hidden = running;
  let text = "";
  switch (snapshot.state) {
    case "preparing":
      text = t(`${prefix}.preparing`);
      break;
    case "running": {
      const left = snapshot.frame > 0 ? Math.round((snapshot.elapsed * (snapshot.frames - snapshot.frame)) / snapshot.frame) : null;
      text = t(`${prefix}.running`, {
        file: snapshot.output,
        percent: Math.floor(fraction * 100),
        left: left == null ? "–" : `${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")}`,
      });
      break;
    }
    case "done":
      text = t(`${prefix}.done`, { file: snapshot.output, seconds: Math.round(snapshot.elapsed) });
      break;
    case "cancelled":
      text = t(`${prefix}.cancelled`);
      break;
    case "failed":
      text = t(`${prefix}.failed`, { message: snapshot.error?.message ?? "" });
      break;
  }
  if (!preview && snapshot.untimed && ["running", "done"].includes(snapshot.state)) {
    text += " " + t("render.untimed", { count: snapshot.untimed });
  }
  $("render-text").textContent = text;
}

async function cancelRender() {
  try {
    showRender(await (await api("/api/render/cancel", {})).json());
  } catch (error) {
    showError(error);
  }
}

async function revealRender() {
  try {
    await api("/api/render/reveal", {});
  } catch (error) {
    showError(error);
  }
}

// --- Checks --------------------------------------------------------------------------------------------------------

// The same rules as the server: starts increase, an end lies after its start and not after the next start.
function isBad(i, field) {
  const line = state.lines[i];
  const time = line[field];
  if (time == null) return false;
  if (time >= duration() && duration() > 0) return true;
  if (field === "end") {
    if (line.start == null || time <= line.start) return true;
    const next = state.lines.slice(i + 1).find((l) => l.start != null);
    return next != null && time > next.start + 0.001;
  }
  for (let j = i - 1; j >= 0; j--) {
    const before = state.lines[j];
    if (before.start != null) return time <= before.start || (before.end != null && time < before.end - 0.001);
  }
  return false;
}

// --- Captions in time (as in the video; see backdrop.py) -------------------------------------------------------------

function captionWindows() {
  const { lead, fade, transition } = state.song;
  const timed = state.lines.filter((line) => line.start != null);
  const captions = timed.map((line, i) => ({
    rows: line.rows,
    start: line.start,
    end: line.end ?? (i + 1 < timed.length ? timed[i + 1].start : duration()),
  }));
  const starts = captions.map((c) => c.start - lead);
  return captions.map((caption, i) => {
    let end;
    if (i + 1 === captions.length) end = Math.min(caption.end + fade, Math.max(duration(), caption.end));
    else if (transition === "crossfade") end = Math.min(caption.end, starts[i + 1]) + fade;
    else end = Math.min(caption.end + fade, starts[i + 1]);
    if (i + 2 < captions.length) end = Math.min(end, starts[i + 2]);
    return { rows: caption.rows, start: starts[i], end };
  });
}

function fadeOpacity(seconds, start, end, fade) {
  if (!(start <= seconds && seconds < end)) return 0;
  fade = Math.min(fade, (end - start) / 2);
  if (fade <= 0) return 1;
  return Math.max(0, Math.min(1, (seconds - start) / fade, (end - seconds) / fade));
}

function shownCaptions(seconds) {
  if (!state.song) return [];
  return captionWindows()
    .map((w) => ({ rows: w.rows, opacity: fadeOpacity(seconds, w.start, w.end, state.song.fade) }))
    .filter((c) => c.opacity > 0)
    .slice(-2);
}

function currentLine(seconds) {
  let current = -1;
  state.lines.forEach((line, i) => {
    if (line.start != null && line.start <= seconds && (line.end == null || seconds < line.end)) current = i;
  });
  return current;
}

// --- Preview -------------------------------------------------------------------------------------------------------

function updatePreview() {
  const playing = !audio.paused;
  const withVideo = playing && state.preview.url != null;
  $("live").hidden = !playing || withVideo;
  video.hidden = !withVideo;
  if (!withVideo && !video.paused) video.pause();
  if (!playing) return;
  if (withVideo) {
    followAudio();
    const { width, height, fps } = state.song.preview;
    const note = previewDesignOutdated() ? "preview_video.outdated_design" : previewOutdated() ? "preview_video.outdated" : "preview_video.playing";
    $("preview-note").textContent = t(note, { width, height, fps });
    return;
  }
  const shown = shownCaptions(audio.currentTime);
  [$("cap-a"), $("cap-b")].forEach((element, k) => {
    element.style.opacity = shown[k]?.opacity ?? 0;
    element.textContent = shown[k]?.rows.join("\n") ?? "";
  });
  $("preview-note").textContent = t("preview.live", {
    lead: state.song.lead,
    fade: state.song.fade,
    transition: t(`transition.${state.song.transition}`),
  });
}

function followAudio() {
  if (video.readyState === 0 || video.seeking) return;
  if (Math.abs(video.currentTime - audio.currentTime) > PREVIEW_DRIFT_SECONDS) video.currentTime = audio.currentTime;
  if (video.paused) video.play().catch(() => {});
}

// An exact still of the video at the playhead, drawn by the server whenever the song is paused and something changed.
function requestStill() {
  if (!state.song) return;
  clearTimeout(state.still.timer);
  state.still.timer = setTimeout(async () => {
    if (!audio.paused) return;
    const serial = ++state.still.serial;
    const time = Math.min(audio.currentTime, Math.max(0, duration() - 0.001));
    $("preview-note").textContent = t("preview.drawing");
    try {
      const blob = await (await api("/api/still", { lines: payload(), design: designPayload(), time })).blob();
      if (serial !== state.still.serial) return;
      if (state.still.url) URL.revokeObjectURL(state.still.url);
      state.still.url = URL.createObjectURL(blob);
      $("still").src = state.still.url;
      $("preview-note").textContent = t("preview.still", { time: formatTime(time) });
      $("design-error").hidden = true;
    } catch (error) {
      if (serial !== state.still.serial) return;
      $("preview-note").textContent = t("preview.failed", { message: error.message });
      $("design-error").textContent = error.message;
      $("design-error").hidden = state.mode !== "design";
    }
  }, STILL_DELAY_MS);
}

function changed() {
  render();
  requestStill();
}

// --- Design --------------------------------------------------------------------------------------------------------

// The settings shown in Design mode; the song file can set every other design key too. `when` hides a setting that
// does not apply (for example the band color of a gradient caption).
const range = (min, max, step) => ({ type: "range", min, max, step });
const DESIGN_FIELDS = [
  { part: "background", fields: [["dim", range(0, 1, 0.05)], ["blur", range(0, 40, 1)]] },
  {
    part: "title",
    fields: [
      ["enabled", { type: "bool" }],
      ["position", { type: "select", options: ["top-center", "top-left"] }],
      ["font", { type: "font" }],
      ["size", range(20, 160, 1)],
      ["color", { type: "color" }],
      ["bold", { type: "bool" }],
      ["italic", { type: "bool" }],
      ["letter_spacing", range(0, 30, 1)],
      ["rule", { type: "bool" }],
      ["panel", { type: "panel" }],
      ...panelFields(),
      ["shadow.blur", range(0, 20, 1)],
      ["shadow.opacity", range(0, 1, 0.05)],
    ],
  },
  {
    part: "caption",
    fields: [
      ["style", { type: "select", options: ["band", "gradient", "panel"] }],
      ["font", { type: "font" }],
      ["size", { ...range(20, 120, 1), when: (v) => v("style") !== "band" }],
      ["text_color", { type: "color" }],
      ["bold", { type: "bool" }],
      ["italic", { type: "bool" }],
      ["band_color", { type: "color", when: (v) => v("style") === "band" }],
      ["band_opacity", { ...range(0, 1, 0.05), when: (v) => v("style") === "band" }],
      ["band_height", { ...range(100, 500, 1), when: (v) => v("style") === "band" }],
      ["gradient.color", { type: "color", when: (v) => v("style") === "gradient" }],
      ["gradient.opacity", { ...range(0, 1, 0.05), when: (v) => v("style") === "gradient" }],
      ["gradient.height", { ...range(50, 800, 10), when: (v) => v("style") === "gradient" }],
      ...panelFields((v) => v("style") === "panel"),
      ["shadow.blur", range(0, 20, 1)],
      ["shadow.opacity", range(0, 1, 0.05)],
      ["lead_seconds", range(0, 1, 0.05)],
      ["fade_seconds", range(0, 1.5, 0.05)],
      ["transition", { type: "select", options: ["sequential", "crossfade"] }],
    ],
  },
  {
    part: "credits",
    fields: [
      ["enabled", { type: "bool" }],
      ["position", { type: "select", options: ["center", "bottom-right"] }],
      ["font", { type: "font" }],
      ["size", range(16, 100, 1)],
      ["color", { type: "color" }],
      ["bold", { type: "bool" }],
      ["italic", { type: "bool" }],
      ["dim", range(0, 1, 0.05)],
      ["panel", { type: "panel" }],
      ...panelFields(),
      ["show_seconds", range(0, 20, 0.5)],
      ["fade_seconds", range(0, 5, 0.1)],
      ["shadow.blur", range(0, 20, 1)],
      ["shadow.opacity", range(0, 1, 0.05)],
    ],
  },
  {
    part: "spectrum",
    fields: [
      ["preset", { type: "select", options: () => Object.keys(state.design.spectrum.presets), raw: true }],
      ["look.baseline_y", { ...range(0, 1, 0.01), when: flatLook }],
      ["look.max_height", { ...range(0, 1, 0.01), when: flatLook }],
      ["look.margin_x", { ...range(0, 0.3, 0.01), when: flatLook }],
      ["look.mirror", { type: "bool", when: flatLook }],
      ["look.style", { type: "select", options: ["bars", "blocks"], when: flatLook }],
      ["look.bar_fill", { ...range(0.05, 1, 0.05), when: flatLook }],
      ["look.block_height_px", { ...range(2, 40, 1), when: (v) => flatLook() && v("look.style") === "blocks" }],
      ["look.block_gap_px", { ...range(0, 20, 1), when: (v) => flatLook() && v("look.style") === "blocks" }],
      ["look.response", { ...range(0.5, 3, 0.1), when: flatLook }],
      ["fill.mode", { type: "select", options: ["solid", "frequency"], when: flatLook }],
      ["foreground", { type: "color", when: (v) => !flatLook() || v("fill.mode") !== "frequency" }],
      ["fill.colors", { type: "colors", when: (v) => flatLook() && v("fill.mode") === "frequency" }],
      ["fx.glow_radius_px", range(0, 40, 1)],
      ["fx.glow_strength", range(0, 1, 0.05)],
      // The song is analysed again for each new analysis value (about half a second), so these apply on release.
      ["analysis.bands", { ...range(16, 1024, 16), lazy: true }],
      ["analysis.min_frequency", { ...range(20, 500, 10), lazy: true }],
      ["analysis.max_frequency", { ...range(2000, 20000, 500), lazy: true }],
      ["analysis.gain", { ...range(0.1, 4, 0.1), lazy: true }],
      ["analysis.attack_seconds", { ...range(0, 0.5, 0.01), lazy: true }],
      ["analysis.release_seconds", { ...range(0, 1.5, 0.05), lazy: true }],
    ],
  },
];

// The preset the spectrum starts from: the song file's own, else the design's, else "default".
function currentPreset() {
  const name = state.design.spectrum.song_preset ?? designValue("spectrum.preset") ?? "default";
  return state.design.spectrum.presets[name] ?? state.design.spectrum.presets.default;
}

// The perspective look has other settings (a camera), which stay in files, and only one color.
function flatLook() {
  return currentPreset().look.kind !== "perspective";
}
const GRADIENT_START = "#4FA3FF";

// The box settings: a caption panel's whenever its style is "panel", a title or credits box while it is on.
function panelFields(when = (v) => v("panel") != null) {
  return [
    ["panel.color", { type: "color", when }],
    ["panel.opacity", { ...range(0, 1, 0.05), when }],
    ["panel.blur", { ...range(0, 60, 1), when }],
    ["panel.radius", { ...range(0, 80, 1), when }],
  ];
}

const getPath = (object, path) => path.split(".").reduce((value, key) => (value == null ? undefined : value[key]), object);
const hasPath = (object, path) => getPath(object, path) !== undefined;

function setPath(object, path, value) {
  const keys = path.split(".");
  let target = object;
  for (const key of keys.slice(0, -1)) {
    if (typeof target[key] !== "object" || target[key] === null) target[key] = {};
    target = target[key];
  }
  target[keys.at(-1)] = value;
}

// Removes the override and the tables it leaves empty; an empty box table stays, as it turns the box on.
function deletePath(object, path) {
  const keys = path.split(".");
  const parents = [object];
  for (const key of keys.slice(0, -1)) {
    const next = parents.at(-1)[key];
    if (typeof next !== "object" || next === null) return;
    parents.push(next);
  }
  delete parents.at(-1)[keys.at(-1)];
  for (let depth = keys.length - 1; depth > 0; depth--) {
    const key = keys[depth - 1];
    if (key === "panel" || Object.keys(parents[depth]).length) break;
    delete parents[depth - 1][key];
  }
}

const baseDesign = () => state.design.bases[state.design.name];

// The design's own value of a setting; inside a box the base design does not have, the defaults of a box; for a
// spectrum key the design does not change, the preset's value.
function baseValue(path) {
  const value = getPath(baseDesign(), path);
  if (path === "spectrum.preset") return value ?? "default";
  if (path.startsWith("spectrum.")) return value ?? getPath(currentPreset(), path.slice("spectrum.".length));
  const box = path.match(/^(\w+)\.panel\.(\w+)$/);
  if (box && getPath(baseDesign(), `${box[1]}.panel`) == null) return state.design.panel[box[2]];
  return value;
}

function designValue(path) {
  if (path.endsWith(".panel") && path.split(".").length === 2) {
    const override = getPath(state.design.overrides, path);
    if (override === false) return null;
    return override !== undefined ? override : baseValue(path);
  }
  return hasPath(state.design.overrides, path) ? getPath(state.design.overrides, path) : baseValue(path);
}

const hex = (value) =>
  Array.isArray(value) ? "#" + value.map((c) => c.toString(16).padStart(2, "0")).join("") : String(value ?? "#000000").toLowerCase();
const colorList = (value) => Array.isArray(value) && value.every((item) => typeof item === "string");

function same(a, b) {
  if (colorList(a) || colorList(b)) return JSON.stringify((a ?? []).map(hex)) === JSON.stringify((b ?? []).map(hex));
  if (Array.isArray(a) || Array.isArray(b) || String(a).startsWith("#")) return hex(a) === hex(b);
  return a === b;
}

function setDesignValue(path, value) {
  if (same(value, baseValue(path))) deletePath(state.design.overrides, path);
  else setPath(state.design.overrides, path, value);
}

function setBox(part, on) {
  const path = `${part}.panel`;
  const inBase = getPath(baseDesign(), path) != null;
  if (on) {
    if (getPath(state.design.overrides, path) === false || inBase) deletePath(state.design.overrides, path);
    else setPath(state.design.overrides, path, {});
  } else if (inBase) setPath(state.design.overrides, path, false);
  else deletePath(state.design.overrides, path);
}

function changedSetting(path) {
  if (path.endsWith(".font")) return hasPath(state.design.overrides, path) || hasPath(state.design.overrides, `${path}_face`);
  return hasPath(state.design.overrides, path);
}

// The live preview while playing follows the caption timing of the design as edited.
function applyCaptionTiming() {
  if (!state.song) return;
  state.song.lead = designValue("caption.lead_seconds");
  state.song.fade = designValue("caption.fade_seconds");
  state.song.transition = designValue("caption.transition");
}

function designChanged(rebuild) {
  state.design.dirty = true;
  applyCaptionTiming();
  if (rebuild) showDesign();
  else markChanged();
  render();
  requestStill();
}

function markChanged() {
  for (const row of $("design-fields").querySelectorAll(".field")) row.classList.toggle("changed", changedSetting(row.dataset.path));
}

async function showDesign() {
  if (!state.song) return;
  if (!state.design.fonts) {
    state.design.fonts = [];
    try {
      state.design.fonts = await (await api("/api/fonts")).json();
    } catch (error) {
      showError(error);
    }
  }
  const select = $("design-base");
  select.replaceChildren(...Object.keys(state.design.bases).map((name) => new Option(name, name)));
  select.value = state.design.name;
  const html = [];
  for (const group of DESIGN_FIELDS) {
    html.push(`<h3>${escapeHtml(t(`design_part.${group.part}`))}</h3>`);
    if (group.part === "spectrum") html.push(songSpectrumNote());
    const value = (key) => designValue(`${group.part}.${key}`);
    for (const [key, field] of group.fields) {
      if (field.when && !field.when(value)) continue;
      html.push(fieldHtml(`${group.part}.${key}`, key, field));
    }
  }
  $("design-fields").innerHTML = html.join("");
  markChanged();
}

// The song file's own [spectrum] wins over the design, so its settings here would not show.
function songSpectrumNote() {
  const { song_preset: preset, song_set: overrides } = state.design.spectrum;
  if (!preset && !overrides.length) return "";
  const what = [preset ? `preset = "${preset.split("/").at(-1)}"` : "", ...overrides].filter(Boolean).join(", ");
  return `<p class="note">${escapeHtml(t("design.song_spectrum", { what }))}</p>`;
}

function fieldHtml(path, key, field) {
  const value = designValue(path);
  const id = `f-${path.replaceAll(".", "-")}`;
  let control;
  switch (field.type) {
    case "range":
      control =
        `<input type="range" id="${id}" min="${field.min}" max="${field.max}" step="${field.step}" value="${value}">` +
        `<input type="number" min="${field.min}" step="${field.step}" value="${value}">`;
      break;
    case "color":
      control = `<input type="color" id="${id}" value="${hex(value)}"><input class="hex" type="text" value="${hex(value)}" maxlength="7">`;
      break;
    case "colors":
      control =
        (value ?? []).map((color, i) => `<input type="color" ${i ? "" : `id="${id}"`} data-index="${i}" value="${hex(color)}">`).join("") +
        ((value ?? []).length < 4 ? `<button type="button" class="add-color" title="${escapeHtml(t("design.add_color"))}">+</button>` : "") +
        ((value ?? []).length > 2 ? `<button type="button" class="remove-color" title="${escapeHtml(t("design.remove_color"))}">−</button>` : "");
      break;
    case "bool":
      control = `<input type="checkbox" id="${id}" ${value ? "checked" : ""}>`;
      break;
    case "panel":
      control = `<input type="checkbox" id="${id}" ${value != null ? "checked" : ""}>`;
      break;
    case "select":
      control = `<select id="${id}">${(typeof field.options === "function" ? field.options() : field.options)
        .map((option) => {
          const label = field.raw ? String(option).split("/").at(-1) : t(`design_value.${option}`);
          return `<option value="${escapeHtml(option)}" ${option === value ? "selected" : ""}>${escapeHtml(label)}</option>`;
        })
        .join("")}</select>`;
      break;
    case "font":
      control = fontSelect(id, path);
      break;
  }
  const label = escapeHtml(t(`design_field.${key.replaceAll(".", "_")}`));
  return `<div class="field" data-path="${path}" data-type="${field.type}" ${field.lazy ? "data-lazy" : ""}><label for="${id}">${label}</label><span class="control">${control}</span><button type="button" class="reset" title="${escapeHtml(t("design.reset"))}">↺</button></div>`;
}

// A font is a file and a face in it; the list holds the fonts of this Mac and the song file's, plus the one in use.
function fontSelect(id, path) {
  const current = hasPath(state.design.overrides, path) || hasPath(state.design.overrides, `${path}_face`)
    ? JSON.stringify([designValue(path), designValue(`${path}_face`) ?? 0])
    : "";
  const base = baseValue(path);
  const fallback = t("design.font_default", { font: base ? String(base).split("/").at(-1) : "fonts.default" });
  const options = [`<option value="">${escapeHtml(fallback)}</option>`];
  let found = current === "";
  for (const font of state.design.fonts) {
    const value = JSON.stringify([font.path, font.face]);
    found ||= value === current;
    options.push(`<option value='${escapeHtml(value)}' ${value === current ? "selected" : ""}>${escapeHtml(font.name)}</option>`);
  }
  if (!found) {
    const [file, face] = JSON.parse(current);
    options.push(`<option value='${escapeHtml(current)}' selected>${escapeHtml(`${String(file).split("/").at(-1)} (${face})`)}</option>`);
  }
  return `<select class="font" id="${id}">${options.join("")}</select>`;
}

// The whole look as it is on the page becomes a user design that any song can name; the page then offers to use it.
async function saveAsDesign(overwrite = false, name = null) {
  // Suggest the current name only when it is a user design: built-in names and design files cannot be saved over.
  const current = state.design.name;
  const suggested = state.design.builtins.includes(current) || current.endsWith(".toml") ? "" : current;
  name ??= prompt(t("design.save_as_prompt"), suggested);
  if (!name?.trim()) return;
  name = name.trim();
  try {
    const result = await (await api("/api/design/save-as", { name, design: designPayload(), overwrite })).json();
    state.design.bases[result.name] = result.base;
    setStatus(t("design.saved_as", { name: result.name }));
    if (confirm(t("design.use_now", { name: result.name }))) {
      state.design.name = result.name;
      state.design.overrides = {};
      designChanged(true);
    } else showDesign();
  } catch (error) {
    if (error.code === "output_exists" && !overwrite) {
      if (confirm(t("design.replace", { name }))) return saveAsDesign(true, name);
    } else showError(error);
  }
}

async function showDesignFolder() {
  try {
    await api("/api/design/folder", {});
  } catch (error) {
    showError(error);
  }
}

function onDesignInput(event) {
  const row = event.target.closest(".field");
  if (!row) return;
  const path = row.dataset.path;
  const type = row.dataset.type;
  const target = event.target;
  if (type === "range") {
    const number = Number(target.value);
    if (Number.isNaN(number)) return;
    for (const input of row.querySelectorAll("input")) if (input !== target) input.value = number;
    if (row.hasAttribute("data-lazy")) return;
    setDesignValue(path, number);
    designChanged(false);
  } else if (type === "colors") {
    const colors = [...(designValue(path) ?? [])];
    colors[Number(target.dataset.index)] = target.value.toUpperCase();
    setDesignValue(path, colors);
    designChanged(false);
  } else if (type === "color") {
    const value = target.value.trim();
    if (!/^#[0-9a-fA-F]{6}$/.test(value)) return;
    for (const input of row.querySelectorAll("input")) if (input !== target) input.value = value.toLowerCase();
    setDesignValue(path, value.toUpperCase());
    designChanged(false);
  }
}

function onDesignChange(event) {
  const row = event.target.closest(".field");
  if (!row) return;
  const path = row.dataset.path;
  const type = row.dataset.type;
  const target = event.target;
  if (type === "range" && row.hasAttribute("data-lazy")) {
    const number = Number(target.value);
    if (Number.isNaN(number)) return;
    setDesignValue(path, number);
    designChanged(false);
    return;
  }
  if (type === "bool") setDesignValue(path, target.checked);
  else if (type === "panel") setBox(path.split(".")[0], target.checked);
  else if (path === "spectrum.preset") {
    const kind = currentPreset().look.kind;
    setDesignValue(path, target.value);
    // Look settings and gradients of a flat preset do not apply to a perspective one, and the other way round.
    if (currentPreset().look.kind !== kind) {
      deletePath(state.design.overrides, "spectrum.look");
      deletePath(state.design.overrides, "spectrum.fill");
    }
  } else if (path === "spectrum.fill.mode") {
    setDesignValue(path, target.value);
    const colors = designValue("spectrum.fill.colors") ?? [];
    if (target.value === "frequency" && colors.length < 2) {
      setDesignValue("spectrum.fill.colors", [hex(designValue("spectrum.foreground")).toUpperCase(), GRADIENT_START]);
    }
  } else if (type === "select") setDesignValue(path, target.value);
  else if (type === "font") {
    deletePath(state.design.overrides, path);
    deletePath(state.design.overrides, `${path}_face`);
    if (target.value) {
      const [file, face] = JSON.parse(target.value);
      setPath(state.design.overrides, path, file);
      if (face !== 0) setPath(state.design.overrides, `${path}_face`, face);
    }
  } else return;
  designChanged(type !== "font");
}

function onDesignReset(event) {
  const colorButton = event.target.closest(".add-color, .remove-color");
  if (colorButton) {
    const path = colorButton.closest(".field").dataset.path;
    const colors = [...(designValue(path) ?? [])];
    if (colorButton.classList.contains("add-color")) colors.push(colors.at(-1) ?? GRADIENT_START);
    else colors.pop();
    setDesignValue(path, colors);
    designChanged(true);
    return;
  }
  const button = event.target.closest(".reset");
  if (!button) return;
  const path = button.closest(".field").dataset.path;
  deletePath(state.design.overrides, path);
  if (path.endsWith(".font")) deletePath(state.design.overrides, `${path}_face`);
  designChanged(true);
}

// --- Drawing -------------------------------------------------------------------------------------------------------

function render() {
  if (!state.song) return;
  const next = nextLine();
  const current = currentLine(now());
  const adjusting = state.mode === "adjust";
  const designing = state.mode === "design";
  $("rows").innerHTML = state.lines
    .map((line, i) => {
      const classes = [
        i === next && !adjusting ? "next" : "",
        i === current ? "current" : "",
        adjusting && (i === state.sel.i || state.multi.has(i)) ? "sel" : "",
        previewStale(i) ? "stale" : "",
      ].join(" ");
      const cell = (field) => {
        const pick = adjusting && i === state.sel.i && state.sel.field === field ? "pick" : "";
        const bad = isBad(i, field) ? "bad" : "";
        return `<td class="t ${field} ${pick} ${bad}" data-field="${field}">${formatTime(line[field])}</td>`;
      };
      return `<tr class="${classes}" id="row-${i}" data-i="${i}"><td class="n">${i + 1}</td>${cell("start")}${cell("end")}<td class="x">${escapeHtml(line.rows.join(" / "))}</td></tr>`;
    })
    .join("");
  $("help").innerHTML = withKeys(t(adjusting ? "help.adjust" : "help.tap"));
  $("help").hidden = designing;
  $("zoom").hidden = designing;
  $("design").hidden = !designing;
  $("multi-info").textContent = state.multi.size > 1 ? t("adjust.multi", { count: state.multi.size }) : "";
  $("save").classList.toggle("dirty", unsaved());
  $("save").disabled = renderingVideo();
  $("preview-video").disabled = rendering();
  $("preview-video").title = state.preview.url && previewOutdated() ? t("preview_video.stale_lines") : "";
  $("render").disabled = unsaved() || !state.song.timing_exists || rendering();
  $("render").title = unsaved() || !state.song.timing_exists ? t("render.unsaved") : "";
  $("mode-tap").classList.toggle("on", state.mode === "tap");
  $("mode-adjust").classList.toggle("on", adjusting);
  $("mode-design").classList.toggle("on", designing);
  $("adjust").hidden = !adjusting;
  $("play").textContent = t(audio.paused ? "play.play" : "play.pause");
  draw();
}

function scrollToRow(i) {
  $(`row-${i}`)?.scrollIntoView({ block: "nearest" });
}

function sizeCanvas(canvas) {
  const rect = canvas.getBoundingClientRect();
  const ratio = devicePixelRatio || 1;
  if (canvas.width !== Math.round(rect.width * ratio)) {
    canvas.width = Math.round(rect.width * ratio);
    canvas.height = Math.round(rect.height * ratio);
    if (canvas.id === "overview" && state.wave) state.wave.peaks = null;
  }
  return { w: canvas.width, h: canvas.height, ratio };
}

function peaks(from, to, width) {
  const result = new Float32Array(width * 2);
  const data = state.wave.data;
  const first = Math.floor(from * state.wave.rate);
  const step = (Math.floor(to * state.wave.rate) - first) / width;
  for (let x = 0; x < width; x++) {
    let low = 0;
    let high = 0;
    const s0 = Math.max(0, Math.floor(first + x * step));
    const s1 = Math.min(data.length, Math.floor(first + (x + 1) * step));
    const increment = Math.max(1, Math.floor((s1 - s0) / 400));
    for (let k = s0; k < s1; k += increment) {
      if (data[k] < low) low = data[k];
      if (data[k] > high) high = data[k];
    }
    result[2 * x] = low;
    result[2 * x + 1] = high;
  }
  return result;
}

function drawWave(context, values, w, h) {
  context.fillStyle = "#5a6577";
  for (let x = 0; x < w; x++) {
    const y0 = ((1 - values[2 * x + 1]) * h) / 2;
    const y1 = ((1 - values[2 * x]) * h) / 2;
    context.fillRect(x, y0, 1, Math.max(1, y1 - y0));
  }
}

function drawMarkers(context, toX, h, ratio, from, to, labels) {
  state.lines.forEach((line, i) =>
    ["start", "end"].forEach((field) => {
      const time = line[field];
      if (time == null || time < from || time > to) return;
      const x = toX(time);
      const selected = state.mode === "adjust" && i === state.sel.i && state.sel.field === field;
      context.fillStyle = field === "start" ? "#4fd18b" : "#ff9f43";
      context.fillRect(x - (selected ? 1.5 : 0.5) * ratio, 0, (selected ? 3 : 1) * ratio, h);
      if (labels) {
        context.font = `${11 * ratio}px sans-serif`;
        context.fillText(field === "start" ? `${i + 1}` : `${i + 1}]`, x + 3 * ratio, 12 * ratio);
      }
    }),
  );
}

function zoomRange() {
  const time = state.mode === "adjust" && selectedTime() != null && audio.paused ? selectedTime() : audio.currentTime;
  const from = Math.max(0, time - 4);
  return [from, from + 8];
}

function draw() {
  const total = duration();
  let canvas = $("overview");
  let { w, h, ratio } = sizeCanvas(canvas);
  let context = canvas.getContext("2d");
  context.clearRect(0, 0, w, h);
  if (state.wave && total) {
    if (!state.wave.peaks) state.wave.peaks = peaks(0, total, w);
    drawWave(context, state.wave.peaks, w, h);
    drawMarkers(context, (s) => (s / total) * w, h, ratio, 0, total, false);
    const [from, to] = zoomRange();
    context.fillStyle = "#4fa3ff22";
    context.fillRect((from / total) * w, 0, ((to - from) / total) * w, h);
    context.fillStyle = "#fff";
    context.fillRect((audio.currentTime / total) * w, 0, ratio, h);
  }
  canvas = $("zoom");
  ({ w, h, ratio } = sizeCanvas(canvas));
  context = canvas.getContext("2d");
  context.clearRect(0, 0, w, h);
  if (state.wave && total) {
    const [from, to] = zoomRange();
    const toX = (s) => ((s - from) / (to - from)) * w;
    drawWave(context, peaks(from, to, w), w, h);
    context.fillStyle = "#ffffff22";
    for (let s = Math.ceil(from); s <= to; s++) context.fillRect(toX(s), h - 6 * ratio, ratio, 6 * ratio);
    drawMarkers(context, toX, h, ratio, from, to, true);
    context.fillStyle = "#fff";
    context.fillRect(toX(audio.currentTime), 0, ratio, h);
  }
}

// --- Input ---------------------------------------------------------------------------------------------------------

function togglePlay() {
  if (!audio.src) return;
  if (audio.paused) audio.play();
  else audio.pause();
}

function setMode(mode) {
  state.mode = mode;
  if (mode === "design") showDesign();
  render();
}

function moveSelection(step, extend) {
  if (extend && !state.multi.size) state.anchor = state.sel.i;
  const i = Math.max(0, Math.min(state.lines.length - 1, state.sel.i + step));
  state.multi.clear();
  if (extend) for (let j = Math.min(state.anchor, i); j <= Math.max(state.anchor, i); j++) state.multi.add(j);
  select(i, state.sel.field);
  const time = selectedTime();
  if (time != null && audio.paused) {
    audio.currentTime = time;
    requestStill();
  }
}

document.addEventListener("keydown", (event) => {
  if (["INPUT", "SELECT", "TEXTAREA"].includes(event.target.tagName) || !state.song) return;
  const key = event.key;
  const command = event.metaKey || event.ctrlKey;
  if (command && (key === "s" || key === "S")) {
    event.preventDefault();
    if (!renderingVideo()) save();
    return;
  }
  if (key === "p" || key === "P") {
    event.preventDefault();
    togglePlay();
  } else if (key === "Backspace") {
    event.preventDefault();
    undo();
  } else if (state.mode === "design") {
    if (key === " ") {
      event.preventDefault();
      togglePlay();
    }
  } else if (state.mode === "tap") {
    if (key === " ") {
      event.preventDefault();
      if (event.repeat || audio.paused) return;
      markStart();
      render();
    } else if (key === "Enter") {
      event.preventDefault();
      if (!audio.paused) {
        markEnd();
        render();
      }
    }
  } else if (key === " ") {
    event.preventDefault();
    togglePlay();
  } else if (key === "ArrowLeft" || key === "ArrowRight") {
    event.preventDefault();
    shift((key === "ArrowLeft" ? -1 : 1) * (event.shiftKey ? 0.5 : 0.05));
  } else if (key === "ArrowUp" || key === "ArrowDown") {
    event.preventDefault();
    moveSelection(key === "ArrowUp" ? -1 : 1, event.shiftKey);
  } else if (key === "Enter") {
    event.preventDefault();
    setToPlayhead();
  } else if (key === "Tab") {
    event.preventDefault();
    select(state.sel.i, state.sel.field === "start" ? "end" : "start");
  } else if (key === "r" || key === "R") {
    event.preventDefault();
    replay();
  } else if (command && (key === "a" || key === "A")) {
    event.preventDefault();
    selectAll();
  } else if (key === "Escape") {
    event.preventDefault();
    state.multi.clear();
    render();
  }
});

$("rows").addEventListener("click", (event) => {
  const cell = event.target.closest("td");
  if (!cell) return;
  const i = Number(cell.closest("tr").dataset.i);
  if (state.mode !== "adjust") state.mode = "adjust";
  if (event.shiftKey) {
    if (!state.multi.size) state.anchor = state.sel.i;
    state.multi.clear();
    for (let j = Math.min(state.anchor, i); j <= Math.max(state.anchor, i); j++) state.multi.add(j);
    state.sel.i = i;
    render();
    return;
  }
  if (event.metaKey || event.ctrlKey) {
    if (!state.multi.size) state.multi.add(state.sel.i);
    if (state.multi.has(i)) state.multi.delete(i);
    else state.multi.add(i);
    render();
    return;
  }
  state.multi.clear();
  select(i, cell.dataset.field || state.sel.field);
  const time = selectedTime();
  if (time != null && audio.paused) {
    audio.currentTime = time;
    requestStill();
  }
});

$("overview").addEventListener("click", (event) => {
  const total = duration();
  if (!total) return;
  const rect = event.target.getBoundingClientRect();
  audio.currentTime = ((event.clientX - rect.left) / rect.width) * total;
  draw();
  requestStill();
});

$("zoom").addEventListener("mousedown", (event) => {
  if (!state.wave) return;
  const rect = event.target.getBoundingClientRect();
  const [from, to] = zoomRange();
  const time = from + ((event.clientX - rect.left) / rect.width) * (to - from);
  const tolerance = (6 / rect.width) * (to - from);
  let best = null;
  state.lines.forEach((line, i) =>
    ["start", "end"].forEach((field) => {
      const distance = Math.abs((line[field] ?? Infinity) - time);
      if (distance < tolerance && (!best || distance < best.distance)) best = { i, field, distance };
    }),
  );
  if (best) {
    state.mode = "adjust";
    state.sel = { i: best.i, field: best.field };
    state.drag = { from, to, rect, prev: state.lines[best.i][best.field] };
    audio.pause();
  } else {
    audio.currentTime = time;
    requestStill();
  }
  render();
});

window.addEventListener("mousemove", (event) => {
  const drag = state.drag;
  if (!drag) return;
  const time = drag.from + ((event.clientX - drag.rect.left) / drag.rect.width) * (drag.to - drag.from);
  state.lines[state.sel.i][state.sel.field] = Math.round(Math.max(0, time) * 100) / 100;
  render();
});

window.addEventListener("mouseup", () => {
  const drag = state.drag;
  if (!drag) return;
  state.undo.push({ i: state.sel.i, field: state.sel.field, prev: drag.prev, group: ++state.group });
  state.dirty = true;
  state.drag = null;
  audio.currentTime = state.lines[state.sel.i][state.sel.field];
  changed();
});

window.addEventListener("beforeunload", (event) => {
  if (unsaved()) event.preventDefault();
});

window.addEventListener("resize", draw);

// --- Start ---------------------------------------------------------------------------------------------------------

let lastCurrent = -2;
function tick() {
  $("time").textContent = `${formatTime(audio.currentTime)} / ${formatTime(duration())}`;
  if (state.song) updatePreview();
  if (!audio.paused || state.drag) {
    draw();
    const current = currentLine(now());
    if (current !== lastCurrent) {
      lastCurrent = current;
      render();
      if (state.mode === "tap") scrollToRow(Math.max(0, nextLine()));
    }
  }
  requestAnimationFrame(tick);
}

async function start() {
  const params = new URLSearchParams(location.search);
  if (params.has("token")) {
    sessionStorage.setItem("token", params.get("token"));
    history.replaceState(null, "", "/");
  }
  state.token = sessionStorage.getItem("token");
  const remembered = stored("language");
  await setLanguage(remembered in LANGUAGES ? remembered : browserLanguage());
  $("language").replaceChildren(...Object.entries(LANGUAGES).map(([code, name]) => new Option(name, code)));
  $("language").value = state.language;
  $("language").addEventListener("change", () => {
    store("language", $("language").value);
    $("language").blur();
    setLanguage($("language").value).catch(showError);
  });
  $("offset").value = stored("offset") ?? "0";
  $("offset").addEventListener("change", () => {
    store("offset", $("offset").value);
    $("offset").blur();
  });
  // Buttons give the focus back, so Space and Enter always tap instead of pressing the last button again.
  document.addEventListener("click", (event) => event.target.closest("button")?.blur());
  $("play").addEventListener("click", togglePlay);
  $("mode-tap").addEventListener("click", () => setMode("tap"));
  $("mode-adjust").addEventListener("click", () => setMode("adjust"));
  $("mode-design").addEventListener("click", () => setMode("design"));
  $("design-base").addEventListener("change", () => {
    state.design.name = $("design-base").value;
    designChanged(true);
  });
  $("save").addEventListener("click", save);
  $("render").addEventListener("click", () => startRender());
  $("preview-video").addEventListener("click", startPreview);
  $("render-cancel").addEventListener("click", cancelRender);
  $("render-reveal").addEventListener("click", revealRender);
  $("render-close").addEventListener("click", () => ($("render-bar").hidden = true));
  $("replay").addEventListener("click", replay);
  $("set-time").addEventListener("click", setToPlayhead);
  $("clear-time").addEventListener("click", clearTime);
  $("select-all").addEventListener("click", selectAll);
  $("error-close").addEventListener("click", () => ($("error").hidden = true));
  $("design-save-as").addEventListener("click", () => saveAsDesign());
  $("design-folder").addEventListener("click", showDesignFolder);
  $("design-fields").addEventListener("input", onDesignInput);
  $("design-fields").addEventListener("change", onDesignChange);
  $("design-fields").addEventListener("click", onDesignReset);
  for (const button of document.querySelectorAll("#adjust [data-shift]")) {
    button.addEventListener("click", () => shift(Number(button.dataset.shift)));
  }
  audio.addEventListener("play", render);
  audio.addEventListener("pause", () => {
    video.pause();
    render();
    requestStill();
  });
  audio.addEventListener("seeked", () => {
    if (audio.paused) requestStill();
  });
  requestAnimationFrame(tick);
  try {
    await loadSong();
    requestStill();
    showRender(await (await api("/api/render")).json());
    if (rendering()) pollRender();
    render();
  } catch (error) {
    showError(error);
  }
}

start();
