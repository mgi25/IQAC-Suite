let loadingCount = 0;

function showLoadingOverlay(text = 'Loading...') {
    const overlay = document.getElementById('loadingOverlay');
    if (!overlay) return;
    const textEl = overlay.querySelector('p');
    if (textEl) textEl.textContent = text;
    loadingCount++;
    overlay.classList.add('show');
}

function hideLoadingOverlay() {
    const overlay = document.getElementById('loadingOverlay');
    if (!overlay) return;
    loadingCount = Math.max(loadingCount - 1, 0);
    if (loadingCount === 0) {
        overlay.classList.remove('show');
    }
}

function fetchWithOverlay(url, options = {}, text = 'Loading...') {
    // Small helper to wrap fetch calls with the overlay lifecycle
    showLoadingOverlay(text);
    return fetch(url, options).finally(() => hideLoadingOverlay());
}

document.addEventListener('DOMContentLoaded', function(){
        const reportFormElement = document.getElementById('report-form');
    const iqacContinueButton = document.querySelector('[data-preview-continue="iqac"]');
    if (!reportFormElement) {
        if (iqacContinueButton) {
            const previewForm = iqacContinueButton.closest('form');
            const previewAction =
                iqacContinueButton.getAttribute('data-preview-action') ||
                iqacContinueButton.getAttribute('formaction');
            iqacContinueButton.addEventListener('click', (event) => {
                event.preventDefault();
                if (!previewForm) return;
                let flagField = previewForm.querySelector('input[name="show_iqac"]');
                if (!flagField) {
                    flagField = document.createElement('input');
                    flagField.type = 'hidden';
                    flagField.name = 'show_iqac';
                    previewForm.appendChild(flagField);
                }
                flagField.value = '1';
                if (previewAction) {
                    previewForm.setAttribute('action', previewAction);
                }
                showLoadingOverlay('Generating report...');
                previewForm.submit();
            });
        }
        return;
    }
        // Central init (single DOMContentLoaded listener)
        const sectionState = {}; // fieldName -> value snapshot
    const urlParams = new URLSearchParams(window.location.search || '');
    const FROM_GA_EDITOR = (urlParams.get('from') === 'ga');
    const RESET_PROGRESS_ON_LOAD = !FROM_GA_EDITOR;

    document.querySelectorAll('.form-group input:not([type=checkbox]):not([type=radio]), .form-group textarea, .form-group select').forEach(function(el){
    if(!el.placeholder) el.placeholder = ' ';
  });

  const posField = document.getElementById('id_pos_pso_mapping');
  const modal = document.getElementById('outcomeModal');
  if(posField && modal && modal.dataset.url){
    posField.addEventListener('click', openOutcomeModal);
    posField.readOnly = true;
    posField.style.cursor = 'pointer';
  }

  initAttachments();
  
  /* ===========================================
     SUBMIT EVENT REPORT PAGE INLINE JAVASCRIPT
     Moved from submit_event_report.html template
     =========================================== */

  // Global variables for form management
  if (typeof window.REPORT_ID === 'undefined') {
    console.log('Event Report Form initializing...');
  }

  const DEFAULT_SECTION_SEQUENCE = [
      'event-information',
      'participants-information',
      'event-summary',
      'event-outcomes',
      'analysis',
      'event-relevance',
      'attachments'
  ];
  const navLinks = Array.from(document.querySelectorAll('.nav-link[data-section]'));
  const derivedSectionOrder = navLinks
      .map((link, index) => {
          const rawOrder = parseInt(link.dataset.order, 10);
          const order = Number.isFinite(rawOrder) ? rawOrder : (index + 1);
          return { section: link.dataset.section, order, index };
      })
      .sort((a, b) => {
          if (a.order === b.order) {
              return a.index - b.index;
          }
          return a.order - b.order;
      })
      .map(item => item.section)
      .filter(Boolean);
  const SECTION_SEQUENCE = derivedSectionOrder.length ? derivedSectionOrder : DEFAULT_SECTION_SEQUENCE;
  const FIRST_SECTION = SECTION_SEQUENCE.includes('event-information')
      ? 'event-information'
      : (SECTION_SEQUENCE[0] || 'event-information');

  let currentSection = FIRST_SECTION;
  let saveAndContinueInFlight = false;
  let sectionProgress = {
      'event-information': false,
      'participants-information': false,
      'event-summary': false,
      'event-outcomes': false,
      'analysis': false,
      'event-relevance': false,
      'attachments': false
  };
  SECTION_SEQUENCE.forEach(section => {
      if (!sectionProgress.hasOwnProperty(section)) {
          sectionProgress[section] = false;
      }
  });

  // Persist progress per proposal to survive page reloads or navigation to GA editor
  const LS_PROGRESS_KEY = `event_report_progress_${window.PROPOSAL_ID || ''}`;
  function saveProgress() {
      try {
          const payload = { sectionProgress, lastSection: currentSection };
          localStorage.setItem(LS_PROGRESS_KEY, JSON.stringify(payload));
      } catch (e) { /* ignore quota errors */ }
  }
  function loadProgress() {
      try {
          const raw = localStorage.getItem(LS_PROGRESS_KEY);
          if (!raw) return;
          const data = JSON.parse(raw);
          if (data && typeof data === 'object') {
              if (data.sectionProgress && typeof data.sectionProgress === 'object') {
                  // Merge and apply saved completion to nav
                  sectionProgress = { ...sectionProgress, ...data.sectionProgress };
                  Object.entries(sectionProgress).forEach(([sec, done]) => {
                      if (done) {
                          enableSection(sec);
                          $(`.nav-link[data-section="${sec}"]`).addClass('completed');
                      }
                  });
              }
              if (data.lastSection && typeof data.lastSection === 'string') {
                  // Ensure the target is enabled before activating
                  enableSection(data.lastSection);
                  activateSection(data.lastSection);
              }
          }
      } catch (e) { /* noop */ }
  }

  const $reportForm = $('#report-form');
  const previewUrl =
      $reportForm.attr('data-preview-url') ||
      $reportForm.data('previewUrl') ||
      $reportForm.data('preview-url');

  function ensureAutosaveUrl() {
      if (window.AUTOSAVE_URL) {
          return;
      }
      const path = window.location.pathname || '';
      let prefix = '';
      if (path.startsWith('/suite/')) prefix = '/suite';
      else if (path.startsWith('/emt/')) prefix = '/emt';
      window.AUTOSAVE_URL = `${prefix}/autosave-event-report/`;
  }

  function autosaveThen(callback) {
      showLoadingOverlay('Saving...');
      ensureAutosaveUrl();
      const savePromise = (window.ReportAutosaveManager && window.ReportAutosaveManager.manualSave)
          ? window.ReportAutosaveManager.manualSave()
          : Promise.resolve();

      const invoke = () => {
          let submitted = false;
          try {
              submitted = Boolean(callback());
          } catch (err) {
              hideLoadingOverlay();
              throw err;
          }
          if (!submitted) {
              hideLoadingOverlay();
          }
          return submitted;
      };

      return savePromise.then(
          () => invoke(),
          () => {
              showNotification('Save failed', 'error');
              return invoke();
          }
      );
  }

  function submitForPreview() {
      if (!previewUrl) {
          showNotification('Preview unavailable. Please reload the page.', 'error');
          return false;
      }

      const form = $('#report-form');
      if (!form.length) {
          showNotification('Unable to locate the report form.', 'error');
          return false;
      }

      form.find('input.section-state-hidden').remove();

      const fieldsByName = {};
      form.find('input[name], select[name], textarea[name]').each(function(){
          const name = this.name;
          if(!fieldsByName[name]){
              fieldsByName[name] = [];
          }
          fieldsByName[name].push(this);
      });

      const appendHidden = (frm, name, value) => {
          frm.append($('<input>', {
              type: 'hidden',
              class: 'section-state-hidden',
              name: name,
              value: value,
          }));
      };

      Object.entries(fieldsByName).forEach(([name, elements]) => {
          const el = elements[0];
          if(el.tagName === 'SELECT'){
              const $el = $(el);
              const vals = $el.val();
              if(Array.isArray(vals)){
                  if(vals.length){
                      vals.forEach(v => appendHidden(form, name, v));
                  } else {
                      appendHidden(form, name, '');
                  }
              } else {
                  appendHidden(form, name, vals || '');
              }
          } else if(el.type === 'checkbox'){
              const checkedVals = elements.filter(e => e.checked).map(e => e.value);
              if(checkedVals.length){
                  checkedVals.forEach(v => appendHidden(form, name, v));
              } else {
                  appendHidden(form, name, '');
              }
          } else if(el.type === 'radio'){
              const checked = elements.find(e => e.checked);
              appendHidden(form, name, checked ? checked.value : '');
          } else {
              appendHidden(form, name, $(el).val() || '');
          }
      });

      Object.entries(sectionState).forEach(([name, value]) => {
          if (fieldsByName[name]) return;
          if (name === 'csrfmiddlewaretoken') return;
          if (Array.isArray(value)) {
              if (value.length) {
                  value.forEach(v => appendHidden(form, name, v));
              } else {
                  appendHidden(form, name, '');
              }
          } else if (typeof value === 'boolean') {
              appendHidden(form, name, value ? 'on' : '');
          } else {
              appendHidden(form, name, value != null ? String(value) : '');
          }
      });

      form.attr('action', previewUrl);
      showLoadingOverlay('Generating preview...');
      form[0].submit();
      return true;
  }

      // Reset progress and always start from the first section on load
      if (RESET_PROGRESS_ON_LOAD) {
          try {
              const LS_PROGRESS_KEY = `event_report_progress_${window.PROPOSAL_ID || ''}`;
              localStorage.removeItem(LS_PROGRESS_KEY);
          } catch (e) {}
          // Clear any UI state
          Object.keys(sectionProgress).forEach(key => {
              sectionProgress[key] = false;
          });
          document.querySelectorAll('.nav-link').forEach(link => {
              link.classList.remove('completed', 'active');
              if (link.dataset.section !== FIRST_SECTION) {
                  link.classList.add('disabled');
              }
          });
          // Ensure first section is active and content is loaded
          activateSection(FIRST_SECTION);
          // Hide final submit
          const submitSection = document.querySelector('.submit-section');
          if (submitSection) submitSection.classList.add('hidden');
          const submitBtn = document.getElementById('submit-report-btn');
          if (submitBtn) submitBtn.disabled = true;
          const reviewBtn = document.getElementById('review-report-btn');
          if (reviewBtn) reviewBtn.disabled = true;
      } else {
          // Rehydrate progress from server-rendered classes (if editing existing draft)
          document.querySelectorAll('.nav-link').forEach(link => {
              if(link.classList.contains('completed')){
                  const s = link.getAttribute('data-section');
                  if(sectionProgress.hasOwnProperty(s)) sectionProgress[s] = true;
              }
          });
          // Also restore from localStorage so progress persists across full reloads and GA editor hops
          loadProgress();
          if(allSectionsCompleted()) enableFinalSubmission();
          // If a target section is specified in the URL (?section=...), activate it
          try {
              const params = new URLSearchParams(window.location.search);
              const fromSection = params.get('section');
              if (fromSection) {
                  enableSection(fromSection);
                  setTimeout(() => {
                      const link = document.querySelector(`.nav-link[data-section="${fromSection}"]`);
                      if (link) link.classList.remove('disabled');
                      activateSection(fromSection);
                  }, 50);
              }
            } catch (e) {}
      }
  
  // Auto-resize textarea functionality
  function autoResizeTextarea(textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = textarea.scrollHeight + 'px';
  }
  
  // Initialize auto-resize for all textareas
  function initializeAutoResize() {
      $(document).on('input', 'textarea', function() {
          autoResizeTextarea(this);
      });
      
      // Initial resize for existing content
      $('textarea').each(function() {
          autoResizeTextarea(this);
      });
      
      // Word counter for event summary
      const hiddenSummaryField = $('textarea[name="event_summary"][hidden]');
      $(document).on('input', '#event-summary-modern', function() {
          const text = $(this).val().trim();
          const wordCount = text ? text.split(/\s+/).filter(word => word.length > 0).length : 0;
          $('#summary-word-count').text(wordCount);
          hiddenSummaryField.val($(this).val());

          // Update styling based on word count
          if (wordCount >= 500) {
              $('#summary-word-count').parent().removeClass('text-danger').addClass('text-success');
          } else {
              $('#summary-word-count').parent().removeClass('text-success').addClass('text-danger');
          }
      });
      
      // Word counter for lessons learned
      $(document).on('input', '#lessons-learned-modern', function() {
          const text = $(this).val().trim();
          const wordCount = text ? text.split(/\s+/).filter(word => word.length > 0).length : 0;
          $('#lessons-word-count').text(wordCount);
          
          // Update styling based on word count (300 recommended)
          if (wordCount >= 300) {
              $('#lessons-word-count').parent().removeClass('text-warning').addClass('text-success');
          } else if (wordCount >= 150) {
              $('#lessons-word-count').parent().removeClass('text-success text-danger').addClass('text-warning');
          } else {
              $('#lessons-word-count').parent().removeClass('text-success text-warning').addClass('text-danger');
          }
      });
      
    // Removed unused societal-impact counter (field not rendered) to avoid dangling listeners
  }
  
  // Call initialization
  initializeAutoResize();
  
  // Initialize SDG modal functionality
  initializeSDGModal();
  
  // Populate fields with proposal data
  populateProposalData();

    // Hook: open POs/PSOs modal when clicking the relevance textarea
    $(document).on('click', '#pos-pso-modern', function(e){
        // Prevent any ancestor click handlers from treating this as a section save
        e.stopPropagation();
        e.preventDefault();
        // ensure the hidden Django form textarea mirrors this field as well
        const hidden = document.getElementById('id_pos_pso_mapping');
        if(hidden){ hidden.value = $(this).val(); }
        openOutcomeModal();
    });

  // Helper to generate placeholder summary text
  function generatePlaceholder(words = 500) {
      const corpus = [
          'lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur', 'adipiscing', 'elit',
          'sed', 'do', 'eiusmod', 'tempor', 'incididunt', 'ut', 'labore', 'et', 'dolore',
          'magna', 'aliqua', 'enim', 'ad', 'minim', 'veniam', 'quis', 'nostrud',
          'exercitation', 'ullamco', 'laboris', 'nisi', 'ut', 'aliquip', 'ex', 'ea',
          'commodo', 'consequat'
      ];
      const out = [];
  while (out.length < words) out.push(corpus[Math.floor(Math.random() * corpus.length)]);
  return out.join(' ');
}

// AI enhance summary button
$(document).on('click', '#ai-enhance-summary', function() {
      const btn = $(this);
      const original = btn.text();
      const textarea = $('#event-summary-modern');
      btn.prop('disabled', true).text('...');
      try {
          const summary = generatePlaceholder();
          textarea.val(summary);
          textarea.trigger('input');
      } catch (err) {
          console.error(err);
      } finally {
      btn.prop('disabled', false).text(original);
  }
});

function aiFill(target, words=320){
    const textarea = $(target);
    const text = generatePlaceholder(words);
    textarea.val(text);
    textarea.trigger('input');
}

$(document).on('click', '#ai-learning-outcomes', function(){
    const btn = $(this);
    const original = btn.text();
    btn.prop('disabled', true).text('...');
    try { aiFill('#learning-outcomes-modern', 80); }
    catch (err) { console.error(err); }
    finally { btn.prop('disabled', false).text(original); }
});

$(document).on('click', '#ai-participant-feedback', function(){
    const btn = $(this);
    const original = btn.text();
    btn.prop('disabled', true).text('...');
    try { aiFill('#participant-feedback-modern', 80); }
    catch (err) { console.error(err); }
    finally { btn.prop('disabled', false).text(original); }
});

$(document).on('click', '#ai-measurable-outcomes', function(){
    const btn = $(this);
    const original = btn.text();
    btn.prop('disabled', true).text('...');
    try { aiFill('#measurable-outcomes-modern', 60); }
    catch (err) { console.error(err); }
    finally { btn.prop('disabled', false).text(original); }
});

$(document).on('click', '#ai-impact-assessment', function(){
    const btn = $(this);
    const original = btn.text();
    btn.prop('disabled', true).text('...');
    try { aiFill('#impact-assessment-modern', 120); }
    catch (err) { console.error(err); }
    finally { btn.prop('disabled', false).text(original); }
});

$(document).on('click', '#ai-objective-achievement', function(){
    const btn = $(this);
    const original = btn.text();
    btn.prop('disabled', true).text('...');
    try { aiFill('#objective-achievement-modern', 320); }
    catch (err) { console.error(err); }
    finally { btn.prop('disabled', false).text(original); }
});

$(document).on('click', '#ai-strengths-analysis', function(){
    const btn = $(this);
    const original = btn.text();
    btn.prop('disabled', true).text('...');
    try { aiFill('#strengths-analysis-modern', 320); }
    catch (err) { console.error(err); }
    finally { btn.prop('disabled', false).text(original); }
});

$(document).on('click', '#ai-challenges-analysis', function(){
    const btn = $(this);
    const original = btn.text();
    btn.prop('disabled', true).text('...');
    try { aiFill('#challenges-analysis-modern', 320); }
    catch (err) { console.error(err); }
    finally { btn.prop('disabled', false).text(original); }
});

$(document).on('click', '#ai-effectiveness-analysis', function(){
    const btn = $(this);
    const original = btn.text();
    btn.prop('disabled', true).text('...');
    try { aiFill('#effectiveness-analysis-modern', 320); }
    catch (err) { console.error(err); }
    finally { btn.prop('disabled', false).text(original); }
});

$(document).on('click', '#ai-lessons-learned', function(){
    const btn = $(this);
    const original = btn.text();
    btn.prop('disabled', true).text('...');
    try { aiFill('#lessons-learned-modern', 320); }
    catch (err) { console.error(err); }
    finally { btn.prop('disabled', false).text(original); }
});

$(document).on('click', '#ai-pos-pso', function(){
    const btn = $(this);
    const original = btn.text();
    btn.prop('disabled', true).text('...');
    try { aiFill('#pos-pso-modern', 120); }
    catch (err) { console.error(err); }
    finally { btn.prop('disabled', false).text(original); }
});

$(document).on('click', '#ai-contemporary-requirements', function(){
    const btn = $(this);
    const original = btn.text();
    btn.prop('disabled', true).text('...');
    try { aiFill('#contemporary-requirements-modern', 120); }
    catch (err) { console.error(err); }
    finally { btn.prop('disabled', false).text(original); }
});

$(document).on('click', '#ai-sdg-implementation', function(){
    const btn = $(this);
    const original = btn.text();
    btn.prop('disabled', true).text('...');
    try { aiFill('#sdg-implementation-modern', 120); }
    catch (err) { console.error(err); }
    finally { btn.prop('disabled', false).text(original); }
});

  // Add validation styling to form fields with errors
  $('.field-error').each(function() {
      $(this).siblings('input, select, textarea').addClass('error');
  });
  
  // Auto-populate actual location with proposal venue if empty
  const actualLocationField = $('#actual-location-modern');
  if (actualLocationField.length && actualLocationField.val().trim() === '' && window.PROPOSAL_DATA && window.PROPOSAL_DATA.venue) {
      actualLocationField.val(window.PROPOSAL_DATA.venue);
  }
  
  // Debug: Log proposal data
  console.log('Event Report Initialization - Proposal Data:', window.PROPOSAL_DATA);
  console.log('Event Report Initialization - Activities:', window.PROPOSAL_ACTIVITIES);
  console.log('Event Report Initialization - Speakers:', window.EXISTING_SPEAKERS);
  
  // Initialize dynamic activities immediately
  setTimeout(() => {
      console.log('Initializing dynamic activities...');
      setupDynamicActivities();
  }, 100);

  // Lightweight field-level autosave for immediate DB sync of a single field
  async function postFieldAutosave(fieldName, value) {
      try {
          if (!window.AUTOSAVE_URL) return Promise.reject('No autosave URL');
          const payload = {
              proposal_id: window.PROPOSAL_ID || '',
              report_id: window.REPORT_ID || '',
          };
          payload[fieldName] = value;
          const res = await fetch(window.AUTOSAVE_URL, {
              method: 'POST',
              headers: {
                  'Content-Type': 'application/json',
                  'X-CSRFToken': window.AUTOSAVE_CSRF
              },
              credentials: 'same-origin',
              body: JSON.stringify(payload)
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok || !data.success) {
              throw new Error((data && data.error) || 'Autosave failed');
          }
          if (data.report_id && data.report_id !== window.REPORT_ID) {
              window.REPORT_ID = data.report_id;
          }
          document.dispatchEvent(new CustomEvent('autosave:success', {detail: {reportId: window.REPORT_ID}}));
          return data;
      } catch (err) {
          document.dispatchEvent(new CustomEvent('autosave:error', {detail: err}));
          throw err;
      }
  }
  
  // Navigation handling
  $('.nav-link').on('click', function(e) {
      e.preventDefault();
      const targetSection = $(this).data('section');
      
      if ($(this).hasClass('disabled')) {
          showNotification('Complete previous sections first', 'error');
          return;
      }
      
      activateSection(targetSection);
  });
  
    // Save & Continue button handling (exclude GA editor & SDG select action buttons)
    // Global Save & Continue: explicitly exclude GA editor, SDG select, SDG save, and Outcome save buttons
    $(document).on('click', '.btn-save-section:not(.btn-ga-editor):not(.btn-sdg-select):not(.btn-sdg-save):not(.btn-outcome-save)', function(e) {
      e.preventDefault();

      if (saveAndContinueInFlight) {
          return;
      }

      if (!validateCurrentSection()) {
          showNotification('Please fill in all required fields', 'error');
          return;
      }

      const $btn = $(this);
      const wasDisabled = $btn.prop('disabled');

      saveAndContinueInFlight = true;
      if (!wasDisabled) {
          $btn.prop('disabled', true);
      }

      const resetInFlightState = () => {
          saveAndContinueInFlight = false;
          if (!wasDisabled) {
              $btn.prop('disabled', false);
          }
      };

      const savePromise = autosaveThen(() => {
          markSectionComplete(currentSection);
          const nextSection = getNextSection(currentSection);

          if (nextSection) {
              enableSection(nextSection);
              activateSection(nextSection);
              showNotification('Section saved! Moving to next section', 'success');
              return false;
          }

          showNotification('All sections completed! Review your report.', 'success');
          return submitForPreview();
      });

      savePromise
          .then((submitted) => {
              if (!submitted) {
                  resetInFlightState();
              }
              return submitted;
          })
          .catch((err) => {
              resetInFlightState();
              throw err;
          });

      return savePromise;
  });

    $(document).on('click', '#review-report-btn', function(e) {
        e.preventDefault();

        if (!allSectionsCompleted()) {
            showNotification('Complete all sections before reviewing', 'error');
            return;
        }

        if (!validateCurrentSection()) {
            showNotification('Please fill in all required fields', 'error');
            return;
        }

        autosaveThen(() => {
            if (!sectionProgress[currentSection]) {
                markSectionComplete(currentSection);
            } else {
                saveProgress();
            }
            return submitForPreview();
        });
    });

    // Back navigation is handled via the navbar; no inline Previous buttons
  
  function activateSection(sectionName) {
      currentSection = sectionName;
      
      // Update navigation
      $('.nav-link').removeClass('active');
      $(`.nav-link[data-section="${sectionName}"]`).addClass('active');
      
      // Update content
      loadSectionContent(sectionName);
    // Persist last active section
    saveProgress();
  }
  
  function loadSectionContent(sectionName) {
      const sectionData = getSectionData(sectionName);
      $('#main-title').text(sectionData.title);
      $('#main-subtitle').text(sectionData.subtitle);
      
      let content = '';
      switch (sectionName) {
          case 'event-information':
              content = getEventInformationContent();
              break;
          case 'participants-information':
              content = getParticipantsInformationContent();
              break;
          case 'event-summary':
              content = getEventSummaryContent();
              break;
          case 'event-outcomes':
              content = getEventOutcomesContent();
              break;
          case 'analysis':
              content = getAnalysisContent();
              break;
          case 'event-relevance':
              content = getEventRelevanceContent();
              break;
          case 'attachments':
              content = getAttachmentsContent();
              break;
          default:
              content = getEventInformationContent();
      }

      $('.form-grid').html(content);

      if (sectionName === 'attachments') {
          setTimeout(() => initAttachments(), 50);
      }

      if (sectionName === 'participants-information') {
          // Defer population until after the new DOM elements are attached, with retries
          const initParticipantsSection = (attempt=0) => {
              const container = document.getElementById('speakers-display');
              if (!container && attempt < 10) {
                  return setTimeout(() => initParticipantsSection(attempt+1), 100);
              }
              populateSpeakersFromProposal();
              fillOrganizingCommittee();
              fillAttendanceCounts();
              if (typeof setupAttendanceLink === 'function') setupAttendanceLink();
          };
          setTimeout(() => initParticipantsSection(0), 50);
      }

          if (sectionName === 'event-relevance') {
              fillEventRelevance();
          }

      if (sectionName === 'event-information') {
          // Initialize activities after content is loaded
          setTimeout(() => {
              setupDynamicActivities();
          }, 100);
      }

      // Restore field values if switching back to a section
      setTimeout(() => {
          restoreFieldValues(sectionName);
          if (window.ReportAutosaveManager) {
              ReportAutosaveManager.reinitialize();
          }
      }, 100);
  }
  
  function getSectionData(section) {
      const sections = {
          'event-information': { 
              title: 'Event Information', 
              subtitle: 'Basic event details fetched from proposal' 
          },
          'participants-information': { 
              title: 'Participants Information', 
              subtitle: 'Attendees, speakers, organizing committee details' 
          },
          'event-summary': { 
              title: 'Summary of Overall Event', 
              subtitle: 'Comprehensive event overview (minimum 500 words)' 
          },
          'event-outcomes': { 
              title: 'Outcomes of the Event', 
              subtitle: 'Post-event evaluation and achievements' 
          },
          'analysis': {
              title: 'Analysis',
              subtitle: 'Detailed analysis and insights (minimum 500 words)'
          },
          'event-relevance': {
              title: 'Relevance of the Event',
              subtitle: 'Program outcomes, graduate attributes, SDGs mapping'
          },
          'attachments': {
              title: 'Attachments & Evidence',
              subtitle: 'Upload photos, certificates, and other supporting files'
          },
          'suggestions': {
              title: 'Suggestions for Improvements',
              subtitle: 'IQAC coordinator feedback and recommendations'
          }
      };
      return sections[section] || { title: 'Section', subtitle: 'Complete this section' };
  }
  
    function getNextSection(current) {
        const currentIndex = SECTION_SEQUENCE.indexOf(current);
        if (currentIndex === -1) {
            return null;
        }
        return currentIndex < SECTION_SEQUENCE.length - 1
            ? SECTION_SEQUENCE[currentIndex + 1]
            : null;
  }

        // getPreviousSection removed; navbar permits free navigation to unlocked sections
  
  function validateCurrentSection() {
      if (currentSection === 'event-information') {
          return validateEventInformation();
      } else if (currentSection === 'participants-information') {
          return validateParticipantsInformation();
      } else if (currentSection === 'event-summary') {
          return validateEventSummary();
      } else if (currentSection === 'event-outcomes') {
          return validateEventOutcomes();
      } else if (currentSection === 'analysis') {
          return validateAnalysis();
      } else if (currentSection === 'event-relevance') {
          return validateEventRelevance();
      } else if (currentSection === 'attachments') {
          return validateAttachments();
      }
      // Add other section validations as needed
      return true;
  }
  
  function validateEventInformation() {
      let isValid = true;
      const eventType = $('#event-type-modern');
      
      if (!eventType.val() || eventType.val().trim() === '') {
          showFieldError(eventType, 'Event Type is required');
          isValid = false;
      } else {
          clearFieldError(eventType);
      }
      
      return isValid;
  }
  
  function validateParticipantsInformation() {
      let isValid = true;
      const requiredFields = [
          { id: '#total-participants-modern', name: 'Total Participants' },
          { id: '#organizing-committee-modern', name: 'Organizing Committee' }
      ];
      
      requiredFields.forEach(function(field) {
          const element = $(field.id);
          if (!element.val() || element.val().trim() === '') {
              showFieldError(element, field.name + ' is required');
              isValid = false;
          } else {
              clearFieldError(element);
          }
      });
      
      return isValid;
  }
  
  function validateEventSummary() {
      let isValid = true;
      const summaryField = $('#event-summary-modern');
      const summary = summaryField.val().trim();
      const wordCount = summary ? summary.split(/\s+/).filter(word => word.length > 0).length : 0;
      
      if (!summary) {
          showFieldError(summaryField, 'Event Summary is required');
          isValid = false;
      } else if (wordCount < 500) {
          showFieldError(summaryField, `Event Summary must be at least 500 words (current: ${wordCount} words)`);
          isValid = false;
      } else {
          clearFieldError(summaryField);
      }
      
      return isValid;
  }
  
  function validateEventOutcomes() {
      let isValid = true;
      const requiredFields = [
          { id: '#learning-outcomes-modern', name: 'Learning Outcomes' },
          { id: '#participant-feedback-modern', name: 'Participant Feedback' },
          { id: '#measurable-outcomes-modern', name: 'Measurable Outcomes' },
          { id: '#impact-assessment-modern', name: 'Impact Assessment' }
      ];
      
      requiredFields.forEach(function(field) {
          const element = $(field.id);
          if (!element.val() || element.val().trim() === '') {
              showFieldError(element, field.name + ' is required');
              isValid = false;
          } else {
              clearFieldError(element);
          }
      });
      
      return isValid;
  }
  
  function validateAnalysis() {
      let isValid = true;
      const requiredFields = [
          { id: '#objective-achievement-modern', name: 'Objective Achievement Analysis' },
          { id: '#strengths-analysis-modern', name: 'Strengths and Successes' },
          { id: '#challenges-analysis-modern', name: 'Challenges and Areas for Improvement' },
          { id: '#effectiveness-analysis-modern', name: 'Overall Effectiveness Analysis' },
          { id: '#lessons-learned-modern', name: 'Lessons Learned and Insights' }
      ];
      
      requiredFields.forEach(function(field) {
          const element = $(field.id);
          if (!element.val() || element.val().trim() === '') {
              showFieldError(element, field.name + ' is required');
              isValid = false;
          } else {
              clearFieldError(element);
          }
      });
      
      return isValid;
  }
  
  function validateEventRelevance() {
      let isValid = true;
      const requiredFields = [
          { id: '#pos-pso-modern', name: "PO's and PSO's Management" },
          { id: '#graduate-attributes-modern', name: 'Graduate Attributes' },
          { id: '#contemporary-requirements-modern', name: 'Contemporary Requirements' },
          { id: '#sdg-implementation-modern', name: 'SDG Implementation' }
      ];

      requiredFields.forEach(function(field) {
          const element = $(field.id);
          if (field.id !== '#graduate-attributes-modern') {
              // For textarea and input fields
              if (!element.val() || element.val().trim() === '') {
                  showFieldError(element, field.name + ' is required');
                  isValid = false;
              } else {
                  clearFieldError(element);
              }
          } else {
              // For GA, rely on hidden Django field or summary content if present
              const hidden = document.getElementById('id_needs_grad_attr_mapping');
              const hasValue = hidden ? (hidden.value && hidden.value.trim() !== '') : (element.text().trim() !== '');
              if (!hasValue) {
                  showFieldError(element, field.name + ' - Please select at least one attribute');
                  isValid = false;
              } else {
                  clearFieldError(element);
              }
          }
      });

      return isValid;
  }

  function validateAttachments() {
      return true;
  }

  function markSectionComplete(sectionName) {
      sectionProgress[sectionName] = true;
      $(`.nav-link[data-section="${sectionName}"]`).addClass('completed');
      if (allSectionsCompleted()) {
          enableFinalSubmission();
      }
    // Persist progress on each completion
    saveProgress();
  }

  function allSectionsCompleted(){
      return SECTION_SEQUENCE.every(section => Boolean(sectionProgress[section]));
  }

  function enableFinalSubmission(){
      const submitSection = document.querySelector('.submit-section');
      if(submitSection){
          submitSection.classList.remove('hidden');
      }
      const btn = document.getElementById('submit-report-btn');
      if(btn){ btn.disabled = false; }
      const reviewBtn = document.getElementById('review-report-btn');
      if(reviewBtn){ reviewBtn.disabled = false; }
  }
  
  function enableSection(sectionName) {
      $(`.nav-link[data-section="${sectionName}"]`).removeClass('disabled');
  }
  
  function restoreFieldValues(sectionName) {
      // Reapply stored values for inputs & textareas present in current section
      const container = document.querySelector('.form-grid');
      if(!container) return;
      container.querySelectorAll('input[name], textarea[name], select[name]').forEach(el => {
          const key = el.name;
          if(sectionState.hasOwnProperty(key)){
              if(el.tagName === 'SELECT' && el.multiple && Array.isArray(sectionState[key])){
                  Array.from(el.options).forEach(o => { o.selected = sectionState[key].includes(o.value); });
              } else if(el.type === 'checkbox') {
                  el.checked = Array.isArray(sectionState[key]) ? sectionState[key].includes(el.value) : sectionState[key] === el.value;
              } else {
                  el.value = sectionState[key];
              }
          }
      });
  }

  // Persist field changes (delegated)
  $(document).on('input change', 'input[name], textarea[name], select[name]', function(){
      const el = this;
      if(el.tagName === 'SELECT' && el.multiple){
          sectionState[el.name] = Array.from(el.selectedOptions).map(o => o.value);
      } else if(el.type === 'checkbox') {
          const checked = Array.from(document.querySelectorAll(`input[name="${el.name}"]:checked`)).map(cb => cb.value);
          sectionState[el.name] = checked;
      } else if(el.type === 'radio') {
          if(el.checked) sectionState[el.name] = el.value;
      } else {
          sectionState[el.name] = el.value;
      }
  });

  // Initial snapshot of any server-rendered fields
  document.querySelectorAll('form#report-form input[name], form#report-form textarea[name], form#report-form select[name]').forEach(el => {
      if(el.tagName === 'SELECT' && el.multiple){
          sectionState[el.name] = Array.from(el.selectedOptions).map(o => o.value);
      } else if(el.type === 'checkbox') {
          if(!sectionState[el.name]) sectionState[el.name] = [];
          if(el.checked) sectionState[el.name].push(el.value);
      } else if(el.type === 'radio') {
          if(el.checked) sectionState[el.name] = el.value;
      } else {
          sectionState[el.name] = el.value;
      }
  });

    // GA inline controls removed; use dedicated editor

  function getEventInformationContent() {
      const eventTypeValue = window.REPORT_ACTUAL_EVENT_TYPE || (window.PROPOSAL_DATA ? window.PROPOSAL_DATA.event_focus_type || '' : '');
      return `
          <!-- Organization Information Section -->
          <div class="form-section-header">
              <h3>Organization Details</h3>
          </div>
          
          <div class="form-row">
              <div class="input-group">
                  <label for="department-modern">Department *</label>
                  <input type="text" id="department-modern" name="department" value="${window.PROPOSAL_DATA ? window.PROPOSAL_DATA.department || '' : ''}">
                  <div class="help-text">Department from original proposal (editable)</div>
              </div>
              <div class="input-group">
                  <label for="location-modern">Venue/Location *</label>
                  <input type="text" id="location-modern" name="venue" value="${window.PROPOSAL_DATA ? window.PROPOSAL_DATA.venue || '' : ''}">
                  <div class="help-text">Venue from original proposal (editable)</div>
              </div>
          </div>

          <!-- Event Information Section -->
          <div class="form-section-header">
              <h3>Event Information</h3>
          </div>

          <div class="form-row full-width">
              <div class="input-group">
                  <label for="event-title-modern">Event Title *</label>
                  <input type="text" id="event-title-modern" name="event_title" value="${window.PROPOSAL_DATA ? window.PROPOSAL_DATA.title || '' : ''}">
                  <div class="help-text">Event title from proposal (editable)</div>
              </div>
          </div>

          <div class="form-row">
              <div class="input-group">
                  <label for="num-activities-modern">Number of Activities</label>
                  <input type="number" id="num-activities-modern" name="num_activities" value="${window.PROPOSAL_DATA ? window.PROPOSAL_DATA.num_activities || 1 : 1}">
                  <div class="help-text">Total activities from proposal (editable)</div>
              </div>
              <div class="input-group">
                  <label for="venue-modern">Venue *</label>
                  <input type="text" id="venue-modern" name="venue_detail" value="${window.PROPOSAL_DATA ? window.PROPOSAL_DATA.venue || '' : ''}">
                  <div class="help-text">Venue from proposal (editable)</div>
              </div>
          </div>

          <!-- Schedule & Academic Information Section -->
          <div class="form-section-header">
              <h3>Schedule & Academic Information</h3>
          </div>

          <div class="form-row">
              <div class="input-group">
                  <label for="start-date-modern">Event Start Date *</label>
                  <input type="date" id="start-date-modern" name="event_start_date" value="${window.PROPOSAL_DATA ? window.PROPOSAL_DATA.event_start_date || '' : ''}">
                  <div class="help-text">Start date from original proposal (editable)</div>
              </div>
              <div class="input-group">
                  <label for="end-date-modern">Event End Date *</label>
                  <input type="date" id="end-date-modern" name="event_end_date" value="${window.PROPOSAL_DATA ? window.PROPOSAL_DATA.event_end_date || '' : ''}">
                  <div class="help-text">End date from original proposal (editable)</div>
              </div>
          </div>

          <div class="form-row">
              <div class="input-group">
                  <label for="academic-year-modern">Academic Year *</label>
                  <input type="text" id="academic-year-modern" value="${window.PROPOSAL_DATA ? window.PROPOSAL_DATA.academic_year || '2024-2025' : '2024-2025'}" disabled>
                  <input type="hidden" name="academic_year" value="${window.PROPOSAL_DATA ? window.PROPOSAL_DATA.academic_year || '2024-2025' : '2024-2025'}">
                  <div class="help-text">Academic year from proposal (not editable)</div>
              </div>
              <div class="input-group">
                  <label for="event-type-modern">Event Type *</label>
                  <input type="text" id="event-type-modern" name="actual_event_type" value="${eventTypeValue}" readonly>
                  <div class="help-text">Event type from proposal (not editable)</div>
              </div>
          </div>

          <!-- Activities Section -->
          <div class="form-section-header">
              <h3>Event Activities</h3>
          </div>

          <!-- Dynamic activities section -->
          <div id="dynamic-activities-section" class="full-width"></div>

          <!-- Additional Information Section -->
          <div class="form-section-header">
              <h3>Additional Information</h3>
          </div>

          <div class="form-row">
              <div class="input-group">
                  <label for="actual-location-modern">Actual Event Location</label>
                  <input type="text" id="actual-location-modern" name="location" placeholder="Enter the actual venue where event was held">
                  <div class="help-text">Specify the actual venue (if different from proposed venue)</div>
              </div>
              <div class="input-group">
                  <label for="blog-link-modern">Blog Link</label>
                  <input type="url" id="blog-link-modern" name="blog_link" placeholder="https://example.com/blog-post">
                  <div class="help-text">Optional: Link to blog post or article about the event</div>
              </div>
          </div>

          <div class="form-row">
              <div class="input-group">
                  <label for="num-participants-modern">Number of Participants</label>
                  <input type="number" id="num-participants-modern" name="num_participants" min="0" placeholder="Enter total participants">
                  <div class="help-text">Total number of people who attended the event</div>
              </div>
              <div class="input-group">
                  <label for="num-volunteers-modern">Number of Student Volunteers</label>
                  <input type="number" id="num-volunteers-modern" name="num_student_volunteers" min="0" placeholder="Enter volunteer count">
                  <div class="help-text">Number of students who volunteered for the event</div>
              </div>
          </div>

          <!-- Save Section -->
          <div class="form-row full-width">
              <div class="save-section-container" style="display: flex; flex-direction: column; align-items: center;">
                  <button type="button" class="btn-save-section" style="margin-bottom: 0.5rem;">Save & Continue</button>
                  <div class="save-help-text" style="margin-top: 0.75rem;">Complete this section to unlock the next one</div>
              </div>
          </div>
      `;
  }
  
  function getParticipantsInformationContent() {
      return `
          <!-- Attendance Information Section -->
          <div class="form-section-header">
              <h3>Attendance Information</h3>
          </div>
          
          <div class="form-row">
              <div class="input-group">
                  <label for="total-participants-modern">Total Participants *</label>
                  <input type="number" id="total-participants-modern" name="num_participants" min="0" required placeholder="Enter total number of attendees">
                  <div class="help-text">Total number of people who attended the event</div>
              </div>
              <div class="input-group">
                  <label for="student-participants-modern">Student Participants</label>
                  <input type="number" id="student-participants-modern" name="num_student_participants" min="0" placeholder="Enter number of students">
                  <div class="help-text">Number of students who participated in the event</div>
              </div>
          </div>

          <div class="form-row">
              <div class="input-group">
                  <label for="faculty-participants-modern">Faculty Participants</label>
                  <input type="number" id="faculty-participants-modern" name="num_faculty_participants" min="0" placeholder="Enter number of faculty">
                  <div class="help-text">Number of faculty members who participated</div>
              </div>
              <div class="input-group">
                  <label for="external-participants-modern">External Participants</label>
                  <input type="number" id="external-participants-modern" name="num_external_participants" min="0" placeholder="Enter number of external participants">
                  <div class="help-text">Number of external participants (industry, other institutions)</div>
              </div>
          </div>

          <!-- Organizing Committee Section -->
          <div class="form-section-header">
              <h3>Organizing Committee</h3>
          </div>
          
          <div class="form-row full-width">
              <div class="input-group">
                  <label for="organizing-committee-modern">Organizing Committee Details *</label>
                  <textarea id="organizing-committee-modern" name="organizing_committee" rows="8" required 
                      placeholder="List the organizing committee members with their roles:&#10;&#10;• Convener: Dr. [Name] - [Department]&#10;• Co-Convener: Prof. [Name] - [Department]&#10;• Student Coordinators: [Names] - [Details]&#10;• Volunteers: [Names and roles]&#10;&#10;Provide details about each member's contribution to the event organization."></textarea>
                  <div class="help-text">Detail the organizing committee structure and member contributions</div>
              </div>
          </div>

          <!-- Speaker Information Section -->
          <div class="form-section-header">
              <h3>Speaker Information</h3>
          </div>

          <div class="form-row full-width">
              <div class="input-group">
                  <label>Speakers from Original Proposal</label>
                  <div class="speakers-reference-card">
                      <div id="speakers-display">
                          <!-- Speakers will be populated here from proposal data -->
                      </div>
                  </div>
                  <div class="help-text">Reference: Speakers planned in the original proposal</div>
              </div>
          </div>

          <!-- Save Section -->
          <div class="form-row full-width">
              <div class="save-section-container">
                  <button type="button" class="btn-save-section">Save & Continue</button>
                  <div class="save-help-text">Complete this section to unlock the next one</div>
              </div>
          </div>
      `;
  }
  
  function getEventSummaryContent() {
      return `
          <!-- Event Summary Section -->
          <div class="form-section-header">
              <h3>Event Summary</h3>
          </div>
          
          <div class="form-row full-width">
              <div class="input-group ai-input">
                  <label for="event-summary-modern">Summary of Overall Event *</label>
                  <textarea id="event-summary-modern" name="event_summary" rows="15" required
                      placeholder="Provide a comprehensive summary of the event (minimum 500 words):&#10;&#10;• Event overview and objectives&#10;• Key activities and sessions conducted&#10;• Timeline and schedule of events&#10;• Participant engagement and interaction&#10;• Key highlights and memorable moments&#10;• Overall atmosphere and reception&#10;• Achievement of planned objectives&#10;• Any unexpected outcomes or learnings&#10;&#10;This should be a detailed narrative that captures the essence of the entire event."></textarea>
                  <button type="button" id="ai-enhance-summary" class="ai-fill-btn" title="Enhance with AI">AI</button>
                  <div class="help-text">
                      Comprehensive overview of the event - minimum 500 words required
                      <span class="word-counter text-danger">
                          Word count: <span id="summary-word-count">0</span> / 500 minimum
                      </span>
                  </div>
              </div>
          </div>

          <!-- Event Highlights Section -->
          <div class="form-section-header">
              <h3>Key Highlights</h3>
          </div>

          <div class="form-row">
              <div class="input-group">
                  <label for="key-achievements-modern">Key Achievements</label>
                  <textarea id="key-achievements-modern" name="key_achievements" rows="6" 
                      placeholder="List the major achievements and successes:&#10;&#10;• [Achievement 1]&#10;• [Achievement 2]&#10;• [Achievement 3]&#10;&#10;Focus on measurable outcomes and significant accomplishments."></textarea>
                  <div class="help-text">Major achievements and successes of the event</div>
              </div>
              <div class="input-group">
                  <label for="notable-moments-modern">Notable Moments</label>
                  <textarea id="notable-moments-modern" name="notable_moments" rows="6" 
                      placeholder="Describe memorable and significant moments:&#10;&#10;• [Notable moment 1]&#10;• [Notable moment 2]&#10;• [Notable moment 3]&#10;&#10;Include moments that had significant impact on participants."></textarea>
                  <div class="help-text">Memorable moments and significant highlights</div>
              </div>
          </div>

          <!-- Save Section -->
          <div class="form-row full-width">
              <div class="save-section-container">
                  <button type="button" class="btn-save-section">Save & Continue</button>
                  <div class="save-help-text">Complete this section to unlock the next one</div>
              </div>
          </div>
      `;
  }
  
  function getEventOutcomesContent() {
      return `
          <!-- Learning Outcomes Section -->
          <div class="form-section-header">
              <h3>Learning Outcomes</h3>
          </div>

          <div class="form-row full-width">
              <div class="input-group ai-input">
                  <label for="learning-outcomes-modern">Learning Outcomes Achieved *</label>
                  <textarea id="learning-outcomes-modern" name="learning_outcomes" rows="8" required
                      placeholder="Describe the learning outcomes achieved by participants:&#10;&#10;• Knowledge gained: [Specific knowledge areas]&#10;• Skills developed: [Technical and soft skills]&#10;• Competencies enhanced: [Professional competencies]&#10;• Understanding improved: [Subject areas or concepts]&#10;&#10;Be specific about what participants learned and how it benefits them."></textarea>
                  <button type="button" id="ai-learning-outcomes" class="ai-fill-btn" title="Fill with AI">AI</button>
                  <div class="help-text">Detail the specific learning outcomes achieved by participants</div>
              </div>
          </div>

          <!-- Feedback and Assessment Section -->
          <div class="form-section-header">
              <h3>Feedback and Assessment</h3>
          </div>

          <div class="form-row">
              <div class="input-group ai-input">
                  <label for="participant-feedback-modern">Participant Feedback *</label>
                  <textarea id="participant-feedback-modern" name="participant_feedback" rows="8" required
                      placeholder="Summarize participant feedback:&#10;&#10;• Overall satisfaction rating: [X/10 or percentage]&#10;• Content quality feedback: [Summary]&#10;• Organization feedback: [Summary]&#10;• Suggestions received: [Key suggestions]&#10;• Testimonials: [Notable quotes]&#10;&#10;Include both quantitative and qualitative feedback."></textarea>
                  <button type="button" id="ai-participant-feedback" class="ai-fill-btn" title="Fill with AI">AI</button>
                  <div class="help-text">Summary of participant feedback and satisfaction</div>
              </div>
              <div class="input-group ai-input">
                  <label for="measurable-outcomes-modern">Measurable Outcomes *</label>
                  <textarea id="measurable-outcomes-modern" name="measurable_outcomes" rows="8" required
                      placeholder="List quantifiable outcomes:&#10;&#10;• Attendance rate: [X% of expected participants]&#10;• Completion rate: [X% completed full program]&#10;• Assessment scores: [If applicable]&#10;• Certification issued: [Number of certificates]&#10;• Follow-up actions: [Concrete next steps]&#10;&#10;Focus on measurable and quantifiable results."></textarea>
                  <button type="button" id="ai-measurable-outcomes" class="ai-fill-btn" title="Fill with AI">AI</button>
                  <div class="help-text">Quantifiable and measurable outcomes from the event</div>
              </div>
          </div>

          <!-- Impact Assessment Section -->
          <div class="form-section-header">
              <h3>Impact Assessment</h3>
          </div>

          <div class="form-row full-width">
              <div class="input-group ai-input">
                  <label for="impact-assessment-modern">Short-term and Long-term Impact *</label>
                  <textarea id="impact-assessment-modern" name="impact_assessment" rows="10" required
                      placeholder="Assess the impact of the event:&#10;&#10;Short-term Impact:&#10;• Immediate learning and awareness gains&#10;• Networking connections established&#10;• Skills immediately applicable&#10;&#10;Long-term Impact:&#10;• Career development opportunities&#10;• Research collaborations initiated&#10;• Behavioral changes expected&#10;• Contribution to academic/professional growth&#10;&#10;Provide evidence-based assessment where possible."></textarea>
                  <button type="button" id="ai-impact-assessment" class="ai-fill-btn" title="Fill with AI">AI</button>
                  <div class="help-text">Assess both immediate and long-term impact on participants and institution</div>
              </div>
          </div>

          <!-- Save Section -->
          <div class="form-row full-width">
              <div class="save-section-container">
                  <button type="button" class="btn-save-section">Save & Continue</button>
                  <div class="save-help-text">Complete this section to unlock the next one</div>
              </div>
          </div>
      `;
  }
  
  function getAnalysisContent() {
      return `
          <!-- Objective Achievement Analysis Section -->
          <div class="form-section-header">
              <h3>Objective Achievement Analysis</h3>
          </div>
          
          <div class="form-row full-width">
              <div class="input-group ai-input">
                  <label for="objective-achievement-modern">Achievement of Planned Objectives *</label>
                  <textarea id="objective-achievement-modern" name="objective_achievement" rows="10" required
                      placeholder="Analyze how well the event achieved its planned objectives:&#10;&#10;Original Objectives:&#10;• Objective 1: [Status - Fully/Partially/Not Achieved]&#10;  Analysis: [Detailed explanation]&#10;&#10;• Objective 2: [Status - Fully/Partially/Not Achieved]&#10;  Analysis: [Detailed explanation]&#10;&#10;Overall Achievement Rate: [X%]&#10;Factors contributing to success/challenges: [Analysis]"></textarea>
                  <button type="button" id="ai-objective-achievement" class="ai-fill-btn" title="Fill with AI">AI</button>
                  <div class="help-text">Detailed analysis of how well planned objectives were achieved</div>
              </div>
          </div>

          <!-- Strengths and Challenges Analysis Section -->
          <div class="form-section-header">
              <h3>Strengths and Challenges Analysis</h3>
          </div>

          <div class="form-row">
              <div class="input-group ai-input">
                  <label for="strengths-analysis-modern">Strengths and Successes *</label>
                  <textarea id="strengths-analysis-modern" name="strengths_analysis" rows="8" required
                      placeholder="Identify and analyze the key strengths:&#10;&#10;• Organizational strengths: [What worked well in planning/execution]&#10;• Content strengths: [Quality of sessions, speakers, materials]&#10;• Participant engagement: [What kept participants engaged]&#10;• Infrastructure/logistics: [What supported the event well]&#10;• Team collaboration: [How the team worked effectively]&#10;&#10;Provide specific examples and evidence."></textarea>
                  <button type="button" id="ai-strengths-analysis" class="ai-fill-btn" title="Fill with AI">AI</button>
                  <div class="help-text">Analyze what worked well and contributed to success</div>
              </div>
              <div class="input-group ai-input">
                  <label for="challenges-analysis-modern">Challenges and Areas for Improvement *</label>
                  <textarea id="challenges-analysis-modern" name="challenges_analysis" rows="8" required
                      placeholder="Identify challenges faced and areas for improvement:&#10;&#10;• Organizational challenges: [Planning, coordination issues]&#10;• Technical challenges: [Equipment, platform, connectivity]&#10;• Participant-related challenges: [Attendance, engagement]&#10;• Content/delivery challenges: [Session quality, timing]&#10;• Resource constraints: [Budget, time, personnel]&#10;&#10;For each challenge, suggest specific improvements."></textarea>
                  <button type="button" id="ai-challenges-analysis" class="ai-fill-btn" title="Fill with AI">AI</button>
                  <div class="help-text">Honest assessment of challenges and improvement opportunities</div>
              </div>
          </div>

          <!-- Effectiveness Analysis Section -->
          <div class="form-section-header">
              <h3>Effectiveness Analysis</h3>
          </div>

          <div class="form-row full-width">
              <div class="input-group ai-input">
                  <label for="effectiveness-analysis-modern">Overall Effectiveness Analysis *</label>
                  <textarea id="effectiveness-analysis-modern" name="effectiveness_analysis" rows="10" required
                      placeholder="Provide a comprehensive effectiveness analysis:&#10;&#10;Methodology Used:&#10;• Data collection methods: [Surveys, interviews, observations]&#10;• Metrics evaluated: [Attendance, satisfaction, learning gains]&#10;&#10;Effectiveness Rating: [X/10 or percentage]&#10;&#10;Key Findings:&#10;• Most effective aspects: [What worked exceptionally well]&#10;• Least effective aspects: [What needs significant improvement]&#10;• Unexpected findings: [Surprising results or outcomes]&#10;&#10;Evidence-based analysis with specific data points where available."></textarea>
                  <button type="button" id="ai-effectiveness-analysis" class="ai-fill-btn" title="Fill with AI">AI</button>
                  <div class="help-text">Comprehensive analysis of event effectiveness with supporting evidence</div>
              </div>
          </div>

          <!-- Lessons Learned Section -->
          <div class="form-section-header">
              <h3>Lessons Learned and Insights</h3>
          </div>

          <div class="form-row full-width">
              <div class="input-group ai-input">
                  <label for="lessons-learned-modern">Lessons Learned and Future Insights *</label>
                  <textarea id="lessons-learned-modern" name="lessons_learned" rows="10" required
                      placeholder="Document key lessons learned and insights for future events:&#10;&#10;Key Lessons Learned:&#10;• Planning phase: [What to do differently in planning]&#10;• Execution phase: [What to improve in delivery]&#10;• Participant management: [Better engagement strategies]&#10;• Resource management: [More efficient resource utilization]&#10;&#10;Actionable Insights:&#10;• Best practices to replicate: [Successful strategies to repeat]&#10;• Practices to avoid: [What didn't work and should be avoided]&#10;• Innovation opportunities: [New approaches to try]&#10;&#10;Recommendations for future similar events."></textarea>
                  <button type="button" id="ai-lessons-learned" class="ai-fill-btn" title="Fill with AI">AI</button>
                  <div class="help-text">
                      Key lessons and insights for future improvement - minimum 300 words recommended
                      <span class="word-counter text-danger">
                          Word count: <span id="lessons-word-count">0</span> / 300 recommended
                      </span>
                  </div>
              </div>
          </div>

          <!-- Save Section -->
          <div class="form-row full-width">
              <div class="save-section-container">
                  <button type="button" class="btn-save-section">Save & Continue</button>
                  <div class="save-help-text">Complete this section to unlock the next one</div>
              </div>
          </div>
      `;
  }
  
  function getEventRelevanceContent() {
      return `
          <!-- POs and PSOs Section -->
          <div class="form-section-header">
              <h3>Program Outcomes & Program Specific Outcomes</h3>
          </div>
          
          <div class="form-row full-width">
              <div class="input-group ai-input">
                  <label for="pos-pso-modern">PO's and PSO's Management *</label>
                  <textarea id="pos-pso-modern" name="pos_pso_mapping" rows="15" required
                      placeholder="Describe how the event addresses Program Outcomes (POs) and Program Specific Outcomes (PSOs):&#10;&#10;Program Outcomes:&#10;• PO1: Engineering Knowledge&#10;• PO2: Problem Analysis&#10;• PO3: Design/Development of Solutions&#10;&#10;Program Specific Outcomes:&#10;• PSO1: [Specific to your program]&#10;• PSO2: [Specific to your program]&#10;&#10;Provide detailed explanation of how each relevant outcome was addressed through this event."></textarea>
                  <button type="button" id="ai-pos-pso" class="ai-fill-btn" title="Fill with AI">AI</button>
                  <div class="help-text">Detail how the event contributes to achieving specific program outcomes</div>
              </div>
          </div>

          <!-- Graduate Attributes Section (summary only, open dedicated editor) -->
          <div class="form-section-header">
              <h3>Graduate Attributes & Contemporary Requirements</h3>
          </div>
          
          <div class="form-row full-width">
              <div class="input-group">
                  <label for="graduate-attributes-modern" style="display:flex;align-items:center;gap:8px;width:100%;">
                      <span>Graduate Attributes *</span>
                      <span style="flex:1 1 auto"></span>
                      <button type="button" id="ga-open-editor-btn" class="btn-ga-editor ga-editor-btn" title="Open dedicated GA editor" style="margin-left:auto;width:auto;">Open GA Editor</button>
                  </label>
                  <div id="graduate-attributes-modern" class="graduate-attributes-groups" style="min-height: 48px;">
                      <div id="ga-summary" class="help-text" data-empty-text="Open the Graduate Attributes editor to select attributes. Your selections will be saved back to this report.">Open the Graduate Attributes editor to select attributes. Your selections will be saved back to this report.</div>
                  </div>
              </div>
          </div>
          
          <div class="form-row">
              <div class="input-group ai-input">
                  <label for="contemporary-requirements-modern">Contemporary Requirements *</label>
                  <textarea id="contemporary-requirements-modern" name="contemporary_requirements" rows="12" required
                      placeholder="Describe how the event addresses contemporary requirements:&#10;&#10;• Employability enhancement&#10;• Entrepreneurship development&#10;• Skill development initiatives&#10;• Industry 4.0 readiness&#10;• Digital transformation skills&#10;• Innovation and creativity&#10;• Leadership and soft skills&#10;• Global competency development&#10;&#10;Provide specific examples of how these requirements were addressed."></textarea>
                  <button type="button" id="ai-contemporary-requirements" class="ai-fill-btn" title="Fill with AI">AI</button>
                  <div class="help-text">Explain how the event addresses employability, entrepreneurship, skill development, etc.</div>
              </div>

              <div class="input-group ai-input">
                  <label for="sdg-implementation-modern">SDG Implementation *</label>
                  <textarea id="sdg-implementation-modern" name="sdg_value_systems_mapping" rows="10" required
                      placeholder="Click 'Select SDG Goals' to choose from the 17 Sustainable Development Goals&#10;&#10;Selected goals will appear here and can be edited:&#10;&#10;You can modify the SDG selection or add additional context about how your event addresses these goals."></textarea>
                  <button type="button" id="ai-sdg-implementation" class="ai-fill-btn" title="Fill with AI">AI</button>
                  <button type="button" id="sdg-select-btn" class="btn-sdg-select sdg-select-btn" style="background:var(--primary-blue);">Select SDG Goals</button>
                  <div class="help-text">Sustainable Development Goals addressed by this event (editable)</div>
              </div>
          </div>

          <!-- Save Section -->
          <div class="form-row full-width">
          <div class="save-section-container">
              <button type="button" class="btn-save-section">Save & Continue</button>
              <div class="save-help-text">Complete this section to unlock the next one</div>
          </div>
      </div>
  `;
}

  function getAttachmentsContent() {
      const tpl = document.getElementById('attachments-section-template');
      if (!tpl) {
          return `
              <div class="form-row full-width">
                  <div class="help-text">Attachments section unavailable. Please reload the page.</div>
              </div>
          `;
      }

      return tpl.innerHTML.trim();
  }

  // Form submission validation
  $('#report-form').on('submit', function(e) {
      // Validate current and ensure all sections complete before final submit
      if (!validateCurrentSection()) {
          e.preventDefault();
          showNotification('Please fill in all required fields in this section', 'error');
          return;
      }
      if(!allSectionsCompleted()) {
          e.preventDefault();
          showNotification('Complete all sections before submitting', 'error');
      }
  });
  
  // Clear field errors on input
  $(document).on('input change', 'input, select, textarea', function() {
      clearFieldError($(this));
  });
});

function showFieldError(field, message) {
    clearFieldError(field);
    field.addClass('error');
    field.after(`<div class="field-error">${message}</div>`);
}

// Restore GA expand/collapse state
function restoreGAExpandState(){
    const $container = $('#graduate-attributes-modern');
    if (!$container.length) return;
    // Determine any categories flagged as open earlier via data attribute matches
    const openKeys = new Set();
    // Read keys from the Set stored in closure if available via data attr fallback
    // We store it on window to access here (outside main closure)
    const globalKeys = window.__GA_EXPAND_KEYS__;
    if (Array.isArray(globalKeys)) {
        globalKeys.forEach(k => openKeys.add(String(k)));
    }
    $container.find('.ga-category').each(function(){
        const key = String($(this).data('cat') || '');
        if (openKeys.has(key)) {
            $(this).addClass('open');
            $(this).children('.ga-options').show();
        }
    });
    if ($container.find('.ga-category.open').length) {
        $container.addClass('ga-expanded');
    } else {
        $container.removeClass('ga-expanded');
    }
}

function clearFieldError(field) {
    field.removeClass('error');
    field.siblings('.field-error').remove();
}

function showNotification(message, type = 'info') {
    // Simple notification system
    const notification = $(`
        <div class="notification ${type}" style="
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem;
            background: ${type === 'error' ? '#dc2626' : '#059669'};
            color: white;
            border-radius: 0.5rem;
            z-index: 1000;
            max-width: 300px;
        ">
            ${message}
        </div>
    `);
    
    $('body').append(notification);
    
    setTimeout(() => {
        notification.fadeOut(() => {
            notification.remove();
        });
    }, 5000);
}

// Populate fields with proposal data
function fillEventRelevance() {
    // POS/PSO: prefer current report value (hidden field), then keep existing, then fall back to proposal snapshot
    (function syncPosPso(){
        const $modern = $('#pos-pso-modern');
        if (!$modern.length) return;
        const hiddenEl = document.getElementById('id_pos_pso_mapping');
        const hiddenVal = (hiddenEl && hiddenEl.value ? String(hiddenEl.value) : '').trim();
        const modernVal = String($modern.val() || '').trim();
        const proposalVal = (window.PROPOSAL_DATA && typeof window.PROPOSAL_DATA.pos_pso !== 'undefined')
            ? String(window.PROPOSAL_DATA.pos_pso || '').trim()
            : '';

        // Decide the desired value without clobbering user edits
        let desired = '';
        if (hiddenVal) desired = hiddenVal; else if (modernVal) desired = modernVal; else desired = proposalVal;

        // Only write if the field is empty; don't overwrite non-empty user input
        if (!modernVal && desired) {
            $modern.val(desired); // no trigger to avoid unintended autosave churn
        }
        // Keep hidden in sync if it's empty but visible has content
        if (hiddenEl && !hiddenVal && modernVal) {
            hiddenEl.value = modernVal;
        }
    })();

    // SDG text: same preference order; avoid overwriting if user already has content
    (function syncSdg(){
        const $modern = $('#sdg-implementation-modern');
        if (!$modern.length) return;
        const hiddenEl = document.getElementById('id_sdg_value_systems_mapping');
        const hiddenVal = (hiddenEl && hiddenEl.value ? String(hiddenEl.value) : '').trim();
        const modernVal = String($modern.val() || '').trim();
        const proposalVal = (window.PROPOSAL_DATA && window.PROPOSAL_DATA.sdg_goals)
            ? String(window.PROPOSAL_DATA.sdg_goals || '').trim()
            : '';

        let desired = '';
        if (hiddenVal) desired = hiddenVal; else if (modernVal) desired = modernVal; else desired = proposalVal;

        if (!modernVal && desired) {
            $modern.val(desired); // avoid firing change to prevent autosave overrides
        }
        if (hiddenEl && !hiddenVal && modernVal) {
            hiddenEl.value = modernVal;
        }
    })();
    // Rebuild GA summary container each time to avoid stale DOM
    updateGASummary();
}

// Helper to (re)construct GA summary pills smartly
function updateGASummary() {
    try {
        const container = document.getElementById('graduate-attributes-modern');
        if (!container) {
            // Not yet rendered; retry shortly
            return setTimeout(updateGASummary, 200);
        }
        // Remove any previous summary / text nodes to ensure clean slate
        const existing = container.querySelectorAll('#ga-summary, .ga-pill-container');
        existing.forEach(el => el.remove());

        // Determine value source
        const hidden = document.getElementById('id_needs_grad_attr_mapping');
        let raw = '';
        if (hidden) raw = (hidden.value || '').trim();
        if (!raw && window.REPORT_GA_MAPPING) raw = String(window.REPORT_GA_MAPPING).trim();

        // Build new summary element
        const summaryDiv = document.createElement('div');
        summaryDiv.id = 'ga-summary';
        summaryDiv.className = 'ga-pill-container';
        const emptyText = 'Open the Graduate Attributes editor to select attributes. Your selections will be saved back to this report.';
        summaryDiv.setAttribute('data-empty-text', emptyText);

        if (!raw) {
            summaryDiv.classList.add('empty');
            summaryDiv.textContent = emptyText;
        } else {
            // Split on commas, trim, dedupe
            const items = Array.from(new Set(raw.split(/[,\n]/).map(s => s.trim()).filter(Boolean)));
            if (items.length === 0) {
                summaryDiv.classList.add('empty');
                summaryDiv.textContent = emptyText;
            } else {
                items.forEach(txt => {
                    const span = document.createElement('span');
                    span.className = 'ga-pill';
                    span.textContent = txt;
                    summaryDiv.appendChild(span);
                });
            }
        }
        container.appendChild(summaryDiv);
    } catch (e) { /* silent */ }
}

function fillOrganizingCommittee() {
    const field = $('#organizing-committee-modern');
    if (field.length && field.val().trim() === '' && window.PROPOSAL_DATA) {
        const parts = [];
        if (window.PROPOSAL_DATA.proposer) {
            parts.push(`Proposer: ${window.PROPOSAL_DATA.proposer}`);
        }
        if (window.PROPOSAL_DATA.faculty_incharges && window.PROPOSAL_DATA.faculty_incharges.length) {
            parts.push(`Faculty In-Charge: ${window.PROPOSAL_DATA.faculty_incharges.join(', ')}`);
        }
        if (window.PROPOSAL_DATA.student_coordinators) {
            parts.push(`Student Coordinators: ${window.PROPOSAL_DATA.student_coordinators}`);
        }
        if (window.PROPOSAL_DATA.volunteers && window.PROPOSAL_DATA.volunteers.length) {
            parts.push(`Volunteers: ${window.PROPOSAL_DATA.volunteers.join(', ')}`);
        }
        field.val(parts.join('\n'));
    }
}

function fillAttendanceCounts() {
    const counts = window.ATTENDANCE_COUNTS || {};
    const present = (counts.present !== undefined && counts.present !== null)
        ? counts.present
        : window.ATTENDANCE_PRESENT;
    const absent = (counts.absent !== undefined && counts.absent !== null)
        ? counts.absent
        : window.ATTENDANCE_ABSENT;
    const volunteers = (counts.volunteers !== undefined && counts.volunteers !== null)
        ? counts.volunteers
        : window.ATTENDANCE_VOLUNTEERS;
    const total = (counts.total !== undefined && counts.total !== null)
        ? counts.total
        : present;

    const updateField = (id, value) => {
        if (value === undefined || value === null) return;
        const el = document.getElementById(id);
        if (!el) return;
        if ('value' in el && typeof el.value !== 'undefined') {
            el.value = value;
        } else {
            el.textContent = value;
        }
    };

    const summaryField = document.getElementById('attendance-modern');
    if (summaryField) {
        const parts = [];
        if (present !== undefined && present !== null) parts.push(`Present: ${present}`);
        if (absent !== undefined && absent !== null) parts.push(`Absent: ${absent}`);
        if (volunteers !== undefined && volunteers !== null) parts.push(`Volunteers: ${volunteers}`);
        if (parts.length) summaryField.value = parts.join(', ');
    }

    updateField('num-participants-modern', total);
    updateField('total-participants-modern', total);
    updateField('num-volunteers-modern', volunteers);
    updateField('num-volunteers-hidden', volunteers);
    updateField('student-participants-modern', counts.students);
    updateField('faculty-participants-modern', counts.faculty);
    updateField('external-participants-modern', counts.external);

    if (typeof setupAttendanceLink === 'function') setupAttendanceLink();
}

function populateProposalData() {
    // Initial fill if fields exist
    setTimeout(function() {
        fillEventRelevance();
        fillOrganizingCommittee();
        fillAttendanceCounts();
    }, 100);

    // Populate when sections become active
    $(document).on('click', '[data-section="event-relevance"]', function() {
        setTimeout(fillEventRelevance, 100);
    });
    $(document).on('click', '[data-section="participants-information"]', function() {
        const init = (attempt=0) => {
            const container = document.getElementById('speakers-display');
            if (!container && attempt < 10) return setTimeout(() => init(attempt+1), 100);
            populateSpeakersFromProposal();
            fillOrganizingCommittee();
            fillAttendanceCounts();
        };
        setTimeout(() => init(0), 50);
    });
}

function getCsrfToken() {
    if (window.AUTOSAVE_CSRF) return window.AUTOSAVE_CSRF;
    const match = document.cookie
        .split(';')
        .map(part => part.trim())
        .find(part => part.startsWith('csrftoken='));
    return match ? decodeURIComponent(match.split('=')[1]) : '';
}

function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function getInitials(value) {
    if (!value) return 'SP';
    return String(value)
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map(part => part.charAt(0).toUpperCase())
        .join('') || 'SP';
}

function normalizeSpeakerValue(value) {
    return value === null || value === undefined ? '' : String(value);
}

function renderEditableSpeakerCard(speaker, index) {
    const id = speaker && (speaker.id || speaker.pk);
    const isNew = Boolean(speaker && (speaker.__isNew || speaker.is_new));
    const name = normalizeSpeakerValue(speaker.full_name || speaker.name);
    const designation = normalizeSpeakerValue(speaker.designation);
    const affiliation = normalizeSpeakerValue(speaker.affiliation || speaker.organization);
    const email = normalizeSpeakerValue(speaker.contact_email || speaker.contact);
    const phone = normalizeSpeakerValue(speaker.contact_number || speaker.phone);
    const linkedin = normalizeSpeakerValue(speaker.linkedin_url || speaker.linkedin || speaker.linkedinUrl);
    const bio = normalizeSpeakerValue(speaker.detailed_profile || speaker.profile || speaker.bio);
    const photoUrl = normalizeSpeakerValue(speaker.photo_url || speaker.photo);
    const initials = getInitials(name);
    const cardClasses = ['speaker-reference-item', 'speaker-card'];
    const isEditable = Boolean(id) || isNew;

    if (isEditable) {
        cardClasses.push('speaker-card-editable');
    } else {
        cardClasses.push('speaker-card-readonly');
    }

    if (isNew) {
        cardClasses.push('speaker-card-new');
    }

    const attributes = [`data-speaker-id="${id ? escapeHtml(id) : ''}"`, `data-speaker-index="${Number.isFinite(index) ? index : 0}"`];
    if (isNew) {
        attributes.push('data-speaker-new="true"');
    }

    return `
        <div class="${cardClasses.join(' ')}" ${attributes.join(' ')}>
            <div class="speaker-card-media">
                <div class="speaker-photo-container">
                    <div class="speaker-photo${photoUrl ? '' : ' speaker-photo-placeholder'}" data-initials="${escapeHtml(initials)}">
                        ${photoUrl ? `<img src="${escapeHtml(photoUrl)}" alt="${escapeHtml(name || 'Speaker photo')}">` : escapeHtml(initials)}
                    </div>
                    <button type="button" class="speaker-photo-remove" title="Remove photo" aria-label="Remove photo" ${photoUrl ? '' : 'hidden'}>&times;</button>
                </div>
                <label class="speaker-photo-upload">
                    <input type="file" class="speaker-photo-input" accept="image/*" ${id ? '' : 'disabled'}>
                    <span>${photoUrl ? 'Change photo' : 'Upload photo'}</span>
                </label>
            </div>
            <div class="speaker-card-content">
                <div class="speaker-header">
                    <div class="speaker-header-body">
                        <div class="speaker-header-title">Speaker ${index + 1}</div>
                        ${isEditable ? '' : '<div class="speaker-readonly-hint">Unable to edit this speaker because the record could not be linked.</div>'}
                    </div>
                    <button type="button" class="speaker-card-remove" title="Remove speaker">
                        <span aria-hidden="true">&times;</span>
                        <span class="sr-only">Remove speaker</span>
                    </button>
                </div>
                <div class="speaker-fields">
                    <div class="speaker-field">
                        <label>Full Name *</label>
                        <input type="text" class="speaker-field-input" data-field="full_name" value="${escapeHtml(name)}" placeholder="Enter full name" ${isEditable ? '' : 'disabled'}>
                    </div>
                    <div class="speaker-field">
                        <label>Designation *</label>
                        <input type="text" class="speaker-field-input" data-field="designation" value="${escapeHtml(designation)}" placeholder="Enter designation" ${isEditable ? '' : 'disabled'}>
                    </div>
                    <div class="speaker-field">
                        <label>Affiliation *</label>
                        <input type="text" class="speaker-field-input" data-field="affiliation" value="${escapeHtml(affiliation)}" placeholder="Enter organization" ${isEditable ? '' : 'disabled'}>
                    </div>
                    <div class="speaker-field">
                        <label>Email *</label>
                        <input type="email" class="speaker-field-input" data-field="contact_email" value="${escapeHtml(email)}" placeholder="name@example.com" ${isEditable ? '' : 'disabled'}>
                    </div>
                    <div class="speaker-field">
                        <label>Contact Number</label>
                        <input type="text" class="speaker-field-input" data-field="contact_number" value="${escapeHtml(phone)}" placeholder="Enter contact number" ${isEditable ? '' : 'disabled'}>
                    </div>
                    <div class="speaker-field">
                        <label>LinkedIn URL</label>
                        <input type="url" class="speaker-field-input" data-field="linkedin_url" value="${escapeHtml(linkedin)}" placeholder="https://linkedin.com/in/username" ${isEditable ? '' : 'disabled'}>
                    </div>
                    <div class="speaker-field speaker-field-full">
                        <label>Profile / Bio *</label>
                        <textarea class="speaker-field-textarea" data-field="detailed_profile" rows="4" placeholder="Brief profile of the speaker" ${isEditable ? '' : 'disabled'}>${escapeHtml(bio)}</textarea>
                    </div>
                </div>
                <div class="speaker-status" role="status" aria-live="polite"></div>
            </div>
        </div>
    `;
}

function getNoSpeakersMessageHtml() {
    return `
        <div class="no-speakers-message">
            <div class="no-speakers-icon"><i class="fas fa-user" aria-hidden="true"></i></div>
            <div class="no-speakers-text">No speakers were defined in the original proposal</div>
            <div class="no-speakers-help">You can add actual speakers in the field below</div>
        </div>
    `;
}

function reindexSpeakerCards(listEl) {
    if (!listEl) return;
    const cards = listEl.querySelectorAll('.speaker-card');
    cards.forEach((card, idx) => {
        card.dataset.speakerIndex = String(idx);
        const title = card.querySelector('.speaker-header-title');
        if (title) {
            title.textContent = `Speaker ${idx + 1}`;
        }
    });
}

function updateSpeakerPhotoPreview(card, photoUrl) {
    const photoEl = card.querySelector('.speaker-photo');
    const removeBtn = card.querySelector('.speaker-photo-remove');
    const uploadLabel = card.querySelector('.speaker-photo-upload span');
    const nameInput = card.querySelector('[data-field="full_name"]');
    const displayName = nameInput ? nameInput.value.trim() : '';
    if (!photoEl) return;

    if (photoUrl) {
        photoEl.innerHTML = `<img src="${escapeHtml(photoUrl)}" alt="${escapeHtml(displayName || 'Speaker photo')}">`;
        photoEl.classList.remove('speaker-photo-placeholder');
        photoEl.setAttribute('data-initials', getInitials(displayName));
        if (removeBtn) removeBtn.hidden = false;
        if (uploadLabel) uploadLabel.textContent = 'Change photo';
    } else {
        const initials = getInitials(displayName);
        photoEl.innerHTML = escapeHtml(initials);
        photoEl.classList.add('speaker-photo-placeholder');
        photoEl.setAttribute('data-initials', initials);
        if (removeBtn) removeBtn.hidden = true;
        if (uploadLabel) uploadLabel.textContent = 'Upload photo';
    }
}

function updateSpeakerCache(updated) {
    if (!updated || !updated.id) return;
    const id = String(updated.id);
    window.SPEAKER_CACHE = window.SPEAKER_CACHE || {};
    window.SPEAKER_CACHE[id] = Object.assign({}, window.SPEAKER_CACHE[id] || {}, updated);

    if (window.PROPOSAL_DATA && Array.isArray(window.PROPOSAL_DATA.speakers)) {
        const arr = window.PROPOSAL_DATA.speakers;
        const idx = arr.findIndex(sp => String(sp.id || sp.pk) === id);
        if (idx !== -1) {
            arr[idx] = Object.assign({}, arr[idx], updated);
        }
    }
    if (Array.isArray(window.EXISTING_SPEAKERS)) {
        const idx = window.EXISTING_SPEAKERS.findIndex(sp => String(sp.id || sp.pk) === id);
        if (idx !== -1) {
            window.EXISTING_SPEAKERS[idx] = Object.assign({}, window.EXISTING_SPEAKERS[idx], updated);
        }
    }
}

function handleSpeakerSave(card) {
    const id = card.dataset.speakerId;
    const updateBase = window.SPEAKER_UPDATE_BASE || '';
    if (!id || !updateBase) return Promise.resolve();

    if (card.__autoSaveTimer) {
        try { clearTimeout(card.__autoSaveTimer); } catch (e) {}
        card.__autoSaveTimer = null;
    }

    const statusEl = card.querySelector('.speaker-status');
    const fileInput = card.querySelector('.speaker-photo-input');
    const scheduleFn = typeof card.__scheduleAutoSave === 'function' ? card.__scheduleAutoSave : null;

    const formData = new FormData();
    card.querySelectorAll('[data-field]').forEach(input => {
        const key = input.dataset.field;
        if (!key) return;
        formData.append(key, input.value || '');
    });

    if (card.dataset.removePhoto === 'true') {
        formData.append('remove_photo', '1');
    }

    if (fileInput && fileInput.files && fileInput.files[0]) {
        formData.append('photo', fileInput.files[0]);
    }

    const url = `${updateBase}${id}/`;
    if (statusEl) {
        statusEl.textContent = 'Saving...';
        statusEl.dataset.state = 'pending';
    }
    card.dataset.saving = 'true';

    return fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken(),
        },
        credentials: 'same-origin',
        body: formData,
    })
        .then(async resp => {
            let data = {};
            try {
                data = await resp.json();
            } catch (err) {}
            if (!resp.ok || !data.success) {
                const error = data.errors || data.error || 'Unable to update speaker';
                throw error;
            }
            return data;
        })
        .then(data => {
            const updated = data.speaker || {};
            updateSpeakerCache(updated);

            const hasQueuedChanges = card.dataset.pendingSave === 'true';
            if (!hasQueuedChanges) {
                card.dataset.dirty = 'false';
                card.dataset.pendingSave = 'false';
                card.dataset.removePhoto = 'false';
                card.classList.remove('speaker-card-dirty');
            }

            const updatedPhoto = updated.photo_url || updated.photo || '';
            if (!hasQueuedChanges && fileInput) {
                if (card.dataset.photoObjectUrl) {
                    try { URL.revokeObjectURL(card.dataset.photoObjectUrl); } catch (e) {}
                    card.dataset.photoObjectUrl = '';
                }
                fileInput.value = '';
                if (updatedPhoto) {
                    updateSpeakerPhotoPreview(card, updatedPhoto);
                }
            }

            if (statusEl) {
                statusEl.textContent = hasQueuedChanges
                    ? 'Saving latest changes...'
                    : 'All changes saved';
                statusEl.dataset.state = hasQueuedChanges ? 'pending' : 'success';
            }
        })
        .catch(err => {
            let message = 'Failed to save speaker';
            if (typeof err === 'string') {
                message = err;
            } else if (err && typeof err === 'object') {
                const firstKey = Object.keys(err)[0];
                if (firstKey) {
                    const val = err[firstKey];
                    if (Array.isArray(val)) message = val[0];
                    else message = String(val);
                }
            }
            if (statusEl) {
                statusEl.textContent = message;
                statusEl.dataset.state = 'error';
            }
            try { showNotification(message, 'error'); } catch (e) {}
        })
        .finally(() => {
            card.dataset.saving = 'false';
            if (card.dataset.pendingSave === 'true' && typeof scheduleFn === 'function') {
                scheduleFn();
            }
        });
}

const SPEAKER_AUTO_SAVE_DELAY = 1200;

function setupSpeakerCardEditors(container) {
    if (!container) return;

    const updateBase = window.SPEAKER_UPDATE_BASE || '';

    if (!container.__speakerCardDelegated) {
        container.addEventListener('click', event => {
            const removeControl = event.target.closest('.speaker-card-remove');
            if (removeControl) {
                event.preventDefault();
                const card = removeControl.closest('.speaker-card');
                if (!card) return;
                const list = container.querySelector('.speakers-list');
                if (!list) return;

                const speakerId = card.dataset.speakerId;
                if (speakerId) {
                    const cacheId = String(speakerId);
                    if (window.SPEAKER_CACHE && Object.prototype.hasOwnProperty.call(window.SPEAKER_CACHE, cacheId)) {
                        delete window.SPEAKER_CACHE[cacheId];
                    }
                    if (window.PROPOSAL_DATA && Array.isArray(window.PROPOSAL_DATA.speakers)) {
                        window.PROPOSAL_DATA.speakers = window.PROPOSAL_DATA.speakers.filter(sp => String(sp.id || sp.pk) !== cacheId);
                    }
                    if (Array.isArray(window.EXISTING_SPEAKERS)) {
                        window.EXISTING_SPEAKERS = window.EXISTING_SPEAKERS.filter(sp => String(sp.id || sp.pk) !== cacheId);
                    }
                }

                card.remove();

                if (!list.querySelector('.speaker-card')) {
                    list.innerHTML = getNoSpeakersMessageHtml();
                } else {
                    reindexSpeakerCards(list);
                }
                return;
            }

            const addControl = event.target.closest('.speaker-card-add');
            if (addControl) {
                event.preventDefault();
                const list = container.querySelector('.speakers-list');
                if (!list) return;

                const placeholder = list.querySelector('.no-speakers-message');
                if (placeholder) placeholder.remove();

                const newIndex = list.querySelectorAll('.speaker-card').length;
                const newCardHtml = renderEditableSpeakerCard({ __isNew: true }, newIndex);
                list.insertAdjacentHTML('beforeend', newCardHtml);
                setupSpeakerCardEditors(container);
                reindexSpeakerCards(list);
                return;
            }
        });
        container.__speakerCardDelegated = true;
    }

    const cards = container.querySelectorAll('.speaker-card');
    cards.forEach(card => {
        if (card.dataset.initialized === 'true') return;
        card.dataset.initialized = 'true';

        const id = card.dataset.speakerId;
        const isNewCard = card.dataset.speakerNew === 'true';
        const statusEl = card.querySelector('.speaker-status');
        const fileInput = card.querySelector('.speaker-photo-input');
        const removeBtn = card.querySelector('.speaker-photo-remove');
        const inputs = card.querySelectorAll('.speaker-field-input, .speaker-field-textarea');
        const canEditRemote = Boolean(id && updateBase);
        const canEdit = isNewCard || canEditRemote;

        if (!canEdit) {
            if (statusEl) {
                statusEl.textContent = id
                    ? 'You do not have permission to edit this speaker.'
                    : 'Speaker information is read-only.';
            }
            if (removeBtn) removeBtn.disabled = true;
            if (fileInput) fileInput.disabled = true;
            inputs.forEach(input => input.disabled = true);
            return;
        }

        if (!canEditRemote) {
            if (removeBtn) removeBtn.disabled = true;
            if (fileInput) fileInput.disabled = true;
        }

        const handleNameInput = value => {
            const photoEl = card.querySelector('.speaker-photo');
            if (photoEl && photoEl.classList.contains('speaker-photo-placeholder')) {
                const initials = getInitials(value);
                photoEl.innerHTML = escapeHtml(initials);
                photoEl.setAttribute('data-initials', initials);
            }
        };

        if (isNewCard) {
            if (statusEl) {
                statusEl.textContent = 'New speaker entry (not linked to a record).';
                delete statusEl.dataset.state;
            }
            inputs.forEach(input => {
                if (input.dataset.field === 'full_name') {
                    input.addEventListener('input', () => handleNameInput(input.value.trim()));
                }
            });
            return;
        }

        card.dataset.removePhoto = 'false';
        card.dataset.dirty = card.dataset.dirty === 'true' ? 'true' : 'false';
        card.dataset.pendingSave = 'false';
        card.dataset.saving = 'false';
        card.__autoSaveTimer = null;
        card.classList.remove('speaker-card-dirty');
        if (statusEl) {
            statusEl.textContent = 'All changes saved';
            statusEl.dataset.state = 'success';
        }

        const scheduleAutoSave = () => {
            if (card.__autoSaveTimer) {
                try { clearTimeout(card.__autoSaveTimer); } catch (e) {}
            }

            if (card.dataset.saving === 'true') {
                card.dataset.pendingSave = 'true';
                card.__autoSaveTimer = null;
                return;
            }

            card.__autoSaveTimer = window.setTimeout(() => {
                card.__autoSaveTimer = null;
                if (card.dataset.dirty === 'true') {
                    card.dataset.pendingSave = 'false';
                    handleSpeakerSave(card);
                } else {
                    card.dataset.pendingSave = 'false';
                }
            }, SPEAKER_AUTO_SAVE_DELAY);
        };

        card.__scheduleAutoSave = scheduleAutoSave;

        const markDirty = () => {
            card.dataset.dirty = 'true';
            card.dataset.pendingSave = 'true';
            card.classList.add('speaker-card-dirty');
            if (statusEl) {
                statusEl.textContent = 'Saving pending changes...';
                statusEl.dataset.state = 'pending';
            }
            scheduleAutoSave();
        };

        inputs.forEach(input => {
            input.addEventListener('input', () => {
                if (input.dataset.field === 'full_name') {
                    handleNameInput(input.value.trim());
                }
                markDirty();
            });

            input.addEventListener('blur', () => {
                if (card.dataset.dirty === 'true') {
                    if (card.dataset.saving === 'true') {
                        card.dataset.pendingSave = 'true';
                        return;
                    }
                    if (card.__autoSaveTimer) {
                        try { clearTimeout(card.__autoSaveTimer); } catch (e) {}
                        card.__autoSaveTimer = null;
                    }
                    card.dataset.pendingSave = 'false';
                    handleSpeakerSave(card);
                }
            });
        });

        if (fileInput) {
            fileInput.addEventListener('change', () => {
                if (fileInput.files && fileInput.files[0]) {
                    if (card.dataset.photoObjectUrl) {
                        try { URL.revokeObjectURL(card.dataset.photoObjectUrl); } catch (e) {}
                    }
                    const objectUrl = URL.createObjectURL(fileInput.files[0]);
                    card.dataset.photoObjectUrl = objectUrl;
                    updateSpeakerPhotoPreview(card, objectUrl);
                    card.dataset.removePhoto = 'false';
                    markDirty();
                } else {
                    if (card.dataset.photoObjectUrl) {
                        try { URL.revokeObjectURL(card.dataset.photoObjectUrl); } catch (e) {}
                        card.dataset.photoObjectUrl = '';
                    }
                }
            });
        }

        if (removeBtn) {
            removeBtn.addEventListener('click', event => {
                event.preventDefault();
                card.dataset.removePhoto = 'true';
                if (fileInput) {
                    if (card.dataset.photoObjectUrl) {
                        try { URL.revokeObjectURL(card.dataset.photoObjectUrl); } catch (e) {}
                        card.dataset.photoObjectUrl = '';
                    }
                    fileInput.value = '';
                }
                updateSpeakerPhotoPreview(card, '');
                markDirty();
            });
        }
    });
}

// Populate speaker reference card with speakers from the original proposal
// Debug function to test speakers - can be called from browser console
window.debugSpeakers = function() {
    console.log('=== SPEAKERS DEBUG INFO ===');
    console.log('window.PROPOSAL_DATA:', window.PROPOSAL_DATA);
    console.log('window.EXISTING_SPEAKERS:', window.EXISTING_SPEAKERS);
    console.log('Speakers container exists:', !!document.getElementById('speakers-display'));
    
    if (window.PROPOSAL_DATA && window.PROPOSAL_DATA.speakers) {
        console.log('Proposal speakers count:', window.PROPOSAL_DATA.speakers.length);
        window.PROPOSAL_DATA.speakers.forEach((sp, i) => {
            console.log(`Speaker ${i}:`, sp);
        });
    }
    
    if (window.EXISTING_SPEAKERS) {
        console.log('Existing speakers count:', window.EXISTING_SPEAKERS.length);
        window.EXISTING_SPEAKERS.forEach((sp, i) => {
            console.log(`Existing speaker ${i}:`, sp);
        });
    }
    
    // Try to repopulate
    console.log('Attempting to repopulate speakers...');
    populateSpeakersFromProposal();
};

function populateSpeakersFromProposal() {
    const container = document.getElementById('speakers-display');
    if (!container) {
        console.warn('Speakers container not found');
        return;
    }

    let speakers = [];
    const readFallbackJson = () => {
        try {
            const tag = document.getElementById('proposal-speakers-json');
            if (!tag) return [];
            const txt = (tag.textContent || tag.innerText || '').trim();
            if (!txt) return [];
            const data = JSON.parse(txt);
            return Array.isArray(data) ? data : [];
        } catch (e) {
            console.warn('Fallback speakers JSON parse failed:', e);
            return [];
        }
    };
    const normalize = (val) => {
        try {
            if (!val) return [];
            if (typeof val === 'string') {
                const parsed = JSON.parse(val);
                return Array.isArray(parsed) ? parsed : [];
            }
            return Array.isArray(val) ? val : [];
        } catch (e) {
            console.warn('Failed to parse speakers JSON string:', e);
            return [];
        }
    };

    const proposalSpeakers = normalize(window.PROPOSAL_DATA && window.PROPOSAL_DATA.speakers);
    const existingSpeakers = normalize(window.EXISTING_SPEAKERS);
    if (proposalSpeakers.length) {
        speakers = proposalSpeakers;
    } else if (existingSpeakers.length) {
        speakers = existingSpeakers;
    } else {
        const fallback = readFallbackJson();
        if (fallback.length) {
            speakers = fallback;
        }
    }

    if (window.PROPOSAL_DATA && typeof window.PROPOSAL_DATA === 'object') {
        window.PROPOSAL_DATA.speakers = speakers;
    }
    if (Array.isArray(window.EXISTING_SPEAKERS)) {
        window.EXISTING_SPEAKERS = speakers;
    }

    window.SPEAKER_CACHE = {};
    let cardsHtml = '';
    if (Array.isArray(speakers) && speakers.length) {
        speakers.forEach((speaker, index) => {
            const record = speaker && typeof speaker === 'object' ? speaker : {};
            const id = record.id || record.pk;
            if (id) {
                window.SPEAKER_CACHE[String(id)] = Object.assign({}, record);
            }
            cardsHtml += renderEditableSpeakerCard(record, index);
        });
    }

    const listHtml = cardsHtml || getNoSpeakersMessageHtml();

    container.innerHTML = `
        <div class="speakers-list speakers-editable">
            ${listHtml}
        </div>
        <div class="speakers-actions">
            <button type="button" class="speaker-card-add">
                <span class="speaker-card-add-icon" aria-hidden="true">+</span>
                <span>Add Speaker</span>
            </button>
        </div>
    `;
    setupSpeakerCardEditors(container);
}

// SDG Modal functionality
function initializeSDGModal() {
    // SDG Goals data
    const sdgGoals = window.SDG_GOALS || [
        { id: 1, title: "No Poverty", description: "End poverty in all its forms everywhere" },
        { id: 2, title: "Zero Hunger", description: "End hunger, achieve food security and improved nutrition" },
        { id: 3, title: "Good Health and Well-being", description: "Ensure healthy lives and promote well-being for all" },
        { id: 4, title: "Quality Education", description: "Ensure inclusive and equitable quality education" },
        { id: 5, title: "Gender Equality", description: "Achieve gender equality and empower all women and girls" },
        { id: 6, title: "Clean Water and Sanitation", description: "Ensure availability and sustainable management of water" },
        { id: 7, title: "Affordable and Clean Energy", description: "Ensure access to affordable, reliable, sustainable energy" },
        { id: 8, title: "Decent Work and Economic Growth", description: "Promote sustained, inclusive economic growth" },
        { id: 9, title: "Industry, Innovation and Infrastructure", description: "Build resilient infrastructure, promote inclusive industrialization" },
        { id: 10, title: "Reduced Inequalities", description: "Reduce inequality within and among countries" },
        { id: 11, title: "Sustainable Cities and Communities", description: "Make cities and human settlements inclusive, safe, resilient" },
        { id: 12, title: "Responsible Consumption and Production", description: "Ensure sustainable consumption and production patterns" },
        { id: 13, title: "Climate Action", description: "Take urgent action to combat climate change" },
        { id: 14, title: "Life Below Water", description: "Conserve and sustainably use the oceans, seas and marine resources" },
        { id: 15, title: "Life on Land", description: "Protect, restore and promote sustainable use of terrestrial ecosystems" },
        { id: 16, title: "Peace, Justice and Strong Institutions", description: "Promote peaceful and inclusive societies" },
        { id: 17, title: "Partnerships for the Goals", description: "Strengthen the means of implementation and revitalize partnerships" }
    ];
    
    // Populate SDG options
    function populateSDGOptions() {
        const container = $('#sdgOptions');
        if (container.length === 0) return;
        
        container.empty();
        
        sdgGoals.forEach(goal => {
            const optionHtml = `
                <div class="sdg-option" data-sdg-id="${goal.id}">
                    <input type="checkbox" id="sdg-${goal.id}" value="SDG${goal.id}">
                    <label for="sdg-${goal.id}">
                        <strong>SDG ${goal.id}: ${goal.title}</strong><br>
                        <small>${goal.description}</small>
                    </label>
                </div>
            `;
            container.append(optionHtml);
        });
    }
    
    // Open SDG modal
    $(document).on('click', '#sdg-select-btn', function() {
        populateSDGOptions();
        
        // Pre-select existing SDG goals
        const currentSDGs = $('#sdg-implementation-modern').val();
        if (currentSDGs) {
            // Extract SDG numbers from the text (look for SDG1, SDG2, etc.)
            const sdgMatches = currentSDGs.match(/SDG\d+/g) || [];
            sdgMatches.forEach(sdg => {
                const sdgNumber = sdg.replace('SDG', '');
                $(`#sdg-${sdgNumber}`).prop('checked', true);
                $(`.sdg-option[data-sdg-id="${sdgNumber}"]`).addClass('selected');
            });
        }
        
        $('#sdgModal').show();
    });
    
    // SDG option selection
    $(document).on('click', '.sdg-option', function() {
        const checkbox = $(this).find('input[type="checkbox"]');
        checkbox.prop('checked', !checkbox.prop('checked'));
        $(this).toggleClass('selected', checkbox.prop('checked'));
    });
    
    // Save SDG selection
    $(document).on('click', '#sdgSave, .btn-sdg-save', function(e) {
        // Avoid triggering any outer Save & Continue handlers
        e.preventDefault();
        e.stopPropagation();
        const selectedSDGs = [];
        const selectedTitles = [];
        $('.sdg-option input[type="checkbox"]:checked').each(function() {
            selectedSDGs.push($(this).val());
            const sdgId = $(this).val().replace('SDG', '');
            const sdgGoal = sdgGoals.find(goal => goal.id == sdgId);
            if (sdgGoal) {
                selectedTitles.push(`${$(this).val()}: ${sdgGoal.title}`);
            }
        });
        
        // Create a formatted string for the textarea
        const formattedSDGs = selectedTitles.length > 0 
            ? selectedTitles.join('\n') + '\n\n(You can edit this text and add additional context about how your event addresses these SDG goals)'
            : '';
        
        $('#sdg-implementation-modern').val(formattedSDGs).trigger('input').trigger('change');
        // Keep hidden Django field in sync so autosave payload is correct
        const sdgHidden = document.getElementById('id_sdg_value_systems_mapping');
        if (sdgHidden) sdgHidden.value = formattedSDGs;
        $('#sdgModal').hide();
        // Persist immediately
        if (window.ReportAutosaveManager && ReportAutosaveManager.manualSave) {
            ReportAutosaveManager.manualSave().then(() => {
                try { showNotification('SDG selection saved', 'success'); } catch(_){}
            }).catch(() => {
                try { showNotification('Failed to save SDG selection', 'error'); } catch(_){}
            });
        }
    });
    
    // Cancel SDG selection
    $(document).on('click', '#sdgCancel', function() {
        $('#sdgModal').hide();
    });
    
    // Close modal when clicking outside
    $(document).on('click', '#sdgModal', function(e) {
        if (e.target === this) {
            $('#sdgModal').hide();
        }
    });
}

function openOutcomeModal(){
  const modal = document.getElementById('outcomeModal');
  const container = document.getElementById('outcomeOptions');
    let url = modal.dataset.url;
    // fallback: derive using API_OUTCOMES_BASE and PROPOSAL_ORG_ID
    if(!url && window.API_OUTCOMES_BASE && window.PROPOSAL_ORG_ID){
        url = `${window.API_OUTCOMES_BASE}${window.PROPOSAL_ORG_ID}/`;
        modal.dataset.url = url;
    }
  if(!url){
    alert('No organization set for this proposal.');
    return;
  }
    const field = document.getElementById('id_pos_pso_mapping');
    const modern = document.getElementById('pos-pso-modern');
    // Prefer visible textarea value to capture user edits; fallback to hidden
    const currentValue = (modern && modern.value ? modern.value : (field ? field.value : '')) || '';
    const selectedSet = new Set(
        currentValue.split('\n')
      .map(s => s.trim())
      .filter(Boolean)
  );
  modal.classList.add('show');
  container.textContent = 'Loading...';
  fetchWithOverlay(url, {}, 'Loading outcomes...')
    .then(r => r.json())
    .then(data => {
      if(data.success){
        container.innerHTML = '';
    data.pos.forEach((po, idx) => { addOption(container, `PO${idx+1}: ${po.description}`, selectedSet); });
    data.psos.forEach((pso, idx) => { addOption(container, `PSO${idx+1}: ${pso.description}`, selectedSet); });
      } else {
        container.textContent = 'No data';
      }
    })
    .catch(() => { container.textContent = 'Error loading'; });
}

function addOption(container, labelText, checkedSet){
    // Outcome option styled similarly to SDG goal tile
    const wrapper = document.createElement('div');
    wrapper.className = 'outcome-option';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.value = labelText;
    if(checkedSet && checkedSet.has(labelText)){
        cb.checked = true;
        wrapper.classList.add('selected');
    }
    const text = document.createElement('div');
    text.style.flex = '1';
    text.style.fontSize = '0.8rem';
    text.style.lineHeight = '1.2rem';
    text.textContent = labelText;
    wrapper.appendChild(cb);
    wrapper.appendChild(text);
    wrapper.addEventListener('click', function(e){
        if(e.target.tagName !== 'INPUT'){
            cb.checked = !cb.checked;
        }
        wrapper.classList.toggle('selected', cb.checked);
    });
    container.appendChild(wrapper);
}

// Legacy outcome modal handlers (only bind if elements exist)
const _outcomeCancelBtn = document.getElementById('outcomeCancel');
const _outcomeSaveBtn = document.getElementById('outcomeSave');
if(_outcomeCancelBtn && document.getElementById('outcomeModal')){
    _outcomeCancelBtn.onclick = function(){
        const m = document.getElementById('outcomeModal');
        if(m) m.classList.remove('show');
    };
}
if(_outcomeSaveBtn && document.getElementById('outcomeModal')){
    // Outcome Save isolated (no 'btn-save-section' class) to avoid triggering global handler
    _outcomeSaveBtn.classList.add('btn-outcome-save');
    _outcomeSaveBtn.onclick = function(e){
        e?.preventDefault?.();
        e?.stopPropagation?.();
        const modal = document.getElementById('outcomeModal');
        if(!modal) return;
    const selected = Array.from(modal.querySelectorAll('.outcome-option input[type=checkbox]:checked')).map(c => c.value);
        const field = document.getElementById('id_pos_pso_mapping');
        if(!field) return;
        field.value = selected.join('\n');
        // Also reflect back to visible textarea if present
        const modern = document.getElementById('pos-pso-modern');
        if (modern) { modern.value = field.value; $(modern).trigger('input').trigger('change'); }
        modal.classList.remove('show');
        // Persist immediately
        if (window.ReportAutosaveManager && ReportAutosaveManager.manualSave) {
            ReportAutosaveManager.manualSave().then(() => {
                try { showNotification('PO/PSO selection saved', 'success'); } catch(_){}
            }).catch(() => {
                try { showNotification('Failed to save PO/PSO', 'error'); } catch(_){}
            });
        }
    };
}

function initAttachments(){
  const list = document.getElementById('attachment-list');
  const addBtn = document.getElementById('add-attachment-btn');
  const template = document.getElementById('attachment-template');
  const totalInput = document.querySelector('input[name$="-TOTAL_FORMS"]');
  if(!list || !addBtn || !template || !totalInput) return;

  const placeholderMarkup = '<span class="attach-add">+</span><span class="attach-text">Add file</span>';

  function setPlaceholder(upload){
    upload.innerHTML = placeholderMarkup;
    delete upload.dataset.fileUrl;
    delete upload.dataset.previewType;
  }

  function bind(block){
    const upload = block.querySelector('.attach-upload');
    const fileInput = block.querySelector('.file-input');
    const removeBtn = block.querySelector('.attach-remove');
    const deleteToggle = block.querySelector('input[name$="-DELETE"]');
    if(!upload || !fileInput || !removeBtn) return;

    const ensureRemovePlacement = () => {
      if (!upload.contains(removeBtn)) {
        upload.appendChild(removeBtn);
      }
    };

    const toggleRemoveVisibility = (visible) => {
      removeBtn.style.display = visible ? 'flex' : 'none';
    };

    upload.addEventListener('click', () => {
      const fileUrl = upload.dataset.fileUrl;
      const previewType = upload.dataset.previewType;
      if (fileUrl) {
        if (previewType === 'image') {
          openImageModal(fileUrl);
        } else {
          try {
            window.open(fileUrl, '_blank', 'noopener');
          } catch (_) {}
        }
        return;
      }
      fileInput.click();
    });

    fileInput.addEventListener('change', () => {
      if(fileInput.files && fileInput.files[0]){
        const file = fileInput.files[0];
        const isImage = file.type && file.type.startsWith('image/');
        const objectUrl = URL.createObjectURL(file);
        if(isImage){
          upload.innerHTML = `<img src="${objectUrl}" alt="Attachment preview">`;
          upload.dataset.previewType = 'image';
        } else {
          const safeName = escapeHtml(file.name || 'Attachment');
          upload.innerHTML = `<div class="attach-file"><span class="attach-file-name">${safeName}</span><span class="attach-text">Click to download</span></div>`;
          upload.dataset.previewType = 'file';
        }
        upload.dataset.fileUrl = objectUrl;
        ensureRemovePlacement();
        toggleRemoveVisibility(true);
        if (deleteToggle) deleteToggle.checked = false;
        if (window.ReportAutosaveManager) {
          ReportAutosaveManager.reinitialize();
        }
      } else if (!upload.dataset.fileUrl) {
        setPlaceholder(upload);
        toggleRemoveVisibility(false);
      }
    });

    removeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      fileInput.value = '';
      if (deleteToggle) deleteToggle.checked = true;
      setPlaceholder(upload);
      toggleRemoveVisibility(false);
      if (window.ReportAutosaveManager) {
        ReportAutosaveManager.reinitialize();
      }
    });

    if (upload.dataset.fileUrl) {
      ensureRemovePlacement();
      toggleRemoveVisibility(true);
    } else {
      if (!upload.innerHTML.trim()) {
        setPlaceholder(upload);
      }
      toggleRemoveVisibility(false);
    }
  }

  list.querySelectorAll('.attachment-block').forEach(bind);

  addBtn.addEventListener('click', () => {
    const idx = parseInt(totalInput.value, 10) || 0;
    const html = template.innerHTML.replace(/__prefix__/g, idx);
    const temp = document.createElement('div');
    temp.innerHTML = html.trim();
    const block = temp.firstElementChild;
    if(!block) return;
    list.appendChild(block);
    totalInput.value = String(idx + 1);
    bind(block);
    if (window.ReportAutosaveManager) {
      ReportAutosaveManager.reinitialize();
    }
    const input = block.querySelector('.file-input');
    if (input) input.click();
  });
}

function openImageModal(src){
  const modal = document.getElementById('imgModal');
  const img = document.getElementById('imgModalImg');
  if(!modal || !img) return;
  img.src = src;
  modal.classList.add('show');
}

document.addEventListener('DOMContentLoaded', function(){
  const modal = document.getElementById('imgModal');
  const closeBtn = modal ? modal.querySelector('.close-btn') : null;
  if(closeBtn){
    closeBtn.addEventListener('click', () => modal.classList.remove('show'));
  }
});

// Function to update speaker display based on selected speakers
function updateSpeakerDisplay() {
    const speakerSelect = document.getElementById('speaker-selection');
    const speakersDisplay = document.getElementById('speakers-display');
    
    if (!speakerSelect || !speakersDisplay) return;
    
    const selectedOptions = Array.from(speakerSelect.selectedOptions);
    
    if (selectedOptions.length === 0) {
        speakersDisplay.innerHTML = '<p class="text-muted text-center py-3">No speakers selected</p>';
        return;
    }
    
    let html = '';
    selectedOptions.forEach((option, index) => {
        const speakerId = option.value;
        const speakerName = option.text;
        
        html += `
            <div class="card speaker-card mb-3" id="speaker-card-${speakerId}">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">Speaker ${index + 1}: ${speakerName}</h6>
                    <small class="text-muted">Speaker ID: ${speakerId}</small>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group mb-3">
                                <label for="speaker-topic-${speakerId}" class="form-label">
                                    Topic/Subject <span class="text-danger">*</span>
                                </label>
                                <input type="text" 
                                       id="speaker-topic-${speakerId}" 
                                       name="speaker_topics[]" 
                                       class="form-control" 
                                       placeholder="Enter the topic/subject covered" 
                                       required>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group mb-3">
                                <label for="speaker-duration-${speakerId}" class="form-label">
                                    Duration (minutes) <span class="text-danger">*</span>
                                </label>
                                <input type="number" 
                                       id="speaker-duration-${speakerId}" 
                                       name="speaker_durations[]" 
                                       class="form-control" 
                                       placeholder="Duration in minutes" 
                                       min="1" 
                                       max="480" 
                                       required>
                            </div>
                        </div>
                    </div>
                    <div class="form-group mb-3">
                        <label for="speaker-feedback-${speakerId}" class="form-label">
                            Feedback/Comments
                        </label>
                        <textarea id="speaker-feedback-${speakerId}" 
                                  name="speaker_feedback[]" 
                                  class="form-control" 
                                  rows="3" 
                                  placeholder="Any feedback or comments about this speaker's session"></textarea>
                    </div>
                    <input type="hidden" name="speaker_ids[]" value="${speakerId}">
                </div>
            </div>
        `;
    });

    speakersDisplay.innerHTML = html;
    if (window.ReportAutosaveManager) {
        ReportAutosaveManager.reinitialize();
    }
}

// Function to handle dynamic content updates when sections are loaded
function initializeSectionSpecificHandlers() {
    // Handle speaker selection changes
    $(document).on('change', '#speaker-selection', function() {
        updateSpeakerDisplay();
    });
    
    // Handle committee member addition
    $(document).on('click', '#add-committee-member', function() {
        const container = $('#committee-members-container');
        const memberCount = container.find('.committee-member-group').length;
        
        const memberHtml = `
            <div class="committee-member-group card mb-3">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h6 class="mb-0">Committee Member ${memberCount + 1}</h6>
                        <button type="button" class="btn btn-sm btn-outline-danger remove-committee-member">
                            <i class="fas fa-trash"></i> Remove
                        </button>
                    </div>
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group mb-3">
                                <label class="form-label">Name <span class="text-danger">*</span></label>
                                <input type="text" name="committee_member_names[]" class="form-control" placeholder="Enter member name" required>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group mb-3">
                                <label class="form-label">Role <span class="text-danger">*</span></label>
                                <input type="text" name="committee_member_roles[]" class="form-control" placeholder="Enter role (e.g., Coordinator, Volunteer)" required>
                            </div>
                        </div>
                    </div>
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group mb-3">
                                <label class="form-label">Department/Organization</label>
                                <input type="text" name="committee_member_departments[]" class="form-control" placeholder="Enter department or organization">
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group mb-3">
                                <label class="form-label">Contact</label>
                                <input type="text" name="committee_member_contacts[]" class="form-control" placeholder="Email or phone number">
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        container.append(memberHtml);
        if (window.ReportAutosaveManager) {
            ReportAutosaveManager.reinitialize();
        }
    });

    // Handle committee member removal
    $(document).on('click', '.remove-committee-member', function() {
        $(this).closest('.committee-member-group').remove();
        
        // Renumber remaining members
        $('#committee-members-container .committee-member-group').each(function(index) {
            $(this).find('h6').text(`Committee Member ${index + 1}`);
        });
        if (window.ReportAutosaveManager) {
            ReportAutosaveManager.reinitialize();
        }
    });
}

function setupDynamicActivities() {
    console.log('Setting up dynamic activities...');
    const numInput = document.getElementById('num-activities-modern');
    const container = document.getElementById('dynamic-activities-section');
    
    console.log('Activities elements:', {
        numInput: !!numInput,
        container: !!container
    });
    
    if (!numInput || !container) {
        console.warn('Activities setup failed - missing elements');
        return;
    }

    // Check if activities are already server-rendered
    const existingRows = container.querySelectorAll('.activity-row');
    let activities = [];

    // If server-rendered activities exist, preserve them
    if (existingRows.length > 0) {
        console.log('Found existing activity rows:', existingRows.length);
        existingRows.forEach((row, idx) => {
            const nameInput = row.querySelector(`input[name^="activity_name"]`);
            const dateInput = row.querySelector(`input[name^="activity_date"]`);
            activities.push({
                activity_name: nameInput ? nameInput.value : '',
                activity_date: dateInput ? dateInput.value : ''
            });
        });
    } else {
        // Fallback to JavaScript data if no server-rendered activities
        console.log('No server-rendered activities, using PROPOSAL_ACTIVITIES:', window.PROPOSAL_ACTIVITIES);
        const initialActivities = Array.isArray(window.PROPOSAL_ACTIVITIES)
            ? window.PROPOSAL_ACTIVITIES
            : [];
        activities = [...initialActivities];

        // Ensure at least one blank activity row exists on initial load
        if (activities.length === 0) {
            console.log('No activities found, adding default empty activity');
            activities.push({ activity_name: '', activity_date: '' });
        }
    }

    function render() {
        console.log('Rendering activities:', activities);
        container.innerHTML = '';
        activities.forEach((act, idx) => {
            const row = document.createElement('div');
            row.className = 'activity-row';
            row.innerHTML = `
                <div class="input-group">
                    <label for="activity_name_${idx + 1}" class="activity-label">${idx + 1}. Activity Name</label>
                    <input type="text" id="activity_name_${idx + 1}" name="activity_name_${idx + 1}" value="${act.activity_name || ''}">
                </div>
                <div class="input-group">
                    <label for="activity_date_${idx + 1}" class="date-label">${idx + 1}. Activity Date</label>
                    <input type="date" id="activity_date_${idx + 1}" name="activity_date_${idx + 1}" value="${act.activity_date || ''}">
                </div>
                <button type="button" class="remove-activity btn btn-sm btn-outline-secondary" title="Remove this activity">×</button>
            `;
            container.appendChild(row);
        });
        numInput.value = activities.length;
        console.log('Activities rendered successfully, count:', activities.length);
        if (window.ReportAutosaveManager) {
            ReportAutosaveManager.reinitialize();
        }
    }

    container.addEventListener('click', (e) => {
        if (e.target.classList.contains('remove-activity')) {
            const row = e.target.closest('.activity-row');
            const index = Array.from(container.children).indexOf(row);
            if (index > -1) {
                activities.splice(index, 1);
                render();
            }
        }
    });

    // Handle input changes to sync with activities array
    container.addEventListener('input', (e) => {
        const input = e.target;
        if (input.name && input.name.startsWith('activity_')) {
            const match = input.name.match(/activity_(name|date)_(\d+)/);
            if (match) {
                const fieldType = match[1];
                const index = parseInt(match[2], 10) - 1; // Convert to 0-based index
                if (activities[index]) {
                    activities[index][`activity_${fieldType}`] = input.value;
                }
            }
        }
    });

    // Create and add "Add Activity" button dynamically (only if it doesn't exist)
    let existingAddBtn = container.parentNode.querySelector('.btn-add-activity');
    if (!existingAddBtn) {
        const addBtn = document.createElement('button');
        addBtn.type = 'button';
        // Important: avoid 'btn-save-section' to prevent Save & Continue handler from firing
        addBtn.className = 'btn-add-item btn-add-activity';
        addBtn.textContent = 'Add Activity';
        addBtn.style.marginTop = '0.5rem';
        addBtn.addEventListener('click', () => {
            activities.push({ activity_name: '', activity_date: '' });
            render();
        });
        
        // Insert the button after the container
        container.parentNode.insertBefore(addBtn, container.nextSibling);
    }

    // Always render the activities from proposal data
    render();
}

function setupAttendanceLink() {
    const attendanceField = $('#attendance-modern');
    const participantFields = $('#num-participants-modern, #total-participants-modern');
    const fields = attendanceField.add(participantFields);
    if (!fields.length) return;

    const attendanceUrl = attendanceField.data('attendance-url');
    if (attendanceUrl) {
        fields
            .attr('data-attendance-url', attendanceUrl)
            .data('attendance-url', attendanceUrl);
    }

    fields.each(function () {
        const field = $(this);
        const url = field.data('attendance-url');
        field
            .prop('readonly', true)
            .css('cursor', 'pointer')
            .attr('href', url || '#');
    });

    $(document)
        .off('click', '#attendance-modern, #num-participants-modern, #total-participants-modern')
        .on('click', '#attendance-modern, #num-participants-modern, #total-participants-modern', async function (e) {
            e.preventDefault();
            const field = $(this);
            const href = field.data('attendance-url');
            if (href) {
                window.location.href = href;
                return;
            }

            // No report yet: trigger an autosave to create it, then redirect
            try {
                showLoadingOverlay('Preparing attendance...');
                // Fallback: if autosave URL isn't injected, infer it from current path
                if (!window.AUTOSAVE_URL) {
                    const path = window.location.pathname || '';
                    let prefix = '';
                    if (path.startsWith('/suite/')) prefix = '/suite';
                    else if (path.startsWith('/emt/')) prefix = '/emt';
                    window.AUTOSAVE_URL = `${prefix}/autosave-event-report/`;
                }

                let reportId = window.REPORT_ID;
                let result = null;
                if (window.ReportAutosaveManager && window.ReportAutosaveManager.manualSave) {
                    try {
                        result = await window.ReportAutosaveManager.manualSave();
                    } catch (autosaveError) {
                        console.error('Autosave failed before opening attendance; continuing when possible.', autosaveError);
                    }
                }

                if (result?.report_id) {
                    reportId = result.report_id;
                }

                if (reportId) {
                    // Respect site prefix (/suite or /emt) when building the URL
                    const path = window.location.pathname || '';
                    let prefix = '';
                    if (path.startsWith('/suite/')) prefix = '/suite';
                    else if (path.startsWith('/emt/')) prefix = '/emt';
                    const attendanceUrl = `${prefix}/reports/${reportId}/attendance/upload/`;
                    fields.each((_, f) => {
                        const jq = $(f);
                        jq
                            .attr('data-attendance-url', attendanceUrl)
                            .data('attendance-url', attendanceUrl)
                            .attr('href', attendanceUrl);
                    });
                    window.location.href = attendanceUrl;
                } else {
                    alert('Unable to prepare attendance. Please try saving once.');
                }
            } catch (e) {
                console.error('Unexpected error while preparing attendance:', e);
                alert('Unable to open attendance page. Please try again.');
            } finally {
                hideLoadingOverlay();
            }
        });
}

function setupGAEditorLink() {
    const btnId = '#ga-open-editor-btn';
    $(document).off('click', btnId).on('click', btnId, async function() {
        try {
            showLoadingOverlay('Preparing Graduate Attributes editor...');
            // Ensure there's a report ID; try manual autosave if available
            let reportId = window.REPORT_ID;
            if ((!reportId || String(reportId).trim() === '') && window.ReportAutosaveManager && ReportAutosaveManager.manualSave) {
                const result = await ReportAutosaveManager.manualSave();
                reportId = result?.report_id || result?.reportId || window.REPORT_ID;
            }
            if (!reportId) {
                alert('Unable to open GA editor. Please save the report once and try again.');
                return;
            }
            // Respect site prefix (/suite or /emt)
            const path = window.location.pathname || '';
            let prefix = '';
            if (path.startsWith('/suite/')) prefix = '/suite';
            else if (path.startsWith('/emt/')) prefix = '/emt';
            const url = `${prefix}/reports/${reportId}/graduate-attributes/edit/?from=ga`;
            window.location.href = url;
        } catch (e) {
            console.error('Failed to prepare GA editor:', e);
            alert('Save failed. Please fix any errors and try again.');
        } finally {
            hideLoadingOverlay();
        }
    });
}


function initializeAutosaveIndicators() {
    $(document).on('autosave:start', function() {
        const indicator = $('#autosave-indicator');
        indicator.removeClass('saved error').addClass('saving show');
        indicator.find('.indicator-text').text('Saving...');
    });

    $(document).on('autosave:success', function(e, data) {
        const indicator = $('#autosave-indicator');
        indicator.removeClass('saving error').addClass('saved');
        indicator.find('.indicator-text').text('Saved');
        setTimeout(() => {
            indicator.removeClass('show');
        }, 2000);

        const reportId = data?.reportId || e.originalEvent?.detail?.reportId || e.detail?.reportId;
        if (reportId) {
            const path = window.location.pathname || '';
            let prefix = '';
            if (path.startsWith('/suite/')) prefix = '/suite';
            else if (path.startsWith('/emt/')) prefix = '/emt';
            const attendanceUrl = `${prefix}/reports/${reportId}/attendance/upload/`;
            $('#attendance-modern, #num-participants-modern, #total-participants-modern')
                .attr('data-attendance-url', attendanceUrl)
                .data('attendance-url', attendanceUrl);
            setupAttendanceLink();
        }
    });

    $(document).on('autosave:error', function() {
        const indicator = $('#autosave-indicator');
        indicator.removeClass('saving saved').addClass('error show');
        indicator.find('.indicator-text').text('Save Failed');
        setTimeout(() => {
            indicator.removeClass('show');
        }, 3000);
    });
}


// Initialize section-specific handlers when document is ready
$(document).ready(function() {
    initializeSectionSpecificHandlers();
    setupDynamicActivities();
    setupAttendanceLink();
    setupGAEditorLink();
    if (window.ReportAutosaveManager) {
        ReportAutosaveManager.reinitialize();
    }
    initializeAutosaveIndicators();

    // Sync GA summary when returning from GA editor (?from=ga)
    (function syncGASummaryOnReturn(){
        try {
            const params = new URLSearchParams(window.location.search || '');
            if(params.get('from') !== 'ga') return;
            const apply = () => updateGASummary();
            apply();
            setTimeout(apply, 600); // retry after potential autosave refresh
            setTimeout(apply, 1500); // final ensure
        } catch (e) { /* ignore */ }
    })();

    $('#report-form').on('submit', function() {
        if (loadingCount === 0) {
            showLoadingOverlay('Submitting...');
        }
    });
});

