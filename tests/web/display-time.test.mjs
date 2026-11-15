import test from 'node:test';
import assert from 'node:assert/strict';
import { sameDisplayEpoch } from '../../web/src/display-time.js';

test('display record matching preserves microseconds and treats explicit offsets as the same instant', () => {
  assert.equal(sameDisplayEpoch('2026-11-14T10:05:00.123456+02:00', '2026-11-14T08:05:00.123456Z'), true);
  assert.equal(sameDisplayEpoch('2026-11-14T08:05:00.123456Z', '2026-11-14T08:05:00.123457Z'), false);
  assert.equal(sameDisplayEpoch('2026-11-14T08:05:00.123Z', '2026-11-14T08:05:00.123000Z'), true);
  assert.equal(sameDisplayEpoch('2026-11-14T08:05:00', '2026-11-14T08:05:00Z'), false);
});
