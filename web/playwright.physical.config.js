import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '../tests/web',
  testMatch: '**/physical.browser.spec.mjs',
  outputDir: 'test-results-physical',
  workers: 1,
  timeout: 600000,
  expect: { timeout: 300000 },
  use: {
    baseURL: process.env.SOMA_PHYSICAL_TEST_URL || 'http://127.0.0.1:5187',
    browserName: 'chromium', viewport: { width: 1440, height: 1000 },
    launchOptions: process.env.SOMA_BROWSER_EXECUTABLE ? { executablePath: process.env.SOMA_BROWSER_EXECUTABLE } : {},
  },
});
