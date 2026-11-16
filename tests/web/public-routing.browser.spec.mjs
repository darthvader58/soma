import { createRequire } from 'node:module';
import { readFile } from 'node:fs/promises';
import { researchCatalog, researchCapabilities } from './research-support.mjs';

const require = createRequire(new URL('../../web/package.json', import.meta.url));
const { test, expect } = require('@playwright/test');

// This spec uses the production entry document and never installs the legacy harness.
test.beforeEach(async ({ page }) => {
  await page.route('**/api/research/catalog', route => route.fulfill({ json: researchCatalog }));
  await page.route('**/api/research/capabilities', route => route.fulfill({ json: { ...researchCapabilities, ready: false } }));
  await page.route('**/src/workbench-viewer.js', route => route.fulfill({
    contentType: 'text/javascript',
    body: `export async function createWorkbenchViewer(container, { onStatus }) {
      onStatus('Test-only routing display. No terrain or scientific result.');
      return { setCatalog() {}, setSelection() {}, setResult() {}, setTime() {}, camera() {}, setLayers() {} };
    }`,
  }));
});

for (const legacyPath of ['/', '/?mode=archive', '/?mode=archive&case=direct-later', '/?mode=archive&case=relay-later#timeline-section']) {
  test(`public entry ${legacyPath} opens only the current dashboard`, async ({ page, baseURL }) => {
    const requestedModules = [];
    page.on('request', request => { if (request.resourceType() === 'script') requestedModules.push(new URL(request.url()).pathname); });
    await page.goto(legacyPath);
    await expect(page).toHaveURL(new URL('/', baseURL).href);
    await expect(page.getByRole('heading', { name: 'Lunar research workbench', exact: true })).toBeVisible();
    await expect(page.locator('#study-inputs')).toBeVisible();
    await expect(page.getByRole('link', { name: /delivery archive/i })).toHaveCount(0);
    await expect(page.locator('#mission-cases')).toHaveCount(0);
    await expect(page.getByRole('heading', { name: /mission cases|plan a delivery from the moon/i })).toHaveCount(0);
    await expect(page.locator('body')).not.toContainText(/Archived delivery|Mission cases|case gallery/i);
    expect(requestedModules).not.toContain('/src/archive.js');
  });
}

test('production entry has no import or route to the retained delivery archive', async () => {
  const entry = await readFile(new URL('../../web/src/main.js', import.meta.url), 'utf8');
  expect(entry).toContain("import('./workbench.js')");
  expect(entry).not.toMatch(/import\s*(?:\(|[^;]*from\s*)['"][^'"]*archive/);
  expect(entry).not.toContain('./archive.js');
});
