const el = (tag, text, className) => {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
};

export function renderTimeline(container, { scenario, result, contacts = [], expected, sampleEpochs = [], onTimeChange = () => {} }) {
  container.replaceChildren();
  const horizon = scenario.analysis_horizon;
  const start = Date.parse(horizon.start_utc), end = Date.parse(horizon.end_utc);
  const validHorizon = Number.isFinite(start) && Number.isFinite(end) && end > start;
  let selectedTime = validHorizon ? horizon.start_utc : null;
  const controls = el('div', undefined, 'timeline-controls');
  const label = el('label', 'Selected time (UTC / stated offset)');
  const slider = el('input'); slider.type = 'range'; slider.min = '0'; slider.max = '10000'; slider.step = '1'; slider.value = '0';
  slider.disabled = !validHorizon;
  slider.setAttribute('aria-label', 'Selected timeline time (UTC / stated offset)'); label.append(slider);
  const output = el('output', horizon.start_utc, 'timeline-time');
  const scale = el('span', undefined, 'muted');
  const samples = el('select');
  samples.setAttribute('aria-label', 'Stored engine sample (UTC / stated offset)');
  const noSample = el('option', 'Select an exact stored engine sample'); noSample.value = ''; samples.append(noSample);
  for (const epoch of [...new Set(sampleEpochs)].filter(epoch => {
    const time = Date.parse(epoch); return Number.isFinite(time) && time >= start && time <= end;
  })) {
    const option = el('option', epoch); option.value = epoch; samples.append(option);
  }
  function update(epoch, notify) {
    const time = Date.parse(epoch);
    if (!validHorizon || !Number.isFinite(time) || time < start || time > end) return;
    selectedTime = epoch;
    slider.value = String(Math.round((time - start) / (end - start) * 10000));
    output.textContent = epoch; slider.setAttribute('aria-valuetext', epoch);
    samples.value = sampleEpochs.find(sample => sameDisplayEpoch(sample, epoch)) ?? '';
    scale.textContent = epoch.endsWith('Z') ? 'UTC' : `UTC${epoch.slice(-6)}`;
    if (notify) onTimeChange(epoch);
  }
  slider.addEventListener('input', () => {
    const fraction = Number(slider.value) / 10000;
    update(fraction === 0 ? horizon.start_utc : fraction === 1 ? horizon.end_utc : new Date(start + (end - start) * fraction).toISOString(), true);
  });
  controls.append(label, output, scale); container.append(controls);
  if (samples.options.length > 1) {
    const sampleLabel = el('label', 'Stored engine sample (UTC / stated offset)');
    sampleLabel.append(samples); controls.append(sampleLabel);
    samples.addEventListener('change', () => { if (samples.value) update(samples.value, true); });
  }
  container.append(el('p', 'Endpoints retain their supplied timestamps and timezone offsets. Intermediate slider times are displayed in UTC to millisecond precision. Scrubbing reads records; it does not run analysis.', 'muted'));
  if (!validHorizon) {
    output.textContent = 'Timeline unavailable';
    container.append(el('p', 'Enter an analysis end later than its valid start before scrubbing. No map time was changed.', 'notice'));
    return { setTime() {}, getTime: () => null, destroy() { container.replaceChildren(); } };
  }
  function lane(title, interval, kind, parent = container) {
    const row = el('div', undefined, 'timeline-lane');
    row.append(el('p', title));
    const track = el('div', undefined, 'timeline-track');
    const segment = el('div', undefined, kind);
    const left = Math.max(0, (Date.parse(interval.start_utc) - start) / (end - start) * 100);
    const right = Math.min(100, (Date.parse(interval.end_utc) - start) / (end - start) * 100);
    segment.style.marginLeft = `${left}%`; segment.style.width = `${Math.max(0, right - left)}%`;
    segment.setAttribute('aria-hidden', 'true'); track.append(segment); row.append(track);
    row.append(el('small', `${interval.start_utc} to ${interval.end_utc}`)); parent.append(row);
  }
  const engineContacts = result?.contacts ?? [];
  for (const contact of engineContacts) {
    const selected = (result.allocations ?? []).some(value => value.contact_id === contact.contact_id);
    lane(`Engine available contact: ${contact.sender} to ${contact.receiver} / ${contact.contact_id}. ${selected ? 'Allocated below.' : 'Unused; reason Unknown.'}`, contact.source_transmit_window, 'timeline-window');
  }
  for (const contact of contacts.filter(value => !engineContacts.some(engine => engine.contact_id === value.contact_id))) lane(`Synthetic source-window reference: ${contact.sender} to ${contact.receiver} / ${contact.contact_id}`, contact.source_transmit_window, 'timeline-window');
  if (!result?.allocations?.length) container.append(el('p', 'No computed transmission supplied. Read the engine status and explanation; missing allocations do not establish success.', 'notice'));
  const scheduled = el('details');
  scheduled.append(el('summary', `Scheduled transmissions and storage (${result?.allocations?.length ?? 0} transmissions)`));
  if (result?.allocations?.length) container.append(scheduled);
  for (const allocation of result?.allocations ?? []) {
    const contact = engineContacts.find(value => value.contact_id === allocation.contact_id);
    const endpoints = contact ? `${contact.sender} to ${contact.receiver}` : 'Unknown endpoints';
    lane(`Engine source transmission: ${endpoints} / ${allocation.contact_id}`, allocation.source_transmit_interval, 'timeline-allocation', scheduled);
    lane(`Engine receiver payload occupancy: ${endpoints}. Bytes available ${allocation.byte_available_utc}`, allocation.receiver_occupancy_interval, 'timeline-allocation', scheduled);
  }
  for (const storage of result?.storage_intervals ?? []) lane(`Engine storage reservation: ${storage.node_id} / ${storage.chunk_id} (${storage.byte_length.toLocaleString('en-US')} bytes)`, storage.interval, 'timeline-storage', scheduled);
  if (expected?.allocations?.length) {
    container.append(el('p', 'Hand calculation preview only. Energy, geometry and replay not evaluated.', 'notice'));
    for (const allocation of expected.allocations) lane(`Synthetic expected transmission: ${allocation.contact_id}`, allocation.source_transmit_interval, 'timeline-expected');
    for (const wait of expected.storage_intervals ?? []) lane(`Synthetic expected storage: ${wait.node_id} (${wait.byte_length.toLocaleString('en-US')} bytes)`, wait.interval, 'timeline-storage');
  }
  update(horizon.start_utc, false);
  return { setTime(epoch) { update(epoch, false); }, getTime: () => selectedTime, destroy() { container.replaceChildren(); } };
}
import { sameDisplayEpoch } from './display-time.js';
