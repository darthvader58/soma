import { createRequire } from 'node:module';
import { readFile } from 'node:fs/promises';
const require = createRequire(new URL('../../web/package.json', import.meta.url));
const { test, expect } = require('@playwright/test');

test('physical date presets use generated geometry and preserve exact engine artifacts without tiles', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.locator('#workspace-mode')).toContainText('Live');
  const submitted = [];
  for (const [name, slot] of [['physical-south-pole-nov-24', 'A'], ['physical-south-pole-nov-30', 'B']]) {
    await page.getByLabel('Declared network example').selectOption({ label: `Physical · ${name}` });
    await expect(page.locator('.scenario-form')).toContainText('Terrain and ephemeris scenario');
    await expect(page.locator('.scenario-form')).toContainText('synthetic_two_body_lunar_preset');
    await expect(page.getByLabel('Show hand-calculated reference')).toBeDisabled();
    const request = page.waitForRequest(request => request.method() === 'POST' && new URL(request.url()).pathname === '/api/plans');
    const response = page.waitForResponse(response => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/plans');
    await page.getByRole('button', { name: 'Plan delivery', exact: true }).click();
    submitted.push((await request).postDataJSON());
    const accepted = await response;
    expect(accepted.status()).toBe(202);
    const job = await accepted.json();
    await expect(page.locator('#display-status')).toContainText(job.scenario_sha256);
    const progress = await (await page.request.get(`/api/plans/${job.job_id}`)).json();
    expect(progress.status).toBe('completed');
    const result = progress.result;
    expect(['feasible_under_assumptions', 'infeasible_in_model']).toContain(result.status);
    console.log(JSON.stringify({ preset: name, job_id: job.job_id, scenario_sha256: job.scenario_sha256,
      status: result.status, solver_status: result.solver_status, model_fidelity: result.model_fidelity,
      delivered_bytes: result.delivered_bytes, contacts: result.contacts.length,
      allocations: result.allocations.length, storage_intervals: result.storage_intervals.length }));
    expect(result.model_fidelity).toBe('assumed_rate_simulation');
    await expect(page.locator('#result')).toContainText('Assumed-rate simulation');
    const display = await (await page.request.get(`/api/plans/${job.job_id}/display-data`)).json();
    expect(display.scenario_sha256).toBe(job.scenario_sha256);
    expect(display.allocations).toEqual(result.allocations);
    expect(display.energy_history).toEqual(result.energy_history);
    expect(display.environment.scenario_sha256).toBe(job.scenario_sha256);
    expect(display.environment.solar_samples.length).toBeGreaterThan(1);
    expect(display.states.length).toBeGreaterThan(1);
    expect(display.renderer_states.length).toBeGreaterThan(1);
    await expect(page.locator('#analysis-location')).toContainText('Completed-job analysis point from Python');
    await expect(page.locator('#analysis-location')).toContainText(String(display.environment.analysis_point.elevation_m));
    await expect(page.locator('#science-context')).toContainText('Exact completed-job diagnostic from Python');
    await expect(page.locator('#science-context')).not.toContainText('invented inputs');
    const epoch = display.states.find(state => state.target === submitted.at(-1).relay_refs[0] && state.time_scale === 'UTC').epoch;
    const posts = [];
    const recordPost = request => { if (request.method() === 'POST') posts.push(request.url()); };
    page.on('request', recordPost);
    await page.getByLabel('Stored engine sample (UTC / stated offset)', { exact: true }).selectOption(epoch);
    await expect(page.locator('#selected-state')).toContainText(epoch);
    await expect(page.locator('#selected-state')).toContainText('synthetic_two_body_lunar_preset');
    expect(posts).toEqual([]);
    page.off('request', recordPost);
    await page.getByRole('button', { name: `Save current result as ${slot}`, exact: true }).click();
    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Download run package (ZIP)', exact: true }).click();
    const downloaded = await readFile(await (await downloadPromise).path());
    const original = await (await page.request.get(`/api/plans/${job.job_id}/export`)).body();
    expect(downloaded.equals(original)).toBe(true);
    await page.getByRole('heading', { name: 'Delivery result', exact: true }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: test.info().outputPath(`${name}.png`) });
  }
  for (const key of ['lander', 'data_volume', 'hardware_profile_ref', 'route_families', 'relay_refs', 'station_refs']) {
    expect(submitted[0][key]).toEqual(submitted[1][key]);
  }
  await expect(page.locator('#comparison')).toContainText('Data-ready time changed; the absolute deadline also changed.');
  await expect(page.locator('#comparison')).toContainText('Initial battery energy (Wh): Unchanged');
  await expect(page.locator('#comparison')).toContainText('Analysis horizon: Changed');
  await page.getByRole('checkbox', { name: 'One lunar relay', exact: true }).uncheck();
  const directResponse = page.waitForResponse(response => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/plans');
  await page.getByRole('button', { name: 'Plan delivery', exact: true }).click();
  const directJob = await (await directResponse).json();
  console.log(JSON.stringify({ direct_job: directJob }));
  await expect.poll(async () => (await page.locator('#job-status').textContent()).trim(), { timeout: 180000 })
    .toMatch(/^(Result loaded:|No delivery result is available)/);
  expect(await page.locator('#validation-errors').textContent()).toBe('');
  await expect(page.locator('#display-status')).toContainText(directJob.scenario_sha256);
  const direct = await (await page.request.get(`/api/plans/${directJob.job_id}`)).json();
  console.log(JSON.stringify({ preset: 'nov-30-direct-only', job_id: directJob.job_id,
    scenario_sha256: directJob.scenario_sha256, status: direct.result.status,
    solver_status: direct.result.solver_status, delivered_bytes: direct.result.delivered_bytes,
    contacts: direct.result.contacts.length }));
  expect(direct.result.status).toBe('infeasible_in_model');
  expect(direct.result.contacts).toHaveLength(0);
  expect(direct.result.delivered_bytes).toBe(0);
  await expect(page.locator('#result')).toContainText('Infeasible');
  await expect(page.locator('#result')).toContainText(direct.result.provenance.reason);
  const directDownload = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download run package (ZIP)', exact: true }).click();
  const directBytes = await readFile(await (await directDownload).path());
  expect(directBytes.equals(await (await page.request.get(`/api/plans/${directJob.job_id}/export`)).body())).toBe(true);
  await page.getByRole('heading', { name: 'Delivery result', exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: test.info().outputPath('physical-result-desktop.png') });
  await page.setViewportSize({ width: 390, height: 1000 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: test.info().outputPath('physical-result-mobile.png') });
  expect(errors).toEqual([]);
});

