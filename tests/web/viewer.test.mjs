import test from 'node:test';
import assert from 'node:assert/strict';
import { registrationGate, isMoonSurfacePick, createMoonViewer } from '../../web/src/viewer.js';

test('missing engine registration blocks aligned overlays', () => {
  assert.equal(registrationGate().passed, false);
  assert.equal(registrationGate({ version: 'identity' }).passed, false);
});

test('an identity label cannot bypass missing landmarks or exceeded residuals', () => {
  const evidence = {
    version: 'synthetic-gate-test-only', authority: 'soma_engine',
    source_frame: 'MOON_ME_DE421', renderer_frame: 'SOMA_MOON_ME_DE421_CORRECTED_V1',
    representation: 'engine_corrected_mesh', conversion_manifest_sha256: 'b'.repeat(64),
    certified_region: { latitude_deg: [-90, -87.5], longitude_deg_east: [-180, 180] },
    release_gate: { overlays_allowed: true, map_registration_passed: true },
    asset_id: 2684829, source_manifest_sha256: 'a'.repeat(64),
    transform_column_major: [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
    tolerance_m: 10, tolerance_justification: 'Synthetic display-gate test only',
    landmarks: Array.from({ length: 4 }, (_, index) => ({
      id: `synthetic-${index}`, source_ref: 'synthetic-test',
      residual_m: 1, horizontal_grid_resolution_allowance_m: 3.54, resolution_adjusted_residual_m: 4.54,
      renderer_position_m: [index, 0, 0], analysis_position_m: [index, 0, 1],
    })),
    distribution_review: { accepted: true, evidence_ref: 'synthetic-review-test' },
  };
  assert.equal(registrationGate(evidence).passed, true);
  assert.equal(registrationGate(evidence, 'OTHER_FRAME').passed, false);
  const corrupt = structuredClone(evidence);
  corrupt.landmarks[3].residual_m = 11;
  assert.equal(registrationGate(corrupt).passed, false);
  corrupt.landmarks[3].residual_m = 1;
  corrupt.landmarks[3].resolution_adjusted_residual_m = 11;
  assert.equal(registrationGate(corrupt).passed, false);
  corrupt.landmarks[3].resolution_adjusted_residual_m = 4.54;
  corrupt.distribution_review.accepted = false;
  assert.equal(registrationGate(corrupt).passed, false);
  corrupt.distribution_review.accepted = true;
  corrupt.landmarks.pop();
  assert.equal(registrationGate(corrupt).passed, false);
});

test('sky, unrelated objects, and absent depth cannot select lunar surface', () => {
  const moon = {};
  assert.equal(isMoonSurfacePick(undefined, moon, true), false);
  assert.equal(isMoonSurfacePick({ primitive: {} }, moon, true), false);
  assert.equal(isMoonSurfacePick({ primitive: moon }, moon, false), false);
  assert.equal(isMoonSurfacePick({ primitive: moon }, moon, true), true);
});

test('missing token produces a readable fallback without importing Cesium', async () => {
  const node = () => ({ children: [], append(...children) { this.children.push(...children); } });
  const container = { ...node(), ownerDocument: { createElement: node }, replaceChildren() { this.children = []; } };
  const statuses = [];
  const viewer = await createMoonViewer(container, { onStatus: (status) => statuses.push(status) });
  assert.equal(statuses.at(-1).state, 'fallback');
  assert.equal(statuses.at(-1).overlaysBlocked, true);
  assert.match(container.children[0].children[1].textContent, /coordinate fields/);
  viewer.setTime('2026-11-14T00:00:00Z');
  viewer.setScenario({});
  viewer.destroy();
  assert.equal(container.children.length, 0);
});
