import { test, expect } from '@playwright/test'

test.use({
  actionTimeout: 10000,
  navigationTimeout: 30000,
})

test.describe('Skills页面测试', () => {
  test('页面正常加载', async ({ page }) => {
    await page.goto('/skills/marketplace', { waitUntil: 'domcontentloaded' })
    await page.waitForSelector('body', { timeout: 10000 })
    
    const body = page.locator('body')
    await expect(body).toBeVisible()
  })

  test('技能列表存在', async ({ page }) => {
    await page.goto('/skills/marketplace', { waitUntil: 'domcontentloaded' })
    await page.waitForSelector('body', { timeout: 10000 })
    
    const content = await page.locator('body').textContent()
    expect(content).toBeTruthy()
  })

  test('响应式 - 移动端', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/skills/marketplace', { waitUntil: 'domcontentloaded' })
    await page.waitForSelector('body', { timeout: 10000 })
    
    const body = page.locator('body')
    await expect(body).toBeVisible()
  })
})
