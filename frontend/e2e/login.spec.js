// @ts-check
import { test, expect } from '@playwright/test'

test.describe('Login Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
  })

  test('should display login form', async ({ page }) => {
    await expect(page.locator('form')).toBeVisible()
    await expect(page.locator('input[type="text"]')).toBeVisible()
    await expect(page.locator('input[type="password"]')).toBeVisible()
    await expect(page.locator('button[type="submit"]')).toBeVisible()
  })

  test('should show error on invalid credentials', async ({ page }) => {
    await page.fill('input[type="text"]', 'wronguser')
    await page.fill('input[type="password"]', 'wrongpassword')
    await page.click('button[type="submit"]')

    // Should remain on login page and show an error message
    await expect(page.locator('.bg-red-50, .bg-red-900\\/30')).toBeVisible({
      timeout: 10000,
    })
  })

  test('should redirect to dashboards on successful login', async ({ page }) => {
    await page.fill('input[type="text"]', 'admin')
    await page.fill('input[type="password"]', 'admin123')
    await page.click('button[type="submit"]')

    // On success we should navigate away from /login
    await expect(page).not.toHaveURL(/\/login/, { timeout: 10000 })
  })

  test('should have a language selector', async ({ page }) => {
    // The language selector component should exist
    const langSelector = page.locator('[data-testid="language-selector"], select, .language-selector').first()
    await expect(langSelector).toBeVisible()
  })
})
