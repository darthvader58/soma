import test from 'node:test';
import assert from 'node:assert/strict';
import { rendererSamplesAtTime } from '../../web/src/renderer-samples.js';

const epoch = '2026-11-24T08:00:00.123456Z';
const frame = 'SOMA_MOON_ME_DE421_CORRECTED_V1';
test('links use Python antenna positions and prefer exact registered lander endpoint states', () => {
  const value = display();
  value.surface_points[0].antenna_position_m = [4, 5, 6];
  assert.deepEqual(rendererSamplesAtTime(value, epoch, ['relay']).links[0].positions[0], [4, 5, 6]);
  value.renderer_states.push({ ...value.renderer_states[0], target: 'lander', position: [7, 8, 9] });
  assert.deepEqual(rendererSamplesAtTime(value, epoch, ['lander', 'relay']).links[0].positions[0], [7, 8, 9]);
});
function display() {
  return {
    registration: { renderer_frame: frame, source_frame: 'MOON_ME_DE421' },
    renderer_states: [{ target: 'relay', frame, source_frame: 'MOON_ME_DE421', origin: 'MOON', position_unit: 'm',
      epoch, epoch_format: 'rfc3339', time_scale: 'UTC', position: [10, 20, 30],
      transform_epoch_utc: epoch, transform_ref: 'renderer-registration.json', provenance_label: 'synthetic_two_body_lunar_preset' }],
    surface_points: [{ id: 'lander', frame, origin: 'MOON', position_unit: 'm', epoch: null, time_scale: 'static', position_m: [1, 2, 3] }],
    contacts: [{ contact_id: 'c', sender: 'lander', receiver: 'relay', source_transmit_window: { start_utc: epoch, end_utc: '2026-11-24T08:01:00Z' } }],
    allocations: [{ contact_id: 'c', source_transmit_interval: { start_utc: epoch, end_utc: '2026-11-24T08:00:00.123457Z' } }],
  };
}

test('renderer uses only exact engine-transformed samples with complete source and transform provenance', () => {
  const value = display();
  assert.deepEqual(rendererSamplesAtTime(value, '2026-11-24T10:00:00.123456+02:00', ['relay']).states, value.renderer_states);
  assert.equal(rendererSamplesAtTime(value, '2026-11-24T08:00:00.123457Z', ['relay']).states.length, 0);
  for (const key of ['frame', 'source_frame', 'origin', 'position_unit', 'epoch_format', 'time_scale', 'transform_ref', 'transform_epoch_utc', 'provenance_label']) {
    const changed = display(); changed.renderer_states[0][key] = key === 'provenance_label' ? '' : 'wrong';
    assert.equal(rendererSamplesAtTime(changed, epoch, ['relay']).states.length, 0, key);
  }
  assert.equal(rendererSamplesAtTime(value, epoch, []).states.length, 0);
});

test('available contacts and scheduled transmissions stay separate and no Earth endpoint is invented', () => {
  const value = display();
  let sample = rendererSamplesAtTime(value, epoch, ['relay']);
  assert.equal(sample.links.length, 1);
  assert.deepEqual(sample.links[0].positions, [[1, 2, 3], [10, 20, 30]]);
  assert.equal(sample.links[0].allocation.contact_id, 'c');
  value.allocations = [];
  assert.equal(rendererSamplesAtTime(value, epoch, ['relay']).links[0].allocation, undefined);
  value.contacts[0].receiver = 'earth-station';
  assert.deepEqual(rendererSamplesAtTime(value, epoch, ['relay']).links, []);
  value.contacts[0].receiver = 'relay';
  value.contacts[0].source_transmit_window.end_utc = epoch;
  assert.deepEqual(rendererSamplesAtTime(value, epoch, ['relay']).links, []);
});
