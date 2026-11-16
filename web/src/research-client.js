import { canonicalScenarioHash } from './contracts.js';
import { validateResearchResult } from './research-contracts.js';

const abortError = () => new DOMException('Study no longer current.', 'AbortError');
export const studyHash = canonicalScenarioHash;

export function validateStudyInputs(study) {
  const errors = [];
  const start = Date.parse(study.time.start_utc), end = Date.parse(study.time.end_utc);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) errors.push('End UTC must be after start UTC.');
  if (end - start > 31 * 86400000) errors.push('A geometry study may span at most 31 days.');
  if (!Number.isFinite(study.time.step_s) || study.time.step_s < 10) errors.push('Sampling step must be at least 10 seconds.');
  const epochs = Math.ceil((end - start) / (study.time.step_s * 1000)) + 1;
  if (epochs > 2000 || epochs * study.sites.length > 5000) errors.push('Reduce the interval or increase the sampling step: maximum 2,000 epochs and 5,000 site/epoch pairs.');
  if (study.sites.length < 1 || study.sites.length > 8) errors.push('Select between 1 and 8 sites.');
  for (const site of study.sites) {
    if (![site.latitude_deg, site.longitude_deg_east, site.elevation_m, site.antenna_height_m, site.panel_height_m].every(Number.isFinite)) errors.push(`${site.name}: enter finite coordinates and heights.`);
    if (Math.abs(site.latitude_deg) > 90 || Math.abs(site.longitude_deg_east) > 180) errors.push(`${site.name}: latitude must be -90 to 90 and east longitude -180 to 180 degrees.`);
    if (site.antenna_height_m < 0 || site.panel_height_m < 0) errors.push(`${site.name}: equipment heights cannot be negative.`);
  }
  return { errors, epochs, pairs: epochs * study.sites.length };
}

export function createResearchClient({ baseUrl = '/api/research', fetchImpl = globalThis.fetch, pollMs = 600 } = {}) {
  let generation = 0, active;
  const url = path => `${baseUrl.replace(/\/$/, '')}${path}`;
  async function request(path, options) {
    const response = await fetchImpl(url(path), options);
    if (!response.ok) {
      let detail;
      try { const body = await response.json(); detail = typeof body.detail === 'string' ? body.detail : body.error?.message; } catch { /* HTTP status remains usable. */ }
      throw new Error(detail || `Research service returned HTTP ${response.status}.`);
    }
    return response.status === 204 ? null : response.json();
  }
  async function cancel() {
    generation += 1;
    const run = active; active = undefined;
    run?.controller.abort();
    if (run?.id) {
      await request(`/jobs/${encodeURIComponent(run.id)}`, { method: 'DELETE' });
      return 'Server cancellation requested. Avoidable remaining work will stop.';
    }
    return 'Stopped waiting. A synchronous calculation may continue on the server.';
  }
  return {
    catalog: () => request('/catalog'), capabilities: () => request('/capabilities'), cancel,
    async analyze(study, capabilities, onProgress = () => {}) {
      const cancellation = cancel();
      const current = generation, controller = new AbortController();
      await cancellation;
      if (current !== generation) throw abortError();
      const snapshot = structuredClone(study), hash = await studyHash(snapshot);
      if (current !== generation) throw abortError();
      const run = { controller }; active = run;
      const assertCurrent = () => { if (current !== generation || controller.signal.aborted) throw abortError(); };
      const options = { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(snapshot), signal: controller.signal };
      try {
        const persistent = capabilities?.async_available === true;
        let result, job;
        if (persistent) {
          job = await request('/jobs', options);
          run.id = job.id ?? job.job_id;
          if (current !== generation || controller.signal.aborted) {
            if (run.id) await request(`/jobs/${encodeURIComponent(run.id)}`, { method: 'DELETE' });
            throw abortError();
          }
          if (!run.id || job.study_sha256 !== hash) throw new Error('Submitted job hash does not match this study.');
          for (;;) {
            assertCurrent();
            job = await request(`/jobs/${encodeURIComponent(run.id)}`, { signal: controller.signal }); assertCurrent();
            if (job.study_sha256 !== hash) throw new Error('Job snapshot hash does not match this study.');
            onProgress(job);
            if (job.status === 'completed') { result = job.result; break; }
            if (['failed', 'canceled', 'cancelled'].includes(job.status)) throw new Error(job.error?.message ?? job.error ?? `Study ${job.status}.`);
            await new Promise((resolve, reject) => {
              const stop = () => { clearTimeout(timer); reject(abortError()); };
              const timer = setTimeout(() => { controller.signal.removeEventListener('abort', stop); resolve(); }, pollMs);
              controller.signal.addEventListener('abort', stop, { once: true });
            });
          }
        } else {
          onProgress({ status: 'running', stage: 'Evaluating geometry in Python. Synchronous request.' });
          result = await request('/analyze', options); assertCurrent();
        }
        validateResearchResult(result);
        if (result?.study_sha256 !== hash || await studyHash(result.request) !== hash) throw new Error('Returned study hash does not match these inputs. Result discarded.');
        assertCurrent();
        if (result.status !== 'completed' || !Array.isArray(result.epochs_utc) || !result.epochs_utc.length) throw new Error('Research response has no completed scientific samples.');
        return { result, jobId: run.id, hash };
      } finally { if (active === run) active = undefined; }
    },
    exportUrl: id => url(`/jobs/${encodeURIComponent(id)}/export`),
  };
}

export function storedSampleAt(samples, epoch) {
  if (!samples?.length) return undefined;
  const time = Date.parse(epoch);
  if (!Number.isFinite(time)) return undefined;
  if (time < Date.parse(samples[0].epoch_utc) || time > Date.parse(samples.at(-1).epoch_utc)) return undefined;
  let low = 0, high = samples.length - 1;
  while (low < high) { const mid = Math.ceil((low + high) / 2); if (Date.parse(samples[mid].epoch_utc) <= time) low = mid; else high = mid - 1; }
  return samples[low];
}
