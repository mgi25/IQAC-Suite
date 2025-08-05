// ===== MINIMAL TEXT SECTION VALIDATION =====
function validateTextSection() {
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

$(document).ready(function() {
    console.log('Initializing dashboard...');
    addAnimationStyles();

    let currentExpandedCard = null;
    let sectionProgress = {
        'basic-info': false,
        'why-this-event': false,
        'schedule': false,
        'speakers': false,
        'expenses': false
    };

    initializeDashboard();

    function initializeDashboard() {
        setupFormHandling();
        updateProgressBar();
        loadExistingData();
        checkForExistingErrors();
        if (!$('.form-errors-banner').length) {
            setTimeout(() => {
                activateSection('basic-info');
            }, 250);
        }
    }

    function checkForExistingErrors() {
        if ($('.form-errors-banner').length) {
            activateSection('basic-info');
        }
    }

    function setupFormHandling() {
        $('.nav-link:not(.disabled)').on('click', function(e) {
            e.preventDefault();
            const section = $(this).data('section');
            if (!$(this).hasClass('disabled')) {
                activateSection(section);
            }
        });
        $(document).on('click', '.btn-save-section', function(e) {
            e.preventDefault();
            e.stopPropagation();
            saveCurrentSection();
        });
    }

    function activateSection(section) {
        if (currentExpandedCard === section) return;
        $('.nav-link').removeClass('active');
        $(`.nav-link[data-section="${section}"]`).addClass('active');
        loadFormContent(section);
        currentExpandedCard = section;
        if (!sectionProgress[section]) {
            markSectionInProgress(section);
        }
    }

    // Basic helper to open a section and ensure the form panel is visible
    function openFormPanel(section) {
        activateSection(section);
        const panel = $('#form-panel');
        if (panel.length) {
            $('html, body').animate({
                scrollTop: panel.offset().top
            }, 300);
        }
    }

    function loadFormContent(section) {
        const sectionData = getSectionData(section);
        $('#main-title').text(sectionData.title);
        $('#main-subtitle').text(sectionData.subtitle);

        // This logic is preserved from your original file.
        // It dynamically loads content for sections other than the first one.
        if (section !== 'basic-info') {
            let formContent = '';
            switch (section) {
                case 'why-this-event': formContent = getWhyThisEventForm(); break;
                case 'schedule': formContent = getScheduleForm(); break;
                case 'speakers': formContent = getSpeakersForm(); break;
                case 'expenses': formContent = getExpensesForm(); break;
                default: formContent = '<div class="form-grid"><p>Section not implemented.</p></div>';
            }
            $('#form-panel-content').html(formContent);
        }

        setTimeout(() => {
            if (section === 'basic-info') {
                setupDjangoFormIntegration();
                // We call the new function to set up the listener for activities.
                setupDynamicActivitiesListener();
                setupOutcomeModal();
            }
            if (section === 'speakers') {
                setupSpeakersSection();
            }
            if (section === 'expenses') {
                setupExpensesSection();
            }
            setupFormFieldSync();
            setupTextSectionStorage();
            clearValidationErrors();
            if (window.AutosaveManager && window.AutosaveManager.reinitialize) {
                window.AutosaveManager.reinitialize();
            }
        }, 100);
    }

    function getSectionData(section) {
        const sections = {
            'basic-info': { title: 'Basic Information', subtitle: 'Title, dates, type, location, etc.' },
            'why-this-event': { title: 'Why This Event?', subtitle: 'Objective, GA Relevance, Learning Outcomes' },
            'schedule': { title: 'Schedule', subtitle: 'Event timeline, sessions, flow' },
            'speakers': { title: 'Speaker Profiles', subtitle: 'Names, expertise, brief bio, etc.' },
            'expenses': { title: 'Expenses', subtitle: 'Budget, funding source, justification' }
        };
        return sections[section] || { title: 'Section', subtitle: 'Complete this section' };
    }

    function setupDjangoFormIntegration() {
        const djangoBasicInfo = $('#django-basic-info');
        const orgTypeSelect = djangoBasicInfo.find('select[name="organization_type"]');
        if (orgTypeSelect.length) {
            const orgTypeField = $('#org-type-modern');
            if (orgTypeField.length && orgTypeField.find('input').length === 0) {
                const orgTypeInputHtml = `<input type="text" id="org-type-modern-input" placeholder="Type or select organization type..." autocomplete="off">`;
                // This correctly preserves the label for "Type of Organisation"
                orgTypeField.html(orgTypeInputHtml);
                const orgTypeInput = $('#org-type-modern-input');
                const orgTypeOptions = Array.from(orgTypeSelect.find('option')).map(opt => ({ value: $(opt).val(), text: $(opt).text() })).filter(o => o.value);
                const orgTypeTS = new TomSelect(orgTypeInput[0], {
                    valueField: 'value', labelField: 'text', searchField: 'text', options: orgTypeOptions, create: false, dropdownParent: 'body',
                    onChange: function(value) {
                        const selectedText = this.options[value]?.text.toLowerCase().trim() || '';
                        orgTypeSelect.val(value).trigger('change');
                        // Add a small delay to ensure DOM is ready
                        setTimeout(() => {
                            handleOrgTypeChange(selectedText, false);
                        }, 50);
                    }
                });
                if (orgTypeSelect.val()) {
                    orgTypeTS.setValue(orgTypeSelect.val());
                    const initialText = orgTypeOptions.find(opt => opt.value === orgTypeSelect.val())?.text?.toLowerCase().trim() || '';
                    if (initialText) {
                        setTimeout(() => {
                            handleOrgTypeChange(initialText, true);
                        }, 100);
                    }
                }
            }
        }

        const academicYearField = $('#academic-year-modern');
        if (academicYearField.length && !academicYearField.val()) {
            const currentYear = new Date().getFullYear();
            const currentMonth = new Date().getMonth();
            const startYear = currentMonth >= 6 ? currentYear : currentYear - 1; // Assuming academic year starts in July
            const endYear = startYear + 1;
            academicYearField.val(`${startYear}-${endYear}`).trigger('change');
        }

        // We add the new field IDs to the list of fields to be synced.
        const fieldsToSync = [
            'event_title', 'target_audience', 'event_start_date', 'event_end_date',
            'event_focus_type', 'venue', 'academic_year', 'student_coordinators', 'num_activities',
            'pos_pso'
        ];
        fieldsToSync.forEach(copyDjangoField);
        setupFacultyTomSelect();
    }
    
    // NEW FUNCTION to handle dynamic activities
    function setupDynamicActivitiesListener() {
        const numActivitiesInput = document.getElementById('num-activities-modern');
        if (!numActivitiesInput || numActivitiesInput.dataset.listenerAttached) return;
        numActivitiesInput.addEventListener('input', () => {
            const count = parseInt(numActivitiesInput.value, 10);
            const container = document.getElementById('dynamic-activities-section');
            if (!container) return;
            container.innerHTML = '';
            if (!isNaN(count) && count > 0) {
                let allGroupsHTML = '';
                for (let i = 1; i <= Math.min(count, 50); i++) {
                    allGroupsHTML += `
                        <div class="dynamic-activity-group">
                            <div class="input-group">
                                <label for="activity_name_${i}">Activity ${i} Name</label>
                                <input type="text" id="activity_name_${i}" name="activity_name_${i}" required>
                            </div>
                            <div class="input-group">
                                <label for="activity_date_${i}">Activity ${i} Date</label>
                                <input type="date" id="activity_date_${i}" name="activity_date_${i}" required>
                            </div>
                        </div>`;
                }
                container.innerHTML = allGroupsHTML;
            }
        });
        numActivitiesInput.dataset.listenerAttached = 'true';
    }
    
    // The rest of the file uses your original, working functions.
    function setupFacultyTomSelect() {
        const facultySelect = $('#faculty-select');
        const djangoFacultySelect = $('#django-basic-info [name="faculty_incharges"]');
        if (!facultySelect.length || !djangoFacultySelect.length || facultySelect[0].tomselect) return;

        const existingOptions = Array.from(djangoFacultySelect.find('option')).map(opt => {
            if ($(opt).val()) return { id: $(opt).val(), text: $(opt).text() };
        }).filter(Boolean);

        const tomselect = new TomSelect(facultySelect[0], {
            plugins: ['remove_button'],
            valueField: 'id',
            labelField: 'text',
            searchField: 'text',
            create: false,
            placeholder: 'Type a faculty name…',
            maxItems: 10,
            options: existingOptions,
            load: (query, callback) => {
                if (!query.length) return callback();
                fetch(`${window.API_FACULTY}?q=${encodeURIComponent(query)}`)
                    .then(r => r.json())
                    .then(callback)
                    .catch(() => callback());
            }
        });

        // Ensure selected values are mirrored into the hidden Django field
        tomselect.on('change', () => {
            const values = tomselect.getValue();
            djangoFacultySelect.empty();
            values.forEach(val => {
                const text = tomselect.options[val]?.text || val;
                djangoFacultySelect.append(new Option(text, val, true, true));
            });
            djangoFacultySelect.trigger('change');
            clearFieldError(facultySelect);
        });

        const initialValues = djangoFacultySelect.val();
        if (initialValues && initialValues.length) {
            tomselect.setValue(initialValues);
        }
    }

    function setupOutcomeModal() {
        const posField = $('#pos-pso-modern');
        const djangoOrgSelect = $('#django-basic-info [name="organization"]');
        const modal = $('#outcomeModal');
        const optionsContainer = $('#outcomeOptions');

        if (!posField.length || !djangoOrgSelect.length || !modal.length) return;

        posField.prop('readonly', true).css('cursor', 'pointer');
        $(document).off('click', '#pos-pso-modern').on('click', '#pos-pso-modern', openOutcomeModal);

        function updateModalUrl() {
            const orgId = djangoOrgSelect.val();
            if (orgId) {
                modal.attr('data-url', `${window.API_OUTCOMES_BASE}${orgId}/`);
                optionsContainer.text('Click to load options');
            } else {
                modal.attr('data-url', '');
                optionsContainer.text('No organization selected.');
            }
        }

        updateModalUrl();
        djangoOrgSelect.off('change.outcomeModal').on('change.outcomeModal', updateModalUrl);

        $('#outcomeCancel').off('click').on('click', () => modal.removeClass('show'));
        $('#outcomeSave').off('click').on('click', () => {
            const selected = modal.find('input[type=checkbox]:checked').map((_, cb) => cb.value).get();
            const existing = posField.val().trim();
            const value = existing ? existing + '\n' + selected.join('\n') : selected.join('\n');
            posField.val(value).trigger('change');
            modal.removeClass('show');
        });
    }

    function openOutcomeModal() {
        const modal = $('#outcomeModal');
        const url = modal.attr('data-url');
        const container = $('#outcomeOptions');
        const posField = $('#pos-pso-modern');
        if (!url) {
            alert('No organization selected.');
            return;
        }
        modal.addClass('show');
        container.text('Loading...');
        fetch(url)
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    container.empty();
                    const existing = posField.val().split('\n').map(s => s.trim());
                    data.pos.forEach(po => { addOption(container, 'PO: ' + po.description, existing); });
                    data.psos.forEach(pso => { addOption(container, 'PSO: ' + pso.description, existing); });
                } else {
                    container.text('No data');
                }
            })
            .catch(() => { container.text('Error loading'); });
    }

    function addOption(container, labelText, existing) {
        const lbl = $('<label>');
        const cb = $('<input type="checkbox">').val(labelText);
        if (existing.includes(labelText)) cb.prop('checked', true);
        lbl.append(cb).append(' ' + labelText);
        container.append(lbl).append('<br>');
    }

    function copyDjangoField(fieldName) {
        const djangoField = $(`#django-basic-info [name="${fieldName}"]`);
        const baseId = fieldName.replace(/_/g, '-');
        let modernField = $(`#${baseId}-modern`);
        if (!modernField.length) {
            modernField = $(`#${baseId}`);
        }
        if (djangoField.length && modernField.length) {
            if (djangoField.is('select')) modernField.html(djangoField.html());
            modernField.val(djangoField.val());
            modernField.on('input change', function() {
                const value = $(this).val();
                djangoField.val(value).trigger('change');
                clearFieldError($(this));
            });
        }
    }

    function handleOrgTypeChange(orgType, preserveOrg = false) {
        let normalizedOrgType = orgType ? orgType.toString().toLowerCase().replace(/[^a-z0-9]+/g, '').trim() : '';
        
        // Remove any existing org-specific fields
        $('.org-specific-field').remove();
        
        if (normalizedOrgType) {
            createOrgField(normalizedOrgType, preserveOrg);
        }
        if (!preserveOrg) {
            $('#django-basic-info [name="organization"]').val('').trigger('change');
        }
    }

    function createOrgField(orgType, preserveOrg) {
        const orgTypeMap = { department: 'Department', club: 'Club', association: 'Association', center: 'Center', cell: 'Cell' };
        let canonicalType = Object.keys(orgTypeMap).find(key => orgType.includes(key)) || orgType;
        const label = orgTypeMap[canonicalType] || capitalizeFirst(canonicalType);
        const orgFieldHtml = `
            <div class="org-specific-field form-row full-width">
                <div class="input-group">
                    <label for="org-modern-select">${label} *</label>
                    <select id="org-modern-select" placeholder="Type ${label} name..."></select>
                </div>
            </div>`;
        
        // Insert after the organization type field
        $('#org-type-modern').closest('.form-row').after(orgFieldHtml);
        
        // Add animation
        setTimeout(() => {
            $('.org-specific-field').addClass('show');
        }, 50);
        
        const newSelect = $('#org-modern-select');
        const hiddenField = $('#django-basic-info [name="organization"]');
        
        if (newSelect.length && typeof TomSelect !== 'undefined') {
            const tom = new TomSelect(newSelect[0], {
                valueField: 'id', 
                labelField: 'text', 
                searchField: 'text', 
                create: false,
                dropdownParent: 'body',
                placeholder: `Type ${label} name...`,
                load: (query, callback) => {
                    if (!query || query.length < 2) return callback();
                    fetch(`${window.API_ORGANIZATIONS}?q=${encodeURIComponent(query)}&org_type=${encodeURIComponent(label)}`)
                        .then(r => r.json())
                        .then(callback)
                        .catch(() => callback());
                },
                onChange: (value) => {
                    hiddenField.val(value).trigger('change');
                    clearFieldError(newSelect);
                }
            });
            
            if (preserveOrg && hiddenField.val()) {
                // Try to find existing option text
                const existingOption = hiddenField.find(`option[value="${hiddenField.val()}"]`);
                if (existingOption.length) {
                    const existingText = existingOption.text();
                    tom.addOption({ id: hiddenField.val(), text: existingText });
                    tom.setValue(hiddenField.val());
                } else {
                    // Fallback: just set the value
                    tom.setValue(hiddenField.val());
                }
            }
        }
    }
    
    function capitalizeFirst(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
    
    // ===== FORM TEMPLATE FUNCTIONS - PRESERVED =====
    function getBasicInfoForm() {
        // This function's content is now generated by the Django template,
        // so we don't need to return a hardcoded string here.
        // The logic to manipulate it is in setupDjangoFormIntegration.
        // The HTML is already in the main template.
        return '';
    }

function getWhyThisEventForm() {
    return `
        <div class="form-grid">
            <div class="form-row full-width">
                <div class="input-group">
                    <label for="need-analysis-modern">Need Analysis - Why is this event necessary? *</label>
                    <textarea id="need-analysis-modern" rows="4" required placeholder="Explain why this event is necessary, what gap it fills, and its relevance to the target audience..."></textarea>
                    <div class="help-text">Provide a detailed explanation of why this event is important.</div>
                </div>
            </div>
            
            <div class="form-row full-width">
                <div class="input-group">
                    <label for="objectives-modern">Objectives - What do you aim to achieve? *</label>
                    <textarea id="objectives-modern" rows="4" required placeholder="• Objective 1: ...&#10;• Objective 2: ...&#10;• Objective 3: ..."></textarea>
                    <div class="help-text">List 3-5 clear, measurable objectives.</div>
                </div>
            </div>
            
            <div class="form-row full-width">
                <div class="input-group">
                    <label for="outcomes-modern">Expected Learning Outcomes - What results do you expect? *</label>
                    <textarea id="outcomes-modern" rows="4" required placeholder="What specific results, skills, or benefits will participants gain?"></textarea>
                    <div class="help-text">Describe the tangible benefits for participants.</div>
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

    function getScheduleForm() {
        return `
            <div class="form-grid">
                <div class="form-row full-width">
                    <div class="input-group">
                        <label for="schedule-modern">Event timeline and schedule *</label>
                        <textarea id="schedule-modern" rows="8" required placeholder="9:00 AM - Registration&#10;9:30 AM - Opening Ceremony..."></textarea>
                        <div class="help-text">Provide a detailed timeline for each activity.</div>
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

    function getSpeakersForm() {
        return `
            <div class="form-grid">
                <div id="speakers-list"></div>

                <div class="form-row full-width">
                    <button type="button" id="add-speaker-btn" class="btn">Add Speaker</button>
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

    function getExpensesForm() {
        return `
            <div class="form-grid">
                <div id="expense-rows"></div>

                <div class="form-row full-width">
                    <button type="button" id="add-expense-btn" class="btn">Add Expense</button>
                </div>

                <div class="form-row full-width">
                    <div class="submit-section-container">
                        <button type="submit" name="final_submit" class="btn-submit" id="submit-proposal-btn">
                            Submit Proposal
                        </button>
                        <div class="submit-help-text">
                            Review all sections before submitting
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    function setupSpeakersSection() {
        const container = $('#speakers-list');
        let index = 0;

        function addSpeakerForm() {
            const html = `
                <div class="speaker-form" data-index="${index}">
                    <h3>Speaker ${index + 1}</h3>
                    <div class="form-row">
                        <div class="input-group">
                            <label for="speaker_full_name_${index}">Full Name</label>
                            <input type="text" id="speaker_full_name_${index}" name="speaker_full_name_${index}" />
                        </div>
                        <div class="input-group">
                            <label for="speaker_designation_${index}">Designation</label>
                            <input type="text" id="speaker_designation_${index}" name="speaker_designation_${index}" />
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="input-group">
                            <label for="speaker_affiliation_${index}">Affiliation</label>
                            <input type="text" id="speaker_affiliation_${index}" name="speaker_affiliation_${index}" />
                        </div>
                        <div class="input-group">
                            <label for="speaker_contact_email_${index}">Email</label>
                            <input type="email" id="speaker_contact_email_${index}" name="speaker_contact_email_${index}" />
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="input-group">
                            <label for="speaker_contact_number_${index}">Contact Number</label>
                            <input type="text" id="speaker_contact_number_${index}" name="speaker_contact_number_${index}" />
                        </div>
                        <div class="input-group">
                            <label for="speaker_photo_${index}">Photo</label>
                            <input type="file" id="speaker_photo_${index}" name="speaker_photo_${index}" />
                        </div>
                    </div>
                    <div class="form-row full-width">
                        <div class="input-group full-width">
                            <label for="speaker_detailed_profile_${index}">Brief Profile / Bio</label>
                            <textarea id="speaker_detailed_profile_${index}" name="speaker_detailed_profile_${index}" rows="3"></textarea>
                        </div>
                    </div>
                    <div class="form-row full-width">
                        <button type="button" class="remove-speaker-btn" data-index="${index}">Remove</button>
                    </div>
                    <hr>
                </div>
            `;
            container.append(html);
            index++;
        }

        $('#add-speaker-btn').on('click', addSpeakerForm);
        container.on('click', '.remove-speaker-btn', function() {
            $(this).closest('.speaker-form').remove();
        });

        addSpeakerForm();
    }

    function setupExpensesSection() {
        const container = $('#expense-rows');
        let index = 0;

        function addExpenseRow() {
            const html = `
                <div class="expense-row" data-index="${index}">
                    <div class="input-group">
                        <label for="expense_sl_no_${index}">Sl. No.</label>
                        <input type="number" id="expense_sl_no_${index}" name="expense_sl_no_${index}" />
                    </div>
                    <div class="input-group">
                        <label for="expense_particulars_${index}">Particulars</label>
                        <input type="text" id="expense_particulars_${index}" name="expense_particulars_${index}" />
                    </div>
                    <div class="input-group">
                        <label for="expense_amount_${index}">Amount</label>
                        <input type="number" step="0.01" id="expense_amount_${index}" name="expense_amount_${index}" />
                    </div>
                    <button type="button" class="remove-expense-btn" data-index="${index}">Remove</button>
                    <hr>
                </div>
            `;
            container.append(html);
            index++;
        }

        $('#add-expense-btn').on('click', addExpenseRow);
        container.on('click', '.remove-expense-btn', function() {
            $(this).closest('.expense-row').remove();
        });

        addExpenseRow();
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
        const sectionOrder = ['basic-info', 'why-this-event', 'schedule', 'speakers', 'expenses'];
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

    function setupTextSectionStorage() {
        const editorMap = {
            '#need-analysis-modern': 'section_need_analysis',
            '#objectives-modern': 'section_objectives',
            '#outcomes-modern': 'section_outcomes',
            '#schedule-modern': 'section_flow'
        };

        Object.entries(editorMap).forEach(([selector, key]) => {
            const el = document.querySelector(selector);
            if (!el) return;

            const saved = localStorage.getItem(key);
            if (saved && !el.value) {
                el.value = saved;
            }

            el.addEventListener('input', () => {
                localStorage.setItem(key, el.value);
            });
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
            case 'why-this-event': return validateWhyThisEvent(); // NEW VALIDATION
            case 'schedule': return validateTextSection();
            default: return true;
        }
    }
    function validateWhyThisEvent() {
        let isValid = true;
        const requiredTextareas = ['#need-analysis-modern', '#objectives-modern', '#outcomes-modern'];
        
        requiredTextareas.forEach(selector => {
            const field = $(selector);
            if (!field.val() || field.val().trim() === '') {
                showFieldError(field, 'This field is required');
                field.addClass('animate-shake');
                setTimeout(() => field.removeClass('animate-shake'), 600);
                isValid = false;
            }
        });
        
        return isValid;
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
        // Before submit, copy any rich text content into hidden fields
        const needAnalysisContent = localStorage.getItem('section_need_analysis') || $('#need-analysis-modern').val() || '';
        const objectivesContent = localStorage.getItem('section_objectives') || $('#objectives-modern').val() || '';
        const outcomesContent = localStorage.getItem('section_outcomes') || $('#outcomes-modern').val() || '';
        const flowContent = localStorage.getItem('section_flow') || $('#schedule-modern').val() || '';

        $('textarea[name="need_analysis"]').val(needAnalysisContent);
        $('textarea[name="objectives"]').val(objectivesContent);
        $('textarea[name="outcomes"]').val(outcomesContent);
        $('textarea[name="flow"]').val(flowContent);

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

        ['section_need_analysis','section_objectives','section_outcomes','section_flow'].forEach(key => {
            localStorage.removeItem(key);
        });

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