import test from 'node:test';
import assert from 'node:assert/strict';
import { describeStatus, formatValue } from '../../web/src/result.js';

test('unknown delivery quantities stay distinct from computed zero', () => {
  assert.equal(formatValue(null, 'bytes'), 'Unknown');
  assert.equal(formatValue(undefined, 'Wh'), 'Unknown');
  assert.equal(formatValue(0, 'bytes'), '0 bytes');
  assert.equal(formatValue(104857600, 'bytes'), '104,857,600 bytes');
});

test('feasibility never removes assumed-rate fidelity or incumbent qualification', () => {
  const summary = describeStatus({ status: 'feasible_under_assumptions', solver_status: 'feasible_incumbent', model_fidelity: 'assumed_rate_simulation' });
  assert.equal(summary.label, 'Feasible under assumptions');
  assert.equal(summary.solver, 'feasible_incumbent');
  assert.equal(summary.fidelity, 'assumed_rate_simulation');
  assert.notEqual(summary.label, describeStatus({ status: 'infeasible_in_model' }).label);
  assert.notEqual(summary.label, describeStatus({ status: 'unknown' }).label);
});

test('exact fractional UTC timestamps remain source strings', () => {
  assert.equal(formatValue('2026-11-14T10:01:23.88608Z'), '2026-11-14T10:01:23.88608Z');
});

test('structured explanation preserves endpoint identity and exact source/receiver timestamps', async () => {
  const { explainResult } = await import('../../web/src/result.js');
  const explanation = explainResult({
    provenance: { reason: 'Synthetic hand-checkable model output.' },
    contacts: [{ contact_id: 'hop', sender: 'lander', receiver: 'specific-earth-station' }],
    allocations: [{ contact_id: 'hop', chunk_id: 'file-a', byte_offset: 16, byte_length: 32,
      source_transmit_interval: { start_utc: '2026-11-14T10:00:00Z', end_utc: '2026-11-14T10:01:23.88608Z' },
      receiver_occupancy_interval: { start_utc: '2026-11-14T10:00:01.3Z', end_utc: '2026-11-14T10:01:25.18608Z' },
      byte_available_utc: '2026-11-14T10:01:25.18608Z' }],
    storage_intervals: [{ node_id: 'lunar-relay', chunk_id: 'file-a', byte_length: 32,
      interval: { start_utc: '2026-11-14T09:00:00Z', end_utc: '2026-11-14T10:00:00Z' } }],
    delivered_bytes: 32, final_byte_arrival_utc: '2026-11-14T10:01:25.18608Z',
    summary: { reason: 'UNAPPROVED PHYSICS STORY' },
  });
  const text = explanation.join('\n');
  assert.match(text, /lander to specific-earth-station/);
  assert.match(text, /byte offset 16/);
  assert.match(text, /10:01:23\.88608Z/);
  assert.match(text, /receiver payload occupancy.*10:01:25\.18608Z/);
  assert.match(text, /lunar-relay stores 32 bytes/);
  assert.doesNotMatch(text, /UNAPPROVED/);
});

test('missing structured explanation remains unknown rather than inferring failure cause', async () => {
  const { explainResult } = await import('../../web/src/result.js');
  const text = explainResult({ status: 'infeasible_in_model', delivered_bytes: null, final_byte_arrival_utc: null }).join(' ');
  assert.match(text, /Unknown/);
  assert.doesNotMatch(text, /battery|blocked|terrain/);
});
