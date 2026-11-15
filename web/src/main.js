import './style.css';
import './phase3.css';
import 'cesium/Build/Cesium/Widgets/widgets.css';
import { renderScenarioForm } from './scenario.js';
import { renderResult } from './result.js';
import { renderTimeline } from './timeline.js';
import { createFixtureClient, createPlanClient } from './client.js';
import { validateScenario } from './contracts.js';
import { createMoonViewer, registrationGate } from './viewer.js';
import { displayTimeText } from './display.js';
import { renderScience } from './science.js';
import { renderComparison } from './comparison.js';
import directScenario from '../fixtures/synthetic-direct/scenario.json' with { type: 'json' };
import directContacts from '../fixtures/synthetic-direct/contacts.json' with { type: 'json' };
import directExpected from '../fixtures/synthetic-direct/expected.json' with { type: 'json' };
import directResult from '../fixtures/synthetic-direct/result.json' with { type: 'json' };
import directResultText from '../fixtures/synthetic-direct/result.json?raw';
import relayScenario from '../fixtures/synthetic-relay/scenario.json' with { type: 'json' };
import relayContacts from '../fixtures/synthetic-relay/contacts.json' with { type: 'json' };
import relayExpected from '../fixtures/synthetic-relay/expected.json' with { type: 'json' };
import relayResult from '../fixtures/synthetic-relay/result.json' with { type: 'json' };
import relayResultText from '../fixtures/synthetic-relay/result.json?raw';
import directEnvironment from '../fixtures/synthetic-direct/environment.json' with { type: 'json' };
import directEnvironmentText from '../fixtures/synthetic-direct/environment.json?raw';
import relayEnvironment from '../fixtures/synthetic-relay/environment.json' with { type: 'json' };
import relayEnvironmentText from '../fixtures/synthetic-relay/environment.json?raw';
import realEnvironment from '../fixtures/recorded-lola/environment.json' with { type: 'json' };
import realEnvironmentText from '../fixtures/recorded-lola/environment.json?raw';
import directPackageUrl from '../fixtures/synthetic-direct/run.zip?url';
import relayPackageUrl from '../fixtures/synthetic-relay/run.zip?url';
import directSummary from '../fixtures/synthetic-direct/summary.json' with { type: 'json' };
import relaySummary from '../fixtures/synthetic-relay/summary.json' with { type: 'json' };

const fixtures = [
  { name: 'Direct to Earth', scenario: directScenario, contacts: directContacts, expected: directExpected, result: directResult, resultText: directResultText, environment: directEnvironment, environmentText: directEnvironmentText, packageUrl: directPackageUrl, summary: directSummary },
  { name: 'One lunar relay', scenario: relayScenario, contacts: relayContacts, expected: relayExpected, result: relayResult, resultText: relayResultText, environment: relayEnvironment, environmentText: relayEnvironmentText, packageUrl: relayPackageUrl, summary: relaySummary },
];
const fixtureMode = import.meta.env.VITE_SOMA_MODE === 'fixture';
const apiUrl = fixtureMode ? undefined : import.meta.env.VITE_SOMA_API_URL || '/api';
const client = fixtureMode ? createFixtureClient(fixtures) : createPlanClient({ baseUrl: apiUrl });
const root = document.querySelector('#app');
root.innerHTML = `
  <header class="app-header">
    <div class="identity"><span class="wordmark">SOMA</span><span class="identity-rule" aria-hidden="true"></span><span>Lunar delivery planner</span></div>
    <span class="phase-label">Phase 5 · Visual draft</span>
  </header>
  <main>
    <div class="page-heading"><div><h1>Plan a delivery from the Moon</h1><p>Inspect the site, data and network assumptions behind a delivery request.</p></div><p class="workspace-mode" id="workspace-mode"></p></div>
    <p class="project-notice">Fixture workspace. Delivery schedules are computed by Python under declared synthetic geometry, service and rate assumptions. Measured-terrain diagnostics remain separate; missing coverage stays unknown.</p>
    <div class="workspace">
      <aside class="scenario-panel panel" id="scenario" aria-labelledby="scenario-title">
        <div class="panel-heading"><h2 id="scenario-title">Scenario</h2><span class="section-index">01</span></div>
        <div class="fixture-control"><label for="fixture-select">Declared network example</label><select id="fixture-select"><option value="0">Direct to Earth</option><option value="1">One lunar relay</option></select><p class="muted">Both examples use the same 100 MiB task and hardware. All contact windows are synthetic.</p></div>
        <div class="scenario-actions"><button class="primary" id="plan-button" type="button">Plan delivery</button><button id="cancel-button" type="button" hidden>Cancel job</button><button id="restore-button" type="button">Restore fixture</button><button id="retry-button" type="button" hidden>Retry same scenario</button></div>
        <p id="job-status" role="status" aria-live="polite">Ready to inspect the captured engine result.</p>
        <div id="validation-errors" class="error-message" role="alert" hidden></div>
        <div id="scenario-form"></div>
      </aside>
      <div class="analysis-column">
        <section class="map-panel panel" aria-labelledby="map-title">
          <div class="panel-heading"><div><h2 id="map-title">Lunar context</h2><p class="muted">Terrain display. Scientific analysis comes from the Python engine.</p></div><span class="section-index">02</span></div>
          <div id="moon-view" class="moon-view" aria-label="Moon terrain viewport"></div>
          <div class="map-details"><p id="map-status" role="status">Preparing map context.</p><p id="display-status" role="status"></p><p id="selected-state" class="muted"></p><p id="analysis-location"></p><p id="draft-location" class="muted" hidden></p><p id="display-pick" class="muted" role="status" hidden></p></div>
        </section>
        <section class="panel timeline-panel" aria-labelledby="timeline-title">
          <div class="panel-heading"><h2 id="timeline-title">Contact timeline</h2><span class="section-index">03</span></div>
          <label class="check-field"><input id="hand-reference" type="checkbox" /> Show hand-calculated reference</label>
          <p class="muted">Reference arithmetic is separate from the engine result. It does not establish energy feasibility.</p>
          <div id="timeline"></div>
        </section>
        <section class="panel result-panel" id="result-section" aria-labelledby="result-title">
          <div class="panel-heading"><h2 id="result-title">Delivery result</h2><span class="section-index">04</span></div>
          <p id="result-context" class="muted">Choose Plan delivery to load the captured engine output for this exact fixture.</p>
          <div id="result"></div>
          <div class="download-actions"><button id="download-scenario" type="button">Download scenario JSON</button><button id="download-result" type="button" disabled>Download result JSON</button><button id="download-package" type="button" disabled>Download fixture run package (ZIP)</button></div>
          <p class="muted">The package preserves the engine scenario, result, manifest, contacts, schedule, energy, buffers, replay, display metadata and structured explanation. No files are reconstructed in this browser.</p>
        </section>
        <section class="panel science-panel" aria-labelledby="science-title">
          <div class="panel-heading"><h2 id="science-title">Sun, horizon and electrical power</h2><span class="section-index">05</span></div>
          <div class="science-source"><label for="science-source">Scientific diagnostic example</label><select id="science-source"><option value="synthetic">Scenario-matched synthetic inputs</option><option value="recorded">Recorded real LOLA example (separate site)</option></select><p id="science-context" class="notice"></p><button id="download-environment" type="button">Download diagnostic JSON</button></div>
          <div id="science"></div>
        </section>
        <section class="panel comparison-panel" aria-labelledby="comparison-title">
          <div class="panel-heading"><h2 id="comparison-title">Compare saved results</h2><span class="section-index">06</span></div>
          <div class="download-actions"><button id="save-a" type="button" disabled>Save current result as A</button><button id="save-b" type="button" disabled>Save current result as B</button><button id="reset-comparison" type="button">Restore comparison fixtures</button></div>
          <p id="comparison-status" role="status">A and B contain the captured direct and relay fixtures.</p>
          <div id="comparison"></div>
        </section>
      </div>
    </div>
    <footer><p>A planning model under declared assumptions. No service booking or mission prediction.</p><a href="https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/" target="_blank" rel="noreferrer">2026 Lunar Landing Site Navigator brief</a></footer>
  </main>`;

const byId = id => document.getElementById(id);
byId('workspace-mode').textContent = apiUrl ? 'Live · Python planning service' : 'Offline · Captured fixtures';
if (apiUrl) {
  byId('download-package').textContent = 'Download run package (ZIP)';
  document.querySelector('.project-notice').textContent = 'Live planning service. The declared examples use synthetic geometry, service and rate assumptions. Results come from Python; failed service requests do not load a fixture result.';
  byId('job-status').textContent = 'Ready to submit the declared scenario to Python.';
  byId('result-context').textContent = 'Choose Plan delivery to request a result from the live service.';
}
let activeFixture = fixtures[0];
let scenario = structuredClone(activeFixture.scenario);
let result = null;
let currentSummary;
let currentDisplay;
let modified = false;
let pendingFields = false;
let generation = 0;
let selectedTime = scenario.data_ready_utc;
let timeline;
let viewer;
let science;
const capturedComparisons = () => fixtures.map(item => structuredClone({ name: item.name, scenario: item.scenario, result: item.result, summary: item.summary }));
let comparisonEntries = capturedComparisons();
const comparison = renderComparison(byId('comparison'), { entries: comparisonEntries });

function selectedEnvironment() {
  if (byId('science-source').value === 'recorded') return { environment: realEnvironment, raw: realEnvironmentText };
  if (apiUrl) return currentDisplay?.environment ? { environment: currentDisplay.environment, raw: `${JSON.stringify(currentDisplay.environment, null, 2)}\n` } : {};
  return modified ? {} : { environment: activeFixture.environment, raw: activeFixture.environmentText };
}

function refreshScience() {
  const { environment } = selectedEnvironment();
  science?.destroy();
  const recorded = byId('science-source').value === 'recorded';
  science = renderScience(byId('science'), { environment, selectedTime, fixtureBacked: !apiUrl && !recorded });
  byId('download-environment').disabled = !environment;
  const point = environment?.analysis_point;
  byId('science-context').textContent = !environment
    ? 'No matching completed-job scientific diagnostic. Saved fixture graphics are hidden.'
    : `${recorded ? 'Separate recorded case using real LOLA and DE421 data; it does not change the scenario or delivery result.' : apiUrl ? 'Exact completed-job diagnostic from Python. Input provenance and synthetic labels are preserved below.' : 'Synthetic algorithm example: all directions, skyline and contact geometry are invented inputs, processed by Python.'} Site ${point.latitude_deg}° planetocentric, ${point.longitude_deg_east}° east; ${point.frame}. Antenna ${point.antenna_height_m} m; panel ${point.panel_height_m} m. Scenario SHA-256 ${environment.scenario_sha256}.`;
}

function showErrors(messages = []) {
  const box = byId('validation-errors');
  box.replaceChildren();
  box.hidden = messages.length === 0;
  for (const message of messages) {
    const paragraph = document.createElement('p');
    paragraph.textContent = message;
    box.append(paragraph);
  }
}

function updateLocation() {
  const fixturePoint = apiUrl ? scenario.lander : activeFixture.scenario.lander;
  const label = apiUrl ? 'Declared scenario point (not renderer-resolved)' : 'Fixture analysis point (synthetic, not service-resolved)';
  byId('analysis-location').textContent = `${label}: ${fixturePoint.latitude_deg}° planetocentric, ${fixturePoint.longitude_deg_east}° east. ${fixturePoint.frame}. Declared elevation ${fixturePoint.elevation_m} m (${fixturePoint.elevation_datum}); reference radius ${fixturePoint.reference_radius_m} m. Antenna ${fixturePoint.antenna_height_m} m; panel ${fixturePoint.panel_height_m} m above declared ground.`;
  const draft = byId('draft-location');
  draft.hidden = !modified;
  const lander = scenario.lander;
  const reference = apiUrl ? 'The declared point has not been registered to the renderer.' : 'The fixture point above is a reference only.';
  draft.textContent = pendingFields
    ? `Draft fields are being edited. No new analysis point has been resolved. ${reference}`
    : `Draft scenario point: ${lander.latitude_deg}° planetocentric, ${lander.longitude_deg_east}° east in declared ${lander.frame}. Antenna ${lander.antenna_height_m} m; panel ${lander.panel_height_m} m. Elevation, frame registration and terrain coverage have not been resolved for these edits. ${reference}`;
}

function clearDisplayPick() {
  byId('display-pick').hidden = true;
  viewer?.clearDisplayPick();
}

function refreshOutput() {
  const contacts = apiUrl ? result?.contacts ?? [] : modified ? [] : activeFixture.contacts;
  const expected = !modified && byId('hand-reference').checked ? activeFixture.expected : undefined;
  renderResult(byId('result'), { result, scenario, contacts, expected });
  timeline?.destroy();
  timeline = renderTimeline(byId('timeline'), {
    scenario, result, contacts, expected,
    onTimeChange(epoch) { selectedTime = epoch; viewer?.setTime(epoch); science?.setTime(epoch); refreshSelectedState(); },
  });
  timeline.setTime(selectedTime);
  selectedTime = timeline.getTime();
  if (selectedTime) viewer?.setTime(selectedTime);
  refreshScience();
  refreshSelectedState();
  byId('download-result').disabled = !result;
  byId('download-package').disabled = !result;
  byId('hand-reference').disabled = modified;
  byId('save-a').disabled = !result;
  byId('save-b').disabled = !result;
}

function refreshSelectedState() {
  byId('selected-state').textContent = displayTimeText(currentDisplay, selectedTime);
}

function setBusy(busy) {
  byId('plan-button').disabled = busy;
  byId('cancel-button').hidden = !busy;
  byId('result-section').setAttribute('aria-busy', String(busy));
}

function cancelCurrent(message) {
  generation++;
  currentSummary = undefined;
  currentDisplay = undefined;
  viewer?.setDisplay(undefined);
  byId('display-status').textContent = 'No current display artifact. Aligned overlays remain blocked.';
  const canceledGeneration = generation;
  Promise.resolve(client.cancel()).catch(error => { if (generation === canceledGeneration) showErrors([error.message]); });
  setBusy(false);
  byId('retry-button').hidden = true;
  if (message) byId('job-status').textContent = message;
}

const form = renderScenarioForm(byId('scenario-form'), {
  scenario,
  onChange(next) {
    cancelCurrent('Scenario changed. Request a new result; the previous result has been cleared.');
    scenario = next;
    result = null;
    modified = true;
    pendingFields = false;
    showErrors();
    byId('result-context').textContent = 'Edited scenario. Synthetic fixture contacts and results are hidden until an exact matching result is available.';
    updateLocation();
    clearDisplayPick();
    viewer?.setScenario(scenario);
    refreshOutput();
  },
});

byId('scenario-form').addEventListener('input', () => {
  cancelCurrent('Scenario fields changed. Request a new result after completing the edit.');
  result = null;
  modified = true;
  pendingFields = true;
  showErrors();
  byId('result-context').textContent = 'Scenario fields changed. Previous results and synthetic reference contacts are hidden.';
  updateLocation();
  clearDisplayPick();
  refreshOutput();
});

function restoreFixture() {
  cancelCurrent(apiUrl ? 'Example restored. Ready to submit it to Python.' : 'Fixture restored. Ready to inspect its captured engine result.');
  scenario = structuredClone(activeFixture.scenario);
  result = null;
  modified = false;
  pendingFields = false;
  selectedTime = scenario.data_ready_utc;
  byId('hand-reference').checked = false;
  clearDisplayPick();
  byId('result-context').textContent = apiUrl ? 'Choose Plan delivery to request a live result for this scenario.' : 'Choose Plan delivery to load the captured engine output for this exact fixture.';
  form.setScenario(scenario);
  showErrors();
  updateLocation();
  viewer?.setScenario(scenario);
  refreshOutput();
}

byId('fixture-select').addEventListener('change', event => {
  activeFixture = fixtures[Number(event.target.value)];
  restoreFixture();
});
byId('restore-button').addEventListener('click', restoreFixture);
byId('hand-reference').addEventListener('change', refreshOutput);
byId('cancel-button').addEventListener('click', () => {
  cancelCurrent('Job canceled. No partial success result is displayed.');
  result = null;
  refreshOutput();
});
byId('science-source').addEventListener('change', refreshScience);
for (const [id, index] of [['save-a', 0], ['save-b', 1]]) byId(id).addEventListener('click', () => {
  if (!result) return;
  comparisonEntries[index] = structuredClone({ name: `Saved ${index === 0 ? 'A' : 'B'}: ${scenario.scenario_id}`, scenario, result, summary: currentSummary });
  comparison.setEntries(comparisonEntries);
  byId('comparison-status').textContent = `Saved the exact scenario and result as ${index === 0 ? 'A' : 'B'}. Later edits do not change this snapshot.`;
});
byId('reset-comparison').addEventListener('click', () => {
  comparisonEntries = capturedComparisons();
  comparison.setEntries(comparisonEntries);
  byId('comparison-status').textContent = 'A and B contain the captured direct and relay fixtures.';
});
const stages = {
  validation: 'Validating scenario', horizon_preparation: 'Preparing horizon data',
  contact_construction: 'Constructing usable contacts', scheduling: 'Scheduling transfers',
  replay: 'Replaying constraints', export: 'Building exports', captured_engine_fixture: 'Loading captured engine run',
};
async function requestPlan(retry = false) {
  if (!byId('scenario-form').querySelector('form').reportValidity()) return;
  const snapshot = form.getScenario();
  const validity = validateScenario(snapshot);
  if (!validity.valid) { showErrors(validity.errors); return; }
  const current = ++generation;
  result = null;
  currentSummary = undefined;
  currentDisplay = undefined;
  viewer?.setDisplay(undefined);
  byId('display-status').textContent = 'No current display artifact. Waiting for the new completed job.';
  refreshOutput();
  showErrors();
  setBusy(true);
  byId('retry-button').hidden = true;
  byId('job-status').textContent = apiUrl ? 'Submitting scenario to the planning service.' : 'Checking the exact scenario against captured engine fixtures.';
  try {
    const callbacks = {
      onProgress(progress) {
        if (current === generation) byId('job-status').textContent = progress.message ?? `${stages[progress.stage] ?? progress.stage}.`;
      },
    };
    const nextResult = retry ? await client.retry(callbacks) : await client.plan(snapshot, callbacks);
    if (current !== generation) return;
    result = nextResult;
    byId('job-status').textContent = `Result loaded: ${result.status}. Loading completed-job summary and display.`;
    byId('result-context').textContent = apiUrl ? 'Engine result matched to the submitted scenario hash.' : 'Captured Python engine output for this exact scenario. This offline client performed no scientific calculation.';
    refreshOutput();
    const artifacts = await Promise.allSettled([client.getSummary(snapshot), client.getDisplay(snapshot)]);
    if (current !== generation) return;
    const nextSummary = artifacts[0].status === 'fulfilled' ? artifacts[0].value : undefined;
    const nextDisplay = artifacts[1].status === 'fulfilled' ? artifacts[1].value : undefined;
    const errors = artifacts.flatMap((artifact, index) => artifact.status === 'rejected' && artifact.reason.name !== 'AbortError' && (apiUrl || index === 0) ? [`${index === 0 ? 'Summary' : 'Display'} unavailable: ${artifact.reason.message}`] : []);
    showErrors(errors);
    result = nextResult;
    currentSummary = nextSummary;
    currentDisplay = nextDisplay;
    viewer?.setDisplay(nextDisplay);
    byId('display-status').textContent = nextDisplay ? `Completed-job display ${nextDisplay.format_version}; scenario SHA-256 ${nextDisplay.scenario_sha256}. ${registrationGate(nextDisplay.registration, scenario.lander.frame).reason}` : 'Display artifact unavailable. Numerical schedule and exact run package remain usable; aligned overlays are blocked.';
    const matching = fixtures.find(item => item.result.scenario_sha256 === result.scenario_sha256);
    if (matching && !apiUrl) { activeFixture = matching; modified = false; pendingFields = false; }
    updateLocation();
    byId('job-status').textContent = `Result loaded: ${result.status}. Solver: ${result.solver_status}.`;
    byId('result-context').textContent = apiUrl ? 'Engine result matched to the submitted scenario hash.' : 'Captured Python engine output for this exact scenario. This offline client performed no scientific calculation.';
    refreshOutput();
  } catch (error) {
    if (current !== generation || error.name === 'AbortError') return;
    result = null;
    byId('job-status').textContent = 'No delivery result is available for this request.';
    showErrors([error.message]);
    byId('retry-button').hidden = false;
    refreshOutput();
  } finally { if (current === generation) setBusy(false); }
}
byId('plan-button').addEventListener('click', () => requestPlan());
byId('retry-button').addEventListener('click', () => requestPlan(true));

function download(text, filename, type = 'application/json') {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
byId('download-scenario').addEventListener('click', () => {
  if (!byId('scenario-form').querySelector('form').reportValidity()) {
    showErrors(['Complete valid scenario fields before downloading. No scenario was exported.']);
    return;
  }
  const snapshot = form.getScenario();
  const validity = validateScenario(snapshot);
  if (!validity.valid) { showErrors(validity.errors); return; }
  download(`${JSON.stringify(snapshot, null, 2)}\n`, `${scenario.scenario_id}-scenario.json`);
});
byId('download-result').addEventListener('click', () => {
  if (!result) return;
  const captured = !apiUrl && fixtures.find(item => item.result.scenario_sha256 === result.scenario_sha256);
  download(captured?.resultText ?? `${JSON.stringify(result, null, 2)}\n`, `${result.scenario_id}-result.json`);
});
byId('download-environment').addEventListener('click', () => {
  const { environment, raw } = selectedEnvironment();
  if (environment && raw) download(raw, `${environment.scenario_id}-environment.json`);
});
byId('download-package').addEventListener('click', async () => {
  if (!result) return;
  const current = generation;
  byId('download-package').disabled = true;
  try {
    const archive = await client.exportRun(form.getScenario());
    if (current === generation) download(archive.bytes, archive.filename, 'application/zip');
  } catch (error) {
    if (current === generation) showErrors([error.message]);
  } finally {
    if (current === generation) byId('download-package').disabled = !result;
  }
});

updateLocation();
refreshOutput();
viewer = await createMoonViewer(byId('moon-view'), {
  scenario, ionToken: import.meta.env.VITE_CESIUM_ION_TOKEN,
  onStatus(status) {
    byId('map-status').textContent = status.message;
    if (['fallback', 'tile_failure', 'render_failure'].includes(status.state)) byId('display-pick').hidden = true;
  },
  onPick(pick) {
    byId('display-pick').hidden = false;
    byId('display-pick').textContent = `Display selection (renderer coordinates only): ${pick.latitude_deg}° latitude, ${pick.longitude_deg_east}° east; rendered elevation ${pick.display_elevation_m} m. This is not a ${scenario.lander.frame} analysis point. It awaits engine resolution of elevation, frame registration and terrain coverage. The fixture analysis point, scenario and equipment heights have not changed.`;
  },
});
viewer.setScenario(scenario);
viewer.setTime(selectedTime);

window.addEventListener('pagehide', () => {
  cancelCurrent();
  timeline?.destroy();
  science?.destroy();
  comparison.destroy();
  viewer?.destroy();
}, { once: true });
