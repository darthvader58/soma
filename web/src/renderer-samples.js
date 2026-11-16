import { sameDisplayEpoch } from './display-time.js';

function epochValue(epoch) {
  const match = typeof epoch === 'string' && epoch.match(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.(\d{1,6}))?(?:Z|[+-]\d{2}:\d{2})$/);
  const milliseconds = Date.parse(epoch);
  return match && Number.isFinite(milliseconds)
    ? BigInt(milliseconds) * 1000n + BigInt((match[1] ?? '').padEnd(6, '0').slice(3)) : undefined;
}

function contains(interval, epoch) {
  const time = epochValue(epoch), start = epochValue(interval?.start_utc), end = epochValue(interval?.end_utc);
  return time !== undefined && start !== undefined && end !== undefined && start <= time && time < end;
}

export function rendererSamplesAtTime(display, epoch, relayIds = []) {
  const registration = display?.registration;
  const states = (display?.renderer_states ?? []).filter(state => relayIds.includes(state.target)
    && sameDisplayEpoch(state.epoch, epoch) && state.epoch_format === 'rfc3339' && state.time_scale === 'UTC'
    && state.origin === 'MOON' && state.frame === registration?.renderer_frame
    && state.source_frame === registration?.source_frame && state.position_unit === 'm'
    && state.transform_ref === 'renderer-registration.json' && sameDisplayEpoch(state.transform_epoch_utc, state.epoch)
    && typeof state.provenance_label === 'string' && state.provenance_label.length > 0
    && Array.isArray(state.position) && state.position.length === 3 && state.position.every(Number.isFinite));
  const points = new Map(states.map(state => [state.target, state.position]));
  for (const point of display?.surface_points ?? []) {
    if (point.frame === registration?.renderer_frame && point.origin === 'MOON'
      && point.position_unit === 'm' && point.epoch === null && point.time_scale === 'static'
      && Array.isArray(point.position_m) && point.position_m.length === 3 && point.position_m.every(Number.isFinite)) {
      if (!points.has(point.id)) points.set(point.id, Array.isArray(point.antenna_position_m) && point.antenna_position_m.length === 3 && point.antenna_position_m.every(Number.isFinite) ? point.antenna_position_m : point.position_m);
    }
  }
  const links = [];
  for (const contact of display?.contacts ?? []) {
    if (!contains(contact.source_transmit_window, epoch) || !points.has(contact.sender) || !points.has(contact.receiver)) continue;
    const allocation = (display.allocations ?? []).find(item => item.contact_id === contact.contact_id && contains(item.source_transmit_interval, epoch));
    links.push({ contact, allocation, positions: [points.get(contact.sender), points.get(contact.receiver)] });
  }
  return { states, links };
}
