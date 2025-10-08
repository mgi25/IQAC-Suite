import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const dashboardPath = path.join(__dirname, '..', 'emt', 'static', 'emt', 'js', 'proposal_dashboard.js');
const dashboardSource = fs.readFileSync(dashboardPath, 'utf8');
const jqueryPath = path.join(__dirname, '..', 'node_modules', 'jquery', 'dist', 'jquery.min.js');
const jquerySource = fs.readFileSync(jqueryPath, 'utf8');

const extractFunctionSource = (startToken: string, endToken: string) => {
  const startIndex = dashboardSource.indexOf(startToken);
  const endIndex = dashboardSource.indexOf(endToken, startIndex);
  if (startIndex === -1 || endIndex === -1) {
    throw new Error(`Unable to extract source between ${startToken} and ${endToken}`);
  }
  return dashboardSource.slice(startIndex, endIndex).trim();
};

const applySource = extractFunctionSource('function applyTargetAudienceSelection', 'function setupAudienceModal');
const collectSource = extractFunctionSource('function collectBasicInfo()', 'function setupWhyThisEventAI');
const saveSource = extractFunctionSource('function saveCurrentSection()', 'function getNextSection');

test('saveCurrentSection advances after autosave with long audience summary', async ({ page }) => {
  const longNames = Array.from({ length: 40 }, (_, idx) => `Student ${idx + 1}`);

  await page.setContent(`
    <div id="django-basic-info">
      <input name="target_audience" />
    </div>
    <input id="target-audience-modern" />
    <input id="target-audience-class-ids" />
    <div class="proposal-nav">
      <a class="nav-link disabled" data-section="basic-info"></a>
      <a class="nav-link disabled" data-section="why-this-event" data-url=""></a>
    </div>
  `);

  await page.addScriptTag({ content: jquerySource });

  await page.evaluate(({ applySource, collectSource, saveSource, longNames }) => {
    window.notifications = [];
    window.$ = window.jQuery;
    window.currentExpandedCard = 'basic-info';
    window.serializeSchedule = () => { window.serializeCalled = true; };
    window.validateCurrentSection = () => true;
    window.markSectionInProgress = () => {};
    window.clearFieldError = () => {};
    window.logAudienceAction = (action, details) => { window.lastAudienceLog = { action, details }; };
    window.showNotification = (message, type) => { window.notifications.push({ message, type }); };
    window.getNextSection = () => 'why-this-event';
    window.openFormPanel = (section) => { window.openedSection = section; };
    window.showLoadingOverlay = () => { window.loadingOverlayShown = true; };
    window.hideLoadingOverlay = () => { window.loadingOverlayHidden = true; };
    window.markSectionComplete = (section) => { window.sectionCompleted = section; };
    window.handleAutosaveErrors = () => { window.autosaveErrorsHandled = true; };
    window.AutosaveManager = {
      manualSave: () => {
        window.manualSaveCalls = (window.manualSaveCalls || 0) + 1;
        return Promise.resolve({});
      }
    };
    window.setTimeout = (fn) => { fn(); return 0; };
    window.clearTimeout = () => {};

    eval(`${applySource}\nwindow.applyTargetAudienceSelection = applyTargetAudienceSelection;`);
    eval(`${collectSource}\nwindow.collectBasicInfo = collectBasicInfo;`);
    eval(`${saveSource}\nwindow.saveCurrentSection = saveCurrentSection;`);

    window.applyTargetAudienceSelection({
      selectedStudents: longNames.map((name, idx) => ({ id: idx + 1, name })),
      selectedFaculty: [],
      userSelected: []
    });

    window.basicInfoSnapshot = window.collectBasicInfo();

    window.saveCurrentSection();
  }, { applySource, collectSource, saveSource, longNames });

  await page.waitForFunction(() => window.sectionCompleted === 'basic-info');
  await page.waitForFunction(() => window.openedSection === 'why-this-event');

  const results = await page.evaluate(() => {
    const djangoField = document.querySelector('#django-basic-info [name="target_audience"]') as HTMLInputElement;
    const navLink = document.querySelector('.proposal-nav .nav-link[data-section="why-this-event"]') as HTMLElement;
    const modernField = window.jQuery('#target-audience-modern');

    return {
      summaryValue: djangoField.value,
      summaryLength: djangoField.value.length,
      fullAudienceAttr: djangoField.getAttribute('data-full-audience'),
      fullAudienceData: window.jQuery(djangoField).data('fullAudience'),
      modernFullAudience: modernField.data('fullAudience'),
      manualSaveCalls: window.manualSaveCalls,
      openedSection: window.openedSection,
      sectionCompleted: window.sectionCompleted,
      navAdvanced: !navLink.classList.contains('disabled'),
      notifications: window.notifications,
      audienceLog: window.lastAudienceLog,
      classIds: (document.getElementById('target-audience-class-ids') as HTMLInputElement).value,
      basicInfoAudience: window.basicInfoSnapshot?.audience ?? null,
    };
  });

  expect(results.summaryLength).toBeLessThanOrEqual(200);
  expect(results.summaryValue).toContain('+');
  expect(results.basicInfoAudience).toBe(results.summaryValue);
  expect(results.basicInfoAudience?.length ?? 0).toBeLessThanOrEqual(200);
  expect(results.fullAudienceAttr).toBe(results.fullAudienceData);
  expect(results.modernFullAudience).toContain('Student 1');
  expect(results.manualSaveCalls).toBe(1);
  expect(results.sectionCompleted).toBe('basic-info');
  expect(results.openedSection).toBe('why-this-event');
  expect(results.navAdvanced).toBeTruthy();
  expect(results.notifications.some(n => n.type === 'warning')).toBeTruthy();
  expect(results.notifications.some(n => n.type === 'success')).toBeTruthy();
  expect(results.audienceLog.details.summary.length).toBeLessThanOrEqual(200);
  expect(results.classIds.split(',').length).toBe(longNames.length);
});
