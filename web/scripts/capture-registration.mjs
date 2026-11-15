import { chromium } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';

if (!process.argv[2] || !process.argv[3]) throw new Error('Usage: node scripts/capture-registration.mjs REQUEST_JSON OUTPUT_JSON');
const request = JSON.parse(await readFile(process.argv[2], 'utf8'));
const diagnosticUrl = process.env.SOMA_REGISTRATION_URL || 'http://127.0.0.1:5173/registration.html';
const browser = await chromium.launch({
  ...(process.env.SOMA_BROWSER_EXECUTABLE ? { executablePath: process.env.SOMA_BROWSER_EXECUTABLE } : {}),
  args: ['--enable-unsafe-swiftshader'],
});
const page = await browser.newPage({ viewport: { width: 1200, height: 1000 } });
let pageErrors = 0, consoleErrors = 0;
page.on('pageerror', () => pageErrors++);
page.on('console', message => { if (message.type() === 'error') consoleErrors++; });
try {
  await page.goto(diagnosticUrl);
  // A large probe JSON can stall keyboard automation; set the textarea value
  // and dispatch the same input notification without altering diagnostic logic.
  await page.locator('#probe-request').evaluate((element, value) => {
    element.value = value;
    element.dispatchEvent(new Event('input', { bubbles: true }));
  }, JSON.stringify(request));
  await page.locator('#measure-probes').click();
  await page.waitForFunction(() => window.somaRegistrationMeasurement && window.somaRegistrationMeasurement.status !== 'running', undefined, { timeout: 140000 });
  const result = await page.evaluate(() => window.somaRegistrationMeasurement);
  if (new URL(diagnosticUrl).searchParams.get('representation') === 'registered' &&
      (result.scene_representation !== 'engine_corrected_mesh' || !result.conversion_manifest_sha256 || !result.registration_certificate_version)) {
    throw new Error('Corrected scene evidence is missing');
  }
  result.capture = { engine: 'chromium', software_webgl_allowed: true, page_errors: pageErrors, console_errors: consoleErrors };
  await writeFile(process.argv[3], JSON.stringify(result, null, 2)+'\n');
  console.log(JSON.stringify({ status: result.status, measured: result.probes.filter(p => p.status === 'measured').length, total: result.probes.length }));
} catch (error) {
  // Browser network messages may contain signed URLs; report categories only.
  console.error(JSON.stringify({ error_type: error.name, page_errors: pageErrors, console_errors: consoleErrors }));
  process.exitCode = 1;
} finally { await browser.close(); }
