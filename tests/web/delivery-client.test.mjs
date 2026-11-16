import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { gzipSync } from 'node:zlib';
import { createHash } from 'node:crypto';
import { createDeliveryClient, deliveryPackageBytes } from '../../web/src/delivery-client.js';

const read = name => JSON.parse(readFileSync(new URL(`../../web/fixtures/synthetic-relay/${name}.json`, import.meta.url)));
const scenario = read('scenario'), result = read('result');
const envelope = () => ({ delivery_api_version: '1.0.0', scenario, scenario_sha256: result.scenario_sha256,
  result: structuredClone(result), summary: { scenario_sha256: result.scenario_sha256 }, replay: { passed: true },
  environment: { scenario_sha256: result.scenario_sha256 },
  display: { ...structuredClone(result), artifact_type: 'soma_display_payload', format_version: '0.5.0',
    interpolation: 'none_unknown_between_samples', states: [], sample_epochs_utc: [] } });
const response = value => new Response(JSON.stringify(value), { headers: { 'Content-Type': 'application/json' } });

test('native request retains scenario/options and accepts matching independently replayed output', async () => {
  let body;
  const client = createDeliveryClient({ fetchImpl: async (url, options) => {
    assert.equal(url, '/api/research/delivery/analyze'); body = JSON.parse(options.body); return response(envelope());
  } });
  const options = { bin_s: 60, chunk_bytes: 16777216, time_limit_s: 10 };
  assert.deepEqual(await client.analyze(scenario, options), envelope());
  assert.deepEqual(body, { scenario, options });
});

test('mismatched scenario, modified display interval and unreplayed feasible candidates fail closed', async () => {
  for (const mutate of [value => { value.scenario_sha256 = '0'.repeat(64); },
    value => { value.display.allocations[0].byte_available_utc = '2026-11-14T12:00:00Z'; },
    value => { value.replay.passed = false; }]) {
    const value = envelope(); mutate(value);
    const client = createDeliveryClient({ fetchImpl: async () => response(value) });
    await assert.rejects(client.analyze(scenario, {}), /scenario|differs|replay/);
  }
});

test('stopped waiting cannot publish even when transport ignores abort', async () => {
  let release, enter;
  const pending = new Promise(resolve => { release = resolve; }), started = new Promise(resolve => { enter = resolve; });
  const client = createDeliveryClient({ fetchImpl: async () => { enter(); await pending; return response(envelope()); } });
  const run = client.analyze(scenario, {}); await started;
  assert.match(client.cancel(), /may continue/); release(); await assert.rejects(run, { name: 'AbortError' });
});

test('inner gzip download preserves native bytes and rejects checksum, declared size and encoding errors', async () => {
  const bytes = readFileSync(new URL('../../web/fixtures/synthetic-relay/run.zip', import.meta.url));
  const record = { encoding: 'gzip+base64', media_type: 'application/zip', bytes_base64: gzipSync(bytes).toString('base64'),
    size_bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') };
  assert.deepEqual(Buffer.from(await deliveryPackageBytes({ export: record })), bytes);
  for (const change of [{ sha256: '0'.repeat(64) }, { size_bytes: bytes.length - 1 }, { encoding: 'base64' }]) {
    await assert.rejects(deliveryPackageBytes({ export: { ...record, ...change } }), /checksum|size|metadata/);
  }
});

test('decoded response budget rejects an oversized stream before parsing', async () => {
  const client = createDeliveryClient({ fetchImpl: async () => new Response(new ReadableStream({ start(controller) {
    controller.enqueue(new Uint8Array(16_000_001)); controller.close();
  } })) });
  await assert.rejects(client.capabilities(), /response budget/);
});

const busy = retryAfter => new Response(JSON.stringify({ detail: 'One delivery computation is already active' }), {
  status: 429, headers: retryAfter === undefined ? {} : { 'Retry-After': retryAfter },
});

test('429 retries sequentially with immutable scenario/options and waiting notification', async () => {
  const bodies = [], notices = [], waits = [];
  const input = structuredClone(scenario), options = { bin_s: 60 };
  let inFlight = 0, peak = 0;
  const client = createDeliveryClient({ wait: async delay => { waits.push(delay); input.scenario_id = 'edited'; options.bin_s = 300; }, fetchImpl: async (_, request) => {
    inFlight++; peak = Math.max(peak, inFlight); bodies.push(request.body); inFlight--;
    return bodies.length === 1 ? busy('3') : response(envelope());
  } });
  await client.analyze(input, options, { onWaiting: value => notices.push(value) });
  assert.equal(peak, 1); assert.equal(bodies.length, 2); assert.equal(bodies[0], bodies[1]);
  assert.equal(JSON.parse(bodies[1]).options.bin_s, 60); assert.deepEqual(waits, [3000]); assert.equal(notices.length, 1);
});

test('busy waiting is finite and Retry-After values are safely clamped', async () => {
  for (const [header, delay] of [['garbage', 3000], ['-1', 3000], ['0', 1000], ['9999999', 30000],
    ['Thu, 01 Jan 1970 00:00:10 GMT', 10000]]) {
    let posts = 0, waited = 0;
    const client = createDeliveryClient({ now: () => 0, retryBudgetMs: delay, wait: async ms => { waited += ms; },
      fetchImpl: async () => { posts++; return busy(header); } });
    await assert.rejects(client.analyze(scenario, {}), error => error.status === 429 && /bounded waiting/.test(error.message));
    assert.equal(posts, 2); assert.equal(waited, delay);
  }
});

test('validation and unavailable errors retain typed HTTP status and never retry', async () => {
  for (const status of [422, 503]) {
    let posts = 0;
    const client = createDeliveryClient({ fetchImpl: async () => { posts++; return new Response('{"detail":"Rejected"}', { status }); } });
    await assert.rejects(client.analyze(scenario, {}), error => error.name === 'DeliveryHTTPError' && error.status === status);
    assert.equal(posts, 1);
  }
});

test('cancel during a real retry timer prevents another post', async () => {
  let queued, posts = 0;
  const waiting = new Promise(resolve => { queued = resolve; });
  const client = createDeliveryClient({ fetchImpl: async () => { posts++; return busy('1'); } });
  const run = client.analyze(scenario, {}, { onWaiting: queued });
  await waiting; client.cancel(); await assert.rejects(run, { name: 'AbortError' }); assert.equal(posts, 1);
});

test('superseding queued retries prevents stale publication even if wait ignores abort', async () => {
  let release, queued, posts = 0;
  const waiting = new Promise(resolve => { queued = resolve; });
  const client = createDeliveryClient({ wait: () => new Promise(resolve => { release = resolve; }),
    fetchImpl: async () => ++posts === 1 ? busy('1') : response(envelope()) });
  const old = client.analyze(scenario, {}, { onWaiting: queued }); await waiting;
  const fresh = client.analyze(scenario, { bin_s: 300 });
  await fresh; release(); await assert.rejects(old, { name: 'AbortError' }); assert.equal(posts, 2);
});
