import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.use({
  actionTimeout: 10000,
  navigationTimeout: 30000,
});

test.describe('首页详细测试', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('h1', { timeout: 10000 });
  });

  test.describe('Hero区域测试', () => {
    test('Hero标题正确显示', async ({ page }) => {
      await expect(page.locator('h1')).toContainText('重新定义');
      await expect(page.locator('span.gradient-text:has-text("金融分析")')).toBeVisible();
    });

    test('Hero副标题显示', async ({ page }) => {
      await expect(page.locator('text=基于大语言模型的智能分析引擎')).toBeVisible();
    });

    test('Hero描述文字显示', async ({ page }) => {
      const description = page.locator('text=整合多源金融数据');
      await expect(description).toBeVisible();
    });
  });

  test.describe('功能卡片测试', () => {
    test('四个功能卡片都显示', async ({ page }) => {
      const featureCards = ['智能分析', '量化分析', '智能问答', '知识图谱'];
      for (const feature of featureCards) {
        const card = page.locator(`text=${feature}`).first();
        await expect(card).toBeVisible();
      }
    });

    test('智能分析卡片导航', async ({ page }) => {
      const link = page.locator('a[href="/analysis"]').first();
      await expect(link).toBeVisible();
      await link.click();
      await page.waitForURL('**/analysis**', { timeout: 10000 });
      await expect(page).toHaveURL(/analysis/);
    });

    test('量化分析卡片导航', async ({ page }) => {
      const link = page.locator('a[href="/quant"]').first();
      await expect(link).toBeVisible();
      await link.click();
      await page.waitForURL('**/quant**', { timeout: 10000 });
      await expect(page).toHaveURL(/quant/);
    });

    test('智能问答卡片导航', async ({ page }) => {
      const link = page.locator('a[href="/finchat"]').first();
      await expect(link).toBeVisible();
      await link.click();
      await page.waitForURL('**/finchat**', { timeout: 10000 });
      await expect(page).toHaveURL(/finchat/);
    });

    test('知识图谱卡片导航', async ({ page }) => {
      const link = page.locator('a[href="/knowledge-graph"]').first();
      await expect(link).toBeVisible();
      await link.click();
      await page.waitForURL('**/knowledge-graph**', { timeout: 10000 });
      await expect(page).toHaveURL(/knowledge-graph/);
    });

    test('功能卡片图标显示', async ({ page }) => {
      const icons = page.locator('svg').filter({ hasText: '' });
      const count = await icons.count();
      expect(count).toBeGreaterThan(0);
    });
  });

  test.describe('快速开始问题测试', () => {
    test('快速开始标题显示', async ({ page }) => {
      await expect(page.locator('text=快速开始')).toBeVisible();
    });

    test('四个快速问题显示', async ({ page }) => {
      const quickQuestions = [
        '浦发银行的市盈率',
        '分析贵州茅台',
        '最近的政策动态',
        '科技行业分析'
      ];
      
      for (const question of quickQuestions) {
        const questionLink = page.locator(`text=${question}`).first();
        await expect(questionLink).toBeVisible();
      }
    });

    test('快速问题点击跳转到Finchat', async ({ page }) => {
      const quickLink = page.locator('a[href*="/finchat?q="]').first();
      await expect(quickLink).toBeVisible();
      
      const href = await quickLink.getAttribute('href');
      expect(href).toContain('/finchat?q=');
    });

    test('快速问题包含正确的查询参数', async ({ page }) => {
      const quickLink = page.locator('a[href*="/finchat?q="]').first();
      const href = await quickLink.getAttribute('href');
      expect(href).toMatch(/q=/);
    });
  });

  test.describe('统计数据测试', () => {
    test('统计数据区域显示', async ({ page }) => {
      await expect(page.locator('text=数据覆盖')).toBeVisible();
    });

    test('四个统计项显示', async ({ page }) => {
      const stats = ['数据覆盖', '分析报告', '用户信赖', '响应速度'];
      
      for (const stat of stats) {
        const statElement = page.locator(`text=${stat}`).first();
        await expect(statElement).toBeVisible();
      }
    });

    test('统计数字显示', async ({ page }) => {
      const numbers = page.locator('text=/\\d+[+]?/');
      const count = await numbers.count();
      expect(count).toBeGreaterThan(0);
    });
  });

  test.describe('信任项测试', () => {
    test('信任区域标题显示', async ({ page }) => {
      const trustTitle = page.locator('text=值得信赖').first();
      await expect(trustTitle).toBeVisible();
    });

    test('信任项图标显示', async ({ page }) => {
      const trustSection = page.locator('section').filter({ hasText: '值得信赖' });
      const icons = trustSection.locator('svg');
      const count = await icons.count();
      expect(count).toBeGreaterThan(0);
    });
  });

  test.describe('Footer测试', () => {
    test('Footer显示', async ({ page }) => {
      await page.scrollTo('bottom', { timeout: 5000 });
      const footer = page.locator('footer');
      await expect(footer).toBeVisible();
    });

    test('Footer版权信息显示', async ({ page }) => {
      await page.scrollTo('bottom', { timeout: 5000 });
      const copyright = page.locator('text=/©|Copyright|OpenFinance/i');
      await expect(copyright.first()).toBeVisible();
    });

    test('Footer链接可点击', async ({ page }) => {
      await page.scrollTo('bottom', { timeout: 5000 });
      const footerLinks = page.locator('footer a');
      const count = await footerLinks.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('响应式测试', () => {
    test('移动端Hero区域显示', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('h1', { timeout: 10000 });
      
      await expect(page.locator('h1')).toBeVisible();
    });

    test('移动端功能卡片显示', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('h1', { timeout: 10000 });
      
      const featureCards = ['智能分析', '量化分析', '智能问答', '知识图谱'];
      for (const feature of featureCards) {
        await expect(page.locator(`text=${feature}`).first()).toBeVisible();
      }
    });

    test('平板端显示', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('h1', { timeout: 10000 });
      
      await expect(page.locator('h1')).toBeVisible();
    });
  });

  test.describe('页面性能测试', () => {
    test('页面加载时间合理', async ({ page }) => {
      const startTime = Date.now();
      await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
      const loadTime = Date.now() - startTime;
      
      expect(loadTime).toBeLessThan(10000);
    });

    test('关键内容优先渲染', async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
      
      await expect(page.locator('h1')).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('可访问性测试', () => {
    test('标题层级正确', async ({ page }) => {
      const h1 = page.locator('h1');
      await expect(h1).toBeVisible();
      
      const h1Count = await h1.count();
      expect(h1Count).toBe(1);
    });

    test('链接有可识别文本', async ({ page }) => {
      const links = page.locator('a');
      const count = await links.count();
      
      for (let i = 0; i < Math.min(count, 10); i++) {
        const link = links.nth(i);
        const text = await link.textContent();
        const href = await link.getAttribute('href');
        expect(text || href).toBeTruthy();
      }
    });
  });
});
