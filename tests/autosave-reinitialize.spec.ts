import { test, expect } from '@playwright/test';
import path from 'path';

test('reinitialize sets saved values and dispatches change events', async ({ page }) => {
  const autosavePath = path.join(__dirname, '..', 'emt', 'static', 'emt', 'js', 'autosave_draft.js');

  await page.route('http://example.com/proposal', route => {
    route.fulfill({
      contentType: 'text/html',
      body: `
        <html><body>
          <select name="organization_type">
            <option value="1">Dept</option>
            <option value="2">Club</option>
          </select>
          <select name="organization">
            <option value="10">Science</option>
            <option value="20">Robotics</option>
          </select>
        </body></html>
      `,
    });
  });
  await page.addInitScript(() => {
    (window as any).USER_ID = 1;
    (window as any).PROPOSAL_ID = '';
  });
  await page.goto('http://example.com/proposal');

  await page.evaluate(() => {
    // default selections rendered by server
    (document.querySelector('[name="organization_type"]') as HTMLSelectElement).value = '1';
    (document.querySelector('[name="organization"]') as HTMLSelectElement).value = '10';
    // saved draft values to apply
    localStorage.setItem('proposal_draft_1_/proposal_new', JSON.stringify({
      organization_type: '2',
      organization: '20'
    }));
    // listen for change events
    (window as any).changes = [];
    document.querySelectorAll('select').forEach(sel => {
      sel.addEventListener('change', () => (window as any).changes.push(sel.name));
    });
  });

  await page.addScriptTag({ path: autosavePath });

  const values = await page.evaluate(() => {
    return {
      organization_type: (document.querySelector('[name="organization_type"]') as HTMLSelectElement).value,
      organization: (document.querySelector('[name="organization"]') as HTMLSelectElement).value,
      changes: (window as any).changes,
    };
  });

  expect(values.organization_type).toBe('2');
  expect(values.organization).toBe('20');
  expect(values.changes.sort()).toEqual(['organization', 'organization_type']);
});
