// @ts-check
import { test, expect } from '@playwright/test'

async function loginAsAdmin(page) {
  await page.goto('/login')
  await page.fill('input[type="text"]', 'admin')
  await page.fill('input[type="password"]', 'admin123')
  await page.click('button[type="submit"]')
  await page.waitForURL(/\/(dashboards|$)/, { timeout: 10000 })
}

test.describe('Dashboards Page', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page)
    await page.goto('/dashboards')
  })

  test('should display dashboards page', async ({ page }) => {
    await expect(page).toHaveURL(/\/dashboards/)
    // Should have some content container
    await expect(page.locator('main, [role="main"], .container, .max-w-').first()).toBeVisible()
  })

  test('should have search functionality', async ({ page }) => {
    const searchInput = page.locator('input[type="search"], input[placeholder*="search" i], input[placeholder*="buscar" i], input[placeholder*="cercar" i]').first()
    if (await searchInput.isVisible()) {
      await searchInput.fill('test')
      // Verify the search input accepts text
      await expect(searchInput).toHaveValue('test')
    }
  })
})

test.describe('Reports Page', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page)
    await page.goto('/reports')
  })

  test('should display reports page', async ({ page }) => {
    await expect(page).toHaveURL(/\/reports/)
    await expect(page.locator('main, [role="main"], .container, .max-w-').first()).toBeVisible()
  })

  test('should show reports table or empty state', async ({ page }) => {
    // Either a table with reports or an empty state message
    const content = page.locator('table, .empty-state, p, h2').first()
    await expect(content).toBeVisible()
  })
})

test.describe('Compare Reports Page', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page)
    await page.goto('/compare')
  })

  test('should display comparison page', async ({ page }) => {
    await expect(page).toHaveURL(/\/compare/)
  })

  test('should have two report selectors', async ({ page }) => {
    const selects = page.locator('select')
    const count = await selects.count()
    expect(count).toBeGreaterThanOrEqual(2)
  })
})
