import { canonicalScenarioJSON } from './contracts.js';
import { sameDisplayEpoch } from './display-time.js';

const resultFields = ['scenario_id', 'run_version', 'model_fidelity', 'contacts', 'allocations',
  'storage_intervals', 'energy_history', 'buffer_history', 'assumptions', 'warnings'];

export function validateDisplayPayload(value, hash, result) {
  if (value?.artifact_type !== 'soma_display_payload' || value.format_version !== '0.5.0' ||
      value.scenario_sha256 !== hash || value.interpolation !== 'none_unknown_between_samples') {
    throw new Error('Display payload has an unsupported version, sampling policy or mismatched scenario hash.');
  }
  for (const key of resultFields) {
    if (value[key] === undefined || canonicalScenarioJSON(value[key]) !== canonicalScenarioJSON(result[key])) {
      throw new Error(`Display payload ${key} differs from its completed result.`);
    }
  }
  if (!Array.isArray(value.states) || !Array.isArray(value.sample_epochs_utc) ||
      !value.sample_epochs_utc.every(epoch => typeof epoch === 'string' && /(?:Z|[+-]\d{2}:\d{2})$/.test(epoch) && Number.isFinite(Date.parse(epoch)))) {
    throw new Error('Display payload omits explicit stored samples.');
  }
  for (const state of value.states) {
    if (!state || typeof state.target !== 'string' || !state.target || typeof state.origin !== 'string' ||
        typeof state.frame !== 'string' || !['m', 'km'].includes(state.position_unit) ||
        !Array.isArray(state.position) || state.position.length !== 3 || !state.position.every(Number.isFinite) ||
        !['UTC', 'TDB'].includes(state.time_scale) || typeof state.provenance_label !== 'string' ||
        (state.time_scale === 'UTC' && (state.epoch_format !== 'rfc3339' || typeof state.epoch !== 'string' || !Number.isFinite(Date.parse(state.epoch)))) ||
        (state.time_scale === 'TDB' && (state.epoch_format !== 'seconds_past_j2000_tdb' || !Number.isFinite(state.epoch)))) {
      throw new Error('Display state omits its stored epoch, origin, frame, units or provenance.');
    }
  }
  if (value.environment && value.environment.scenario_sha256 !== hash) {
    throw new Error('Display environment does not match the submitted scenario hash.');
  }
  return value;
}

// Exact stored records only: no interpolation, propagation or resource integration.
export function displayAtTime(display, epoch) {
  const at = records => (records ?? []).filter(record => sameDisplayEpoch(record.epoch_utc ?? record.epoch, epoch));
  return {
    epoch_utc: epoch,
    states: at(display?.states),
    energy: at(display?.energy_history),
    buffers: at(display?.buffer_history),
    solar: at(display?.environment?.solar_samples),
    power: at(display?.environment?.power_samples),
    state_status: at(display?.states).length ? 'stored_sample' : 'unknown',
  };
}

export function displayTimeText(display, epoch) {
  const sample = displayAtTime(display, epoch);
  if (!display) return `Selected time ${epoch} UTC. No matching completed-job display artifact. Spacecraft state: Unknown.`;
  const states = sample.states.length
    ? sample.states.map(state => `${state.target}: [${state.position.join(', ')}] ${state.position_unit}; ${state.origin} origin, ${state.frame}, stored epoch ${state.epoch} ${state.time_scale}; ${state.provenance_label}`).join('; ')
    : `Spacecraft state: Unknown. ${(display.state_unavailable_reasons ?? ['No exact stored sample at this time']).join('; ')}.`;
  const energy = sample.energy.length ? sample.energy.map(row => `${row.node_id}: ${row.stored_energy_wh ?? 'Unknown'} Wh`).join('; ') : 'Unknown (no exact stored energy sample)';
  const buffers = sample.buffers.length ? sample.buffers.map(row => `${row.node_id}: ${row.stored_bytes ?? 'Unknown'} bytes`).join('; ') : 'Unknown (no exact stored buffer sample)';
  return `Selected time ${epoch} UTC. ${states} Stored energy: ${energy}. Stored buffers: ${buffers}. Values between unsupported samples remain unknown.`;
}
