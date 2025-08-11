import { test } from '@playwright/test';
import percySnapshot from '@percy/playwright';

test('critical paths render correctly', async ({ page }) => {
  await page.goto('https://example.com');
  const label = 'critical-path';
  await percySnapshot(page, label, { widths: [1280] });
});
