import { createRequire } from 'node:module';
import { readFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const require = createRequire(new URL('../../web/package.json', import.meta.url));
const { test, expect } = require('@playwright/test');
const python = fileURLToPath(new URL('../../.venv/bin/python', import.meta.url));

async function submit(page) {
  const response = page.waitForResponse(value => value.request().method() === 'POST' && new URL(value.url()).pathname === '/api/plans');
  await page.getByRole('button', { name: 'Plan delivery', exact: true }).click();
  const accepted = await response;
  expect(accepted.status()).toBe(202);
  return accepted.json();
}

async function completed(page, job) {
  await expect(page.locator('#job-status')).toContainText('Result loaded:');
  const response = await page.request.get(`/api/plans/${job.job_id}`);
  const body = await response.json();
  expect(body.status).toBe('completed');
  expect(body.scenario_sha256).toBe(job.scenario_sha256);
  await expect(page.locator('#result')).toContainText(job.scenario_sha256);
  return body.result;
}

test.beforeEach(async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.__somaErrors = errors;
  await page.goto('/');
  await expect(page.locator('#workspace-mode')).toContainText('Live');
  await expect(page.getByRole('heading', { name: 'Lunar terrain unavailable' })).toBeVisible();
});

test.afterEach(async ({ page }) => { expect(page.__somaErrors).toEqual([]); });

test('live engine computes direct failure and relay delivery; display, CSV and ZIP retain its exact schedule', async ({ page }) => {
  const directJob = await submit(page);
  const direct = await completed(page, directJob);
  expect(direct.status).toBe('infeasible_in_model');
  expect(direct.provenance.reason).toContain('307,200,000');

  await page.getByLabel('Declared network example').selectOption('1');
  const relayJob = await submit(page);
  const result = await completed(page, relayJob);
  expect(result.status).toBe('feasible_under_assumptions');
  expect(result.delivered_bytes).toBe(104857600);
  expect(['feasible_incumbent', 'proven_optimum']).toContain(result.solver_status);
  await expect(page.locator('#display-status')).toContainText(relayJob.scenario_sha256);
  const display = await (await page.request.get(`/api/plans/${relayJob.job_id}/display-data`)).json();
  expect(display.allocations).toEqual(result.allocations);
  expect(display.energy_history).toEqual(result.energy_history);
  expect(display.states).toEqual([]);
  expect(display.registration.release_gate.overlays_allowed).toBe(true);
  expect(display.registration.release_gate.map_registration_passed).toBe(true);
  expect(display.registration.representation).toBe('engine_corrected_mesh');
  expect(display.registration.status).toBe('registered_for_region');
  expect(display.registration.certified_region).toEqual({ latitude_deg: [-90, -87.5], longitude_deg_east: [-180, 180] });
  expect(display.registration.conversion_manifest_sha256).toMatch(/^[a-f0-9]{64}$/);
  expect(display.environment.scenario_sha256).toBe(relayJob.scenario_sha256);
  const snapshot = await page.locator('#result').textContent();
  const postRequests = [];
  page.on('request', request => { if (request.method() === 'POST') postRequests.push(request.url()); });
  const time = page.getByRole('slider', { name: 'Selected timeline time (UTC / stated offset)', exact: true });
  await time.focus(); await page.keyboard.press('End');
  await expect(page.locator('#selected-state')).toContainText('2026-11-14T10:05:00Z');
  await expect(page.locator('#selected-state')).toContainText('Spacecraft state: Unknown');
  const lastEnergy = display.energy_history.find(value => value.epoch_utc === '2026-11-14T10:05:00Z');
  expect(lastEnergy).toBeTruthy();
  await expect(page.locator('#selected-state')).toContainText(String(lastEnergy.stored_energy_wh));
  await expect(page.locator('#result')).toHaveText(snapshot);
  expect(postRequests).toEqual([]);

  const pending = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download run package (ZIP)', exact: true }).click();
  const download = await pending;
  const zipPath = test.info().outputPath('live-relay-run.zip');
  await download.saveAs(zipPath);
  const fromUI = await readFile(zipPath);
  const serverBytes = await (await page.request.get(`/api/plans/${relayJob.job_id}/export`)).body();
  expect(fromUI.equals(serverBytes)).toBe(true);
  const checked = JSON.parse(execFileSync(python, ['-c', `
import csv,hashlib,io,json,sys,zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
    m=json.loads(z.read('run-manifest.json'))
    assert all(hashlib.sha256(z.read(n)).hexdigest()==r['sha256'] for n,r in m['files'].items())
    result=json.loads(z.read('result.json')); display=json.loads(z.read('display-data.json'))
    assert display['allocations']==result['allocations']
    rows=list(csv.DictReader(io.StringIO(z.read('schedule.csv').decode())))
    print(json.dumps({'result':result,'schedule':rows,'replay':json.loads(z.read('replay.json'))}))
`, zipPath], { encoding: 'utf8' }));
  expect(checked.result).toEqual(result);
  expect(checked.replay.passed).toBe(true);
  expect(checked.schedule).toHaveLength(result.allocations.length);
  for (const allocation of result.allocations) {
    const row = checked.schedule.find(value => value.allocation_id === allocation.allocation_id);
    expect(row.source_transmit_start_utc).toBe(allocation.source_transmit_interval.start_utc);
    expect(row.source_transmit_end_utc).toBe(allocation.source_transmit_interval.end_utc);
    expect(row.receiver_occupancy_start_utc).toBe(allocation.receiver_occupancy_interval.start_utc);
    expect(row.receiver_occupancy_end_utc).toBe(allocation.receiver_occupancy_interval.end_utc);
    expect(row.byte_available_utc).toBe(allocation.byte_available_utc);
  }
  await page.getByRole('heading', { name: 'Delivery result', exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: test.info().outputPath('phase-5-live-relay.png') });
  await page.setViewportSize({ width: 390, height: 1000 });
  await page.getByRole('heading', { name: 'Delivery result', exact: true }).scrollIntoViewIfNeeded();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: test.info().outputPath('phase-5-live-mobile.png') });
});

test('changed volume is genuinely rescheduled and unsupported site coverage remains unknown', async ({ page }) => {
  await page.getByLabel('Data volume', { exact: true }).fill('16');
  await page.getByLabel('Volume unit (changing this changes the task)').selectOption('byte');
  const job = await submit(page);
  const result = await completed(page, job);
  expect(result.status).toBe('feasible_under_assumptions');
  expect(result.delivered_bytes).toBe(16);
  expect(result.scenario_sha256).not.toBe('857f1772d4052a5d06c955d6b63b847c989550442ada201d8ad592a1f95375ed');
  await page.getByLabel('Planetocentric latitude (°)', { exact: true }).fill('-88.5');
  const unknownJob = await submit(page);
  expect(unknownJob.scenario_sha256).not.toBe(job.scenario_sha256);
  const unknown = await completed(page, unknownJob);
  expect(unknown.status).toBe('unknown');
  expect(unknown.delivered_bytes).toBeNull();
  expect(unknown.warnings.join(' ')).toContain('site, frame, elevation or equipment heights');
  await expect(page.locator('#result')).toContainText('Unknown');
  await expect(page.locator('#result')).not.toContainText('Delivered16 bytes');
});

test('a real running service job can be canceled without publishing a success', async ({ page }) => {
  await page.getByLabel('Declared network example').selectOption('1');
  const job = await submit(page);
  await page.getByRole('button', { name: 'Cancel job', exact: true }).click();
  await expect(page.locator('#job-status')).toContainText('Job canceled');
  await expect.poll(async () => (await (await page.request.get(`/api/plans/${job.job_id}`)).json()).status).toBe('canceled');
  await expect(page.locator('#result')).toContainText('No engine result has been loaded');
  await expect(page.getByRole('button', { name: 'Download run package (ZIP)', exact: true })).toBeDisabled();
});

test('editing during a real job invalidates it and only the newer scenario is displayed', async ({ page }) => {
  await page.getByLabel('Declared network example').selectOption('1');
  const old = await submit(page);
  await page.getByLabel('Planetocentric latitude (°)', { exact: true }).fill('-88.5');
  const current = await submit(page);
  const result = await completed(page, current);
  expect(result.status).toBe('unknown');
  await expect(page.locator('#result')).not.toContainText(old.scenario_sha256);
  await expect.poll(async () => (await (await page.request.get(`/api/plans/${old.job_id}`)).json()).status).toBe('canceled');
  await expect(page.locator('#display-status')).toContainText(current.scenario_sha256);
});
