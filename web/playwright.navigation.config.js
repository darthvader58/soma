import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: '../tests/web', testMatch: '**/navigation.browser.spec.mjs', outputDir: 'test-results-navigation', workers: 1,
  use: { baseURL: 'http://127.0.0.1:5193', browserName: 'chromium', viewport: { width: 1440, height: 1000 },
    launchOptions: process.env.SOMA_BROWSER_EXECUTABLE ? { executablePath: process.env.SOMA_BROWSER_EXECUTABLE } : {} },
  webServer: { command: 'npm run dev -- --port 5193 --strictPort', url: 'http://127.0.0.1:5193', reuseExistingServer: false,
    env: { VITE_CESIUM_ION_TOKEN: '', VITE_SOMA_API_URL: '/api' } },
});
