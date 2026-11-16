import { createRequire } from 'node:module';
import { readFile } from 'node:fs/promises';
const require = createRequire(new URL('../../web/package.json', import.meta.url));
const { test, expect } = require('@playwright/test');

test.beforeEach(async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Lunar terrain unavailable' })).toBeVisible();
  page.__somaErrors = errors;
});

test.afterEach(async ({ page }) => { expect(page.__somaErrors).toEqual([]); });

test('computed direct failure and replayed relay schedule remain separate from hand arithmetic', async ({ page }) => {
  await page.getByRole('button', { name: 'Plan delivery', exact: true }).click();
  await expect(page.locator('#job-status')).toContainText('infeasible_in_model');
  await expect(page.locator('#result')).toContainText('Solver: proven_infeasible_discretized_model');
  await expect(page.locator('#result')).toContainText('Model fidelity: assumed_rate_simulation');
  await expect(page.locator('#result')).toContainText('Delivered0 bytes');
  await page.getByLabel('Declared network example').selectOption('1');
  await expect(page.getByRole('checkbox', { name: 'One lunar relay', exact: true })).toBeChecked();
  await page.getByRole('button', { name: 'Plan delivery', exact: true }).click();
  await expect(page.locator('#job-status')).toContainText('feasible_under_assumptions');
  await expect(page.locator('#result')).toContainText('104,857,600 bytes');
  await expect(page.locator('#result')).toContainText('Assumed-rate simulation');
  await expect(page.locator('#result')).toContainText('receiver payload occupancy');
  await page.getByText('Scheduled transmissions and storage (14 transmissions)', { exact: true }).click();
  await expect(page.locator('#timeline .timeline-allocation').first()).toBeVisible();
  await page.getByLabel('Show hand-calculated reference').check();
  await expect(page.locator('#result')).toContainText('2026-11-14T09:06:59.4304Z');
  await expect(page.locator('#result')).toContainText('2026-11-14T10:01:23.88608Z');
  await expect(page.locator('#result')).toContainText('This is not an engine-generated plan');
  const timeline = page.getByRole('slider', { name: 'Selected timeline time (UTC / stated offset)', exact: true });
  await timeline.focus();
  await page.keyboard.press('End');
  await expect(page.locator('.timeline-time')).toHaveText('2026-11-14T10:05:00Z');
  await page.getByText('Declared hardware and assumptions', { exact: true }).click();
  await expect(page.locator('.scenario-hardware')).toContainText('storage_capacity_bytes');
  await page.getByText('Complete engine provenance', { exact: true }).click();
  await expect(page.locator('#result details pre')).toContainText('implementation_status');
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: test.info().outputPath('desktop-relay.png'), fullPage: false });
});

test('Phase 2 keeps fixture analysis coordinates separate from typed drafts and preserves the deadline rule', async ({ page }) => {
  await expect(page.locator('.phase-label')).toContainText('Phase 5');
  const fixturePoint = await page.locator('#analysis-location').textContent();
  await expect(page.locator('#analysis-location')).toContainText('synthetic, not service-resolved');
  await expect(page.locator('#analysis-location')).toContainText('Antenna 2 m; panel 1 m');
  await expect(page.getByRole('checkbox', { name: /Earth-orbit relay/ })).toBeDisabled();
  await expect(page.locator('.scenario-form')).toContainText('Deadline rule: fixed absolute deadline');
  const deadline = await page.getByLabel('Last-byte deadline (UTC / qualified offset)', { exact: true }).inputValue();
  const horizonEnd = await page.getByLabel('Analysis ends (UTC / qualified offset)', { exact: true }).inputValue();
  await page.getByLabel('Planetocentric latitude (°)', { exact: true }).fill('-88.5');
  await expect(page.locator('#draft-location')).toContainText('being edited');
  await page.getByLabel('Data ready (UTC / qualified offset)', { exact: true }).fill('2026-11-14T08:55:00Z');
  await page.getByLabel('Panel height (m)', { exact: true }).focus();
  await expect(page.locator('#draft-location')).toContainText('-88.5°');
  await expect(page.locator('#draft-location')).toContainText('have not been resolved');
  await expect(page.locator('#analysis-location')).toHaveText(fixturePoint);
  await expect(page.getByLabel('Last-byte deadline (UTC / qualified offset)', { exact: true })).toHaveValue(deadline);
  await expect(page.getByLabel('Analysis ends (UTC / qualified offset)', { exact: true })).toHaveValue(horizonEnd);
  await page.getByRole('button', { name: 'Restore fixture' }).click();
  await expect(page.locator('#draft-location')).toBeHidden();
});

test('display picks leave scientific inputs and captured output unchanged; scrub shares map time without planning', async ({ page }) => {
  // This module supplies controlled renderer events, not Moon tiles or scientific coordinates.
  await page.route('**/src/viewer.js', route => route.fulfill({ contentType: 'text/javascript', body: `
    export function registrationGate() { return { allowed: false, reason: 'Test renderer events only; scientific overlays blocked.' }; }
    export async function createMoonViewer(container, { onPick, onStatus }) {
      const pick = document.createElement('button');
      pick.textContent = 'Simulate renderer surface pick';
      const fail = document.createElement('button');
      fail.textContent = 'Simulate renderer failure';
      const state = document.createElement('p');
      state.textContent = 'Test renderer events only; no Moon tiles.';
      container.append(state, pick, fail);
      const clearDisplayPick = () => { container.dataset.marker = 'cleared'; };
      pick.onclick = () => { container.dataset.marker = 'display-only'; onPick({ latitude_deg: -88.75, longitude_deg_east: 15, display_elevation_m: 987, service_resolved: false }); };
      fail.onclick = () => { clearDisplayPick(); onStatus({ state: 'fallback', message: 'Simulated rendering failure. Use typed coordinates.' }); };
      return { setScenario() { clearDisplayPick(); }, setDisplay() {}, clearDisplayPick,
        setTime(epoch) { container.dataset.selectedTime = epoch; }, destroy() {} };
    }
  ` }));
  await page.reload();
  await page.getByRole('button', { name: 'Plan delivery', exact: true }).click();
  const result = await page.locator('#result').textContent();
  const status = await page.locator('#job-status').textContent();
  const fixturePoint = await page.locator('#analysis-location').textContent();
  await page.getByRole('button', { name: 'Simulate renderer surface pick' }).click();
  await expect(page.locator('#display-pick')).toContainText('Frame alignment is unverified at this point.');
  await expect(page.locator('#display-pick')).toContainText('rendered elevation 987 m');
  await expect(page.locator('#display-pick')).toContainText('Numerical DEM elevation and terrain coverage await service resolution.');
  await expect(page.locator('#moon-view')).toHaveAttribute('data-marker', 'display-only');
  await expect(page.locator('#analysis-location')).toHaveText(fixturePoint);
  await expect(page.getByLabel('Planetocentric latitude (°)', { exact: true })).toHaveValue('-89');
  await expect(page.getByLabel('Antenna height (m)', { exact: true })).toHaveValue('2');
  await expect(page.getByLabel('Panel height (m)', { exact: true })).toHaveValue('1');
  const slider = page.getByRole('slider', { name: 'Selected timeline time (UTC / stated offset)', exact: true });
  await slider.focus(); await page.keyboard.press('End');
  await expect(page.locator('#moon-view')).toHaveAttribute('data-selected-time', '2026-11-14T10:05:00Z');
  await expect(page.locator('#result')).toHaveText(result);
  await expect(page.locator('#job-status')).toHaveText(status);
  await page.getByRole('button', { name: 'Simulate renderer failure' }).click();
  await expect(page.locator('#display-pick')).toBeHidden();
  await expect(page.locator('#result')).toHaveText(result);
  await page.getByRole('button', { name: 'Simulate renderer surface pick' }).click();
  await page.getByRole('button', { name: 'Restore fixture' }).click();
  await expect(page.locator('#display-pick')).toBeHidden();
  await expect(page.locator('#moon-view')).toHaveAttribute('data-marker', 'cleared');
});

test('timeline preserves qualified-offset endpoints and disables an invalid horizon', async ({ page }) => {
  for (const [name, value] of [
    ['Analysis begins (UTC / qualified offset)', '2026-11-14T10:50:00.123456+02:00'],
    ['Analysis ends (UTC / qualified offset)', '2026-11-14T12:05:00.654321+02:00'],
  ]) {
    await page.getByLabel(name, { exact: true }).fill(value);
    await page.getByLabel('Panel height (m)', { exact: true }).focus();
  }
  const slider = page.getByRole('slider', { name: 'Selected timeline time (UTC / stated offset)', exact: true });
  await slider.focus(); await page.keyboard.press('End');
  await expect(page.locator('.timeline-time')).toHaveText('2026-11-14T12:05:00.654321+02:00');
  await expect(page.locator('.timeline-controls')).toContainText('UTC+02:00');
  await page.keyboard.press('Home');
  await expect(page.locator('.timeline-time')).toHaveText('2026-11-14T10:50:00.123456+02:00');
  await page.getByLabel('Analysis ends (UTC / qualified offset)', { exact: true }).fill('2026-11-14T08:00:00Z');
  await page.getByLabel('Panel height (m)', { exact: true }).focus();
  await expect(slider).toBeDisabled();
  await expect(page.locator('#timeline')).toContainText('Timeline unavailable');
});

test('Phase 3 science shows supplied heights, directions, unknown terrain and blocked reasons without planning', async ({ page }) => {
  const science = page.locator('#science');
  await expect(science).toContainText('Fixture-backed engine diagnostic');
  await expect(page.locator('#science-context')).toContainText('invented inputs, processed by Python');
  await expect(science.locator('.science-provenance')).toContainText('Height: 1 m');
  await expect(science).toContainText('Earth center (not a station)');
  await expect(science).toContainText('synthetic-earth-station (configured Earth station)');
  await expect(science).toContainText('synthetic_terrain_blockage');
  const contactTable = science.getByRole('table').filter({ has: page.getByRole('columnheader', { name: 'Contact / endpoints', exact: true }) });
  await expect(contactTable).not.toContainText('synthetic-blocked-interval');
  await page.getByLabel('Horizon observer height').focus();
  await page.getByLabel('Horizon observer height').selectOption('antenna');
  await expect(science.locator('.science-provenance')).toContainText('Height: 2 m');
  await expect(page.getByLabel('Horizon observer height')).toBeFocused();
  await expect(science.locator('.plot-endpoint').first()).toBeVisible();
  const jobStatus = await page.locator('#job-status').textContent();
  const slider = page.getByRole('slider', { name: 'Selected timeline time (UTC / stated offset)', exact: true });
  await slider.focus(); await page.keyboard.press('End');
  await expect(science.locator('.science-selected-time')).toContainText('2026-11-14T10:05:00Z');
  await expect(science).toContainText('Selected sample: 1.');
  await expect(page.locator('#job-status')).toHaveText(jobStatus);
  await page.getByLabel('Scientific diagnostic example').selectOption('recorded');
  await expect(page.locator('#science-context')).toContainText('Separate recorded case using real LOLA and DE421');
  await expect(science).toContainText('Selected sample: Unknown');
  await expect(science).toContainText('Battery status: unknown');
  await expect(science).toContainText('Converged: false');
  await expect(science).toContainText('No usable contacts supplied');
  await science.getByRole('img').first().scrollIntoViewIfNeeded();
  await page.screenshot({ path: test.info().outputPath('phase-3-real-science.png'), fullPage: false });
  await page.getByLabel('Scientific diagnostic example').selectOption('synthetic');
  await science.getByRole('img').first().scrollIntoViewIfNeeded();
  await page.screenshot({ path: test.info().outputPath('phase-3-synthetic-science.png'), fullPage: false });
  await page.setViewportSize({ width: 390, height: 1000 });
  await science.getByRole('img').first().scrollIntoViewIfNeeded();
  await page.screenshot({ path: test.info().outputPath('phase-3-mobile-science.png'), fullPage: false });
});

test('diagnostic downloads preserve engine bytes and edited inputs cannot reuse scientific graphics', async ({ page }) => {
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download diagnostic JSON' }).click();
  const downloaded = await readFile(await (await downloadPromise).path(), 'utf8');
  const source = await readFile(new URL('../../web/fixtures/synthetic-direct/environment.json', import.meta.url), 'utf8');
  expect(downloaded).toBe(source);
  const artifact = JSON.parse(downloaded);
  expect(artifact.artifact_type).toBe('soma_environment_diagnostic');
  expect(artifact).not.toHaveProperty('allocations');
  await page.getByLabel('Panel height (m)', { exact: true }).fill('3');
  await expect(page.locator('#science-context')).toContainText('No matching completed-job scientific diagnostic');
  await expect(page.getByRole('button', { name: 'Download diagnostic JSON' })).toBeDisabled();
  await expect(page.locator('#science svg')).toHaveCount(0);
});

test('two saved results expose task differences and remain immutable after edits', async ({ page }) => {
  await expect(page.locator('#comparison')).toContainText('Network configuration: Changed');
  await expect(page.locator('#comparison')).toContainText('Initial battery energy (Wh): Unchanged');
  await expect(page.locator('#comparison')).toContainText('synthetic-lunar-relay');
  await expect(page.locator('#comparison')).toContainText('Mean relay wait per byte (s)');
  await page.getByRole('button', { name: 'Plan delivery', exact: true }).click();
  await page.getByRole('button', { name: 'Save current result as A' }).click();
  await page.getByLabel('Declared network example').selectOption('1');
  await page.getByRole('button', { name: 'Plan delivery', exact: true }).click();
  await page.getByRole('button', { name: 'Save current result as B' }).click();
  const comparison = await page.locator('#comparison').textContent();
  await page.getByLabel('Planetocentric latitude (°)', { exact: true }).fill('-88');
  await expect(page.locator('#comparison')).toHaveText(comparison);
  await expect(page.getByRole('button', { name: 'Save current result as A' })).toBeDisabled();
  await page.getByRole('button', { name: 'Restore comparison fixtures' }).click();
  await expect(page.locator('#comparison-status')).toContainText('captured direct and relay fixtures');
});

test('editing invalidates captured output and cannot reuse an offline result', async ({ page }) => {
  await page.getByRole('button', { name: 'Plan delivery', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Download result JSON' })).toBeEnabled();
  await page.getByLabel('Antenna height (m)', { exact: true }).fill('3');
  await expect(page.getByRole('button', { name: 'Download result JSON' })).toBeDisabled();
  await page.getByLabel('Panel height (m)', { exact: true }).click();
  await page.getByRole('button', { name: 'Plan delivery', exact: true }).click();
  await expect(page.locator('#validation-errors')).toContainText('no captured engine result matches');
  await expect(page.locator('#result')).not.toContainText('b1d39f45');
  await page.getByRole('button', { name: 'Restore fixture' }).click();
  await expect(page.getByLabel('Antenna height (m)', { exact: true })).toHaveValue('2');
  await page.getByLabel('East longitude', { exact: false }).fill('180');
  await page.getByRole('button', { name: 'Plan delivery', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Download result JSON' })).toBeDisabled();
  await page.getByRole('button', { name: 'Restore fixture' }).click();
  await page.getByRole('checkbox', { name: 'Direct to Earth', exact: true }).uncheck();
  await page.getByRole('button', { name: 'Plan delivery', exact: true }).click();
  await expect(page.locator('#validation-errors')).toContainText('route_families');
});

test('JSON downloads preserve edited scenario fields and exact captured result bytes', async ({ page }) => {
  await page.getByRole('button', { name: 'Plan delivery', exact: true }).click();
  const resultPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download result JSON' }).click();
  const resultDownload = await resultPromise;
  const downloaded = await readFile(await resultDownload.path(), 'utf8');
  const original = await readFile(new URL('../../web/fixtures/synthetic-direct/result.json', import.meta.url), 'utf8');
  expect(downloaded).toBe(original);
  await page.getByLabel('Volume unit (changing this changes the task)').selectOption('byte');
  await page.getByLabel('Data volume', { exact: true }).fill('104857600');
  await page.getByLabel('Panel height (m)', { exact: true }).click();
  const scenarioPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download scenario JSON' }).click();
  const scenarioDownload = await scenarioPromise;
  const edited = JSON.parse(await readFile(await scenarioDownload.path(), 'utf8'));
  expect(edited.data_volume).toEqual({ value: 104857600, unit: 'byte' });
  expect(edited.profiles.hardware[0].storage_capacity_bytes).toBe(209715200);
  expect(edited.profiles.hardware[0].battery.initial_energy_wh).toBe(80);
  const invalidDownloads = [];
  page.on('download', item => invalidDownloads.push(item));
  await page.getByLabel('Planetocentric latitude (°)', { exact: true }).fill('');
  await page.getByRole('button', { name: 'Download scenario JSON' }).click();
  await expect(page.locator('#validation-errors')).toContainText('No scenario was exported');
  expect(invalidDownloads).toHaveLength(0);
});

test('complete fixture package downloads byte-for-byte and the selected schedule stays readable without tiles', async ({ page }) => {
  await page.getByLabel('Declared network example').selectOption('1');
  await page.getByRole('button', { name: 'Plan delivery', exact: true }).click();
  await expect(page.locator('#job-status')).toContainText('feasible_under_assumptions');
  await expect(page.getByRole('heading', { name: 'Lunar terrain unavailable' })).toBeVisible();
  await expect(page.locator('#result .details-list')).toContainText('104,857,600 bytes');
  await page.getByText('Inspect structured schedule explanation', { exact: true }).click();
  const explanation = page.locator('#result .result-section').filter({ has: page.getByRole('heading', { name: 'Structured schedule explanation', exact: true }) });
  await expect(explanation).toContainText('synthetic-lunar-relay to synthetic-earth-station');
  await expect(explanation).toContainText('bytes available');
  await page.getByText('Inspect engine battery history', { exact: true }).click();
  await expect(page.locator('#result')).toContainText('Stored energy (Wh)');
  const pending = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download fixture run package (ZIP)' }).click();
  const downloaded = await readFile(await (await pending).path());
  const original = await readFile(new URL('../../web/fixtures/synthetic-relay/run.zip', import.meta.url));
  expect(downloaded.equals(original)).toBe(true);
  await page.getByRole('heading', { name: 'Delivery result', exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: test.info().outputPath('phase-4-relay-result.png'), fullPage: false });
  await page.setViewportSize({ width: 390, height: 1000 });
  await page.getByRole('heading', { name: 'Delivery result', exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: test.info().outputPath('phase-4-mobile-result.png'), fullPage: false });
});

test('an explicitly delayed fixture job can be canceled without a stale success card', async ({ page }) => {
  const original = await readFile(new URL('../../web/src/client.js', import.meta.url), 'utf8');
  await page.route('**/src/client.js', route => route.fulfill({ contentType: 'text/javascript', body: original.replace('fixtureDelayMs = 0', 'fixtureDelayMs = 1500') }));
  await page.reload();
  await page.getByLabel('Declared network example').selectOption('1');
  await page.getByRole('button', { name: 'Plan delivery', exact: true }).click();
  await expect(page.locator('#job-status')).toContainText('Explicit delayed fixture test');
  await page.getByRole('button', { name: 'Cancel job', exact: true }).click();
  await expect(page.locator('#job-status')).toContainText('Job canceled');
  await page.waitForTimeout(1700);
  await expect(page.locator('#result')).toContainText('No engine result has been loaded');
  await expect(page.getByRole('button', { name: 'Download fixture run package (ZIP)' })).toBeDisabled();
});

test('retry retains the edited scenario and restore clears the retry action', async ({ page }) => {
  await page.getByLabel('Antenna height (m)', { exact: true }).fill('3');
  await page.getByRole('button', { name: 'Plan delivery', exact: true }).click();
  await expect(page.locator('#validation-errors')).toContainText('no captured engine result matches');
  await page.getByRole('button', { name: 'Retry same scenario', exact: true }).click();
  await expect(page.locator('#validation-errors')).toContainText('no captured engine result matches');
  await expect(page.getByLabel('Antenna height (m)', { exact: true })).toHaveValue('3');
  await page.getByRole('button', { name: 'Restore fixture', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Retry same scenario', exact: true })).toBeHidden();
});

test('all editable scenario fields round trip while hidden scientific metadata is preserved', async ({ page }) => {
  await page.getByLabel('Declared network example').selectOption('1');
  for (const [name, value] of [
    ['Planetocentric latitude (°)', '-88.5'],
    ['East longitude (°, −180 to <180)', '15'],
    ['Antenna height (m)', '3'], ['Panel height (m)', '1.5'],
    ['Data volume', '104857600'],
    ['Data ready (UTC / qualified offset)', '2026-11-14T08:51:00Z'],
    ['Last-byte deadline (UTC / qualified offset)', '2026-11-14T10:04:00Z'],
    ['Analysis begins (UTC / qualified offset)', '2026-11-14T08:49:00Z'],
    ['Analysis ends (UTC / qualified offset)', '2026-11-14T10:06:00Z'],
  ]) await page.getByLabel(name, { exact: true }).fill(value);
  await page.getByLabel('Volume unit (changing this changes the task)').selectOption('byte');
  await page.getByLabel('Hardware profile', { exact: true }).selectOption('synthetic-lander-hardware-v1');
  await page.getByRole('checkbox', { name: 'Direct to Earth', exact: true }).uncheck();
  await page.getByRole('checkbox', { name: 'One lunar relay', exact: true }).uncheck();
  await page.getByRole('checkbox', { name: 'One lunar relay', exact: true }).check();
  const relay = page.getByRole('checkbox', { name: /synthetic-lunar-relay/ });
  await relay.uncheck(); await relay.check();
  const pending = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download scenario JSON' }).click();
  const download = await pending;
  const edited = JSON.parse(await readFile(await download.path(), 'utf8'));
  const expected = JSON.parse(await readFile(new URL('../../web/fixtures/synthetic-relay/scenario.json', import.meta.url), 'utf8'));
  Object.assign(expected.lander, { latitude_deg: -88.5, longitude_deg_east: 15, antenna_height_m: 3, panel_height_m: 1.5 });
  expected.data_volume = { value: 104857600, unit: 'byte' };
  expected.data_ready_utc = '2026-11-14T08:51:00Z';
  expected.deadline_utc = '2026-11-14T10:04:00Z';
  expected.analysis_horizon = { start_utc: '2026-11-14T08:49:00Z', end_utc: '2026-11-14T10:06:00Z' };
  expected.route_families = ['single_lunar_relay'];
  expect(edited).toEqual(expected);
});

for (const width of [390, 820, 1440]) {
  test(`viewport ${width}px supports keyboard and contains the layout`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.getByRole('button', { name: 'Plan delivery', exact: true }).focus();
    await page.keyboard.press('Enter');
    await expect(page.locator('#job-status')).toContainText('infeasible_in_model');
    await page.getByLabel('Show hand-calculated reference').check();
    const dimensions = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth }));
    expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.width);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: test.info().outputPath(`workspace-${width}.png`), fullPage: false });
  });
}

test('keyboard focus, skip link and 200 percent text resizing remain usable', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 1000 });
  await page.getByRole('link', { name: 'Skip to scenario' }).focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/#scenario$/);
  await page.getByRole('button', { name: 'Plan delivery', exact: true }).focus();
  const focus = await page.locator('#plan-button').evaluate(node => getComputedStyle(node).outlineStyle);
  expect(focus).not.toBe('none');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Restore fixture' })).toBeFocused();
  await page.addStyleTag({ content: ':root { font-size: 200%; }' });
  const dimensions = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth }));
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.width);
  await expect(page.getByLabel('Planetocentric latitude (°)', { exact: true })).toBeVisible();
});
