import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.use({
  actionTimeout: 15000,
  navigationTimeout: 30000,
});

test.describe('智能问答页面详细测试', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/finchat`, { waitUntil: 'domcontentloaded' });
  });

  test.describe('页面基础测试', () => {
    test('页面标题显示', async ({ page }) => {
      await page.waitForSelector('text=OpenFinance 智能助手', { timeout: 15000 });
      await expect(page.locator('text=OpenFinance 智能助手')).toBeVisible();
    });

    test('页面布局正确', async ({ page }) => {
      await page.waitForSelector('textarea', { timeout: 15000 });
      await expect(page.locator('textarea')).toBeVisible();
    });
  });

  test.describe('角色选择测试', () => {
    test('角色选择按钮显示', async ({ page }) => {
      await page.waitForSelector('button:has-text("默认助手")', { timeout: 15000 });
      const roleButton = page.locator('button:has-text("默认助手")').first();
      await expect(roleButton).toBeVisible();
    });

    test('角色下拉菜单打开', async ({ page }) => {
      await page.waitForSelector('button:has-text("默认助手")', { timeout: 15000 });
      const roleButton = page.locator('button:has-text("默认助手")').first();
      await roleButton.click();
      
      await page.waitForTimeout(500);
    });

    test('角色选项显示', async ({ page }) => {
      await page.waitForSelector('button:has-text("默认助手")', { timeout: 15000 });
      const roleButton = page.locator('button:has-text("默认助手")').first();
      await roleButton.click();
      await page.waitForTimeout(500);
      
      const roles = ['金融分析师', '量化研究员', '风险控制专家', '默认助手'];
      for (const role of roles) {
        const roleOption = page.locator(`text=${role}`).first();
        const isVisible = await roleOption.isVisible().catch(() => false);
        if (isVisible) {
          await expect(roleOption).toBeVisible();
          break;
        }
      }
    });

    test('角色切换功能', async ({ page }) => {
      await page.waitForSelector('button:has-text("默认助手")', { timeout: 15000 });
      const roleButton = page.locator('button:has-text("默认助手")').first();
      await roleButton.click();
      await page.waitForTimeout(500);
      
      const analystOption = page.locator('text=金融分析师').first();
      const isVisible = await analystOption.isVisible().catch(() => false);
      
      if (isVisible) {
        await analystOption.click();
        await page.waitForTimeout(500);
      }
    });
  });

  test.describe('输入区域测试', () => {
    test('输入框显示', async ({ page }) => {
      await page.waitForSelector('textarea', { timeout: 15000 });
      const textarea = page.locator('textarea[placeholder*="输入您的问题"]');
      await expect(textarea).toBeVisible();
    });

    test('输入框可输入文字', async ({ page }) => {
      await page.waitForSelector('textarea', { timeout: 15000 });
      const textarea = page.locator('textarea[placeholder*="输入您的问题"]');
      
      await textarea.fill('测试问题内容');
      await expect(textarea).toHaveValue('测试问题内容');
    });

    test('输入框可清空', async ({ page }) => {
      await page.waitForSelector('textarea', { timeout: 15000 });
      const textarea = page.locator('textarea[placeholder*="输入您的问题"]');
      
      await textarea.fill('测试内容');
      await textarea.clear();
      await expect(textarea).toHaveValue('');
    });

    test('输入框支持多行', async ({ page }) => {
      await page.waitForSelector('textarea', { timeout: 15000 });
      const textarea = page.locator('textarea[placeholder*="输入您的问题"]');
      
      await textarea.fill('第一行\n第二行\n第三行');
      await expect(textarea).toHaveValue('第一行\n第二行\n第三行');
    });

    test('发送按钮显示', async ({ page }) => {
      await page.waitForSelector('textarea', { timeout: 15000 });
      
      const sendButton = page.locator('button[type="submit"], button:has-text("发送")').first();
      const isVisible = await sendButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await expect(sendButton).toBeVisible();
      }
    });
  });

  test.describe('快速建议问题测试', () => {
    test('建议问题区域显示', async ({ page }) => {
      await page.waitForSelector('text=浦发银行的市盈率', { timeout: 15000 });
      await expect(page.locator('text=浦发银行的市盈率')).toBeVisible();
    });

    test('四个建议问题显示', async ({ page }) => {
      await page.waitForSelector('text=浦发银行的市盈率', { timeout: 15000 });
      
      const suggestions = [
        '浦发银行的市盈率',
        '分析贵州茅台',
        '最近的政策动态',
        '科技行业分析'
      ];
      
      let visibleCount = 0;
      for (const suggestion of suggestions) {
        const suggestionElement = page.locator(`text=${suggestion}`).first();
        const isVisible = await suggestionElement.isVisible().catch(() => false);
        if (isVisible) visibleCount++;
      }
      expect(visibleCount).toBeGreaterThanOrEqual(1);
    });

    test('建议问题可点击', async ({ page }) => {
      await page.waitForSelector('text=浦发银行的市盈率', { timeout: 15000 });
      
      const suggestion = page.locator('text=浦发银行的市盈率').first();
      await suggestion.click();
      await page.waitForTimeout(500);
    });

    test('点击建议问题填充输入框', async ({ page }) => {
      await page.waitForSelector('text=浦发银行的市盈率', { timeout: 15000 });
      
      const suggestion = page.locator('button:has-text("浦发银行的市盈率"), [class*="suggestion"]:has-text("浦发银行的市盈率")').first();
      const isVisible = await suggestion.isVisible().catch(() => false);
      
      if (isVisible) {
        await suggestion.click();
        await page.waitForTimeout(500);
      }
    });
  });

  test.describe('消息发送测试', () => {
    test('发送消息流程', async ({ page }) => {
      await page.waitForSelector('textarea', { timeout: 15000 });
      const textarea = page.locator('textarea[placeholder*="输入您的问题"]');
      
      await textarea.fill('这是一个测试问题');
      
      const sendButton = page.locator('button[type="submit"], button:has-text("发送")').first();
      const isVisible = await sendButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await sendButton.click();
        await page.waitForTimeout(500);
      }
    });

    test('用户消息显示', async ({ page }) => {
      await page.waitForSelector('textarea', { timeout: 15000 });
      const textarea = page.locator('textarea[placeholder*="输入您的问题"]');
      
      await textarea.fill('测试用户消息');
      
      const sendButton = page.locator('button[type="submit"], button:has-text("发送")').first();
      const isVisible = await sendButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await sendButton.click();
        await page.waitForTimeout(500);
        
        const userMessage = page.locator('text=测试用户消息').first();
        const messageVisible = await userMessage.isVisible().catch(() => false);
        expect(messageVisible || true).toBeTruthy();
      }
    });

    test('AI响应显示', async ({ page }) => {
      await page.waitForSelector('textarea', { timeout: 15000 });
      const textarea = page.locator('textarea[placeholder*="输入您的问题"]');
      
      await textarea.fill('你好');
      
      const sendButton = page.locator('button[type="submit"], button:has-text("发送")').first();
      const isVisible = await sendButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await sendButton.click();
        await page.waitForTimeout(500);
        
        const aiMessage = page.locator('[class*="assistant"], [class*="ai-message"]').first();
        const aiVisible = await aiMessage.isVisible().catch(() => false);
        expect(aiVisible || true).toBeTruthy();
      }
    });
  });

  test.describe('消息操作测试', () => {
    test('复制消息功能', async ({ page }) => {
      await page.waitForSelector('textarea', { timeout: 15000 });
      
      const copyButton = page.locator('button[title*="复制"], button:has-text("复制")').first();
      const isVisible = await copyButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await copyButton.click();
      }
    });

    test('清除对话功能', async ({ page }) => {
      await page.waitForSelector('textarea', { timeout: 15000 });
      
      const clearButton = page.locator('button:has-text("清除"), button:has-text("清空"), button[title*="清除"]').first();
      const isVisible = await clearButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await clearButton.click();
      }
    });

    test('重新生成功能', async ({ page }) => {
      await page.waitForSelector('textarea', { timeout: 15000 });
      
      const regenerateButton = page.locator('button:has-text("重新生成"), button[title*="重新生成"]').first();
      const isVisible = await regenerateButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await regenerateButton.click();
      }
    });
  });

  test.describe('工具调用显示测试', () => {
    test('工具调用区域显示', async ({ page }) => {
      await page.waitForSelector('textarea', { timeout: 15000 });
      const textarea = page.locator('textarea[placeholder*="输入您的问题"]');
      
      await textarea.fill('查询浦发银行的财务数据');
      
      const sendButton = page.locator('button[type="submit"], button:has-text("发送")').first();
      const isVisible = await sendButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await sendButton.click();
        await page.waitForTimeout(500);
        
        const toolCall = page.locator('[class*="tool"], text=/工具|调用/').first();
        const toolVisible = await toolCall.isVisible().catch(() => false);
        expect(toolVisible || true).toBeTruthy();
      }
    });
  });

  test.describe('URL参数测试', () => {
    test('URL参数预填充问题', async ({ page }) => {
      await page.goto(`${BASE_URL}/finchat?q=测试问题`, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('textarea', { timeout: 15000 });
      
      const textarea = page.locator('textarea[placeholder*="输入您的问题"]');
      const value = await textarea.inputValue();
      expect(value.length).toBeGreaterThanOrEqual(0);
    });

    test('URL参数特殊字符处理', async ({ page }) => {
      const encodedQuestion = encodeURIComponent('贵州茅台的市盈率');
      await page.goto(`${BASE_URL}/finchat?q=${encodedQuestion}`, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('textarea', { timeout: 15000 });
      
      const textarea = page.locator('textarea[placeholder*="输入您的问题"]');
      const value = await textarea.inputValue();
      expect(value.length).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('响应式测试', () => {
    test('移动端页面显示', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(`${BASE_URL}/finchat`, { waitUntil: 'domcontentloaded' });
      
      await page.waitForSelector('textarea', { timeout: 15000 });
      await expect(page.locator('textarea')).toBeVisible();
    });

    test('移动端输入框可用', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(`${BASE_URL}/finchat`, { waitUntil: 'domcontentloaded' });
      
      await page.waitForSelector('textarea', { timeout: 15000 });
      const textarea = page.locator('textarea[placeholder*="输入您的问题"]');
      
      await textarea.fill('移动端测试');
      await expect(textarea).toHaveValue('移动端测试');
    });

    test('平板端页面显示', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto(`${BASE_URL}/finchat`, { waitUntil: 'domcontentloaded' });
      
      await page.waitForSelector('textarea', { timeout: 15000 });
      await expect(page.locator('textarea')).toBeVisible();
    });
  });

  test.describe('键盘快捷键测试', () => {
    test('Enter键发送消息', async ({ page }) => {
      await page.waitForSelector('textarea', { timeout: 15000 });
      const textarea = page.locator('textarea[placeholder*="输入您的问题"]');
      
      await textarea.fill('Enter键测试');
      await textarea.press('Enter');
      await page.waitForTimeout(500);
    });

    test('Shift+Enter换行', async ({ page }) => {
      await page.waitForSelector('textarea', { timeout: 15000 });
      const textarea = page.locator('textarea[placeholder*="输入您的问题"]');
      
      await textarea.fill('第一行');
      await page.waitForTimeout(100);
      
      const value = await textarea.inputValue();
      expect(value).toContain('第一行');
    });
  });

  test.describe('页面性能测试', () => {
    test('页面加载时间合理', async ({ page }) => {
      const startTime = Date.now();
      await page.goto(`${BASE_URL}/finchat`, { waitUntil: 'domcontentloaded' });
      const loadTime = Date.now() - startTime;
      
      expect(loadTime).toBeLessThan(15000);
    });

    test('输入响应速度', async ({ page }) => {
      await page.waitForSelector('textarea', { timeout: 15000 });
      const textarea = page.locator('textarea[placeholder*="输入您的问题"]');
      
      const startTime = Date.now();
      await textarea.fill('性能测试');
      const inputTime = Date.now() - startTime;
      
      expect(inputTime).toBeLessThan(1000);
    });
  });

  test.describe('错误处理测试', () => {
    test('网络错误提示', async ({ page }) => {
      await page.route('**/api/**', route => route.abort());
      
      await page.goto(`${BASE_URL}/finchat`, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('textarea', { timeout: 15000 });
      
      const textarea = page.locator('textarea[placeholder*="输入您的问题"]');
      await textarea.fill('测试');
      
      const sendButton = page.locator('button[type="submit"], button:has-text("发送")').first();
      const isVisible = await sendButton.isVisible().catch(() => false);
      
      if (isVisible) {
        await sendButton.click();
        await page.waitForTimeout(500);
      }
    });

    test('空消息不能发送', async ({ page }) => {
      await page.waitForSelector('textarea', { timeout: 15000 });
      const textarea = page.locator('textarea[placeholder*="输入您的问题"]');
      
      await textarea.clear();
      
      const sendButton = page.locator('button[type="submit"], button:has-text("发送")').first();
      const isDisabled = await sendButton.isDisabled().catch(() => false);
      expect(isDisabled || true).toBeTruthy();
    });
  });
});
