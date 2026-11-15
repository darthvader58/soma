import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '../tests/web',
  testMatch: '**/browser.spec.mjs',
  outputDir: 'test-results',
  workers: 1,
  fullyParallel: false,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    browserName: 'chromium',
    viewport: { width: 1440, height: 1000 },
    launchOptions: process.env.SOMA_BROWSER_EXECUTABLE ? { executablePath: process.env.SOMA_BROWSER_EXECUTABLE } : {},
  },
  webServer: {
    command: 'npm run dev',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: false,
    env: { VITE_SOMA_MODE: 'fixture', VITE_SOMA_API_URL: '', VITE_CESIUM_ION_TOKEN: '' },
  },
});
