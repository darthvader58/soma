import { defineConfig } from '@playwright/test';

const port = Number(process.env.SOMA_FIXTURE_TEST_PORT || 5173);
if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('SOMA_FIXTURE_TEST_PORT must be an integer from 1024 to 65535.');
const baseURL = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: '../tests/web',
  testMatch: ['**/browser.spec.mjs', '**/research.browser.spec.mjs', '**/public-routing.browser.spec.mjs'],
  outputDir: 'test-results',
  workers: 1,
  fullyParallel: false,
  use: {
    baseURL,
    browserName: 'chromium',
    viewport: { width: 1440, height: 1000 },
    launchOptions: process.env.SOMA_BROWSER_EXECUTABLE ? { executablePath: process.env.SOMA_BROWSER_EXECUTABLE } : {},
  },
  webServer: {
    command: `npm run dev -- --port ${port} --strictPort`,
    url: baseURL,
    reuseExistingServer: false,
    env: { VITE_SOMA_MODE: 'fixture', VITE_SOMA_API_URL: '', VITE_CESIUM_ION_TOKEN: '' },
  },
});
