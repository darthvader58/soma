import { createDeliveryClient, deliveryPackageBytes } from './delivery-client.js';
import { renderTimeline } from './timeline.js';
import { describeStatus, explainResult, formatValue } from './result.js';
import { renderScience } from './science.js';
import { displayTimeText } from './display.js';
import { validateScenario } from './contracts.js';

const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const utcInput = epoch => Number.isFinite(Date.parse(epoch)) ? new Date(epoch).toISOString().slice(0, 19) : '';
const download = (bytes, name, type) => {
  const url = URL.createObjectURL(new Blob([bytes], { type })), link = document.createElement('a');
  link.href = url; link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
};

export function createDeliveryWorkspace({ root, apiBase = '/api', getCatalog = () => [], getInspectedSite = () => undefined,
  onGeometry = () => {}, onMap = () => {}, onTime = () => {}, onFocus = () => {} }) {
  const toolbar = document.createElement('section');
  toolbar.className = 'study-toolbar delivery-toolbar';
  toolbar.dataset.analysisTool = 'delivery';
  toolbar.hidden = true;
  toolbar.setAttribute('aria-label', 'Data delivery planning');
  toolbar.innerHTML = `<div class="analysis-name"><strong>Lunar data delivery</strong><span>Plan last-byte arrival at the configured Earth network.</span></div><div class="delivery-primary-actions"><div class="study-run"><button id="plan-delivery" class="research-primary" type="button" aria-describedby="delivery-blocker" disabled>Plan delivery</button><button id="stop-delivery" type="button" hidden>Stop waiting</button><button id="delivery-supported-site" type="button" disabled>Use supported south-pole site</button></div><p id="delivery-blocker" role="status" hidden></p></div>`;

  const status = document.createElement('div');
  status.className = 'research-status delivery-status';
  status.dataset.analysisTool = 'delivery'; status.hidden = true;
  status.innerHTML = '<p id="delivery-status" role="status" aria-live="polite">Checking the Python delivery service and declared modeling limits.</p><span id="delivery-elapsed" hidden></span><span id="delivery-budget"></span>';

  const inputs = document.createElement('aside');
  inputs.className = 'object-panel delivery-inputs'; inputs.id = 'delivery-inputs';
  inputs.dataset.analysisTool = 'delivery'; inputs.hidden = true;
  inputs.setAttribute('aria-label', 'Delivery task and network inputs');
  inputs.innerHTML = '<h2>Delivery task</h2><p class="panel-description">A lander, a finite dataset and an absolute last-byte deadline.</p><div id="delivery-form"><p>Hardware, service and source coverage must be declared by the Python service before planning.</p></div>';

  const inspector = document.createElement('aside');
  inspector.className = 'inspector-panel delivery-inspector';
  inspector.dataset.analysisTool = 'delivery'; inspector.hidden = true;
  inspector.setAttribute('aria-label', 'Earth delivery outcome');
  inspector.innerHTML = '<h2>Earth delivery outcome</h2><div id="delivery-outcome"><p>Choose Plan delivery to calculate this task in Python. To recover an unsupported location, choose Use supported south-pole site above, then Plan delivery.</p><p>Camera controls inspect views; they do not calculate a delivery plan.</p></div><div id="delivery-profiles"></div>';

  const dock = document.createElement('section');
  dock.className = 'time-dock delivery-dock';
  dock.dataset.analysisTool = 'delivery'; dock.hidden = true;
  dock.setAttribute('aria-label', 'Delivery timeline, resources and evidence');
  dock.innerHTML = '<div class="delivery-section-heading"><h2>Transfers, waiting and Earth arrival</h2><div class="delivery-downloads"><button id="delivery-export-scenario" type="button" disabled>Scenario JSON</button><button id="delivery-export-result" type="button" disabled>Delivery JSON</button><button id="delivery-export-package" type="button" disabled>Python run package</button><button id="delivery-geometry" type="button">Inspect geometry inputs</button></div></div><p class="sample-note">Source transmission, receiver occupancy and byte availability retain their separate Python timestamps. Missing results stay unknown.</p><div id="delivery-timeline"><p>No scheduled transmissions are available until Python completes a plan.</p></div><p id="delivery-resource-readout" class="sample-note"></p><div id="delivery-evidence"></div>';
  dock.querySelector('#delivery-geometry').addEventListener('click', onGeometry);

  root.append(toolbar, status, inputs, inspector, dock);
  const $ = id => root.querySelector(`#${id}`);
  const client = createDeliveryClient({ baseUrl: `${apiBase.replace(/\/$/, '')}/research/delivery` });
  let capabilities, scenario, artifact, stale = false, running = false, revision = 0, active = false, timeline, epoch;
  const options = { chunk_bytes: 16_777_216, bin_s: 60, time_limit_s: 10 };
  const message = value => { $('delivery-status').textContent = value; };
  const hardware = () => scenario.profiles.hardware.find(item => item.id === scenario.hardware_profile_ref);
  let waitingTimer;
  function stopTimer() { clearInterval(waitingTimer); waitingTimer = undefined; $('delivery-elapsed').hidden = true; $('delivery-elapsed').textContent = ''; }
  const supportedSite = site => {
    const coverage = capabilities.coverage;
    return Number.isFinite(site.latitude_deg) && Number.isFinite(site.longitude_deg_east) &&
      site.latitude_deg >= coverage.latitude_bounds_deg[0] && site.latitude_deg <= coverage.latitude_bounds_deg[1] &&
      site.longitude_deg_east >= coverage.longitude_bounds_deg_east[0] && site.longitude_deg_east <= coverage.longitude_bounds_deg_east[1];
  };
  function invalidate() {
    stopTimer();
    revision += 1; stale = Boolean(artifact);
    if (running) { client.cancel(); running = false; }
    $('stop-delivery').hidden = true;
    for (const id of ['delivery-export-result', 'delivery-export-package']) $(id).disabled = true;
    message(artifact ? 'Inputs changed. The displayed delivery belongs to the previous scenario; plan delivery to update.' : 'Ready to calculate this declared delivery task in Python.');
    if ($('delivery-profile-json')) $('delivery-profile-json').textContent = JSON.stringify(scenario.profiles, null, 2);
    renderProfiles();
    refreshBudget();
  }
  function refreshBudget() {
    if (!scenario || !capabilities) return;
    const limits = capabilities.limits, coverage = capabilities.coverage;
    const duration = (Date.parse(scenario.analysis_horizon.end_utc) - Date.parse(scenario.analysis_horizon.start_utc)) / 1000;
    const bytes = scenario.data_volume.value * (scenario.data_volume.unit === 'MiB' ? 1_048_576 : 1);
    const errors = [];
    for (const input of inputs.querySelectorAll('input[type="number"]')) if (input.value === '' || !Number.isFinite(Number(input.value))) errors.push(`Enter a finite number for ${input.parentElement.firstChild.textContent.trim()}.`);
    const contract = validateScenario(scenario);
    if (!contract.valid) errors.push(`Complete the declared inputs: ${contract.errors.join('; ')}`);
    const battery = hardware().battery;
    if (battery.initial_energy_wh > battery.capacity_wh || battery.reserve_wh > battery.capacity_wh) errors.push('Initial energy and reserve must not exceed battery capacity.');
    const start = Date.parse(scenario.analysis_horizon.start_utc), end = Date.parse(scenario.analysis_horizon.end_utc);
    const ready = Date.parse(scenario.data_ready_utc), deadline = Date.parse(scenario.deadline_utc);
    if (![start, end, ready, deadline].every(Number.isFinite)) errors.push('Enter complete UTC dates for readiness, deadline and analysis interval.');
    else if (ready < start || deadline < ready || deadline > end) errors.push('Readiness and last-byte deadline must lie in order within the analysis interval.');
    if (Number.isFinite(start) && Number.isFinite(end) && (start < Date.parse(coverage.start_utc) || end > Date.parse(coverage.end_utc))) errors.push('The requested analysis interval is outside the published provider date coverage.');
    if (!Number.isFinite(duration) || duration <= 0 || duration > limits.max_duration_s) errors.push(`Analysis horizon must be positive and at most ${limits.max_duration_s / 3600} hours.`);
    if (!Number.isSafeInteger(bytes) || bytes < 1 || bytes > limits.max_data_volume_bytes) errors.push(`Data volume must contain an integer from 1 to ${limits.max_data_volume_bytes.toLocaleString()} bytes.`);
    if (!scenario.route_families.length) errors.push('Select at least one route family.');
    if (!Number.isInteger(options.chunk_bytes) || options.chunk_bytes < 1 || Math.ceil(bytes / options.chunk_bytes) > limits.max_chunks) errors.push(`Choose an integer chunk size that requires at most ${limits.max_chunks} chunks.`);
    if (!Number.isInteger(options.bin_s) || options.bin_s < limits.min_bin_s || options.bin_s > limits.max_bin_s) errors.push(`Planning bin must be an integer from ${limits.min_bin_s} to ${limits.max_bin_s} seconds.`);
    if (!Number.isFinite(options.time_limit_s) || options.time_limit_s < 1 || options.time_limit_s > limits.max_solver_time_s) errors.push(`Solver limit must be 1 to ${limits.max_solver_time_s} seconds.`);
    if (!supportedSite(scenario.lander)) errors.push('This location is outside the declared numerical terrain coverage. Choose Use supported south-pole site to recover; global geometry remains available in the Geometry tool.');
    $('delivery-input-errors').textContent = errors.join(' ');
    $('delivery-input-errors').hidden = !errors.length;
    $('plan-delivery').disabled = running || !capabilities.ready || Boolean(errors.length);
    $('delivery-blocker').textContent = errors.length ? `Plan delivery blocked: ${errors.join(' ')}` : !capabilities.ready ? 'Plan delivery unavailable: Python compute or source data are not ready.' : '';
    $('delivery-blocker').hidden = !$('delivery-blocker').textContent;
    if (errors.length && !running) message(`Plan delivery blocked: ${errors.join(' ')}`);
    $('delivery-budget').textContent = `${scenario.data_volume.value} ${scenario.data_volume.unit} · ${Number.isFinite(duration) ? duration / 3600 : '?'} h · ${scenario.route_families.length} route ${scenario.route_families.length === 1 ? 'family' : 'families'}`;
  }
  function renderForm() {
    const profile = hardware(), coverage = capabilities.coverage;
    const number = (label, path, value, minimum) => `<label>${label}<input type="number" step="any" data-delivery-path="${path}" value="${value}" ${minimum === undefined ? '' : `min="${minimum}"`}></label>`;
    const date = (label, path, value) => `<label>${label}<input type="datetime-local" step="1" data-delivery-path="${path}" value="${utcInput(value)}"></label>`;
    $('delivery-form').innerHTML = `<p class="delivery-coverage">Terrain coverage: ${coverage.latitude_bounds_deg.join(' to ')}° N; ${coverage.longitude_bounds_deg_east.join(' to ')}° E. ${coverage.start_utc} to ${coverage.end_utc}. At most ${capabilities.limits.max_duration_s / 3600} hours per plan.</p>
      <div class="delivery-form-actions"><button id="delivery-use-inspected" type="button">Use inspected geometry site</button><button id="delivery-restore" type="button">Restore declared inputs</button></div>
      <p id="delivery-input-errors" class="delivery-input-errors" role="alert" hidden></p>
      <h3>Lander location</h3><div class="delivery-fields">
      ${number('Delivery latitude (° N)', 'lander.latitude_deg', scenario.lander.latitude_deg)}${number('Delivery longitude (° E)', 'lander.longitude_deg_east', scenario.lander.longitude_deg_east)}
      ${number('Requested elevation above reference sphere (m)', 'lander.elevation_m', scenario.lander.elevation_m)}${number('Delivery antenna height (m)', 'lander.antenna_height_m', scenario.lander.antenna_height_m, 0)}${number('Delivery panel height (m)', 'lander.panel_height_m', scenario.lander.panel_height_m, 0)}</div>
      <p class="delivery-note">Python resolves numerical DEM ground elevation for this provider. The request and resolved analysis point are both retained; a rendered pick is not numerical elevation.</p>
      <h3>Dataset and deadline</h3><div class="delivery-fields">
      ${number('Delivery data volume', 'data_volume.value', scenario.data_volume.value, 1)}<label>Delivery volume unit<select data-delivery-path="data_volume.unit"><option value="MiB" ${scenario.data_volume.unit === 'MiB' ? 'selected' : ''}>MiB</option><option value="byte" ${scenario.data_volume.unit === 'byte' ? 'selected' : ''}>byte</option></select></label>
      ${date('Data ready UTC', 'data_ready_utc', scenario.data_ready_utc)}${date('Last-byte deadline UTC', 'deadline_utc', scenario.deadline_utc)}${date('Delivery analysis starts UTC', 'analysis_horizon.start_utc', scenario.analysis_horizon.start_utc)}${date('Delivery analysis ends UTC', 'analysis_horizon.end_utc', scenario.analysis_horizon.end_utc)}</div>
      <p class="delivery-note">Dates use UTC. Changes do not move the absolute deadline or service calendars automatically.</p><button id="delivery-apply-service" type="button">Use analysis interval as assumed service</button>
      <h3>Route families</h3><div class="delivery-routes">${[['direct_to_earth', 'Direct to Earth'], ['single_lunar_relay', 'One lunar store-and-forward relay']].map(([value, label]) => `<label><input type="checkbox" data-delivery-route="${value}" ${scenario.route_families.includes(value) ? 'checked' : ''}>${label}</label>`).join('')}</div>
      <h3>Hardware and energy</h3><p>Delivery hardware profile: <strong>${esc(profile.id)}</strong> · ${esc(profile.input_class)}. The provider supplies this profile; edit its declared parameters below.</p>
      <div class="delivery-fields">${number('Initial battery energy (Wh)', 'hardware.battery.initial_energy_wh', profile.battery.initial_energy_wh, 0)}${number('Battery reserve (Wh)', 'hardware.battery.reserve_wh', profile.battery.reserve_wh, 0)}${number('Battery capacity (Wh)', 'hardware.battery.capacity_wh', profile.battery.capacity_wh, 0)}${number('Base electrical load (W)', 'hardware.base_load_w', profile.base_load_w, 0)}${number('Fixed panel area (m²)', 'hardware.panel.area_m2', profile.panel.area_m2, 0)}${number('Panel efficiency', 'hardware.panel.efficiency', profile.panel.efficiency, 0)}</div>
      <h3>Numerical budgets</h3><div class="delivery-fields">${number('Planning bin (s)', 'options.bin_s', options.bin_s, capabilities.limits.min_bin_s)}${number('Solver time limit (s)', 'options.time_limit_s', options.time_limit_s, 1)}${number('Chunk bytes', 'options.chunk_bytes', options.chunk_bytes, 1)}</div>
      <details><summary>Complete declared profiles and service</summary><p>Profiles are explicit assumptions or published inputs, not access to a booked network.</p><pre id="delivery-profile-json">${esc(JSON.stringify(scenario.profiles, null, 2))}</pre></details>`;
    for (const input of inputs.querySelectorAll('[data-delivery-path]')) input.addEventListener('input', () => {
      const path = input.dataset.deliveryPath.split('.');
      let target = path[0] === 'hardware' ? hardware() : path[0] === 'options' ? options : scenario;
      if (['hardware', 'options'].includes(path[0])) path.shift();
      const key = path.pop(); for (const part of path) target = target[part];
      if (input.type === 'number') target[key] = input.value === '' ? NaN : Number(input.value);
      else if (input.type === 'datetime-local') {
        const time = Date.parse(`${input.value}Z`);
        target[key] = Number.isFinite(time) ? new Date(time).toISOString().replace('.000Z', 'Z') : '';
      } else target[key] = input.value;
      invalidate();
      if (input.dataset.deliveryPath === 'hardware_profile_ref') renderForm();
    });
    for (const input of inputs.querySelectorAll('[data-delivery-route]')) input.addEventListener('change', () => {
      scenario.route_families = [...inputs.querySelectorAll('[data-delivery-route]:checked')].map(item => item.dataset.deliveryRoute); invalidate();
    });
    $('delivery-use-inspected').addEventListener('click', () => {
      const site = getInspectedSite();
      if (!site) { message('Inspect a geometry site first, then explicitly copy its declared inputs.'); return; }
      if (!supportedSite(site)) { message(`${site.name} is outside the delivery provider’s supported south-pole terrain coverage. The current delivery site, task and exports remain unchanged. Use Geometry to inspect this location, or choose Use supported south-pole site for delivery.`); return; }
      for (const key of ['latitude_deg', 'longitude_deg_east', 'elevation_m', 'antenna_height_m', 'panel_height_m']) scenario.lander[key] = site[key];
      invalidate(); renderForm(); message(`Copied ${site.name}. Terrain coverage and numerical ground resolution remain Python checks.`);
    });
    $('delivery-restore').addEventListener('click', () => { scenario = structuredClone(capabilities.scenario_template); invalidate(); renderForm(); });
    $('delivery-apply-service').addEventListener('click', () => {
      for (const group of Object.values(scenario.profiles)) for (const item of group) {
        if (item.service.input_class === 'assumed') item.service.windows = [structuredClone(scenario.analysis_horizon)];
        if (item.trajectory?.kind === 'synthetic_two_body_lunar_preset') item.trajectory.coverage = structuredClone(scenario.analysis_horizon);
      }
      invalidate(); renderForm(); message('Assumed service windows and synthetic trajectory coverage now use the explicitly chosen analysis interval. The deadline is unchanged.');
    });
    $('delivery-export-scenario').disabled = false;
    refreshBudget();
  }
  function table(title, headers, rows) {
    const section = document.createElement('section'); section.className = 'delivery-records';
    section.innerHTML = `<h3>${esc(title)}</h3><div class="delivery-table-scroll" role="region" aria-label="${esc(title)}" tabindex="0"><table><thead><tr>${headers.map(value => `<th>${esc(value)}</th>`).join('')}</tr></thead><tbody>${rows.map(row => `<tr>${row.map(value => `<td>${esc(formatValue(value))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
    return section;
  }
  function renderProfiles() {
    if (!scenario) return;
    if ($('delivery-profile-json')) $('delivery-profile-json').textContent = JSON.stringify(scenario.profiles, null, 2);
    const relay = scenario.profiles.relays.find(item => scenario.relay_refs.includes(item.id));
    $('delivery-profiles').innerHTML = `<h3>Declared network${stale ? ' · edited inputs' : ''}</h3><p>Rate method: ${esc(scenario.rate_method)}. Pointing: ${esc(scenario.pointing_assumption)}.</p><p>${esc(scenario.service_assumption_label)}</p><p>Hardware: ${esc(hardware().id)} · ${esc(hardware().input_class)}. Battery ${esc(hardware().battery.initial_energy_wh)} Wh initially; reserve ${esc(hardware().battery.reserve_wh)} Wh.</p>${relay ? `<p>Relay: ${esc(relay.id)} · ${esc(relay.trajectory.kind)} · ${relay.storage_capacity_bytes.toLocaleString()} bytes storage. No operational relay or LRO service is implied.</p>` : ''}<p>Ground stations: ${scenario.station_refs.map(esc).join(', ')}. Their declared service is not an operator allocation.</p>`;
  }
  function renderAtTime(value) {
    epoch = value;
    if (!artifact) return;
    $('delivery-resource-readout').textContent = `${stale ? 'Previous scenario. ' : ''}${displayTimeText(artifact.display, value)}`;
    renderScience($('delivery-science'), { environment: artifact.environment, selectedTime: value, fixtureBacked: false });
    if (active) onTime(value);
  }
  function renderArtifact() {
    const result = artifact.result, status = describeStatus(result);
    $('delivery-outcome').innerHTML = `<p class="delivery-outcome-code"><strong>${esc(status.label)}</strong></p><p>${esc(result.provenance.reason)}</p><dl class="delivery-facts"><dt>Unique bytes at the Earth network</dt><dd>${esc(formatValue(result.delivered_bytes, 'bytes'))}</dd><dt>Final byte arrives UTC</dt><dd>${esc(formatValue(result.final_byte_arrival_utc))}</dd><dt>Solver</dt><dd>${esc(result.solver_status)}</dd><dt>Fidelity</dt><dd>${esc(result.model_fidelity)}</dd><dt>Independent replay</dt><dd>${artifact.replay?.passed === true ? 'Passed' : 'No validated candidate supplied'}</dd><dt>Scenario SHA256</dt><dd>${esc(artifact.scenario_sha256)}</dd></dl><p>Earth delivery counts unique bytes received by an eligible configured station. It does not book an antenna or model onward terrestrial delivery.</p><p>Requested elevation: ${artifact.scenario.lander.elevation_m} m. Numerical analysis ground: ${esc(formatValue(artifact.environment.analysis_point?.elevation_m, 'm'))}.</p>`;
    const evidence = $('delivery-evidence'); evidence.replaceChildren();
    const explanation = document.createElement('details'); explanation.open = true;
    explanation.innerHTML = '<summary>Calculated route and waiting</summary>';
    for (const line of explainResult(result)) { const paragraph = document.createElement('p'); paragraph.textContent = line; explanation.append(paragraph); }
    evidence.append(explanation);
    const focus = document.createElement('section'); focus.className = 'delivery-focus';
    focus.innerHTML = '<h3>Inspect a transfer or wait</h3><p>Select an exact Python epoch and focus the scene. Positions remain unknown where Python supplied no matching stored sample.</p>';
    const focusButton = (label, epoch, mode) => {
      const button = document.createElement('button'); button.type = 'button'; button.textContent = label;
      button.addEventListener('click', () => { timeline.setTime(epoch); renderAtTime(epoch); if (active) onFocus(mode); });
      focus.append(button);
    };
    for (const [index, allocation] of result.allocations.entries()) {
      const contact = result.contacts.find(item => item.contact_id === allocation.contact_id);
      focusButton(`Transfer ${index + 1}: ${contact?.sender ?? '?'} to ${contact?.receiver ?? '?'} · ${allocation.source_transmit_interval.start_utc}`, allocation.source_transmit_interval.start_utc, artifact.scenario.relay_refs.includes(contact?.receiver) ? 'moon-network' : 'network');
    }
    for (const [index, storage] of result.storage_intervals.entries()) focusButton(`Wait ${index + 1}: ${storage.node_id} · ${storage.interval.start_utc}`, storage.interval.start_utc, artifact.scenario.relay_refs.includes(storage.node_id) ? 'follow' : 'site');
    if (result.final_byte_arrival_utc) focusButton(`Last byte at Earth · ${result.final_byte_arrival_utc}`, result.final_byte_arrival_utc, 'network');
    if (result.allocations.length || result.storage_intervals.length) evidence.append(focus);
    evidence.append(table('Exact selected transfers', ['Chunk / bytes', 'Contact', 'Source transmit UTC', 'Receiver occupied UTC', 'Bytes available UTC'], result.allocations.map(item => [ `${item.chunk_id} / ${item.byte_length}`, item.contact_id, `${item.source_transmit_interval.start_utc} to ${item.source_transmit_interval.end_utc}`, `${item.receiver_occupancy_interval.start_utc} to ${item.receiver_occupancy_interval.end_utc}`, item.byte_available_utc ])));
    evidence.append(table('Exact storage reservations', ['Node / chunk', 'Bytes', 'Wait interval UTC'], result.storage_intervals.map(item => [`${item.node_id} / ${item.chunk_id}`, item.byte_length, `${item.interval.start_utc} to ${item.interval.end_utc}`])));
    evidence.append(table('Usable contacts, not selected transfers', ['Sender → receiver', 'Source transmit window UTC', 'Net payload bps', 'One-way delay s', 'Service / quality'], result.contacts.map(item => [`${item.sender} → ${item.receiver}`, `${item.source_transmit_window.start_utc} to ${item.source_transmit_window.end_utc}`, item.payload_rate_bps, item.one_way_delay.seconds, `${item.service_provenance}; ${item.quality_flags.join('; ')}`])));
    evidence.append(table('Schedule battery history', ['Node', 'Epoch UTC', 'Stored energy Wh'], result.energy_history.map(item => [item.node_id, item.epoch_utc, item.stored_energy_wh])));
    evidence.append(table('Schedule buffer history', ['Node', 'Epoch UTC', 'Stored payload bytes'], result.buffer_history.map(item => [item.node_id, item.epoch_utc, item.stored_bytes])));
    const caveats = document.createElement('details');
    caveats.innerHTML = `<summary>Assumptions, warnings and replay</summary><h3>Assumptions</h3><ul>${result.assumptions.map(value => `<li>${esc(value)}</li>`).join('')}</ul><h3>Warnings</h3><ul>${result.warnings.map(value => `<li>${esc(value)}</li>`).join('')}</ul><pre>${esc(JSON.stringify(artifact.replay, null, 2))}</pre>`;
    evidence.append(caveats);
    const science = document.createElement('details'); science.innerHTML = '<summary>Terrain, illumination, power and contact diagnostics</summary><div id="delivery-science"></div>'; evidence.append(science);
    timeline?.destroy(); timeline = renderTimeline($('delivery-timeline'), { scenario: artifact.scenario, result, sampleEpochs: artifact.display.sample_epochs_utc, onTimeChange: renderAtTime });
    for (const id of ['delivery-export-result', 'delivery-export-package']) $(id).disabled = false;
    epoch = result.allocations[0]?.source_transmit_interval.start_utc ?? artifact.scenario.data_ready_utc;
    timeline.setTime(epoch); renderAtTime(epoch);
    if (active) onMap(artifact, epoch);
  }
  async function plan() {
    if (!scenario || running) return;
    const current = revision; running = true; $('stop-delivery').hidden = false; refreshBudget();
    message('Calculating this delivery in Python. The result and selected transfer will appear when complete.');
    const started = performance.now();
    $('delivery-elapsed').hidden = false; $('delivery-elapsed').textContent = 'Waiting: 0 s';
    waitingTimer = setInterval(() => { if (running && current === revision) $('delivery-elapsed').textContent = `Waiting: ${Math.floor((performance.now() - started) / 1000)} s`; }, 1000);
    try {
      const response = await client.analyze(scenario, options, { onWaiting: () => {
        if (current === revision && running) message('Server is finishing another calculation. Waiting to retry automatically for up to 240 seconds. Stop waiting or edit inputs to cancel this browser wait.');
      } });
      if (current !== revision) return;
      artifact = response; stale = false; renderProfiles(); renderArtifact();
      message(`Calculated delivery in Python · ${describeStatus(response.result).label} · ${response.scenario_sha256.slice(0, 12)}. Rates and service retain their declared assumptions.`);
    } catch (error) { if (error.name !== 'AbortError' && current === revision) message(`Delivery unavailable: ${error.message} No captured or fabricated result replaced it.`); }
    finally { if (current === revision) { stopTimer(); running = false; $('stop-delivery').hidden = true; refreshBudget(); } }
  }
  async function load() {
    message('Checking Python delivery readiness, numerical terrain coverage and explicit profiles.');
    try {
      capabilities = await client.capabilities();
      scenario = structuredClone(capabilities.scenario_template);
      if (!scenario) throw new Error('The service did not supply a complete declared scenario template.');
      options.time_limit_s = Math.min(options.time_limit_s, capabilities.limits.max_solver_time_s);
      renderForm();
      $('delivery-supported-site').disabled = false;
      renderProfiles();
      const methods = document.createElement('details'); methods.className = 'delivery-methods';
      methods.innerHTML = `<summary>Python library methods and availability</summary>${(capabilities.library_capabilities ?? []).map(item => `<section><h3><a href="${esc(item.docs_path)}">${esc(item.label)}</a></h3><p>${esc(item.python_module)} · ${esc(item.http_operation ?? 'Python only')}</p><p>${esc(item.limitation)}</p></section>`).join('')}`;
      $('delivery-profiles').after(methods);
      message(capabilities.ready ? 'Python delivery service ready. Edit the declared task and choose Plan delivery.' : 'Delivery compute or source data are unavailable. Geometry remains available; no delivery result will be fabricated.');
    } catch (error) { message(`Delivery service unavailable: ${error.message}`); $('delivery-form').innerHTML = '<p>Source and compute readiness could not be established.</p><button id="delivery-retry" type="button">Retry delivery readiness</button>'; $('delivery-retry').addEventListener('click', load); }
  }
  $('plan-delivery').addEventListener('click', plan);
  $('delivery-supported-site').addEventListener('click', () => {
    if (!scenario || !capabilities) return;
    for (const key of ['latitude_deg', 'longitude_deg_east', 'elevation_m', 'antenna_height_m', 'panel_height_m']) scenario.lander[key] = capabilities.scenario_template.lander[key];
    invalidate(); renderForm();
    if (!$('delivery-blocker').textContent) message('Supported south-pole lander inputs restored. Payload, task epochs, hardware, network and planning options are unchanged. Choose Plan delivery to calculate.');
    if (active) onFocus('polar');
  });
  $('stop-delivery').title = 'Stops waiting in this browser. The Python calculation may continue on the server.';
  $('stop-delivery').addEventListener('click', () => { stopTimer(); revision += 1; running = false; message(client.cancel()); $('stop-delivery').hidden = true; refreshBudget(); });
  $('delivery-export-scenario').addEventListener('click', () => download(`${JSON.stringify(scenario, null, 2)}\n`, 'soma-delivery-scenario.json', 'application/json'));
  $('delivery-export-result').addEventListener('click', () => { if (!stale && artifact) download(`${JSON.stringify(artifact.result, null, 2)}\n`, `soma-delivery-${artifact.scenario_sha256.slice(0, 12)}.json`, 'application/json'); });
  $('delivery-export-package').addEventListener('click', async () => {
    if (!artifact || stale) return;
    const current = artifact;
    try { const bytes = await deliveryPackageBytes(current); if (current === artifact && !stale) download(bytes, `soma-delivery-${current.scenario_sha256.slice(0, 12)}.zip`, 'application/zip'); }
    catch (error) { message(`Run package unavailable: ${error.message}`); }
  });
  return {
    activate() { active = true; if (!capabilities) load(); else if (artifact) { onMap(artifact, epoch); } },
    deactivate() { active = false; stopTimer(); if (running) { revision += 1; running = false; message(client.cancel()); $('stop-delivery').hidden = true; refreshBudget(); } },
    refreshMap() { if (active && artifact) onMap(artifact, epoch); },
    inspectNode(id) {
      const source = artifact?.scenario ?? scenario;
      const node = source && (id === source.lander.id ? source.lander : Object.values(source.profiles).flat().find(item => item.id === id));
      let panel = $('delivery-node');
      if (!panel) { panel = document.createElement('details'); panel.id = 'delivery-node'; inspector.append(panel); }
      panel.open = true; panel.innerHTML = `<summary>Selected network object${stale ? ' · previous scenario' : ''}</summary>${node ? `<pre>${esc(JSON.stringify(node, null, 2))}</pre>` : '<p>This marker is catalog context, outside this delivery network. Use Geometry, then explicitly copy its declared site inputs to change the lander.</p>'}`;
    },
  };
}
