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
// Updated Modern Proposal Dashboard JavaScript
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

    // Global state management
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

    // Initialize dashboard
    initializeDashboard();

    function initializeDashboard() {
        console.log('Setting up dashboard...');
        setupCardExpansion();
        updateProgressBar();
        loadExistingData();

        // Check for existing form errors and mark sections
        checkForExistingErrors();

        // Auto-open first card if no errors
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

    // ===== CARD EXPANSION LOGIC =====
    function setupCardExpansion() {
        $(document).off('click.cardExpansion').on('click.cardExpansion', '.proposal-card:not(.disabled) .card-header', function(e) {
            e.preventDefault();
            e.stopPropagation();

            const card = $(this).closest('.proposal-card');
            const section = card.data('section');

            if (card.hasClass('disabled') || currentExpandedCard === section) {
                return;
            }

            openFormPanel(section);
        });

        // Close panel button
        $('#form-panel-close').off('click.panelClose').on('click.panelClose', function(e) {
            e.preventDefault();
            e.stopPropagation();
            closeFormPanel();
        });

        // Save and continue button
        $(document).off('click.saveSection').on('click.saveSection', '.btn-save-section', function(e) {
            e.preventDefault();
            e.stopPropagation();
            saveCurrentSection();
        });

        // Close on Escape key
        $(document).off('keydown.escapeClose').on('keydown.escapeClose', function(e) {
            if (e.which === 27 && currentExpandedCard) {
                closeFormPanel();
            }
        });
    }

    function openFormPanel(section) {
        if (currentExpandedCard === section) return;

        const card = $(`[data-section="${section}"]`);

        // Mark current card as active
        $('.proposal-card').removeClass('active');
        card.addClass('active');

        // Switch to split view
        $('.dashboard-container').addClass('split-view');

        // Load form content into panel
        loadFormContent(section);

        // Show the form panel
        $('#form-panel').addClass('active');

        currentExpandedCard = section;

        // Mark as in progress if not already completed
        if (!sectionProgress[section]) {
            markSectionInProgress(section);
        }

        setTimeout(() => {
            const firstInput = $('#form-panel-content').find('input:not([type="hidden"]), textarea, select').first();
            if (firstInput.length) {
                firstInput.focus();
            }
        }, 500);
    }

    function closeFormPanel() {
        // Hide the form panel
        $('#form-panel').removeClass('active');

        // Switch back to full grid view
        $('.dashboard-container').removeClass('split-view');

        // Remove active state from cards
        $('.proposal-card').removeClass('active');

        currentExpandedCard = null;
    }

    function loadFormContent(section) {
        // Update panel header
        const card = $(`[data-section="${section}"]`);
        const number = card.data('order');
        const title = card.find('.card-title').text();
        const subtitle = card.find('.card-subtitle').text();

        $('#form-panel-number').text(number);
        $('#form-panel-title').text(title);
        $('#form-panel-subtitle').text(subtitle);

        // Load the appropriate form content
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

        // Re-initialize components after loading content
        setTimeout(() => {
            console.log('=== FORM CONTENT LOADED ===');
            console.log('Current section:', section);

            if (section === 'basic-info') {
                console.log('Setting up Django form integration...');
                setupDjangoFormIntegration();
            }

            // Setup section-specific form syncing
            setupFormFieldSync();
            if (section === 'speakers') {
                setupSpeakerFormHandlers();
            }

            // Clear any existing validation errors from previous loads
            clearValidationErrors();

            // IMPORTANT: Let autosave_draft.js handle autosave
            if (window.AutosaveManager && window.AutosaveManager.reinitialize) {
                window.AutosaveManager.reinitialize();
                console.log('Reinitialize autosave manager');
            }

            console.log('=== FORM SETUP COMPLETE ===');
        }, 100);
    }

    // ===== DJANGO FORM INTEGRATION =====
    function setupDjangoFormIntegration() {
        console.log('Setting up Django form integration...');

        const djangoBasicInfo = $('#django-basic-info');

        // Organization Type with TomSelect
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
        
        // Copy other fields
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

    // Organization type change handler
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

    // Create org field with proper naming and TomSelect
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
    
    // ===== FORM TEMPLATE FUNCTIONS =====
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

    function speakerFormHtml(index) {
        return `
            <div class="speaker-form" data-index="${index}">
                <div class="form-row">
                    <div class="input-group">
                        <label for="form-${index}-full_name">Full Name *</label>
                        <input type="text" id="form-${index}-full_name" name="form-${index}-full_name" required>
                    </div>
                    <div class="input-group">
                        <label for="form-${index}-designation">Designation *</label>
                        <input type="text" id="form-${index}-designation" name="form-${index}-designation" required>
                    </div>
                </div>
                <div class="form-row">
                    <div class="input-group">
                        <label for="form-${index}-affiliation">Affiliation *</label>
                        <input type="text" id="form-${index}-affiliation" name="form-${index}-affiliation" required>
                    </div>
                    <div class="input-group">
                        <label for="form-${index}-contact_email">Email *</label>
                        <input type="email" id="form-${index}-contact_email" name="form-${index}-contact_email" required>
                    </div>
                </div>
                <div class="form-row">
                    <div class="input-group">
                        <label for="form-${index}-contact_number">Contact Number *</label>
                        <input type="text" id="form-${index}-contact_number" name="form-${index}-contact_number" required>
                    </div>
                    <div class="input-group">
                        <label for="form-${index}-photo">Photo</label>
                        <input type="file" id="form-${index}-photo" name="form-${index}-photo" accept="image/*">
                    </div>
                </div>
                <div class="form-row full-width">
                    <div class="input-group">
                        <label for="form-${index}-detailed_profile">Detailed Profile *</label>
                        <textarea id="form-${index}-detailed_profile" name="form-${index}-detailed_profile" rows="4" required></textarea>
                    </div>
                </div>
                <div class="form-row full-width text-right">
                    <button type="button" class="btn-remove-speaker">Remove Speaker</button>
                </div>
            </div>
        `;
    }

    function getSpeakersForm() {
        return `
            <form id="speakers-form" enctype="multipart/form-data">
                <input type="hidden" name="form-TOTAL_FORMS" value="1">
                <input type="hidden" name="form-INITIAL_FORMS" value="0">
                <input type="hidden" name="form-MIN_NUM_FORMS" value="0">
                <input type="hidden" name="form-MAX_NUM_FORMS" value="1000">
                <div id="speaker-forms">
                    ${speakerFormHtml(0)}
                </div>
                <div class="form-row full-width">
                    <button type="button" id="add-speaker-btn">Add Speaker</button>
                </div>
                <div class="form-row full-width">
                    <div class="save-section-container">
                        <button type="button" class="btn-save-section">Save & Continue</button>
                    </div>
                </div>
            </form>
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

    // ===== SAVE SECTION FUNCTIONALITY =====
    function saveCurrentSection() {
        console.log('Saving section:', currentExpandedCard);
        if (!currentExpandedCard) return;

        if (!validateCurrentSection()) {
            showNotification('Please complete all required fields.', 'error');
            return;
        }

        const section = currentExpandedCard;
        const formSelectors = {
            'need-analysis': '#need-analysis-form',
            'objectives': '#objectives-form',
            'outcomes': '#outcomes-form',
            'flow': '#flow-form',
            'speakers': '#speakers-form'
        };

        const urlBases = {
            'need-analysis': '/suite/need-analysis/',
            'objectives': '/suite/objectives/',
            'outcomes': '/suite/expected-outcomes/',
            'flow': '/suite/tentative-flow/',
            'speakers': '/suite/speaker-profile/'
        };

        if (formSelectors[section] && urlBases[section]) {
            if (!window.PROPOSAL_ID) {
                showNotification('Please save Basic Information first.', 'error');
                return;
            }

            const url = urlBases[section] + window.PROPOSAL_ID + '/';
            if (section === 'speakers') {
                const formEl = $(formSelectors[section])[0];
                const formData = new FormData(formEl);
                formData.append('csrfmiddlewaretoken', window.AUTOSAVE_CSRF);
                $.ajax({
                    url: url,
                    method: 'POST',
                    data: formData,
                    processData: false,
                    contentType: false,
                    success: function() {
                        finalizeSectionSave(section);
                    },
                    error: function() {
                        showNotification('Error saving section. Please try again.', 'error');
                    }
                });
            } else {
                const contentVal = $(`${formSelectors[section]} [name="content"]`).val();
                $.ajax({
                    url: url,
                    method: 'POST',
                    data: {
                        content: contentVal,
                        csrfmiddlewaretoken: window.AUTOSAVE_CSRF
                    },
                    success: function() {
                        finalizeSectionSave(section);
                    },
                    error: function() {
                        showNotification('Error saving section. Please try again.', 'error');
                    }
                });
            }
        } else {
            if (window.AutosaveManager && window.AutosaveManager.manualSave) {
                window.AutosaveManager.manualSave();
            }
            finalizeSectionSave(section);
        }
    }

    function finalizeSectionSave(section) {
        markSectionComplete(section);
        closeFormPanel();
        showNotification('Section saved successfully!', 'success');

        const nextOrder = parseInt($(`[data-section="${section}"]`).data('order')) + 1;
        const nextCard = $(`[data-order="${nextOrder}"]`);
        if (nextCard.length && !nextCard.hasClass('disabled')) {
            setTimeout(() => {
                openFormPanel(nextCard.data('section'));
            }, 1000);
        }
    }


    // ===== FORM FIELD SYNC =====
    function setupFormFieldSync() {
        const mappings = {
            'need-analysis-modern': '#need-analysis-form [name="content"]',
            'objectives-modern': '#objectives-form [name="content"]',
            'outcomes-modern': '#outcomes-form [name="content"]',
            'flow-modern': '#flow-form [name="content"]'
        };

        $('#form-panel-content').on('input.sync change.sync', 'input, textarea, select', function() {
            const fieldId = $(this).attr('id');
            const targetSelector = mappings[fieldId];

            if (targetSelector) {
                $(targetSelector).val($(this).val());
                console.log(`Synced ${fieldId} -> ${targetSelector}`);
            } else if (fieldId && fieldId.endsWith('-modern')) {
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

    function setupSpeakerFormHandlers() {
        const form = $('#speakers-form');
        if (!form.length) return;

        const container = $('#speaker-forms');
        const totalForms = form.find('input[name="form-TOTAL_FORMS"]');

        form.off('click.addSpeaker').on('click.addSpeaker', '#add-speaker-btn', function(e) {
            e.preventDefault();
            const index = parseInt(totalForms.val());
            container.append(speakerFormHtml(index));
            totalForms.val(index + 1);
        });

        container.off('click.removeSpeaker').on('click.removeSpeaker', '.btn-remove-speaker', function(e) {
            e.preventDefault();
            $(this).closest('.speaker-form').remove();
            const forms = container.children('.speaker-form');
            totalForms.val(forms.length);
            forms.each(function(i) {
                $(this).attr('data-index', i);
                $(this).find('input, textarea').each(function() {
                    const newName = $(this).attr('name').replace(/form-\d+-/, `form-${i}-`);
                    const newId = $(this).attr('id').replace(/form-\d+-/, `form-${i}-`);
                    $(this).attr({ name: newName, id: newId });
                });
            });
        });
    }

    // ===== STATUS & PROGRESS FUNCTIONS =====
    function markSectionInProgress(section) {
        const card = $(`[data-section="${section}"]`);
        const statusIcon = $(`#${section}-status`);
        card.removeClass('completed').addClass('in-progress');
        statusIcon.text('◐').attr('data-status', 'in-progress');
    }

    function markSectionComplete(section) {
        sectionProgress[section] = true;
        const card = $(`[data-section="${section}"]`);
        const statusIcon = $(`#${section}-status`);
        card.removeClass('in-progress').addClass('completed');
        statusIcon.text('✓').attr('data-status', 'completed');
        statusIcon.addClass('animate-bounce');
        setTimeout(() => statusIcon.removeClass('animate-bounce'), 1000);
        updateProgressBar();
        unlockNextSection(section);
    }

    // Unlock the next section card in the dashboard
    function unlockNextSection(section) {
        const currentCard = $(`[data-section="${section}"]`);
        if (!currentCard.length) {
            console.warn('unlockNextSection: currentCard not found for section', section);
            return;
        }
        const currentOrder = parseInt(currentCard.data('order'));
        const nextOrder = currentOrder + 1;
        const nextCard = $(`.proposal-card[data-order="${nextOrder}"]`);
        console.log('unlockNextSection:', {section, currentOrder, nextOrder, nextCardLength: nextCard.length});
        if (nextCard.length) {
            if (nextCard.hasClass('disabled')) {
                nextCard.removeClass('disabled');
                // Optionally, add a visual cue
                nextCard.addClass('animate-bounce');
                setTimeout(() => nextCard.removeClass('animate-bounce'), 1000);
                // Force reflow for some browsers
                nextCard[0].offsetHeight;
                console.log('unlockNextSection: nextCard unlocked', nextCard[0]);
            } else {
                console.log('unlockNextSection: nextCard already enabled', nextCard[0]);
            }
        } else {
            console.warn('unlockNextSection: nextCard not found for order', nextOrder);
        }
    }

    // ===== VALIDATION FUNCTIONS =====
    function validateCurrentSection() {
        if (!currentExpandedCard) return false;
        clearValidationErrors();

        switch (currentExpandedCard) {
            case 'basic-info': return validateBasicInfo();
            case 'need-analysis':
            case 'objectives':
            case 'outcomes':
            case 'flow': return validateTextSection();
            case 'speakers': return validateSpeakers();
            default: return true;
        }
    }

    function validateBasicInfo() {
        let isValid = true;

        // Check org type (which is now a TomSelect-backed input)
        const orgTypeInput = $('#org-type-modern-input');
        if (!orgTypeInput.val() || !orgTypeInput[0].tomselect.getValue()) {
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

    function validateSpeakers() {
        let isValid = true;
        $('#speakers-form').find('input[required], textarea[required]').each(function() {
            if (!$(this).val()) {
                showFieldError($(this), 'This field is required');
                isValid = false;
            }
        });
        return isValid;
    }

    // (Assuming validateTextSection, clearValidationErrors, showFieldError, updateProgressBar, unlockNextSection etc. exist and are correct)
    // ... other helper functions ...

    // ===== LOAD EXISTING DATA =====
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

    // ===== KEYBOARD SHORTCUTS =====
    $(document).on('keydown', function(e) {
        if (e.ctrlKey && e.which === 83) { // Ctrl + S
            e.preventDefault();
            if (window.AutosaveManager && window.AutosaveManager.manualSave) {
                window.AutosaveManager.manualSave();
                showNotification('Draft saved manually.', 'info');
            }
        }
        if (e.which === 27 && currentExpandedCard) { // Escape key
            closeFormPanel();
        }
    });

    // ===== NOTIFICATIONS =====
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

    // ===== UTILITY FUNCTIONS =====
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


    // ===== PROGRESS BAR FUNCTION (always defined) =====
    function updateProgressBar() {
        // No-op for now, but prevents ReferenceError and can be implemented later
    }
    if (typeof clearFieldError !== 'function') {
        window.clearFieldError = function() {};
    }
    if (typeof clearValidationErrors !== 'function') {
        window.clearValidationErrors = function() {};
    }

    // ===== ADD ANIMATIONS CSS =====
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
                .notification.notification-info { border-left: 4px solid #3b82f6; }
                .notification.show { opacity: 1; transform: translateX(0); }

                .org-specific-field { opacity: 0; transform: translateY(-10px); transition: all 0.3s ease; }
                .org-specific-field.show { opacity: 1; transform: translateY(0); }
            </style>
        `;
        $('head').append(animationStyles);
    }
    
    console.log('Dashboard initialized successfully! 🚀');

});