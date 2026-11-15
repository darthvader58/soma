import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createFixtureClient, createPlanClient } from '../../web/src/client.js';

const scenario = JSON.parse(readFileSync(new URL('../../fixtures/synthetic-direct/scenario.json', import.meta.url), 'utf8'));
const root = fileURLToPath(new URL('../../', import.meta.url));
const result = JSON.parse(execFileSync(process.env.SOMA_PYTHON || `${root}.venv/bin/python`, ['-m', 'soma', 'plan', 'fixtures/synthetic-direct/scenario.json'], { cwd: root, encoding: 'utf8' }));
const response = value => ({ ok: true, status: 200, json: async () => value });
const completed = { status: 'completed', stage: 'complete', scenario_sha256: result.scenario_sha256, result };

test('offline mode returns only captured exact matching scenario', async () => {
  const client = createFixtureClient([{ scenario, result }]);
  assert.deepEqual(await client.plan(scenario), result);
  const changed = structuredClone(scenario);
  changed.lander.antenna_height_m++;
  await assert.rejects(client.plan(changed), /Offline.*exact scenario/);
});

test('live client polls stages and validates the final hash', async () => {
  const stages = [];
  const queue = [{ job_id: 'example' }, { status: 'running', stage: 'validation', scenario_sha256: result.scenario_sha256 }, completed];
  const client = createPlanClient({ baseUrl: 'https://example.invalid', pollIntervalMs: 0, fetchImpl: async () => response(queue.shift()) });
  assert.deepEqual(await client.plan(scenario, { onProgress: value => stages.push(value.stage) }), result);
  assert.deepEqual(stages, ['validation', 'complete']);
});

test('a late response cannot publish after a newer request', async () => {
  let release;
  let firstPosted;
  const firstReached = new Promise(resolve => { firstPosted = resolve; });
  let posts = 0;
  const client = createPlanClient({ fetchImpl: async (_url, options) => {
    if (options.method === 'POST') {
      posts++;
      if (posts === 1) { firstPosted(); return new Promise(resolve => { release = () => resolve(response({ job_id: 'old' })); }); }
      return response({ job_id: 'new' });
    }
    return response(completed);
  } });
  const old = client.plan(scenario);
  const rejected = assert.rejects(old, { name: 'AbortError' });
  await firstReached;
  assert.deepEqual(await client.plan(scenario), result);
  release();
  await rejected;
});

test('cancel aborts the active request and requests service cancellation', async () => {
  let reached;
  const polling = new Promise(resolve => { reached = resolve; });
  const methods = [];
  const client = createPlanClient({ fetchImpl: async (_url, options) => {
    methods.push(options.method || 'GET');
    if (options.method === 'POST') return response({ job_id: 'cancel-me' });
    if (options.method === 'DELETE') return { ok: true, status: 204 };
    reached();
    return new Promise((_resolve, reject) => options.signal.addEventListener('abort', () => reject(new DOMException('Canceled', 'AbortError')), { once: true }));
  } });
  const plan = client.plan(scenario);
  const rejected = assert.rejects(plan, { name: 'AbortError' });
  await polling;
  await client.cancel();
  await rejected;
  assert.deepEqual(methods, ['POST', 'GET', 'DELETE']);
});

test('explicit delayed fixture test can be canceled without publishing a result', async () => {
  const stages = [];
  const client = createFixtureClient([{ scenario, result }], { fixtureDelayMs: 1000 });
  await assert.rejects(client.plan(scenario, { onProgress(progress) {
    stages.push(progress.stage);
    assert.match(progress.message, /no scientific computation/);
    client.cancel();
  } }), { name: 'AbortError' });
  assert.deepEqual(stages, ['delayed_fixture_test']);
  await assert.rejects(client.exportRun(scenario), /No completed/);
  await assert.rejects(client.retry(), /No failed immutable/);
});

test('late accepted POST is deleted as an orphan and cannot publish progress', async () => {
  let release, reached;
  const posting = new Promise(resolve => { reached = resolve; });
  const deleted = [], published = [];
  const client = createPlanClient({ fetchImpl: async (url, options) => {
    if (options.method === 'POST') { reached(); return new Promise(resolve => { release = () => resolve(response({ job_id: 'late-post' })); }); }
    if (options.method === 'DELETE') { deleted.push(url); return { ok: true, status: 204 }; }
    throw new Error('Stale job must not poll.');
  } });
  const pending = client.plan(scenario, { onProgress: value => published.push(value) });
  const rejection = assert.rejects(pending, { name: 'AbortError' });
  await posting;
  await client.cancel();
  release();
  await rejection;
  assert.deepEqual(deleted, ['/plans/late-post']);
  assert.deepEqual(published, []);
});

test('superseding an accepted active job deletes it before planning the replacement', async () => {
  let reached;
  const polling = new Promise(resolve => { reached = resolve; });
  let posts = 0;
  const deleted = [];
  const client = createPlanClient({ fetchImpl: async (url, options) => {
    if (options.method === 'POST') return response({ job_id: ++posts === 1 ? 'old-active' : 'replacement' });
    if (options.method === 'DELETE') { deleted.push(url); return { ok: true, status: 204 }; }
    if (url.endsWith('old-active')) {
      reached();
      return new Promise((_resolve, reject) => options.signal.addEventListener('abort', () => reject(new DOMException('Canceled', 'AbortError')), { once: true }));
    }
    return response(completed);
  } });
  const old = client.plan(scenario);
  const rejected = assert.rejects(old, { name: 'AbortError' });
  await polling;
  await client.plan(scenario);
  await rejected;
  assert.deepEqual(deleted, ['/plans/old-active']);
});

test('retry submits the failed detached snapshot and preserves its scenario hash', async () => {
  const mutable = structuredClone(scenario);
  const submissions = [];
  let posts = 0;
  const client = createPlanClient({ fetchImpl: async (_url, options) => {
    if (options.method === 'POST') {
      submissions.push(JSON.parse(options.body));
      if (++posts === 1) throw new Error('Controlled transport failure');
      return response({ job_id: 'retry' });
    }
    return response(completed);
  } });
  await assert.rejects(client.plan(mutable), /Controlled transport failure/);
  mutable.lander.antenna_height_m++;
  const retried = await client.retry();
  assert.deepEqual(submissions, [scenario, scenario]);
  assert.equal(retried.scenario_sha256, result.scenario_sha256);
  assert.ok(Object.isFrozen(retried));
  assert.ok(Object.isFrozen(retried.provenance));
  await client.cancel();
  await assert.rejects(client.retry(), /No failed immutable/);
});

test('live completed run retains job identifier and downloads exact package bytes', async () => {
  const bytes = Uint8Array.from([80, 75, 3, 4, 0, 255, 128, 10]);
  const calls = [];
  const client = createPlanClient({ fetchImpl: async (url, options = {}) => {
    calls.push(url);
    if (options.method === 'POST') return response({ job_id: 'run/id' });
    if (url.endsWith('/export')) return { ok: true, arrayBuffer: async () => bytes.buffer,
      headers: new Headers({ 'X-SOMA-Scenario-SHA256': result.scenario_sha256 }) };
    return response(completed);
  } });
  await client.plan(scenario);
  const artifact = await client.exportRun(scenario);
  assert.deepEqual(artifact.bytes, bytes);
  assert.equal(artifact.fixture, false);
  assert.match(artifact.filename, /-run\.zip$/);
  assert.equal(calls.at(-1), '/plans/run%2Fid/export');
  const edit = structuredClone(scenario); edit.lander.antenna_height_m++;
  await assert.rejects(client.exportRun(edit), /exact scenario hash/);
});

test('package mismatched scenario header fails and canceled artifact cannot be exported', async () => {
  const client = createPlanClient({ fetchImpl: async (url, options = {}) => {
    if (options.method === 'POST') return response({ job_id: 'zip' });
    if (url.endsWith('/export')) return { ok: true, headers: new Headers({ 'X-SOMA-Scenario-SHA256': '0'.repeat(64) }),
      arrayBuffer: async () => new ArrayBuffer(0) };
    return response(completed);
  } });
  await client.plan(scenario);
  await assert.rejects(client.exportRun(scenario), /package does not match/);
  await client.cancel();
  await assert.rejects(client.exportRun(scenario), /No completed/);
});

test('fixture package uses exact fetched or captured bytes and never constructs an archive', async () => {
  const bytes = Uint8Array.from([80, 75, 0, 255]);
  let requested;
  const client = createFixtureClient([{ scenario, result, packageUrl: '/captured/run.zip' }], {
    fetchImpl: async url => { requested = url; return { ok: true, arrayBuffer: async () => bytes.buffer }; },
  });
  await client.plan(scenario);
  const downloaded = await client.exportRun(scenario);
  assert.equal(requested, '/captured/run.zip');
  assert.deepEqual(downloaded.bytes, bytes);
  assert.equal(downloaded.fixture, true);
  const captured = createFixtureClient([{ scenario, result, packageBytes: bytes }]);
  await captured.plan(scenario);
  bytes[0] = 0;
  assert.equal((await captured.exportRun(scenario)).bytes[0], 80);
});

test('mismatched completed result cannot be published through progress or exported', async () => {
  let published = false;
  const client = createPlanClient({ fetchImpl: async (_url, options = {}) => {
    if (options.method === 'POST') return response({ job_id: 'bad-hash' });
    if (options.method === 'DELETE') return { ok: true, status: 204 };
    return response({ ...completed, result: { ...result, scenario_sha256: '0'.repeat(64) } });
  } });
  await assert.rejects(client.plan(scenario, { onProgress: () => { published = true; } }), /result does not match/);
  assert.equal(published, false);
  await assert.rejects(client.exportRun(scenario), /No completed/);
});
