import { chromium } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';

if (!process.argv[2] || !process.argv[3]) throw new Error('Usage: node scripts/capture-registration.mjs REQUEST_JSON OUTPUT_JSON');
const request = JSON.parse(await readFile(process.argv[2], 'utf8'));
const browser = await chromium.launch({
  ...(process.env.SOMA_BROWSER_EXECUTABLE ? { executablePath: process.env.SOMA_BROWSER_EXECUTABLE } : {}),
  args: ['--enable-unsafe-swiftshader'],
});
const page = await browser.newPage({ viewport: { width: 1200, height: 1000 } });
let pageErrors = 0, consoleErrors = 0;
page.on('pageerror', () => pageErrors++);
page.on('console', message => { if (message.type() === 'error') consoleErrors++; });
try {
  await page.goto('http://127.0.0.1:5173/registration.html');
  await page.locator('#probe-request').fill(JSON.stringify(request));
  await page.locator('#measure-probes').click();
  await page.waitForFunction(() => window.somaRegistrationMeasurement && window.somaRegistrationMeasurement.status !== 'running', undefined, { timeout: 140000 });
  const result = await page.evaluate(() => window.somaRegistrationMeasurement);
  result.capture = { engine: 'chromium', software_webgl_allowed: true, page_errors: pageErrors, console_errors: consoleErrors };
  await writeFile(process.argv[3], JSON.stringify(result, null, 2)+'\n');
  console.log(JSON.stringify({ status: result.status, measured: result.probes.filter(p => p.status === 'measured').length, total: result.probes.length }));
} catch (error) {
  // Browser network messages may contain signed URLs; report categories only.
  console.error(JSON.stringify({ error_type: error.name, page_errors: pageErrors, console_errors: consoleErrors }));
  process.exitCode = 1;
} finally { await browser.close(); }
