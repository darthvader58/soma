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
