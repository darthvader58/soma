import { canonicalScenarioHash, validateScenario, validateResult } from './contracts.js';
import { validateDisplayPayload } from './display.js';

const abortError = () => new DOMException('Planning canceled or superseded.', 'AbortError');
function assertValid(check, label) {
  if (!check.valid) throw new Error(`${label}: ${check.errors.join('; ')}`);
}
function frozen(value) {
  if (value && typeof value === 'object') {
    for (const child of Object.values(value)) frozen(child);
    Object.freeze(value);
  }
  return value;
}
function checkedResult(result, hash) {
  assertValid(validateResult(result), 'Invalid engine result');
  if (result.scenario_sha256 !== hash) throw new Error('Engine result does not match the submitted scenario hash.');
  return frozen(structuredClone(result));
}
function checkedSummary(summary, hash, result) {
  if (summary?.artifact_type !== 'soma_run_summary' || summary?.format_version !== '0.4.0' || summary.scenario_sha256 !== hash) {
    throw new Error('Run summary has an unsupported version or mismatched scenario hash.');
  }
  if (result && ['scenario_id','status','solver_status','model_fidelity','delivered_bytes','final_byte_arrival_utc']
    .some(key => summary[key] !== result[key])) throw new Error('Run summary metadata differs from its completed result.');
  return frozen(structuredClone(summary));
}
function wait(ms, signal) {
  return new Promise((resolve, reject) => {
    if (signal.aborted) { reject(abortError()); return; }
    const abort = () => { clearTimeout(timer); reject(abortError()); };
    const timer = setTimeout(() => { signal.removeEventListener('abort', abort); resolve(); }, ms);
    signal.addEventListener('abort', abort, { once: true });
  });
}
function exportFilename(id) {
  return `${String(id).replace(/[^A-Za-z0-9_.-]/g, '_')}-run.zip`;
}
async function packageBytes(response, hash) {
  if (!response.ok) throw new Error(`Run package returned HTTP ${response.status}.`);
  const suppliedHash = response.headers?.get('X-SOMA-Scenario-SHA256');
  if (suppliedHash && suppliedHash !== hash) throw new Error('Run package does not match the submitted scenario hash.');
  return new Uint8Array(await response.arrayBuffer());
}

export function createFixtureClient(fixtures, { fetchImpl = globalThis.fetch, fixtureDelayMs = 0 } = {}) {
  if (!Number.isFinite(fixtureDelayMs) || fixtureDelayMs < 0) throw new Error('Fixture test delay must be nonnegative.');
  const captured = fixtures.map(value => ({ ...value, scenario: structuredClone(value.scenario), result: structuredClone(value.result),
    ...(value.summary ? { summary: structuredClone(value.summary) } : {}),
    ...(value.display ? { display: structuredClone(value.display) } : {}),
    ...(value.packageBytes ? { packageBytes: new Uint8Array(value.packageBytes) } : {}) }));
  let generation = 0;
  let active;
  let completed;
  let failed;
  const assertCurrent = (current, run) => { if (current !== generation || run.controller.signal.aborted) throw abortError(); };
  function cancel() {
    generation++;
    active?.controller.abort();
    active = undefined;
    completed = undefined;
    failed = undefined;
  }
  async function plan(scenario, { onProgress = () => {} } = {}) {
    cancel();
    const current = generation;
    const run = { controller: new AbortController() };
    active = run;
    const snapshot = structuredClone(scenario);
    let hash;
    try {
      assertValid(validateScenario(snapshot), 'Invalid scenario');
      hash = await canonicalScenarioHash(snapshot);
      assertCurrent(current, run);
      const fixtureHashes = await Promise.all(captured.map(fixture => canonicalScenarioHash(fixture.scenario)));
      assertCurrent(current, run);
      const fixture = captured[fixtureHashes.indexOf(hash)];
      if (!fixture) throw new Error('Offline: no captured engine result matches this exact scenario. Restore the fixture or connect the planning service.');
      if (fixtureDelayMs) {
        onProgress({ status: 'running', stage: 'delayed_fixture_test', scenario_sha256: hash,
          message: 'Explicit delayed fixture test; no scientific computation is running.' });
        await wait(fixtureDelayMs, run.controller.signal);
        assertCurrent(current, run);
      }
      const result = checkedResult(fixture.result, hash);
      onProgress({ status: 'completed', stage: 'captured_engine_fixture', scenario_sha256: hash });
      assertCurrent(current, run);
      completed = { fixture, hash, current, scenarioId: snapshot.scenario_id, result };
      return result;
    } catch (error) {
      if (current === generation && error.name !== 'AbortError' && hash) failed = frozen({ scenario: snapshot, hash });
      throw error;
    } finally { if (active === run) active = undefined; }
  }
  return {
    cancel, plan,
    retry(options) {
      if (!failed) return Promise.reject(new Error('No failed immutable scenario is available to retry.'));
      return plan(failed.scenario, options);
    },
    async getSummary(scenario) {
      const artifact = completed;
      const hash = await canonicalScenarioHash(scenario);
      if (!artifact || artifact !== completed || artifact.hash !== hash) throw new Error('No completed summary matches this scenario.');
      return checkedSummary(artifact.fixture.summary, hash, artifact.result);
    },
    async getDisplay(scenario) {
      const artifact = completed;
      const hash = await canonicalScenarioHash(scenario);
      if (!artifact || artifact !== completed || artifact.hash !== hash) throw new Error('No completed display matches this scenario.');
      return frozen(structuredClone(validateDisplayPayload(artifact.fixture.display, hash, artifact.result)));
    },
    async exportRun(scenario) {
      const artifact = completed;
      const hash = await canonicalScenarioHash(scenario);
      if (!artifact || artifact !== completed || hash !== artifact.hash) throw new Error('No completed run package matches this exact scenario hash.');
      let bytes;
      if (artifact.fixture.packageBytes) bytes = new Uint8Array(artifact.fixture.packageBytes);
      else if (artifact.fixture.packageUrl) bytes = await packageBytes(await fetchImpl(artifact.fixture.packageUrl), hash);
      else throw new Error('No captured engine run package is available for this fixture.');
      if (completed !== artifact || generation !== artifact.current) throw abortError();
      return { bytes, filename: exportFilename(artifact.scenarioId), fixture: true };
    },
  };
}

export function createPlanClient({ baseUrl = '', fetchImpl = globalThis.fetch, pollIntervalMs = 500 } = {}) {
  let generation = 0;
  let active;
  let completed;
  let failed;
  const endpoint = path => `${baseUrl.replace(/\/$/, '')}${path}`;
  async function request(path, options = {}) {
    const response = await fetchImpl(endpoint(path), options);
    if (!response.ok) {
      let detail;
      if (response.status === 422) {
        try {
          const body = await response.json();
          if (typeof body?.detail === 'string' && body.detail.trim()) detail = body.detail.slice(0, 2000);
        } catch { /* A malformed error body retains the HTTP status message. */ }
      }
      if (options.signal?.aborted) throw abortError();
      throw new Error(detail ? `Scenario rejected: ${detail}` : `Planning service returned HTTP ${response.status}.`);
    }
    return response.status === 204 ? null : response.json();
  }
  async function remove(run) {
    if (!run?.id || run.cleanupRequested) return;
    run.cleanupRequested = true;
    await request(`/plans/${encodeURIComponent(run.id)}`, { method: 'DELETE' });
  }
  function invalidate() {
    generation++;
    const previous = active;
    active = undefined;
    previous?.controller.abort();
    completed = undefined;
    failed = undefined;
    return previous;
  }
  async function cancel() { await remove(invalidate()); }
  async function plan(scenario, { onProgress = () => {} } = {}) {
    const previous = invalidate();
    const current = generation;
    const run = { controller: new AbortController() };
    active = run;
    const assertCurrent = () => { if (current !== generation || run.controller.signal.aborted) throw abortError(); };
    const snapshot = structuredClone(scenario);
    let hash;
    try {
      await remove(previous);
      assertCurrent();
      assertValid(validateScenario(snapshot), 'Invalid scenario');
      hash = await canonicalScenarioHash(snapshot);
      assertCurrent();
      const job = await request('/plans', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(snapshot), signal: run.controller.signal });
      if (!job || typeof job.job_id !== 'string' || !job.job_id) throw new Error('Planning service omitted job_id.');
      run.id = job.job_id;
      if (current !== generation || run.controller.signal.aborted) {
        await remove(run);
        throw abortError();
      }
      if (job.scenario_sha256 !== undefined && job.scenario_sha256 !== hash) throw new Error('Accepted job does not match the submitted scenario hash.');
      for (;;) {
        const progress = await request(`/plans/${encodeURIComponent(run.id)}`, { signal: run.controller.signal });
        assertCurrent();
        if (progress.scenario_sha256 !== hash) throw new Error('Job progress does not match the submitted scenario hash.');
        const result = progress.status === 'completed' ? checkedResult(progress.result, hash) : undefined;
        onProgress(structuredClone(progress));
        assertCurrent();
        if (progress.status === 'canceled') throw abortError();
        if (progress.status === 'failed') throw new Error(progress.error || 'Planning service failed.');
        if (progress.status === 'completed') {
          completed = { id: run.id, hash, current, scenarioId: snapshot.scenario_id, result };
          return result;
        }
        if (!['queued', 'running', 'cancel_requested', 'canceling'].includes(progress.status)) throw new Error('Planning service returned an unknown job state.');
        await wait(pollIntervalMs, run.controller.signal);
        assertCurrent();
      }
    } catch (error) {
      if (current === generation && error.name !== 'AbortError' && hash) failed = frozen({ scenario: snapshot, hash });
      // A bad result or failed polling must not leave avoidable work running.
      try { await remove(run); } catch (cleanupError) {
        if (error.name !== 'AbortError') error.message += ` Cancellation failed: ${cleanupError.message}`;
      }
      if (current !== generation || run.controller.signal.aborted) throw abortError();
      throw error;
    } finally { if (active === run) active = undefined; }
  }
  return {
    cancel, plan,
    retry(options) {
      if (!failed) return Promise.reject(new Error('No failed immutable scenario is available to retry.'));
      return plan(failed.scenario, options);
    },
    async getSummary(scenario) {
      const artifact = completed;
      const hash = await canonicalScenarioHash(scenario);
      if (!artifact || artifact !== completed || artifact.hash !== hash) throw new Error('No completed summary matches this scenario.');
      const value = await request(`/plans/${encodeURIComponent(artifact.id)}/summary`);
      if (completed !== artifact || generation !== artifact.current) throw abortError();
      return checkedSummary(value, hash, artifact.result);
    },
    async getDisplay(scenario) {
      const artifact = completed;
      const hash = await canonicalScenarioHash(scenario);
      if (!artifact || artifact !== completed || artifact.hash !== hash) throw new Error('No completed display matches this scenario.');
      const value = await request(`/plans/${encodeURIComponent(artifact.id)}/display-data`);
      if (completed !== artifact || generation !== artifact.current) throw abortError();
      return frozen(structuredClone(validateDisplayPayload(value, hash, artifact.result)));
    },
    async exportRun(scenario) {
      const artifact = completed;
      const hash = await canonicalScenarioHash(scenario);
      if (!artifact || artifact !== completed || artifact.hash !== hash) throw new Error('No completed run package matches this exact scenario hash.');
      const response = await fetchImpl(endpoint(`/plans/${encodeURIComponent(artifact.id)}/export`));
      const bytes = await packageBytes(response, hash);
      if (completed !== artifact || generation !== artifact.current) throw abortError();
      return { bytes, filename: exportFilename(artifact.scenarioId), fixture: false };
    },
  };
}
