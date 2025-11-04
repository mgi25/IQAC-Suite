import { test, expect } from '@playwright/test';
import path from 'path';

test('autosave sends explicit blanks when fields are cleared', async ({ page }) => {
  const autosavePath = path.join(__dirname, '..', 'emt', 'static', 'emt', 'js', 'autosave_draft.js');

  await page.setContent('<form><input name="title" value="Original" /></form>');
  await page.addScriptTag({ path: autosavePath });

  await page.evaluate(() => {
    (window as any).AUTOSAVE_URL = '/suite/autosave-proposal/';
    (window as any).AUTOSAVE_CSRF = 'TOKEN';
    (window as any).__payloads = [];
    let counter = 0;
    window.fetch = ((_fetch) => (input: any, init?: any) => {
      const body = init?.body;
      if (typeof body === 'string') {
        try {
          (window as any).__payloads.push(JSON.parse(body));
        } catch {
          // ignore JSON parse failures in tests
        }
      }
      counter += 1;
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({ proposal_id: 100 + counter, success: true }),
      });
    })(window.fetch);
  });

  await page.evaluate(async () => {
    await (window as any).AutosaveManager.manualSave();
  });

  await page.fill('input[name="title"]', '');

  await page.evaluate(async () => {
    await (window as any).AutosaveManager.manualSave();
  });

  const payloads = await page.evaluate(() => (window as any).__payloads);
  expect(payloads.length).toBeGreaterThanOrEqual(2);
  const lastPayload = payloads[payloads.length - 1];
  expect(lastPayload).toHaveProperty('title', '');
});
