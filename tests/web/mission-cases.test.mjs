import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { canonicalScenarioHash, validateResult } from '../../web/src/contracts.js';
import { validateDisplayPayload } from '../../web/src/display.js';
import { missionCases, missionCaseFromUrl, missionOutcome, controlledTestExplanation, hasRelayFocus, relayFocusEpoch } from '../../web/src/mission-cases.js';

test('mission case URLs resolve only available captured identities', () => {
  const ids = missionCases.map(item => item.id);
  for (const id of ids) assert.equal(missionCaseFromUrl(`?case=${id}`, ids), id);
  assert.equal(missionCaseFromUrl('?case=unavailable', ids), 'direct-ready');
  assert.equal(missionCaseFromUrl('', ids), 'direct-ready');
});

test('physical mission sensitivity captures preserve unknown outcomes, exact packages and distinct hashes', async () => {
  const evidencePath = '../../web/fixtures/demo-constraints/demonstration.json';
  const evidenceBytes = await readFile(new URL(evidencePath, import.meta.url));
  assert.deepEqual(evidenceBytes, await readFile(new URL('../../fixtures/demo-constraints/demonstration.json', import.meta.url)));
  const evidence = JSON.parse(evidenceBytes);
  const hashes = [];
  const baseline = JSON.parse(await readFile(new URL('../../web/fixtures/physical-south-pole/relay-later/scenario.json', import.meta.url), 'utf8'));
  for (const id of ['battery-low', 'service-off']) {
    const prefix = new URL(`../../web/fixtures/demo-constraints/${id}/`, import.meta.url);
    const json = async file => JSON.parse(await readFile(new URL(file, prefix), 'utf8'));
    const scenario = await json('scenario.json'), result = await json('result.json'), display = await json('display-data.json');
    const hash = await canonicalScenarioHash(scenario); hashes.push(hash);
    assert.equal(result.scenario_sha256, hash);
    assert.equal(validateResult(result).valid, true);
    assert.equal(result.status, 'unknown');
    assert.equal(result.solver_status, 'unresolved');
    assert.equal(result.delivered_bytes, null);
    assert.equal(scenario.analysis_mode, 'terrain_ephemeris');
    for (const field of ['data_volume', 'lander', 'data_ready_utc', 'deadline_utc', 'analysis_horizon', 'route_families']) assert.deepEqual(scenario[field], baseline[field]);
    assert.equal(validateDisplayPayload(display, hash, result).scenario_sha256, hash);
    assert.ok(display.renderer_states.length > 0);
    assert.equal(display.environment.scenario_sha256, hash);
    const controlled = evidence.cases.find(item => item.case_id === id);
    assert.match(controlledTestExplanation(controlled, id, result), /Baseline-schedule counterfactual replay/);
    assert.equal(controlledTestExplanation(controlled, 'other', result), '');
    assert.equal(controlledTestExplanation(controlled, id, { ...result, scenario_sha256: 'other' }), '');
    assert.deepEqual(await readFile(new URL('run.zip', prefix)), await readFile(new URL(`../../fixtures/demo-constraints/${id}/run.zip`, import.meta.url)));
  }
  assert.notEqual(hashes[0], hashes[1]);
});

test('mission outcome uses only matching native result and summary', () => {
  const result = { status: 'infeasible_in_model', scenario_sha256: 'a', delivered_bytes: 0,
    final_byte_arrival_utc: null, provenance: { reason: 'Native engine reason' } };
  assert.equal(controlledTestExplanation(undefined, undefined, result), '');
  assert.match(missionOutcome(result, { scenario_sha256: 'other', limiting_reason: 'Wrong case' }), /Native engine reason/);
  assert.doesNotMatch(missionOutcome(result, { scenario_sha256: 'other', limiting_reason: 'Wrong case' }), /Wrong case/);
  assert.match(missionOutcome(result, { scenario_sha256: 'a', limiting_reason: 'Exact bound' }), /Exact bound/);
  assert.equal(hasRelayFocus({ sample_epochs_utc: [relayFocusEpoch], renderer_states: [{ epoch: relayFocusEpoch }] }), true);
  assert.equal(hasRelayFocus({ sample_epochs_utc: [relayFocusEpoch], renderer_states: [] }), false);
  assert.equal(hasRelayFocus({ sample_epochs_utc: ['2026-11-30T09:33:00Z'] }), false);
  assert.match(missionOutcome({ ...result, status: 'unknown', delivered_bytes: null }), /Delivered: Unknown bytes. Last byte: Unknown/);
});
