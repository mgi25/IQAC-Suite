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
      $(document).on('input', '#event-summary-modern', function() {
          const text = $(this).val().trim();
          const wordCount = text ? text.split(/\s+/).filter(word => word.length > 0).length : 0;
          $('#summary-word-count').text(wordCount);
          
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
      
      if (validateCurrentSection()) {
          markSectionComplete(currentSection);
          const nextSection = getNextSection(currentSection);
          
          if (nextSection) {
              enableSection(nextSection);
              activateSection(nextSection);
              showNotification('Section saved! Moving to next section', 'success');
          } else {
              showNotification('All sections completed!', 'success');
          }
      } else {
          showNotification('Please fill in all required fields', 'error');
      }
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
              // Special validation for multi-select
              if (!element.val() || element.val().length === 0) {
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
      } else {
          sectionState[el.name] = el.value;
      }
  });

  // Initial snapshot of any server-rendered fields
  document.querySelectorAll('form#report-form input[name], form#report-form textarea[name], form#report-form select[name]').forEach(el => {
      if(el.tagName === 'SELECT' && el.multiple){
          sectionState[el.name] = Array.from(el.selectedOptions).map(o => o.value);
      } else {
          sectionState[el.name] = el.value;
      }
  });
  
  function getEventInformationContent() {
      const selectedEventType = window.REPORT_ACTUAL_EVENT_TYPE || (window.PROPOSAL_DATA ? window.PROPOSAL_DATA.event_focus_type || '' : '');
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
                  <label for="event-type-modern">Actual Event Type *</label>
                  <select id="event-type-modern" name="actual_event_type" required>
                      <option value="">Select the type of event that was conducted</option>
                      <option value="Training Program" ${selectedEventType === 'Training Program' ? 'selected' : ''}>Training Program</option>
                      <option value="Workshop" ${selectedEventType === 'Workshop' ? 'selected' : ''}>Workshop</option>
                      <option value="Seminar" ${selectedEventType === 'Seminar' ? 'selected' : ''}>Seminar</option>
                      <option value="Conference" ${selectedEventType === 'Conference' ? 'selected' : ''}>Conference</option>
                      <option value="Guest Lecture" ${selectedEventType === 'Guest Lecture' ? 'selected' : ''}>Guest Lecture</option>
                      <option value="Webinar" ${selectedEventType === 'Webinar' ? 'selected' : ''}>Webinar</option>
                      <option value="Competition" ${selectedEventType === 'Competition' ? 'selected' : ''}>Competition</option>
                      <option value="Cultural Event" ${selectedEventType === 'Cultural Event' ? 'selected' : ''}>Cultural Event</option>
                      <option value="Sports Event" ${selectedEventType === 'Sports Event' ? 'selected' : ''}>Sports Event</option>
                      <option value="Exhibition" ${selectedEventType === 'Exhibition' ? 'selected' : ''}>Exhibition</option>
                      <option value="Panel Discussion" ${selectedEventType === 'Panel Discussion' ? 'selected' : ''}>Panel Discussion</option>
                      <option value="Hackathon" ${selectedEventType === 'Hackathon' ? 'selected' : ''}>Hackathon</option>
                      <option value="Field Trip" ${selectedEventType === 'Field Trip' ? 'selected' : ''}>Field Trip</option>
                      <option value="Other" ${selectedEventType === 'Other' ? 'selected' : ''}>Other</option>
                  </select>
                  <div class="help-text">Select the actual type of event that was conducted</div>
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
                  <button type="submit" name="save_draft" class="btn-draft-section">Save as Draft</button>
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
                  <button type="submit" name="save_draft" class="btn-draft-section">Save as Draft</button>
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
              <div class="input-group">
                  <label for="event-summary-modern">Summary of Overall Event *</label>
                  <textarea id="event-summary-modern" name="event_summary" rows="15" required 
                      placeholder="Provide a comprehensive summary of the event (minimum 500 words):&#10;&#10;• Event overview and objectives&#10;• Key activities and sessions conducted&#10;• Timeline and schedule of events&#10;• Participant engagement and interaction&#10;• Key highlights and memorable moments&#10;• Overall atmosphere and reception&#10;• Achievement of planned objectives&#10;• Any unexpected outcomes or learnings&#10;&#10;This should be a detailed narrative that captures the essence of the entire event."></textarea>
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
                  <button type="submit" name="save_draft" class="btn-draft-section">Save as Draft</button>
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
              <div class="input-group">
                  <label for="learning-outcomes-modern">Learning Outcomes Achieved *</label>
                  <textarea id="learning-outcomes-modern" name="learning_outcomes" rows="8" required 
                      placeholder="Describe the learning outcomes achieved by participants:&#10;&#10;• Knowledge gained: [Specific knowledge areas]&#10;• Skills developed: [Technical and soft skills]&#10;• Competencies enhanced: [Professional competencies]&#10;• Understanding improved: [Subject areas or concepts]&#10;&#10;Be specific about what participants learned and how it benefits them."></textarea>
                  <div class="help-text">Detail the specific learning outcomes achieved by participants</div>
              </div>
          </div>

          <!-- Feedback and Assessment Section -->
          <div class="form-section-header">
              <h3>Feedback and Assessment</h3>
          </div>

          <div class="form-row">
              <div class="input-group">
                  <label for="participant-feedback-modern">Participant Feedback *</label>
                  <textarea id="participant-feedback-modern" name="participant_feedback" rows="8" required 
                      placeholder="Summarize participant feedback:&#10;&#10;• Overall satisfaction rating: [X/10 or percentage]&#10;• Content quality feedback: [Summary]&#10;• Organization feedback: [Summary]&#10;• Suggestions received: [Key suggestions]&#10;• Testimonials: [Notable quotes]&#10;&#10;Include both quantitative and qualitative feedback."></textarea>
                  <div class="help-text">Summary of participant feedback and satisfaction</div>
              </div>
              <div class="input-group">
                  <label for="measurable-outcomes-modern">Measurable Outcomes *</label>
                  <textarea id="measurable-outcomes-modern" name="measurable_outcomes" rows="8" required 
                      placeholder="List quantifiable outcomes:&#10;&#10;• Attendance rate: [X% of expected participants]&#10;• Completion rate: [X% completed full program]&#10;• Assessment scores: [If applicable]&#10;• Certification issued: [Number of certificates]&#10;• Follow-up actions: [Concrete next steps]&#10;&#10;Focus on measurable and quantifiable results."></textarea>
                  <div class="help-text">Quantifiable and measurable outcomes from the event</div>
              </div>
          </div>

          <!-- Impact Assessment Section -->
          <div class="form-section-header">
              <h3>Impact Assessment</h3>
          </div>

          <div class="form-row full-width">
              <div class="input-group">
                  <label for="impact-assessment-modern">Short-term and Long-term Impact *</label>
                  <textarea id="impact-assessment-modern" name="impact_assessment" rows="10" required 
                      placeholder="Assess the impact of the event:&#10;&#10;Short-term Impact:&#10;• Immediate learning and awareness gains&#10;• Networking connections established&#10;• Skills immediately applicable&#10;&#10;Long-term Impact:&#10;• Career development opportunities&#10;• Research collaborations initiated&#10;• Behavioral changes expected&#10;• Contribution to academic/professional growth&#10;&#10;Provide evidence-based assessment where possible."></textarea>
                  <div class="help-text">Assess both immediate and long-term impact on participants and institution</div>
              </div>
          </div>

          <!-- Save Section -->
          <div class="form-row full-width">
              <div class="save-section-container">
                  <button type="button" class="btn-save-section">Save & Continue</button>
                  <button type="submit" name="save_draft" class="btn-draft-section">Save as Draft</button>
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
              <div class="input-group">
                  <label for="objective-achievement-modern">Achievement of Planned Objectives *</label>
                  <textarea id="objective-achievement-modern" name="objective_achievement" rows="10" required 
                      placeholder="Analyze how well the event achieved its planned objectives:&#10;&#10;Original Objectives:&#10;• Objective 1: [Status - Fully/Partially/Not Achieved]&#10;  Analysis: [Detailed explanation]&#10;&#10;• Objective 2: [Status - Fully/Partially/Not Achieved]&#10;  Analysis: [Detailed explanation]&#10;&#10;Overall Achievement Rate: [X%]&#10;Factors contributing to success/challenges: [Analysis]"></textarea>
                  <div class="help-text">Detailed analysis of how well planned objectives were achieved</div>
              </div>
          </div>

          <!-- Strengths and Challenges Analysis Section -->
          <div class="form-section-header">
              <h3>Strengths and Challenges Analysis</h3>
          </div>

          <div class="form-row">
              <div class="input-group">
                  <label for="strengths-analysis-modern">Strengths and Successes *</label>
                  <textarea id="strengths-analysis-modern" name="strengths_analysis" rows="8" required 
                      placeholder="Identify and analyze the key strengths:&#10;&#10;• Organizational strengths: [What worked well in planning/execution]&#10;• Content strengths: [Quality of sessions, speakers, materials]&#10;• Participant engagement: [What kept participants engaged]&#10;• Infrastructure/logistics: [What supported the event well]&#10;• Team collaboration: [How the team worked effectively]&#10;&#10;Provide specific examples and evidence."></textarea>
                  <div class="help-text">Analyze what worked well and contributed to success</div>
              </div>
              <div class="input-group">
                  <label for="challenges-analysis-modern">Challenges and Areas for Improvement *</label>
                  <textarea id="challenges-analysis-modern" name="challenges_analysis" rows="8" required 
                      placeholder="Identify challenges faced and areas for improvement:&#10;&#10;• Organizational challenges: [Planning, coordination issues]&#10;• Technical challenges: [Equipment, platform, connectivity]&#10;• Participant-related challenges: [Attendance, engagement]&#10;• Content/delivery challenges: [Session quality, timing]&#10;• Resource constraints: [Budget, time, personnel]&#10;&#10;For each challenge, suggest specific improvements."></textarea>
                  <div class="help-text">Honest assessment of challenges and improvement opportunities</div>
              </div>
          </div>

          <!-- Effectiveness Analysis Section -->
          <div class="form-section-header">
              <h3>Effectiveness Analysis</h3>
          </div>

          <div class="form-row full-width">
              <div class="input-group">
                  <label for="effectiveness-analysis-modern">Overall Effectiveness Analysis *</label>
                  <textarea id="effectiveness-analysis-modern" name="effectiveness_analysis" rows="10" required 
                      placeholder="Provide a comprehensive effectiveness analysis:&#10;&#10;Methodology Used:&#10;• Data collection methods: [Surveys, interviews, observations]&#10;• Metrics evaluated: [Attendance, satisfaction, learning gains]&#10;&#10;Effectiveness Rating: [X/10 or percentage]&#10;&#10;Key Findings:&#10;• Most effective aspects: [What worked exceptionally well]&#10;• Least effective aspects: [What needs significant improvement]&#10;• Unexpected findings: [Surprising results or outcomes]&#10;&#10;Evidence-based analysis with specific data points where available."></textarea>
                  <div class="help-text">Comprehensive analysis of event effectiveness with supporting evidence</div>
              </div>
          </div>

          <!-- Lessons Learned Section -->
          <div class="form-section-header">
              <h3>Lessons Learned and Insights</h3>
          </div>

          <div class="form-row full-width">
              <div class="input-group">
                  <label for="lessons-learned-modern">Lessons Learned and Future Insights *</label>
                  <textarea id="lessons-learned-modern" name="lessons_learned" rows="10" required 
                      placeholder="Document key lessons learned and insights for future events:&#10;&#10;Key Lessons Learned:&#10;• Planning phase: [What to do differently in planning]&#10;• Execution phase: [What to improve in delivery]&#10;• Participant management: [Better engagement strategies]&#10;• Resource management: [More efficient resource utilization]&#10;&#10;Actionable Insights:&#10;• Best practices to replicate: [Successful strategies to repeat]&#10;• Practices to avoid: [What didn't work and should be avoided]&#10;• Innovation opportunities: [New approaches to try]&#10;&#10;Recommendations for future similar events."></textarea>
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
                  <button type="submit" name="save_draft" class="btn-draft-section">Save as Draft</button>
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
              <div class="input-group">
                  <label for="pos-pso-modern">PO's and PSO's Management *</label>
                  <textarea id="pos-pso-modern" name="pos_pso" rows="15" required 
                      placeholder="Describe how the event addresses Program Outcomes (POs) and Program Specific Outcomes (PSOs):&#10;&#10;Program Outcomes:&#10;• PO1: Engineering Knowledge&#10;• PO2: Problem Analysis&#10;• PO3: Design/Development of Solutions&#10;&#10;Program Specific Outcomes:&#10;• PSO1: [Specific to your program]&#10;• PSO2: [Specific to your program]&#10;&#10;Provide detailed explanation of how each relevant outcome was addressed through this event."></textarea>
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
                  <select id="graduate-attributes-modern" name="graduate_attributes" multiple class="graduate-attributes-select" required>
                      <option value="engineering_knowledge">Engineering Knowledge</option>
                      <option value="problem_analysis">Problem Analysis</option>
                      <option value="design_solutions">Design/Development of Solutions</option>
                      <option value="investigation">Conduct Investigations</option>
                      <option value="modern_tools">Modern Tool Usage</option>
                      <option value="engineer_society">The Engineer and Society</option>
                      <option value="environment_sustainability">Environment and Sustainability</option>
                      <option value="ethics">Ethics</option>
                      <option value="individual_teamwork">Individual and Team Work</option>
                      <option value="communication">Communication</option>
                      <option value="project_management">Project Management and Finance</option>
                      <option value="lifelong_learning">Life-long Learning</option>
                  </select>
                  <div class="help-text">Select relevant graduate attributes developed through this event</div>
              </div>
          </div>
          
          <div class="form-row">
              <div class="input-group">
                  <label for="contemporary-requirements-modern">Contemporary Requirements *</label>
                  <textarea id="contemporary-requirements-modern" name="contemporary_requirements" rows="12" required 
                      placeholder="Describe how the event addresses contemporary requirements:&#10;&#10;• Employability enhancement&#10;• Entrepreneurship development&#10;• Skill development initiatives&#10;• Industry 4.0 readiness&#10;• Digital transformation skills&#10;• Innovation and creativity&#10;• Leadership and soft skills&#10;• Global competency development&#10;&#10;Provide specific examples of how these requirements were addressed."></textarea>
                  <div class="help-text">Explain how the event addresses employability, entrepreneurship, skill development, etc.</div>
              </div>
              
              <div class="input-group">
                  <label for="sdg-implementation-modern">SDG Implementation *</label>
                  <textarea id="sdg-implementation-modern" name="sdg_goals" rows="10" required 
                      placeholder="Click 'Select SDG Goals' to choose from the 17 Sustainable Development Goals&#10;&#10;Selected goals will appear here and can be edited:&#10;&#10;You can modify the SDG selection or add additional context about how your event addresses these goals."></textarea>
                  <button type="button" id="sdg-select-btn" class="btn-select-sdg">Select SDG Goals</button>
                  <div class="help-text">Sustainable Development Goals addressed by this event (editable)</div>
              </div>
          </div>

          <!-- Save Section -->
          <div class="form-row full-width">
              <div class="save-section-container">
                  <button type="button" class="btn-save-section">Save & Continue</button>
                  <button type="submit" name="save_draft" class="btn-draft-section">Save as Draft</button>
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
    // Populate PO/PSO field when section becomes active
    $(document).on('click', '[data-section="event-relevance"]', function() {
        setTimeout(function() {
            if ($('#pos-pso-modern').length && window.PROPOSAL_DATA && window.PROPOSAL_DATA.pos_pso) {
                $('#pos-pso-modern').val(window.PROPOSAL_DATA.pos_pso);
            }
            if ($('#sdg-implementation-modern').length && window.PROPOSAL_DATA && window.PROPOSAL_DATA.sdg_goals) {
                $('#sdg-implementation-modern').val(window.PROPOSAL_DATA.sdg_goals);
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
  modal.classList.add('show');
  container.textContent = 'Loading...';
  fetch(url)
    .then(r => r.json())
    .then(data => {
      if(data.success){
        container.innerHTML = '';
        data.pos.forEach(po => { addOption(container,'PO: ' + po.description); });
        data.psos.forEach(pso => { addOption(container,'PSO: ' + pso.description); });
      } else {
        container.textContent = 'No data';
      }
    })
    .catch(() => { container.textContent = 'Error loading'; });
}

function addOption(container, labelText){
  const lbl = document.createElement('label');
  const cb = document.createElement('input');
  cb.type = 'checkbox';
  cb.value = labelText;
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
        let existing = field.value.trim();
        if(existing){ existing += '\n'; }
        field.value = existing + selected.join('\n');
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
    });
    
    // Handle committee member removal
    $(document).on('click', '.remove-committee-member', function() {
        $(this).closest('.committee-member-group').remove();
        
        // Renumber remaining members
        $('#committee-members-container .committee-member-group').each(function(index) {
            $(this).find('h6').text(`Committee Member ${index + 1}`);
        });
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
                    <label for="activity_name_${idx + 1}" class="activity-label">Activity ${idx + 1} Name</label>
                    <input type="text" id="activity_name_${idx + 1}" name="activity_name_${idx + 1}" value="${act.activity_name || ''}">
                </div>
                <div class="input-group">
                    <label for="activity_date_${idx + 1}" class="date-label">Activity ${idx + 1} Date</label>
                    <input type="date" id="activity_date_${idx + 1}" name="activity_date_${idx + 1}" value="${act.activity_date || ''}">
                </div>
                <button type="button" class="remove-activity" data-index="${idx}">Remove</button>
            `;
            container.appendChild(row);
        });
        numInput.value = activities.length;
        console.log('Activities rendered successfully, count:', activities.length);
    }

    container.addEventListener('click', (e) => {
        if (e.target.classList.contains('remove-activity')) {
            const index = parseInt(e.target.dataset.index, 10);
            activities.splice(index, 1);
            render();
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

function setupAttendanceModal() {
    const attendanceField = $('#attendance-modern');
    const modal = $('#attendanceModal');
    const notesField = $('#attendance-data');
    const participantInput = $('#num-participants-modern');
    const volunteerInput = $('#num-volunteers-modern');

    if (!attendanceField.length || !modal.length) return;

    // Populate field from existing data
    if (notesField.val()) {
        try {
            const existing = JSON.parse(notesField.val());
            attendanceField.val(existing.map(p => p.name).join(', '));
            participantInput.val(existing.length);
        } catch (e) {
            // ignore
        }
    }

    attendanceField.prop('readonly', true).css('cursor', 'pointer');
    $(document).off('click', '#attendance-modern').on('click', '#attendance-modern', openAttendanceModal);
    $('#attendanceCancel').off('click').on('click', () => modal.removeClass('show'));

    function openAttendanceModal() {
        const container = $('#attendanceOptions');
        modal.addClass('show');
        $('#attendanceSave').hide();

        let available = [];
        let selected = [];
        let userAvailable = [];
        let userSelected = [];
        let currentType = null;
        let classStudentMap = {};
        let departmentFacultyMap = {};

        container.html(`
            <div id="attendanceStep1">
                <div class="audience-type-selector">
                    <button type="button" data-type="students">Students</button>
                    <button type="button" data-type="faculty">Faculty</button>
                </div>
                <div class="dual-list" id="attendanceGroupList" style="display:none;">
                    <div class="dual-list-column">
                        <input type="text" id="attendanceAvailableSearch" placeholder="Search available">
                        <select id="attendanceAvailable" multiple></select>
                    </div>
                    <div class="dual-list-controls">
                        <button type="button" id="attendanceAddAll">&raquo;</button>
                        <button type="button" id="attendanceAdd">&gt;</button>
                        <button type="button" id="attendanceRemove">&lt;</button>
                        <button type="button" id="attendanceRemoveAll">&laquo;</button>
                    </div>
                    <div class="dual-list-column">
                        <input type="text" id="attendanceSelectedSearch" placeholder="Search selected">
                        <select id="attendanceSelected" multiple></select>
                    </div>
                </div>
                <button type="button" id="attendanceContinue" class="btn-continue" style="display:none;">Continue</button>
            </div>
            <div id="attendanceStep2" style="display:none;">
                <div class="dual-list user-list" id="attendeeUserList">
                    <div class="dual-list-column">
                        <input type="text" id="attendeeAvailableSearch" placeholder="Search available">
                        <select id="attendeeAvailable" multiple></select>
                    </div>
                    <div class="dual-list-controls">
                        <button type="button" id="attendeeAdd">&gt;</button>
                        <button type="button" id="attendeeRemove">&lt;</button>
                    </div>
                    <div class="dual-list-column">
                        <input type="text" id="attendeeSelectedSearch" placeholder="Search selected">
                        <select id="attendeeSelected" multiple></select>
                    </div>
                </div>
                <div class="audience-custom">
                    <select id="attendanceCustomInput" placeholder="Add custom participant"></select>
                </div>
                <button type="button" id="attendanceBack" class="btn-continue">Back</button>
            </div>
        `);

        const listContainer = container.find('#attendanceGroupList');
        const availableSelect = container.find('#attendanceAvailable');
        const selectedSelect = container.find('#attendanceSelected');
        const userListContainer = container.find('#attendeeUserList');
        const userAvailableSelect = container.find('#attendeeAvailable');
        const userSelectedSelect = container.find('#attendeeSelected');
        const step1 = container.find('#attendanceStep1');
        const step2 = container.find('#attendanceStep2');
        const continueBtn = container.find('#attendanceContinue');
        const backBtn = container.find('#attendanceBack');

        function filterOptions(input, select) {
            const term = input.val().toLowerCase();
            select.find('option').each(function() {
                const txt = $(this).text().toLowerCase();
                $(this).toggle(txt.includes(term));
            });
        }

        function renderLists() {
            availableSelect.empty();
            selectedSelect.empty();
            available.forEach(item => {
                availableSelect.append($('<option>').val(item.id).text(item.name));
            });
            selected.forEach(item => {
                selectedSelect.append($('<option>').val(item.id).text(item.name));
            });
            filterOptions($('#attendanceSelectedSearch'), selectedSelect);
        }

        function renderUserLists() {
            userAvailableSelect.empty();
            userSelectedSelect.empty();
            userAvailable.forEach(u => {
                userAvailableSelect.append($('<option>').val(u.id).text(u.name));
            });
            userSelected.forEach(u => {
                userSelectedSelect.append($('<option>').val(u.id).text(u.name));
            });
            filterOptions($('#attendeeSelectedSearch'), userSelectedSelect);
        }

        function updateUserLists() {
            userAvailable = [];
            if (currentType === 'students') {
                selected.forEach(cls => {
                    (classStudentMap[cls.id] || []).forEach(stu => {
                        if (!userSelected.some(u => u.id === `stu-${stu.id}`) &&
                            !userAvailable.some(u => u.id === `stu-${stu.id}`)) {
                            userAvailable.push({ id: `stu-${stu.id}`, name: stu.name });
                        }
                    });
                });
            } else if (currentType === 'faculty') {
                selected.forEach(dept => {
                    (departmentFacultyMap[dept.id] || []).forEach(fac => {
                        if (!userSelected.some(u => u.id === `fac-${fac.id}`) &&
                            !userAvailable.some(u => u.id === `fac-${fac.id}`)) {
                            userAvailable.push({ id: `fac-${fac.id}`, name: fac.name });
                        }
                    });
                });
            }
            renderUserLists();
        }

        function loadAvailable(term = '') {
            available = [];
            const orgId = window.PROPOSAL_ORG_ID;
            const orgName = window.PROPOSAL_ORG_NAME;
            if (!orgId) {
                availableSelect.html('<option>No organization</option>');
                return;
            }
            if (currentType === 'students') {
                classStudentMap = {};
                fetch(`${window.API_CLASSES_BASE}${orgId}/?q=${encodeURIComponent(term)}`, { credentials: 'include' })
                    .then(r => r.json())
                    .then(data => {
                        if (data.success && data.classes.length) {
                            data.classes.forEach(cls => {
                                classStudentMap[String(cls.id)] = cls.students || [];
                                available.push({ id: String(cls.id), name: cls.name });
                            });
                            renderLists();
                        } else {
                            availableSelect.html('<option>No classes</option>');
                        }
                    })
                    .catch(() => {
                        availableSelect.html('<option>Error loading</option>');
                    });
            } else if (currentType === 'faculty') {
                departmentFacultyMap = {};
                fetch(`${window.API_FACULTY}?org_id=${orgId}&q=${encodeURIComponent(term)}`, { credentials: 'include' })
                    .then(r => r.json())
                    .then(data => {
                        data.forEach(f => {
                            const dept = f.department || 'General';
                            if (!departmentFacultyMap[dept]) departmentFacultyMap[dept] = [];
                            departmentFacultyMap[dept].push({ id: f.id, name: f.name });
                        });
                        available = Object.keys(departmentFacultyMap).map(dept => ({ id: dept, name: dept }));
                        available.sort((a, b) => a.name.localeCompare(b.name));
                        renderLists();
                    })
                    .catch(() => {
                        availableSelect.html('<option>Error loading</option>');
                    });
            }
        }

        container.find('button[data-type]').on('click', function() {
            currentType = $(this).data('type');
            available = [];
            selected = [];
            listContainer.show();
            continueBtn.show();
            step2.hide();
            $('#attendanceSave').hide();
            loadAvailable('');
        });

        container.on('click', '#attendanceAdd', function() {
            const ids = availableSelect.val() || [];
            ids.forEach(id => {
                const idx = available.findIndex(it => it.id === id);
                if (idx > -1) {
                    selected.push(available[idx]);
                    available.splice(idx, 1);
                }
            });
            renderLists();
        });

        container.on('click', '#attendanceAddAll', function() {
            selected = selected.concat(available);
            available = [];
            renderLists();
        });

        container.on('click', '#attendanceRemove', function() {
            const ids = selectedSelect.val() || [];
            ids.forEach(id => {
                const idx = selected.findIndex(it => it.id === id);
                if (idx > -1) {
                    available.push(selected[idx]);
                    selected.splice(idx, 1);
                }
            });
            renderLists();
        });

        container.on('click', '#attendanceRemoveAll', function() {
            available = available.concat(selected);
            selected = [];
            renderLists();
        });

        continueBtn.on('click', function() {
            updateUserLists();
            step1.hide();
            step2.show();
            continueBtn.hide();
            $('#attendanceSave').show();
        });

        backBtn.on('click', function() {
            step2.hide();
            step1.show();
            continueBtn.show();
            $('#attendanceSave').hide();
        });

        const customTS = new TomSelect('#attendanceCustomInput', {
            persist: false,
            create: true,
            onItemAdd(value, text) {
                userSelected.push({ id: `custom-${Date.now()}`, name: text });
                customTS.clear();
                renderUserLists();
            }
        });

        container.on('input', '#attendanceAvailableSearch', function() {
            const term = $(this).val().trim();
            if (currentType) loadAvailable(term);
        });

        container.on('input', '#attendanceSelectedSearch', function() {
            filterOptions($(this), selectedSelect);
        });

        container.on('click', '#attendeeAdd', function() {
            const ids = userAvailableSelect.val() || [];
            ids.forEach(id => {
                const idx = userAvailable.findIndex(u => u.id === id);
                if (idx > -1) {
                    userSelected.push(userAvailable[idx]);
                    userAvailable.splice(idx, 1);
                }
            });
            renderUserLists();
        });

        container.on('click', '#attendeeRemove', function() {
            const ids = userSelectedSelect.val() || [];
            ids.forEach(id => {
                const idx = userSelected.findIndex(u => u.id === id);
                if (idx > -1) {
                    userAvailable.push(userSelected[idx]);
                    userSelected.splice(idx, 1);
                }
            });
            renderUserLists();
        });

        container.on('input', '#attendeeAvailableSearch', function() {
            const term = $(this).val().toLowerCase();
            userAvailableSelect.find('option').each(function() {
                const txt = $(this).text().toLowerCase();
                $(this).toggle(txt.includes(term));
            });
        });

        container.on('input', '#attendeeSelectedSearch', function() {
            filterOptions($(this), userSelectedSelect);
        });

        $('#attendanceSave').off('click').on('click', () => {
            const data = userSelected.map(u => ({ name: u.name }));
            notesField.val(JSON.stringify(data)).trigger('change').trigger('input');
            attendanceField.val(data.map(d => d.name).join(', ')).trigger('change').trigger('input');
            participantInput.val(data.length).trigger('change').trigger('input');
            volunteerInput.val(0).trigger('change').trigger('input');
            modal.removeClass('show');
        });
    }
}

// Initialize section-specific handlers when document is ready
$(document).ready(function() {
    initializeSectionSpecificHandlers();
    setupDynamicActivities();
    setupAttendanceModal();
});

