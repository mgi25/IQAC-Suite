import { test, expect } from '@playwright/test';
import path from 'path';

// Ensure autosave helper respects custom URL prefixes
// by using window.AUTOSAVE_URL instead of a hardcoded path.
test('autosave respects custom prefix', async ({ page }) => {
  const autosavePath = path.join(__dirname, '..', 'emt', 'static', 'emt', 'js', 'autosave_draft.js');

  await page.setContent('<form><input name="title" value="Test" /></form>');
  await page.addScriptTag({ path: autosavePath });
  await page.evaluate(() => {
    (window as any).AUTOSAVE_URL = '/custom/autosave-proposal/';
    (window as any).AUTOSAVE_CSRF = 'TOKEN';
    (window as any).__fetchCalls = [];
    window.fetch = ((originalFetch) => (input: any, init?: any) => {
      (window as any).__fetchCalls.push(typeof input === 'string' ? input : input.toString());
      return Promise.resolve({
        ok: true,
        json: async () => ({}),
        text: async () => '',
        status: 200,
      });
    })(window.fetch);
  });

  await page.evaluate(() => (window as any).autosave());
  const urls = await page.evaluate(() => (window as any).__fetchCalls);
  expect(urls).toContain('/custom/autosave-proposal/');
});
