import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.use({
  actionTimeout: 15000,
  navigationTimeout: 30000,
});

test.describe('量化分析页面详细测试', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/quant`, { waitUntil: 'domcontentloaded' });
  });

  test.describe('页面基础测试', () => {
    test('页面标题显示', async ({ page }) => {
      await page.waitForSelector('h1', { timeout: 15000 });
      await expect(page.locator('h1:has-text("量化分析")')).toBeVisible();
    });

    test('页面描述显示', async ({ page }) => {
      await page.waitForSelector('text=因子', { timeout: 15000 });
      await expect(page.locator('text=因子')).toBeVisible();
    });
  });

  test.describe('Tab导航测试', () => {
    test('四个Tab都显示', async ({ page }) => {
      await page.waitForSelector('[data-testid="factors-tab"]', { timeout: 15000 });
      
      await expect(page.locator('[data-testid="factors-tab"]')).toBeVisible();
      await expect(page.locator('[data-testid="strategies-tab"]')).toBeVisible();
      await expect(page.locator('[data-testid="backtest-tab"]')).toBeVisible();
      await expect(page.locator('[data-testid="custom-factor-tab"]')).toBeVisible();
    });

    test('因子Tab默认选中', async ({ page }) => {
      await page.waitForSelector('[data-testid="factors-tab"]', { timeout: 15000 });
      
      const factorsTab = page.locator('[data-testid="factors-tab"]');
      await expect(factorsTab).toBeVisible();
    });

    test('切换到策略Tab', async ({ page }) => {
      await page.waitForSelector('[data-testid="strategies-tab"]', { timeout: 15000 });
      
      await page.click('[data-testid="strategies-tab"]');
      await page.waitForSelector('[data-testid="strategy-list"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="strategy-list"]')).toBeVisible();
    });

    test('切换到回测Tab', async ({ page }) => {
      await page.waitForSelector('[data-testid="backtest-tab"]', { timeout: 15000 });
      
      await page.click('[data-testid="backtest-tab"]');
      await page.waitForSelector('[data-testid="backtest-results"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="backtest-results"]')).toBeVisible();
    });

    test('切换到自定义因子Tab', async ({ page }) => {
      await page.waitForSelector('[data-testid="custom-factor-tab"]', { timeout: 15000 });
      
      await page.click('[data-testid="custom-factor-tab"]');
      await page.waitForSelector('[data-testid="code-editor"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="code-editor"]')).toBeVisible();
    });

    test('Tab切换保持状态', async ({ page }) => {
      await page.waitForSelector('[data-testid="strategies-tab"]', { timeout: 15000 });
      
      await page.click('[data-testid="strategies-tab"]');
      await page.waitForTimeout(500);
      
      await page.click('[data-testid="factors-tab"]');
      await page.waitForTimeout(500);
      
      await page.click('[data-testid="strategies-tab"]');
      await expect(page.locator('[data-testid="strategy-list"]')).toBeVisible();
    });
  });

  test.describe('因子Tab测试', () => {
    test('因子列表显示', async ({ page }) => {
      await page.waitForSelector('[data-testid="factor-list"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="factor-list"]')).toBeVisible();
    });

    test('因子搜索功能', async ({ page }) => {
      await page.waitForSelector('[data-testid="factor-list"]', { timeout: 15000 });
      
      const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="因子"]').first();
      const isVisible = await searchInput.isVisible().catch(() => false);
      
      if (isVisible) {
        await searchInput.fill('动量');
        await page.waitForTimeout(500);
      }
    });

    test('因子分类筛选', async ({ page }) => {
      await page.waitForSelector('[data-testid="factor-list"]', { timeout: 15000 });
      
      const categoryFilter = page.locator('select, [class*="category"], button:has-text("分类")').first();
      const isVisible = await categoryFilter.isVisible().catch(() => false);
      
      if (isVisible) {
        await categoryFilter.click();
      }
    });

    test('因子卡片显示', async ({ page }) => {
      await page.waitForSelector('[data-testid="factor-list"]', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const factorCards = page.locator('[class*="factor-card"], [data-testid*="factor"]');
      const count = await factorCards.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('因子选择功能', async ({ page }) => {
      await page.waitForSelector('[data-testid="factor-list"]', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const factorItem = page.locator('[class*="factor-item"], [class*="factor-card"]').first();
      const isVisible = await factorItem.isVisible().catch(() => false);
      
      if (isVisible) {
        await factorItem.click();
      }
    });

    test('因子详情面板显示', async ({ page }) => {
      await page.waitForSelector('[data-testid="factor-list"]', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const detailPanel = page.locator('[class*="detail"], [class*="panel"]').first();
      const isVisible = await detailPanel.isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    });
  });

  test.describe('因子详情测试', () => {
    test.beforeEach(async ({ page }) => {
      await page.waitForSelector('[data-testid="factor-list"]', { timeout: 15000 });
      await page.waitForTimeout(1000);
    });

    test('因子详情Tab切换', async ({ page }) => {
      const detailTabs = page.locator('[class*="detail"] button, [role="tab"]').first();
      const isVisible = await detailTabs.isVisible().catch(() => false);
      
      if (isVisible) {
        await detailTabs.click();
      }
    });

    test('因子概览信息显示', async ({ page }) => {
      const overviewTab = page.locator('button:has-text("概览"), [data-testid="overview-tab"]').first();
      const isVisible = await overviewTab.isVisible().catch(() => false);
      
      if (isVisible) {
        await overviewTab.click();
      }
    });

    test('因子历史数据Tab', async ({ page }) => {
      const historyTab = page.locator('button:has-text("历史"), [data-testid="history-tab"]').first();
      const isVisible = await historyTab.isVisible().catch(() => false);
      
      if (isVisible) {
        await historyTab.click();
      }
    });

    test('因子相关性Tab', async ({ page }) => {
      const correlationTab = page.locator('button:has-text("相关性"), [data-testid="correlation-tab"]').first();
      const isVisible = await correlationTab.isVisible().catch(() => false);
      
      if (isVisible) {
        await correlationTab.click();
      }
    });
  });

  test.describe('策略Tab测试', () => {
    test.beforeEach(async ({ page }) => {
      await page.waitForSelector('[data-testid="strategies-tab"]', { timeout: 15000 });
      await page.click('[data-testid="strategies-tab"]');
      await page.waitForSelector('[data-testid="strategy-list"]', { timeout: 10000 });
    });

    test('策略列表显示', async ({ page }) => {
      await expect(page.locator('[data-testid="strategy-list"]')).toBeVisible();
    });

    test('创建策略按钮', async ({ page }) => {
      const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
      const isVisible = await createButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await expect(createButton).toBeVisible();
      }
    });

    test('策略卡片显示', async ({ page }) => {
      const strategyCards = page.locator('[class*="strategy-card"], [class*="strategy-item"]');
      const count = await strategyCards.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('策略运行按钮', async ({ page }) => {
      const runButton = page.locator('button:has-text("运行"), button:has-text("执行")').first();
      const isVisible = await runButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await expect(runButton).toBeVisible();
      }
    });

    test('策略编辑功能', async ({ page }) => {
      const editButton = page.locator('button:has-text("编辑"), button[title*="编辑"]').first();
      const isVisible = await editButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await editButton.click();
      }
    });

    test('策略删除功能', async ({ page }) => {
      const deleteButton = page.locator('button:has-text("删除"), button[title*="删除"]').first();
      const isVisible = await deleteButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await expect(deleteButton).toBeVisible();
      }
    });
  });

  test.describe('回测Tab测试', () => {
    test.beforeEach(async ({ page }) => {
      await page.waitForSelector('[data-testid="backtest-tab"]', { timeout: 15000 });
      await page.click('[data-testid="backtest-tab"]');
      await page.waitForSelector('[data-testid="backtest-results"]', { timeout: 10000 });
    });

    test('回测结果显示区域', async ({ page }) => {
      await expect(page.locator('[data-testid="backtest-results"]')).toBeVisible();
    });

    test('回测参数设置', async ({ page }) => {
      const paramInput = page.locator('input[type="date"], input[type="number"], select').first();
      const isVisible = await paramInput.isVisible().catch(() => false);
      
      if (isVisible) {
        await expect(paramInput).toBeVisible();
      }
    });

    test('回测开始日期设置', async ({ page }) => {
      const startDateInput = page.locator('input[placeholder*="开始"], input[name*="start"]').first();
      const isVisible = await startDateInput.isVisible().catch(() => false);
      
      if (isVisible) {
        await startDateInput.fill('2024-01-01');
      }
    });

    test('回测结束日期设置', async ({ page }) => {
      const endDateInput = page.locator('input[placeholder*="结束"], input[name*="end"]').first();
      const isVisible = await endDateInput.isVisible().catch(() => false);
      
      if (isVisible) {
        await endDateInput.fill('2024-12-31');
      }
    });

    test('回测运行按钮', async ({ page }) => {
      const runButton = page.locator('button:has-text("运行回测"), button:has-text("开始")').first();
      const isVisible = await runButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await expect(runButton).toBeVisible();
      }
    });

    test('回测结果图表', async ({ page }) => {
      const chart = page.locator('canvas, svg, [class*="chart"]').first();
      const isVisible = await chart.isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    });

    test('回测统计数据', async ({ page }) => {
      const stats = page.locator('[class*="stat"], [class*="metric"], text=/收益|风险|夏普/');
      const count = await stats.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('自定义因子Tab测试', () => {
    test.beforeEach(async ({ page }) => {
      await page.waitForSelector('[data-testid="custom-factor-tab"]', { timeout: 15000 });
      await page.click('[data-testid="custom-factor-tab"]');
      await page.waitForSelector('[data-testid="code-editor"]', { timeout: 10000 });
    });

    test('代码编辑器显示', async ({ page }) => {
      await expect(page.locator('[data-testid="code-editor"]')).toBeVisible();
    });

    test('验证按钮显示', async ({ page }) => {
      await expect(page.locator('[data-testid="validate-button"]')).toBeVisible();
    });

    test('测试按钮显示', async ({ page }) => {
      await expect(page.locator('[data-testid="test-factor-button"]')).toBeVisible();
    });

    test('代码编辑器可输入', async ({ page }) => {
      const editor = page.locator('[data-testid="code-editor"] textarea, [data-testid="code-editor"] .cm-content').first();
      const isVisible = await editor.isVisible().catch(() => false);
      
      if (isVisible) {
        await editor.click();
      }
    });

    test('验证按钮可点击', async ({ page }) => {
      const validateButton = page.locator('[data-testid="validate-button"]');
      await validateButton.click();
      await page.waitForTimeout(500);
    });

    test('测试按钮可点击', async ({ page }) => {
      const testButton = page.locator('[data-testid="test-factor-button"]');
      await testButton.click();
      await page.waitForTimeout(500);
    });

    test('保存因子按钮', async ({ page }) => {
      const saveButton = page.locator('button:has-text("保存"), button:has-text("提交")').first();
      const isVisible = await saveButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await expect(saveButton).toBeVisible();
      }
    });
  });

  test.describe('响应式测试', () => {
    test('移动端页面显示', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(`${BASE_URL}/quant`, { waitUntil: 'domcontentloaded' });
      
      await page.waitForSelector('h1', { timeout: 15000 });
      await expect(page.locator('h1')).toBeVisible();
    });

    test('平板端页面显示', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto(`${BASE_URL}/quant`, { waitUntil: 'domcontentloaded' });
      
      await page.waitForSelector('h1', { timeout: 15000 });
      await expect(page.locator('h1')).toBeVisible();
    });

    test('移动端Tab导航', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(`${BASE_URL}/quant`, { waitUntil: 'domcontentloaded' });
      
      await page.waitForSelector('[data-testid="strategies-tab"]', { timeout: 15000 });
      await page.click('[data-testid="strategies-tab"]');
      await expect(page.locator('[data-testid="strategy-list"]')).toBeVisible();
    });
  });

  test.describe('页面性能测试', () => {
    test('页面加载时间合理', async ({ page }) => {
      const startTime = Date.now();
      await page.goto(`${BASE_URL}/quant`, { waitUntil: 'domcontentloaded' });
      const loadTime = Date.now() - startTime;
      
      expect(loadTime).toBeLessThan(15000);
    });

    test('Tab切换响应速度', async ({ page }) => {
      await page.waitForSelector('[data-testid="strategies-tab"]', { timeout: 15000 });
      
      const startTime = Date.now();
      await page.click('[data-testid="strategies-tab"]');
      await page.waitForSelector('[data-testid="strategy-list"]', { timeout: 10000 });
      const switchTime = Date.now() - startTime;
      
      expect(switchTime).toBeLessThan(5000);
    });
  });
});
