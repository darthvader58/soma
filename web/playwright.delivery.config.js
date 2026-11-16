import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: '../tests/web', testMatch: '**/delivery-live.browser.spec.mjs', outputDir: 'test-results-delivery', workers: 1,
  timeout: 120000, expect: { timeout: 90000 },
  use: { baseURL: 'http://127.0.0.1:5191', browserName: 'chromium', viewport: { width: 1440, height: 1000 },
    launchOptions: process.env.SOMA_BROWSER_EXECUTABLE ? { executablePath: process.env.SOMA_BROWSER_EXECUTABLE } : {} },
  webServer: [
    { command: '../.venv/bin/uvicorn soma.api.app:app --app-dir .. --host 127.0.0.1 --port 8071',
      url: 'http://127.0.0.1:8071/docs', reuseExistingServer: false, timeout: 30000,
      env: { SOMA_RESEARCH_DATA_ROOT: '../api/_data', SOMA_RESEARCH_RUN_ROOT: '' },
      gracefulShutdown: { signal: 'SIGTERM', timeout: 3000 } },
    { command: 'npm run dev -- --port 5191 --strictPort', url: 'http://127.0.0.1:5191', reuseExistingServer: false,
      env: { VITE_SOMA_API_URL: '/api', SOMA_API_PROXY_TARGET: 'http://127.0.0.1:8071', VITE_CESIUM_ION_TOKEN: '' },
      gracefulShutdown: { signal: 'SIGTERM', timeout: 3000 } },
  ],
});
