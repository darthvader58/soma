import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { createWorkbenchViewer, navigateCamera, earthBodyAtEpoch } from '../../web/src/workbench-viewer.js';

const require = createRequire(new URL('../../web/package.json', import.meta.url));
const Cesium = require('cesium');

async function displayHarness(t, realCamera = false) {
  const previous = globalThis.ResizeObserver;
  globalThis.ResizeObserver = class { observe() {} disconnect() {} };
  t.after(() => { globalThis.ResizeObserver = previous; });
  let scene;
  class Viewer {
    constructor() {
      scene = this;
      this.entities = new Cesium.EntityCollection();
      const primitives = [];
      this.scene = { canvas: { clientWidth: 800, clientHeight: 500 }, primitives: { values: primitives, add(value) { primitives.push(value); return value; }, remove(value) { const index = primitives.indexOf(value); if (index >= 0) primitives.splice(index, 1); } },
        drawingBufferWidth: 800, drawingBufferHeight: 500, mapProjection: new Cesium.GeographicProjection(Cesium.Ellipsoid.MOON), mode: Cesium.SceneMode.SCENE3D,
        renderError: { addEventListener() {} }, requestRender() {} };
      this.camera = realCamera ? new Cesium.Camera(this.scene) : { frustum: { fovy: Math.PI / 3 }, cancelFlight() {}, setView(view) { this.lastView = view; }, flyTo() {} };
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

function earthDisplayFixture() {
  const read = name => JSON.parse(readFileSync(new URL(`../../web/fixtures/physical-south-pole/relay-later/${name}.json`, import.meta.url)));
  const scenario = read('scenario'), display = read('display-data'), epoch = display.renderer_states[0].epoch;
  const rotation = [0, -1, 0, 1, 0, 0, 0, 0, 1];
  display.renderer_states.push({ ...display.renderer_states[0], target: 'EARTH', position: [380000000, 1000000, 2000000] });
  display.earth_body = { status: 'available', body_id: 'EARTH', reference_ellipsoid: 'WGS84', radii_m: [6378137, 6378137, 6356752.314245179], body_fixed_frame: 'ITRF93', renderer_frame: display.registration.renderer_frame,
    position_unit: 'm', time_scale: 'UTC', rotation_layout: 'row_major', rotation_unit: 'dimensionless', orientation_samples: [{ epoch_utc: epoch, rotation_body_fixed_to_renderer_row_major: rotation }], provenance: { scope: 'Synthetic orientation/center contract test only' } };
  return { scenario, display, epoch, rotation };
}

test('Earth body uses exact supplied pose and WGS84 radii, hides between epochs, remains separate from endpoint markers and fits Earth view', async t => {
  for (const name of ['HTMLCanvasElement', 'HTMLVideoElement', 'HTMLImageElement', 'ImageBitmap', 'OffscreenCanvas']) { const previous = globalThis[name]; globalThis[name] = class {}; t.after(() => { if (previous === undefined) delete globalThis[name]; else globalThis[name] = previous; }); }
  const { api, scene } = await displayHarness(t, true), fixture = earthDisplayFixture();
  const before = structuredClone(fixture.display);
  api.setDelivery(fixture); api.setTime(fixture.epoch);
  const primitive = scene.scene.primitives.values.find(value => value.geometryInstances?.id === 'delivery-earth-body');
  assert.ok(primitive); assert.equal(primitive.appearance.flat, true);
  const body = earthBodyAtEpoch(fixture.display, fixture.epoch);
  assert.deepEqual(Cesium.Matrix4.getTranslation(primitive.modelMatrix, new Cesium.Cartesian3()), new Cesium.Cartesian3(...body.center));
  assert.deepEqual(Cesium.Matrix4.getMatrix3(primitive.modelMatrix, new Cesium.Matrix3()), Cesium.Matrix3.fromRowMajorArray(fixture.rotation));
  assert.deepEqual(primitive.geometryInstances.geometry._radii, new Cesium.Cartesian3(...body.radii));
  api.camera('earth');
  assert.equal(scene.entities.getById('delivery-node-EARTH').label.show.getValue(), false);
  assert.ok(Cesium.Cartesian3.distance(scene.camera.positionWC, new Cesium.Cartesian3(...body.center)) > 6378137);
  for (let index = 0; index < 100; index++) api.navigate('zoom-in');
  api.setTime(fixture.epoch);
  assert.equal(scene.entities.getById('delivery-node-EARTH').label.show.getValue(), false);
  assert.ok(Cesium.Cartesian3.distance(scene.camera.positionWC, new Cesium.Cartesian3(...body.center)) >= 6388137);
  api.camera('network'); assert.equal(primitive.show, true);
  assert.equal(scene.entities.getById('delivery-node-EARTH').label.show.getValue(), true);
  const unsupportedEpoch = new Date(Date.parse(fixture.epoch) + 1).toISOString();
  api.setTime(unsupportedEpoch); assert.equal(primitive.show, false);
  assert.equal(earthBodyAtEpoch(fixture.display, unsupportedEpoch), undefined);
  api.setTime(fixture.epoch); assert.equal(primitive.show, true);
  assert.deepEqual(fixture.display, before);
  api.setResult(undefined); assert.equal(scene.scene.primitives.values.includes(primitive), false);
});

test('unsupported Earth orientation metadata, frame, missing center or nonrotation never draws a body', () => {
  for (const change of [body => { body.status = 'unknown'; }, body => { body.renderer_frame = 'wrong'; }, body => { body.radii_m[0] = 1737400; }, body => { body.orientation_samples[0].rotation_body_fixed_to_renderer_row_major[0] = 3; }]) {
    const { display, epoch } = earthDisplayFixture(); change(display.earth_body); assert.equal(earthBodyAtEpoch(display, epoch), undefined);
  }
  const { display, epoch } = earthDisplayFixture(); display.renderer_states = display.renderer_states.filter(state => state.target !== 'EARTH');
  assert.equal(earthBodyAtEpoch(display, epoch), undefined);
});

test('all navigation actions move a real Cesium camera without changing source state or time; zoom stays bounded', () => {
  for (const distance of [1800000, 4000000, 800000000]) {
    for (const action of ['zoom-in', 'zoom-out', 'pan-left', 'pan-right', 'pan-up', 'pan-down', 'rotate-left', 'rotate-right', 'tilt-up', 'tilt-down']) {
      const scene = { drawingBufferWidth: 800, drawingBufferHeight: 500, mapProjection: new Cesium.GeographicProjection(Cesium.Ellipsoid.MOON), mode: Cesium.SceneMode.SCENE3D, requestRender() {} };
      const camera = new Cesium.Camera(scene);
      camera.setView({ destination: new Cesium.Cartesian3(distance, 0, 0), orientation: { direction: new Cesium.Cartesian3(-1, 0, 0), up: Cesium.Cartesian3.UNIT_Z } });
      const source = result(), snapshot = structuredClone(source), clock = { epoch: source.epochs_utc[0] };
      const viewer = { camera, scene, trackedEntity: {}, clock };
      camera.lookAtTransform(Cesium.Matrix4.fromTranslation(new Cesium.Cartesian3(100, 0, 0)));
      assert.equal(navigateCamera(Cesium, viewer, action), true, `${distance}: ${action}`);
      assert.equal(viewer.trackedEntity, undefined);
      assert.ok(Cesium.Matrix4.equals(camera.transform, Cesium.Matrix4.IDENTITY));
      assert.deepEqual(source, snapshot); assert.equal(clock.epoch, source.epochs_utc[0]);
      for (let i = 0; i < 100; i++) navigateCamera(Cesium, viewer, 'zoom-in');
      assert.ok(Cesium.Cartesian3.magnitude(camera.positionWC) >= 1747400);
      for (let i = 0; i < 100; i++) navigateCamera(Cesium, viewer, 'zoom-out');
      assert.ok(Cesium.Cartesian3.magnitude(camera.positionWC) <= 2e9);
    }
  }
});

test('unavailable network and site views cannot replace the last successful reset preset', async t => {
  const previous = globalThis.matchMedia; globalThis.matchMedia = () => ({ matches: true }); t.after(() => { globalThis.matchMedia = previous; });
  const { api, scene } = await displayHarness(t, true);
  api.camera('global');
  const globalPosition = Cesium.Cartesian3.clone(scene.camera.positionWC);
  api.camera('network'); api.camera('site');
  assert.equal(api.navigate('pan-left'), true);
  assert.equal(api.navigate('reset'), true);
  assert.ok(Cesium.Cartesian3.equalsEpsilon(globalPosition, scene.camera.positionWC, 1e-12, 1e-5));
});

test('close spacecraft following uses its stored current position to scale manual zoom without crossing it', () => {
  const scene = { drawingBufferWidth: 800, drawingBufferHeight: 500, mapProjection: new Cesium.GeographicProjection(Cesium.Ellipsoid.MOON), mode: Cesium.SceneMode.SCENE3D, requestRender() {} };
  const camera = new Cesium.Camera(scene), point = new Cesium.Cartesian3(1800000, 0, 0);
  camera.setView({ destination: new Cesium.Cartesian3(1801000, 0, 0), orientation: { direction: new Cesium.Cartesian3(-1, 0, 0), up: Cesium.Cartesian3.UNIT_Z } });
  const epoch = Cesium.JulianDate.fromIso8601('2026-04-01T00:00:00Z'), snapshot = Cesium.JulianDate.clone(epoch);
  const position = new Cesium.ConstantPositionProperty(point), source = Cesium.Cartesian3.clone(position.getValue(epoch));
  const viewer = { camera, scene, clock: { currentTime: epoch }, trackedEntity: { position } };
  const before = Cesium.Cartesian3.distance(camera.positionWC, point);
  assert.equal(navigateCamera(Cesium, viewer, 'zoom-in', Cesium.Cartesian3.ZERO), true);
  const after = Cesium.Cartesian3.distance(camera.positionWC, point);
  assert.ok(after < before && after >= before * 0.8);
  assert.ok(camera.positionWC.x > point.x);
  assert.equal(viewer.trackedEntity, undefined);
  assert.ok(Cesium.JulianDate.equals(epoch, snapshot));
  assert.ok(Cesium.Cartesian3.equals(position.getValue(epoch), source));
});

test('manual navigation releases follow and reset restores the last network fit without Earth/station history paths', async t => {
  const previous = globalThis.matchMedia; globalThis.matchMedia = () => ({ matches: true }); t.after(() => { globalThis.matchMedia = previous; });
  const read = name => JSON.parse(readFileSync(new URL(`../../web/fixtures/physical-south-pole/relay-later/${name}.json`, import.meta.url)));
  const { api, scene } = await displayHarness(t, true);
  const scenario = read('scenario'), display = read('display-data'), state = display.renderer_states[0];
  display.renderer_states.push({ ...state, target: 'EARTH', position: [380000000, 0, 0] }, { ...state, target: scenario.station_refs[0], position: [380001000, 0, 0] });
  const window = { start_utc: state.epoch, end_utc: new Date(Date.parse(state.epoch) + 1000).toISOString() };
  display.contacts = [{ contact_id: 'earth-allocation', sender: scenario.lander.id, receiver: scenario.station_refs[0], source_transmit_window: window }];
  display.allocations = [{ contact_id: 'earth-allocation', source_transmit_interval: window }];
  api.setDelivery({ scenario, display }); api.setTime(state.epoch); api.camera('network');
  const position = Cesium.Cartesian3.clone(scene.camera.positionWC), direction = Cesium.Cartesian3.clone(scene.camera.directionWC);
  assert.equal(scene.entities.getById('delivery-path-EARTH'), undefined);
  assert.equal(scene.entities.getById(`delivery-path-${scenario.station_refs[0]}`), undefined);
  assert.equal(scene.entities.getById(`delivery-path-${scenario.relay_refs[0]}`).polyline.show.getValue(), false);
  scene.trackedEntity = scene.entities.getById(`delivery-node-${scenario.relay_refs[0]}`);
  assert.equal(api.navigate('pan-left'), true); assert.equal(scene.trackedEntity, undefined);
  api.setTime(state.epoch);
  assert.equal(scene.entities.getById(`delivery-path-${scenario.relay_refs[0]}`).polyline.show.getValue(), false);
  assert.equal(scene.entities.getById(`delivery-node-${scenario.station_refs[0]}`).label.show.getValue(), true);
  assert.equal(scene.entities.getById('delivery-node-EARTH').show, false);
  assert.equal(scene.entities.getById(`delivery-node-${scenario.relay_refs[0]}`).show, false);
  const lander = scene.entities.getById(`delivery-surface-${scenario.lander.id}`);
  assert.equal(lander.label.show.getValue(), true);
  display.contacts[0].sender = scenario.relay_refs[0];
  api.setTime(state.epoch);
  assert.equal(scene.entities.getById(`delivery-node-${scenario.relay_refs[0]}`).show, true);
  assert.equal(scene.entities.getById(`delivery-node-${scenario.relay_refs[0]}`).label.show.getValue(), true);
  assert.equal(lander.label.show.getValue(), false);
  api.camera('moon-network');
  assert.equal(lander.label.show.getValue(), true);
  api.camera('network'); api.navigate('pan-right'); api.setTime(state.epoch);
  assert.equal(lander.label.show.getValue(), false);
  assert.equal(scene.entities.getById(`delivery-node-${scenario.relay_refs[0]}`).label.show.getValue(), true);
  assert.equal(api.navigate('reset'), true);
  assert.ok(Cesium.Cartesian3.equalsEpsilon(position, scene.camera.positionWC, 1e-12, 1e-5));
  assert.ok(Cesium.Cartesian3.equalsEpsilon(direction, scene.camera.directionWC, 1e-12, 1e-8));
});

test('network scale labels keep Earth readable and lunar-hop fit retains exact endpoint positions', async t => {
  const read = name => JSON.parse(readFileSync(new URL(`../../web/fixtures/physical-south-pole/relay-later/${name}.json`, import.meta.url)));
  const { api, scene } = await displayHarness(t);
  const scenario = read('scenario'), display = read('display-data');
  const epoch = display.renderer_states[0].epoch;
  const relay = display.renderer_states[0];
  display.renderer_states.push({ ...relay, target: 'EARTH', position: [380000000, 0, 0] });
  display.renderer_states.push({ ...relay, target: scenario.station_refs[0], position: [380000000, 1000, 0] });
  const window = { start_utc: epoch, end_utc: new Date(Date.parse(epoch) + 1000).toISOString() };
  display.contacts = [{ contact_id: 'selected', sender: scenario.lander.id, receiver: scenario.relay_refs[0], source_transmit_window: window },
    { contact_id: 'unused-earth', sender: scenario.lander.id, receiver: 'EARTH', source_transmit_window: window }];
  display.allocations = [{ contact_id: 'selected', source_transmit_interval: window }];
  api.setDelivery({ scenario, display }); api.setTime(epoch); api.camera('network');
  const earth = scene.entities.getById('delivery-node-EARTH');
  const station = scene.entities.getById(`delivery-node-${scenario.station_refs[0]}`);
  const relayNode = scene.entities.getById(`delivery-node-${scenario.relay_refs[0]}`);
  assert.equal(earth.label.show.getValue(), true);
  assert.equal(station.label.show.getValue(), false);
  assert.equal(relayNode.label.show.getValue(), false);
  assert.equal(earth.label.text.getValue(), 'Earth network · educational stations');
  api.camera('moon-network');
  assert.equal(relayNode.label.show.getValue(), true);
  assert.equal(station.label.show.getValue(), false);
  assert.ok(Cesium.Cartesian3.magnitude(scene.camera.lastView.destination) > scenario.lander.reference_radius_m);
  assert.ok([scene.camera.lastView.orientation.up.x, scene.camera.lastView.orientation.up.y, scene.camera.lastView.orientation.up.z].every(Number.isFinite));
  assert.ok(scene.entities.getById('delivery-link-selected'));
  assert.equal(scene.entities.getById('delivery-link-unused-earth'), undefined);
  assert.deepEqual(display.renderer_states[0], relay);
});

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
