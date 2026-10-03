import { test, expect } from '@playwright/test'

const EMAIL = process.env.E2E_EMAIL
const PASSWORD = process.env.E2E_PASSWORD

test('authenticate and save storage state', async ({ page, context }) => {
  if (!EMAIL || !PASSWORD) {
    throw new Error('Set E2E_EMAIL and E2E_PASSWORD before running e2e tests.')
  }

  await page.goto('/login')
  await page.getByRole('button', { name: 'Pharmacy' }).click()
  await page.getByPlaceholder('admin@hospital.com').fill(EMAIL)
  await page.getByPlaceholder('••••••••').fill(PASSWORD)
  await page.getByRole('button', { name: /Sign In/i }).click()

  await page.waitForURL('**/pharmacy')
  await expect(page.getByRole('button', { name: 'Sales' })).toBeVisible()

  await context.storageState({ path: 'playwright/.auth/pharmacy-user.json' })
})

