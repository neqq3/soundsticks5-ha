const assert = require('node:assert/strict');
const classes = new Map();
global.HTMLElement = class { attachShadow() { return this.shadowRoot = {innerHTML:'',querySelectorAll:()=>[],querySelector:()=>null}; } };
global.customElements = {get:n=>classes.get(n),define:(n,c)=>classes.set(n,c)};
global.window = {customCards:[]};
require('../soundsticks5-lovelace.js');
const Card = classes.get('soundsticks5-lovelace-card');
const c = new Card();
const ble='media_player.ble', ma='media_player.ma';
const calls=[];
c._hass={language:'zh',states:{
  [ble]:{state:'playing',attributes:{volume_level:.15}},
  [ma]:{state:'playing',attributes:{media_title:'Signals',media_artist:'Lazer Boomerang',volume_level:.8,supported_features:16433}}
},callService:async(...args)=>calls.push(args)};
c._entities={media_player:ble};
c._config={playback_mode:'entity',playback_entity:ma};
(async()=>{
  c._render();
  assert.match(c.shadowRoot.innerHTML,/Signals/);
  assert.match(c.shadowRoot.innerHTML,/Lazer Boomerang/);
  assert.match(c.shadowRoot.innerHTML,/data-key="media_player"[^>]*value="15"/);
  await c._sendTransport('toggle');
  assert.deepEqual(calls.pop(),['media_player','media_pause',{entity_id:ma}]);
  c._hass.states[ma].state='paused';
  await c._sendTransport('toggle');
  assert.deepEqual(calls.pop(),['media_player','media_play',{entity_id:ma}]);
  await c._sendTransport('next');
  assert.deepEqual(calls.pop(),['media_player','media_next_track',{entity_id:ma}]);
  c._hass.states[ma].attributes.supported_features=1;
  await c._sendTransport('next'); assert.equal(calls.length,0);
  c._hass.states[ma].state='unavailable';
  await c._sendTransport('toggle'); assert.equal(calls.length,0);
  c._render(); assert.doesNotMatch(c.shadowRoot.innerHTML,/Signals/);
  c._config.playback_mode='auto'; assert.equal(c._transport().id,ble);
  c._hass.states[ma].state='playing'; assert.equal(c._transport().id,ma);
  c._hass.states[ma].state='paused'; assert.equal(c._transport().id,ma);
  c._hass.states[ma].state='idle'; assert.equal(c._transport().id,ble);
  c._config.playback_mode='ble'; await c._sendTransport('toggle');
  assert.deepEqual(calls.pop(),['media_player','media_pause',{entity_id:ble}]);
  c._config={playback_mode:'auto'};
  c._registry=[{entity_id:ble,device_id:'speaker'},{entity_id:ma,device_id:'other'}];
  c._hass.states[ma].state='playing'; assert.equal(c._transport().id,ble);
  c._registry[1].device_id='speaker'; assert.equal(c._transport().id,ma);
  c._registry.push({entity_id:'media_player.ambiguous',device_id:'speaker'});
  assert.equal(c._transport().id,ble);
  console.log('PASS: metadata, transport routing, BLE volume, unavailable/unsupported controls, auto fallback and ambiguity');
})().catch(e=>{console.error(e);process.exitCode=1});
