// @ts-check
import { test, expect } from '@playwright/test'

/**
 * Helper: login as admin and return authenticated page.
 */
async function loginAsAdmin(page) {
  await page.goto('/login')
  await page.fill('input[type="text"]', 'admin')
  await page.fill('input[type="password"]', 'admin123')
  await page.click('button[type="submit"]')
  await page.waitForURL(/\/(dashboards|$)/, { timeout: 10000 })
}

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page)
  })

  test('should show main navigation links', async ({ page }) => {
    // Desktop navigation should have key links
    const nav = page.locator('nav, [role="navigation"]').first()
    await expect(nav).toBeVisible()
  })

  test('should navigate to dashboards page', async ({ page }) => {
    await page.goto('/dashboards')
    await expect(page).toHaveURL(/\/dashboards/)
  })

  test('should navigate to reports page', async ({ page }) => {
    await page.goto('/reports')
    await expect(page).toHaveURL(/\/reports/)
  })

  test('should navigate to compare page', async ({ page }) => {
    await page.goto('/compare')
    await expect(page).toHaveURL(/\/compare/)
  })

  test('should redirect unauthenticated users to login', async ({ page }) => {
    // Clear auth state
    await page.evaluate(() => localStorage.removeItem('access_token'))
    await page.goto('/dashboards')

    // Should redirect to login
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 })
  })
})
