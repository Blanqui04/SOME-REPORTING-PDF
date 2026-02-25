// @ts-check
import { test, expect } from '@playwright/test'

test.describe('PWA Support', () => {
  test('should have a web app manifest', async ({ page }) => {
    await page.goto('/')
    const manifest = page.locator('link[rel="manifest"]')
    await expect(manifest).toBeAttached()
  })

  test('should have a theme-color meta tag', async ({ page }) => {
    await page.goto('/')
    const themeColor = page.locator('meta[name="theme-color"]')
    await expect(themeColor).toBeAttached()
  })

  test('manifest should be valid JSON', async ({ page, request }) => {
    await page.goto('/')
    const manifestHref = await page.locator('link[rel="manifest"]').getAttribute('href')
    if (manifestHref) {
      const baseURL = page.url().replace(/\/$/, '')
      const manifestURL = manifestHref.startsWith('http')
        ? manifestHref
        : `${baseURL}${manifestHref.startsWith('/') ? '' : '/'}${manifestHref}`

      const response = await request.get(manifestURL)
      expect(response.ok()).toBeTruthy()

      const json = await response.json()
      expect(json).toHaveProperty('name')
      expect(json).toHaveProperty('icons')
      expect(json.icons.length).toBeGreaterThan(0)
    }
  })
})

test.describe('Responsive Design', () => {
  test('should display mobile menu on small screens', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/login')

    // Login page should be usable on mobile
    await expect(page.locator('form')).toBeVisible()
    await expect(page.locator('input[type="text"]')).toBeVisible()
  })
})
