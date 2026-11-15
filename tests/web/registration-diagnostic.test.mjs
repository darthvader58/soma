import test from 'node:test';
import assert from 'node:assert/strict';
import { validateProbeRequest, diagnosticRepresentation } from '../../web/src/registration-diagnostic.js';

test('corrected diagnostic is explicit and development-only', () => {
  assert.equal(diagnosticRepresentation('', false), 'unmodified_asset');
  assert.equal(diagnosticRepresentation('?representation=registered', true), 'engine_corrected_mesh');
  assert.throws(() => diagnosticRepresentation('?representation=registered', false));
  assert.throws(() => diagnosticRepresentation('?representation=candidate', true));
});

const request = () => ({ format_version: '0.1.0', request_id: 'reference-probes', source_frame: 'MOON_ME_DE421',
  candidate_bridge: 'identity_for_measurement_only', probes: [{ id: 'a', position_m: [1737400, 0, 0] }] });

test('raw-mesh request is detached and explicitly unregistered', () => {
  const input = request(); const accepted = validateProbeRequest(input);
  input.probes[0].position_m[0] = 1;
  assert.equal(accepted.probes[0].position_m[0], 1737400);
  assert.equal(accepted.candidate_bridge, 'identity_for_measurement_only');
});

test('invalid identities, coordinates and excessive work cannot start a measurement', () => {
  for (const change of [
    r => { r.candidate_bridge = 'registered'; },
    r => { r.source_frame = 'IAU_MOON'; },
    r => { r.probes.push(structuredClone(r.probes[0])); },
    r => { r.probes[0].position_m[0] = Infinity; },
    r => { r.probes[0].position_m = [6378137, 0, 0]; },
    r => { r.probes = Array.from({ length: 4097 }, (_, i) => ({ id: String(i), position_m: [1737400, 0, 0] })); },
  ]) { const input = request(); change(input); assert.throws(() => validateProbeRequest(input)); }
});
