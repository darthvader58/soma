import './workbench.css';
import 'cesium/Build/Cesium/Widgets/widgets.css';
import { createResearchClient, validateStudyInputs, storedSampleAt } from './research-client.js';
import { createWorkbenchViewer } from './workbench-viewer.js';
import bootstrapCatalog from '../fixtures/research-catalog.json' with { type: 'json' };

const root = document.querySelector('#app');
root.innerHTML = `
<header class="research-header"><a class="research-brand" href="/">SOMA</a><div class="workspace-title"><h1>Lunar research workbench</h1><p>Moon-fixed geometry & public spacecraft histories</p></div><nav aria-label="Resources"><a href="/docs/getting-started/live-research">Documentation</a><a href="/docs/reference/research-api">Python reference</a><div class="theme-control"><label for="theme-select">Appearance</label><select id="theme-select"><option value="light">Light</option><option value="dark">Dark</option></select></div></nav></header>
<main class="research-workspace">
  <section class="study-toolbar" id="study-inputs" aria-label="Geometry study inputs">
    <div class="analysis-name"><strong>Sun & Earth geometry</strong><span>Define a study. Inspect the calculated geometry.</span></div>
    <div class="study-fields">
    <label>Start UTC<input id="study-start" type="datetime-local" step="1" value="2026-11-16T00:00:00"></label>
    <label>End UTC<input id="study-end" type="datetime-local" step="1" value="2026-11-16T06:00:00"></label>
    <label class="step-input">Step (s)<input id="study-step" type="number" min="10" value="120"></label>
    </div><div class="study-run"><button id="run-study" class="research-primary" type="button">Run analysis</button><button id="cancel-study" type="button" hidden>Stop waiting</button></div>
  </section>
  <div class="research-status"><p id="research-status" role="status" aria-live="polite">Connecting to the Python geometry service.</p><span id="request-budget"></span></div>
  <aside class="object-panel" aria-labelledby="objects-heading">
    <div class="research-panel-heading"><h2 id="objects-heading">Study objects</h2><span id="site-count">0 / 8</span></div>
    <p class="panel-description">Choose up to 8 surface locations.</p>
    <label class="site-search">Find a lunar site<input id="site-search" type="search" placeholder="Name or location type"></label>
    <div class="object-section-heading"><h3>Surface sites</h3><button id="add-custom" type="button">+ Custom site</button></div>
    <div id="site-list" class="site-list"></div>
    <section class="spacecraft-section"><h3>Spacecraft</h3><div id="spacecraft-list"><p>Checking public ephemerides.</p></div></section>
    <section class="layer-section"><h3>Display layers</h3><label><input id="layer-labels" type="checkbox" checked> Selected site labels</label><label><input id="layer-paths" type="checkbox" checked> Stored spacecraft path</label><label><input id="layer-directions" type="checkbox" checked> Sun / Earth schematics</label></section>
    <p class="object-footnote">Catalog markers are sourced locations, not certified landing sites.</p>
  </aside>
  <section class="scene-panel" aria-label="Lunar mission scene">
    <div class="scene-toolbar"><div class="scene-camera" aria-label="Camera"><button type="button" data-camera="global" aria-pressed="true">Global</button><button type="button" data-camera="polar" aria-pressed="false">South pole</button><button type="button" data-camera="site" aria-pressed="false">Selected site</button><button id="follow-spacecraft" type="button" data-camera="follow" aria-pressed="false" disabled>Follow spacecraft</button></div><span id="scene-frame">MOON_ME_DE421</span></div>
    <div id="research-moon" class="research-moon"></div>
    <p id="research-map-status" class="scene-caption" role="status">Preparing lunar scene.</p>
  </section>
  <aside class="inspector-panel" aria-labelledby="inspector-heading"><div class="research-panel-heading"><h2 id="inspector-heading">Site inspector</h2><span id="inspector-kind"></span></div><div id="site-inspector"><p>Select a site from the object list.</p></div></aside>
  <section class="time-dock" aria-label="Shared UTC timeline and geometry results">
    <div class="time-controls"><button id="play-study" type="button" disabled>Play</button><button id="previous-sample" type="button" aria-label="Previous stored sample" disabled>‹</button><button id="next-sample" type="button" aria-label="Next stored sample" disabled>›</button><output id="selected-utc">No calculated time samples</output><label>Playback speed<select id="playback-speed"><option value="60">60×</option><option value="600" selected>600×</option><option value="3600">3600×</option></select></label><div class="research-downloads"><button id="save-alternative" type="button" disabled>Save alternative</button><button id="export-study" type="button">Study JSON</button><button id="export-result" type="button" disabled>Result JSON</button><a id="export-package" hidden>Run package</a></div></div>
    <label class="cursor-label" for="study-cursor">Study time UTC</label><input id="study-cursor" type="range" min="0" max="1" value="0" step="1" disabled><div class="time-extent"><span id="time-start">Start UTC</span><span id="time-end">End UTC</span></div>
    <div class="dock-data"><div class="geometry-chart"><div class="chart-heading"><h2>Local center elevation</h2><span>Sun: solid · Earth: dashed</span></div><div id="geometry-chart"><p>Run a study to inspect changing geometry.</p></div></div><div class="geometry-table"><h2>Site comparison</h2><div id="site-comparison"><p>Same interval and sampling for every selected site.</p></div></div></div>
    <p id="sample-note" class="sample-note">Geometry does not evaluate terrain visibility, sunlight fraction, power or usable communications.</p><div id="saved-alternatives"></div>
    <details id="study-methods" class="source-details" style="overflow-wrap:anywhere;min-width:0" hidden><summary>Methods & sources</summary><div id="study-methods-content" role="region" aria-label="Study methods and sources" tabindex="0" style="max-height:min(22dvh,180px);overflow:auto;overscroll-behavior:contain;min-width:0;padding:0 4px 6px 0"></div></details>
  </section>
</main>`;

const $ = id => document.getElementById(id);
let savedTheme;
try { savedTheme = localStorage.getItem('soma-research-theme'); } catch { /* Appearance still works when storage is unavailable. */ }
document.documentElement.dataset.theme = savedTheme === 'dark' ? 'dark' : 'light';
$('theme-select').value = document.documentElement.dataset.theme;
$('theme-select').addEventListener('change', event => {
  document.documentElement.dataset.theme = event.target.value;
  try { localStorage.setItem('soma-research-theme', event.target.value); } catch { /* The current page retains the selected appearance. */ }
});
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const client = createResearchClient({ baseUrl: `${(import.meta.env.VITE_SOMA_API_URL || '/api').replace(/\/$/, '')}/research` });
let catalog = [], selected = new Set(), inspected, inspectedCraft, capabilities, viewer, result, completed, stale = false, running = false, revision = 0;
let cursor = 0, playing = false, lastFrame, customIndex = 0, alternatives = [], spacecraft = new Set();
const status = message => { $('research-status').textContent = message; };
const utcInput = epoch => epoch.replace(/Z$/, '').slice(0, 19);
const inputUtc = value => value ? new Date(`${value}Z`).toISOString().replace('.000Z', 'Z') : '';
function requestStudy() {
  return { study_version: '1.0.0', analysis_type: 'geometry', frame: 'MOON_ME_DE421', reference_radius_m: 1737400,
    surface_model: 'reference_sphere', sites: [...selected].map(id => {
      const item = catalog.find(site => site.id === id);
      const fields = Object.fromEntries(['id', 'name', 'latitude_deg', 'longitude_deg_east', 'elevation_m', 'antenna_height_m', 'panel_height_m'].map(key => [key, item[key]]));
      if (fields.longitude_deg_east === 180) fields.longitude_deg_east = -180;
      return fields;
    }), time: { start_utc: inputUtc($('study-start').value), end_utc: inputUtc($('study-end').value), step_s: Number($('study-step').value) }, spacecraft_refs: [...spacecraft] };
}
function budget() {
  try {
    const check = validateStudyInputs(requestStudy());
    $('request-budget').textContent = `${selected.size} sites · ${check.epochs.toLocaleString()} epochs · ${check.pairs.toLocaleString()} pairs`;
    $('request-budget').classList.toggle('budget-error', check.errors.length > 0);
    return check;
  } catch { return { errors: ['Enter valid UTC dates.'] }; }
}
function markChanged() {
  revision += 1; stale = Boolean(result); pause();
  if (running) { client.cancel().then(message => status(`Inputs changed. ${message}`)).catch(error => status(error.message)); setRunning(false); }
  else status(result ? 'Inputs changed. Displayed samples belong to the previous study; run analysis to update.' : 'Ready to calculate these inputs in Python.');
  $('export-result').disabled = stale || !result; $('save-alternative').disabled = stale || !result; $('export-package').hidden = true;
  budget(); renderInspectorReadout(); renderMethods();
}
function renderSites() {
  const query = $('site-search').value.toLowerCase();
  $('site-list').replaceChildren();
  for (const site of catalog.filter(item => `${item.name} ${item.kind ?? ''}`.toLowerCase().includes(query))) {
    const row = document.createElement('div'); row.className = `site-row${site.id === inspected ? ' inspecting' : ''}`;
    const check = document.createElement('input'); check.type = 'checkbox'; check.checked = selected.has(site.id); check.setAttribute('aria-label', `Include ${site.name}`);
    check.addEventListener('change', () => {
      if (check.checked && selected.size >= 8) { check.checked = false; status('A study supports at most 8 sites. Remove a site before adding another.'); return; }
      check.checked ? selected.add(site.id) : selected.delete(site.id); inspect(site.id); markChanged(); renderSites();
    });
    const button = document.createElement('button'); button.type = 'button'; button.setAttribute('aria-pressed', String(site.id === inspected));
    button.innerHTML = `<span>${esc(site.name)}</span><small>${esc(site.kind?.replaceAll('_', ' ') ?? 'Custom location')}</small>`;
    const inclusion = document.createElement('label'); inclusion.className = 'site-inclusion'; inclusion.append(check);
    button.addEventListener('click', () => inspect(site.id)); row.append(inclusion, button); $('site-list').append(row);
  }
  $('site-count').textContent = `${selected.size} / 8`;
  if (!$('site-list').childElementCount) $('site-list').textContent = 'No catalog sites match. Clear the search or add a custom site.';
  viewer?.setCatalog(catalog); viewer?.setSelection([...selected], inspected);
}
function inspect(id) { inspectedCraft = undefined; inspected = id; $('inspector-heading').textContent = 'Site inspector'; renderSites(); renderInspector(); renderChart(); viewer?.setSelection([...selected], id); }
function inspectSpacecraft(id) {
  inspectedCraft = id;
  const craft = result?.spacecraft.find(item => item.id === id);
  const profile = capabilities?.spacecraft?.find(item => item.id === id);
  $('inspector-heading').textContent = 'Spacecraft inspector';
  $('inspector-kind').textContent = 'Archived ephemeris';
  $('site-inspector').innerHTML = `<h3>${esc(craft?.name ?? profile?.name ?? id)}</h3><p class="inspector-note">Reconstructed public mission trajectory. No relay service, attitude or instrument footprint is inferred.</p><section class="readout-section"><h3>Native Moon-fixed state <span id="stale-label"></span></h3><div id="site-readout"></div></section><details class="source-details" open><summary>Source & quality</summary><div id="spacecraft-source"></div><p>MOON_ME_DE421 · Moon origin · position in meters and velocity in meters per second.</p><p>Playback interpolates position for presentation only. The numerical state below always comes from a stored epoch. No extrapolation beyond ephemeris coverage.</p></details>`;
  if (profile?.source_url) { const link = document.createElement('a'); link.href = profile.source_url; link.target = '_blank'; link.rel = 'noreferrer'; link.textContent = 'NASA PDS / NAIF source'; $('spacecraft-source').append(link); }
  renderInspectorReadout();
}
function renderInspector() {
  const site = catalog.find(item => item.id === inspected);
  if (!site) return;
  $('inspector-kind').textContent = selected.has(site.id) ? 'In study' : 'Context';
  $('site-inspector').innerHTML = `<h3>${esc(site.name)}</h3><p class="inspector-coordinate">${Number(site.latitude_deg).toFixed(5)}° N · ${Number(site.longitude_deg_east).toFixed(5)}° E</p>
    <div class="site-fields"><label>Latitude (° N)<input data-site-field="latitude_deg" type="number" min="-90" max="90" step="any" value="${site.latitude_deg}"></label><label>Longitude (° E)<input data-site-field="longitude_deg_east" type="number" min="-180" max="180" step="any" value="${site.longitude_deg_east}"></label><label>Elevation above reference sphere (m)<input data-site-field="elevation_m" type="number" step="any" value="${site.elevation_m}"></label><label>Antenna height (m)<input data-site-field="antenna_height_m" type="number" min="0" step="any" value="${site.antenna_height_m}"></label><label>Panel height (m)<input data-site-field="panel_height_m" type="number" min="0" step="any" value="${site.panel_height_m}"></label></div>
    <p class="inspector-note">Changing published coordinates creates a user-defined study location. Elevation is an input, not a tile measurement.</p>
    <section class="readout-section"><h3>Stored geometry <span id="stale-label"></span></h3><div id="site-readout"></div></section>
    <details class="source-details" open><summary>Source & quality</summary><div id="site-sources"></div><p>${esc(site.coordinate_notes ?? site.realization_notes ?? site.coordinate_precision_notes ?? '')}</p><p>MOON_ME_DE421 · 1,737,400 m reference sphere. Global context markers are not certified terrain alignment.</p><p id="site-quality"></p></details>`;
  const sources = site.source_urls ?? (site.source_url ? [site.source_url] : site.sources?.map(item => item.url) ?? []);
  for (const [index, source] of sources.entries()) {
    const url = typeof source === 'string' ? source : source.url;
    if (!/^https:\/\//.test(url ?? '')) continue;
    const link = document.createElement('a'); link.href = url; link.target = '_blank'; link.rel = 'noreferrer'; link.textContent = `Coordinate source ${index + 1}`; $('site-sources').append(link);
  }
  if (!sources.length) $('site-sources').textContent = site.input_class === 'user_defined' ? 'User-defined coordinates.' : 'Catalog source metadata unavailable.';
  for (const field of $('site-inspector').querySelectorAll('[data-site-field]')) field.addEventListener('input', () => {
    site[field.dataset.siteField] = field.value === '' ? NaN : Number(field.value);
    site.input_class = 'user_defined';
    delete site.position_m;
    $('site-inspector').querySelector('.inspector-coordinate').textContent = `${Number(site.latitude_deg).toFixed(5)}° N · ${Number(site.longitude_deg_east).toFixed(5)}° E`;
    markChanged(); viewer?.setCatalog(catalog);
  });
  renderInspectorReadout();
}
const deg = value => Number.isFinite(value) ? `${value.toFixed(3)}°` : 'unknown';
function renderInspectorReadout() {
  if (!$('site-readout')) return;
  if (inspectedCraft) {
    const craft = result?.spacecraft.find(item => item.id === inspectedCraft);
    const sample = storedSampleAt(craft?.samples, selectedEpoch());
    $('stale-label').textContent = stale ? '(previous inputs)' : '';
    $('site-readout').innerHTML = sample ? `<p class="sample-epoch">${esc(sample.epoch_utc)}</p><dl class="sample-values"><dt>Position X / Y / Z (m)</dt><dd>${sample.position_m.map(value => value.toFixed(1)).join(' / ')}</dd><dt>Velocity X / Y / Z (m/s)</dt><dd>${sample.velocity_m_s.map(value => value.toFixed(3)).join(' / ')}</dd><dt>Input class</dt><dd>${esc(craft.input_class.replaceAll('_', ' '))}</dd></dl>` : '<p>No stored state for this spacecraft at the selected time. Include its ephemeris and run analysis inside its coverage.</p>';
    return;
  }
  const site = result?.sites.find(item => item.id === inspected), epoch = selectedEpoch(), sample = storedSampleAt(site?.samples, epoch);
  $('stale-label').textContent = stale ? '(previous inputs)' : '';
  if (!sample) { $('site-readout').innerHTML = '<p>No calculated sample for this site. Include it and run analysis.</p>'; $('site-quality').textContent = 'Reference-sphere geometry only. Terrain, solar fraction, power and usable contacts are not evaluated.'; return; }
  $('site-readout').innerHTML = `<p class="sample-epoch">${esc(sample.epoch_utc)}</p><dl class="sample-values"><dt>Sun elevation / azimuth</dt><dd>${deg(sample.sun.elevation_deg)} / ${deg(sample.sun.azimuth_deg)}</dd><dt>Earth elevation / azimuth</dt><dd>${deg(sample.earth.elevation_deg)} / ${deg(sample.earth.azimuth_deg)}</dd><dt>Earth range</dt><dd>${Number.isFinite(sample.earth.range_m) ? `${(sample.earth.range_m / 1000).toFixed(1)} km` : 'unknown'}</dd></dl>`;
  $('site-quality').textContent = `Reference-sphere geometry. Sun uses panel height (${site.panel_height_m} m); Earth center uses antenna height (${site.antenna_height_m} m). Terrain visibility, solar disk fraction, power and usable contacts are not evaluated. Discrete epochs; no event detection. Pole azimuth reference meridian: ${site.quality?.pole_reference_meridian_deg_east ?? 'unknown'}° E.`;
}
function selectedEpoch() { return result ? new Date(cursor).toISOString().replace('.000Z', 'Z') : ''; }
function setCursor(milliseconds) {
  if (!result) return;
  const first = Date.parse(result.epochs_utc[0]), last = Date.parse(result.epochs_utc.at(-1));
  cursor = Math.min(last, Math.max(first, milliseconds)); $('study-cursor').value = String(cursor);
  const epoch = selectedEpoch(); $('time-start').textContent = result.epochs_utc[0]; $('time-end').textContent = result.epochs_utc.at(-1); $('selected-utc').textContent = epoch; viewer?.setTime(epoch);
  renderInspectorReadout(); renderChart();
  const sample = storedSampleAt(result.sites.find(item => item.id === inspected)?.samples, epoch);
  $('sample-note').textContent = `${stale ? 'Previous study. ' : ''}Scientific readout: stored sample ${sample?.epoch_utc ?? 'unavailable'}. Spacecraft motion between samples is linear display interpolation, with no extrapolation. Geometry does not establish terrain-clear access.`;
}
function pause() { playing = false; $('play-study').textContent = 'Play'; lastFrame = undefined; }
function animate(timestamp) {
  if (!playing || !result) return;
  if (lastFrame !== undefined) setCursor(cursor + Math.min(timestamp - lastFrame, 250) * Number($('playback-speed').value));
  lastFrame = timestamp;
  if (cursor >= Date.parse(result.epochs_utc.at(-1))) { pause(); return; }
  requestAnimationFrame(animate);
}
function renderChart() {
  const site = result?.sites.find(item => item.id === inspected);
  if (!site?.samples?.length) { $('geometry-chart').innerHTML = '<p>Include this site in a calculated study to plot its Sun and Earth center elevations.</p>'; return; }
  const width = Math.max(280, $('geometry-chart').clientWidth || 680), height = 138, left = 49, right = 12, top = 12, bottom = 22;
  const values = site.samples.flatMap(sample => [sample.sun.elevation_deg, sample.earth.elevation_deg]).filter(Number.isFinite);
  const minimum = Math.min(...values), maximum = Math.max(...values);
  const padding = Math.max((maximum - minimum) * 0.12, 0.25);
  const lower = Math.max(-90, Math.floor((minimum - padding) * 10) / 10);
  const upper = Math.min(90, Math.ceil((maximum + padding) * 10) / 10);
  const start = Date.parse(result.epochs_utc[0]), end = Date.parse(result.epochs_utc.at(-1));
  const x = epoch => left + (Date.parse(epoch) - start) / Math.max(1, end - start) * (width - left - right);
  const y = value => top + (upper - value) / (upper - lower) * (height - top - bottom);
  const path = key => site.samples.filter(sample => Number.isFinite(sample[key]?.elevation_deg)).map((sample, index) => `${index ? 'L' : 'M'}${x(sample.epoch_utc).toFixed(2)} ${y(sample[key].elevation_deg).toFixed(2)}`).join(' ');
  const ticks = [upper, (upper + lower) / 2, lower].map(value => `<text x="0" y="${y(value)+4}">${value.toFixed(1)}°</text>`).join('');
  const horizontal = lower <= 0 && upper >= 0 ? `<line x1="${left}" x2="${width-right}" y1="${y(0)}" y2="${y(0)}" class="chart-zero"/>` : '';
  $('geometry-chart').innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Stored Sun and Earth elevation samples for ${esc(site.name)}; displayed axis ${lower.toFixed(1)} to ${upper.toFixed(1)} degrees"><title>${esc(site.name)} · stored center elevation samples</title>${horizontal}${ticks}<path d="${path('sun')}" class="chart-sun"/><path d="${path('earth')}" class="chart-earth"/><line x1="${x(selectedEpoch())}" x2="${x(selectedEpoch())}" y1="${top}" y2="${height-bottom}" class="chart-cursor"/></svg>`;
}
function renderComparison() {
  if (!result) return;
  $('site-comparison').innerHTML = `<table><thead><tr><th>Site</th><th>Sun min / max</th><th>Earth min / max</th></tr></thead><tbody>${result.sites.map(site => `<tr><th>${esc(site.name)}</th><td>${deg(site.summary.sun_elevation_min_deg)} / ${deg(site.summary.sun_elevation_max_deg)}</td><td>${deg(site.summary.earth_elevation_min_deg)} / ${deg(site.summary.earth_elevation_max_deg)}</td></tr>`).join('')}</tbody></table>`;
}
let previousChartWidth, chartResizeFrame;
const chartResizeObserver = new ResizeObserver(entries => {
  const width = entries[0].contentRect.width;
  if (width !== previousChartWidth) {
    previousChartWidth = width;
    if (chartResizeFrame) cancelAnimationFrame(chartResizeFrame);
    chartResizeFrame = requestAnimationFrame(() => { chartResizeFrame = undefined; renderChart(); });
  }
});
chartResizeObserver.observe($('geometry-chart'));
window.addEventListener('pagehide', () => { chartResizeObserver.disconnect(); if (chartResizeFrame) cancelAnimationFrame(chartResizeFrame); }, { once: true });
function renderMethods() {
  $('study-methods').hidden = !result;
  if (!result) return;
  const content = $('study-methods-content'); content.replaceChildren();
  const appendText = (parent, tag, value) => {
    const element = document.createElement(tag); element.textContent = value; parent.append(element); return element;
  };
  if (stale) appendText(content, 'p', 'These methods and sources describe the previous study shown above.');
  const provenance = result.provenance;
  const fields = document.createElement('dl'); content.append(fields);
  for (const [label, value] of [
    ['Study SHA256', result.study_sha256], ['Provider', provenance.provider], ['Frame', result.frame],
    ['Origin', result.origin], ['Aberration convention', provenance.aberration], ['Geometry model', provenance.geometry_model],
    ['Kernel manifest SHA256', provenance.kernel_manifest_sha256], ['Effective kernel manifest SHA256', provenance.effective_kernel_manifest_sha256],
  ]) { appendText(fields, 'dt', label); appendText(fields, 'dd', value); }
  const sources = [...provenance.kernels, ...provenance.spacecraft_sources.map(source => source.manifest ?? source)];
  appendText(content, 'h3', 'Kernel sources');
  const kernels = document.createElement('ul'); content.append(kernels);
  for (const source of sources) {
    const item = document.createElement('li'); kernels.append(item);
    appendText(item, 'p', source.name ?? source.path ?? source.id ?? 'Name not supplied');
    appendText(item, 'p', `SHA256: ${source.sha256 ?? 'not supplied'}`);
    let officialUrl;
    try {
      const url = new URL(source.source_url);
      if (url.protocol === 'https:' && !url.username && !url.password && !url.port &&
          (url.hostname === 'nasa.gov' || url.hostname.endsWith('.nasa.gov'))) officialUrl = url.href;
    } catch { /* Missing or malformed source metadata remains plain text. */ }
    if (officialUrl) {
      const link = appendText(item, 'a', source.source_url); link.href = officialUrl; link.target = '_blank'; link.rel = 'noreferrer';
    } else if (source.source_url) appendText(item, 'p', source.source_url);
    if (Array.isArray(source.limitations)) {
      const list = document.createElement('ul'); item.append(list);
      for (const limitation of source.limitations) appendText(list, 'li', limitation);
    }
  }
  for (const [title, values] of [['Limitations', result.limitations], ['Assumptions', provenance.assumptions]]) {
    appendText(content, 'h3', title); const list = document.createElement('ul'); content.append(list);
    for (const value of values) appendText(list, 'li', value);
  }
}
function setRunning(value) { running = value; $('run-study').disabled = value; $('cancel-study').hidden = !value; $('cancel-study').textContent = capabilities?.async_available === true ? 'Cancel study' : 'Stop waiting'; }
async function runStudy() {
  const check = budget();
  if (check.errors.length) { status(check.errors.join(' ')); return; }
  const current = revision; setRunning(true); status('Submitting these sites and UTC epochs to Python.');
  try {
    const calculated = await client.analyze(requestStudy(), capabilities, progress => { if (current === revision) status(progress.stage ?? progress.status); });
    if (current !== revision) return;
    completed = calculated; result = calculated.result; stale = false; pause();
    $('study-cursor').disabled = false; $('study-cursor').min = String(Date.parse(result.epochs_utc[0])); $('study-cursor').max = String(Date.parse(result.epochs_utc.at(-1)));
    for (const id of ['play-study', 'previous-sample', 'next-sample', 'export-result', 'save-alternative']) $(id).disabled = false;
    $('follow-spacecraft').disabled = !result.spacecraft?.length;
    if (calculated.jobId) { $('export-package').href = client.exportUrl(calculated.jobId); $('export-package').hidden = false; }
    viewer?.setResult(result); setCursor(Date.parse(result.epochs_utc[0])); renderComparison(); renderMethods();
    status(`Calculated in Python · ${result.sites.length} sites · ${result.epochs_utc.length} stored epochs · ${calculated.hash.slice(0, 12)}. Reference-sphere geometry; terrain visibility is not evaluated.`);
    if (inspectedCraft) inspectSpacecraft(inspectedCraft); else renderInspector();
  } catch (error) { if (error.name !== 'AbortError' && current === revision) status(`Analysis unavailable: ${error.message} No replacement result was generated.`); }
  finally { if (current === revision) setRunning(false); }
}
function download(value, filename) {
  const url = URL.createObjectURL(new Blob([`${JSON.stringify(value, null, 2)}\n`], { type: 'application/json' }));
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$('run-study').addEventListener('click', runStudy);
$('cancel-study').addEventListener('click', async () => { revision += 1; setRunning(false); try { status(await client.cancel()); } catch (error) { status(`Stopped waiting; server cancellation could not be confirmed. ${error.message}`); } });
for (const id of ['study-start', 'study-end', 'study-step']) $(id).addEventListener('input', markChanged);
$('site-search').addEventListener('input', renderSites);
$('add-custom').addEventListener('click', () => {
  if (selected.size >= 8) { status('Remove a site before adding another. Maximum 8 sites.'); return; }
  const id = `custom-${++customIndex}`;
  catalog.push({ id, name: `Custom site ${customIndex}`, kind: 'user location', latitude_deg: 0, longitude_deg_east: 0, elevation_m: 0, antenna_height_m: 2, panel_height_m: 1, input_class: 'user_defined' });
  selected.add(id); inspect(id); markChanged();
});
$('study-cursor').addEventListener('input', event => { pause(); setCursor(Number(event.target.value)); });
$('play-study').addEventListener('click', () => { if (playing) pause(); else { if (cursor >= Date.parse(result.epochs_utc.at(-1))) setCursor(Date.parse(result.epochs_utc[0])); playing = true; $('play-study').textContent = 'Pause'; requestAnimationFrame(animate); } });
for (const [id, delta] of [['previous-sample', -1], ['next-sample', 1]]) $(id).addEventListener('click', () => {
  pause(); const epochs = result.epochs_utc.map(Date.parse); const index = epochs.findIndex(time => time >= cursor); setCursor(epochs[Math.max(0, Math.min(epochs.length - 1, index + delta))]);
});
for (const button of root.querySelectorAll('[data-camera]')) button.addEventListener('click', () => {
  viewer?.camera(button.dataset.camera);
  for (const control of root.querySelectorAll('[data-camera]')) control.setAttribute('aria-pressed', String(control === button));
});
for (const id of ['layer-labels', 'layer-paths', 'layer-directions']) $(id).addEventListener('change', () => viewer?.setLayers({ labels: $('layer-labels').checked, paths: $('layer-paths').checked, directions: $('layer-directions').checked }));
$('export-study').addEventListener('click', () => { try { download(requestStudy(), 'soma-study.json'); } catch { status('Enter valid study fields before exporting.'); } });
$('export-result').addEventListener('click', () => { if (result && !stale) download(result, `soma-result-${completed.hash.slice(0, 12)}.json`); });
$('save-alternative').addEventListener('click', () => {
  if (!result || stale) return;
  if (alternatives.some(item => item.study_sha256 === result.study_sha256)) { status('This exact study is already saved as an alternative.'); return; }
  alternatives.push(structuredClone(result));
  $('saved-alternatives').innerHTML = `<details open><summary>Saved calculated alternatives (${alternatives.length})</summary><table><thead><tr><th>Study hash</th><th>UTC interval</th><th>Sites / epochs</th><th>Step</th><th>Result</th></tr></thead><tbody>${alternatives.map((item, index) => `<tr><td>${esc(item.study_sha256.slice(0,12))}</td><td>${esc(item.request.time.start_utc)} to ${esc(item.request.time.end_utc)}</td><td>${item.sites.length} / ${item.epochs_utc.length}</td><td>${item.request.time.step_s} s</td><td><button type="button" data-alternative="${index}">Download saved result</button></td></tr>`).join('')}</tbody></table><p>Each row preserves its own site set, heights, interval and sampling. No aggregate site ranking is inferred.</p></details>`;
  for (const button of $('saved-alternatives').querySelectorAll('[data-alternative]')) button.addEventListener('click', () => {
    const saved = alternatives[Number(button.dataset.alternative)];
    download(saved, `soma-alternative-${saved.study_sha256.slice(0,12)}.json`);
  });
});

async function initialize() {
  catalog = structuredClone(bootstrapCatalog.sites);
  selected = new Set([catalog[0], catalog[Math.floor(catalog.length / 2)], catalog.at(-1)].filter(Boolean).map(site => site.id));
  inspected = catalog[0]?.id; renderSites(); renderInspector();
  const mapPromise = createWorkbenchViewer($('research-moon'), { ionToken: import.meta.env.VITE_CESIUM_ION_TOKEN, apiBase: import.meta.env.VITE_SOMA_API_URL || '/api',
    onStatus: message => { $('research-map-status').textContent = message; }, onSelect: inspect,
    onPick: coordinates => {
      if (selected.size >= 8) { status('Remove a site before adding a picked location. Maximum 8 sites.'); return; }
      const id = `custom-${++customIndex}`;
      catalog.push({ id, name: `Picked site ${customIndex}`, kind: 'display pick', ...coordinates, elevation_m: 0, antenna_height_m: 2, panel_height_m: 1, input_class: 'user_defined', coordinate_notes: 'Coordinates selected from rendered Moon. Elevation is explicitly 0 m above the reference sphere; not measured terrain.' });
      selected.add(id); inspect(id); markChanged();
    },
  }).then(value => { viewer = value; viewer.setCatalog(catalog); viewer.setSelection([...selected], inspected); if (result) viewer.setResult(result); });
  const loaded = await Promise.allSettled([client.catalog(), client.capabilities()]);
  if (loaded[0].status === 'fulfilled' && revision === 0) {
    catalog = loaded[0].value.sites.map(site => ({ ...site, elevation_m: 0, antenna_height_m: 2, panel_height_m: 1 }));
    selected = new Set([catalog[0], catalog[Math.floor(catalog.length / 2)], catalog.at(-1)].filter(Boolean).map(site => site.id));
    inspected = catalog[0]?.id; renderSites(); renderInspector();
  } else if (loaded[0].status === 'rejected') { status(`Catalog service unavailable. Showing the sourced catalog v${bootstrapCatalog.catalog_version}; new scientific results still require Python.`); }
  if (loaded[1].status === 'fulfilled') {
    capabilities = loaded[1].value;
    $('spacecraft-list').replaceChildren();
    for (const craft of capabilities.spacecraft ?? []) {
      const label = document.createElement('label'); const input = document.createElement('input'); input.type = 'checkbox'; input.disabled = !craft.available;
      input.setAttribute('aria-label', `Include ${craft.name}`); label.append(input, document.createTextNode(craft.name));
      const note = document.createElement('p'); note.textContent = `${craft.input_class ?? 'Public ephemeris'} · ${craft.coverage?.start_utc ?? 'coverage unavailable'} to ${craft.coverage?.end_utc ?? 'unknown'}. No relay service implied.`;
      const useCoverage = () => {
        const start = new Date(craft.coverage.start_utc);
        const nextMonth = Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + 1, 1);
        const preferred = nextMonth + 6 * 3600000 <= Date.parse(craft.coverage.end_utc) ? nextMonth : start.getTime();
        $('study-start').value = utcInput(new Date(preferred).toISOString());
        $('study-end').value = utcInput(new Date(Math.min(Date.parse(craft.coverage.end_utc), preferred + 6 * 3600000)).toISOString());
        spacecraft.add(craft.id); input.checked = true;
      };
      if (craft.available && craft.coverage?.start_utc && spacecraft.size === 0 && revision === 0) {
        spacecraft.add(craft.id); input.checked = true;
        useCoverage();
      }
      input.addEventListener('change', () => { input.checked ? spacecraft.add(craft.id) : spacecraft.delete(craft.id); markChanged(); });
      $('spacecraft-list').append(label, note);
      const inspectButton = document.createElement('button'); inspectButton.type = 'button'; inspectButton.textContent = 'Inspect stored state'; inspectButton.addEventListener('click', () => inspectSpacecraft(craft.id)); $('spacecraft-list').append(inspectButton);
      if (craft.available && craft.coverage?.start_utc) {
        const coverageButton = document.createElement('button'); coverageButton.type = 'button'; coverageButton.textContent = craft.id.startsWith('lro-') ? 'Use LRO coverage' : 'Use ephemeris interval';
        coverageButton.addEventListener('click', () => { useCoverage(); markChanged(); runStudy(); }); $('spacecraft-list').append(coverageButton);
      }
      if (craft.source_url) { const link = document.createElement('a'); link.href = craft.source_url; link.textContent = 'Ephemeris source'; link.target = '_blank'; link.rel = 'noreferrer'; $('spacecraft-list').append(link); }
    }
    if (!capabilities.spacecraft?.length) $('spacecraft-list').textContent = 'No spacecraft ephemeris configured.';
    const coverage = capabilities.coverage;
    if (coverage) $('study-start').title = $('study-end').title = `Actual kernel coverage: ${coverage.start_utc} to ${coverage.end_utc}`;
    status(capabilities.ready ? `Python geometry service ready. ${capabilities.async_available === true ? 'Persistent study jobs.' : 'Bounded synchronous compute.'}` : 'Python geometry data are unavailable. Run analysis reports the exact service error; no fixture replaces it.');
    budget();
    if (capabilities.ready && selected.size && revision === 0) await runStudy();
  } else { $('spacecraft-list').textContent = 'Spacecraft capabilities unavailable.'; status('Python geometry service unavailable. Add or edit sites and UTC inputs; analysis will report the connection error. No scientific result is fabricated.'); budget(); }
  await mapPromise;
}
initialize();
