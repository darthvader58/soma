import { canonicalScenarioHash, validateScenario, validateResult } from './contracts.js';
import { validateDisplayPayload } from './display.js';

const MAX_RESPONSE_BYTES = 16_000_000;
const abortError = () => new DOMException('Delivery request canceled or superseded.', 'AbortError');
const assertValid = (check, label) => { if (!check.valid) throw new Error(`${label}: ${check.errors.join('; ')}`); };

async function boundedJSON(response) {
  const wireLength = Number(response.headers?.get('Content-Length'));
  if (Number.isFinite(wireLength) && wireLength > 4_000_000) throw new Error('Delivery response exceeds the wire response budget.');
  const reader = response.body.getReader(), parts = [];
  let length = 0;
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    length += value.length;
    if (length > MAX_RESPONSE_BYTES) { await reader.cancel(); throw new Error('Delivery response exceeds the decoded response budget.'); }
    parts.push(value);
  }
  const content = new Uint8Array(length); let offset = 0;
  for (const part of parts) { content.set(part, offset); offset += part.length; }
  let document;
  try { document = JSON.parse(new TextDecoder().decode(content)); }
  catch { throw new Error(`Delivery service returned unreadable data (HTTP ${response.status}).`); }
  if (!response.ok) throw new Error(typeof document.detail === 'string' ? document.detail : `Delivery service returned HTTP ${response.status}.`);
  return document;
}

export async function deliveryPackageBytes(artifact) {
  const record = artifact.export;
  if (record?.encoding !== 'gzip+base64' || record.media_type !== 'application/zip' ||
      !/^[a-f0-9]{64}$/.test(record.sha256 ?? '') || !Number.isInteger(record.size_bytes) ||
      record.size_bytes < 1 || record.size_bytes > 16_000_000 || typeof record.bytes_base64 !== 'string') {
    throw new Error('Python run package has unsupported metadata.');
  }
  if (typeof DecompressionStream === 'undefined') throw new Error('This browser cannot decompress the Python run package. Use a current browser; no replacement package was created.');
  const compressed = Uint8Array.from(atob(record.bytes_base64), char => char.charCodeAt(0));
  const stream = new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'));
  const reader = stream.getReader(), parts = []; let length = 0;
  for (;;) {
    const { value, done } = await reader.read(); if (done) break;
    length += value.length;
    if (length > record.size_bytes) { await reader.cancel(); throw new Error('Python run package exceeds its declared size.'); }
    parts.push(value);
  }
  const bytes = new Uint8Array(length); let offset = 0;
  for (const part of parts) { bytes.set(part, offset); offset += part.length; }
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', bytes));
  const hash = [...digest].map(value => value.toString(16).padStart(2, '0')).join('');
  if (length !== record.size_bytes || hash !== record.sha256) throw new Error('Python run package checksum or size differs from its manifest.');
  return bytes;
}

export function createDeliveryClient({ baseUrl = '/api/research/delivery', fetchImpl = globalThis.fetch } = {}) {
  let generation = 0, active;
  const endpoint = path => `${baseUrl.replace(/\/$/, '')}${path}`;
  function cancel() { generation += 1; active?.abort(); active = undefined; return 'Stopped waiting. The bounded Python calculation may continue on the server; no durable job or server cancellation is claimed.'; }
  return {
    capabilities: () => fetchImpl(endpoint('/capabilities')).then(boundedJSON),
    cancel,
    async analyze(scenario, options) {
      cancel(); const current = generation, controller = new AbortController(); active = controller;
      const snapshot = structuredClone(scenario);
      assertValid(validateScenario(snapshot), 'Invalid delivery scenario');
      const hash = await canonicalScenarioHash(snapshot);
      if (current !== generation) throw abortError();
      try {
        const response = await fetchImpl(endpoint('/analyze'), { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ scenario: snapshot, options }), signal: controller.signal });
        const artifact = await boundedJSON(response);
        if (current !== generation || controller.signal.aborted) throw abortError();
        if (artifact.delivery_api_version !== '1.0.0' || artifact.scenario_sha256 !== hash ||
            await canonicalScenarioHash(artifact.scenario) !== hash) throw new Error('Delivery response does not match the submitted scenario.');
        assertValid(validateResult(artifact.result), 'Invalid delivery result');
        if (artifact.result.scenario_sha256 !== hash || artifact.summary?.scenario_sha256 !== hash) throw new Error('Delivery result or summary has a mismatched scenario hash.');
        validateDisplayPayload(artifact.display, hash, artifact.result);
        if (artifact.environment?.scenario_sha256 !== hash) throw new Error('Delivery diagnostics do not match the submitted scenario.');
        if (artifact.result.status === 'feasible_under_assumptions' && artifact.replay?.passed !== true) throw new Error('A feasible delivery result requires successful independent replay.');
        return artifact;
      } finally { if (active === controller) active = undefined; }
    },
  };
}
