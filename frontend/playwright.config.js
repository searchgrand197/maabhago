import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  timeout: 120000,
  expect: { timeout: 10000 },
  use: {
    baseURL: 'http://127.0.0.1:5173',
    headless: true,
    viewport: { width: 1440, height: 900 },
  },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 5173',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: true,
    timeout: 120000,
  },
  projects: [
    {
      name: 'setup',
      testMatch: /auth\.setup\.spec\.js/,
    },
    {
      name: 'chromium',
      testIgnore: /auth\.setup\.spec\.js/,
      use: {
        storageState: 'playwright/.auth/pharmacy-user.json',
      },
      dependencies: ['setup'],
    },
  ],
})

