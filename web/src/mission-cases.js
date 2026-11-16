export const missionCases = [
  { id: 'direct-ready', title: 'Direct delivery', label: 'Terrain-backed baseline',
    question: 'Can the lander deliver 16 MiB directly to Earth before the deadline?',
    change: 'Baseline site, published numerical LOLA terrain and DE421 ephemerides; assumed radio rate and service.' },
  { id: 'direct-later', title: 'Later direct', label: 'Controlled date change',
    question: 'Does direct delivery still work at the later date?',
    change: 'Move from 24 to 30 November 2026, translating the six-hour deadline and service windows. The 16 MiB task, lander hardware and 80 Wh initial battery stay fixed.' },
  { id: 'relay-later', title: 'Lunar relay', label: 'Store and forward',
    question: 'Can a declared lunar relay deliver the same later task?',
    change: 'Enable the single lunar-relay route for the later case. The synthetic two-body relay has finite storage and assumed service and rates.' },
  { id: 'battery-low', title: 'Battery constraint', label: 'Synthetic constraint test',
    question: 'Can the synthetic relay task run with only 1 Wh above reserve?',
    change: 'Only initial lander energy changes: 80 Wh to 11 Wh. Reserve remains 10 Wh. Synthetic contacts and the 100 MiB task stay fixed.' },
  { id: 'service-off', title: 'Service constraint', label: 'Synthetic constraint test',
    question: 'Does geometric contact suffice when relay service is unavailable?',
    change: 'Only the synthetic relay service calendar changes to no available windows. The 100 MiB task, hardware and initial battery remain unchanged.' },
];

export const relayFocusEpoch = '2026-11-30T09:33:30Z';

export function missionCaseFromUrl(search, availableIds) {
  const requested = new URLSearchParams(search).get('case');
  return availableIds.includes(requested) ? requested : 'direct-ready';
}

export function hasRelayFocus(display) {
  return (display?.sample_epochs_utc ?? []).includes(relayFocusEpoch)
    && (display?.renderer_states ?? []).some(state => state.epoch === relayFocusEpoch);
}

export function missionOutcome(result, summary) {
  if (!result) return 'Loading the exact captured Python run.';
  const matchingSummary = summary?.scenario_sha256 === result.scenario_sha256 ? summary : undefined;
  const status = { feasible_under_assumptions: 'Feasible under assumptions', infeasible_in_model: 'Infeasible in model', unknown: 'Unknown' }[result.status];
  const bytes = result.delivered_bytes === null ? 'Unknown' : result.delivered_bytes.toLocaleString('en-US');
  return `${status}. Delivered: ${bytes} bytes. Last byte: ${result.final_byte_arrival_utc ?? 'No complete-file arrival'}. ${matchingSummary?.limiting_reason ?? result.provenance.reason}`;
}

export function controlledTestExplanation(evidence, caseId, result) {
  if (!result || !evidence || evidence.case_id !== caseId || evidence.scenario_sha256 !== result.scenario_sha256
    || evidence.status !== result.status || evidence.solver_status !== result.solver_status
    || evidence.delivered_bytes !== result.delivered_bytes || typeof evidence.constraint_explanation !== 'string') return '';
  const codes = [...new Set((evidence.baseline_counterfactual_errors ?? []).map(item => item.code))];
  return `${evidence.constraint_explanation} Baseline-schedule counterfactual replay: ${codes.join(', ') || 'Unknown'}. This explanation is supplied with the controlled test; the solver-native outcome remains above.`;
}
