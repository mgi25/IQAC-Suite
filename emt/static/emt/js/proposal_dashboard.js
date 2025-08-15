$(document).ready(function() {
    console.log('Initializing dashboard...');
    addAnimationStyles();

    let currentExpandedCard = null;
    let sectionProgress = {
        'basic-info': false,
        'why-this-event': false,
        'schedule': false,
        'speakers': false,
        'expenses': false,
        'income': false
    };
    let audienceClassMap = {};
    let firstErrorField = null;
    const autoFillEnabled = new URLSearchParams(window.location.search).has('autofill');
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    // Demo data used for rapid prototyping. Remove once real data is wired.
    const AUTO_FILL_DATA = {
        titles: ['AI Workshop', 'Tech Symposium', 'Innovation Summit'],
        audiences: ['All Students', 'CSE Students', 'Faculty Members'],
        venues: ['Main Auditorium', 'Conference Hall A', 'Online Platform'],
        focusTypes: ['Workshop', 'Seminar', 'Training'],
        objectives: [
            '• Learn about emerging technologies\n• Encourage innovation\n• Foster collaboration',
            '• Understand basics\n• Gain hands-on experience',
            '• Explore research trends\n• Build industry connections'
        ],
        outcomes: [
            'Participants will understand fundamentals',
            'Improved networking amongst attendees',
            'Creation of follow-up projects'
        ],
        need: [
            'To bridge the gap between theory and practice',
            'Demand for skills in industry',
            'Enhance student exposure to experts'
        ],
        schedule: [
            '09:00 AM - Registration\n10:00 AM - Inauguration\n11:00 AM - Keynote Session',
            '10:00 AM - Welcome\n10:30 AM - Talk 1\n12:00 PM - Lunch'
        ],
        speakerNames: ['Dr. Jane Smith', 'Prof. John Doe', 'Ms. Alice Johnson'],
        designations: ['Professor', 'Senior Analyst', 'Researcher'],
        affiliations: ['XYZ University', 'Tech Corp', 'Research Lab'],
        emails: ['jane@example.com', 'john@example.com', 'alice@example.com'],
        phones: ['9876543210', '9123456780', '9988776655'],
        linkedins: [
            'https://linkedin.com/in/jane',
            'https://linkedin.com/in/john',
            'https://linkedin.com/in/alice'
        ],
        bios: [
            'Expert in AI and ML with 10 years of experience.',
            'Data science enthusiast and keynote speaker.',
            'Researcher focusing on emerging technologies.'
        ],
        expenseItems: ['Venue Setup', 'Refreshments', 'Equipment Rental'],
        incomeItems: ['Registration Fees', 'Sponsorship', 'Donations']
    };

    const getRandom = arr => arr[Math.floor(Math.random() * arr.length)];

    initializeDashboard();

    function initializeDashboard() {
        setupFormHandling();
        updateProgressBar();
        loadExistingData();
        checkForExistingErrors();
        enablePreviouslyVisitedSections();
        $('#autofill-btn').on('click', () => autofillTestData(currentExpandedCard));
        if (!$('.form-errors-banner').length) {
            setTimeout(() => {
                activateSection('basic-info');
            }, 250);
        }
    }

    function enablePreviouslyVisitedSections() {
        // Always enable basic-info section
        $(`.proposal-nav .nav-link[data-section="basic-info"]`).removeClass('disabled');
        
        // Enable any sections that have been completed or are in progress
        Object.keys(sectionProgress).forEach(section => {
            if (sectionProgress[section] === true || sectionProgress[section] === 'in-progress') {
                $(`.proposal-nav .nav-link[data-section="${section}"]`).removeClass('disabled');
            }
        });
        
        // Enable the next section only if the previous section is completed
        const sectionOrder = ['basic-info', 'why-this-event', 'schedule', 'speakers', 'expenses', 'income'];
        for (let i = 0; i < sectionOrder.length - 1; i++) {
            const currentSection = sectionOrder[i];
            const nextSection = sectionOrder[i + 1];
            
            if (sectionProgress[currentSection] === true) {
                $(`.proposal-nav .nav-link[data-section="${nextSection}"]`).removeClass('disabled');
            }
        }
    }

    function checkForExistingErrors() {
        if ($('.form-errors-banner').length) {
            activateSection('basic-info');
        }
    }

    function setupFormHandling() {
        // Allow navigation with proper validation
    $('.proposal-nav .nav-link').on('click', function(e) {
            e.preventDefault();
            const section = $(this).data('section');
            const currentOrder = parseInt($(`.proposal-nav .nav-link[data-section="${currentExpandedCard}"]`).data('order')) || 0;
            const targetOrder = parseInt($(this).data('order')) || 0;
            
            // Always allow navigation to basic-info
            if (section === 'basic-info') {
                $(this).removeClass('disabled');
                activateSection(section);
                return;
            }
            
            // Check section status
            const sectionStatus = sectionProgress[section];
            
            // Allow navigation if:
            // 1. Going backwards to a previously completed/started section
            // 2. Section has been completed or is in progress
            // 3. Moving to the immediate next section if current section is valid
            const canNavigate = 
                targetOrder < currentOrder || // Going backwards
                sectionStatus === true || // Section completed
                sectionStatus === 'in-progress' || // Section in progress
                (targetOrder === currentOrder + 1 && validateCurrentSection()); // Next section + current valid
            
            if (canNavigate) {
                // If moving forward to a new section, validate current section first
                if (targetOrder > currentOrder && currentExpandedCard) {
                    if (!validateCurrentSection()) {
                        showNotification('Please complete all required fields in the current section first.', 'error');
                        return;
                    }
                }
                
                $(this).removeClass('disabled');
                activateSection(section);
            } else {
                // Show helpful message based on the situation
                if (targetOrder > currentOrder + 1) {
                    showNotification('Please complete the previous sections first.', 'info');
                } else {
                    showNotification('Please complete all required fields in the current section first.', 'error');
                }
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
        
        $('.proposal-nav .nav-link').removeClass('active');
        $(`.proposal-nav .nav-link[data-section="${section}"]`).addClass('active');
        loadFormContent(section);
        currentExpandedCard = section;
        
        // Mark section as in-progress if it hasn't been started yet
        if (!sectionProgress[section]) {
            markSectionInProgress(section);
        }
        
        // Remove disabled class from current section
        $(`.proposal-nav .nav-link[data-section="${section}"]`).removeClass('disabled');
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

        // Load content for all sections, including basic-info
        let formContent = '';
        switch (section) {
            case 'basic-info': formContent = getBasicInfoForm(); break;
            case 'why-this-event': formContent = getWhyThisEventForm(); break;
            case 'schedule': formContent = getScheduleForm(); break;
            case 'speakers': formContent = getSpeakersForm(); break;
            case 'expenses': formContent = getExpensesForm(); break;
            case 'income': formContent = getIncomeForm(); break;
            default: formContent = '<div class="form-grid"><p>Section not implemented.</p></div>';
        }
        $('#form-panel-content').html(formContent);

        setTimeout(() => {
            if (section === 'basic-info') {
                setupDjangoFormIntegration();
                // We call the new function to set up the listener for activities.
                setupDynamicActivitiesListener();
                setupOutcomeModal();
                setupAudienceModal();
            }
            if (section === 'speakers') {
                setupSpeakersSection();
            }
            if (section === 'expenses') {
                setupExpensesSection();
            }
            if (section === 'income') {
                setupIncomeSection();
            }
            if (section === 'why-this-event') {
                setupWhyThisEventAI();
            }
            setupFormFieldSync();
            setupTextSectionStorage();
            clearValidationErrors();
            if (window.AutosaveManager && window.AutosaveManager.reinitialize) {
                window.AutosaveManager.reinitialize();
            }
            if (autoFillEnabled) {
                autofillTestData(section);
            }
        }, 100);
    }

    function getSectionData(section) {
        const sections = {
            'basic-info': { title: 'Basic Information', subtitle: 'Title, dates, type, location, etc.' },
            'why-this-event': { title: 'Why This Event?', subtitle: 'Objective, GA Relevance, Learning Outcomes' },
            'schedule': { title: 'Schedule', subtitle: 'Event timeline, sessions, flow' },
            'speakers': { title: 'Speaker Profiles', subtitle: 'Names, expertise, brief bio, etc.' },
            'expenses': { title: 'Expenses', subtitle: 'Budget, funding source, justification' },
            'income': { title: 'Details of Income', subtitle: 'Registration fees, sponsorship, participation rates' }
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
                    valueField: 'value',
                    labelField: 'text',
                    searchField: 'text',
                    options: orgTypeOptions,
                    create: false,
                    dropdownParent: 'body',
                    maxItems: 1,
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
                    // Set the initial org type without triggering the change handler
                    // so the pre-selected organization value is preserved.
                    orgTypeTS.setValue(orgTypeSelect.val(), true);
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
            'event_focus_type', 'venue', 'academic_year', 'num_activities',
            'pos_pso'
        ];
        fieldsToSync.forEach(copyDjangoField);
        setupSDGModal();
        setupFacultyTomSelect();
        setupCommitteesTomSelect();
        setupStudentCoordinatorSelect();

        const orgSelect = djangoBasicInfo.find('[name="organization"]');
        const committeesIds = djangoBasicInfo.find('[name="committees_collaborations_ids"]');
        orgSelect.off('change.studentCoordinator').on('change.studentCoordinator', setupStudentCoordinatorSelect);
        if (committeesIds.length) {
            committeesIds.off('change.studentCoordinator').on('change.studentCoordinator', setupStudentCoordinatorSelect);
        }
    }
    
    // NEW FUNCTION to handle dynamic activities
    function setupDynamicActivitiesListener() {
        const numActivitiesInput = document.getElementById('num-activities-modern');
        if (!numActivitiesInput || numActivitiesInput.dataset.listenerAttached) return;
        const container = document.getElementById('dynamic-activities-section');
        function render(count) {
            if (!container) return;
            container.innerHTML = '';
            if (!isNaN(count) && count > 0) {
                let html = '';
                for (let i = 1; i <= Math.min(count, 50); i++) {
                    html += `
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
                container.innerHTML = html;
                if (window.EXISTING_ACTIVITIES && window.EXISTING_ACTIVITIES.length) {
                    window.EXISTING_ACTIVITIES.forEach((act, idx) => {
                        const index = idx + 1;
                        $(`#activity_name_${index}`).val(act.name);
                        $(`#activity_date_${index}`).val(act.date);
                    });
                }
                if (window.AutosaveManager && window.AutosaveManager.reinitialize) {
                    window.AutosaveManager.reinitialize();
                }
            }
        }
        numActivitiesInput.addEventListener('input', () => {
            const count = parseInt(numActivitiesInput.value, 10);
            render(count);
        });
        numActivitiesInput.dataset.listenerAttached = 'true';
        if (window.EXISTING_ACTIVITIES && window.EXISTING_ACTIVITIES.length) {
            numActivitiesInput.value = window.EXISTING_ACTIVITIES.length;
            render(window.EXISTING_ACTIVITIES.length);
        }
    }
    
    // The rest of the file uses your original, working functions.
    function setupFacultyTomSelect() {
        const facultySelect = $('#faculty-select');
        const djangoFacultySelect = $('#django-basic-info [name="faculty_incharges"]');
        const djangoOrgSelect = $('#django-basic-info [name="organization"]');
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
                const orgId = djangoOrgSelect.val();
                if (!query.length || !orgId) return callback();
                fetch(`${window.API_FACULTY}?org_id=${orgId}&q=${encodeURIComponent(query)}`)
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

    function setupCommitteesTomSelect() {
        const select = $('#committees-collaborations-modern');
        const djangoField = $('#django-basic-info [name="committees_collaborations"]');
        const idsField = $('#django-basic-info [name="committees_collaborations_ids"]');
        if (!select.length || !djangoField.length || select[0].tomselect) return;

        const existingNames = djangoField.val()
            ? djangoField.val().split(',').map(s => s.trim()).filter(Boolean)
            : [];
        const existingIds = idsField.length && idsField.val()
            ? idsField.val().split(',').map(s => s.trim()).filter(Boolean)
            : [];

        const tom = new TomSelect(select[0], {
            plugins: ['remove_button'],
            valueField: 'id',
            labelField: 'text',
            searchField: 'text',
            create: false,
            load: (query, callback) => {
                if (!query.length) return callback();
                const orgId = $('#django-basic-info [name="organization"]').val();
                const exclude = orgId ? `&exclude=${encodeURIComponent(orgId)}` : '';
                fetch(`${window.API_ORGANIZATIONS}?q=${encodeURIComponent(query)}${exclude}`)
                    .then(r => r.json())
                    .then(data => callback(data))
                    .catch(() => callback());
            }
        });

        tom.on('change', () => {
            const ids = tom.getValue();
            const names = ids.map(id => tom.options[id]?.text || id);
            djangoField.val(names.join(', ')).trigger('change');
            if (idsField.length) {
                idsField.val(ids.join(', ')).trigger('change');
            }
            clearFieldError(select);
        });

        if (existingIds.length) {
            fetch(`${window.API_ORGANIZATIONS}?ids=${existingIds.join(',')}`)
                .then(r => r.json())
                .then(data => {
                    data.forEach(opt => tom.addOption(opt));
                    tom.setValue(existingIds);
                })
                .catch(() => {
                    if (existingNames.length) {
                        existingNames.forEach((name, idx) => {
                            const id = existingIds[idx] || name;
                            tom.addOption({ id, text: name });
                        });
                        tom.setValue(existingIds.length ? existingIds : existingNames);
                    }
                });
        } else if (existingNames.length) {
            existingNames.forEach((name, idx) => {
                const id = existingIds[idx] || name;
                tom.addOption({ id, text: name });
            });
            tom.setValue(existingIds.length ? existingIds : existingNames);
        }

        const orgSelect = $('#django-basic-info [name="organization"]');
        orgSelect.on('change.committees', () => {
            const orgId = orgSelect.val();
            const orgName = orgSelect.find('option:selected').text().trim();
            if (!orgId) return;
            // remove selected organization from committees list
            const optionId = tom.options[orgId] ? orgId : Object.keys(tom.options).find(id => tom.options[id].text === orgName);
            if (optionId) {
                tom.removeItem(optionId);
                tom.removeOption(optionId);
            }
        });
    }

    function setupStudentCoordinatorSelect() {
        const select = $('#student-coordinators-modern');
        const djangoField = $('#django-basic-info [name="student_coordinators"]');
        const orgSelect = $('#django-basic-info [name="organization"]');
        const committeesField = $('#django-basic-info [name="committees_collaborations_ids"]');
        const list = $('#student-coordinators-list');
        if (!select.length || !djangoField.length) return;

        if (select[0].tomselect) {
            select[0].tomselect.destroy();
        }

        const tom = new TomSelect(select[0], {
            plugins: ['remove_button'],
            valueField: 'text',
            labelField: 'text',
            searchField: 'text',
            create: false,
            placeholder: 'Type a student name…',
            load: function(query, callback) {
                const ids = [];
                const main = orgSelect.val();
                if (main) ids.push(main);
                if (committeesField.length && committeesField.val()) {
                    committeesField.val().split(',').map(id => id.trim()).filter(Boolean).forEach(id => ids.push(id));
                }
                const orgParam = ids.length ? `&org_ids=${encodeURIComponent(ids.join(','))}` : '';
                const url = `/suite/api/students/?q=${encodeURIComponent(query)}${orgParam}`;
                fetch(url)
                    .then(response => response.json())
                    .then(json => {
                        callback(json);
                    })
                    .catch(() => {
                        callback();
                    });
            },
        });

        const existing = djangoField.val()
            ? djangoField.val().split(',').map(s => s.trim()).filter(Boolean)
            : [];
        if (existing.length) {
            tom.addOptions(existing.map(n => ({ text: n })));
            tom.setValue(existing);
            updateList(existing);
        }

        tom.on('change', () => {
            const values = tom.getValue();
            const arr = Array.isArray(values) ? values : [values];
            djangoField.val(arr.join(', ')).trigger('change');
            clearFieldError(select);
            updateList(arr);
        });

        select[0].tomselect = tom;

        function updateList(values) {
            if (!list.length) return;
            list.empty();
            (Array.isArray(values) ? values : [values])
                .filter(Boolean)
                .forEach(name => {
                    list.append($('<li>').text(name));
                });
        }
    }

    function setupOutcomeModal() {
        const posField = $('#pos-pso-modern');
        const djangoOrgSelect = $('#django-basic-info [name="organization"]');
        const modal = $('#outcomeModal');
        const optionsContainer = $('#outcomeOptions');
        const djangoPosField = $('#django-basic-info [name="pos_pso"]');

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
            posField.val(value).trigger('input').trigger('change');
            if (djangoPosField.length) {
                djangoPosField.val(value).trigger('input').trigger('change');
            }
            modal.removeClass('show');
        });
    }

    function setupAudienceModal() {
        const audienceField = $('#target-audience-modern');
        const classIdsField = $('#target-audience-class-ids');
        const djangoOrgSelect = $('#django-basic-info [name="organization"]');
        const modal = $('#audienceModal');
        const container = $('#audienceOptions');

        if (!audienceField.length || !djangoOrgSelect.length || !modal.length) return;

        audienceField.prop('readonly', true).css('cursor', 'pointer');
        $(document).off('click', '#target-audience-modern').on('click', '#target-audience-modern', openAudienceModal);

        $('#audienceCancel').off('click').on('click', () => modal.removeClass('show'));
        $('#audienceSave').off('click').on('click', () => {
            const selected = modal.find('input[name="audience-user"]:checked').map((_, cb) => $(cb).data('name')).get();
            audienceField.val(selected.join(', ')).trigger('change').trigger('input');
            if (classIdsField.length) {
                classIdsField.val('').trigger('change').trigger('input');
            }
            modal.removeClass('show');
        });
    }

    function openAudienceModal() {
        const modal = $('#audienceModal');
        const container = $('#audienceOptions');
        const djangoOrgSelect = $('#django-basic-info [name="organization"]');
        const classIdsField = $('#target-audience-class-ids');
        const preselected = classIdsField.length && classIdsField.val()
            ? classIdsField.val().split(',').map(s => s.trim()).filter(Boolean)
            : [];
        modal.addClass('show');
        $('#audienceSave').hide();
        container.html(`
            <div class="audience-type-selector">
                <button type="button" data-type="students">Students</button>
                <button type="button" data-type="faculty">Faculty</button>
            </div>
            <div id="audienceList">Select an option above.</div>
        `);
        const list = $('#audienceList');

        function collectOrgIds() {
            const primaryOrgId = djangoOrgSelect.val();
            const committeeTS = $('#committees-collaborations-modern')[0]?.tomselect;
            const extraOrgIds = committeeTS ? committeeTS.getValue().filter(id => /^\d+$/.test(id)) : [];
            const orgIds = [];
            if (primaryOrgId) {
                orgIds.push({ id: primaryOrgId, name: djangoOrgSelect.find('option:selected').text().trim() });
            }
            if (committeeTS) {
                extraOrgIds.forEach(id => {
                    const name = committeeTS.options[id]?.text || '';
                    orgIds.push({ id, name });
                });
            }
            return orgIds;
        }

        function loadStudentView(preselectIds) {
            const orgIds = collectOrgIds();
            if (!orgIds.length) { list.text('Select an organization first.'); return; }
            list.text('Loading...');
            Promise.all(orgIds.map(o =>
                fetch(`${window.API_CLASSES_BASE}${o.id}/`, { credentials: 'include' })
                    .then(r => r.json().then(data => ({ org: o, data })))
            ))
            .then(results => {
                audienceClassMap = {};
                results.forEach(res => {
                    const { org, data } = res;
                    if (data.success && data.classes.length) {
                        data.classes.forEach(cls => {
                            audienceClassMap[cls.id] = { ...cls, org_name: org.name };
                        });
                    }
                });
                renderStudentSelection(preselectIds, list);
            })
            .catch(() => { list.text('Error loading.'); });
        }

        container.find('button[data-type]').on('click', function() {
            const type = $(this).data('type');
            const orgIds = collectOrgIds();
            if (!orgIds.length) { list.text('Select an organization first.'); return; }

            if (type === 'students') {
                $('#audienceSave').hide();
                list.text('Loading...');
                Promise.all(orgIds.map(o =>
                    fetch(`${window.API_CLASSES_BASE}${o.id}/`, { credentials: 'include' })
                        .then(r => r.json().then(data => ({ org: o, data })))
                ))
                .then(results => {
                    audienceClassMap = {};
                    renderClassSelection(results, list, preselected);
                })
                .catch(() => { list.text('Error loading.'); });
            } else {
                $('#audienceSave').show();
                list.empty();
                Promise.all(orgIds.map(o =>
                    fetch(`${window.API_FACULTY}?org_id=${o.id}`, { credentials: 'include' })
                        .then(r => r.json().then(data => ({ org: o, data })))
                ))
                .then(results => {
                    let hasAny = false;
                    results.forEach(res => {
                        const { org, data } = res;
                        if (data.length) {
                            hasAny = true;
                            const orgHeader = $('<div class="audience-org-header">').text(org.name);
                            list.append(orgHeader);
                            data.forEach(f => {
                                const name = f.text.replace(/\s*\(.*?\)\s*$/, '');
                                const label = `${name} (${org.name})`;
                                const cb = $('<input type="checkbox" name="audience-user">').val(f.id).data('name', label);
                                const lbl = $('<label>').append(cb).append(' ' + label);
                                list.append(lbl).append('<br>');
                            });
                        }
                    });
                    if (!hasAny) list.text('No faculty found.');
                })
                .catch(() => { list.text('Error loading.'); });
            }
        });

        if (preselected.length) {
            loadStudentView(preselected);
        }
    }

    function renderClassSelection(results, list, preselected = []) {
        list.empty();
        let hasAny = false;
        const selectAll = $('<label class="audience-select-all"><input type="checkbox" id="audienceSelectAllClasses"> Select All Classes</label>');
        list.append(selectAll);
        results.forEach(res => {
            const { org, data } = res;
            if (data.success && data.classes.length) {
                hasAny = true;
                const orgHeader = $('<div class="audience-org-header">').text(org.name);
                list.append(orgHeader);
                data.classes.forEach(cls => {
                    audienceClassMap[cls.id] = { ...cls, org_name: org.name };
                    const lbl = $('<label class="audience-class-choice">');
                    const cb = $('<input type="checkbox" class="audience-class-choice-cb">').val(cls.id);
                    if (preselected.includes(String(cls.id))) {
                        cb.prop('checked', true);
                    }
                    lbl.append(cb).append(' ' + cls.name);
                    list.append(lbl).append('<br>');
                });
            }
        });
        if (!hasAny) {
            list.text('No classes found.');
            return;
        }
        $('#audienceSelectAllClasses').on('change', function() {
            list.find('.audience-class-choice-cb').prop('checked', $(this).is(':checked'));
        });
        const continueBtn = $('<button type="button" class="btn-continue">Continue</button>');
        list.append(continueBtn);
        continueBtn.on('click', function() {
            const selected = list.find('.audience-class-choice-cb:checked').map((_, cb) => $(cb).val()).get();
            if (!selected.length) {
                alert('Please select at least one class.');
                return;
            }
            const audienceField = $('#target-audience-modern');
            const classIdsField = $('#target-audience-class-ids');
            const names = selected.map(id => {
                const cls = audienceClassMap[id];
                return cls ? `${cls.name} (${cls.org_name})` : '';
            });
            audienceField.val(names.join(', ')).trigger('change').trigger('input');
            classIdsField.val(selected.join(',')).trigger('change').trigger('input');
            renderStudentSelection(selected, list);
        });
    }

    function renderStudentSelection(selectedIds, list) {
        list.empty();
        $('#audienceSave').show();
        selectedIds.forEach(id => {
            const cls = audienceClassMap[id];
            if (!cls) return;
            const classLbl = $('<label class="audience-class">');
            const classCb = $('<input type="checkbox" class="audience-class-cb" checked>').val(id);
            classLbl.append(classCb).append(' ' + cls.name);
            const studentsDiv = $('<div class="audience-students" style="margin-left:1em;"></div>');
            cls.students.forEach(st => {
                const stCb = $('<input type="checkbox" name="audience-user" checked>').val(st.id).data('name', st.name);
                const stLbl = $('<label>').append(stCb).append(' ' + st.name);
                studentsDiv.append(stLbl).append('<br>');
            });
            list.append(classLbl).append('<br>').append(studentsDiv);
            classCb.on('change', function() {
                studentsDiv.find('input[type=checkbox]').prop('checked', $(this).is(':checked'));
            });
        });

        const audienceField = $('#target-audience-modern');
        const classIdsField = $('#target-audience-class-ids');
        $('#audienceSave').off('click').on('click', () => {
            const selectedClasses = list.find('.audience-class-cb:checked').map((_, cb) => $(cb).val()).get();
            const names = selectedClasses.map(id => {
                const cls = audienceClassMap[id];
                return cls ? `${cls.name} (${cls.org_name})` : '';
            });
            audienceField.val(names.join(', ')).trigger('change').trigger('input');
            classIdsField.val(selectedClasses.join(',')).trigger('change').trigger('input');
            $('#audienceModal').removeClass('show');
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

    function setupSDGModal() {
        const hidden = $('#django-basic-info [name="sdg_goals"]');
        const input = $('#sdg-goals-modern');
        const modal = $('#sdgModal');
        const container = $('#sdgOptions');
        if (!hidden.length || !input.length || !modal.length) return;

        if (container.children().length === 0 && window.SDG_GOALS) {
            let html = '';
            window.SDG_GOALS.forEach(goal => {
                html += `<label><input type="checkbox" value="${goal.id}"> ${goal.name}</label><br>`;
            });
            container.html(html);
        }

        const hiddenMap = {};
        hidden.each(function(){ hiddenMap[$(this).val()] = $(this); });

        const existing = Object.keys(hiddenMap).filter(id => hiddenMap[id].prop('checked'));
        if (existing.length) {
            const names = window.SDG_GOALS.filter(g => existing.includes(String(g.id))).map(g => g.name);
            input.val(names.join(', '));
            container.find('input[type=checkbox]').each(function(){
                if (existing.includes($(this).val())) $(this).prop('checked', true);
            });
        }

        input.prop('readonly', true).css('cursor', 'pointer');
        input.off('click').on('click', () => modal.addClass('show'));
        $('#sdgCancel').off('click').on('click', () => modal.removeClass('show'));
        $('#sdgSave').off('click').on('click', () => {
            const selected = container.find('input[type=checkbox]:checked').map((_, cb) => cb.value).get();
            Object.entries(hiddenMap).forEach(([id, el]) => {
                el.prop('checked', selected.includes(id));
            });
            hidden.first().trigger('change');
            const names = window.SDG_GOALS.filter(g => selected.includes(String(g.id))).map(g => g.name);
            input.val(names.join(', '));
            modal.removeClass('show');
        });
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
                maxItems: 1,
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
        // Return the actual basic info form HTML content
        return `
            <div class="form-grid">
                <!-- Organization Information Section -->
                <div class="form-section-header">
                    <h3>Organization Details</h3>
                </div>
                
                <div class="form-row full-width">
                    <div class="input-group">
                        <label for="org-type-modern-input">Type of Organisation *</label>
                        <div id="org-type-modern">
                            <select required><option value="">Select Organization Type</option></select>
                        </div>
                        <div class="help-text">Choose the type of organization hosting this event</div>
                    </div>
                </div>

                <!-- Dynamic organization field will be inserted here -->

                <div class="form-row full-width">
                    <div class="input-group">
                        <label for="committees-collaborations-modern">Committees & Collaborations</label>
                        <select id="committees-collaborations-modern" multiple placeholder="Type or select organizations..."></select>
                        <div class="help-text">Mention internal committees and external partners involved</div>
                    </div>
                </div>

                <!-- Event Information Section -->
                <div class="form-section-header">
                    <h3>Event Information</h3>
                </div>

                <div class="form-row">
                    <div class="input-group">
                        <label for="event-title-modern">Event Title *</label>
                        <input type="text" id="event-title-modern" required placeholder="Enter a descriptive event title">
                        <div class="help-text">Provide a clear and engaging title for your event</div>
                    </div>
                    <div class="input-group">
                        <label for="target-audience-modern">Target Audience *</label>
                        <input type="text" id="target-audience-modern" required readonly placeholder="Select target audience">
                        <div class="help-text">Specify who this event is intended for</div>
                    </div>
                </div>

                <div class="form-row">
                    <div class="input-group">
                        <label for="event-focus-type-modern">Event Focus Type</label>
                        <input type="text" id="event-focus-type-modern" placeholder="Enter event focus">
                        <div class="help-text">Specify the primary focus of your event</div>
                    </div>
                    <div class="input-group">
                        <label for="venue-modern">Location</label>
                        <input type="text" id="venue-modern" placeholder="e.g., Main Auditorium, Online">
                        <div class="help-text">Specify where the event will take place</div>
                    </div>
                </div>
                
                <!-- Date and Academic Information Section -->
                <div class="form-section-header">
                    <h3>Schedule & Academic Information</h3>
                </div>
                
                <div class="form-row">
                    <div class="input-group">
                        <label for="event-start-date">Start Date *</label>
                        <input type="date" id="event-start-date" required>
                        <div class="help-text">When does your event begin?</div>
                    </div>
                    <div class="input-group">
                        <label for="event-end-date">End Date *</label>
                        <input type="date" id="event-end-date" required>
                        <div class="help-text">When does your event end?</div>
                    </div>
                </div>

                <div class="form-row">
                    <div class="input-group">
                        <label for="academic-year-modern">Academic Year *</label>
                        <input type="text" id="academic-year-modern" placeholder="2024-2025" required>
                        <div class="help-text">Academic year for which this event is planned</div>
                    </div>
                    <div class="input-group">
                        <label for="pos-pso-modern">POS & PSO Management</label>
                        <input type="text" id="pos-pso-modern" name="pos_pso" placeholder="e.g., PO1, PSO2">
                        <div class="help-text">Program outcomes and specific outcomes addressed</div>
                    </div>
                </div>

                <!-- SDG Goals Section -->
                <div class="form-section-header">
                    <h3>SDG Goals</h3>
                </div>

                <div class="form-row full-width">
                    <div class="input-group">
                        <label for="sdg-goals-modern">Aligned SDG Goals</label>
                        <input type="text" id="sdg-goals-modern" placeholder="Select SDG goals">
                        <div class="help-text">Specify which Sustainable Development Goals this event addresses</div>
                    </div>
                </div>

                <!-- Activities Section -->
                <div class="form-section-header">
                    <h3>Activities Planning</h3>
                </div>

                <div class="form-row">
                    <div class="input-group">
                        <label for="num-activities-modern">Number of Activities</label>
                        <input type="number" id="num-activities-modern" min="1" max="50" placeholder="Enter number of activities">
                        <div class="help-text">How many activities will your event include?</div>
                    </div>
                    <div class="input-group">
                        <label for="student-coordinators-modern">Student Coordinators</label>
                        <select id="student-coordinators-modern" multiple></select>
                        <div class="help-text">Search and select student coordinators by name</div>
                    </div>
                </div>
                
                <!-- Dynamic activities section -->
                <div id="dynamic-activities-section" class="full-width"></div>

                <!-- Faculty Section -->
                <div class="form-section-header">
                    <h3>Faculty Information</h3>
                </div>

                <div class="form-row full-width">
                    <div class="input-group">
                        <label for="faculty-select">Faculty Incharges *</label>
                        <select id="faculty-select" multiple></select>
                        <div class="help-text">Select faculty members who will be in charge of this event</div>
                    </div>
                </div>
                
                <!-- Save Section -->
                <div class="form-row full-width">
                    <div class="save-section-container" style="display: flex; flex-direction: column; align-items: center;">
                        <button type="button" class="btn-save-section" style="margin-bottom: 0.5rem;">Save & Continue</button>
                        <div class="save-help-text" style="margin-top: 0.75rem;">Complete this section to unlock the next one</div>
                    </div>
                </div>
            </div>
        `;
    }

function getWhyThisEventForm() {
    return `
        <div class="form-grid">
            <div class="form-row full-width" style="text-align:right;">
                <button type="button" id="btn-generate-why" class="btn">Generate with AI</button>
            </div>
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
                        <textarea id="schedule-modern" name="flow" rows="8" required placeholder="9:00 AM - Registration&#10;9:30 AM - Opening Ceremony..."></textarea>
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
            <div class="speakers-section">
                <div id="speakers-list" class="speakers-container"></div>

                <div class="add-speaker-section">
                    <button type="button" id="add-speaker-btn" class="btn-add-speaker">
                        Add Another Speaker
                    </button>
                    <div class="help-text" style="text-align: center; margin-top: 0.5rem;">
                        Add all speakers who will be presenting at your event
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

    function getExpensesForm() {
        return `
            <div class="expenses-section">
                <div id="expense-rows" class="expenses-container"></div>

                <div class="add-expense-section">
                    <button type="button" id="add-expense-btn" class="btn-add-expense">
                        Add Another Expense
                    </button>
                    <div class="help-text" style="text-align: center; margin-top: 0.5rem;">
                        Add all expense items for your event
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

    function setupSpeakersSection() {
        const container = $('#speakers-list');
        let index = 0;

        function addSpeakerForm() {
            const html = `
                <div class="speaker-form-container" data-index="${index}">
                    <div class="speaker-form-card">
                        <div class="speaker-form-header">
                            <h3 class="speaker-title">Speaker ${index + 1}</h3>
                            <button type="button" class="btn-remove-speaker remove-speaker-btn" data-index="${index}" title="Remove Speaker">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                        
                        <div class="speaker-form-content">
                            <div class="speaker-form-grid">
                                <div class="input-group">
                                    <label for="speaker_full_name_${index}">Full Name *</label>
                                    <input type="text" id="speaker_full_name_${index}" name="speaker_full_name_${index}" required />
                                    <div class="help-text">Enter the speaker's full name</div>
                                </div>
                                <div class="input-group">
                                    <label for="speaker_designation_${index}">Designation *</label>
                                    <input type="text" id="speaker_designation_${index}" name="speaker_designation_${index}" required />
                                    <div class="help-text">Job title or role</div>
                                </div>
                                <div class="input-group">
                                    <label for="speaker_affiliation_${index}">Affiliation *</label>
                                    <input type="text" id="speaker_affiliation_${index}" name="speaker_affiliation_${index}" required />
                                    <div class="help-text">Organization or institution</div>
                                </div>
                                <div class="input-group">
                                    <label for="speaker_contact_email_${index}">Email *</label>
                                    <input type="email" id="speaker_contact_email_${index}" name="speaker_contact_email_${index}" required />
                                    <div class="help-text">Official contact email</div>
                                </div>
                                <div class="input-group">
                                    <label for="speaker_contact_number_${index}">Contact Number</label>
                                    <input type="text" id="speaker_contact_number_${index}" name="speaker_contact_number_${index}" />
                                    <div class="help-text">Phone number</div>
                                </div>
                                <div class="input-group">
                                    <label for="speaker_linkedin_url_${index}">LinkedIn Profile</label>
                                    <input type="url" id="speaker_linkedin_url_${index}" name="speaker_linkedin_url_${index}" placeholder="https://linkedin.com/in/username" />
                                    <div class="help-text">LinkedIn profile URL (optional)</div>
                                </div>
                                <div class="input-group">
                                    <label for="speaker_photo_${index}">Photo</label>
                                    <input type="file" id="speaker_photo_${index}" name="speaker_photo_${index}" accept="image/*" />
                                    <img class="linkedin-photo" style="max-width:100px; display:none;" />
                                    <div class="help-text">Upload headshot (JPG, PNG)</div>
                                </div>
                            </div>
                            
                            <div class="input-group bio-section">
                                <label for="speaker_detailed_profile_${index}">Brief Profile / Bio *</label>
                                <textarea id="speaker_detailed_profile_${index}" name="speaker_detailed_profile_${index}" rows="4" required placeholder="Brief description of speaker's expertise, background, and qualifications..."></textarea>
                                <div class="help-text">Provide a concise professional biography</div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            container.append(html);
            index++;
            if (window.AutosaveManager && window.AutosaveManager.reinitialize) {
                window.AutosaveManager.reinitialize();
            }
        }

        function updateSpeakerHeaders() {
            container.children('.speaker-form-container').each(function(i) {
                $(this).find('.speaker-title').text(`Speaker ${i + 1}`);
                $(this).attr('data-index', i);
                $(this).find('.remove-speaker-btn').attr('data-index', i);
            });
        }

        function showEmptyState() {
            if (container.children('.speaker-form-container').length === 0) {
                container.html(`
                    <div class="speakers-empty-state">
                        <div class="empty-state-icon">🎤</div>
                        <h4>No speakers added yet</h4>
                        <p>Add speakers who will be presenting at your event</p>
                    </div>
                `);
            } else {
                container.find('.speakers-empty-state').remove();
            }
        }

        $('#add-speaker-btn').on('click', function() {
            addSpeakerForm();
            showEmptyState();
        });

        container.on('click', '.remove-speaker-btn', function() {
            $(this).closest('.speaker-form-container').remove();
            updateSpeakerHeaders();
            showEmptyState();
            if (window.AutosaveManager && window.AutosaveManager.reinitialize) {
                window.AutosaveManager.reinitialize();
            }
        });

        container.on('change', "input[id^='speaker_linkedin_url_']", async function() {
            const url = $(this).val().trim();
            if (!url) return;
            try {
                const resp = await fetch(window.API_FETCH_LINKEDIN, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': window.AUTOSAVE_CSRF || ''
                    },
                    body: JSON.stringify({ url })
                });
                if (!resp.ok) return;
                const data = await resp.json();
                const form = $(this).closest('.speaker-form-container');
                const idx = form.data('index');
                const nameInput = form.find(`#speaker_full_name_${idx}`)[0];
                const desigInput = form.find(`#speaker_designation_${idx}`)[0];
                const affInput = form.find(`#speaker_affiliation_${idx}`)[0];
                if (data.name && nameInput && !nameInput.value) nameInput.value = data.name;
                if (data.designation && desigInput && !desigInput.value) desigInput.value = data.designation;
                if (data.affiliation && affInput && !affInput.value) affInput.value = data.affiliation;
                if (data.image) {
                    const imgPreview = form.find('.linkedin-photo')[0];
                    if (imgPreview) {
                        imgPreview.src = data.image;
                        imgPreview.style.display = 'block';
                    }
                    const photoInput = form.find(`#speaker_photo_${idx}`)[0];
                    if (photoInput) {
                        try {
                            const imgResp = await fetch(data.image);
                            const blob = await imgResp.blob();
                            const file = new File([blob], 'photo.jpg', { type: blob.type });
                            const dt = new DataTransfer();
                            dt.items.add(file);
                            photoInput.files = dt.files;
                        } catch (err) {
                            console.error('Could not set photo file', err);
                        }
                    }
                }
            } catch (err) {
                console.error('LinkedIn fetch failed', err);
            }
        });

        if (window.EXISTING_SPEAKERS && window.EXISTING_SPEAKERS.length) {
            container.empty();
            window.EXISTING_SPEAKERS.forEach(sp => {
                addSpeakerForm();
                const idx = index - 1;
                $(`#speaker_full_name_${idx}`).val(sp.full_name);
                $(`#speaker_designation_${idx}`).val(sp.designation);
                $(`#speaker_affiliation_${idx}`).val(sp.affiliation);
                $(`#speaker_contact_email_${idx}`).val(sp.contact_email);
                $(`#speaker_contact_number_${idx}`).val(sp.contact_number);
                $(`#speaker_linkedin_url_${idx}`).val(sp.linkedin_url);
                $(`#speaker_detailed_profile_${idx}`).val(sp.detailed_profile);
            });
            showEmptyState();
        } else {
            showEmptyState();
        }
    }

    function setupExpensesSection() {
        const container = $('#expense-rows');
        let index = 0;

        function addExpenseRow() {
            const html = `
                <div class="expense-form-container" data-index="${index}">
                    <div class="expense-form-card">
                        <div class="expense-form-header">
                            <h3 class="expense-title">Expense ${index + 1}</h3>
                            <button type="button" class="btn-remove-expense remove-expense-btn" data-index="${index}" title="Remove Expense">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                        
                        <div class="expense-form-content">
                            <div class="expense-form-grid">
                                <div class="input-group">
                                    <label for="expense_sl_no_${index}">Sl. No.</label>
                                    <input type="number" id="expense_sl_no_${index}" name="expense_sl_no_${index}" />
                                    <div class="help-text">Entry number</div>
                                </div>
                                <div class="input-group">
                                    <label for="expense_particulars_${index}">Particulars *</label>
                                    <input type="text" id="expense_particulars_${index}" name="expense_particulars_${index}" required />
                                    <div class="help-text">Expense item description</div>
                                </div>
                                <div class="input-group">
                                    <label for="expense_amount_${index}">Amount (₹) *</label>
                                    <input type="number" step="0.01" id="expense_amount_${index}" name="expense_amount_${index}" required />
                                    <div class="help-text">Cost in Indian Rupees</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            container.append(html);
            index++;
            if (window.AutosaveManager && window.AutosaveManager.reinitialize) {
                window.AutosaveManager.reinitialize();
            }
        }

        function updateExpenseHeaders() {
            container.children('.expense-form-container').each(function(i) {
                $(this).find('.expense-title').text(`Expense ${i + 1}`);
                $(this).attr('data-index', i);
                $(this).find('.remove-expense-btn').attr('data-index', i);
            });
        }

        function showEmptyState() {
            if (container.children('.expense-form-container').length === 0) {
                container.html(`
                    <div class="expenses-empty-state">
                        <div class="empty-state-icon">🎤</div>
                        <h4>No expenses added yet</h4>
                        <p>Add all expense items for your event budget</p>
                    </div>
                `);
            } else {
                container.find('.expenses-empty-state').remove();
            }
        }

        $('#add-expense-btn').on('click', function() {
            addExpenseRow();
            showEmptyState();
        });

        container.on('click', '.remove-expense-btn', function() {
            $(this).closest('.expense-form-container').remove();
            updateExpenseHeaders();
            showEmptyState();
            if (window.AutosaveManager && window.AutosaveManager.reinitialize) {
                window.AutosaveManager.reinitialize();
            }
        });

        if (window.EXISTING_EXPENSES && window.EXISTING_EXPENSES.length) {
            container.empty();
            window.EXISTING_EXPENSES.forEach(ex => {
                addExpenseRow();
                const idx = index - 1;
                $(`#expense_sl_no_${idx}`).val(ex.sl_no);
                $(`#expense_particulars_${idx}`).val(ex.particulars);
                $(`#expense_amount_${idx}`).val(ex.amount);
            });
            showEmptyState();
        } else {
            showEmptyState();
        }
    }

    // ===== INCOME SECTION FUNCTIONALITY =====
    function getIncomeForm() {
        return `
            <div class="income-section">
                <div id="income-rows" class="income-container"></div>

                <div class="add-income-section">
                    <button type="button" id="add-income-btn" class="btn-add-income">
                        Add Income Item
                    </button>
                    <div class="help-text" style="text-align: center; margin-top: 0.5rem;">
                        Add all income sources for your event
                    </div>
                </div>

                <div class="form-row full-width">
                    <div class="submit-section">
                        <button type="submit" name="final_submit" class="btn-submit" id="submit-proposal-btn" disabled>
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

    function setupIncomeSection() {
        const container = $('#income-rows');
        let index = 0;

        function addIncomeRow() {
            const html = `
                <div class="income-form-container" data-index="${index}">
                    <div class="income-form-card">
                        <div class="income-form-header">
                            <h3 class="income-title">Income Item ${index + 1}</h3>
                            <button type="button" class="btn-remove-income remove-income-btn" data-index="${index}" title="Remove Income Item">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                        
                        <div class="income-form-content">
                            <div class="income-form-grid">
                                <div class="input-group">
                                    <label for="income_sl_no_${index}">Sl. No.</label>
                                    <input type="number" id="income_sl_no_${index}" name="income_sl_no_${index}" />
                                    <div class="help-text">Entry number</div>
                                </div>
                                <div class="input-group">
                                    <label for="income_particulars_${index}">Particulars *</label>
                                    <input type="text" id="income_particulars_${index}" name="income_particulars_${index}" required />
                                    <div class="help-text">Income source description</div>
                                </div>
                                <div class="input-group">
                                    <label for="income_participants_${index}">No of Participants</label>
                                    <input type="number" id="income_participants_${index}" name="income_participants_${index}" />
                                    <div class="help-text">Number of participants</div>
                                </div>
                                <div class="input-group">
                                    <label for="income_rate_${index}">Rate (₹)</label>
                                    <input type="number" step="0.01" id="income_rate_${index}" name="income_rate_${index}" />
                                    <div class="help-text">Rate per participant</div>
                                </div>
                                <div class="input-group">
                                    <label for="income_amount_${index}">Amount (₹) *</label>
                                    <input type="number" step="0.01" id="income_amount_${index}" name="income_amount_${index}" required />
                                    <div class="help-text">Total amount in Indian Rupees</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            container.append(html);
            
            // Auto-calculate amount when participants and rate change
            const participantsInput = $(`#income_participants_${index}`);
            const rateInput = $(`#income_rate_${index}`);
            const amountInput = $(`#income_amount_${index}`);
            
            function calculateAmount() {
                const participants = parseFloat(participantsInput.val()) || 0;
                const rate = parseFloat(rateInput.val()) || 0;
                const calculatedAmount = participants * rate;
                if (calculatedAmount > 0) {
                    amountInput.val(calculatedAmount.toFixed(2));
                }
            }
            
            participantsInput.on('input change', calculateAmount);
            rateInput.on('input change', calculateAmount);
            
            index++;
            if (window.AutosaveManager && window.AutosaveManager.reinitialize) {
                window.AutosaveManager.reinitialize();
            }
        }

        function updateIncomeHeaders() {
            container.children('.income-form-container').each(function(i) {
                $(this).find('.income-title').text(`Income Item ${i + 1}`);
                $(this).attr('data-index', i);
                $(this).find('.remove-income-btn').attr('data-index', i);
            });
        }

        function showEmptyState() {
            if (container.children('.income-form-container').length === 0) {
                container.html(`
                    <div class="income-empty-state">
                        <div class="empty-state-icon">🎤</div>
                        <h4>No income sources added yet</h4>
                        <p>Add income items for your event budget</p>
                    </div>
                `);
            } else {
                container.find('.income-empty-state').remove();
            }
        }

        $('#add-income-btn').on('click', function() {
            addIncomeRow();
            showEmptyState();
        });

        container.on('click', '.remove-income-btn', function() {
            $(this).closest('.income-form-container').remove();
            updateIncomeHeaders();
            showEmptyState();
            if (window.AutosaveManager && window.AutosaveManager.reinitialize) {
                window.AutosaveManager.reinitialize();
            }
        });

        // Load existing income data if available
        if (window.EXISTING_INCOME && window.EXISTING_INCOME.length) {
            container.empty();
            window.EXISTING_INCOME.forEach(inc => {
                addIncomeRow();
                const idx = index - 1;
                $(`#income_sl_no_${idx}`).val(inc.sl_no);
                $(`#income_particulars_${idx}`).val(inc.particulars);
                $(`#income_participants_${idx}`).val(inc.participants);
                $(`#income_rate_${idx}`).val(inc.rate);
                $(`#income_amount_${idx}`).val(inc.amount);
            });
            showEmptyState();
        } else {
            showEmptyState();
        }
    }
    
    // ===== SAVE SECTION FUNCTIONALITY - FULLY PRESERVED =====
    function saveCurrentSection() {
        if (!currentExpandedCard) return;

        if (validateCurrentSection()) {
            if (window.AutosaveManager && window.AutosaveManager.manualSave) {
                window.AutosaveManager.manualSave()
                    .then(() => {
                        markSectionComplete(currentExpandedCard);
                        showNotification('Section saved successfully!', 'success');

                        const nextSection = getNextSection(currentExpandedCard);
                        if (nextSection) {
                            $(`.proposal-nav .nav-link[data-section="${nextSection}"]`).removeClass('disabled');
                            setTimeout(() => {
                                openFormPanel(nextSection);
                            }, 1000);
                        }
                    })
                    .catch(err => {
                        console.error('Autosave failed:', err);
                        if (err && err.errors) {
                            handleAutosaveErrors(err);
                        }
                        showNotification('Autosave failed. Please check for missing fields.', 'error');
                    });
            } else {
                markSectionComplete(currentExpandedCard);
            }
        } else {
            showNotification('Please complete all required fields.', 'error');
        }
    }

    // ===== SECTION NAVIGATION - PRESERVED =====
    function getNextSection(currentSection) {
        const sectionOrder = ['basic-info', 'why-this-event', 'schedule', 'speakers', 'expenses', 'income'];
        const currentIndex = sectionOrder.indexOf(currentSection);
        return currentIndex < sectionOrder.length - 1 ? sectionOrder[currentIndex + 1] : null;
    }

    // ===== FORM FIELD SYNC - FULLY PRESERVED =====
    function setupFormFieldSync() {
        $('#form-panel-content').on('input.sync change.sync', 'input, textarea, select', function() {
            const fieldId = $(this).attr('id');
            if (fieldId && fieldId.endsWith('-modern')) {
                if (fieldId === 'student-coordinators-modern') return; // handled separately
                let baseName = fieldId.replace('-modern', '').replace(/-/g, '_');
                if (fieldId === 'schedule-modern') {
                    baseName = 'flow';
                }
                let djangoField = $(`#django-forms [name="${baseName}"]`);
                if (!djangoField.length && baseName === 'flow') {
                    djangoField = $(`textarea[name="flow"]`);
                }
                if (djangoField.length) {
                    djangoField.val($(this).val());
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

    function collectBasicInfo() {
        const getVal = (modernSelector, djangoName) => {
            const modern = $(modernSelector);
            if (modern.length && modern.val()) return modern.val();
            return $(`#django-basic-info [name="${djangoName}"]`).val() || '';
        };
        return {
            title: getVal('#event-title-modern', 'event_title'),
            audience: getVal('#target-audience-modern', 'target_audience'),
            focus: getVal('#event-focus-type-modern', 'event_focus_type'),
            venue: getVal('#venue-modern', 'venue')
        };
    }

    function setupWhyThisEventAI() {
        const cfg = [
            {btn: '#btn-ai-need', field: '#need-analysis-modern', url: window.AI_NEED_URL},
            {btn: '#btn-ai-objectives', field: '#objectives-modern', url: window.AI_OBJECTIVES_URL},
            {btn: '#btn-ai-outcomes', field: '#outcomes-modern', url: window.AI_OUTCOMES_URL}
        ];

        cfg.forEach(({btn, field, url}) => {
            $(btn).off('click').on('click', async function() {
                const textarea = $(field);
                const payload = collectBasicInfo();
                payload.context = textarea.val();
                const btnEl = $(this);
                const original = btnEl.text();
                btnEl.prop('disabled', true).text('Generating...');
                try {
                    const fd = new FormData();
                    Object.entries(payload).forEach(([k, v]) => fd.append(k, v || ''));
                    const resp = await fetch(url, {
                        method: 'POST',
                        headers: {'X-CSRFToken': csrftoken},
                        body: fd
                    });
                    const data = await resp.json();
                    if (data.ok) {
                        textarea.val(data.text);
                        textarea.trigger('input');
                    } else {
                        showNotification(data.error || 'Generation failed', 'error');
                    }
                } catch (err) {
                    showNotification('AI request failed', 'error');
                } finally {
                    btnEl.prop('disabled', false).text(original);
                }
            });
        });
    }

    // ===== STATUS & PROGRESS FUNCTIONS - PRESERVED =====
    function markSectionInProgress(section) {
        sectionProgress[section] = 'in-progress';
        const navLink = $(`.proposal-nav .nav-link[data-section="${section}"]`);
        navLink.addClass('in-progress').removeClass('completed disabled');
        console.log(`Section ${section} marked as in progress`);
    }

    function markSectionComplete(section) {
        sectionProgress[section] = true;
        const navLink = $(`.proposal-nav .nav-link[data-section="${section}"]`);
        navLink.addClass('completed').removeClass('in-progress disabled');
        unlockNextSection(section);
        
        // Also enable navigation to all previously completed sections
        enablePreviouslyVisitedSections();
        
        console.log(`Section ${section} marked as complete`);
        updateProgressBar();
        updateSubmitButton();
    }

    function autofillTestData(section) {
        const today = new Date().toISOString().split('T')[0];

        if (section === 'basic-info') {
            const fields = {
                'event-title-modern': getRandom(AUTO_FILL_DATA.titles),
                'target-audience-modern': getRandom(AUTO_FILL_DATA.audiences),
                'target-audience-class-ids': '1',
                'venue-modern': getRandom(AUTO_FILL_DATA.venues),
                'event-focus-type-modern': getRandom(AUTO_FILL_DATA.focusTypes),
                'event-start-date': today,
                'event-end-date': today,
                'academic-year-modern': '2024-2025',
                'pos-pso-modern': 'PO1, PSO2',
                'sdg-goals-modern': 'Goal 4',
                'num-activities-modern': '1'
            };

            Object.entries(fields).forEach(([id, value]) => {
                const el = document.getElementById(id);
                if (!el) return;
                el.value = value;
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            });

            // Fill dynamic activity once rendered
            setTimeout(() => {
                const actName = document.getElementById('activity_name_1');
                const actDate = document.getElementById('activity_date_1');
                if (actName) actName.value = 'Intro Session';
                if (actDate) actDate.value = today;
            }, 150);

            const sc = document.getElementById('student-coordinators-modern');
            if (sc && !sc.options.length) {
                sc.appendChild(new Option('Demo Student', '1', true, true));
                sc.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }

        if (section === 'why-this-event') {
            const need = document.getElementById('need-analysis-modern');
            const obj = document.getElementById('objectives-modern');
            const out = document.getElementById('outcomes-modern');
            if (need) need.value = getRandom(AUTO_FILL_DATA.need);
            if (obj) obj.value = getRandom(AUTO_FILL_DATA.objectives);
            if (out) out.value = getRandom(AUTO_FILL_DATA.outcomes);
        }

        if (section === 'schedule') {
            const sched = document.getElementById('schedule-modern');
            if (sched) sched.value = getRandom(AUTO_FILL_DATA.schedule);
        }

        if (section === 'speakers') {
            document.getElementById('add-speaker-btn')?.click();
            setTimeout(() => {
                const idx = 0;
                const name = document.getElementById(`speaker_full_name_${idx}`);
                const desig = document.getElementById(`speaker_designation_${idx}`);
                const aff = document.getElementById(`speaker_affiliation_${idx}`);
                const email = document.getElementById(`speaker_contact_email_${idx}`);
                const phone = document.getElementById(`speaker_contact_number_${idx}`);
                const linked = document.getElementById(`speaker_linkedin_url_${idx}`);
                const bio = document.getElementById(`speaker_detailed_profile_${idx}`);
                if (name) name.value = getRandom(AUTO_FILL_DATA.speakerNames);
                if (desig) desig.value = getRandom(AUTO_FILL_DATA.designations);
                if (aff) aff.value = getRandom(AUTO_FILL_DATA.affiliations);
                if (email) email.value = getRandom(AUTO_FILL_DATA.emails);
                if (phone) phone.value = getRandom(AUTO_FILL_DATA.phones);
                if (linked) linked.value = getRandom(AUTO_FILL_DATA.linkedins);
                if (bio) bio.value = getRandom(AUTO_FILL_DATA.bios);
            }, 100);
        }

        if (section === 'expenses') {
            document.getElementById('add-expense-btn')?.click();
            setTimeout(() => {
                const idx = 0;
                const sl = document.getElementById(`expense_sl_no_${idx}`);
                const part = document.getElementById(`expense_particulars_${idx}`);
                const amt = document.getElementById(`expense_amount_${idx}`);
                if (sl) sl.value = '1';
                if (part) part.value = getRandom(AUTO_FILL_DATA.expenseItems);
                if (amt) amt.value = '1000';
            }, 100);
        }

        if (section === 'income') {
            document.getElementById('add-income-btn')?.click();
            setTimeout(() => {
                const idx = 0;
                const sl = document.getElementById(`income_sl_no_${idx}`);
                const part = document.getElementById(`income_particulars_${idx}`);
                const partCount = document.getElementById(`income_participants_${idx}`);
                const rate = document.getElementById(`income_rate_${idx}`);
                const amt = document.getElementById(`income_amount_${idx}`);
                if (sl) sl.value = '1';
                if (part) part.value = getRandom(AUTO_FILL_DATA.incomeItems);
                if (partCount) partCount.value = '50';
                if (rate) rate.value = '100';
                if (amt) amt.value = '5000';
            }, 100);
        }
    }

    function unlockNextSection(section) {
        const currentNavLink = $(`.proposal-nav .nav-link[data-section="${section}"]`);
        if (!currentNavLink.length) {
            console.warn('unlockNextSection: currentNavLink not found for section', section);
            return;
        }
        const currentOrder = parseInt(currentNavLink.data('order'));
        const nextOrder = currentOrder + 1;
        const nextNavLink = $(`.proposal-nav .nav-link[data-order="${nextOrder}"]`);
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
        firstErrorField = null;

        let valid = false;
        switch (currentExpandedCard) {
            case 'basic-info':
                valid = validateBasicInfo();
                break;
            case 'why-this-event':
                valid = validateWhyThisEvent();
                break;
            case 'schedule':
                valid = validateSchedule();
                break;
            case 'speakers':
                valid = validateSpeakers();
                break;
            case 'expenses':
                valid = validateExpenses();
                break;
            case 'income':
                valid = validateIncome();
                break;
            default:
                valid = true;
        }

        if (!valid && firstErrorField && firstErrorField.length) {
            $('html, body').animate({scrollTop: firstErrorField.offset().top - 100}, 500);
            firstErrorField.focus();
        }

        return valid;
    }
    
    function validateSchedule() {
        const scheduleField = $('#schedule-modern');
        if (!scheduleField.val() || scheduleField.val().trim() === '') {
            showFieldError(scheduleField, 'Schedule is required');
            scheduleField.addClass('animate-shake');
            setTimeout(() => scheduleField.removeClass('animate-shake'), 600);
            return false;
        }
        return true;
    }
    
    function validateSpeakers() {
        // Speakers section is optional - always return true
        // If speakers are added, validate them, but don't require at least one speaker
        const speakerContainers = $('.speaker-form-container');
        
        if (speakerContainers.length === 0) {
            // No speakers added - this is fine since speakers are optional
            return true;
        }
        
        let isValid = true;
        speakerContainers.each(function() {
            const container = $(this);
            const requiredFields = container.find('input[required], textarea[required]');
            
            requiredFields.each(function() {
                if (!$(this).val() || $(this).val().trim() === '') {
                    const fieldName = $(this).closest('.input-group').find('label').text().replace(' *', '');
                    showFieldError($(this), `${fieldName} is required`);
                    isValid = false;
                }
            });
        });
        
        return isValid;
    }
    
    function validateExpenses() {
        // Expenses section is optional - always return true
        // If expenses are added, validate them, but don't require at least one expense
        const expenseContainers = $('.expense-form-container');
        
        if (expenseContainers.length === 0) {
            // No expenses added - this is fine since expenses are optional
            return true;
        }
        
        let isValid = true;
        expenseContainers.each(function() {
            const container = $(this);
            const requiredFields = container.find('input[required]');
            
            requiredFields.each(function() {
                if (!$(this).val() || $(this).val().trim() === '') {
                    const fieldName = $(this).closest('.input-group').find('label').text().replace(' *', '');
                    showFieldError($(this), `${fieldName} is required`);
                    isValid = false;
                }
            });
        });
        
        return isValid;
    }

    function validateIncome() {
        // Income section is optional - always return true
        // If income items are added, validate them, but don't require at least one income item
        const incomeContainers = $('.income-form-container');
        
        if (incomeContainers.length === 0) {
            // No income items added - this is fine since income is optional
            return true;
        }
        
        let isValid = true;
        incomeContainers.each(function() {
            const container = $(this);
            const requiredFields = container.find('input[required]');
            
            requiredFields.each(function() {
                if (!$(this).val() || $(this).val().trim() === '') {
                    const fieldName = $(this).closest('.input-group').find('label').text().replace(' *', '');
                    showFieldError($(this), `${fieldName} is required`);
                    isValid = false;
                }
            });
        });
        
        return isValid;
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
                window.AutosaveManager.manualSave().catch(() => {});
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
            if (!firstErrorField) {
                firstErrorField = field;
            }
        }
    }

    function handleAutosaveErrors(errorData) {
        const errors = errorData?.errors || errorData;
        if (!errors) return;
        clearValidationErrors();
        firstErrorField = null;

        const mark = (name, message) => {
            let field = $(`#${name.replace(/_/g, '-')}-modern`);
            if (!field.length) {
                field = $(`[name="${name}"]`);
                if (field.length && field.attr('type') === 'hidden') {
                    const alt = $(`#${field.attr('id')}-modern`);
                    if (alt.length) field = alt;
                }
            }
            if (field.length) {
                showFieldError(field, message);
            }
        };

        Object.entries(errors).forEach(([key, val]) => {
            if (Array.isArray(val)) {
                mark(key, val[0]);
            } else if (typeof val === 'object') {
                Object.entries(val).forEach(([idx, sub]) => {
                    if (key === 'activities') {
                        if (sub.name) mark(`activity_name_${idx}`, sub.name);
                        if (sub.date) mark(`activity_date_${idx}`, sub.date);
                    } else if (key === 'speakers') {
                        if (sub.full_name) mark(`speaker_full_name_${idx}`, sub.full_name);
                        if (sub.designation) mark(`speaker_designation_${idx}`, sub.designation);
                        if (sub.affiliation) mark(`speaker_affiliation_${idx}`, sub.affiliation);
                        if (sub.contact_email) mark(`speaker_contact_email_${idx}`, sub.contact_email);
                        if (sub.detailed_profile) mark(`speaker_detailed_profile_${idx}`, sub.detailed_profile);
                        if (sub.contact_number) mark(`speaker_contact_number_${idx}`, sub.contact_number);
                        if (sub.linkedin_url) mark(`speaker_linkedin_url_${idx}`, sub.linkedin_url);
                    } else if (key === 'expenses') {
                        if (sub.particulars) mark(`expense_particulars_${idx}`, sub.particulars);
                        if (sub.amount) mark(`expense_amount_${idx}`, sub.amount);
                    } else if (key === 'income') {
                        if (sub.particulars) mark(`income_particulars_${idx}`, sub.particulars);
                        if (sub.participants) mark(`income_participants_${idx}`, sub.participants);
                        if (sub.rate) mark(`income_rate_${idx}`, sub.rate);
                        if (sub.amount) mark(`income_amount_${idx}`, sub.amount);
                    }
                });
            }
        });

        if (firstErrorField && firstErrorField.length) {
            $('html, body').animate({scrollTop: firstErrorField.offset().top - 100}, 500);
            firstErrorField.focus();
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
            window.autosaveDraft().catch(() => {});
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

        $(document).on('autosave:error', function(e) {
            const indicator = $('#autosave-indicator');
            indicator.removeClass('saving saved').addClass('error show');
            indicator.find('.indicator-text').text('Save Failed');
            if (e.originalEvent && e.originalEvent.detail) {
                handleAutosaveErrors(e.originalEvent.detail);
            }
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

function getCookie(name){const v=`; ${document.cookie}`.split(`; ${name}=`);if(v.length===2)return v.pop().split(';').shift();}
function val(sel){return document.querySelector(sel)?.value?.trim()||"";}
function arr(sel){return Array.from(document.querySelectorAll(sel)).map(x=>x.value).filter(Boolean);}

function collectFactsFromForm(){
  return {
    organization_type: val('#id_organization_type') || val('#id_type_of_organisation'),
    department: val('#id_department'),
    committees_collaborations: arr('input[name="committees_collaborations"]'),
    event_title: val('#id_event_title') || val('#id_title'),
    target_audience: val('#id_target_audience'),
    event_focus_type: val('#id_event_focus_type') || val('#id_focus'),
    location: val('#id_location'),
    start_date: val('#id_start_date'),
    end_date: val('#id_end_date'),
    academic_year: val('#id_academic_year'),
    pos_pso_management: val('#id_pos_pso_management') || val('#id_pos_pso'),
    sdg_goals: arr('select#id_sdg_goals option:checked').map(o=>o.textContent.trim()),
    num_activities: val('#id_num_activities'),
    student_coordinators: arr('input[name="student_coordinators"]'),
    faculty_incharges: arr('input[name="faculty_incharges"]'),
    additional_context: val('#id_additional_context')
  };
}

function applyBullets(field, items){
  const el = document.querySelector(`#id_${field}`);
  const text = (items || []).map(i=>`• ${i}`).join('\n');
  if (window.CKEDITOR && CKEDITOR.instances[`id_${field}`]) {
    CKEDITOR.instances[`id_${field}`].setData((CKEDITOR.instances[`id_${field}`].getData()?'<p></p>':'') + text.replace(/\n/g,'<br>'));
  } else if (el) {
    el.value = text;
    el.dispatchEvent(new Event('input',{bubbles:true}));
  }
}

function applyText(field, text){
  const el = document.querySelector(`#id_${field}`);
  if (window.CKEDITOR && CKEDITOR.instances[`id_${field}`]) {
    CKEDITOR.instances[`id_${field}`].setData(text);
  } else if (el) {
    el.value = text;
    el.dispatchEvent(new Event('input',{bubbles:true}));
  }
}

async function generateWhyEvent(){
  const btn = document.querySelector('#btn-generate-why') || this;
  const orig = btn?.innerHTML; if (btn) btn.innerHTML='Generating…';
  try{
    const facts = collectFactsFromForm();
    const body = new URLSearchParams(Object.entries(facts));
    const res = await fetch('/suite/generate-why-event/', {
      method:'POST',
      headers:{'X-CSRFToken':getCookie('csrftoken')},
      body
    });
    const data = await res.json();
    if(!res.ok || !data.ok){ alert(data.error || 'Generation failed'); return; }
    applyText('need_analysis', data.need_analysis || '');
    applyBullets('objectives', data.objectives || []);
    applyBullets('learning_outcomes', data.learning_outcomes || []);
    if (typeof window.autosave === 'function') window.autosave();
  }catch(e){ console.error(e); alert('Generation failed'); }
  finally{ if(btn) btn.innerHTML = orig || 'Generate with AI'; }
}
document.addEventListener('DOMContentLoaded',()=>{
  const b = document.querySelector('#btn-generate-why');
  if (b && !b._wired){ b.addEventListener('click', generateWhyEvent); b._wired = true; }
});
