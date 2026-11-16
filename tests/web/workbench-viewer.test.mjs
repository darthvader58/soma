import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { createWorkbenchViewer } from '../../web/src/workbench-viewer.js';

const require = createRequire(new URL('../../web/package.json', import.meta.url));
const Cesium = require('cesium');

async function displayHarness(t) {
  const previous = globalThis.ResizeObserver;
  globalThis.ResizeObserver = class { observe() {} disconnect() {} };
  t.after(() => { globalThis.ResizeObserver = previous; });
  let scene;
  class Viewer {
    constructor() {
      scene = this;
      this.entities = new Cesium.EntityCollection();
      this.scene = { canvas: { clientWidth: 800, clientHeight: 500 }, primitives: { add: value => value },
        renderError: { addEventListener() {} }, requestRender() {} };
      this.camera = { frustum: { fovy: Math.PI / 3 }, cancelFlight() {}, setView() {}, flyTo() {} };
      this.clock = {};
    }
    resize() {}
    destroy() {}
  }
  const C = { ...Cesium, Viewer, ScreenSpaceEventHandler: class { setInputAction() {} destroy() {} } };
  const api = await createWorkbenchViewer({}, { loadCesium: async () => C });
  t.after(() => api.destroy());
  return { api, scene };
}

const result = () => ({ epochs_utc: ['2026-04-01T00:00:00Z'], spacecraft: [], sites: [{
  id: 'custom-a', name: 'Calculated custom site', position_m: [1737400, 0, 0],
  samples: [{ epoch_utc: '2026-04-01T00:00:00Z', sun: { direction_moon_fixed: [1, 0, 0] }, earth: { direction_moon_fixed: [0, 1, 0] } }],
}] });

test('a calculated custom point is a pickable labeled context ring without altering engine positions', async t => {
  const { api, scene } = await displayHarness(t);
  const calculated = result(), original = structuredClone(calculated);
  api.setCatalog([{ id: 'custom-a', name: 'Draft custom site' }]);
  api.setSelection(['custom-a'], 'custom-a');
  api.setResult(calculated);
  const marker = scene.entities.getById('evaluated-custom-a');
  assert.ok(marker);
  const position = marker.position.getValue(Cesium.JulianDate.fromIso8601(calculated.epochs_utc[0]));
  assert.ok(Math.abs(Cesium.Cartesian3.magnitude(position) - 1747400) < 1e-6);
  assert.equal(marker.properties.siteId.getValue(), 'custom-a');
  assert.equal(marker.label.text.getValue(), 'Calculated custom site · evaluated');
  assert.equal(marker.point.color.getValue().alpha, 0);
  assert.equal(scene.entities.getById('catalog-custom-a'), undefined);
  assert.deepEqual(calculated, original);
  api.setLayers({ labels: false, paths: true, directions: true });
  assert.equal(scene.entities.getById('evaluated-custom-a').label.show.getValue(), false);
});

test('an unchecked context selection does not borrow another site direction vectors', async t => {
  const { api, scene } = await displayHarness(t);
  api.setResult(result());
  api.setSelection(['custom-a'], 'custom-a');
  assert.equal(scene.entities.values.filter(entity => entity.polyline).length, 2);
  api.setSelection(['custom-a'], 'uncalculated-context');
  assert.equal(scene.entities.values.filter(entity => entity.polyline).length, 0);
});
