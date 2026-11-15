export function formatValue(value, unit = '') {
  return value === null || value === undefined ? 'Unknown' : `${typeof value === 'number' ? value.toLocaleString('en-US', { maximumFractionDigits: 10 }) : value}${unit ? ` ${unit}` : ''}`;
}

export function describeStatus(result) {
  const labels = { unknown: 'Unknown', feasible_under_assumptions: 'Feasible under assumptions', infeasible_in_model: 'Infeasible in model' };
  return { label: labels[result?.status] ?? 'No result', code: result?.status ?? 'unknown', solver: result?.solver_status ?? 'Not run', fidelity: result?.model_fidelity ?? 'Not evaluated' };
}

export function explainResult(result) {
  if (!result) return ['No engine result has been loaded.'];
  const lines = [result.provenance?.reason ?? 'Unknown: no engine explanation supplied.'];
  for (const allocation of result.allocations ?? []) {
    const contact = (result.contacts ?? []).find(value => value.contact_id === allocation.contact_id);
    const endpoints = contact ? `${contact.sender} to ${contact.receiver}` : 'Unknown endpoints';
    lines.push(`${endpoints}: ${allocation.byte_length} bytes of ${allocation.chunk_id}, byte offset ${allocation.byte_offset}. Source transmits ${allocation.source_transmit_interval.start_utc} to ${allocation.source_transmit_interval.end_utc}; receiver payload occupancy ${allocation.receiver_occupancy_interval.start_utc} to ${allocation.receiver_occupancy_interval.end_utc}; bytes available ${allocation.byte_available_utc}.`);
  }
  for (const storage of result.storage_intervals ?? []) lines.push(`${storage.node_id} stores ${storage.byte_length} bytes of ${storage.chunk_id} from ${storage.interval.start_utc} to ${storage.interval.end_utc}.`);
  lines.push(`Delivered file bytes: ${formatValue(result.delivered_bytes)}. Final byte arrival: ${formatValue(result.final_byte_arrival_utc)}.`);
  return lines;
}

const el = (tag, text, className) => {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
};
const interval = value => value ? `${value.start_utc} to ${value.end_utc}` : 'Unknown';

function section(container, title) {
  const node = el('section', undefined, 'result-section'); node.append(el('h3', title)); container.append(node); return node;
}
function records(container, title) {
  const group = section(container, title);
  const details = el('details');
  details.append(el('summary', `Inspect ${title.toLowerCase()}`));
  group.append(details);
  return details;
}

function table(container, headers, rows, empty) {
  if (!rows.length) { container.append(el('p', empty, 'muted')); return; }
  const wrap = el('div', undefined, 'table-scroll');
  wrap.tabIndex = 0; wrap.setAttribute('role', 'region'); wrap.setAttribute('aria-label', headers.join(', '));
  const node = el('table', undefined, 'data-table');
  const head = el('thead'); const tr = el('tr');
  for (const header of headers) { const th = el('th', header); th.scope = 'col'; tr.append(th); }
  head.append(tr); node.append(head);
  const body = el('tbody');
  for (const row of rows) { const tr = el('tr'); for (const value of row) tr.append(el('td', formatValue(value))); body.append(tr); }
  node.append(body); wrap.append(node); container.append(wrap);
}

function allocations(container, values = [], contacts = []) {
  table(container, ['Contact / endpoints', 'Payload (bytes)', 'Source transmit (UTC)', 'Receiver occupied (UTC)', 'Bytes available (UTC)'], values.map(value => {
    const contact = contacts.find(contact => contact.contact_id === value.contact_id);
    return [`${value.contact_id}${contact ? `: ${contact.sender} to ${contact.receiver}` : ''}`, value.byte_length, interval(value.source_transmit_interval), interval(value.receiver_occupancy_interval), value.byte_available_utc];
  }), 'No computed transmission.');
}

export function renderResult(container, { result, scenario, contacts = [], expected }) {
  container.replaceChildren();
  const status = describeStatus(result);
  const top = el('div', undefined, 'status-line');
  top.append(el('strong', status.label, `status-badge status-${status.code}`));
  container.append(top, el('p', `Solver: ${status.solver} · Model fidelity: ${status.fidelity}`));
  if (!result) { container.append(el('p', 'No engine result has been loaded.', 'notice')); return; }
  container.append(el('p', result.provenance?.reason ?? 'Unknown: no reason supplied.', 'notice'));
  if (result.model_fidelity === 'assumed_rate_simulation') container.append(el('p', 'Assumed-rate simulation. A feasible status retains the declared rate and service assumptions.', 'notice'));
  const facts = el('dl', undefined, 'details-list');
  for (const [label, value] of [['Delivered', formatValue(result.delivered_bytes, 'bytes')], ['Final byte arrival (UTC)', formatValue(result.final_byte_arrival_utc)], ['Scenario', result.scenario_id], ['Scenario SHA-256', result.scenario_sha256]]) facts.append(el('dt', label), el('dd', value));
  container.append(facts);
  const explanation = records(container, 'Structured schedule explanation');
  for (const line of explainResult(result)) explanation.append(el('p', line));
  table(section(container, 'Engine contacts'), ['Endpoints / contact', 'Source transmit window (UTC)', 'Net payload rate (bps)', 'Capacity (bits)', 'Service / quality flags', 'Allocation use / unused reason'], (result.contacts ?? []).map(contact => [
    `${contact.sender} to ${contact.receiver} / ${contact.contact_id}`, interval(contact.source_transmit_window), contact.payload_rate_bps, contact.available_capacity_bits,
    `${contact.service_provenance}; ${contact.quality_flags.join('; ')}`,
    (result.allocations ?? []).some(value => value.contact_id === contact.contact_id) ? 'Allocated; see source and receiver intervals below.' : 'Unused. Reason: Unknown; no reason field supplied by the frozen contact contract.'
  ]), 'No computed usable contacts. Unknown: no usable-contact records were supplied.');
  allocations(section(container, 'Engine allocations'), result.allocations, result.contacts);
  table(records(container, 'Engine storage'), ['Node', 'Payload (bytes)', 'Stored interval (UTC)'], (result.storage_intervals ?? []).map(value => [value.node_id, value.byte_length, interval(value.interval)]), 'No computed storage history.');
  table(records(container, 'Engine battery history'), ['Node', 'Epoch (UTC)', 'Stored energy (Wh)'], (result.energy_history ?? []).map(value => [value.node_id, value.epoch_utc, value.stored_energy_wh]), 'Battery state has not been computed. No energy feasibility claim is available.');
  table(records(container, 'Engine buffer history'), ['Node', 'Epoch (UTC)', 'Stored payload (bytes)'], (result.buffer_history ?? []).map(value => [value.node_id, value.epoch_utc, value.stored_bytes]), 'No computed buffer history.');
  const caveats = section(container, 'Assumptions and warnings');
  for (const [title, values] of [['Assumptions', result.assumptions], ['Warnings', result.warnings]]) {
    caveats.append(el('h4', title)); const list = el('ul');
    for (const value of values ?? []) list.append(el('li', value));
    if (!list.childNodes.length) list.append(el('li', 'None supplied.'));
    caveats.append(list);
  }
  const input = section(container, 'Synthetic contact inputs');
  input.append(el('p', 'Separate synthetic source-window reference. These rows are not selected transmissions or an independent assessment of geometry, link closure or energy.', 'muted'));
  table(input, ['Endpoints / contact', 'Source transmit window (UTC)', 'Net payload rate (bps)', 'Capacity (bits)', 'Delay model / seconds', 'Service / quality flags'], contacts.map(contact => [
    `${contact.sender} to ${contact.receiver} / ${contact.contact_id}`, interval(contact.source_transmit_window), contact.payload_rate_bps, contact.available_capacity_bits,
    `${contact.one_way_delay.model} / ${contact.one_way_delay.seconds} s`, `${contact.service_provenance}; ${contact.quality_flags.join('; ')}`
  ]), 'No synthetic contact inputs.');
  if (expected) {
    const hand = section(container, 'Hand calculation / synthetic expected schedule');
    hand.append(el('p', 'Separate arithmetic reference. Energy and replay have not been evaluated. This is not an engine-generated plan.', 'notice'));
    hand.append(el('p', `Capacity conclusion: ${expected.capacity_conclusion}`));
    hand.append(el('p', `File: ${formatValue(expected.file_bytes, 'bytes')} · Direct capacity: ${formatValue(expected.direct_capacity_bits, 'bits')} · Shortfall: ${formatValue(expected.direct_shortfall_bits, 'bits')}`));
    allocations(hand, expected.allocations, contacts);
    table(hand, ['Storage node', 'Payload (bytes)', 'Expected wait (UTC)'], (expected.storage_intervals ?? []).map(value => [value.node_id, value.byte_length, interval(value.interval)]), 'No expected relay wait.');
    hand.append(el('p', expected.propagation_note));
  }
  const provenance = section(container, 'Provenance');
  for (const value of scenario?.input_provenance ?? []) provenance.append(el('p', `${value.input_class}: ${value.scope}. ${value.description}`));
  const details = el('details'); details.append(el('summary', 'Complete engine provenance'));
  details.append(el('pre', JSON.stringify(result.provenance, null, 2))); provenance.append(details);
  return { destroy() { container.replaceChildren(); } };
}
