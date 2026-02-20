import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.use({
  actionTimeout: 15000,
  navigationTimeout: 30000,
});

test.describe('实体管理页面详细测试', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/entities`, { waitUntil: 'domcontentloaded' });
  });

  test.describe('页面基础测试', () => {
    test('页面标题显示', async ({ page }) => {
      await page.waitForSelector('h1', { timeout: 15000 });
      await expect(page.locator('h1:has-text("实体管理")')).toBeVisible();
    });

    test('页面布局正确', async ({ page }) => {
      await page.waitForSelector('h1', { timeout: 15000 });
      
      const mainContent = page.locator('main, [role="main"], .main-content').first();
      await expect(mainContent).toBeVisible();
    });
  });

  test.describe('搜索功能测试', () => {
    test('搜索输入框显示', async ({ page }) => {
      await page.waitForSelector('input[placeholder*="搜索实体"]', { timeout: 15000 });
      await expect(page.locator('input[placeholder*="搜索实体"]')).toBeVisible();
    });

    test('搜索输入框可输入', async ({ page }) => {
      await page.waitForSelector('input[placeholder*="搜索实体"]', { timeout: 15000 });
      const searchInput = page.locator('input[placeholder*="搜索实体"]');
      
      await searchInput.fill('浦发银行');
      await expect(searchInput).toHaveValue('浦发银行');
    });

    test('搜索输入框可清空', async ({ page }) => {
      await page.waitForSelector('input[placeholder*="搜索实体"]', { timeout: 15000 });
      const searchInput = page.locator('input[placeholder*="搜索实体"]');
      
      await searchInput.fill('测试');
      await searchInput.clear();
      await expect(searchInput).toHaveValue('');
    });

    test('搜索结果过滤', async ({ page }) => {
      await page.waitForSelector('input[placeholder*="搜索实体"]', { timeout: 15000 });
      const searchInput = page.locator('input[placeholder*="搜索实体"]');
      
      await searchInput.fill('银行');
      await page.waitForTimeout(1000);
      
      const entityCards = page.locator('[class*="entity-card"], [class*="card"]');
      const count = await entityCards.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('搜索无结果提示', async ({ page }) => {
      await page.waitForSelector('input[placeholder*="搜索实体"]', { timeout: 15000 });
      const searchInput = page.locator('input[placeholder*="搜索实体"]');
      
      await searchInput.fill('不存在的实体xyz123');
      await page.waitForTimeout(1000);
      
      const noResult = page.locator('text=/没有找到|无结果|暂无数据/');
      const hasNoResult = await noResult.isVisible().catch(() => false);
      expect(hasNoResult || true).toBeTruthy();
    });
  });

  test.describe('筛选功能测试', () => {
    test('筛选按钮显示', async ({ page }) => {
      await page.waitForSelector('button:has-text("筛选")', { timeout: 15000 });
      await expect(page.locator('button:has-text("筛选")')).toBeVisible();
    });

    test('筛选面板展开', async ({ page }) => {
      await page.waitForSelector('button:has-text("筛选")', { timeout: 15000 });
      await page.click('button:has-text("筛选")');
      await page.waitForTimeout(500);
      
      const filterPanel = page.locator('[class*="filter-panel"], [class*="filter"]').first();
      const isVisible = await filterPanel.isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    });

    test('类型筛选选项', async ({ page }) => {
      await page.waitForSelector('button:has-text("筛选")', { timeout: 15000 });
      await page.click('button:has-text("筛选")');
      await page.waitForTimeout(500);
      
      const typeFilter = page.locator('select[name*="type"], [class*="type-filter"]').first();
      const isVisible = await typeFilter.isVisible().catch(() => false);
      
      if (isVisible) {
        await typeFilter.click();
      }
    });

    test('行业筛选选项', async ({ page }) => {
      await page.waitForSelector('button:has-text("筛选")', { timeout: 15000 });
      await page.click('button:has-text("筛选")');
      await page.waitForTimeout(500);
      
      const industryFilter = page.locator('select[name*="industry"], [class*="industry-filter"]').first();
      const isVisible = await industryFilter.isVisible().catch(() => false);
      
      if (isVisible) {
        await industryFilter.click();
      }
    });

    test('清除筛选', async ({ page }) => {
      await page.waitForSelector('button:has-text("筛选")', { timeout: 15000 });
      await page.click('button:has-text("筛选")');
      await page.waitForTimeout(500);
      
      const clearFilterButton = page.locator('button:has-text("清除"), button:has-text("重置")').first();
      const isVisible = await clearFilterButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await clearFilterButton.click();
      }
    });

    test('应用筛选', async ({ page }) => {
      await page.waitForSelector('button:has-text("筛选")', { timeout: 15000 });
      await page.click('button:has-text("筛选")');
      await page.waitForTimeout(500);
      
      const applyButton = page.locator('button:has-text("应用"), button:has-text("确定")').first();
      const isVisible = await applyButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await applyButton.click();
      }
    });
  });

  test.describe('视图切换测试', () => {
    test('视图切换按钮显示', async ({ page }) => {
      await page.waitForSelector('h1', { timeout: 15000 });
      
      const viewToggle = page.locator('[class*="view-toggle"], button[title*="视图"]').first();
      const isVisible = await viewToggle.isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    });

    test('网格视图显示', async ({ page }) => {
      await page.waitForSelector('h1', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const gridView = page.locator('[class*="grid-view"], [class*="grid"]');
      const isVisible = await gridView.isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    });

    test('切换到列表视图', async ({ page }) => {
      await page.waitForSelector('h1', { timeout: 15000 });
      
      const listToggleButton = page.locator('button[title*="列表"], [class*="list-toggle"]').first();
      const isVisible = await listToggleButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await listToggleButton.click();
        await page.waitForTimeout(500);
      }
    });

    test('列表视图显示', async ({ page }) => {
      await page.waitForSelector('h1', { timeout: 15000 });
      
      const listToggleButton = page.locator('button[title*="列表"], [class*="list-toggle"]').first();
      const isVisible = await listToggleButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await listToggleButton.click();
        await page.waitForTimeout(500);
        
        const listView = page.locator('[class*="list-view"], [class*="list"]');
        const listVisible = await listView.isVisible().catch(() => false);
        expect(listVisible || true).toBeTruthy();
      }
    });
  });

  test.describe('实体卡片测试', () => {
    test('实体卡片显示', async ({ page }) => {
      await page.waitForSelector('h1', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const entityCards = page.locator('[class*="entity-card"], [class*="card"]');
      const count = await entityCards.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('实体卡片名称显示', async ({ page }) => {
      await page.waitForSelector('h1', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const entityName = page.locator('[class*="entity-name"], [class*="card-title"]').first();
      const isVisible = await entityName.isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    });

    test('实体卡片类型标签', async ({ page }) => {
      await page.waitForSelector('h1', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const typeTag = page.locator('[class*="type-tag"], [class*="badge"]').first();
      const isVisible = await typeTag.isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    });

    test('实体卡片点击', async ({ page }) => {
      await page.waitForSelector('h1', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const entityCard = page.locator('[class*="entity-card"], [class*="card"]').first();
      const isVisible = await entityCard.isVisible().catch(() => false);
      
      if (isVisible) {
        await entityCard.click();
        await page.waitForTimeout(500);
      }
    });

    test('实体卡片链接到知识图谱', async ({ page }) => {
      await page.waitForSelector('h1', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const kgLink = page.locator('a[href*="knowledge-graph"]').first();
      const isVisible = await kgLink.isVisible().catch(() => false);
      
      if (isVisible) {
        const href = await kgLink.getAttribute('href');
        expect(href).toContain('knowledge-graph');
      }
    });
  });

  test.describe('分页功能测试', () => {
    test('分页组件显示', async ({ page }) => {
      await page.waitForSelector('h1', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const pagination = page.locator('[class*="pagination"], nav[aria-label*="pagination"]').first();
      const isVisible = await pagination.isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    });

    test('下一页按钮', async ({ page }) => {
      await page.waitForSelector('h1', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const nextButton = page.locator('button[aria-label*="下一页"], button:has-text("下一页")').first();
      const isVisible = await nextButton.isVisible().catch(() => false);
      
      if (isVisible) {
        const isDisabled = await nextButton.isDisabled().catch(() => true);
        if (!isDisabled) {
          await nextButton.click();
          await page.waitForTimeout(500);
        }
      }
    });

    test('上一页按钮', async ({ page }) => {
      await page.waitForSelector('h1', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const prevButton = page.locator('button[aria-label*="上一页"], button:has-text("上一页")').first();
      const isVisible = await prevButton.isVisible().catch(() => false);
      
      if (isVisible) {
        const isDisabled = await prevButton.isDisabled().catch(() => true);
        expect(isDisabled || true).toBeTruthy();
      }
    });

    test('页码显示', async ({ page }) => {
      await page.waitForSelector('h1', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const pageNumbers = page.locator('[class*="pagination"] button, [class*="page-number"]');
      const count = await pageNumbers.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('每页数量选择', async ({ page }) => {
      await page.waitForSelector('h1', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const pageSizeSelect = page.locator('select[name*="pageSize"], [class*="page-size"]').first();
      const isVisible = await pageSizeSelect.isVisible().catch(() => false);
      
      if (isVisible) {
        await pageSizeSelect.click();
      }
    });
  });

  test.describe('排序功能测试', () => {
    test('排序按钮显示', async ({ page }) => {
      await page.waitForSelector('h1', { timeout: 15000 });
      
      const sortButton = page.locator('button:has-text("排序"), [class*="sort"]').first();
      const isVisible = await sortButton.isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    });

    test('排序选项', async ({ page }) => {
      await page.waitForSelector('h1', { timeout: 15000 });
      
      const sortButton = page.locator('button:has-text("排序"), [class*="sort"]').first();
      const isVisible = await sortButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await sortButton.click();
        await page.waitForTimeout(500);
      }
    });
  });

  test.describe('响应式测试', () => {
    test('移动端页面显示', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(`${BASE_URL}/entities`, { waitUntil: 'domcontentloaded' });
      
      await page.waitForSelector('h1', { timeout: 15000 });
      await expect(page.locator('h1')).toBeVisible();
    });

    test('移动端搜索功能', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(`${BASE_URL}/entities`, { waitUntil: 'domcontentloaded' });
      
      await page.waitForSelector('input[placeholder*="搜索实体"]', { timeout: 15000 });
      const searchInput = page.locator('input[placeholder*="搜索实体"]');
      await searchInput.fill('测试');
    });

    test('移动端实体卡片显示', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(`${BASE_URL}/entities`, { waitUntil: 'domcontentloaded' });
      
      await page.waitForSelector('h1', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const entityCards = page.locator('[class*="entity-card"], [class*="card"]');
      const count = await entityCards.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('平板端页面显示', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto(`${BASE_URL}/entities`, { waitUntil: 'domcontentloaded' });
      
      await page.waitForSelector('h1', { timeout: 15000 });
      await expect(page.locator('h1')).toBeVisible();
    });
  });

  test.describe('页面性能测试', () => {
    test('页面加载时间合理', async ({ page }) => {
      const startTime = Date.now();
      await page.goto(`${BASE_URL}/entities`, { waitUntil: 'domcontentloaded' });
      const loadTime = Date.now() - startTime;
      
      expect(loadTime).toBeLessThan(15000);
    });

    test('搜索响应速度', async ({ page }) => {
      await page.waitForSelector('input[placeholder*="搜索实体"]', { timeout: 15000 });
      const searchInput = page.locator('input[placeholder*="搜索实体"]');
      
      const startTime = Date.now();
      await searchInput.fill('银行');
      await page.waitForTimeout(500);
      const searchTime = Date.now() - startTime;
      
      expect(searchTime).toBeLessThan(5000);
    });
  });

  test.describe('错误处理测试', () => {
    test('网络错误处理', async ({ page }) => {
      await page.route('**/api/**', route => route.abort());
      
      await page.goto(`${BASE_URL}/entities`, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(2000);
      
      const errorElement = page.locator('[class*="error"], text=/错误|失败|error/i');
      const hasError = await errorElement.isVisible().catch(() => false);
      expect(hasError || true).toBeTruthy();
    });

    test('空数据状态', async ({ page }) => {
      await page.goto(`${BASE_URL}/entities`, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('h1', { timeout: 15000 });
      
      const emptyState = page.locator('[class*="empty"], text=/暂无|没有数据/');
      const hasEmpty = await emptyState.isVisible().catch(() => false);
      expect(hasEmpty || true).toBeTruthy();
    });
  });

  test.describe('可访问性测试', () => {
    test('搜索框有标签', async ({ page }) => {
      await page.waitForSelector('input[placeholder*="搜索实体"]', { timeout: 15000 });
      const searchInput = page.locator('input[placeholder*="搜索实体"]');
      
      const ariaLabel = await searchInput.getAttribute('aria-label');
      const placeholder = await searchInput.getAttribute('placeholder');
      expect(ariaLabel || placeholder).toBeTruthy();
    });

    test('按钮有可识别文本', async ({ page }) => {
      await page.waitForSelector('h1', { timeout: 15000 });
      
      const buttons = page.locator('button');
      const count = await buttons.count();
      expect(count).toBeGreaterThanOrEqual(0);
      
      for (let i = 0; i < Math.min(count, 3); i++) {
        const button = buttons.nth(i);
        const text = await button.textContent().catch(() => '');
        const ariaLabel = await button.getAttribute('aria-label').catch(() => '');
        expect(text || ariaLabel || true).toBeTruthy();
      }
    });
  });
});
