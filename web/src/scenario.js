export function patchScenario(scenario, path, value) {
  const next = structuredClone(scenario);
  const keys = path.split('.');
  let cursor = next;
  for (const key of keys.slice(0, -1)) {
    if (!Object.hasOwn(cursor, key)) throw new Error(`Unknown scenario field: ${path}`);
    cursor = cursor[key];
  }
  if (!Object.hasOwn(cursor, keys.at(-1))) throw new Error(`Unknown scenario field: ${path}`);
  cursor[keys.at(-1)] = structuredClone(value);
  return next;
}

const el = (tag, text, className) => {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
};
let formNumber = 0;

export function renderScenarioForm(container, { scenario, onChange = () => {} }) {
  let current = structuredClone(scenario);
  const prefix = `scenario-${++formNumber}`;
  function draw() {
    container.replaceChildren();
    const form = el('form', undefined, 'scenario-form');
    form.addEventListener('submit', event => event.preventDefault());
    container.append(form);
    const note = el('p', current.analysis_mode === 'synthetic_fixture'
      ? 'Synthetic fixture. Coordinates, dates, hardware and contact windows are invented test inputs.'
      : 'Terrain and ephemeris analysis requires engine-confirmed coverage.', 'notice');
    form.append(note);
    function section(title) {
      const group = el('fieldset', undefined, 'form-section');
      group.append(el('legend', title));
      const grid = el('div', undefined, 'form-grid');
      group.append(grid); form.append(group); return grid;
    }
    function field(parent, label, path, { type = 'number', min, max, options } = {}) {
      const wrapper = el('div', undefined, 'field');
      const id = `${prefix}-${path.replaceAll('.', '-')}`;
      const caption = el('label', label); caption.htmlFor = id;
      const input = el(options ? 'select' : 'input'); input.id = id; input.name = path;
      if (options) for (const [value, text] of options) {
        const option = el('option', text); option.value = value; input.append(option);
      }
      else { input.type = type; if (type === 'number') input.step = 'any'; }
      input.required = true;
      if (min !== undefined) input.min = min;
      if (max !== undefined) input.max = max;
      if (type === 'text' && path.includes('utc')) {
        input.pattern = '\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d{1,6})?(Z|(?:\\+|-)\\d{2}:\\d{2})';
        input.title = 'Use an ISO timestamp with seconds and timezone, for example 2026-11-14T08:50:00Z';
      }
      input.value = path.split('.').reduce((value, key) => value[key], current);
      input.addEventListener('change', () => {
        if (!input.reportValidity()) return;
        current = patchScenario(current, path, type === 'number' && !options ? input.valueAsNumber : input.value);
        onChange(structuredClone(current));
      });
      wrapper.append(caption, input); parent.append(wrapper);
      return input;
    }
    const site = section('Lunar site');
    field(site, 'Planetocentric latitude (°)', 'lander.latitude_deg', { min: -90, max: 90 });
    const longitude = field(site, 'East longitude (°, −180 to <180)', 'lander.longitude_deg_east', { min: -180 });
    longitude.addEventListener('input', () => longitude.setCustomValidity(longitude.valueAsNumber >= 180 ? 'Longitude must be less than 180 degrees.' : ''));
    field(site, 'Antenna height (m)', 'lander.antenna_height_m', { min: 0 });
    field(site, 'Panel height (m)', 'lander.panel_height_m', { min: 0 });
    site.append(el('p', `${current.lander.frame} · reference radius ${current.lander.reference_radius_m} m · elevation ${current.lander.elevation_m} m (${current.lander.elevation_datum})`, 'muted field-wide'));
    const task = section('Data and time');
    task.append(el('p', 'Deadline rule: fixed absolute deadline. Changing the site or data-ready time leaves the deadline and analysis horizon unchanged. Edit those fields explicitly. Saved-result comparison flags changes to task controls.', 'muted field-wide'));
    field(task, 'Data volume', 'data_volume.value', { min: 1 }).step = '1';
    field(task, 'Volume unit (changing this changes the task)', 'data_volume.unit', { options: [['MiB', 'MiB'], ['byte', 'bytes']] });
    field(task, 'Data ready (UTC / qualified offset)', 'data_ready_utc', { type: 'text' });
    field(task, 'Last-byte deadline (UTC / qualified offset)', 'deadline_utc', { type: 'text' });
    field(task, 'Analysis begins (UTC / qualified offset)', 'analysis_horizon.start_utc', { type: 'text' });
    field(task, 'Analysis ends (UTC / qualified offset)', 'analysis_horizon.end_utc', { type: 'text' });
    const network = section('Hardware and routes');
    const hardwareSelect = field(network, 'Hardware profile', 'hardware_profile_ref', { options: current.profiles.hardware.map(profile => [profile.id, `${profile.id} (${profile.input_class})`]) });
    for (const [family, label] of [['direct_to_earth', 'Direct to Earth'], ['single_lunar_relay', 'One lunar relay']]) {
      const wrapper = el('label', undefined, 'check-field');
      const input = el('input'); input.type = 'checkbox'; input.name = family;
      input.checked = current.route_families.includes(family);
      input.disabled = family === 'single_lunar_relay' && !current.profiles.relays.length;
      input.addEventListener('change', () => {
        const selected = new Set(current.route_families);
        input.checked ? selected.add(family) : selected.delete(family);
        current = patchScenario(current, 'route_families', [...selected]);
        onChange(structuredClone(current));
      }); wrapper.append(input, document.createTextNode(label)); network.append(wrapper);
    }
    const futureRoute = el('label', undefined, 'check-field field-wide');
    const earthOrbit = el('input'); earthOrbit.type = 'checkbox'; earthOrbit.disabled = true;
    futureRoute.append(earthOrbit, document.createTextNode('Earth-orbit relay (Phase 7; unavailable in the baseline)'));
    network.append(futureRoute);
    for (const relay of current.profiles.relays) {
      const label = el('label', undefined, 'check-field field-wide');
      const input = el('input'); input.type = 'checkbox'; input.checked = current.relay_refs.includes(relay.id);
      input.addEventListener('change', () => {
        const refs = new Set(current.relay_refs); input.checked ? refs.add(relay.id) : refs.delete(relay.id);
        current = patchScenario(current, 'relay_refs', [...refs]); onChange(structuredClone(current));
      }); label.append(input, document.createTextNode(`${relay.id} (${relay.input_class}; ${relay.behavior}; storage ${relay.storage_capacity_bytes.toLocaleString('en-US')} bytes)`)); network.append(label);
    }
    if (!current.profiles.relays.length) network.append(el('p', 'No relay profile is embedded in this scenario. Load the relay fixture to inspect that network.', 'muted field-wide'));
    const details = el('details'); details.append(el('summary', 'Declared hardware and assumptions'));
    const hardware = current.profiles.hardware.find(profile => profile.id === current.hardware_profile_ref);
    const pre = el('pre', JSON.stringify({ hardware, rate_method: current.rate_method, pointing_assumption: current.pointing_assumption, service_assumption_label: current.service_assumption_label, station_refs: current.station_refs }, null, 2));
    hardwareSelect.addEventListener('change', () => {
      pre.textContent = JSON.stringify({ hardware: current.profiles.hardware.find(profile => profile.id === current.hardware_profile_ref), rate_method: current.rate_method, pointing_assumption: current.pointing_assumption, service_assumption_label: current.service_assumption_label, station_refs: current.station_refs }, null, 2);
    });
    details.append(pre); form.append(details);
  }
  draw();
  return { getScenario: () => structuredClone(current), setScenario(next) { current = structuredClone(next); draw(); }, destroy() { container.replaceChildren(); } };
}
