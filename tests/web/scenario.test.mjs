import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { patchScenario, scenarioProvenance } from '../../web/src/scenario.js';

const fixture = JSON.parse(await readFile(new URL('../../fixtures/synthetic-relay/scenario.json', import.meta.url)));

test('coordinate and height edits preserve embedded resource limits, units and assumptions', () => {
  let next = patchScenario(fixture, 'lander.latitude_deg', -88.3);
  next = patchScenario(next, 'lander.antenna_height_m', 3);
  assert.equal(next.lander.latitude_deg, -88.3);
  assert.equal(next.lander.antenna_height_m, 3);
  assert.equal(next.lander.panel_height_m, 1);
  assert.equal(fixture.lander.antenna_height_m, 2);
  const expected = structuredClone(fixture);
  expected.lander.latitude_deg = -88.3;
  expected.lander.antenna_height_m = 3;
  assert.deepEqual(JSON.parse(JSON.stringify(next)), expected);
});

test('route and relay references can change without deleting declared profiles', () => {
  const direct = patchScenario(patchScenario(fixture, 'route_families', ['direct_to_earth']), 'relay_refs', []);
  assert.deepEqual(direct.profiles, fixture.profiles);
  assert.deepEqual(direct.relay_refs, []);
  assert.deepEqual(fixture.relay_refs, ['synthetic-lunar-relay']);
  assert.equal(direct.profiles.relays[0].storage_capacity_bytes, 104857600);
});

test('qualified epochs round trip exactly and edits cannot introduce undocumented fields', () => {
  const epoch = '2026-11-14T02:00:00.123456-07:00';
  assert.equal(patchScenario(fixture, 'data_ready_utc', epoch).data_ready_utc, epoch);
  assert.throws(() => patchScenario(fixture, 'battery.capacity', 1000), /Unknown scenario field/);
  assert.throws(() => patchScenario(fixture, 'lander.solar_hour', 12), /Unknown scenario field/);
});

test('physical scenario provenance preserves input classes and synthetic trajectory labels', () => {
  const scenario = structuredClone(fixture);
  scenario.analysis_mode = 'terrain_ephemeris';
  scenario.profiles.relays[0].trajectory.kind = 'synthetic_two_body_lunar_preset';
  const provenance = scenarioProvenance(scenario);
  assert.equal(provenance.mode, 'terrain_ephemeris');
  assert.equal(provenance.rate, 'assumed_net_rate');
  assert.deepEqual(provenance.inputs, scenario.input_provenance);
  assert.equal(provenance.relays[0].trajectory, 'synthetic_two_body_lunar_preset');
  assert.deepEqual(provenance.relays[0].coverage, scenario.profiles.relays[0].trajectory.coverage);
  scenario.relay_refs = [];
  assert.deepEqual(scenarioProvenance(scenario).relays, []);
});
