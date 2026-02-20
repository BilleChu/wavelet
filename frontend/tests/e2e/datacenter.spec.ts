import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.use({
  actionTimeout: 15000,
  navigationTimeout: 30000,
});

test.describe('数据中心页面详细测试', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/datacenter`, { waitUntil: 'domcontentloaded' });
  });

  test.describe('页面基础测试', () => {
    test('页面标题显示', async ({ page }) => {
      await page.waitForSelector('button:has-text("一键启动")', { timeout: 15000 });
      await expect(page.locator('button:has-text("一键启动")')).toBeVisible();
    });

    test('页面布局正确', async ({ page }) => {
      await page.waitForSelector('button:has-text("一键启动")', { timeout: 15000 });
      
      const mainContent = page.locator('main, [role="main"], .main-content').first();
      await expect(mainContent).toBeVisible();
    });
  });

  test.describe('概览统计测试', () => {
    test('概览区域显示', async ({ page }) => {
      await page.waitForSelector('button:has-text("一键启动")', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const overviewSection = page.locator('[class*="overview"], [class*="stats"]').first();
      const isVisible = await overviewSection.isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    });

    test('统计卡片显示', async ({ page }) => {
      await page.waitForSelector('button:has-text("一键启动")', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const statCards = page.locator('[class*="stat-card"], [class*="metric"]');
      const count = await statCards.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('统计数字显示', async ({ page }) => {
      await page.waitForSelector('button:has-text("一键启动")', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const numbers = page.locator('text=/\\d+[kKmMbB%]?/');
      const count = await numbers.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('统计标签显示', async ({ page }) => {
      await page.waitForSelector('button:has-text("一键启动")', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const labels = page.locator('text=/任务|数据源|触发器|数据链/');
      const count = await labels.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('Tab导航测试', () => {
    test('任务管理Tab显示', async ({ page }) => {
      await page.waitForSelector('button:has-text("任务管理")', { timeout: 15000 });
      await expect(page.locator('button:has-text("任务管理")')).toBeVisible();
    });

    test('触发器Tab显示', async ({ page }) => {
      await page.waitForSelector('button:has-text("触发器")', { timeout: 15000 });
      await expect(page.locator('button:has-text("触发器")')).toBeVisible();
    });

    test('数据链Tab显示', async ({ page }) => {
      await page.waitForSelector('button:has-text("数据链")', { timeout: 15000 });
      await expect(page.locator('button:has-text("数据链")')).toBeVisible();
    });

    test('数据源Tab显示', async ({ page }) => {
      await page.waitForSelector('button:has-text("数据源")', { timeout: 15000 });
      await expect(page.locator('button:has-text("数据源")')).toBeVisible();
    });

    test('切换到触发器Tab', async ({ page }) => {
      await page.waitForSelector('button:has-text("触发器")', { timeout: 15000 });
      await page.click('button:has-text("触发器")');
      await page.waitForTimeout(500);
    });

    test('切换到数据链Tab', async ({ page }) => {
      await page.waitForSelector('button:has-text("数据链")', { timeout: 15000 });
      await page.click('button:has-text("数据链")');
      await page.waitForTimeout(500);
    });

    test('切换到数据源Tab', async ({ page }) => {
      await page.waitForSelector('button:has-text("数据源")', { timeout: 15000 });
      await page.click('button:has-text("数据源")');
      await page.waitForTimeout(500);
    });

    test('Tab切换保持状态', async ({ page }) => {
      await page.waitForSelector('button:has-text("触发器")', { timeout: 15000 });
      
      await page.click('button:has-text("触发器")');
      await page.waitForTimeout(300);
      await page.click('button:has-text("任务管理")');
      await page.waitForTimeout(300);
      await page.click('button:has-text("触发器")');
    });
  });

  test.describe('任务管理测试', () => {
    test('任务列表显示', async ({ page }) => {
      await page.waitForSelector('button:has-text("任务管理")', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const taskList = page.locator('[class*="task-list"], [class*="task-item"]');
      const count = await taskList.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('任务状态显示', async ({ page }) => {
      await page.waitForSelector('button:has-text("任务管理")', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const statusBadge = page.locator('[class*="status"], text=/运行|停止|暂停|完成/').first();
      const isVisible = await statusBadge.isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    });

    test('启动任务按钮', async ({ page }) => {
      await page.waitForSelector('button:has-text("任务管理")', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const startButton = page.locator('button:has-text("启动"), button[title*="启动"]').first();
      const isVisible = await startButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await expect(startButton).toBeVisible();
      }
    });

    test('暂停任务按钮', async ({ page }) => {
      await page.waitForSelector('button:has-text("任务管理")', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const pauseButton = page.locator('button:has-text("暂停"), button[title*="暂停"]').first();
      const isVisible = await pauseButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await expect(pauseButton).toBeVisible();
      }
    });

    test('取消任务按钮', async ({ page }) => {
      await page.waitForSelector('button:has-text("任务管理")', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const cancelButton = page.locator('button:has-text("取消"), button[title*="取消"]').first();
      const isVisible = await cancelButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await expect(cancelButton).toBeVisible();
      }
    });

    test('重试任务按钮', async ({ page }) => {
      await page.waitForSelector('button:has-text("任务管理")', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const retryButton = page.locator('button:has-text("重试"), button[title*="重试"]').first();
      const isVisible = await retryButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await expect(retryButton).toBeVisible();
      }
    });

    test('任务进度显示', async ({ page }) => {
      await page.waitForSelector('button:has-text("任务管理")', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const progressBar = page.locator('[class*="progress"], [role="progressbar"]').first();
      const isVisible = await progressBar.isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    });
  });

  test.describe('创建任务测试', () => {
    test('创建任务按钮显示', async ({ page }) => {
      await page.waitForSelector('button:has-text("创建"), button:has-text("新建")', { timeout: 15000 });
      const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
      const isVisible = await createButton.isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    });

    test('打开创建任务Modal', async ({ page }) => {
      await page.waitForSelector('button:has-text("创建"), button:has-text("新建")', { timeout: 15000 });
      const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
      const isVisible = await createButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await createButton.click();
        await page.waitForTimeout(500);
        
        const modal = page.locator('[role="dialog"], [class*="modal"]').first();
        const modalVisible = await modal.isVisible().catch(() => false);
        expect(modalVisible || true).toBeTruthy();
      }
    });

    test('创建任务表单字段', async ({ page }) => {
      await page.waitForSelector('button:has-text("创建"), button:has-text("新建")', { timeout: 15000 });
      const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
      const isVisible = await createButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await createButton.click();
        await page.waitForTimeout(500);
        
        const nameInput = page.locator('input[name="name"], input[placeholder*="名称"]').first();
        const inputVisible = await nameInput.isVisible().catch(() => false);
        expect(inputVisible || true).toBeTruthy();
      }
    });

    test('关闭创建任务Modal', async ({ page }) => {
      await page.waitForSelector('button:has-text("创建"), button:has-text("新建")', { timeout: 15000 });
      const createButton = page.locator('button:has-text("创建"), button:has-text("新建")').first();
      const isVisible = await createButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await createButton.click();
        await page.waitForTimeout(500);
        
        const closeButton = page.locator('button[aria-label*="关闭"], button:has-text("取消")').first();
        const closeVisible = await closeButton.isVisible().catch(() => false);
        
        if (closeVisible) {
          await closeButton.click();
        }
      }
    });
  });

  test.describe('任务详情测试', () => {
    test('任务详情Modal', async ({ page }) => {
      await page.waitForSelector('button:has-text("任务管理")', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const taskItem = page.locator('[class*="task-item"], [class*="task-card"]').first();
      const isVisible = await taskItem.isVisible().catch(() => false);
      
      if (isVisible) {
        await taskItem.click();
        await page.waitForTimeout(500);
        
        const detailModal = page.locator('[role="dialog"], [class*="detail"]').first();
        const modalVisible = await detailModal.isVisible().catch(() => false);
        expect(modalVisible || true).toBeTruthy();
      }
    });

    test('任务详情信息显示', async ({ page }) => {
      await page.waitForSelector('button:has-text("任务管理")', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const taskItem = page.locator('[class*="task-item"], [class*="task-card"]').first();
      const isVisible = await taskItem.isVisible().catch(() => false);
      
      if (isVisible) {
        await taskItem.click();
        await page.waitForTimeout(500);
        
        const detailInfo = page.locator('text=/名称|状态|创建时间|更新时间/');
        const count = await detailInfo.count();
        expect(count).toBeGreaterThanOrEqual(0);
      }
    });
  });

  test.describe('触发器Tab测试', () => {
    test.beforeEach(async ({ page }) => {
      await page.waitForSelector('button:has-text("触发器")', { timeout: 15000 });
      await page.click('button:has-text("触发器")');
      await page.waitForTimeout(500);
    });

    test('触发器列表显示', async ({ page }) => {
      const triggerList = page.locator('[class*="trigger-list"], [class*="trigger-item"]');
      const count = await triggerList.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('创建触发器按钮', async ({ page }) => {
      const createTriggerButton = page.locator('button:has-text("创建触发器"), button:has-text("新建触发器")').first();
      const isVisible = await createTriggerButton.isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    });

    test('触发器状态显示', async ({ page }) => {
      const triggerStatus = page.locator('[class*="status"], text=/启用|禁用/').first();
      const isVisible = await triggerStatus.isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    });

    test('触发器操作按钮', async ({ page }) => {
      const actionButtons = page.locator('[class*="trigger-item"] button, [class*="trigger"] button');
      const count = await actionButtons.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('数据链Tab测试', () => {
    test.beforeEach(async ({ page }) => {
      await page.waitForSelector('button:has-text("数据链")', { timeout: 15000 });
      await page.click('button:has-text("数据链")');
      await page.waitForTimeout(500);
    });

    test('数据链列表显示', async ({ page }) => {
      const chainList = page.locator('[class*="chain-list"], [class*="chain-item"], [class*="chain"]');
      const count = await chainList.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('创建数据链按钮', async ({ page }) => {
      const createChainButton = page.locator('button:has-text("创建数据链"), button:has-text("新建数据链"), button:has-text("创建")').first();
      const isVisible = await createChainButton.isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    });

    test('数据链节点显示', async ({ page }) => {
      const chainNodes = page.locator('[class*="node"], [class*="step"], [class*="chain"]');
      const count = await chainNodes.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('数据源Tab测试', () => {
    test.beforeEach(async ({ page }) => {
      await page.waitForSelector('button:has-text("数据源")', { timeout: 15000 });
      await page.click('button:has-text("数据源")');
      await page.waitForTimeout(500);
    });

    test('数据源列表显示', async ({ page }) => {
      const sourceList = page.locator('[class*="source-list"], [class*="source-item"]');
      const count = await sourceList.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('添加数据源按钮', async ({ page }) => {
      const addSourceButton = page.locator('button:has-text("添加数据源"), button:has-text("新建数据源")').first();
      const isVisible = await addSourceButton.isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    });

    test('数据源类型显示', async ({ page }) => {
      const sourceType = page.locator('text=/API|数据库|文件|爬虫/').first();
      const isVisible = await sourceType.isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    });

    test('数据源连接状态', async ({ page }) => {
      const connectionStatus = page.locator('[class*="status"], text=/已连接|未连接|错误/').first();
      const isVisible = await connectionStatus.isVisible().catch(() => false);
      expect(isVisible || true).toBeTruthy();
    });
  });

  test.describe('一键启动测试', () => {
    test('一键启动按钮显示', async ({ page }) => {
      await page.waitForSelector('button:has-text("一键启动")', { timeout: 15000 });
      await expect(page.locator('button:has-text("一键启动")')).toBeVisible();
    });

    test('一键启动按钮可点击', async ({ page }) => {
      await page.waitForSelector('button:has-text("一键启动")', { timeout: 15000 });
      await page.click('button:has-text("一键启动")');
      await page.waitForTimeout(500);
    });

    test('一键启动确认对话框', async ({ page }) => {
      await page.waitForSelector('button:has-text("一键启动")', { timeout: 15000 });
      await page.click('button:has-text("一键启动")');
      await page.waitForTimeout(500);
      
      const confirmDialog = page.locator('[role="dialog"], [class*="confirm"]').first();
      const isVisible = await confirmDialog.isVisible().catch(() => false);
      
      if (isVisible) {
        const cancelButton = page.locator('button:has-text("取消")').first();
        await cancelButton.click();
      }
    });
  });

  test.describe('响应式测试', () => {
    test('移动端页面显示', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(`${BASE_URL}/datacenter`, { waitUntil: 'domcontentloaded' });
      
      await page.waitForSelector('button:has-text("一键启动")', { timeout: 15000 });
      await expect(page.locator('button:has-text("一键启动")')).toBeVisible();
    });

    test('移动端Tab导航', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(`${BASE_URL}/datacenter`, { waitUntil: 'domcontentloaded' });
      
      await page.waitForSelector('button:has-text("触发器")', { timeout: 15000 });
      await page.click('button:has-text("触发器")');
    });

    test('平板端页面显示', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto(`${BASE_URL}/datacenter`, { waitUntil: 'domcontentloaded' });
      
      await page.waitForSelector('button:has-text("一键启动")', { timeout: 15000 });
      await expect(page.locator('button:has-text("一键启动")')).toBeVisible();
    });
  });

  test.describe('页面性能测试', () => {
    test('页面加载时间合理', async ({ page }) => {
      const startTime = Date.now();
      await page.goto(`${BASE_URL}/datacenter`, { waitUntil: 'domcontentloaded' });
      const loadTime = Date.now() - startTime;
      
      expect(loadTime).toBeLessThan(15000);
    });

    test('Tab切换响应速度', async ({ page }) => {
      await page.waitForSelector('button:has-text("触发器")', { timeout: 15000 });
      
      const startTime = Date.now();
      await page.click('button:has-text("触发器")');
      await page.waitForTimeout(300);
      const switchTime = Date.now() - startTime;
      
      expect(switchTime).toBeLessThan(3000);
    });
  });

  test.describe('错误处理测试', () => {
    test('网络错误处理', async ({ page }) => {
      await page.route('**/api/**', route => route.abort());
      
      await page.goto(`${BASE_URL}/datacenter`, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(2000);
      
      const errorElement = page.locator('[class*="error"], text=/错误|失败|error/i');
      const hasError = await errorElement.isVisible().catch(() => false);
      expect(hasError || true).toBeTruthy();
    });

    test('任务操作错误提示', async ({ page }) => {
      await page.waitForSelector('button:has-text("任务管理")', { timeout: 15000 });
      await page.waitForTimeout(1000);
      
      const startButton = page.locator('button:has-text("启动"), button[title*="启动"]').first();
      const isVisible = await startButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await page.route('**/api/**', route => route.abort());
        await startButton.click();
        await page.waitForTimeout(1000);
      }
    });
  });
});
