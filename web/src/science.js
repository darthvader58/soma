const known = value => value !== null && value !== undefined && value !== '';
const text = value => known(value) ? String(value) : 'Unknown';
const numeric = value => typeof value === 'number' && Number.isFinite(value);
const el = (tag, value, cls) => {
  const node = document.createElement(tag);
  if (value !== undefined) node.textContent = text(value);
  if (cls) node.className = cls;
  return node;
};
const interval = value => value ? `${text(value.start_utc)} to ${text(value.end_utc)}` : 'Unknown';

// A missing record breaks the drawn line; no scientific values are interpolated.
export function plotSegments(samples, x, y) {
  const segments = [];
  let current = [];
  for (const sample of samples ?? []) {
    const a = x(sample);
    const b = y(sample);
    if (!numeric(a) || !numeric(b)) {
      if (current.length) segments.push(current);
      current = [];
    } else current.push([a, b]);
  }
  if (current.length) segments.push(current);
  return segments;
}

export function scienceViewModel(environment, epoch, role = 'panel') {
  const profile = environment?.horizons?.[role];
  return {
    profile,
    directions: (environment?.tracks ?? []).filter(track => track.observer_role === role).map(track => ({
      target: track.target === 'EARTH' ? 'Earth center (not a station)' : track.target,
      definition: track.target_definition,
      sample: track.samples?.find(sample => sameDisplayEpoch(sample.epoch_utc, epoch)),
    })),
    solar: environment?.solar_samples?.find(sample => sameDisplayEpoch(sample.epoch_utc, epoch)),
    power: environment?.power_samples?.find(sample => sameDisplayEpoch(sample.epoch_utc, epoch)),
    battery: environment?.battery?.samples?.find(sample => sameDisplayEpoch(sample.epoch_utc, epoch)),
    decisions: (environment?.contact_decisions ?? []).map(decision => ({
      ...decision,
      reasons: decision.reasons?.length ? decision.reasons : ['Unknown: no decision reason supplied'],
    })),
    contacts: environment?.contacts ?? [],
  };
}

function table(parent, headings, rows, empty) {
  if (!rows.length) {
    parent.append(el('p', empty, 'muted'));
    return;
  }
  const wrapper = el('div', undefined, 'science-table-scroll');
  const grid = el('table');
  const head = el('thead');
  const tr = el('tr');
  for (const label of headings) {
    const th = el('th', label);
    th.scope = 'col';
    tr.append(th);
  }
  head.append(tr);
  grid.append(head);
  const body = el('tbody');
  for (const row of rows) {
    const line = el('tr');
    for (const value of row) line.append(el('td', value));
    body.append(line);
  }
  grid.append(body);
  wrapper.append(grid);
  parent.append(wrapper);
}
function plot(parent, samples, x, y, bounds, title, xlabel, ylabel, markers = []) {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  const screenX = value => 50 + 572 * (value - bounds[0]) / (bounds[1] - bounds[0] || 1);
  const screenY = value => 202 - 186 * (value - bounds[2]) / (bounds[3] - bounds[2] || 1);
  svg.setAttribute('viewBox', '0 0 640 240');
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', title);
  svg.classList.add('science-plot');
  const label = document.createElementNS(ns, 'title');
  label.textContent = title;
  svg.append(label);
  const line = document.createElementNS(ns, 'path');
  line.setAttribute('d', 'M50 16V202H622');
  line.setAttribute('class', 'plot-axis');
  svg.append(line);
  for (const points of plotSegments(samples, x, y)) {
    const path = document.createElementNS(ns, 'path');
    path.setAttribute('d', points.map(([a, b], i) => `${i ? 'L' : 'M'}${screenX(a)} ${screenY(b)}`).join(' '));
    path.setAttribute('class', 'plot-data');
    svg.append(path);
    for (const [a, b] of points) {
      const dot = document.createElementNS(ns, 'circle');
      dot.setAttribute('cx', String(screenX(a)));
      dot.setAttribute('cy', String(screenY(b)));
      dot.setAttribute('r', '3');
      dot.setAttribute('class', 'plot-sample');
      svg.append(dot);
    }
  }
  for (const [value, px, py] of [[`${bounds[3]} ${ylabel}`, 8, 12], [`${bounds[2]}`, 8, 204], [xlabel, 50, 232]]) {
    const label = document.createElementNS(ns, 'text');
    label.setAttribute('x', px);
    label.setAttribute('y', py);
    label.textContent = value;
    svg.append(label);
  }
  const placedLabels = [];
  for (const [index, marker] of markers.entries()) {
    const direction = marker.sample?.direction;
    if (!numeric(direction?.azimuth_deg) || !numeric(direction?.elevation_deg)) continue;
    const px = screenX(direction.azimuth_deg);
    const py = screenY(direction.elevation_deg);
    const circle = document.createElementNS(ns, 'circle');
    circle.setAttribute('cx', px);
    circle.setAttribute('cy', py);
    circle.setAttribute('r', '5');
    circle.setAttribute('class', 'plot-endpoint');
    const tooltip = document.createElementNS(ns, 'title');
    tooltip.textContent = `${marker.target}: ${text(marker.sample.classification)} / ${text(marker.sample.classification_reason)}`;
    circle.append(tooltip);
    svg.append(circle);
    const labelX = Math.min(px + 7, 490);
    const preferredY = Math.max(25, py - 9);
    let labelY = preferredY;
    for (let attempt = 0; attempt < 12; attempt++) {
      if (!placedLabels.some(item => Math.abs(item.x - labelX) < 110 && Math.abs(item.y - labelY) < 22)) break;
      labelY = preferredY + (attempt % 2 === 0 ? 1 : -1) * (Math.floor(attempt / 2) + 1) * 22;
    }
    placedLabels.push({ x: labelX, y: labelY });
    if (labelY !== preferredY) {
      const leader = document.createElementNS(ns, 'path');
      const attachmentX = px > labelX ? labelX + 100 : labelX - 4;
      leader.setAttribute('d', `M${px} ${py}L${attachmentX} ${labelY - 5}`);
      leader.setAttribute('class', 'plot-label-leader');
      svg.append(leader);
    }
    const label = document.createElementNS(ns, 'text');
    label.setAttribute('x', labelX);
    label.setAttribute('y', labelY);
    label.textContent = marker.target === 'SUN' ? 'Sun'
      : marker.target === 'Earth center (not a station)' ? 'Earth center'
      : `Endpoint ${index + 1}`;
    svg.append(label);
  }
  parent.append(svg);
}

export function renderScience(container, { environment, selectedTime, fixtureBacked = true }) {
  let role = 'panel'; let epoch = selectedTime;
  function render() {
    container.replaceChildren(); container.classList.add('science-display');
    container.append(el('p', fixtureBacked ? 'Fixture-backed engine diagnostic. Graphics read stored samples only.' : 'Engine diagnostic. Graphics read stored samples only.', 'notice'));
    if (!environment) { container.append(el('p', 'Unknown: no environment diagnostic is available.')); return; }
    container.append(el('p', 'Directional inset only. Renderer registration is blocked; no scientific overlays are placed on the Moon.'));
    const label = el('label', 'Observer height '); const select = el('select'); select.setAttribute('aria-label', 'Horizon observer height');
    for (const value of ['panel','antenna']) { const option=el('option', value === 'panel' ? 'Panel' : 'Antenna'); option.value=value; select.append(option); } select.value=role;
    select.addEventListener('change', () => {
      role = select.value;
      const focused = document.activeElement === select;
      render();
      if (focused) container.querySelector('select').focus();
    });
    label.append(select);container.append(label);
    const model=scienceViewModel(environment,epoch,role); const profile=model.profile; const site=profile?.site;
    container.append(el('p', `Selected UTC: ${text(epoch)}. Exact stored samples only; no interpolation.`, 'science-selected-time'));
    container.append(el('h3', `${role === 'panel' ? 'Panel' : 'Antenna'} horizon`));
    const terrain=environment.provenance?.terrain ?? [];
    const hashes = terrain.flatMap(item => [
      item.sha256, item.source_sha256, item.source_hash, item.elevation_sha256, item.count_sha256,
      ...Object.values(item.files ?? {}).map(file => file.sha256),
    ]).filter(known);
    container.append(el('p', `Height: ${text(site?.height_m)} m · Frame: ${text(site?.frame ?? environment.frame)} · Datum: ${text(site?.elevation_datum)}. Source hashes: ${[...new Set(hashes)].join(', ') || 'Unknown'}. Horizon cache SHA-256: ${text(profile?.cache_key)}.`, 'science-provenance'));
    container.append(el('p', `Converged: ${text(profile?.converged)}. Unknown horizon samples remain gaps. A distant-target horizon does not assess a finite spacecraft link.`));
    const elevations = [...(profile?.bands ?? []).map(sample => sample.elevation_deg),
      ...model.directions.map(item => item.sample?.direction?.elevation_deg)].filter(numeric);
    const lower = elevations.length ? Math.floor(Math.min(...elevations)) - 1 : -5;
    const upper = elevations.length ? Math.ceil(Math.max(...elevations)) + 1 : 5;
    plot(container,profile?.bands,s=>s.azimuth_deg,s=>s.elevation_deg,[0,360,lower,upper],`${role} engine horizon; unknown samples are gaps`,'Azimuth 0 to 360° east of north','elevation °',model.directions);
    const horizonDetails=el('details');horizonDetails.append(el('summary','Horizon sample values'));
    table(horizonDetails,['Azimuth (°)','Elevation (°)','Unknown samples','Quality'],(profile?.bands??[]).map(s=>[s.azimuth_deg,s.elevation_deg,s.unknown_samples,s.quality_flags?.join('; ')]),'No horizon samples supplied.');container.append(horizonDetails);
    container.append(el('h3','Engine endpoint directions'));
    table(container,['Target / definition','Azimuth (°)','Elevation (°)','Range (m)','Classification / reason'],model.directions.map(d=>[`${text(d.target)} / ${text(d.definition)}`,d.sample?.direction?.azimuth_deg,d.sample?.direction?.elevation_deg,d.sample?.direction?.range_m,`${text(d.sample?.classification)} / ${text(d.sample?.classification_reason)}`]),'No endpoint directions supplied for this observer.');
    container.append(el('p','Earth-center direction does not establish visibility or service at a configured ground station.'));
    container.append(el('h3','Solar disk visible fraction'));
    container.append(el('p',`Selected sample: ${text(model.solar?.visible_fraction)}. Status: ${text(model.solar?.status)}. Method: ${text(model.solar?.method)}. Bounds: ${text(model.solar?.lower_bound)} to ${text(model.solar?.upper_bound)}.`));
    const samples=environment.solar_samples??[]; const times=samples.map(s=>Date.parse(s.epoch_utc)).filter(Number.isFinite);
    plot(container,samples,s=>Date.parse(s.epoch_utc),s=>s.visible_fraction,[times[0]??0,times.at(-1)??1,0,1],'Engine solar disk visible fraction; unknown samples are gaps',`${text(samples[0]?.epoch_utc)} to ${text(samples.at(-1)?.epoch_utc)} UTC`,'fraction');
    const details=el('details');details.append(el('summary','Solar sample values'));table(details,['Epoch (UTC)','Visible fraction','Lower / upper bound','Status / method'],samples.map(s=>[s.epoch_utc,s.visible_fraction,`${text(s.lower_bound)} / ${text(s.upper_bound)}`,`${text(s.status)} / ${text(s.method)}`]),'Unknown: no solar disk samples supplied.');container.append(details);
    container.append(el('h3', 'Engine electrical power and battery'));
    container.append(el('p', 'This diagnostic battery trace includes base load only. The delivery result contains the selected schedule battery history including radio activity.'));
    container.append(el('p', `Selected generated power: ${text(model.power?.generated_power_w)} W. Selected stored energy: ${text(model.battery?.stored_energy_wh)} Wh. Battery status: ${text(environment.battery?.status)}. These records do not establish schedule energy feasibility.`));
    table(container, ['Epoch (UTC)', 'Generated power (W)', 'Status / method'],
      (environment.power_samples ?? []).map(sample => [
        sample.epoch_utc, sample.generated_power_w,
        `${text(sample.status)} / ${text(sample.method)}`,
      ]), 'Unknown: no electrical power samples supplied.');
    table(container, ['Epoch (UTC)', 'Stored energy (Wh)', 'Trace status'],
      (environment.battery?.samples ?? []).map(sample => [
        sample.epoch_utc, sample.stored_energy_wh,
        environment.battery?.status,
      ]), 'Unknown: no battery samples supplied.');
    const batteryIntervals = environment.battery?.intervals ?? [];
    if (batteryIntervals.length) {
      const intervalDetails = el('details');
      intervalDetails.append(el('summary', 'Engine battery interval records'));
      intervalDetails.append(el('pre', JSON.stringify(batteryIntervals, null, 2)));
      container.append(intervalDetails);
    }
    table(container, ['Battery violation', 'Bin', 'Declared constraint'],
      (environment.battery?.violations ?? []).map(item => [item.reason, item.bin_index, JSON.stringify(item)]),
      'No battery violation records supplied. Missing inputs remain Unknown.');
    container.append(el('h3','Usable contacts (not selected transmissions)'));
    const stations=environment.scenario?.profiles?.stations??[]; const endpoint=id=>stations.some(s=>s.id===id)?`${id} (configured Earth station)`:text(id);
    table(container,['Contact / endpoints','Source transmit window (UTC)','Rate method / net bps','Service / quality'],model.contacts.map(c=>[`${text(c.contact_id)}: ${endpoint(c.sender)} to ${endpoint(c.receiver)}`,interval(c.source_transmit_window),`${text(c.rate_method)} / ${text(c.payload_rate_bps)}`,`${text(c.service_provenance)} / ${text(c.quality_flags?.join('; '))}`]),'No usable contacts supplied.');
    container.append(el('h3','Contact construction decisions'));
    table(container,['Candidate','Decision','Reasons'],model.decisions.map(d=>[d.candidate_id,d.status,d.reasons.join('; ')]),'Unknown: no contact decision reasons supplied.');
    container.append(el('p','Selected transmissions appear only in the delivery result allocations. A geometric opportunity or blocked decision is not a transmission.'));
    for(const [heading,items] of [['Assumptions',environment.assumptions],['Warnings',environment.warnings]]) {container.append(el('h3',heading));const list=el('ul');for(const item of items??[])list.append(el('li',item));if(!items?.length)list.append(el('li','None supplied.'));container.append(list);}
  }
  render();return {setTime(value){epoch=value;render();},destroy(){container.replaceChildren();}};
}
import { sameDisplayEpoch } from './display-time.js';

