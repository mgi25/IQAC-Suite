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
    showLoadingOverlay(text);
    return fetch(url, options).finally(() => {
        hideLoadingOverlay();
    });
}

document.addEventListener('DOMContentLoaded', function(){
    // Central init (consolidated single DOMContentLoaded listener)
    const sectionState = {}; // fieldName -> value snapshot
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
  
  let currentSection = 'event-information';
  let sectionProgress = {
      'event-information': false,
      'participants-information': false,
      'event-summary': false,
      'event-outcomes': false,
      'analysis': false,
      'event-relevance': false
  };

  const previewUrl = $('#report-form').data('preview-url');

  // Rehydrate progress from server-rendered classes (if editing existing draft)
  document.querySelectorAll('.nav-link').forEach(link => {
      if(link.classList.contains('completed')){
          const s = link.getAttribute('data-section');
          if(sectionProgress.hasOwnProperty(s)) sectionProgress[s] = true;
      }
  });
  if(allSectionsCompleted()) enableFinalSubmission();
  
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
  
  // Save & Continue button handling
  $(document).on('click', '.btn-save-section', function(e) {
      e.preventDefault();
      if (!validateCurrentSection()) {
          showNotification('Please fill in all required fields', 'error');
          return;
      }

      let submitted = false;
      const proceed = () => {
          markSectionComplete(currentSection);
          const nextSection = getNextSection(currentSection);

          if (nextSection) {
              enableSection(nextSection);
              activateSection(nextSection);
              showNotification('Section saved! Moving to next section', 'success');
          } else {
              showNotification('All sections completed! Review your report.', 'success');
              const form = $('#report-form');

              // Remove any previously appended hidden inputs
              form.find('input.section-state-hidden').remove();

              // Serialize every form control, including empty or unchecked ones
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
                      value: value
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

              form.attr('action', previewUrl);
              showLoadingOverlay('Generating preview...');
              form[0].submit();
              submitted = true;
          }
      };

      showLoadingOverlay('Saving...');
      const savePromise = (window.ReportAutosaveManager && window.ReportAutosaveManager.manualSave)
          ? window.ReportAutosaveManager.manualSave()
          : Promise.resolve();

      savePromise.then(() => {
          proceed();
          if (!submitted) hideLoadingOverlay();
      }).catch(() => {
          showNotification('Save failed', 'error');
          proceed();
          if (!submitted) hideLoadingOverlay();
      });
  });
  
  function activateSection(sectionName) {
      currentSection = sectionName;
      
      // Update navigation
      $('.nav-link').removeClass('active');
      $(`.nav-link[data-section="${sectionName}"]`).addClass('active');
      
      // Update content
      loadSectionContent(sectionName);
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
          default:
              content = getEventInformationContent();
      }
      
      $('.form-grid').html(content);

      if (sectionName === 'participants-information') {
          populateSpeakersFromProposal();
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
          'suggestions': { 
              title: 'Suggestions for Improvements', 
              subtitle: 'IQAC coordinator feedback and recommendations' 
          }
      };
      return sections[section] || { title: 'Section', subtitle: 'Complete this section' };
  }
  
    function getNextSection(current) {
            // Order must exactly match existing nav/link + sectionProgress keys.
            // Removed 'suggestions' (no nav item defined) which previously blocked final submission.
            const order = ['event-information', 'participants-information', 'event-summary', 'event-outcomes', 'analysis', 'event-relevance'];
      const currentIndex = order.indexOf(current);
      return currentIndex < order.length - 1 ? order[currentIndex + 1] : null;
  }
  
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
          if (field.id === '#graduate-attributes-modern') {
              const checked = element.find('input[name="needs_grad_attr_mapping"]:checked');
              if (checked.length === 0) {
                  showFieldError(element, field.name + ' - Please select at least one attribute');
                  isValid = false;
              } else {
                  clearFieldError(element);
              }
          } else {
              // For textarea and input fields
              if (!element.val() || element.val().trim() === '') {
                  showFieldError(element, field.name + ' is required');
                  isValid = false;
              } else {
                  clearFieldError(element);
              }
          }
      });
      
      return isValid;
  }
  
  function markSectionComplete(sectionName) {
      sectionProgress[sectionName] = true;
      $(`.nav-link[data-section="${sectionName}"]`).addClass('completed');
      if (allSectionsCompleted()) {
          enableFinalSubmission();
      }
  }

  function allSectionsCompleted(){
      return Object.values(sectionProgress).every(Boolean);
  }

  function enableFinalSubmission(){
      const submitSection = document.querySelector('.submit-section');
      if(submitSection){
          submitSection.classList.remove('hidden');
      }
      const btn = document.getElementById('submit-report-btn');
      if(btn){ btn.disabled = false; }
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

  // Graduate Attributes toggle behavior
  $(document).on('click', '.ga-toggle', function(){
      $(this).next('.ga-options').slideToggle();
  });

  // Clear error when selecting graduate attributes
  $(document).on('change', 'input[name="needs_grad_attr_mapping"]', function(){
      clearFieldError($('#graduate-attributes-modern'));
  });

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
                  <input type="text" id="academic-year-modern" name="academic_year" value="${window.PROPOSAL_DATA ? window.PROPOSAL_DATA.academic_year || '2024-2025' : '2024-2025'}">
                  <div class="help-text">Academic year from proposal (editable)</div>
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

          <div class="form-row">
              <div class="input-group">
                  <label for="num-activities-modern">Number of Activities</label>
                  <input type="number" id="num-activities-modern" name="num_activities" value="${window.PROPOSAL_DATA ? window.PROPOSAL_DATA.num_activities || 1 : 1}">
                  <div class="help-text">Total activities from proposal (editable)</div>
              </div>
          </div>

          <!-- Dynamic activities section -->
          <div id="report-activities" class="full-width"></div>
          <button type="button" id="add-activity-btn" class="btn-add-item" style="display: none;">Add Activity</button>

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

          <div class="form-row full-width">
              <div class="input-group">
                  <label for="actual-speakers-modern">Actual Speakers</label>
                  <textarea id="actual-speakers-modern" name="actual_speakers" rows="8" 
                      placeholder="List the actual speakers who participated:&#10;&#10;• Speaker 1: Dr. [Name] - [Designation] - [Institution/Company]&#10;  Topic: [Session topic]&#10;  Duration: [Time duration]&#10;&#10;• Speaker 2: Prof. [Name] - [Designation] - [Institution/Company]&#10;  Topic: [Session topic]&#10;  Duration: [Time duration]&#10;&#10;Include any changes from the original proposal and reasons for changes."></textarea>
                  <div class="help-text">List actual speakers and any changes from the original proposal</div>
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

          <!-- Graduate Attributes Section -->
          <div class="form-section-header">
              <h3>Graduate Attributes & Contemporary Requirements</h3>
          </div>
          
          <div class="form-row">
              <div class="input-group">
                  <label for="graduate-attributes-modern">Graduate Attributes *</label>
                  <div id="graduate-attributes-modern" class="graduate-attributes-groups">
                      <div class="ga-category">
                          <button type="button" class="ga-toggle">Academic Excellence</button>
                          <div class="ga-options">
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="academic_extensive_knowledge"> Academic Excellence: Extensive knowledge in the chosen discipline with ability to apply it effectively </label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="domain_expertise"> Domain Expertise: Comprehensive specialist knowledge of the field of study and defined professional skills ensuring work readiness</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="problem_solving"> Problem solving: Making informed choices in a variety of situations, useful in a scholarly context that enables the students to understand and develop solutions</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="knowledge_application"> Knowledge Application: Ability to use available knowledge to make decisions and perform tasks</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="self_learning_research"> Self-Learning and research Skills: Ability to create new understanding and knowledge through the process of research and inquiry.</label>
                          </div>
                      </div>
                      <div class="ga-category">
                          <button type="button" class="ga-toggle">Professional Excellence</button>
                          <div class="ga-options">
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="professional_excellence"> Professional Excellence: Application of knowledge and its derivatives objectively and effectively accomplishing the organizational goals.</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="practical_skills"> Practical Skills: Ability to use theoretical knowledge in real-life situations.</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="creative_thinking"> Creative Thinking: Ability to look at problems or situations from a fresh or unorthodox perspective.</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="employability"> Employability: Denotes the academic and professional expertise along with the soft skills and pleasant demeanors necessary for success at a job.</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="entrepreneurship"> Entrepreneurship: Capacity and willingness to develop, organize and manage any value-adding venture along with any risk.</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="continuous_learning"> Continuous Learning: Also referred to as life-long learning, is the ongoing, voluntary, and self-motivated pursuit of knowledge for either personal or professional reasons.</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="analytical_skills"> Analytical Skills: Ability to firm up on the relevance of information and its interpretation towards planning, problem-solving or decision making.</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="critical_solution_thinking"> Critical and Solution-Oriented Thinking: Ability to objectively analyze and evaluate an issue or problem in order to form a judgement or solution</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="global_perspective"> Global Perspective: Recognition and appreciation of other cultures and recognizing the global context of an issue and/or perceptions in decision making</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="innovativeness"> Innovativeness: The skill and imagination to create new things/ideas/ methods to gain an organizational advantage</label>
                          </div>
                      </div>
                      <div class="ga-category">
                          <button type="button" class="ga-toggle">Personality</button>
                          <div class="ga-options">
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="personality"> Personality: Personality refers to individual differences in characteristics, patterns of thinking, feeling and behaving</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="self_awareness"> Self-Awareness: Ability to critically introspect on one's attitude, thoughts, feeling and behavior and their impact in life situations</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="emotional_self_regulation"> Emotional Self-Regulation: Ability to manage emotions effectively</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="self_esteem"> Self-Esteem: Confidence in one's own worth and abilities</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="humility"> Humility: Quality of having a modest or low view of one's importance, not influenced by ego</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="accessibility"> Accessibility: Quality of being approachable by others.</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="positive_attitude"> Positive Attitude: Mental perception of optimism that focuses on positive results</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="personal_integrity"> Personal Integrity: An innate moral conviction to stand against things that are not virtuous or morally right</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="adaptability"> Adaptability: Quality of being able to adjust to new conditions in any given circumstance</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="tolerance"> Tolerance: Ability or willingness to forbear the existence of opinions/behavior/development that one dislikes or disagrees with</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="peer_recognition"> Peer Recognition: Genuine expression of appreciation for or exchanged between team members/colleagues</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="sense_of_transcendence"> Sense of Transcendence: Ability to go beyond and connect to the Almighty through a sense of purpose, meaning, hope and gratitude</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="compassion"> Compassion: Genuine concern for others and their life situation</label>
                          </div>
                      </div>
                      <div class="ga-category">
                          <button type="button" class="ga-toggle">Leadership</button>
                          <div class="ga-options">
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="leadership"> Leadership: Ability to lead the action of a team or a group or an organization towards achieving the goals with voluntary participation by all</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="logical_resolution"> Logical Resolution of Issues: Attitude of logically resolving the issues which may consequently include questioning, observing physical reality, testing, hypothesizing, analyzing and communicating</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="self_confidence"> Self-Confidence: The belief in one's own capability</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="initiative"> Initiative: Self-motivation and willingness to do things or to get things done by one's own voluntary act</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="dynamism"> Dynamism: Quality of being proactive in terms of thoughts, tasks or responsibility</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="empathy"> Empathy: Capacity to understand or feel what another person is experiencing i.e., the capacity to place oneself in another's position</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="inclusiveness"> Inclusiveness: Quality of including different types of people and treating them fairly and equally</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="team_building"> Team Building Skills: Ability to motivate the team members and increase the overall performance of the team</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="facilitation"> Facilitation: Ability to guide the team members to achieve their task with minimum emphasis on criticism</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="consultative_decision_making"> Consultative Decision Making: Considering the views of others in decision making.</label>
                          </div>
                      </div>
                      <div class="ga-category">
                          <button type="button" class="ga-toggle">Communication</button>
                          <div class="ga-options">
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="communication"> Communication: Ability to convey intended meaning through the use of mutually understood means or methods</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="verbal_skills"> Verbal skills: Ability to speak, tell or write in simple understandable language set to a pleasant tone to ensure that the listener or reader is motivated to listen, follow or act</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="non_verbal_skills"> Non-Verbal Skills: Ability to convey information informally in an amicable manner without exchange of words</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="mutual_respect"> Mutual Respect: Ability to maintain decorum and mutual respect while communicating by signs and bodily expressions</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="listening"> Listening: Ability to be a good listener to accurately receive and interpret messages in the communication process</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="clarity_comprehensiveness"> Clarity and Comprehensiveness: Ability to communicate clearly and sequentially to ensure its full understanding to the reader with no scope for misunderstanding or confusion</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="assertiveness"> Assertiveness: Ability to stand up for one's own or other's viewpoints in a calm and positive way, without being either aggressive or passive.</label>
                          </div>
                      </div>
                      <div class="ga-category">
                          <button type="button" class="ga-toggle">Social Sensitivity</button>
                          <div class="ga-options">
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="social_sensitivity"> Social Sensitivity: Ability and willingness to perceive, understand and respect the feelings and viewpoints of members of the society and to recognize and respond to social issues.</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="respecting_diversity"> Respecting Diversity: Awareness of and insight into differences and diversity and treat them respectfully and equitably.</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="civic_sense"> Civic Sense: Responsibility of a person to encompass norms of society that help it run smoothly without disturbing others.</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="law_abiding"> Law Abiding: Awareness and voluntary compliance of lawful duties as a citizen of the country and not to carry out anything illegal.</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="cross_cultural_recognition"> Cross Cultural Recognition: Acknowledgement of and respect for equality, opportunity in recognition and appreciation of all other cultural beliefs.</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="knowledge_sharing"> Knowledge Sharing: Attitude to help and develop the underprivileged members of the society by spreading education.</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="environmental_sensitivity"> Environmental Sensitivity: Working to conserving natural environment in all areas and prevent its destruction.</label>
                              <label><input type="checkbox" name="needs_grad_attr_mapping" value="social_awareness_contribution"> Social Awareness and Contribution: Appreciating the role for removal of problems of the less privileged groups of the society and contribute towards their upliftment.</label>
                          </div>
                      </div>
                  </div>
                  <div class="help-text">Select relevant graduate attributes developed through this event</div>
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
                  <button type="button" id="sdg-select-btn" class="btn-select-sdg">Select SDG Goals</button>
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
function populateProposalData() {
    function fillEventRelevance() {
        if ($('#pos-pso-modern').length && window.PROPOSAL_DATA && window.PROPOSAL_DATA.pos_pso) {
            $('#pos-pso-modern').val(window.PROPOSAL_DATA.pos_pso);
        }
        if ($('#sdg-implementation-modern').length && window.PROPOSAL_DATA && window.PROPOSAL_DATA.sdg_goals) {
            $('#sdg-implementation-modern').val(window.PROPOSAL_DATA.sdg_goals);
        }
    }

    // Populate on load
    setTimeout(fillEventRelevance, 100);

    // Populate when section becomes active
    $(document).on('click', '[data-section="event-relevance"]', function() {
        setTimeout(fillEventRelevance, 100);
    });

    // Populate organizing committee details when section becomes active
    $(document).on('click', '[data-section="participants-information"]', function() {
        setTimeout(function() {
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
        }, 100);
    });
}

// Populate speaker reference card with speakers from the original proposal
function populateSpeakersFromProposal() {
    console.log('Populating speakers from proposal...');
    const container = document.getElementById('speakers-display');
    if (!container) {
        console.warn('Speakers container not found');
        return;
    }

    const speakers = (window.PROPOSAL_DATA && window.PROPOSAL_DATA.speakers) || window.EXISTING_SPEAKERS || [];
    console.log('Speakers data:', speakers);
    
    if (!speakers.length) {
        container.innerHTML = '<div class="no-speakers-message">No speakers were defined in the original proposal</div>';
        return;
    }

    let html = '';
    speakers.forEach(sp => {
        html += `
            <div class="speaker-reference-item">
                <div class="speaker-name">${sp.full_name || sp.name || ''}</div>
                <div class="speaker-affiliation">${sp.affiliation || sp.organization || ''}</div>
            </div>
        `;
    });
    container.innerHTML = html;
    console.log('Speakers populated successfully');
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
    $(document).on('click', '#sdgSave', function() {
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
        
        $('#sdg-implementation-modern').val(formattedSDGs);
        $('#sdgModal').hide();
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
  const url = modal.dataset.url;
  if(!url){
    alert('No organization set for this proposal.');
    return;
  }
  const field = document.getElementById('id_pos_pso_mapping');
  const selectedSet = new Set(
    (field ? field.value.split('\n') : [])
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
        data.pos.forEach(po => { addOption(container,'PO: ' + po.description, selectedSet); });
        data.psos.forEach(pso => { addOption(container,'PSO: ' + pso.description, selectedSet); });
      } else {
        container.textContent = 'No data';
      }
    })
    .catch(() => { container.textContent = 'Error loading'; });
}

function addOption(container, labelText, checkedSet){
  const lbl = document.createElement('label');
  const cb = document.createElement('input');
  cb.type = 'checkbox';
  cb.value = labelText;
  if(checkedSet && checkedSet.has(labelText)){
    cb.checked = true;
  }
  lbl.appendChild(cb);
  lbl.appendChild(document.createTextNode(' ' + labelText));
  container.appendChild(lbl);
  container.appendChild(document.createElement('br'));
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
    _outcomeSaveBtn.onclick = function(){
        const modal = document.getElementById('outcomeModal');
        if(!modal) return;
        const selected = Array.from(modal.querySelectorAll('input[type=checkbox]:checked')).map(c => c.value);
        const field = document.getElementById('id_pos_pso_mapping');
        if(!field) return;
        field.value = selected.join('\n');
        modal.classList.remove('show');
    };
}

function initAttachments(){
  const list = document.getElementById('attachment-list');
  const addBtn = document.getElementById('add-attachment-btn');
  const template = document.getElementById('attachment-template');
  const totalInput = document.querySelector('input[name$="-TOTAL_FORMS"]');
  if(!list || !addBtn || !template || !totalInput) return;

  function bind(block){
    const upload = block.querySelector('.attach-upload');
    const fileInput = block.querySelector('.file-input');
    const removeBtn = block.querySelector('.attach-remove');
    upload.addEventListener('click', () => {
      const img = upload.querySelector('img');
      if(img){
        openImageModal(img.src);
      } else {
        fileInput.click();
      }
    });
    fileInput.addEventListener('change', () => {
      if(fileInput.files && fileInput.files[0]){
        const url = URL.createObjectURL(fileInput.files[0]);
        upload.innerHTML = `<img src="${url}">`;
        upload.appendChild(removeBtn);
        removeBtn.style.display = 'flex';
      }
    });
    removeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      fileInput.value = '';
      upload.innerHTML = '<span class="attach-add">+</span>';
      removeBtn.style.display = 'none';
      const del = block.querySelector('input[name$="-DELETE"]');
      if(del) del.checked = true;
      if (window.ReportAutosaveManager) {
        ReportAutosaveManager.reinitialize();
      }
    });
  }

  list.querySelectorAll('.attachment-block').forEach(bind);

  addBtn.addEventListener('click', () => {
    const idx = +totalInput.value;
    const html = template.innerHTML.replace(/__prefix__/g, idx);
    const temp = document.createElement('div');
    temp.innerHTML = html.trim();
    const block = temp.firstElementChild;
    list.appendChild(block);
    totalInput.value = idx + 1;
    bind(block);
    if (window.ReportAutosaveManager) {
      ReportAutosaveManager.reinitialize();
    }
    block.querySelector('.file-input').click();
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
                <button type="button" class="remove-activity btn btn-sm btn-outline-danger">×</button>
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

    // Create and add "Add Activity" button dynamically
    const addBtn = document.createElement('button');
    addBtn.type = 'button';
    addBtn.className = 'btn-add-item';
    addBtn.textContent = 'Add Activity';
    addBtn.style.marginTop = '0.5rem';
    addBtn.addEventListener('click', () => {
        activities.push({ activity_name: '', activity_date: '' });
        render();
    });
    
    // Insert the button after the container
    container.parentNode.insertBefore(addBtn, container.nextSibling);

    // Always render the activities from proposal data
    render();
}

function setupAttendanceLink() {
    const attendanceField = $('#attendance-modern');
    if (!attendanceField.length) return;

    attendanceField.prop('readonly', true).css('cursor', 'pointer');
    const url = attendanceField.data('attendance-url');
    $(document).off('click', '#attendance-modern').on('click', '#attendance-modern', () => {
        if (url) {
            window.location.href = url;
        } else {
            alert('Save report to manage attendance via CSV');
        }
    });
}


function initializeAutosaveIndicators() {
    $(document).on('autosave:start', function() {
        const indicator = $('#autosave-indicator');
        indicator.removeClass('saved error').addClass('saving show');
        indicator.find('.indicator-text').text('Saving...');
    });

    $(document).on('autosave:success', function() {
        const indicator = $('#autosave-indicator');
        indicator.removeClass('saving error').addClass('saved');
        indicator.find('.indicator-text').text('Saved');
        setTimeout(() => {
            indicator.removeClass('show');
        }, 2000);
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
    if (window.ReportAutosaveManager) {
        ReportAutosaveManager.reinitialize();
    }
    initializeAutosaveIndicators();

    $('#report-form').on('submit', function() {
        if (loadingCount === 0) {
            showLoadingOverlay('Submitting...');
        }
    });
});

