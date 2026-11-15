import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '../tests/web',
  testMatch: '**/live.browser.spec.mjs',
  outputDir: 'test-results-live',
  workers: 1,
  fullyParallel: false,
  timeout: 90000,
  expect: { timeout: 45000 },
  use: {
    baseURL: 'http://127.0.0.1:5175',
    browserName: 'chromium',
    viewport: { width: 1440, height: 1000 },
    launchOptions: process.env.SOMA_BROWSER_EXECUTABLE ? { executablePath: process.env.SOMA_BROWSER_EXECUTABLE } : {},
  },
  webServer: [
    {
      name: 'SOMA engine',
      command: '../.venv/bin/uvicorn soma.api.app:app --app-dir .. --host 127.0.0.1 --port 8065',
      url: 'http://127.0.0.1:8065/docs',
      reuseExistingServer: false,
      timeout: 30000,
      gracefulShutdown: { signal: 'SIGTERM', timeout: 3000 },
    },
    {
      name: 'SOMA live browser',
      command: 'npm run dev -- --port 5175',
      url: 'http://127.0.0.1:5175',
      reuseExistingServer: false,
      timeout: 30000,
      env: {
        VITE_SOMA_MODE: 'live',
        VITE_SOMA_API_URL: '/api',
        SOMA_API_PROXY_TARGET: 'http://127.0.0.1:8065',
        VITE_CESIUM_ION_TOKEN: '',
      },
      gracefulShutdown: { signal: 'SIGTERM', timeout: 3000 },
    },
  ],
});
