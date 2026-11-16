import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createFixtureClient, createPlanClient } from '../../web/src/client.js';

const scenario = JSON.parse(readFileSync(new URL('../../fixtures/synthetic-direct/scenario.json', import.meta.url), 'utf8'));
const result = JSON.parse(readFileSync(new URL('../../web/fixtures/synthetic-direct/result.json', import.meta.url), 'utf8'));
const response = value => ({ ok: true, status: 200, json: async () => value });
const completed = { status: 'completed', stage: 'complete', scenario_sha256: result.scenario_sha256, result };
const display = () => ({ ...structuredClone(result), artifact_type: 'soma_display_payload', format_version: '0.5.0',
  states: [], sample_epochs_utc: [], environment: null, interpolation: 'none_unknown_between_samples',
  registration: { status: 'blocked_pending_asset_registration' }, state_status: 'unknown' });

test('422 exposes only bounded string detail and other errors retain their HTTP status', async () => {
  for (const [status, body, expected] of [
    [422, { detail: 'Relay trajectory coverage must contain the analysis horizon' }, 'Scenario rejected: Relay trajectory coverage must contain the analysis horizon'],
    [422, { detail: 'x'.repeat(2100) }, `Scenario rejected: ${'x'.repeat(2000)}`],
    [422, { detail: [{ msg: 'unapproved structure' }] }, 'Planning service returned HTTP 422.'],
    [422, { detail: '' }, 'Planning service returned HTTP 422.'],
    [500, { detail: 'private server internals' }, 'Planning service returned HTTP 500.'],
  ]) {
    const client = createPlanClient({ fetchImpl: async () => ({ ok: false, status, json: async () => body }) });
    await assert.rejects(client.plan(scenario), { message: expected });
  }
  const malformed = createPlanClient({ fetchImpl: async () => ({ ok: false, status: 422, json: async () => { throw new SyntaxError('invalid JSON'); } }) });
  await assert.rejects(malformed.plan(scenario), { message: 'Planning service returned HTTP 422.' });
});

test('canceling while 422 detail parses cannot publish a rejected stale scenario', async () => {
  let release, reached;
  const parsing = new Promise(resolve => { reached = resolve; });
  const client = createPlanClient({ fetchImpl: async () => ({ ok: false, status: 422, json: async () => {
    reached(); return new Promise(resolve => { release = resolve; });
  } }) });
  const pending = client.plan(scenario);
  const rejected = assert.rejects(pending, { name: 'AbortError' });
  await parsing;
  await client.cancel();
  release({ detail: 'old unsupported scenario' });
  await rejected;
  await assert.rejects(client.retry(), /No failed immutable scenario/);
});

test('offline mode returns only captured exact matching scenario', async () => {
  const client = createFixtureClient([{ scenario, result }]);
  assert.deepEqual(await client.plan(scenario), result);
  const changed = structuredClone(scenario);
  changed.lander.antenna_height_m++;
  await assert.rejects(client.plan(changed), /Offline.*exact scenario/);
});

test('versioned summaries must match the completed result and cannot survive cancellation', async () => {
  const summary = JSON.parse(readFileSync(new URL('../../web/fixtures/synthetic-direct/summary.json', import.meta.url), 'utf8'));
  const client = createFixtureClient([{ scenario, result, summary }]);
  await client.plan(scenario);
  assert.deepEqual(await client.getSummary(scenario), summary);
  client.cancel();
  await assert.rejects(client.getSummary(scenario), /No completed summary/);
  const mismatched = createFixtureClient([{ scenario, result, summary: { ...summary, status: 'unknown' } }]);
  await mismatched.plan(scenario);
  await assert.rejects(mismatched.getSummary(scenario), /differs/);
  const invalid = createFixtureClient([{ scenario, result, summary: { ...summary, format_version: 'unapproved' } }]);
  await invalid.plan(scenario);
  await assert.rejects(invalid.getSummary(scenario), /unsupported version/);
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

test('live display fetch binds exact job, immutable result, scenario hash and artifact version', async () => {
  const paths = [];
  let supplied = display();
  const client = createPlanClient({ fetchImpl: async (url, options = {}) => {
    paths.push(url);
    if (options.method === 'POST') return response({ job_id: 'display/job' });
    return response(url.endsWith('/display-data') ? supplied : completed);
  } });
  await client.plan(scenario);
  const artifact = await client.getDisplay(scenario);
  assert.equal(paths.at(-1), '/plans/display%2Fjob/display-data');
  assert.deepEqual(artifact.allocations, result.allocations);
  assert.ok(Object.isFrozen(artifact.registration));
  supplied = { ...display(), format_version: 'unapproved' };
  await assert.rejects(client.getDisplay(scenario), /unsupported version/);
  supplied = { ...display(), scenario_sha256: '0'.repeat(64) };
  await assert.rejects(client.getDisplay(scenario), /mismatched scenario hash/);
  const changed = structuredClone(scenario); changed.lander.antenna_height_m++;
  await assert.rejects(client.getDisplay(changed), /No completed display/);
});

test('canceling or replacing a completion rejects a late display artifact even for same hash', async () => {
  for (const replace of [false, true]) {
    let release, reached;
    const started = new Promise(resolve => { reached = resolve; });
    const client = createPlanClient({ fetchImpl: async (url, options = {}) => {
      if (options.method === 'POST') return response({ job_id: 'display' });
      if (url.endsWith('/display-data')) {
        reached();
        return new Promise(resolve => { release = () => resolve(response(display())); });
      }
      return response(completed);
    } });
    await client.plan(scenario);
    const pending = client.getDisplay(scenario);
    const rejected = assert.rejects(pending, { name: 'AbortError' });
    await started;
    if (replace) await client.plan(scenario); else await client.cancel();
    release();
    await rejected;
  }
});

test('offline display data is explicit captured input and is invalidated with its completion', async () => {
  const captured = display();
  const client = createFixtureClient([{ scenario, result, display: captured }]);
  await client.plan(scenario);
  captured.registration.status = 'tampered';
  assert.equal((await client.getDisplay(scenario)).registration.status, 'blocked_pending_asset_registration');
  client.cancel();
  await assert.rejects(client.getDisplay(scenario), /No completed display/);
});

test('lazy captured display is validated and cannot publish after cancellation', async () => {
  let release;
  let started;
  const fetching = new Promise(resolve => { started = resolve; });
  const client = createFixtureClient([{ scenario, result, displayUrl: '/captured/display.json' }], {
    fetchImpl: async url => {
      assert.equal(url, '/captured/display.json');
      started();
      return new Promise(resolve => { release = () => resolve(response(display())); });
    },
  });
  await client.plan(scenario);
  const pending = client.getDisplay(scenario);
  const rejected = assert.rejects(pending, { name: 'AbortError' });
  await fetching;
  client.cancel();
  release();
  await rejected;
});
