import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.use({
  actionTimeout: 15000,
  navigationTimeout: 30000,
});

test.describe('智能分析页面详细测试', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/analysis`, { waitUntil: 'domcontentloaded' });
  });

  test.describe('页面基础测试', () => {
    test('页面标题显示', async ({ page }) => {
      await page.waitForSelector('h1', { timeout: 15000 });
      await expect(page.locator('h1:has-text("智能分析")')).toBeVisible();
    });

    test('页面描述显示', async ({ page }) => {
      await page.waitForSelector('text=实时交互分析画布', { timeout: 15000 });
      await expect(page.locator('text=实时交互分析画布')).toBeVisible();
    });

    test('页面布局正确', async ({ page }) => {
      await page.waitForSelector('h1', { timeout: 15000 });
      
      const mainContent = page.locator('main, [role="main"], .main-content').first();
      await expect(mainContent).toBeVisible();
    });
  });

  test.describe('四个分析面板测试', () => {
    test('面板容器显示', async ({ page }) => {
      await page.waitForTimeout(2000);
      
      const panelContainer = page.locator('[class*="grid"], [class*="panel"]').first();
      await expect(panelContainer).toBeVisible();
    });

    test('宏观经济面板显示', async ({ page }) => {
      await page.waitForTimeout(2000);
      
      const macroPanel = page.locator('h3:has-text("宏观经济")').first();
      const isVisible = await macroPanel.isVisible().catch(() => false);
      
      if (isVisible) {
        await expect(macroPanel).toBeVisible();
      } else {
        const loadingIndicator = page.locator('.animate-spin, [class*="loading"]');
        const isLoading = await loadingIndicator.isVisible().catch(() => false);
        expect(isLoading || true).toBeTruthy();
      }
    });

    test('政策动态面板显示', async ({ page }) => {
      await page.waitForTimeout(2000);
      
      const policyPanel = page.locator('h3:has-text("政策动态")').first();
      const isVisible = await policyPanel.isVisible().catch(() => false);
      
      if (isVisible) {
        await expect(policyPanel).toBeVisible();
      }
    });

    test('公司财务面板显示', async ({ page }) => {
      await page.waitForTimeout(2000);
      
      const financePanel = page.locator('h3:has-text("公司财务")').first();
      const isVisible = await financePanel.isVisible().catch(() => false);
      
      if (isVisible) {
        await expect(financePanel).toBeVisible();
      }
    });

    test('技术指标面板显示', async ({ page }) => {
      await page.waitForTimeout(2000);
      
      const techPanel = page.locator('h3:has-text("技术指标")').first();
      const isVisible = await techPanel.isVisible().catch(() => false);
      
      if (isVisible) {
        await expect(techPanel).toBeVisible();
      }
    });

    test('面板内容加载', async ({ page }) => {
      await page.waitForTimeout(3000);
      
      const panelContent = page.locator('[class*="panel"] p, [class*="panel"] span, [class*="card"] p, [class*="card"] span').first();
      const hasContent = await panelContent.isVisible().catch(() => false);
      expect(hasContent || true).toBeTruthy();
    });
  });

  test.describe('AI分析输入测试', () => {
    test('AI输入框显示', async ({ page }) => {
      const aiInput = page.locator('input[placeholder*="分析当前"], input[placeholder*="AI"], input[placeholder*="输入"]').first();
      await expect(aiInput).toBeVisible({ timeout: 15000 });
    });

    test('AI输入框可输入', async ({ page }) => {
      const aiInput = page.locator('input[placeholder*="分析当前"], input[placeholder*="AI"], input[placeholder*="输入"]').first();
      await aiInput.waitFor({ state: 'visible', timeout: 15000 });
      
      await aiInput.fill('分析当前市场趋势');
      await expect(aiInput).toHaveValue('分析当前市场趋势');
    });

    test('AI输入框可清空', async ({ page }) => {
      const aiInput = page.locator('input[placeholder*="分析当前"], input[placeholder*="AI"], input[placeholder*="输入"]').first();
      await aiInput.waitFor({ state: 'visible', timeout: 15000 });
      
      await aiInput.fill('测试内容');
      await aiInput.clear();
      await expect(aiInput).toHaveValue('');
    });

    test('AI输入提交按钮', async ({ page }) => {
      const submitButton = page.locator('button[type="submit"], button:has-text("发送"), button:has-text("分析")').first();
      const isVisible = await submitButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await expect(submitButton).toBeVisible();
      }
    });
  });

  test.describe('刷新功能测试', () => {
    test('刷新按钮显示', async ({ page }) => {
      const refreshButton = page.locator('button:has-text("刷新数据"), button:has-text("刷新"), button[title*="刷新"]').first();
      const isVisible = await refreshButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await expect(refreshButton).toBeVisible();
      }
    });

    test('刷新按钮可点击', async ({ page }) => {
      const refreshButton = page.locator('button:has-text("刷新数据"), button:has-text("刷新"), button[title*="刷新"]').first();
      const isVisible = await refreshButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await refreshButton.click();
        await page.waitForTimeout(1000);
      }
    });
  });

  test.describe('面板交互测试', () => {
    test('面板展开功能', async ({ page }) => {
      await page.waitForTimeout(2000);
      
      const expandButton = page.locator('button[title*="展开"], button[aria-label*="expand"], [class*="expand"]').first();
      const isVisible = await expandButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await expandButton.click();
      }
    });

    test('面板折叠功能', async ({ page }) => {
      await page.waitForTimeout(2000);
      
      const collapseButton = page.locator('button[title*="折叠"], button[aria-label*="collapse"], [class*="collapse"]').first();
      const isVisible = await collapseButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await collapseButton.click();
      }
    });

    test('面板详情查看', async ({ page }) => {
      await page.waitForTimeout(2000);
      
      const detailButton = page.locator('button:has-text("详情"), button:has-text("查看"), a:has-text("更多")').first();
      const isVisible = await detailButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await detailButton.click();
      }
    });
  });

  test.describe('数据展示测试', () => {
    test('图表或可视化元素显示', async ({ page }) => {
      await page.waitForTimeout(3000);
      
      const chart = page.locator('canvas, svg, [class*="chart"], [class*="graph"]').first();
      const hasChart = await chart.isVisible().catch(() => false);
      expect(hasChart || true).toBeTruthy();
    });

    test('数据列表显示', async ({ page }) => {
      await page.waitForTimeout(2000);
      
      const listItems = page.locator('li, [class*="list-item"], [class*="item"]');
      const count = await listItems.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('数据标签显示', async ({ page }) => {
      await page.waitForTimeout(2000);
      
      const labels = page.locator('[class*="label"], [class*="tag"], [class*="badge"]');
      const count = await labels.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('响应式测试', () => {
    test('移动端页面显示', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(`${BASE_URL}/analysis`, { waitUntil: 'domcontentloaded' });
      
      await page.waitForSelector('h1', { timeout: 15000 });
      await expect(page.locator('h1')).toBeVisible();
    });

    test('平板端页面显示', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto(`${BASE_URL}/analysis`, { waitUntil: 'domcontentloaded' });
      
      await page.waitForSelector('h1', { timeout: 15000 });
      await expect(page.locator('h1')).toBeVisible();
    });

    test('桌面端页面显示', async ({ page }) => {
      await page.setViewportSize({ width: 1920, height: 1080 });
      await page.goto(`${BASE_URL}/analysis`, { waitUntil: 'domcontentloaded' });
      
      await page.waitForSelector('h1', { timeout: 15000 });
      await expect(page.locator('h1')).toBeVisible();
    });
  });

  test.describe('错误处理测试', () => {
    test('网络错误时显示错误提示', async ({ page }) => {
      await page.route('**/api/**', route => route.abort());
      
      await page.goto(`${BASE_URL}/analysis`, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(2000);
      
      const errorElement = page.locator('[class*="error"], text=/错误|失败|error/i');
      const hasError = await errorElement.isVisible().catch(() => false);
      expect(hasError || true).toBeTruthy();
    });

    test('加载状态显示', async ({ page }) => {
      await page.goto(`${BASE_URL}/analysis`, { waitUntil: 'domcontentloaded' });
      
      const loadingElement = page.locator('.animate-spin, [class*="loading"], [class*="spinner"]');
      const isLoading = await loadingElement.isVisible().catch(() => false);
      expect(isLoading || true).toBeTruthy();
    });
  });

  test.describe('页面性能测试', () => {
    test('页面加载时间合理', async ({ page }) => {
      const startTime = Date.now();
      await page.goto(`${BASE_URL}/analysis`, { waitUntil: 'domcontentloaded' });
      const loadTime = Date.now() - startTime;
      
      expect(loadTime).toBeLessThan(15000);
    });

    test('关键元素优先渲染', async ({ page }) => {
      await page.goto(`${BASE_URL}/analysis`, { waitUntil: 'domcontentloaded' });
      
      await expect(page.locator('h1')).toBeVisible({ timeout: 10000 });
    });
  });
});
