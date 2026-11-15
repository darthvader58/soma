import test from 'node:test';
import assert from 'node:assert/strict';
import { createMoonViewer, MOON_ASSET_ID } from '../../web/src/viewer.js';

class Element {
  children = [];
  ownerDocument = { createElement: () => new Element() };
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; }
}
class Event {
  listeners = new Set();
  addEventListener(fn) { this.listeners.add(fn); return () => this.listeners.delete(fn); }
  fire() { for (const fn of [...this.listeners]) fn(); }
}
function harness({ assetFails = false, depth = true, deferredAsset = false } = {}) {
  const state = { statuses: [], picks: [], imports: 0, entities: [], depthCalls: 0 };
  const moon = { tileFailed: new Event(), dead: false, isDestroyed() { return this.dead; }, destroy() { this.dead = true; } };
  let resolveAsset;
  const assetPromise = new Promise((resolve) => { resolveAsset = resolve; });
  class Cartesian3 {
    constructor(x, y, z) { Object.assign(this, { x, y, z }); }
    static clone(point) { return { ...point }; }
  }
  const cesium = {
    Ellipsoid: { MOON: {} }, Ion: {}, SceneMode: { SCENE3D: 3 },
    Color: { WHITE: 'white', BLACK: 'black', fromCssColorString: (value) => value },
    Cartesian3, Cartesian2: class { constructor(x, y) { Object.assign(this, { x, y }); } },
    LightingModel: { UNLIT: 'unlit' }, ScreenSpaceEventType: { LEFT_CLICK: 'click' },
    JulianDate: { fromIso8601: (epoch) => { if (!Number.isFinite(Date.parse(epoch))) throw Error(); return epoch; } },
    Math: { toDegrees: (radians) => radians * 180 / Math.PI },
    Cartographic: { fromCartesian: () => ({ latitude: -Math.PI / 2, longitude: Math.PI, height: 50 }) },
    CustomShader: class { dead = false; constructor(options) { state.shader = this; state.shaderOptions = options; } isDestroyed() { return this.dead; } destroy() { this.dead = true; } },
    Cesium3DTileset: { fromIonAssetId: async (id) => { state.assetId = id; if (assetFails) throw Error(); if (deferredAsset) return assetPromise; return moon; } },
    Viewer: class {
      dead = false;
      clock = {};
      camera = { setView() {} };
      entities = { add: (entity) => { state.entities.push(entity); return entity; }, remove: (entity) => { state.entities.splice(state.entities.indexOf(entity), 1); } };
      scene = { canvas: {}, pickPositionSupported: depth, renderError: new Event(),
        primitives: { add: (primitive) => { state.primitive = primitive; } },
        pick: () => state.picked, pickPosition: () => { state.depthCalls++; return state.point; }, requestRender() {} };
      constructor(container, options) { state.viewer = this; state.options = options; assert.equal(cesium.Ellipsoid.default, cesium.Ellipsoid.MOON); }
      isDestroyed() { return this.dead; }
      destroy() { this.dead = true; }
    },
    ScreenSpaceEventHandler: class {
      constructor() { state.handler = this; }
      setInputAction(fn) { state.click = fn; }
      destroy() { state.handlerDead = true; }
    },
  };
  const container = new Element();
  return { state, moon, cesium, container, resolveAsset: () => resolveAsset(moon),
    start: (ionToken = 'test-token') => createMoonViewer(container, { ionToken,
      scenario: { data_ready_utc: '2026-11-14T08:50:00Z' },
      loadCesium: async () => { state.imports++; return cesium; },
      onPick: (pick) => state.picks.push(pick), onStatus: (status) => state.statuses.push(status),
    }),
    select() { state.picked = { primitive: moon }; state.point = { x: 1, y: 2, z: 3 }; state.click({ position: {} }); },
  };
}

test('tokenless fallback never imports Cesium and remains safe to dispose', async () => {
  const h = harness(); const api = await h.start(' ');
  assert.equal(h.state.imports, 0);
  assert.equal(h.state.statuses.at(-1).state, 'fallback');
  assert.match(h.container.children[0].children[1].textContent, /coordinate fields/);
  api.clearDisplayPick(); api.destroy(); api.destroy();
});

test('official Moon configuration, raw Cartesian marker, display contract and clearing', async () => {
  const h = harness(); const api = await h.start();
  assert.equal(h.state.assetId, MOON_ASSET_ID);
  for (const key of ['globe', 'baseLayer', 'sceneModePicker', 'baseLayerPicker', 'geocoder', 'shadows']) assert.equal(h.state.options[key], false);
  assert.equal(h.state.options.scene3DOnly, true);
  assert.equal(h.state.shaderOptions.lightingModel, 'unlit');
  h.select();
  const marker = h.state.entities[0];
  assert.deepEqual(marker.position, h.state.point);
  assert.notEqual(marker.position, h.state.point);
  assert.match(marker.label.text, /Display point.*not service-resolved/);
  assert.equal(h.state.picks[0].service_resolved, false);
  assert.equal(h.state.picks[0].display_elevation_m, 50);
  assert.equal(h.state.picks[0].longitude_deg_east, -180);
  assert.equal(h.state.picks[0].elevation_m, undefined);
  assert.equal(h.state.statuses.at(-1).overlaysBlocked, true);
  api.clearDisplayPick(); assert.equal(h.state.entities.length, 0);
  h.select(); api.setScenario({}); assert.equal(h.state.entities.length, 0);
  api.destroy();
});

for (const kind of ['sky', 'asset', 'unsupported depth', 'missing depth', 'invalid depth']) {
  test(`rejects ${kind} without selecting an analysis point`, async () => {
    const h = harness({ depth: kind !== 'unsupported depth' }); const api = await h.start();
    h.state.picked = kind === 'sky' ? undefined : { primitive: kind === 'asset' ? {} : h.moon };
    h.state.point = kind === 'missing depth' ? undefined : { x: 1, y: 2, z: 3 };
    if (kind === 'invalid depth') h.cesium.Cartographic.fromCartesian = () => ({ latitude: NaN });
    h.state.click({ position: {} });
    assert.equal(h.state.picks.length, 0); assert.equal(h.state.entities.length, 0);
    if (['sky', 'asset', 'unsupported depth'].includes(kind)) assert.equal(h.state.depthCalls, 0);
    api.destroy();
  });
}

for (const failure of ['tile', 'render']) {
  test(`${failure} failure clears selection, detaches listeners and blocks stale callbacks`, async () => {
    const h = harness(); const api = await h.start(); h.select();
    const viewer = h.state.viewer;
    (failure === 'tile' ? h.moon.tileFailed : viewer.scene.renderError).fire();
    assert.equal(viewer.dead, true); assert.equal(h.state.shader.dead, true);
    assert.equal(h.state.entities.length, 0); assert.equal(h.state.handlerDead, true);
    assert.equal(h.moon.tileFailed.listeners.size, 0); assert.equal(viewer.scene.renderError.listeners.size, 0);
    assert.equal(h.state.statuses.at(-1).state, 'fallback');
    h.select(); assert.equal(h.state.picks.length, 1);
    api.destroy();
  });
}

test('asset failure disposes partial initialization', async () => {
  const h = harness({ assetFails: true }); const api = await h.start();
  assert.equal(h.state.viewer.dead, true); assert.equal(h.state.shader.dead, true);
  assert.equal(h.state.statuses.at(-1).state, 'fallback'); api.destroy();
});

test('timezone-qualified time is passed through and invalid time cannot change the clock', async () => {
  const h = harness(); const api = await h.start();
  assert.equal(h.state.viewer.clock.currentTime, '2026-11-14T08:50:00Z');
  api.setTime('2026-11-14T09:00:00+02:00');
  assert.equal(h.state.viewer.clock.currentTime, '2026-11-14T09:00:00+02:00');
  for (const value of ['2026-11-14T10:00:00', 'invalidZ']) api.setTime(value);
  assert.equal(h.state.viewer.clock.currentTime, '2026-11-14T09:00:00+02:00');
  assert.equal(h.state.statuses.at(-1).state, 'invalid_time');
  const previous = h.state.picks.length; api.destroy(); h.select();
  assert.equal(h.state.picks.length, previous);
});


test('render failure during asset loading keeps fallback and destroys a late tileset', async () => {
  const h = harness({ deferredAsset: true });
  const pending = h.start();
  await Promise.resolve();
  const viewer = h.state.viewer;
  viewer.scene.renderError.fire();
  assert.equal(h.state.statuses.at(-1).state, 'fallback');
  const fallbackPanel = h.container.children[0];
  h.resolveAsset();
  const api = await pending;
  assert.equal(h.container.children[0], fallbackPanel);
  assert.equal(h.state.statuses.some(({ state }) => state === 'ready'), false);
  assert.equal(h.state.primitive, undefined);
  assert.equal(h.moon.dead, true);
  assert.equal(viewer.dead, true);
  assert.equal(h.state.shader.dead, true);
  assert.equal(viewer.scene.renderError.listeners.size, 0);
  assert.equal(h.moon.tileFailed.listeners.size, 0);
  assert.equal(h.state.handler, undefined);
  assert.equal(h.state.picks.length, 0);
  api.destroy();
});
