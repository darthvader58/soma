import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { validateScenario, canonicalScenarioHash } from '../../web/src/contracts.js';
import { comparisonViewModel } from '../../web/src/comparison.js';

const load = async (path) => JSON.parse(await readFile(new URL(`../../${path}`, import.meta.url), 'utf8'));

test('physical presets preserve the engine frozen scenario contract byte-for-byte', async () => {
  for (const file of ['scenario.json', 'scenario-later.json']) {
    const original = await readFile(new URL(`../../fixtures/physical-south-pole/${file}`, import.meta.url), 'utf8');
    const copied = await readFile(new URL(`../../web/fixtures/physical-south-pole/${file}`, import.meta.url), 'utf8');
    assert.equal(copied, original);
    const scenario = JSON.parse(copied);
    assert.deepEqual(validateScenario(scenario), { valid: true, errors: [] });
    assert.equal(scenario.analysis_mode, 'terrain_ephemeris');
    assert.equal(scenario.rate_method, 'assumed_net_rate');
    assert.equal(scenario.profiles.relays[0].trajectory.kind, 'synthetic_two_body_lunar_preset');
    assert.equal(scenario.profiles.relays[0].trajectory.reference, 'soma-polar-200km-v1');
    assert.equal(scenario.profiles.hardware[0].battery.initial_energy_wh, 80);
  }
});

test('date presets keep equipment and task fixed while explicitly moving full finite mission windows', async () => {
  const a = await load('web/fixtures/physical-south-pole/scenario.json');
  const b = await load('web/fixtures/physical-south-pole/scenario-later.json');
  assert.notEqual(await canonicalScenarioHash(a), await canonicalScenarioHash(b));
  const comparison = comparisonViewModel([{ scenario: a }, { scenario: b }]);
  assert.equal(comparison.differences.find(item => item.label === 'Hardware configuration').changed, false);
  assert.equal(comparison.differences.find(item => item.label === 'Network configuration').changed, true);
  assert.match(comparison.rows[0].comparisonRule, /six-hour mission-age deadline/);
  for (const key of ['lander', 'data_volume', 'hardware_profile_ref', 'relay_refs', 'station_refs', 'route_families', 'rate_method', 'pointing_assumption', 'service_assumption_label']) {
    assert.deepEqual(a[key], b[key], key);
  }
  for (const scenario of [a, b]) {
    assert.equal(Date.parse(scenario.deadline_utc) - Date.parse(scenario.data_ready_utc), 6 * 3600 * 1000);
    assert.equal(scenario.analysis_horizon.start_utc, scenario.data_ready_utc);
    assert.equal(scenario.analysis_horizon.end_utc, scenario.deadline_utc);
    for (const profile of [...scenario.profiles.hardware, ...scenario.profiles.relays, ...scenario.profiles.stations]) {
      assert.deepEqual(profile.service.windows, [scenario.analysis_horizon]);
      assert.ok(Number.isFinite(profile.storage_capacity_bytes));
    }
    assert.deepEqual(scenario.profiles.relays[0].trajectory.coverage, scenario.analysis_horizon);
  }
});
