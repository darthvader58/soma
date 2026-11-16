import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: '../tests/web', testMatch: '**/research-live.browser.spec.mjs', outputDir: 'test-results-research-live', workers: 1,
  timeout: 90000, expect: { timeout: 60000 },
  use: { baseURL: 'http://127.0.0.1:5189', browserName: 'chromium', viewport: { width: 1440, height: 1000 },
    launchOptions: process.env.SOMA_BROWSER_EXECUTABLE ? { executablePath: process.env.SOMA_BROWSER_EXECUTABLE } : {} },
  webServer: [
    { command: '../.venv/bin/uvicorn soma.api.app:app --app-dir .. --host 127.0.0.1 --port 8069',
      url: 'http://127.0.0.1:8069/docs', reuseExistingServer: false, timeout: 30000,
      env: { SOMA_RESEARCH_DATA_ROOT: '../api/_data', SOMA_RESEARCH_RUN_ROOT: '' },
      gracefulShutdown: { signal: 'SIGTERM', timeout: 3000 } },
    { command: 'npm run dev -- --port 5189 --strictPort', url: 'http://127.0.0.1:5189', reuseExistingServer: false,
      env: { VITE_SOMA_API_URL: '/api', SOMA_API_PROXY_TARGET: 'http://127.0.0.1:8069', VITE_CESIUM_ION_TOKEN: '' },
      gracefulShutdown: { signal: 'SIGTERM', timeout: 3000 } },
  ],
});
