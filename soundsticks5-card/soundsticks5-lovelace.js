/**
 * SoundSticks 5 — Lovelace card in the official Harman Kardon design language.
 *
 * 独立自定义卡片：不修改 soundsticks5 集成，HACS 升级不覆盖。
 * 通过稳定 unique_id（soundsticks5_*）自动发现实体，与集成内置卡片同一套实体。
 *
 * 设计语言来源：HK One App（harman / kardon）
 *   浅灰底 + 纯白大圆角卡 + 超大留白 + 细字重无衬线
 *   harman / kardon 品牌字 · SOUNDSTICKS 5 小字全大写
 *   柔和主题色块 · 整条渐变色滑块 · 分段胶囊速度钮 · 黑色 iOS toggle
 */

const THEMES = {
  ocean:     { zh: "碧波荡漾", en: "Ocean",     g: ["#06DFBE", "#37ACFF", "#5B32FF"], led: "#2fd0b6" },
  aurora:    { zh: "极光幻境", en: "Aurora",    g: ["#42EA66", "#0E8ED9"],            led: "#3fd387" },
  blossom:   { zh: "落英缤纷", en: "Blossom",   g: ["#D786C5", "#8C53E8"],            led: "#c887d3" },
  sunrise:   { zh: "旭日东升", en: "Sunrise",   g: ["#FF5359", "#F7A86B", "#EBCC6C", "#E1ED6E"], led: "#ff8a6d" },
  fireplace: { zh: "雪夜炉火", en: "Fireplace", g: ["#E7BA5A", "#F64302"],            led: "#f47c2c" },
  static:    { zh: "静谧时光", en: "Static",    g: ["#FFE9C9", "#F5C96A", "#8FEA7F", "#66B9F2", "#D36BE5", "#F075A2"], led: "#efd47f" },
};

const ENTITY_KEYS = [
  "media_player", "lighting", "theme", "color", "color_reset", "brightness", "speed",
  "eq_125", "eq_250", "eq_500", "eq_1000", "eq_2000", "eq_4000", "eq_8000", "eq_reset",
  "feedback_tone", "auto_off", "auto_off_remaining", "operating_state", "preset",
  "refresh_state", "release_ble", "ble_connection",
];

const EQ_BANDS = [125, 250, 500, 1000, 2000, 4000, 8000];

class SoundSticks5LovelaceCard extends HTMLElement {
  static getStubConfig() { return {}; }
  static getConfigElement() { return document.createElement("soundsticks5-lovelace-editor"); }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._entities = {};
    this._discovering = false;
    this._didDiscover = false;
    this._timers = new Map();
    this._draft = new Map();
    this._dragging = new Set();
  }

  setConfig(config) {
    this._config = config || {};
    this._entities = {};
    this._didDiscover = false;
    for (const key of ENTITY_KEYS) if (this._config[key]) this._entities[key] = this._config[key];
    if (this._hass && !this._discovering) void this._discoverEntities();
    this._safeRender();
  }

  set hass(value) {
    this._hass = value;
    if (!this._discovering && !this._didDiscover) this._discoverEntities();
    if (!this._dragging.size) this._safeRender();
  }

  getCardSize() { return 17; }

  /* ---------- entity plumbing (same stable unique_id scheme as the integration) ---------- */

  async _discoverEntities() {
    this._discovering = true;
    try {
      const registry = await this._hass.callWS({ type: "config/entity_registry/list" });
      this._registry = registry;
      for (const item of registry) {
        if (item.platform !== "soundsticks5" || !item.unique_id?.startsWith("soundsticks5_")) continue;
        const key = item.unique_id.slice("soundsticks5_".length);
        if (!this._entities[key]) this._entities[key] = item.entity_id;
      }
    } catch (e) { /* discovery stays manual via YAML */ }
    finally {
      this._discovering = false;
      this._didDiscover = true;
      this._safeRender();
    }
  }

  _state(key) {
    const entityId = this._entities[key];
    return entityId ? this._hass?.states?.[entityId] : undefined;
  }

  _zh() { return (this._hass?.language || "").toLowerCase().startsWith("zh"); }
  _t(zh, en) { return this._zh() ? zh : en; }
  _escape(v) { return String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]); }

  _numeric(key, fallback = null) {
    if (this._draft.has(key)) return this._draft.get(key);
    const raw = this._state(key)?.state;
    if (raw === undefined || raw === "unknown" || raw === "unavailable" || raw === "") return fallback;
    const n = Number(raw);
    return Number.isFinite(n) ? n : fallback;
  }

  _call(key, service, data = {}) {
    const entityId = this._entities[key];
    if (!entityId) return Promise.reject(new Error(`Missing entity: ${key}`));
    return this._hass.callService(entityId.split(".")[0], service, { entity_id: entityId, ...data });
  }

  _domainCall(service, data = {}) { return this._hass.callService("soundsticks5", service, data); }

  _transport() {
    const bleId = this._entities.media_player;
    const mode = this._config.playback_mode || "auto";
    let externalId = this._config.playback_entity;
    // Auto-discovery requires the same HA device, never a similar display name.
    if (!externalId && mode === "auto") {
      const device = this._registry?.find((item) => item.entity_id === bleId)?.device_id;
      const candidates = device ? this._registry.filter((item) => item.device_id === device &&
        item.entity_id.startsWith("media_player.") && item.entity_id !== bleId && !item.disabled_by) : [];
      if (candidates.length === 1) externalId = candidates[0].entity_id;
    }
    const external = externalId?.startsWith("media_player.") ? this._hass?.states?.[externalId] : undefined;
    const useExternal = mode === "entity" || (mode === "auto" && ["playing", "paused"].includes(external?.state));
    const id = useExternal ? externalId : bleId;
    const state = useExternal ? external : this._state("media_player");
    return { id, state, external: useExternal, available: !!state && !["unknown", "unavailable"].includes(state.state) };
  }

  _canTransport(target, action) {
    if (!target.available) return false;
    if (!target.external) return true;
    const feature = { previous: 16, next: 32, toggle: target.state.state === "playing" ? 1 : 16384 }[action];
    return !!(Number(target.state.attributes?.supported_features) & feature);
  }

  async _sendTransport(action) {
    const target = this._transport();
    if (!this._canTransport(target, action)) return;
    const service = { previous: "media_previous_track", next: "media_next_track",
      toggle: target.state.state === "playing" ? "media_pause" : "media_play" }[action];
    try {
      await this._hass.callService("media_player", service, { entity_id: target.id });
      this._transportError = "";
    } catch (error) {
      this._transportError = this._t("播放控制失败，请检查所选播放器。", "Playback command failed. Check the selected player.");
    }
    this._safeRender();
  }

  /* ---------- slider draft / debounce ---------- */

  _finishDraft(key) {
    window.setTimeout(() => {
      this._draft.delete(key);
      this._dragging.delete(key);
      this._safeRender();
    }, 450);
  }

  _sendRange(input, final = false) {
    const key = input.dataset.key;
    const value = Number(input.value);
    this._draft.set(key, value);
    input.closest(".range")?.querySelector("output")?.replaceChildren(String(value));
    const old = this._timers.get(key);
    if (old) clearTimeout(old);
    const send = async () => {
      this._timers.delete(key);
      try {
        if (key === "media_player") await this._call(key, "volume_set", { volume_level: value / 100 });
        else await this._call(key, "set_value", { value });
      } finally {
        if (final) this._finishDraft(key);
      }
    };
    if (final) void send();
    else this._timers.set(key, setTimeout(() => void send(), 220));
  }

  /* ---------- product photo (real SoundSticks 5 shot, transparent PNG in /local) ---------- */

  _lightColor(theme) {
    // Approximate the selected position on the App palette, not measured LED RGB.
    const position = Math.max(0, Math.min(100, this._numeric("color", 50))) / 100 * (theme.g.length - 1);
    const index = Math.min(Math.floor(position), theme.g.length - 2);
    const mix = position - index;
    const channels = (hex) => [1, 3, 5].map((offset) => parseInt(hex.slice(offset, offset + 2), 16));
    const start = channels(theme.g[index]);
    const end = channels(theme.g[index + 1]);
    return `rgb(${start.map((value, channel) => Math.round(value + (end[channel] - value) * mix)).join(",")})`;
  }

  _speedWaves(count) {
    if (count < 3) return `<span class="sub" aria-hidden="true">${count === 1 ? "~" : "≈"}</span>`;
    return `<span class="sub triple-wave" aria-hidden="true"><i>~</i><i>~</i><i>~</i></span>`;
  }

  _productImg(ledColor, lightOn) {
    const src = this._config.image || "/local/soundsticks5.png?source=app-original";
    return `<div class="product-wrap">
      <img class="product" src="${this._escape(src)}" alt="SoundSticks 5" draggable="false"
           onerror="this.style.display='none';this.parentElement.classList.add('no-img')">
      ${lightOn ? `<div class="product-glow" style="--led:${ledColor}"></div>` : ""}
    </div>`;
  }

  /* ---------- range row ---------- */

  _safeRender() {
    try {
      this._render();
    } catch (e) {
      console.error('[soundsticks5-lovelace] render failed:', e);
      if (this.shadowRoot) {
        this.shadowRoot.innerHTML = `` + '<ha-card style="padding:18px"><div style="padding:14px 18px;background:#fdeceb;color:#c03b2b;border-radius:14px;font-size:12.5px">' + `卡片渲染出错：${String((e && e.message) || e)}</div></ha-card>`;
      }
    }
  }

  _range(key, label, min = 0, max = 100, cssClass = "") {
    const value = this._numeric(key);
    const disabled = value === null || !this._state(key);
    const shown = value === null ? "—" : value;
    return `<label class="range ${cssClass} ${disabled ? "is-disabled" : ""}"><span>${label}</span><output>${shown}</output><input data-key="${key}" type="range" min="${min}" max="${max}" step="1" value="${value ?? min}" ${disabled ? "disabled" : ""}></label>`;
  }

  /* ---------- main render ---------- */

  _render() {
    if (!this.shadowRoot || !this._hass) return;
    const bleMedia = this._state("media_player");
    const transport = this._transport();
    const media = transport.available ? transport.state : undefined;
    const themeState = this._state("theme")?.state;
    const activeTheme = THEMES[themeState] ? themeState : "ocean";
    const themeInfo = THEMES[activeTheme];
    const ledColor = this._lightColor(themeInfo);
    const lightOn = this._state("lighting")?.state === "on";
    const title = media?.attributes?.media_title || (!transport.available && transport.external ? this._t("播放器不可用", "Player unavailable") : this._t("暂无曲目信息", "Track information unavailable"));
    const artist = media?.attributes?.media_artist || "";
    const mediaVolume = this._draft.has("media_player") ? this._draft.get("media_player") : Math.round((bleMedia?.attributes?.volume_level ?? 0) * 100);
    const feedbackOn = this._state("feedback_tone")?.state === "on";
    const missing = !bleMedia && !this._discovering;
    const operating = this._state("operating_state")?.state || "unknown";
    const playing = media?.state === "playing";
    const speed = this._state("speed")?.state || "medium";
    const autoOff = this._state("auto_off")?.state || "never";
    const presetState = this._state("preset");
    const presetNames = presetState?.attributes?.options || [];
    if (!presetNames.includes(this._selectedPreset)) this._selectedPreset = presetNames.includes(presetState?.state) ? presetState.state : presetNames[0];
    const presetOptions = presetNames.map((n) => `<option value="${this._escape(n)}" ${this._selectedPreset === n ? "selected" : ""}>${this._escape(n)}</option>`).join("");

    const AUTO_LABELS = { never: [this._t("从不", "Never")], "10_minutes": [this._t("10 分钟", "10 minutes")], "1_hour": [this._t("1 小时", "1 hour")], "2_hours": [this._t("2 小时", "2 hours")], "4_hours": [this._t("4 小时", "4 hours")] };

    const themeButtons = Object.entries(THEMES).map(([key, info]) =>
      `<button class="theme ${key === activeTheme ? "active" : ""}" data-theme="${key}" style="--g:${info.g.join(",")}" aria-pressed="${key === activeTheme}"><span>${this._t(info.zh, info.en)}</span></button>`
    ).join("");

    const eq = EQ_BANDS.map((hz) => this._range(`eq_${hz}`, hz >= 1000 ? `${hz / 1000}k` : hz, -12, 12, "eq-range")).join("");

    this.shadowRoot.innerHTML = `
    <style>
      :host{
        display:block;
        container-type:inline-size; container-name:soundsticks;
        --hk-bg:#ececef; --hk-card:#ffffff; --hk-ink:#151517; --hk-soft:#88898d; --hk-faint:#b9bbc0;
        --hk-line:#e8e9ec; --hk-dark:#3c3d41; --hk-accent:${ledColor};
        --hk-font:"SF Pro Display","SF Pro Text","Segoe UI",Roboto,"PingFang SC","Noto Sans SC",system-ui,sans-serif;
        font-family:var(--hk-font); color:var(--hk-ink);
      }
      *{box-sizing:border-box; -webkit-tap-highlight-color:transparent}
      button,input,select{font:inherit; color:inherit}
      button{cursor:pointer; background:none; border:none}
      ha-card{display:block; background:var(--hk-bg); border:none; border-radius:28px; box-shadow:0 1px 2px rgba(18,20,24,.05),0 18px 48px rgba(18,20,24,.08); overflow:hidden; padding:20px 18px 8px}

      .card{background:var(--hk-card); border-radius:22px; padding:24px 24px; margin-bottom:16px; box-shadow:0 1px 1px rgba(18,20,24,.03)}

      /* ---------- hero ---------- */
      .hero{padding:8px 24px 22px; text-align:left}
      .brand{font-size:17px; font-weight:600; letter-spacing:.01em; color:var(--hk-ink); margin-bottom:4px}
      .brand em{font-style:normal; color:var(--hk-faint); font-weight:300; padding:0 2px}
      .brand span.k{color:var(--hk-soft); font-weight:500}
      .model{font-size:11px; letter-spacing:.18em; color:var(--hk-soft); font-weight:600}
      .product-wrap{position:relative; display:flex; justify-content:center; width:min(250px,72%); margin:0 auto; padding:14px 0 6px}
      .product{width:100%; height:auto; display:block; user-select:none; -webkit-user-drag:none}
      .product-glow{position:absolute; left:50%; bottom:23%; width:38%; height:25%; transform:translateX(-50%);
        background:radial-gradient(ellipse at center, var(--led) 0%, transparent 68%);
        filter:blur(10px); opacity:.45; pointer-events:none}
      .product-wrap.no-img{min-height:96px}
      .product-wrap.no-img:after{content:"SOUNDSTICKS 5"; align-self:center; font-size:11px; letter-spacing:.3em; color:var(--hk-faint)}
      .hero-meta{display:flex; align-items:center; justify-content:space-between; margin-top:6px}
      .status{display:inline-flex; align-items:center; gap:8px; font-size:11.5px; color:var(--hk-soft); letter-spacing:.02em}
      .status i{width:7px; height:7px; border-radius:50%; background:#c2c4c9}
      .status.on i{background:var(--hk-accent); box-shadow:0 0 0 3px color-mix(in srgb,var(--hk-accent) 16%,transparent)}
      .hero-actions{display:flex; gap:8px}
      .ghost{width:38px; height:38px; border-radius:50%; display:grid; place-items:center; border:1px solid var(--hk-line); color:var(--hk-soft); transition:all .15s}
      .ghost:hover{color:var(--hk-ink); border-color:var(--hk-faint); background:#f6f6f8}

      /* ---------- playback bar ---------- */
      .player{background:var(--hk-dark); border-radius:22px; padding:20px 24px 24px; margin-bottom:16px; color:#f4f4f6}
      .player .top{display:flex; align-items:center; gap:14px; margin-bottom:16px}
      .player .bt{width:42px; height:42px; border-radius:12px; background:rgba(255,255,255,.08); display:grid; place-items:center; flex:none}
      .player .bt ha-icon{color:#fff; --mdc-icon-size:22px}
      .player .np{flex:1; min-width:0}
      .player .np .t{font-size:14px; font-weight:500; letter-spacing:.01em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis}
      .player .np .a{font-size:11.5px; color:rgba(244,244,246,.55); margin-top:3px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis}
      .transport{display:flex; align-items:center; justify-content:center; gap:20px; margin:2px 0 18px}
      .transport button{width:46px; height:46px; border-radius:50%; display:grid; place-items:center; color:#f4f4f6; transition:background .15s}
      .transport button:disabled{opacity:.3; cursor:default}
      .transport-source{font-size:10px; color:rgba(244,244,246,.55); margin:0 0 12px; overflow-wrap:anywhere}
      .transport button:hover{background:rgba(255,255,255,.09)}
      .transport .main{width:60px; height:60px; background:#fff; color:#2a2b2e; box-shadow:0 8px 20px rgba(0,0,0,.3)}
      .transport .main:hover{background:#fff}
      .transport ha-icon{--mdc-icon-size:24px}
      .transport .main ha-icon{--mdc-icon-size:30px}
      .vol{display:flex; align-items:center; gap:12px}
      .vol ha-icon{color:rgba(244,244,246,.6); --mdc-icon-size:20px}
      .vol output{font-size:11px; color:rgba(244,244,246,.55); font-variant-numeric:tabular-nums; min-width:24px; text-align:right}
      .vol input{flex:1}

      /* sliders */
      input[type=range]{-webkit-appearance:none; appearance:none; width:100%; height:6px; border-radius:99px; background:#e3e4e8; outline:none; cursor:pointer}
      input[type=range]::-webkit-slider-thumb{-webkit-appearance:none; appearance:none; width:22px; height:22px; border-radius:50%; background:#fff; border:1px solid rgba(20,22,26,.18); box-shadow:0 2px 7px rgba(18,20,24,.28); cursor:grab}
      input[type=range]::-moz-range-thumb{width:22px; height:22px; border-radius:50%; background:#fff; border:1px solid rgba(20,22,26,.18); box-shadow:0 2px 7px rgba(18,20,24,.28); cursor:grab}
      input[type=range]:disabled{opacity:.4}
      .player input[type=range]{background:rgba(255,255,255,.22)}
      .range{display:grid; grid-template-columns:1fr auto; gap:8px 14px; align-items:center; font-size:14px; margin:16px 0}
      .range output{font-size:11.5px; color:var(--hk-soft); font-variant-numeric:tabular-nums}
      .range input{grid-column:1/-1}
      .range.is-disabled{opacity:.5}

      /* gradient color slider */
      .color-slider input{background:linear-gradient(90deg,${themeInfo.g.join(",")}); height:12px; box-shadow:inset 0 0 0 1px rgba(0,0,0,.15)}
      .color-slider input::-webkit-slider-thumb,.brightness-slider input::-webkit-slider-thumb{box-sizing:border-box; width:26px; height:26px; background:transparent; border:5px solid #fff; box-shadow:0 0 0 1px rgba(20,22,26,.22),0 2px 5px rgba(18,20,24,.20)}
      .color-slider input::-moz-range-thumb,.brightness-slider input::-moz-range-thumb{box-sizing:border-box; width:26px; height:26px; background:transparent; border:5px solid #fff; box-shadow:0 0 0 1px rgba(20,22,26,.22),0 2px 5px rgba(18,20,24,.20)}
      .brightness-slider input{height:12px; background:linear-gradient(90deg,#93969d,#faf7f3); box-shadow:inset 0 0 0 1px rgba(20,22,26,.15)}

      /* ---------- section headers ---------- */
      .sec-head{display:flex; align-items:center; justify-content:space-between; margin-bottom:6px}
      .sec-head h3{font-size:13px; font-weight:600; letter-spacing:.02em; margin:0}
      .link{font-size:12px; color:var(--hk-soft); padding:4px 2px; border-radius:8px}
      .link:hover{color:var(--hk-ink); background:#f4f4f6}

      /* ---------- lighting ---------- */
      .themes{display:grid; grid-template-columns:repeat(3,minmax(0,96px)); justify-content:center; gap:10px; margin:10px auto 0}
      .theme{position:relative; min-width:0; height:128px; border-radius:24px; overflow:hidden; padding:0;
        background:linear-gradient(168deg,var(--g));
        transition:transform .18s ease, box-shadow .18s ease}
      .theme:before{content:""; position:absolute; inset:0; pointer-events:none;
        background:linear-gradient(180deg,rgba(255,255,255,.58),rgba(255,255,255,.38) 55%,rgba(255,255,255,.48));
        transition:opacity .22s ease}
      .theme:after{content:""; position:absolute; inset:0; pointer-events:none; opacity:0;
        background:radial-gradient(ellipse 72% 65% at 50% 60%,rgba(255,255,255,.58),rgba(255,255,255,.12) 46%,rgba(17,29,38,.28) 100%);
        box-shadow:inset 0 0 0 1px rgba(255,255,255,.24); border-radius:inherit; transition:opacity .22s ease}
      .theme span{position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
        z-index:1; font-size:12px; letter-spacing:.02em; color:rgba(28,30,34,.70);
        transition:color .22s ease, text-shadow .22s ease}
      .theme span.horiz{writing-mode:horizontal-tb; letter-spacing:.06em; font-size:12.5px}
      /* 选中：遮罩换成中心提亮，颜色更饱和，文字转白 */
      .theme.active{box-shadow:0 5px 14px rgba(18,20,24,.14)}
      .theme.active:before{opacity:0}
      .theme.active:after{opacity:1}
      .theme.active span{color:#fff; text-shadow:0 1px 6px rgba(18,20,24,.3)}
      .theme:not(.active):hover{transform:translateY(-1px)}
      /* Sunrise opens from cool sky into a pale horizon; fireplace glows from embers. */
      .theme[data-theme="sunrise"]{background:linear-gradient(180deg,#7baac9 0%,#ccdce5 36%,#f5dd9b 65%,#efa76e 100%)}
      .theme[data-theme="sunrise"].active:after{background:radial-gradient(ellipse 70% 42% at 50% 64%,rgba(255,253,222,.90),rgba(255,245,204,.16) 65%,transparent 100%)}
      .theme[data-theme="fireplace"]{background:radial-gradient(ellipse 80% 76% at 50% 85%,#ffc453 0%,#e96b20 35%,#9d301f 67%,#49292b 100%)}
      .theme[data-theme="fireplace"].active:after{background:radial-gradient(ellipse 44% 46% at 50% 74%,rgba(255,226,155,.62),transparent 85%)}

      /* segmented speed */
      .seg{display:grid; grid-template-columns:repeat(3,1fr); background:#f1f1f4; border-radius:99px; padding:4px; margin-top:8px}
      .seg button{padding:11px 0; border-radius:99px; font-size:13px; color:var(--hk-soft); display:flex; flex-direction:column; align-items:center; gap:2px; transition:all .16s}
      .seg button .sub{font-size:10px; letter-spacing:.05em; opacity:.7; line-height:14px; height:14px}
      .triple-wave{position:relative; width:14px}
      .triple-wave i{position:absolute; inset:0; font-style:normal; text-align:center}
      .triple-wave i:first-child{transform:translateY(-3px)}
      .triple-wave i:last-child{transform:translateY(3px)}
      .seg button.on{background:#2a2b2e; color:#fff; box-shadow:0 3px 10px rgba(18,20,24,.25)}

      /* ---------- EQ ---------- */
      .eq{display:grid; grid-template-columns:repeat(7,1fr); gap:8px; align-items:end; margin-top:10px}
      .eq-range{display:flex; flex-direction:column-reverse; align-items:center; gap:8px; margin:0; text-align:center}
      .eq-range input{writing-mode:vertical-lr; direction:rtl; height:150px; width:8px; grid-column:auto}
      .eq-range input::-webkit-slider-thumb{width:18px; height:18px}
      .eq-range output{font-size:10.5px; color:var(--hk-ink); font-variant-numeric:tabular-nums; min-height:14px}
      .eq-range span{font-size:10px; color:var(--hk-soft)}

      /* ---------- settings list ---------- */
      .row{display:flex; align-items:center; justify-content:space-between; gap:14px; padding:15px 0}
      .row+.row{border-top:1px solid var(--hk-line)}
      .row .lab{font-size:14px}
      .row .desc{font-size:11.5px; color:var(--hk-soft); margin-top:3px; max-width:46ch}
      .row .val{font-size:13px; color:var(--hk-soft)}
      select{background:#f3f3f5; color:var(--hk-ink); border:1px solid var(--hk-line); border-radius:11px; padding:9px 12px; font-size:13px}
      select:focus-visible{outline:2px solid var(--hk-dark); outline-offset:1px}

      /* iOS toggle (HK dark) */
      .toggle{width:46px; height:28px; border-radius:99px; background:#dcdde1; padding:3px; transition:background .18s; flex:none}
      .toggle i{display:block; width:22px; height:22px; border-radius:50%; background:#fff; box-shadow:0 2px 5px rgba(18,20,24,.28); transition:transform .18s}
      .toggle.on{background:#1c1d20}
      .toggle.on i{transform:translateX(18px)}

      /* preset */
      .preset-grid{display:grid; grid-template-columns:minmax(0,1fr) auto auto; gap:8px; margin-top:6px}
      .preset-message{font-size:12px; color:var(--hk-soft); margin:10px 0 0}
      .preset-grid select{min-width:0}
      .preset-new{display:grid; grid-template-columns:1fr auto; gap:10px; margin-top:10px}
      .preset-new input{background:#f3f3f5; border:1px solid var(--hk-line); border-radius:11px; padding:9px 12px; font-size:13px; min-width:0}
      .btn{background:#f3f3f5; border:1px solid var(--hk-line); border-radius:11px; padding:9px 14px; font-size:13px; color:var(--hk-ink)}
      .btn:hover{background:#ececef}
      .btn.dark{background:#2a2b2e; color:#fff; border-color:#2a2b2e}

      .notice{margin:0 2px 14px; padding:15px 20px; background:#fdeceb; color:#c03b2b; border-radius:16px; font-size:12.5px}
      .foot{padding:4px 8px 12px; text-align:center; font-size:9.5px; letter-spacing:.14em; color:var(--hk-faint)}

      button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--hk-dark); outline-offset:2px}
      @container soundsticks (max-width:540px){
        ha-card{padding:14px 10px 6px; border-radius:22px}
        .card{padding:20px 18px; border-radius:18px}
        .hero{padding:6px 18px 18px}
        .player{padding:18px 18px 20px; border-radius:18px}
        .eq-range input{height:124px}
      }
      @media(prefers-reduced-motion:reduce){*{animation:none!important; transition:none!important}}
    </style>

    <ha-card>
      <!-- HERO / brand -->
      <div class="hero">
        <div class="brand">harman<em>/</em><span class="k">kardon</span></div>
        <div class="model">SOUNDSTICKS 5</div>
        ${this._productImg(ledColor, lightOn)}
        <div class="hero-meta">
          <span class="status ${lightOn ? "on" : ""}"><i></i>${lightOn ? this._t("灯光开启", "Lighting on") : this._t("灯光关闭", "Lighting off")}</span>
          <div class="hero-actions">
            <button class="ghost" title="${this._t("获取状态", "Refresh state")}" data-action="refresh_state:press"><ha-icon icon="mdi:refresh"></ha-icon></button>
            <button class="ghost" title="${this._t("释放 BLE 控制", "Release BLE control")}" data-action="release_ble:press"><ha-icon icon="mdi:bluetooth-off"></ha-icon></button>
          </div>
        </div>
      </div>

      <!-- PLAYBACK -->
      <div class="player">
        <div class="top">
          <div class="bt"><ha-icon icon="${transport.external ? "mdi:music" : "mdi:bluetooth"}"></ha-icon></div>
          <div class="np">
            <div class="t">${this._escape(title)}</div>
            <div class="a">${this._escape(artist || (playing ? this._t("正在播放", "Now playing") : this._t("已暂停", "Paused")))}</div>
          </div>
        </div>
        ${this._transportError ? `<div class="transport-source" role="alert">${this._escape(this._transportError)}</div>` : ""}
        <div class="transport">
          <button data-transport="previous" ${this._canTransport(transport,"previous") ? "" : "disabled"} title="${this._t("上一首", "Previous")}"><ha-icon icon="mdi:skip-previous"></ha-icon></button>
          <button class="main" data-transport="toggle" ${this._canTransport(transport,"toggle") ? "" : "disabled"} title="${playing ? this._t("暂停", "Pause") : this._t("播放", "Play")}"><ha-icon icon="${playing ? "mdi:pause" : "mdi:play"}"></ha-icon></button>
          <button data-transport="next" ${this._canTransport(transport,"next") ? "" : "disabled"} title="${this._t("下一首", "Next")}"><ha-icon icon="mdi:skip-next"></ha-icon></button>
        </div>
        <div class="vol">
          <ha-icon icon="mdi:volume-low"></ha-icon>
          <input data-key="media_player" type="range" min="0" max="100" step="1" value="${mediaVolume}" ${bleMedia ? "" : "disabled"}>
          <output>${mediaVolume}</output>
          <ha-icon icon="mdi:volume-high"></ha-icon>
        </div>
      </div>

      <!-- LIGHTING -->
      <div class="card">
        <div class="sec-head"><h3>${this._t("灯光", "Lighting")}</h3><button class="toggle ${lightOn ? "on" : ""}" data-toggle="lighting" aria-label="${this._t("灯光开关", "Lighting")}"><i></i></button></div>
        <div class="themes">${themeButtons}</div>

        <div class="sec-head" style="margin-top:20px"><h3>${this._t("颜色", "Color")}</h3><button class="link" data-action="color_reset:press">${this._t("重置", "Reset")}</button></div>
        ${this._range("color", "", 0, 100, "color-slider")}

        ${this._range("brightness", this._t("亮度", "Brightness"), 0, 100, "brightness-slider")}

        <div class="sec-head" style="margin-top:6px"><h3>${this._t("速度", "Speed")}</h3></div>
        <div class="seg">
          <button data-speed="low" class="${speed === "low" ? "on" : ""}">${this._t("低", "Low")}${this._speedWaves(1)}</button>
          <button data-speed="medium" class="${speed === "medium" ? "on" : ""}">${this._t("中", "Medium")}${this._speedWaves(2)}</button>
          <button data-speed="high" class="${speed === "high" ? "on" : ""}">${this._t("高", "High")}${this._speedWaves(3)}</button>
        </div>
      </div>

      <!-- EQ -->
      <div class="card">
        <div class="sec-head"><h3>${this._t("均衡器", "Equalizer")}</h3><button class="link" data-action="eq_reset:press">${this._t("重置", "Reset")}</button></div>
        <div class="eq">${eq}</div>
      </div>

      <!-- PRESETS -->
      <div class="card">
        <div class="sec-head"><h3>${this._t("场景预设", "Presets")}</h3></div>
        <div class="preset-grid">
          <select data-preset-select aria-label="${this._t("选择预设", "Select preset")}" ${presetOptions && !this._presetBusy ? "" : "disabled"}>${presetOptions || `<option>${this._t("尚无预设", "No presets")}</option>`}</select>
          <button class="btn dark" data-preset-apply ${presetOptions && !this._presetBusy ? "" : "disabled"}>${this._presetBusy ? this._t("应用中", "Applying") : this._t("应用", "Apply")}</button>
          <button class="btn" data-preset-delete ${presetOptions && !this._presetBusy ? "" : "disabled"}>${this._t("删除", "Delete")}</button>
        </div>
        ${this._presetMessage ? `<div class="preset-message" role="status">${this._escape(this._presetMessage)}</div>` : ""}
        <div class="preset-new">
          <input data-preset-name maxlength="40" placeholder="${this._t("例如：夜间氛围", "e.g. Evening")}">
          <button class="btn dark" data-preset-save>${this._t("保存当前", "Save")}</button>
        </div>
      </div>

      <!-- DEVICE SETTINGS -->
      <div class="card">
        <div class="sec-head"><h3>${this._t("产品设置", "Settings")}</h3></div>
        <div class="row">
          <div><div class="lab">${this._t("自动关闭", "Auto-off")}</div><div class="desc">${this._t("无活动一段时间后自动关机", "Power off after a period of inactivity")}</div></div>
          <select data-key="auto_off" data-option>
            ${Object.entries(AUTO_LABELS).map(([v, l]) => `<option value="${v}" ${autoOff === v ? "selected" : ""}>${l[0]}</option>`).join("")}
          </select>
        </div>
        <div class="row">
          <div><div class="lab">${this._t("反馈音", "Feedback tone")}</div><div class="desc">${this._t("启用/禁用按钮操作音效", "Button feedback sound")}</div></div>
          <button class="toggle ${feedbackOn ? "on" : ""}" data-toggle="feedback_tone" aria-label="${this._t("反馈音", "Feedback tone")}"><i></i></button>
        </div>
      </div>

      ${missing ? `<div class="notice">${this._t("未找到 SoundSticks 5 实体，可在卡片 YAML 中显式填写实体 ID。", "No SoundSticks 5 entities found; supply entity IDs in the card YAML.")}</div>` : ""}
      <div class="foot">HARMAN / KARDON · SOUNDSTICKS 5</div>
    </ha-card>`;

    this._bind();
  }

  /* ---------- events ---------- */

  _bind() {
    this.shadowRoot.querySelector("[data-preset-select]")?.addEventListener("change", (event) => {
      this._selectedPreset = event.target.value;
      this._presetMessage = "";
    });
    this.shadowRoot.querySelector("[data-preset-apply]")?.addEventListener("click", async () => {
      const name = this._selectedPreset;
      if (!name || this._presetBusy) return;
      this._presetBusy = true;
      this._presetMessage = "";
      this._safeRender();
      try {
        await this._call("preset", "select_option", {option:name});
        this._presetMessage = this._t("已应用：", "Applied: ") + name;
      } catch (error) {
        this._presetMessage = this._t("应用未完成，请检查设备状态后重试。", "Apply did not complete. Check the device and retry.");
      } finally {
        this._presetBusy = false;
        this._safeRender();
      }
    });
    this.shadowRoot.querySelectorAll("[data-transport]").forEach((node) => node.addEventListener("click", () => void this._sendTransport(node.dataset.transport)));
    this.shadowRoot.querySelectorAll("[data-action]").forEach((node) => node.addEventListener("click", () => {
      const [key, service] = node.dataset.action.split(":");
      void this._call(key, service);
    }));
    this.shadowRoot.querySelectorAll("[data-theme]").forEach((node) => node.addEventListener("click", () => {
      void this._call("theme", "select_option", { option: node.dataset.theme });
    }));
    this.shadowRoot.querySelectorAll("[data-speed]").forEach((node) => node.addEventListener("click", () => {
      void this._call("speed", "select_option", { option: node.dataset.speed });
    }));
    this.shadowRoot.querySelectorAll("[data-option]").forEach((node) => node.addEventListener("change", () => {
      void this._call(node.dataset.key, "select_option", { option: node.value });
    }));
    this.shadowRoot.querySelectorAll("input[type=range]").forEach((node) => {
      node.addEventListener("pointerdown", () => this._dragging.add(node.dataset.key));
      node.addEventListener("input", () => this._sendRange(node));
      node.addEventListener("change", () => this._sendRange(node, true));
      node.addEventListener("keyup", (e) => { if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"].includes(e.key)) this._sendRange(node, true); });
    });
    this.shadowRoot.querySelectorAll("[data-toggle]").forEach((node) => node.addEventListener("click", () => {
      const key = node.dataset.toggle;
      void this._call(key, this._state(key)?.state === "on" ? "turn_off" : "turn_on");
    }));
    this.shadowRoot.querySelector("[data-preset-save]")?.addEventListener("click", async () => {
      const input = this.shadowRoot.querySelector("[data-preset-name]");
      const name = input?.value.trim();
      if (!name) return input?.focus();
      await this._domainCall("save_preset", { name });
      input.value = "";
    });
    this.shadowRoot.querySelector("[data-preset-delete]")?.addEventListener("click", () => {
      const name = this._selectedPreset;
      if (name && !["unknown", "unavailable"].includes(name)) void this._domainCall("delete_preset", { name });
    });
  }
}

class SoundSticks5LovelaceEditor extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: "open" }); }
  setConfig(config) { this._config = { ...config }; this._render(); }
  set hass(hass) { this._hass = hass; if (!this._ready) this._render(); }
  _render() {
    if (!this._config || !this._hass) return;
    this._ready = true;
    const zh = this._hass.language?.startsWith("zh");
    const t = (a,b) => zh ? a : b;
    const esc = (v) => String(v ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c]);
    const ids = Object.keys(this._hass.states).filter(id=>id.startsWith("media_player."));
    for (const id of [this._config.playback_entity, this._config.media_player]) if (id && !ids.includes(id)) ids.push(id);
    const options = (selected) => `<option value="">${t("自动识别 / 未指定","Automatic / not selected")}</option>` + ids.sort().map(id=>`<option value="${esc(id)}" ${id===selected?'selected':''}>${esc(this._hass.states[id]?.attributes?.friendly_name || id)} · ${esc(id)}</option>`).join("");
    this.shadowRoot.innerHTML = `<style>:host{display:block}label{display:block;margin:16px 0}select{display:block;width:100%;padding:12px;margin-top:8px;color:var(--primary-text-color);background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:8px}p{font-size:13px;line-height:1.6;color:var(--secondary-text-color)}</style>
      <label>${t("播放控制方式","Playback control")}<select data-config="playback_mode">
      ${[["auto",t("自动","Automatic")],["entity",t("指定媒体实体","Selected media entity")],["ble",t("仅 BLE","BLE only")]].map(([value,label])=>`<option value="${value}" ${(this._config.playback_mode||"auto")===value?'selected':''}>${label}</option>`).join("")}</select></label>
      <label>${t("播放源实体","Playback source entity")}<select data-config="playback_entity">${options(this._config.playback_entity)}</select></label>
      <p>${t("歌名、歌手、播放状态及上一首 / 播放 / 暂停 / 下一首使用同一个播放源。指定模式不会在源离线时转而控制其他播放器。","Track information and transport controls use the same source. Selected mode never switches to another player when offline.")}</p>
      <p>${t("自动模式：所选播放源正在播放或暂停时使用它，否则使用 BLE。未指定时，只识别同一 HA 设备下唯一的其他播放器；不会按名字猜测。","Automatic: use the selected source when playing or paused, otherwise BLE. Without a selection, only a unique player on the same HA device can be detected; names are not used for matching.")}</p>
      <label>${t("音箱 BLE 媒体实体","Speaker BLE media entity")}<select data-config="media_player">${options(this._config.media_player)}</select></label>
      <p>${t("音箱音量、灯光和 EQ 始终通过 SoundSticks 集成控制。","Speaker volume, lighting and EQ always use the SoundSticks integration.")}</p>`;
    this.shadowRoot.querySelectorAll("select").forEach(select=>select.addEventListener("change",()=>{
      const config={...this._config};
      if(select.value) config[select.dataset.config]=select.value; else delete config[select.dataset.config];
      this._config=config;
      this.dispatchEvent(new CustomEvent("config-changed",{detail:{config},bubbles:true,composed:true}));
    }));
  }
}
if (!customElements.get("soundsticks5-lovelace-editor")) customElements.define("soundsticks5-lovelace-editor", SoundSticks5LovelaceEditor);
if (!customElements.get("soundsticks5-lovelace-card")) customElements.define("soundsticks5-lovelace-card", SoundSticks5LovelaceCard);
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "soundsticks5-lovelace-card"))
  window.customCards.push({ type: "soundsticks5-lovelace-card", name: "SoundSticks 5 (HK design)", description: "Harman Kardon design-language card for SoundSticks 5" });
