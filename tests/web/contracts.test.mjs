import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { validateScenario, validateResult, canonicalScenarioHash } from '../../web/src/contracts.js';

const read = name => JSON.parse(readFileSync(new URL(`../../${name}`, import.meta.url), 'utf8'));
const root = fileURLToPath(new URL('../../', import.meta.url));
const python = process.env.SOMA_PYTHON || `${root}.venv/bin/python`;
const capture = name => JSON.parse(execFileSync(python, ['-m', 'soma', 'validate', `fixtures/${name}/scenario.json`], { cwd: root, encoding: 'utf8' }));

for (const name of ['synthetic-direct', 'synthetic-relay']) {
  test(`${name} validates and hashes identically in Python and browser`, async () => {
    const scenario = read(`fixtures/${name}/scenario.json`);
    const result = read(`web/fixtures/${name}/result.json`);
    const validated = capture(name);
    assert.deepEqual(validateScenario(scenario), { valid: true, errors: [] });
    assert.equal(validateResult(result).valid, true);
    assert.equal(await canonicalScenarioHash(scenario), result.scenario_sha256);
    assert.equal(validated.scenario_sha256, result.scenario_sha256);
    for (const property of ['status', 'solver_status', 'model_fidelity']) {
      const broken = structuredClone(result);
      delete broken[property];
      assert.equal(validateResult(broken).valid, false);
    }
    const unknown = { ...result, status: 'unknown', solver_status: 'unresolved', model_fidelity: 'not_implemented',
      delivered_bytes: null, final_byte_arrival_utc: null, contacts: [], allocations: [], storage_intervals: [], energy_history: [], buffer_history: [],
      provenance: { ...result.provenance, implementation_status: 'not_implemented' } };
    assert.equal(validateResult(unknown).valid, true);
    const fabricated = { ...unknown, delivered_bytes: 0 };
    assert.equal(validateResult(fabricated).valid, false);
  });
}

test('required heights, finite storage, explicit units, UTC and frame cannot be omitted', () => {
  const original = read('fixtures/synthetic-relay/scenario.json');
  for (const key of ['antenna_height_m', 'panel_height_m', 'frame', 'reference_radius_m']) {
    const scenario = structuredClone(original);
    delete scenario.lander[key];
    assert.equal(validateScenario(scenario).valid, false, key);
  }
  const scenario = structuredClone(original);
  delete scenario.profiles.relays[0].storage_capacity_bytes;
  assert.equal(validateScenario(scenario).valid, false);
  scenario.profiles.relays[0].storage_capacity_bytes = 104857600;
  scenario.data_volume = 100;
  assert.equal(validateScenario(scenario).valid, false);
  scenario.data_volume = original.data_volume;
  scenario.data_ready_utc = '2026-11-14T08:50:00';
  assert.equal(validateScenario(scenario).valid, false);
});

test('JCS hashes agree across Unicode, negative zero, exponent and ordering cases', async () => {
  for (const vector of read('fixtures/hash-vectors.json')) assert.equal(await canonicalScenarioHash(vector.input), vector.sha256);
  const vectors = [{ b: 1, a: 0.000001, text: 'Lune é 🌕' }, { '\ue000': 2, '😀': 1, nested: { z: -0, a: 1e-7 } }];
  for (const vector of vectors) {
    const expected = execFileSync(python, ['-c', 'import json,sys; from soma.validation import scenario_sha256; print(scenario_sha256(json.loads(sys.argv[1])))', JSON.stringify(vector)], { cwd: root, encoding: 'utf8' }).trim();
    assert.equal(await canonicalScenarioHash(vector), expected);
  }
  for (const value of [Infinity, NaN, 9007199254740992, '\ud800', undefined]) await assert.rejects(canonicalScenarioHash({ value }));
});
