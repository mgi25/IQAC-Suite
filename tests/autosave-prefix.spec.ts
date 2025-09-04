import { test, expect } from '@playwright/test';
import path from 'path';

// Ensure autosave helper respects custom URL prefixes
// by using window.AUTOSAVE_URL instead of a hardcoded path.
test('autosave respects custom prefix', async ({ page }) => {
  const autosavePath = path.join(__dirname, '..', 'emt', 'static', 'emt', 'js', 'autosave_draft.js');

  // Intercept the expected autosave URL
  const routePromise = page.waitForRequest('**/custom/autosave-proposal/');
  await page.route('**/custom/autosave-proposal/', route => {
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });

  await page.addInitScript(() => {
    // Define globals used by autosave()
    (window as any).AUTOSAVE_URL = '/custom/autosave-proposal/';
    (window as any).AUTOSAVE_CSRF = 'TOKEN';
  });

  await page.setContent('<form><input name="title" value="Test" /></form>');
  await page.addScriptTag({ path: autosavePath });

  await page.evaluate(() => (window as any).autosave());
  const request = await routePromise;
  expect(request.url()).toContain('/custom/autosave-proposal/');
});
