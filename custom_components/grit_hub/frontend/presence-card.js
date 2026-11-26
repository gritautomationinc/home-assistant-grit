/* GRIT Presence dashboard card. The Hub remains the source of radar settings. */
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[char]);
const emptyZone = () => ({ x1: 0, y1: 0, x2: 0, y2: 0 });
const isEmpty = (zone) => !zone || ["x1", "y1", "x2", "y2"].every((key) => zone[key] === 0);
const clamp = (value, low, high) => Math.max(low, Math.min(high, value));

class GritPresenceCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._zones = Array.from({ length: 4 }, emptyZone);
    this._selected = 0;
    this._live = false;
    this._busy = false;
    this._snapshot = null;
    this._updates = null;
    this._message = "";
    this._draw = null;
  }

  setConfig(config) {
    if (!config || typeof config.entity !== "string" || !config.entity.startsWith("binary_sensor.")) {
      throw new Error("GRIT Presence card needs an Occupied binary_sensor entity");
    }
    if (this._config?.entity !== config.entity) {
      if (this._live) this._setLive(false);
      this._loaded = false;
      this._snapshot = null;
    }
    this._config = config;
    this._loadIfReady();
  }

  set hass(hass) {
    this._hass = hass;
    this._loadIfReady();
    this._updateStatus();
  }

  getCardSize() { return 8; }

  connectedCallback() { this._loadIfReady(); }

  disconnectedCallback() {
    clearInterval(this._pollTimer);
    clearInterval(this._keepaliveTimer);
    clearInterval(this._updateTimer);
    if (this._live) this._setLive(false);
    this._loaded = false;
  }

  _context() {
    const state = this._hass?.states?.[this._config?.entity];
    const entryId = state?.attributes?.entry_id;
    const deviceId = state?.attributes?.device_id;
    if (typeof entryId !== "string" || typeof deviceId !== "string") return null;
    return { entryId, deviceId };
  }

  _path(action = "") {
    const { entryId, deviceId } = this._context();
    return `grit_hub/presence/${encodeURIComponent(entryId)}/${encodeURIComponent(deviceId)}${action ? `/${action}` : ""}`;
  }

  _loadIfReady() {
    if (!this.isConnected || !this._hass || !this._config || this._loaded) return;
    if (!this._context()) {
      this.shadowRoot.innerHTML = '<ha-card><div style="padding:20px">Select a GRIT Presence Occupied entity.</div></ha-card>';
      return;
    }
    this._loaded = true;
    this._load().catch((error) => this._showError(error));
  }

  async _load() {
    const snapshot = await this._hass.callApi("GET", this._path());
    this._snapshot = snapshot;
    this._zones = Array.from({ length: 4 }, (_, index) => snapshot.zones?.[index] || emptyZone());
    this._render();
    await this._loadUpdates();
  }

  async _loadUpdates() {
    try {
      this._updates = await this._hass.callApi("GET", this._path("updates"));
      this._renderFirmware();
      clearInterval(this._updateTimer);
      if (this._updates?.running) {
        this._updateTimer = setInterval(() => this._loadUpdates(), 10_000);
      }
    } catch (error) {
      this._updates = null;
      this._renderFirmware();
    }
  }

  _showError(error) {
    this._message = error?.message || "The Presence request failed. Refresh this card and try again.";
    this._renderMessage();
  }

  _admin() { return this._hass?.user?.is_admin === true; }

  _render() {
    const snapshot = this._snapshot;
    if (!snapshot) return;
    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; color:var(--primary-text-color); }
        ha-card { display:block; overflow:hidden; border-radius:var(--ha-card-border-radius, 12px); background:var(--card-background-color, #fff); box-shadow:var(--ha-card-box-shadow, 0 2px 10px #00000014); }
        .head { padding:22px 24px 16px; display:flex; justify-content:space-between; gap:18px; align-items:flex-start; border-bottom:1px solid var(--divider-color); }
        h2 { margin:0; font-size:1.35rem; line-height:1.25; font-weight:700; letter-spacing:-.02em; }
        .subtitle { margin:6px 0 0; color:var(--secondary-text-color); font-size:.9rem; }
        .badge { display:inline-flex; align-items:center; gap:7px; border-radius:999px; padding:7px 11px; font-size:.78rem; font-weight:700; white-space:nowrap; background:var(--secondary-background-color); }
        .badge::before { content:""; width:8px; height:8px; border-radius:50%; background:var(--secondary-text-color); }
        .badge.occupied { background:#dff3e6; color:#145c33; }
        .badge.occupied::before { background:#198754; }
        .badge.clear { background:#f0f3f2; color:#384c43; }
        .badge.clear::before { background:#718b7c; }
        .body { display:grid; grid-template-columns:minmax(0, 1.5fr) minmax(235px, 1fr); gap:22px; padding:22px 24px; }
        .map-wrap { min-width:0; }
        .section-title { font-size:.86rem; font-weight:700; margin:0 0 10px; }
        .map { display:block; width:100%; aspect-ratio:600 / 620; border:1px solid var(--divider-color); border-radius:8px; background:var(--secondary-background-color); touch-action:none; cursor:crosshair; }
        .map-note { margin:8px 0 0; color:var(--secondary-text-color); font-size:.78rem; line-height:1.45; }
        .side { min-width:0; }
        .zone-list { display:grid; gap:7px; }
        .zone { display:flex; justify-content:space-between; gap:8px; align-items:center; width:100%; padding:10px 12px; text-align:left; color:var(--primary-text-color); background:var(--card-background-color); border:1px solid var(--divider-color); border-radius:8px; cursor:pointer; font:inherit; }
        .zone.selected { border-color:#f45116; box-shadow:0 0 0 1px #f45116 inset; }
        .zone:focus-visible, button:focus-visible, input:focus-visible { outline:2px solid #f45116; outline-offset:2px; }
        .zone small { color:var(--secondary-text-color); }
        .editor { margin-top:17px; padding-top:16px; border-top:1px solid var(--divider-color); }
        .fields { display:grid; grid-template-columns:1fr 1fr; gap:9px; }
        label { display:grid; gap:4px; color:var(--secondary-text-color); font-size:.78rem; font-weight:600; }
        input, select { width:100%; box-sizing:border-box; padding:8px; border-radius:7px; border:1px solid var(--divider-color); background:var(--card-background-color); color:var(--primary-text-color); font:inherit; }
        .actions { display:flex; flex-wrap:wrap; gap:8px; margin-top:13px; }
        button.action { border:1px solid var(--divider-color); border-radius:7px; background:var(--card-background-color); color:var(--primary-text-color); padding:9px 12px; font:inherit; font-size:.84rem; font-weight:600; cursor:pointer; }
        button.action.primary { background:#f45116; border-color:#f45116; color:white; }
        button.action:disabled { opacity:.45; cursor:not-allowed; }
        .firmware { border-top:1px solid var(--divider-color); padding:17px 24px 21px; display:flex; justify-content:space-between; align-items:center; gap:16px; flex-wrap:wrap; }
        .firmware p { margin:4px 0 0; color:var(--secondary-text-color); font-size:.82rem; }
        .message { padding:0 24px 17px; color:var(--error-color, #a02724); font-size:.84rem; min-height:1em; }
        @media (max-width:700px) { .head { padding:18px; } .body { grid-template-columns:1fr; padding:18px; } .firmware { padding:17px 18px; } .message { padding:0 18px 14px; } }
      </style>
      <ha-card>
        <div class="head"><div><h2>${escapeHtml(snapshot.name)}</h2><p class="subtitle">GRIT Presence${snapshot.sensorMask & 1 ? " · LD2450 coverage" : " · occupancy"}</p></div><span class="badge" id="occupancy"></span></div>
        <div class="body">
          <div class="map-wrap"><h3 class="section-title">Coverage map</h3><svg class="map" id="map" viewBox="0 0 600 620" role="img" aria-label="Top-down Presence radar coverage and zones"></svg><p class="map-note">Sensor at the bottom. Each grid line is 1 m; zones are green. Drag to draw or move a zone; use coordinates to resize it.</p><div class="actions"><button class="action" id="live" ${this._admin() ? "" : "disabled"}>Start live radar</button></div></div>
          <div class="side"><h3 class="section-title">Zones</h3><div class="zone-list" id="zones"></div><div class="editor" id="editor"></div><div class="editor" id="settings"></div></div>
        </div>
        <div class="firmware" id="firmware"></div><div class="message" id="message" role="status"></div>
      </ha-card>`;
    this.shadowRoot.getElementById("live").addEventListener("click", () => this._setLive(!this._live));
    const map = this.shadowRoot.getElementById("map");
    map.addEventListener("pointerdown", (event) => this._pointerDown(event));
    map.addEventListener("pointermove", (event) => this._pointerMove(event));
    map.addEventListener("pointerup", (event) => this._pointerUp(event));
    map.addEventListener("pointercancel", () => { this._draw = null; this._renderMap(); });
    this._updateStatus(); this._renderMap(); this._renderZones(); this._renderSettings(); this._renderFirmware(); this._renderMessage();
  }

  _updateStatus() {
    const badge = this.shadowRoot.getElementById("occupancy");
    if (!badge) return;
    const state = this._hass?.states?.[this._config?.entity]?.state;
    const occupied = state === "on" ? true : state === "off" ? false : null;
    const online = this._snapshot?.online;
    badge.className = `badge ${online === false || occupied == null ? "" : occupied ? "occupied" : "clear"}`;
    badge.textContent = online === false || occupied == null ? "Unavailable" : occupied ? "Occupied" : "Unoccupied";
  }

  _renderMessage() { const el = this.shadowRoot.getElementById("message"); if (el) el.textContent = this._message; }

  _renderZones() {
    const list = this.shadowRoot.getElementById("zones");
    if (!list) return;
    list.innerHTML = this._zones.map((zone, index) => `<button class="zone ${index === this._selected ? "selected" : ""}" data-zone="${index}"><span>Zone ${index + 1}</span><small>${isEmpty(zone) ? "Empty" : this._snapshot?.zoneOccupied?.[`z${index + 1}`] ? "Occupied" : "Configured"}</small></button>`).join("");
    list.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => { this._selected = Number(button.dataset.zone); this._renderZones(); this._renderEditor(); this._renderMap(); }));
    this._renderEditor();
  }

  _renderEditor() {
    const el = this.shadowRoot.getElementById("editor");
    if (!el) return;
    const zone = this._zones[this._selected];
    el.innerHTML = `<h3 class="section-title">Zone ${this._selected + 1} · millimeters</h3><div class="fields">${["x1", "y1", "x2", "y2"].map((field) => `<label>${field.toUpperCase()}<input type="number" step="100" min="${field[0] === "x" ? -3000 : 0}" max="${field[0] === "x" ? 3000 : 6000}" data-field="${field}" value="${zone[field]}" ${this._admin() ? "" : "disabled"}></label>`).join("")}</div><div class="actions"><button class="action primary" id="save-zones" ${this._admin() && !this._busy ? "" : "disabled"}>Save zones</button><button class="action" id="clear-zone" ${this._admin() && !this._busy ? "" : "disabled"}>Clear zone</button></div>`;
    el.querySelectorAll("input").forEach((input) => input.addEventListener("change", () => {
      const number = Number(input.value);
      const field = input.dataset.field;
      if (!Number.isInteger(number) || number < (field[0] === "x" ? -3000 : 0) || number > (field[0] === "x" ? 3000 : 6000)) {
        input.setCustomValidity("Enter a valid millimeter position"); input.reportValidity(); return;
      }
      input.setCustomValidity(""); this._zones[this._selected][field] = number; this._renderMap();
    }));
    el.querySelector("#save-zones").addEventListener("click", () => this._saveZones());
    el.querySelector("#clear-zone").addEventListener("click", () => { this._zones[this._selected] = emptyZone(); this._renderEditor(); this._renderMap(); this._renderZones(); });
  }

  _renderSettings() {
    const el = this.shadowRoot.getElementById("settings");
    if (!el || !this._snapshot) return;
    const behavior = this._snapshot.presenceBehavior;
    const options = ["Automation Control", "Occupancy Required", "Vacancy Required"];
    el.innerHTML = `<h3 class="section-title">Presence settings</h3><label>Behavior<select id="behavior" ${this._admin() ? "" : "disabled"}>${options.map((label, index) => `<option value="${index}" ${index === behavior ? "selected" : ""}>${label}</option>`).join("")}</select></label><div class="fields" style="margin-top:10px"><label>Activation delay · seconds<input id="delay-on" type="number" min="0" max="600" step="0.1" value="${(this._snapshot.triggerOnDebounceMs ?? 250) / 1000}" ${this._admin() ? "" : "disabled"}></label><label>Deactivation delay · seconds<input id="delay-off" type="number" min="0" max="600" step="0.1" value="${(this._snapshot.triggerOffDebounceMs ?? 1500) / 1000}" ${this._admin() ? "" : "disabled"}></label></div><p class="map-note">Changing behavior may unlink connected devices. Check those connections in the GRIT app afterward.</p><div class="actions"><button class="action" id="save-settings" ${this._admin() && !this._busy ? "" : "disabled"}>Save settings</button></div>`;
    el.querySelector("#save-settings").addEventListener("click", () => this._saveSettings());
  }

  async _saveSettings() {
    if (this._busy) return;
    const el = this.shadowRoot.getElementById("settings");
    const on = Number(el.querySelector("#delay-on").value);
    const off = Number(el.querySelector("#delay-off").value);
    if (![on, off].every((value) => Number.isFinite(value) && value >= 0 && value <= 600 && Number.isInteger(value * 1000))) {
      this._message = "Enter delays from 0 to 600 seconds."; this._renderMessage(); return;
    }
    const behavior = Number(el.querySelector("#behavior").value);
    this._busy = true; this._renderSettings();
    try {
      await this._hass.callApi("PUT", this._path("settings"), {
        presenceBehavior: behavior,
        triggerOnDebounceMs: Math.round(on * 1000),
        triggerOffDebounceMs: Math.round(off * 1000),
      });
      this._message = "Presence settings saved to the GRIT Hub.";
      await this._refresh(); this._renderSettings();
    } catch (error) { this._showError(error); }
    finally { this._busy = false; this._renderSettings(); this._renderMessage(); }
  }

  _renderMap() {
    const svg = this.shadowRoot.getElementById("map");
    if (!svg) return;
    const x = (mm) => 300 + mm / 10;
    const y = (mm) => 600 - mm / 10;
    const grid = Array.from({ length: 7 }, (_, index) => {
      const p = index * 100;
      return `<line x1="${p}" y1="0" x2="${p}" y2="600" stroke="var(--divider-color)"/><line x1="0" y1="${p}" x2="600" y2="${p}" stroke="var(--divider-color)"/>`;
    }).join("");
    const zones = this._zones.map((zone, index) => {
      if (isEmpty(zone)) return "";
      const x0 = x(Math.min(zone.x1, zone.x2)); const y0 = y(Math.max(zone.y1, zone.y2));
      const width = Math.abs(zone.x2 - zone.x1) / 10; const height = Math.abs(zone.y2 - zone.y1) / 10;
      return `<rect data-zone="${index}" x="${x0}" y="${y0}" width="${width}" height="${height}" fill="${this._snapshot?.zoneOccupied?.[`z${index + 1}`] ? "#3aa86566" : "#3aa86524"}" stroke="${index === this._selected ? "#f45116" : "#269255"}" stroke-width="3"/><text x="${x0 + 8}" y="${y0 + 19}" fill="var(--primary-text-color)" font-size="15" font-weight="700" pointer-events="none">${index + 1}</text>`;
    }).join("");
    const targets = this._live ? (this._snapshot?.targets || []).map((target) => `<circle cx="${x(target.x)}" cy="${y(target.y)}" r="8" fill="#e54840" stroke="white" stroke-width="3"/>`).join("") : "";
    const preview = this._draw?.mode === "new" ? `<rect x="${Math.min(this._draw.start.x, this._draw.end.x)}" y="${Math.min(this._draw.start.y, this._draw.end.y)}" width="${Math.abs(this._draw.end.x - this._draw.start.x)}" height="${Math.abs(this._draw.end.y - this._draw.start.y)}" fill="#f4511622" stroke="#f45116" stroke-width="2" stroke-dasharray="7 5"/>` : "";
    svg.innerHTML = `<rect x="0" y="0" width="600" height="600" fill="var(--card-background-color)"/>${grid}<path d="M300 600 L0 427 L0 600 Z M300 600 L600 427 L600 600 Z" fill="var(--secondary-background-color)"/><path d="M300 600 L0 427 M300 600 L600 427" stroke="var(--secondary-text-color)" stroke-dasharray="6 6" fill="none"/>${zones}${targets}${preview}<path d="M288 600 L300 578 L312 600 Z" fill="var(--primary-text-color)"/><text x="300" y="616" text-anchor="middle" fill="var(--secondary-text-color)" font-size="13">Sensor</text>`;
  }

  _point(event) {
    const svg = this.shadowRoot.getElementById("map");
    const rect = svg.getBoundingClientRect();
    return { x: clamp(Math.round((event.clientX - rect.left) / rect.width * 600), 0, 600), y: clamp(Math.round((event.clientY - rect.top) / rect.height * 620), 0, 600) };
  }
  _pointerDown(event) {
    if (!this._admin()) return;
    const existing = event.target.dataset?.zone;
    if (existing != null) {
      const slot = Number(existing);
      this._draw = { mode: "move", slot, start: this._point(event), original: { ...this._zones[slot] } };
      this._selected = slot;
      event.currentTarget.setPointerCapture(event.pointerId);
      return;
    }
    const slot = this._zones.findIndex(isEmpty);
    if (slot < 0) { this._message = "Clear a zone before drawing another."; this._renderMessage(); return; }
    const start = this._point(event);
    this._draw = { mode: "new", slot, start, end: start };
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  _pointerMove(event) {
    if (!this._draw) return;
    const point = this._point(event);
    if (this._draw.mode === "move") {
      const original = this._draw.original;
      let dx = (point.x - this._draw.start.x) * 10;
      let dy = (this._draw.start.y - point.y) * 10;
      dx = clamp(dx, -3000 - Math.min(original.x1, original.x2), 3000 - Math.max(original.x1, original.x2));
      dy = clamp(dy, -Math.min(original.y1, original.y2), 6000 - Math.max(original.y1, original.y2));
      this._zones[this._draw.slot] = { x1: original.x1 + dx, y1: original.y1 + dy, x2: original.x2 + dx, y2: original.y2 + dy };
    } else this._draw.end = point;
    this._renderMap();
  }
  _pointerUp(event) {
    if (!this._draw) return;
    if (this._draw.mode === "move") { this._draw = null; this._renderZones(); this._renderMap(); return; }
    this._draw.end = this._point(event);
    const { start, end, slot } = this._draw;
    this._draw = null;
    if (Math.abs(start.x - end.x) < 20 || Math.abs(start.y - end.y) < 20) { this._renderMap(); return; }
    this._zones[slot] = { x1: (start.x - 300) * 10, y1: (600 - start.y) * 10, x2: (end.x - 300) * 10, y2: (600 - end.y) * 10 };
    this._selected = slot; this._renderZones(); this._renderMap();
  }

  async _saveZones() {
    if (this._busy) return;
    const active = this._zones.filter((zone) => !isEmpty(zone)).map((zone) => ({
      left: Math.min(zone.x1, zone.x2), right: Math.max(zone.x1, zone.x2),
      bottom: Math.min(zone.y1, zone.y2), top: Math.max(zone.y1, zone.y2),
    }));
    if (active.some((zone) => zone.right - zone.left < 200 || zone.top - zone.bottom < 200)) {
      this._message = "Each zone must be at least 200 mm wide and deep."; this._renderMessage(); return;
    }
    if (active.some((zone, index) => active.slice(index + 1).some((other) =>
      zone.left < other.right && zone.right > other.left && zone.bottom < other.top && zone.top > other.bottom))) {
      this._message = "Zones cannot overlap."; this._renderMessage(); return;
    }
    this._busy = true; this._renderEditor();
    try {
      await this._hass.callApi("PUT", this._path("zones"), { zones: this._zones });
      this._message = "Zones saved to the GRIT Hub.";
      await this._refresh();
    } catch (error) { this._showError(error); }
    finally { this._busy = false; this._renderEditor(); this._renderMessage(); }
  }

  async _setLive(active) {
    if (!this._context()) return;
    clearInterval(this._pollTimer); clearInterval(this._keepaliveTimer);
    (this._stopTimers || []).forEach(clearTimeout); this._stopTimers = [];
    const path = this._path("radar-stream");
    try {
      await this._hass.callApi("POST", path, { active });
      this._live = active;
      const button = this.shadowRoot.getElementById("live");
      if (button) button.textContent = active ? "Stop live radar" : "Start live radar";
      if (active) {
        this._pollTimer = setInterval(() => this._refresh(), 300);
        this._keepaliveTimer = setInterval(() => this._hass.callApi("POST", path, { active: true }).catch((error) => this._showError(error)), 8000);
      } else {
        this._snapshot.targets = []; this._renderMap();
        this._stopTimers = [400, 900].map((delay) => setTimeout(() =>
          this._hass.callApi("POST", path, { active: false }).catch(() => {}), delay));
      }
    } catch (error) { this._showError(error); }
  }

  async _refresh() {
    if (this._polling) return;
    this._polling = true;
    try {
      const snapshot = await this._hass.callApi("GET", this._path());
      const oldZones = JSON.stringify(this._snapshot?.zoneOccupied || {});
      this._snapshot = snapshot;
      this._updateStatus(); this._renderMap();
      if (JSON.stringify(snapshot.zoneOccupied || {}) !== oldZones) {
        const list = this.shadowRoot.getElementById("zones");
        list?.querySelectorAll("button").forEach((button, index) => {
          const note = button.querySelector("small");
          if (note) note.textContent = isEmpty(this._zones[index]) ? "Empty" : snapshot.zoneOccupied?.[`z${index + 1}`] ? "Occupied" : "Configured";
        });
      }
    } catch (error) { this._showError(error); }
    finally { this._polling = false; }
  }

  _renderFirmware() {
    const el = this.shadowRoot.getElementById("firmware");
    if (!el) return;
    const count = this._updates?.count;
    const running = this._updates?.running;
    const text = this._updates == null ? "Update status unavailable" : running ? `Updating Presence fleet${this._updates.percentComplete == null ? "" : ` · ${Math.round(this._updates.percentComplete)}%`}` : count ? `${count} Presence device${count === 1 ? "" : "s"} eligible` : "Presence firmware up to date";
    el.innerHTML = `<div><strong>Presence firmware</strong><p>${escapeHtml(text)}. This updates eligible Presence devices across the Hub.</p></div><button class="action primary" id="install" ${this._admin() && count > 0 && !running && !this._busy ? "" : "disabled"}>Update Presence fleet</button>`;
    el.querySelector("#install").addEventListener("click", async () => {
      if (this._busy) return;
      this._busy = true; this._renderFirmware();
      try {
        await this._hass.callApi("POST", this._path("install-update"), {});
        this._message = "Presence firmware update requested on the GRIT Hub.";
        await this._loadUpdates();
      } catch (error) { this._showError(error); }
      finally { this._busy = false; this._renderFirmware(); this._renderMessage(); }
    });
  }
}

if (!customElements.get("grit-presence-card")) customElements.define("grit-presence-card", GritPresenceCard);
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "grit-presence-card")) {
  window.customCards.push({ type: "grit-presence-card", name: "GRIT Presence", description: "GRIT Presence occupancy, radar zones, and firmware updates" });
}
