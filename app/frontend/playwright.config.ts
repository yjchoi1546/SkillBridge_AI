import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests', fullyParallel: false, workers: 1, timeout: 35_000,
  reporter: 'list',
  use: { baseURL: process.env.SB_TEST_URL || 'http://127.0.0.1:5173', ...devices['Desktop Chrome'], channel: 'chrome', screenshot: 'only-on-failure', trace: 'retain-on-failure' },
  webServer: { command: `npm run dev -- --port ${new URL(process.env.SB_TEST_URL || 'http://127.0.0.1:5173').port}`, url: process.env.SB_TEST_URL || 'http://127.0.0.1:5173', reuseExistingServer: !process.env.CI },
});
