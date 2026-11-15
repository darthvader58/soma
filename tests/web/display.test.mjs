import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { displayAtTime, displayTimeText, validateDisplayPayload } from '../../web/src/display.js';

const result = JSON.parse(readFileSync(new URL('../../web/fixtures/synthetic-relay/result.json', import.meta.url), 'utf8'));
function display() {
  return { ...structuredClone(result), artifact_type: 'soma_display_payload', format_version: '0.5.0',
    interpolation: 'none_unknown_between_samples', states: [], sample_epochs_utc: [], environment: null,
    state_unavailable_reasons: ['no_stored_trajectory_states'] };
}

test('display preserves all completed result intervals, metrics and provenance', () => {
  const value = display();
  assert.equal(validateDisplayPayload(value, result.scenario_sha256, result), value);
  for (const key of ['format_version', 'scenario_sha256', 'run_version', 'interpolation']) {
    assert.throws(() => validateDisplayPayload({ ...value, [key]: 'wrong' }, result.scenario_sha256, result), /unsupported|differs/);
  }
  const changed = display();
  changed.allocations[0].source_transmit_interval.end_utc = '2026-11-14T12:00:00Z';
  assert.throws(() => validateDisplayPayload(changed, result.scenario_sha256, result), /allocations differs/);
  assert.throws(() => validateDisplayPayload({ ...value, environment: { scenario_sha256: '0'.repeat(64) } }, result.scenario_sha256, result), /environment does not match/);
});

test('selected time exposes only exact samples, retaining zero and unknown', () => {
  const value = display();
  value.energy_history = [{ node_id: 'lander', epoch_utc: '2026-11-14T09:00:00.123456Z', stored_energy_wh: 0 }];
  value.buffer_history = [{ node_id: 'relay', epoch_utc: '2026-11-14T09:00:00.123456Z', stored_bytes: null }];
  const exact = displayAtTime(value, '2026-11-14T11:00:00.123456+02:00');
  assert.equal(exact.energy[0].stored_energy_wh, 0);
  assert.equal(exact.buffers[0].stored_bytes, null);
  assert.equal(exact.state_status, 'unknown');
  assert.equal(displayAtTime(value, '2026-11-14T09:00:00.123457Z').energy.length, 0);
  assert.match(displayTimeText(value, '2026-11-14T09:00:00.123456Z'), /lander: 0 Wh.*relay: Unknown bytes/);
  assert.match(displayTimeText(value, '2026-11-14T09:00:00.123457Z'), /no exact stored energy sample/);
  assert.match(displayTimeText(undefined, '2026-11-14T09:00:00Z'), /No matching completed-job/);
});

test('stored spacecraft sample retains reference metadata and never extends coverage', () => {
  const value = display();
  value.states = [{ target: 'synthetic-relay', origin: 'MOON', frame: 'MOON_ME_DE421',
    epoch: '2026-11-14T09:00:00Z', epoch_format: 'rfc3339', time_scale: 'UTC',
    position: [1, 2, 3], position_unit: 'm', provenance_label: 'synthetic test only' }];
  validateDisplayPayload(value, result.scenario_sha256, result);
  assert.deepEqual(displayAtTime(value, '2026-11-14T09:00:00Z').states, value.states);
  assert.equal(displayAtTime(value, '2026-11-14T09:00:01Z').states.length, 0);
  assert.match(displayTimeText(value, '2026-11-14T09:00:00Z'), /MOON origin, MOON_ME_DE421/);
  delete value.states[0].frame;
  assert.throws(() => validateDisplayPayload(value, result.scenario_sha256, result), /Display state/);
});
