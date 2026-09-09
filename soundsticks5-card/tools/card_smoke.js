// 最小 DOM 桩：验证 soundsticks5-lovelace-card 渲染不抛异常
class Fake {
  constructor() {
    this.shadowRoot = { innerHTML: "", querySelectorAll: () => [], querySelector: () => null };
  }
  attachShadow() { return this.shadowRoot; }
}
global.HTMLElement = Fake;
let Defined = null;
global.customElements = { get: () => null, define: (n, c) => { Defined = c; } };
global.window = { customCards: [], setTimeout: () => 0, clearTimeout: () => {} };
const realError = console.error;
global.console.error = (...a) => { realError("[卡片内部错误]", ...a); };

require("../soundsticks5-lovelace.js");

const IDS = {
  media_player: "media_player.soundsticks_5_media",
  lighting: "light.soundsticks_5_lighting",
  theme: "select.soundsticks_5_lighting_theme",
  color: "number.soundsticks_5_current_theme_color",
  brightness: "number.soundsticks_5_lighting_brightness",
  speed: "select.soundsticks_5_lighting_speed",
  eq_125: "number.soundsticks_5_eq_125_hz",
  eq_250: "number.soundsticks_5_eq_250_hz",
  eq_500: "number.soundsticks_5_eq_500_hz",
  eq_1000: "number.soundsticks_5_eq_1000_hz",
  eq_2000: "number.soundsticks_5_eq_2000_hz",
  eq_4000: "number.soundsticks_5_eq_4000_hz",
  eq_8000: "number.soundsticks_5_eq_8000_hz",
  feedback_tone: "switch.soundsticks_5_feedback_tone",
  auto_off: "select.soundsticks_5_auto_off",
  auto_off_remaining: "sensor.soundsticks_5_auto_off_remaining",
  operating_state: "sensor.soundsticks_5_operating_state",
  preset: "select.soundsticks_5_preset",
  ble_connection: "sensor.soundsticks_5_ble_connection",
};

function mkStates(full) {
  if (!full) return {};
  const s = {};
  for (const v of Object.values(IDS)) s[v] = { entity_id: v, state: "on", attributes: {} };
  s[IDS.media_player].state = "playing";
  s[IDS.media_player].attributes = { media_title: "测试曲目", media_artist: "测试歌手", volume_level: 0.42 };
  s[IDS.theme].state = "ocean";
  s[IDS.preset].attributes = { options: ["夜间氛围"] };
  return s;
}

function run(label, full) {
  const card = new Defined();
  card._hass = {
    states: mkStates(full),
    language: "zh",
    callService: async () => {},
    callWS: async () => [],
  };
  card.setConfig({});
  card._safeRender();
  const html = card.shadowRoot.innerHTML;
  const ok = html.length > 3000 && !html.includes("卡片渲染出错");
  const verdict = ok ? "渲染正常" : "渲染异常";
  console.log(label + ": HTML " + html.length + " 字符 -> " + verdict);
  if (!ok) console.log("  片段: " + html.slice(0, 400));
  return ok;
}

console.log("注册元素名: " + (global.window.customCards[0] && global.window.customCards[0].type));
const a = run("[无实体]", false);
const b = run("[实体齐全]", true);
process.exit(a && b ? 0 : 1);
