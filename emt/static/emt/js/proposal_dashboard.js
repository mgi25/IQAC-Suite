// ===== MINIMAL TEXT SECTION VALIDATION =====
function validateTextSection() {
    // Find the first required textarea in the form panel
    const textarea = $('#form-panel-content textarea[required]').first();
    if (!textarea.length) return true;
    if (!textarea.val() || textarea.val().trim() === '') {
        showNotification('Please fill out the required field.', 'error');
        textarea.addClass('animate-shake');
        setTimeout(() => textarea.removeClass('animate-shake'), 600);
        return false;
    }
    return true;
}

// Updated Modern Proposal Dashboard JavaScript - ALL FUNCTIONALITY PRESERVED
$(document).ready(function() {
    // Log all organization type options on page load for debugging
    setTimeout(() => {
        const orgTypeSelect = $('#django-basic-info select[name="organization_type"]');
        if (orgTypeSelect.length) {
            const optionTexts = [];
            orgTypeSelect.find('option').each(function() {
                optionTexts.push($(this).text());
            });
            console.log('DEBUG: All org type options on page load:', optionTexts);
        } else {
            console.log('DEBUG: No org type select found on page load.');
        }
    }, 1000);
    console.log('Initializing dashboard...');

    // Add animation styles first
    addAnimationStyles();

    // Global state management - PRESERVED FROM ORIGINAL
    let currentExpandedCard = null;
    let sectionProgress = {
        'basic-info': false,
        'need-analysis': false,
        'objectives': false,
        'outcomes': false,
        'flow': false,
        'speakers': false,
        'expenses': false
    };

    // Initialize dashboard - PRESERVED
    initializeDashboard();

    function initializeDashboard() {
        console.log('Setting up dashboard...');
        setupFormHandling(); // Simplified for new UI
        updateProgressBar();
        loadExistingData();

        // Check for existing form errors and mark sections
        checkForExistingErrors();

        // Auto-start with basic-info section
        if (!$('.form-errors-banner').length) {
            setTimeout(() => {
                openFormPanel('basic-info');
            }, 500);
        }
    }

    function checkForExistingErrors() {
        // Check if form has errors and mark sections accordingly
        if ($('.form-errors-banner').length) {
            openFormPanel('basic-info');
        }
    }

    // ===== SIMPLIFIED FORM HANDLING FOR NEW UI =====
    function setupFormHandling() {
        // Navigation click handlers
        $('.nav-link:not(.disabled)').on('click', function(e) {
            e.preventDefault();
            const section = $(this).data('section');
            if (!$(this).hasClass('disabled')) {
                activateSection(section);
            }
        });

        // Save and continue button - PRESERVED FUNCTIONALITY
        $(document).off('click.saveSection').on('click.saveSection', '.btn-save-section', function(e) {
            e.preventDefault();
            e.stopPropagation();
            saveCurrentSection();
        });

        // Keyboard shortcuts - PRESERVED
        $(document).off('keydown.escapeClose').on('keydown.escapeClose', function(e) {
            if (e.which === 27) { // Escape key
                // Can be used for other purposes in simplified UI
            }
        });
    }

    function activateSection(section) {
        // Update navigation
        $('.nav-link').removeClass('active');
        $(`.nav-link[data-section="${section}"]`).addClass('active');

        // Load form content into panel
        loadFormContent(section);

        currentExpandedCard = section;

        // Mark as in progress if not already completed - PRESERVED
        if (!sectionProgress[section]) {
            markSectionInProgress(section);
        }

        // Focus on first input - PRESERVED
        setTimeout(() => {
            const firstInput = $('#form-panel-content').find('input:not([type="hidden"]), textarea, select').first();
            if (firstInput.length) {
                firstInput.focus();
            }
        }, 500);
    }

    // ===== FORM PANEL MANAGEMENT - ADAPTED FOR NEW UI =====
    function openFormPanel(section) {
        if (currentExpandedCard === section) return;

        console.log('Opening section:', section);

        // Load form content into panel
        loadFormContent(section);

        currentExpandedCard = section;

        // Mark as in progress if not already completed - PRESERVED
        if (!sectionProgress[section]) {
            markSectionInProgress(section);
        }

        // Focus on first input - PRESERVED
        setTimeout(() => {
            const firstInput = $('#form-panel-content').find('input:not([type="hidden"]), textarea, select').first();
            if (firstInput.length) {
                firstInput.focus();
            }
        }, 500);
    }

    // ===== FORM CONTENT LOADING - PRESERVED FUNCTIONALITY =====
    function loadFormContent(section) {
        // Update main headers
        const sectionData = getSectionData(section);
        $('#main-title').text(sectionData.title);
        $('#main-subtitle').text(sectionData.subtitle);

        // Load the appropriate form content - PRESERVED
        let formContent = '';

        switch (section) {
            case 'basic-info':
                formContent = getBasicInfoForm();
                break;
            case 'need-analysis':
                formContent = getNeedAnalysisForm();
                break;
            case 'objectives':
                formContent = getObjectivesForm();
                break;
            case 'outcomes':
                formContent = getOutcomesForm();
                break;
            case 'flow':
                formContent = getFlowForm();
                break;
            case 'speakers':
                formContent = getSpeakersForm();
                break;
            case 'expenses':
                formContent = getExpensesForm();
                break;
            default:
                formContent = '<div class="form-grid"><p>Form content for ' + section + ' is not yet implemented.</p></div>';
        }

        $('#form-panel-content').html(formContent);

        // Re-initialize components after loading content - PRESERVED
        setTimeout(() => {
            console.log('=== FORM CONTENT LOADED ===');
            console.log('Current section:', section);

            if (section === 'basic-info') {
                console.log('Setting up Django form integration...');
                setupDjangoFormIntegration();
            }

            // Setup section-specific form syncing - PRESERVED
            setupFormFieldSync();

            // Clear any existing validation errors from previous loads - PRESERVED
            clearValidationErrors();

            // IMPORTANT: Let autosave_draft.js handle autosave - PRESERVED
            if (window.AutosaveManager && window.AutosaveManager.reinitialize) {
                window.AutosaveManager.reinitialize();
                console.log('Reinitialize autosave manager');
            }

            console.log('=== FORM SETUP COMPLETE ===');
        }, 100);
    }

    // ===== SECTION DATA HELPER =====
    function getSectionData(section) {
        const sections = {
            'basic-info': { title: 'Basic Information', subtitle: 'Organization details and event basics' },
            'need-analysis': { title: 'Need Analysis', subtitle: 'Why is this event needed?' },
            'objectives': { title: 'Objectives', subtitle: 'What do you aim to achieve?' },
            'outcomes': { title: 'Expected Outcomes', subtitle: 'What results do you expect?' },
            'flow': { title: 'Tentative Flow', subtitle: 'Event timeline and schedule' },
            'speakers': { title: 'Speaker Profiles', subtitle: 'Add speaker details' },
            'expenses': { title: 'Expenses', subtitle: 'Event costs and expenditures' }
        };
        return sections[section] || { title: 'Section', subtitle: 'Complete this section' };
    }

    // ===== DJANGO FORM INTEGRATION - FULLY PRESERVED =====
    function setupDjangoFormIntegration() {
        console.log('Setting up Django form integration...');

        const djangoBasicInfo = $('#django-basic-info');

        // Organization Type with TomSelect - PRESERVED
        const orgTypeSelect = djangoBasicInfo.find('select[name="organization_type"]');
        if (orgTypeSelect.length) {
            const orgTypeField = $('#org-type-modern');
            const orgTypeInputHtml = `<input type="text" id="org-type-modern-input" placeholder="Type or select organization type..." autocomplete="off">`;
            orgTypeField.replaceWith(orgTypeInputHtml);
            const orgTypeInput = $('#org-type-modern-input');
            
            const orgTypeOptions = [];
            orgTypeSelect.find('option').each(function() {
                const val = $(this).val();
                const text = $(this).text();
                if (val && text && text.trim() !== '---------') {
                    orgTypeOptions.push({ value: val, text: text });
                }
            });

            if (typeof TomSelect !== 'undefined') {
                const orgTypeTS = new TomSelect(orgTypeInput[0], {
                    valueField: 'value',
                    labelField: 'text',
                    searchField: 'text',
                    options: orgTypeOptions,
                    create: false,
                    dropdownParent: 'body',
                    render: {
                        option: function(data, escape) {
                            return `<div class="ts-dropdown-option">${escape(data.text)}</div>`;
                        }
                    },
                    onChange: function(value) {
                        const selected = orgTypeOptions.find(opt => opt.value === value);
                        const selectedText = selected ? selected.text.toLowerCase().trim() : '';
                        orgTypeSelect.val(value).trigger('change');
                        handleOrgTypeChange(selectedText);
                        clearFieldError(orgTypeInput);
                    },
                    placeholder: 'Type or select organization type...',
                });

                if (orgTypeSelect.val()) {
                    orgTypeTS.setValue(orgTypeSelect.val());
                    const initialText = orgTypeOptions.find(opt => opt.value === orgTypeSelect.val())?.text?.toLowerCase().trim() || '';
                    handleOrgTypeChange(initialText, true);
                }
            }
        }
        
        // Copy other fields - PRESERVED
        copyDjangoField('event_title');
        copyDjangoField('event_datetime');
        copyDjangoField('venue');
        copyDjangoField('target_audience');
        copyDjangoField('event_focus_type');
        copyDjangoField('academic_year');
        copyDjangoField('student_coordinators');
        copyDjangoField('num_activities');
        
        setupFacultyTomSelect();
    }
    
    // ===== FACULTY TOMSELECT - FULLY PRESERVED =====
    function setupFacultyTomSelect() {
        const facultySelect = $('#faculty-select');
        const djangoFacultySelect = $('#django-basic-info [name="faculty_incharges"]');

        if (!facultySelect.length || !djangoFacultySelect.length) {
             console.log('Faculty select fields not found.');
             return;
        }

        const existingOptions = [];
        djangoFacultySelect.find('option').each(function() {
            if ($(this).val()) {
                existingOptions.push({
                    id: $(this).val(),
                    text: $(this).text()
                });
            }
        });

        if (typeof TomSelect === 'undefined') {
            console.log('TomSelect not available, using simple select for faculty.');
            facultySelect.html(djangoFacultySelect.html());
            facultySelect.prop('multiple', true);
            facultySelect.on('change', function() {
                djangoFacultySelect.val($(this).val());
            });
            return;
        }

        const tomselect = new TomSelect('#faculty-select', {
            plugins: ['remove_button'],
            valueField: 'id',
            labelField: 'text',
            searchField: 'text',
            create: false,
            placeholder: 'Type a faculty name…',
            maxItems: 10,
            options: existingOptions,
            load: function(query, callback) {
                if (!query.length) return callback();
                
                if (window.API_FACULTY) {
                    fetch(window.API_FACULTY + '?q=' + encodeURIComponent(query))
                        .then(response => response.json())
                        .then(data => callback(data))
                        .catch(() => callback());
                } else {
                    // Mock faculty data for testing
                    const mockFaculty = [
                        {id: 1, text: 'Dr. John Smith (Computer Science)'},
                        {id: 2, text: 'Prof. Jane Doe (Mathematics)'},
                        {id: 3, text: 'Dr. Mike Johnson (Physics)'}
                    ].filter(item => 
                        item.text.toLowerCase().includes(query.toLowerCase())
                    );
                    callback(mockFaculty);
                }
            }
        });
        
        if (window.AutosaveManager && window.AutosaveManager.registerTomSelect) {
            window.AutosaveManager.registerTomSelect('faculty-select', tomselect);
            console.log('Registered Faculty TomSelect with autosave manager');
        }

        tomselect.on('change', function() {
            const values = tomselect.getValue();
            djangoFacultySelect.val(values);
            console.log('Faculty select changed:', values);
            clearFieldError($('#faculty-select'));
        });

        const initialValues = djangoFacultySelect.val();
        if (initialValues && initialValues.length) {
            tomselect.setValue(initialValues);
        }
    }

    // ===== DJANGO FIELD COPYING - PRESERVED =====
    function copyDjangoField(fieldName) {
        const djangoField = $(`#django-basic-info [name="${fieldName}"]`);
        const modernField = $(`#${fieldName.replace(/_/g, '-')}-modern`);

        if (djangoField.length && modernField.length) {
            modernField.val(djangoField.val());

            if (djangoField.is('select') && modernField.is('select')) {
                modernField.html(djangoField.html());
                modernField.val(djangoField.val());
            }

            modernField.on('input change', function() {
                djangoField.val($(this).val());
                console.log(`Synced ${fieldName}:`, $(this).val());
                clearFieldError($(this));
            });

            const errors = djangoField.siblings('.error');
            if (errors.length) {
                modernField.data('django-errors', errors.text());
            }
        }
    }

    // ===== ORGANIZATION TYPE CHANGE HANDLER - PRESERVED =====
    function handleOrgTypeChange(orgType, preserveOrg = false) {
        console.log('=== ORG TYPE CHANGE DEBUG ===');
        console.log('Selected org type:', orgType);

        let normalizedOrgType = orgType ? orgType.toString().toLowerCase().replace(/[^a-z0-9]+/g, '').trim() : '';
        console.log('Normalized org type:', normalizedOrgType);

        $('.org-specific-field').remove();

        if (normalizedOrgType !== '') {
            createOrgField(normalizedOrgType, preserveOrg);
            const targetFieldId = `#org-${normalizedOrgType}-field`;
            let targetField = $(targetFieldId);
            if (targetField.length) {
                targetField.css('display', 'block').addClass('show');
            } else {
                console.error('FIELD NOT FOUND for org type:', normalizedOrgType);
            }
        }
        if (!preserveOrg) {
            $(`#django-basic-info [name="organization"]`).val('');
        }
        console.log('=== END ORG TYPE CHANGE DEBUG ===');
    }

    // ===== CREATE ORG FIELD - PRESERVED =====
    function createOrgField(orgType, preserveOrg) {
        console.log('Creating org field for:', orgType);
        const orgTypeMap = {
            department: { label: 'Department', placeholder: 'Type department name...' },
            club: { label: 'Club', placeholder: 'Type club name...' },
            association: { label: 'Association', placeholder: 'Type association name...' },
            center: { label: 'Center', placeholder: 'Type center name...' },
            cell: { label: 'Cell', placeholder: 'Type cell name...' }
        };

        let canonicalType = Object.keys(orgTypeMap).find(key => orgType.includes(key)) || orgType;

        const label = orgTypeMap[canonicalType]?.label || capitalizeFirst(canonicalType);
        const placeholder = orgTypeMap[canonicalType]?.placeholder || `Type ${canonicalType} name...`;

        const orgFieldHtml = `
            <div class="org-specific-field form-row" id="org-${canonicalType}-field" style="display: block;">
                <div class="input-group">
                    <label for="org-${canonicalType}-modern-select">${label} *</label>
                    <select id="org-${canonicalType}-modern-select" placeholder="${placeholder}"></select>
                </div>
            </div>
        `;

        const orgTypeInput = $('#org-type-modern-input');
        orgTypeInput.closest('.input-group').parent().after(orgFieldHtml);

        console.log('Created field for:', canonicalType);

        const newSelect = $(`#org-${canonicalType}-modern-select`);
        const hiddenField = $(`#django-basic-info [name="organization"]`);

        if (typeof TomSelect !== 'undefined' && newSelect.length) {
            const tom = new TomSelect(newSelect[0], {
                valueField: 'id',
                labelField: 'text',
                searchField: 'text',
                create: false,
                dropdownParent: 'body',
                load: function(query, callback) {
                    let url = window.API_ORGANIZATIONS + '?q=' + encodeURIComponent(query || '');
                    url += '&org_type=' + encodeURIComponent(label);
                    fetch(url)
                        .then(r => r.json())
                        .then(callback)
                        .catch(() => callback());
                },
                onChange: function(value) {
                    hiddenField.val(value);
                    clearFieldError(newSelect);
                },
                placeholder: placeholder,
            });

            const existingValue = preserveOrg ? hiddenField.val() : '';
            if (existingValue) {
                const existingText = hiddenField.find(`option[value="${existingValue}"]`).text();
                if (existingText) {
                    tom.addOption({ id: existingValue, text: existingText });
                    tom.setValue(existingValue);
                }
            }
        }
    }

    function capitalizeFirst(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
    
    // ===== FORM TEMPLATE FUNCTIONS - FULLY PRESERVED =====
    function getBasicInfoForm() {
        return `
            <div class="form-grid">
                <div class="form-row">
                    <div class="input-group">
                        <label for="org-type-modern-input">Type of Organisation *</label>
                        <div id="org-type-modern"> <select required><option value="">Select Organization Type</option></select>
                        </div>
                    </div>
                </div>

                <div class="form-row">
                    <div class="input-group">
                        <label for="event-title-modern">Event Title *</label>
                        <input type="text" id="event-title-modern" required>
                    </div>
                    <div class="input-group">
                        <label for="event-datetime-modern">Date & Time *</label>
                        <input type="datetime-local" id="event-datetime-modern" required>
                    </div>
                </div>

                <div class="form-row">
                    <div class="input-group">
                        <label for="venue-modern">Venue *</label>
                        <input type="text" id="venue-modern" required>
                    </div>
                    <div class="input-group">
                        <label for="target-audience-modern">Target Audience *</label>
                        <input type="text" id="target-audience-modern" required>
                    </div>
                </div>

                <div class="form-row">
                    <div class="input-group">
                        <label for="event-focus-type-modern">Event Focus Type</label>
                        <select id="event-focus-type-modern">
                            <option value="">Select Focus Type</option>
                        </select>
                    </div>
                    <div class="input-group">
                        <label for="academic-year-modern">Academic Year *</label>
                        <input type="text" id="academic-year-modern" placeholder="2024-2025" required>
                    </div>
                </div>

                <div class="form-row">
                    <div class="input-group">
                        <label for="student-coordinators-modern">Student Coordinators</label>
                        <input type="text" id="student-coordinators-modern">
                    </div>
                    <div class="input-group">
                        <label for="num-activities-modern">Number of Activities</label>
                        <input type="number" id="num-activities-modern" min="1">
                    </div>
                </div>

                <div class="form-row full-width">
                    <div class="input-group">
                        <label for="faculty-select">Faculty Incharges *</label>
                        <select id="faculty-select" multiple>
                            </select>
                    </div>
                </div>
                
                <div class="form-row full-width">
                    <div class="save-section-container">
                        <button type="button" class="btn-save-section">Save & Continue</button>
                        <div class="save-help-text">Complete this section to unlock the next one</div>
                    </div>
                </div>
            </div>
        `;
    }

    function getNeedAnalysisForm() {
        return `
            <div class="form-grid">
                <div class="form-row full-width">
                    <div class="input-group">
                        <label for="need-analysis-modern">Describe the need for this event *</label>
                        <textarea id="need-analysis-modern" rows="6" required placeholder="Explain why this event is necessary, what gap it fills, and its relevance to the target audience..."></textarea>
                        <div class="help-text">Provide a detailed explanation of why this event is important.</div>
                    </div>
                </div>
                <div class="form-row full-width">
                    <div class="save-section-container">
                        <button type="button" class="btn-save-section">Save & Continue</button>
                    </div>
                </div>
            </div>
        `;
    }

    function getObjectivesForm() {
        return `
            <div class="form-grid">
                <div class="form-row full-width">
                    <div class="input-group">
                        <label for="objectives-modern">List the main objectives *</label>
                        <textarea id="objectives-modern" rows="6" required placeholder="• Objective 1: ...&#10;• Objective 2: ...&#10;• Objective 3: ..."></textarea>
                        <div class="help-text">List 3-5 clear, measurable objectives.</div>
                    </div>
                </div>
                <div class="form-row full-width">
                    <div class="save-section-container">
                        <button type="button" class="btn-save-section">Save & Continue</button>
                    </div>
                </div>
            </div>
        `;
    }

    function getOutcomesForm() {
        return `
            <div class="form-grid">
                <div class="form-row full-width">
                    <div class="input-group">
                        <label for="outcomes-modern">Describe expected outcomes *</label>
                        <textarea id="outcomes-modern" rows="6" required placeholder="What specific results, skills, or benefits will participants gain?"></textarea>
                        <div class="help-text">Describe the tangible benefits for participants.</div>
                    </div>
                </div>
                <div class="form-row full-width">
                    <div class="save-section-container">
                        <button type="button" class="btn-save-section">Save & Continue</button>
                    </div>
                </div>
            </div>
        `;
    }

    function getFlowForm() {
        return `
            <div class="form-grid">
                <div class="form-row full-width">
                    <div class="input-group">
                        <label for="flow-modern">Event flow and timeline *</label>
                        <textarea id="flow-modern" rows="8" required placeholder="9:00 AM - Registration&#10;9:30 AM - Opening Ceremony..."></textarea>
                        <div class="help-text">Provide a detailed timeline for each activity.</div>
                    </div>
                </div>
                <div class="form-row full-width">
                    <div class="save-section-container">
                        <button type="button" class="btn-save-section">Save & Continue</button>
                    </div>
                </div>
            </div>
        `;
    }

    function getSpeakersForm() {
        return `
            <div class="form-grid">
                <div class="speakers-notice"><p>Speaker management is under development.</p></div>
                <div class="form-row full-width">
                    <div class="save-section-container">
                        <button type="button" class="btn-save-section">Mark as Complete</button>
                    </div>
                </div>
            </div>
        `;
    }

    function getExpensesForm() {
        return `
            <div class="form-grid">
                <div class="expenses-notice"><p>Expense management is under development.</p></div>
                <div class="form-row full-width">
                    <div class="save-section-container">
                        <button type="button" class="btn-save-section">Mark as Complete</button>
                    </div>
                </div>
            </div>
        `;
    }

    // ===== SAVE SECTION FUNCTIONALITY - FULLY PRESERVED =====
    function saveCurrentSection() {
        console.log('Saving section:', currentExpandedCard);
        if (!currentExpandedCard) return;

        if (validateCurrentSection()) {
            markSectionComplete(currentExpandedCard);
            if (window.AutosaveManager && window.AutosaveManager.manualSave) {
                window.AutosaveManager.manualSave();
            }
            showNotification('Section saved successfully!', 'success');
            
            const nextOrder = parseInt($(`[data-section="${currentExpandedCard}"]`).data('order')) + 1;
            const nextSection = getNextSection(currentExpandedCard);
            if (nextSection) {
                setTimeout(() => {
                    openFormPanel(nextSection);
                }, 1000);
            }
        } else {
            showNotification('Please complete all required fields.', 'error');
        }
    }

    // ===== SECTION NAVIGATION - PRESERVED =====
    function getNextSection(currentSection) {
        const sectionOrder = ['basic-info', 'need-analysis', 'objectives', 'outcomes', 'flow', 'speakers', 'expenses'];
        const currentIndex = sectionOrder.indexOf(currentSection);
        return currentIndex < sectionOrder.length - 1 ? sectionOrder[currentIndex + 1] : null;
    }

    // ===== FORM FIELD SYNC - FULLY PRESERVED =====
    function setupFormFieldSync() {
        $('#form-panel-content').on('input.sync change.sync', 'input, textarea, select', function() {
            const fieldId = $(this).attr('id');
            if (fieldId && fieldId.endsWith('-modern')) {
                const baseName = fieldId.replace('-modern', '').replace(/-/g, '_');
                const djangoField = $(`#django-forms [name="${baseName}"]`);
                if (djangoField.length) {
                    djangoField.val($(this).val());
                    console.log(`Synced ${baseName}:`, $(this).val());
                }
            }
            clearFieldError($(this));
        });
    }

    // ===== STATUS & PROGRESS FUNCTIONS - PRESERVED =====
    function markSectionInProgress(section) {
        sectionProgress[section] = 'in-progress';
        const navLink = $(`.nav-link[data-section="${section}"]`);
        navLink.addClass('in-progress').removeClass('completed');
        console.log(`Section ${section} marked as in progress`);
    }

    function markSectionComplete(section) {
        sectionProgress[section] = true;
        const navLink = $(`.nav-link[data-section="${section}"]`);
        navLink.addClass('completed').removeClass('in-progress');
        unlockNextSection(section);
        console.log(`Section ${section} marked as complete`);
        updateProgressBar();
        updateSubmitButton();
    }

    function unlockNextSection(section) {
        const currentNavLink = $(`.nav-link[data-section="${section}"]`);
        if (!currentNavLink.length) {
            console.warn('unlockNextSection: currentNavLink not found for section', section);
            return;
        }
        const currentOrder = parseInt(currentNavLink.data('order'));
        const nextOrder = currentOrder + 1;
        const nextNavLink = $(`.nav-link[data-order="${nextOrder}"]`);
        console.log('unlockNextSection:', {section, currentOrder, nextOrder, nextNavLinkLength: nextNavLink.length});
        if (nextNavLink.length) {
            if (nextNavLink.hasClass('disabled')) {
                nextNavLink.removeClass('disabled');
                // Optionally, add a visual cue
                nextNavLink.addClass('animate-bounce');
                setTimeout(() => nextNavLink.removeClass('animate-bounce'), 1000);
                console.log('unlockNextSection: nextNavLink unlocked', nextNavLink[0]);
            } else {
                console.log('unlockNextSection: nextNavLink already enabled', nextNavLink[0]);
            }
        } else {
            console.warn('unlockNextSection: nextNavLink not found for order', nextOrder);
        }
    }

    function updateSubmitButton() {
        const completedSections = Object.values(sectionProgress).filter(status => status === true).length;
        const totalSections = Object.keys(sectionProgress).length;
        
        if (completedSections === totalSections) {
            $('#submit-proposal-btn').prop('disabled', false);
            $('.submit-section').addClass('ready');
        }
    }

    // ===== VALIDATION FUNCTIONS - FULLY PRESERVED =====
    function validateCurrentSection() {
        if (!currentExpandedCard) return false;
        clearValidationErrors();

        switch (currentExpandedCard) {
            case 'basic-info': return validateBasicInfo();
            case 'need-analysis':
            case 'objectives':
            case 'outcomes':
            case 'flow': return validateTextSection();
            default: return true;
        }
    }

    function validateBasicInfo() {
        let isValid = true;

        // Check org type (which is now a TomSelect-backed input)
        const orgTypeInput = $('#org-type-modern-input');
        if (!orgTypeInput.val() || !orgTypeInput[0].tomselect?.getValue()) {
            showFieldError(orgTypeInput.parent(), 'Organization type is required');
            isValid = false;
        }

        // Check organization if org type is selected
        if (orgTypeInput.val()) {
            // Try select (TomSelect)
            let orgField = $(`.org-specific-field:visible select`);
            if (orgField.length) {
                if (!orgField[0].tomselect || !orgField[0].tomselect.getValue()) {
                    showFieldError(orgField.parent(), 'Organization selection is required');
                    isValid = false;
                }
            } else {
                // Fallback: check for input field
                orgField = $(`.org-specific-field:visible input`);
                if (orgField.length && (!orgField.val() || !orgField.val().trim())) {
                    showFieldError(orgField.parent(), 'Organization selection is required');
                    isValid = false;
                }
            }
        }
        
        $('#form-panel-content input[required], #form-panel-content textarea[required], #form-panel-content select[required]').each(function() {
            // Skip fields already handled or special cases
            const id = $(this).attr('id');
            if (
                id === 'faculty-select' ||
                id === 'event-focus-type-modern' ||
                $(this).closest('.org-specific-field').length ||
                (id && id.startsWith('org-type'))
            ) return;

            if (!$(this).val() || $(this).val().trim() === '') {
                const fieldName = $(this).closest('.input-group').find('label').text().replace(' *', '');
                showFieldError($(this), `${fieldName} is required`);
                isValid = false;
            }
        });
        
        // Special check for faculty select (TomSelect)
        const facultyTomSelect = $('#faculty-select')[0]?.tomselect;
        if (facultyTomSelect && facultyTomSelect.getValue().length === 0) {
            showFieldError(facultyTomSelect.$wrapper, 'At least one Faculty Incharge is required.');
            isValid = false;
        }

        return isValid;
    }

    // ===== LOAD EXISTING DATA - PRESERVED =====
    function loadExistingData() {
        let hasBasicData = false;
        $('#django-forms input, #django-forms textarea, #django-forms select').each(function() {
            let val = $(this).val();
            if (Array.isArray(val)) {
                val = val.length ? val[0] : '';
            }
            if (typeof val === 'string' && val.trim() !== '') {
                // A more robust check might be needed, but this is a simple start
                if ($(this).attr('name') === 'event_title') {
                    hasBasicData = true;
                    return false;
                }
            }
        });
        
        if (hasBasicData) {
            markSectionComplete('basic-info');
        }

        updateProgressBar();
    }

    // ===== KEYBOARD SHORTCUTS - PRESERVED =====
    $(document).on('keydown', function(e) {
        if (e.ctrlKey && e.which === 83) { // Ctrl + S
            e.preventDefault();
            if (window.AutosaveManager && window.AutosaveManager.manualSave) {
                window.AutosaveManager.manualSave();
                showNotification('Draft saved manually.', 'info');
            }
        }
        if (e.which === 27 && currentExpandedCard) { // Escape key
            // Could be used for other functionality in new UI
        }
    });

    // ===== NOTIFICATIONS - PRESERVED =====
    function showNotification(message, type = 'info') {
        const notification = $(`
            <div class="notification notification-${type}">
                <div style="font-weight: 600;">${$('<div>').text(message).html()}</div>
            </div>
        `);
        $('body').append(notification);
        setTimeout(() => {
            notification.addClass('show');
        }, 50);
        setTimeout(() => {
            notification.removeClass('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    window.showNotification = showNotification;

    // ===== UTILITY FUNCTIONS - PRESERVED =====
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // ===== PROGRESS BAR FUNCTION - PRESERVED =====
    function updateProgressBar() {
        const completedSections = Object.values(sectionProgress).filter(status => status === true).length;
        const totalSections = Object.keys(sectionProgress).length;
        const progressPercent = Math.round((completedSections / totalSections) * 100);
        
        // Update any progress indicators in new UI
        console.log(`Progress: ${progressPercent}% (${completedSections}/${totalSections} sections complete)`);
        
        // If there's a progress element, update it
        const progressFill = $('#overall-progress-fill');
        const progressText = $('#overall-progress-text');
        if (progressFill.length) {
            progressFill.css('width', progressPercent + '%');
        }
        if (progressText.length) {
            progressText.text(progressPercent + '% Complete');
        }
    }

    // ===== ERROR HANDLING FUNCTIONS - PRESERVED =====
    function clearFieldError(field) {
        if (field && field.length) {
            field.removeClass('has-error');
            field.closest('.input-group').removeClass('has-error');
        }
    }

    function clearValidationErrors() {
        $('.has-error').removeClass('has-error');
        $('.animate-shake').removeClass('animate-shake');
    }

    function showFieldError(field, message) {
        if (field && field.length) {
            field.addClass('has-error');
            field.closest('.input-group').addClass('has-error');
            
            // Could add error message display here
            console.warn('Validation error:', message);
        }
    }

    // ===== ADD ANIMATIONS CSS - PRESERVED =====
    function addAnimationStyles() {
        const animationStyles = `
            <style>
                @keyframes bounce { 0%, 20%, 53%, 80%, 100% { transform: translate3d(0,0,0); } 40%, 43% { transform: translate3d(0,-10px,0); } 70% { transform: translate3d(0,-5px,0); } 90% { transform: translate3d(0,-2px,0); } }
                @keyframes shake { 0%, 100% { transform: translateX(0); } 25% { transform: translateX(-5px); } 75% { transform: translateX(5px); } }
                .animate-bounce { animation: bounce 0.6s ease-in-out; }
                .animate-shake { animation: shake 0.5s ease-in-out; }
                
                .notification { position: fixed; top: 20px; right: 20px; background: white; padding: 1rem 1.5rem; border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.15); z-index: 1001; opacity: 0; transform: translateX(100%); transition: all 0.3s ease; max-width: 320px; }
                .notification.notification-success { border-left: 4px solid #22c55e; }
                .notification.notification-error { border-left: 4px solid #ef4444; }
                .notification.notification-info { border-left: 4px solid #264487; }
                .notification.show { opacity: 1; transform: translateX(0); }

                .org-specific-field { opacity: 0; transform: translateY(-10px); transition: all 0.3s ease; }
                .org-specific-field.show { opacity: 1; transform: translateY(0); }

                .has-error input, .has-error select, .has-error textarea { border-color: #ef4444 !important; }
                .has-error .ts-control { border-color: #ef4444 !important; }
            </style>
        `;
        $('head').append(animationStyles);
    }

    // ===== AUTOSAVE INTEGRATION - ENHANCED =====
    
    // Hook into autosave system if available
    if (window.autosaveDraft) {
        // Trigger autosave on form changes
        $('#form-panel-content').on('input change', 'input, textarea, select', debounce(function() {
            window.autosaveDraft();
        }, 1000));
    }

    // ===== FORM SUBMISSION HANDLING - PRESERVED =====
    $('#proposal-form').on('submit', function(e) {
        // Let the form submit naturally, but ensure all sections are synced
        console.log('Form submission - ensuring all data is synced');
        
        // Trigger any final validations
        if (!validateCurrentSection()) {
            e.preventDefault();
            showNotification('Please complete all required fields before submitting.', 'error');
            return false;
        }

        // Clear local storage on successful submission
        if (window.clearLocal && typeof window.clearLocal === 'function') {
            window.clearLocal();
        }

        console.log('Form submitted successfully');
    });

    // ===== INITIALIZE AUTOSAVE INDICATORS - PRESERVED =====
    function initializeAutosaveIndicators() {
        // Show autosave indicator when saving
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
            indicator.removeClass('saving saved').addClass('error');
            indicator.find('.indicator-text').text('Save Failed');
            setTimeout(() => {
                indicator.removeClass('show');
            }, 3000);
        });
    }

    // Initialize autosave indicators
    initializeAutosaveIndicators();

    console.log('Dashboard initialized successfully! 🚀');
    console.log('All original functionality preserved with new UI');
});