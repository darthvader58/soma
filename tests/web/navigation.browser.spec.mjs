import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { gzipSync } from 'node:zlib';
import { createServer } from 'node:http';
import { researchCatalog, researchCapabilities } from './research-support.mjs';
const require = createRequire(new URL('../../web/package.json', import.meta.url));
const { test, expect } = require('@playwright/test');
const fixtureServers = new Set();
test.afterEach(async () => {
  await Promise.all([...fixtureServers].map(server => new Promise(resolve => { server.close(resolve); server.closeAllConnections(); })));
  fixtureServers.clear();
});

test('visible real-Cesium camera controls work in both tools and remain keyboard reachable at 390px', async ({ page }, info) => {
  const errors = []; const calculations = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/api/research/catalog', route => route.fulfill({ json: researchCatalog }));
  await page.route('**/api/research/capabilities', route => route.fulfill({ json: { ...researchCapabilities, ready: false } }));
  await page.route('**/api/research/delivery/capabilities', route => route.fulfill({ status: 503, json: { detail: 'Test-only source unavailable' } }));
  page.on('request', request => { if (request.url().endsWith('/analyze')) calculations.push(request.url()); });
  await page.goto('/');
  const navigation = page.getByRole('region', { name: 'Moon camera navigation', exact: true });
  await expect(page.getByRole('button', { name: 'Zoom in', exact: true })).toBeEnabled();
  const start = await page.locator('#study-start').inputValue();
  const time = await page.locator('#selected-utc').textContent();
  await page.getByRole('button', { name: 'Zoom in', exact: true }).click();
  const zoomed = await navigation.getAttribute('data-camera-position');
  expect(JSON.parse(zoomed).every(Number.isFinite)).toBe(true);
  await navigation.locator('summary[aria-label="Pan, rotate & tilt"]').click();
  for (const name of ['Pan left', 'Pan right', 'Pan up', 'Pan down', 'Rotate left', 'Rotate right', 'Tilt up', 'Tilt down', 'Zoom out']) {
    await page.getByRole('button', { name, exact: true }).click();
    await expect(page.locator('#camera-navigation-state')).toContainText('Manual view');
  }
  await expect(page.locator('[data-camera="global"]')).toHaveAttribute('aria-pressed', 'false');
  const manualPosition = await navigation.getAttribute('data-camera-position');
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await navigation.getAttribute('data-camera-position')).toBe(manualPosition);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  expect(await navigation.locator('details').getAttribute('open')).not.toBeNull();
  const panelBounds = await navigation.boundingBox(), captionBounds = await page.locator('#research-map-status').boundingBox(), canvasBounds = await page.locator('#research-moon').boundingBox();
  expect(panelBounds.y).toBeGreaterThanOrEqual(captionBounds.y + captionBounds.height);
  expect(panelBounds.y).toBeGreaterThanOrEqual(canvasBounds.y + canvasBounds.height);
  const pan = page.getByRole('button', { name: 'Pan left', exact: true });
  await page.keyboard.press('Tab'); await pan.focus(); await expect(pan).toBeFocused();
  await page.keyboard.press('Enter');
  expect(await navigation.getAttribute('data-camera-position')).not.toBe(manualPosition);
  const tilt = page.getByRole('button', { name: 'Tilt down', exact: true });
  await tilt.focus(); await page.keyboard.press('Enter');
  const scrolledPanel = await navigation.boundingBox();
  for (const name of ['Zoom in', 'Zoom out', 'Reset view']) {
    const bounds = await page.getByRole('button', { name, exact: true }).boundingBox();
    expect(bounds.y).toBeGreaterThanOrEqual(scrolledPanel.y);
    expect(bounds.y + bounds.height).toBeLessThanOrEqual(scrolledPanel.y + scrolledPanel.height);
    await expect(page.getByRole('button', { name, exact: true })).toBeInViewport();
  }
  await page.getByRole('button', { name: 'Reset view', exact: true }).click();
  await expect(page.locator('[data-camera="global"]')).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', { name: 'Data delivery', exact: true }).click();
  await page.getByRole('button', { name: 'Zoom out', exact: true }).click();
  await expect(page.locator('#camera-navigation-state')).toContainText('Manual view');
  await page.getByRole('button', { name: 'Reset view', exact: true }).focus();
  await page.keyboard.press('Space');
  await expect(page.locator('#camera-navigation-state')).toContainText('global view');
  await page.screenshot({ path: info.outputPath('camera-controls-mobile.png'), fullPage: true });
  await page.getByRole('button', { name: 'Geometry', exact: true }).click();
  expect(await page.locator('#study-start').inputValue()).toBe(start);
  expect(await page.locator('#selected-utc').textContent()).toBe(time);
  expect(calculations).toEqual([]); expect(errors).toEqual([]);
});

for (const fallback of [false, true]) test(`Python Earth display fixture renders ${fallback ? 'a blue fallback after texture failure' : 'textured Earth and the full network'} without changing source epochs`, async ({ page }, info) => {
  test.skip(!process.env.SOMA_EARTH_BROWSER_FIXTURE, 'Set SOMA_EARTH_BROWSER_FIXTURE to a Python-produced full delivery envelope.');
  const artifact = JSON.parse(readFileSync(process.env.SOMA_EARTH_BROWSER_FIXTURE, 'utf8'));
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.route('**/api/research/catalog', route => route.fulfill({ json: researchCatalog }));
  await page.route('**/api/research/capabilities', route => route.fulfill({ json: { ...researchCapabilities, ready: false } }));
  const scenario = artifact.scenario;
  await page.route('**/api/research/delivery/capabilities', route => route.fulfill({ json: { ready: true, scenario_template: scenario,
    coverage: { ...scenario.analysis_horizon, latitude_bounds_deg: [-90, -87.5], longitude_bounds_deg_east: [-180, 180] },
    limits: { max_duration_s: 86400, max_data_volume_bytes: 134217728, max_chunks: 128, min_bin_s: 1, max_bin_s: 3600, max_solver_time_s: 10 }, library_capabilities: [] } }));
  const wireBytes = gzipSync(JSON.stringify(artifact));
  const fixtureServer = createServer((request, response) => {
    response.setHeader('Access-Control-Allow-Origin', '*');
    response.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    response.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    if (request.method === 'OPTIONS') { response.writeHead(204); response.end(); return; }
    response.writeHead(200, { 'Content-Type': 'application/json', 'Content-Encoding': 'gzip', 'Content-Length': wireBytes.length });
    response.end(wireBytes);
  });
  fixtureServers.add(fixtureServer);
  await new Promise((resolve, reject) => { fixtureServer.once('error', reject); fixtureServer.listen(0, '127.0.0.1', resolve); });
  const fixtureUrl = `http://127.0.0.1:${fixtureServer.address().port}/delivery`;
  await page.route('**/api/research/delivery/analyze', route => route.continue({ url: fixtureUrl }));
  if (fallback) await page.route('**/assets/earth/nasa-blue-marble-november-2004.jpg', route => route.abort());
  await page.goto('/'); await page.getByRole('button', { name: 'Data delivery', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Plan delivery', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Plan delivery', exact: true }).click();
  await expect(page.locator('#delivery-status')).toContainText('Calculated delivery in Python');
  const earth = page.getByRole('button', { name: 'Earth', exact: true });
  await expect(earth).toBeEnabled();
  expect(JSON.parse(await earth.getAttribute('data-radii'))).toEqual([6378137, 6378137, 6356752.314245179]);
  const epoch = artifact.result.allocations[0]?.source_transmit_interval.start_utc ?? scenario.data_ready_utc;
  await expect(earth).toHaveAttribute('data-epoch', epoch);
  await page.getByRole('button', { name: 'Earth', exact: true }).click();
  await expect(page.locator('#research-map-status')).toContainText('Python ITRF93 orientation');
  await expect(page.locator('.earth-display-credit')).toContainText(fallback ? 'blue reference surface; texture unavailable' : 'November 2004 reference composite');
  await page.screenshot({ path: info.outputPath(fallback ? 'earth-fallback-desktop.png' : 'earth-textured-desktop.png'), fullPage: true });
  await page.getByRole('button', { name: 'Earth network', exact: true }).click();
  await expect(page.locator('#research-map-status')).toContainText('Moon and Earth endpoints retain Python distances');
  await page.screenshot({ path: info.outputPath(fallback ? 'earth-network-fallback-desktop.png' : 'earth-network-desktop.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', { name: 'Earth', exact: true }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  const canvas = await page.locator('#research-moon').boundingBox(), controls = await page.locator('.scene-navigation').boundingBox();
  expect(controls.y).toBeGreaterThanOrEqual(canvas.y + canvas.height);
  await page.screenshot({ path: info.outputPath(fallback ? 'earth-fallback-mobile.png' : 'earth-textured-mobile.png'), fullPage: true });
  await page.getByRole('button', { name: 'Earth network', exact: true }).click();
  await page.screenshot({ path: info.outputPath(fallback ? 'earth-network-fallback-mobile.png' : 'earth-network-mobile.png'), fullPage: true });
  await expect(page.locator('#delivery-resource-readout')).toContainText(epoch);
  expect(errors).toEqual([]);
});
