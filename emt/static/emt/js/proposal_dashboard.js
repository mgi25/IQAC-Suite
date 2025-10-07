function showLoadingOverlay() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.add('show');
    }
}

function hideLoadingOverlay() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.remove('show');
    }
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
        'expenses': false,
        'income': false,
        'cdl-support': false
    };
    const optionalSections = ['speakers', 'expenses', 'income', 'cdl-support'];
    let firstErrorField = null;
    let lastValidationIssues = [];
    let scheduleTableBody = null;
    let scheduleHiddenField = null;
    let speakersHiddenField = null;
    let expensesHiddenField = null;
    let incomeHiddenField = null;
    const autoFillEnabled = new URLSearchParams(window.location.search).has('autofill');
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const originalFormAction = $('#proposal-form').attr('action') || '';
    let isAutofilling = false;
    const SECTION_AUTOFILL_ORDER = ['basic-info', 'why-this-event', 'schedule', 'speakers', 'expenses', 'income'];

    const delay = (ms = 200) => new Promise(resolve => setTimeout(resolve, ms));

    const cleanFieldValue = (value) => {
        if (value === undefined || value === null) return '';
        return String(value).trim();
    };

    const parseSerializedArray = (raw) => {
        if (!raw) return [];
        try {
            const text = typeof raw === 'string' ? raw.trim() : String(raw || '').trim();
            if (!text) return [];
            const parsed = JSON.parse(text);
            return Array.isArray(parsed) ? parsed : [];
        } catch (err) {
            console.warn('Failed to parse serialized section payload', err);
            return [];
        }
    };

    const readSerializedField = (field) => {
        if (!field) return [];
        if (Object.prototype.hasOwnProperty.call(field, 'value')) {
            return parseSerializedArray(field.value);
        }
        return parseSerializedArray(field.textContent);
    };

    const writeSerializedField = (field, items) => {
        if (!field) return;
        const payload = (Array.isArray(items) && items.length)
            ? JSON.stringify(items)
            : '[]';
        if (Object.prototype.hasOwnProperty.call(field, 'value')) {
            if (field.value !== payload) {
                field.value = payload;
            }
        } else if (field.textContent !== payload) {
            field.textContent = payload;
        }
        field.dispatchEvent(new Event('input', { bubbles: true }));
    };

    const getStoredSectionData = (fieldId, fallback = []) => {
        const field = document.getElementById(fieldId);
        const stored = readSerializedField(field);
        if (stored.length) {
            return stored;
        }
        if (Array.isArray(fallback) && fallback.length) {
            return fallback;
        }
        return [];
    };

    // Demo data used for rapid prototyping. Remove once real data is wired.
    const AUTO_FILL_DATA = {
        titles: [
            'Data Science & AI Collaboration Summit',
            'Intelligent Systems Innovation Day',
            'Analytics for Social Impact Workshop'
        ],
        venues: ['Innovation Lab', 'Tech Collaboration Hub', 'Virtual Intelligence Studio'],
        focusTypes: ['Interdisciplinary Workshop', 'Research Colloquium', 'Hands-on Bootcamp'],
        objectives: [
            '• Build collaboration between Data Science and Computer Science teams\n• Share successful interdisciplinary project case studies\n• Identify new avenues for student industry engagement',
            '• Provide hands-on exposure to cutting-edge analytics tools\n• Encourage joint problem-solving across departments\n• Prepare participants for collaborative capstone projects',
            '• Strengthen cross-functional research pipelines\n• Develop mentor networks for student innovators\n• Align departmental initiatives with institutional IQAC goals'
        ],
        outcomes: [
            'Participants document a roadmap for Data Science and Computer Science collaborations.',
            'Inter-department mentor groups formed to support ongoing analytics initiatives.',
            'Prototype ideas shortlisted for institutional funding and external showcases.'
        ],
        need: [
            'To unify Data Science and Computer Science initiatives under a single collaborative program.',
            'To ensure students gain industry-ready exposure by working with both analytics and engineering mentors.',
            'To accelerate interdisciplinary research outputs aligned with institutional strategic plans.'
        ],
        schedule: [
            '09:00 AM - Welcome & Orientation\n11:00 AM - Joint Data Lab\n14:00 PM - Innovation Showcase',
            '10:00 AM - Strategy Briefing\n12:30 PM - Faculty Roundtable\n15:00 PM - Project Pitch Session'
        ],
        speakerNames: ['Dr. Kavya Menon', 'Prof. Arun Pillai', 'Ms. Neha Ramesh'],
        designations: ['Head of Data Science', 'Professor of Computer Science', 'Industry Mentor'],
        affiliations: ['Department of Data Science', 'School of Computer Science', 'AI Innovation Hub'],
        emails: ['kavya.menon@example.edu', 'arun.pillai@example.edu', 'neha.ramesh@example.com'],
        phones: ['9876543210', '9123456780', '9988776655'],
        linkedins: [
            'https://www.linkedin.com/in/kavyamenon',
            'https://www.linkedin.com/in/arunpillai',
            'https://www.linkedin.com/in/neharamesh'
        ],
        bios: [
            'Researcher focusing on applied machine learning, leading collaborative projects across CS and Data Science.',
            'Specialist in distributed systems and AI integration with extensive industry collaboration experience.',
            'Innovation strategist mentoring analytics-driven startups and academic hackathons.'
        ],
        expenseItems: ['Collaboration Lab Setup', 'Expert Honorarium', 'Workshop Materials & Logistics'],
        incomeItems: ['Registration Fees', 'Department Funding Support', 'Industry Sponsorship'],
        scheduleRows: [
            { time: '09:00', activity: 'Welcome & Collaboration Roadmap' },
            { time: '11:00', activity: 'Hands-on Data Lab with CS & DS Teams' },
            { time: '14:00', activity: 'Innovation Showcase & Feedback' }
        ],
        speakerProfiles: [
            {
                full_name: 'Dr. Kavya Menon',
                designation: 'Head of Data Science',
                affiliation: 'Department of Data Science',
                email: 'kavya.menon@example.edu',
                phone: '9876543210',
                linkedin: 'https://www.linkedin.com/in/kavyamenon',
                bio: 'Researcher focusing on applied machine learning, leading collaborative projects across CS and Data Science.'
            },
            {
                full_name: 'Prof. Arun Pillai',
                designation: 'Professor of Computer Science',
                affiliation: 'School of Computer Science',
                email: 'arun.pillai@example.edu',
                phone: '9123456780',
                linkedin: 'https://www.linkedin.com/in/arunpillai',
                bio: 'Specialist in distributed systems and AI integration with extensive industry collaboration experience.'
            }
        ],
        expenseRows: [
            { sl: '1', particulars: 'Collaboration Lab Setup', amount: '15000' },
            { sl: '2', particulars: 'Expert Honorarium', amount: '12000' },
            { sl: '3', particulars: 'Workshop Materials & Logistics', amount: '8000' }
        ],
        incomeRows: [
            { sl: '1', particulars: 'Registration Fees', participants: '80', rate: '250', amount: '20000' },
            { sl: '2', particulars: 'Department Funding Support', participants: '1', rate: '15000', amount: '15000' }
        ],
        activityPlan: [
            { name: 'Orientation & Goals with Faculty Incharge', daysFromStart: 0 },
            { name: 'Joint Coding Sprint', daysFromStart: 0 },
            { name: 'Industry Collaboration Meeting', daysFromStart: 1 }
        ]
    };

    const getRandom = arr => arr[Math.floor(Math.random() * arr.length)];

    const setFieldValue = (element, value) => {
        if (!element) return;
        element.value = value;
        try {
            element.dispatchEvent(new Event('input', { bubbles: true }));
        } catch (e) { /* noop */ }
        try {
            element.dispatchEvent(new Event('change', { bubbles: true }));
        } catch (e) { /* noop */ }
    };

    const setFieldValueById = (id, value) => {
        const el = document.getElementById(id);
        if (el) {
            setFieldValue(el, value);
        }
    };

    const waitForCondition = (conditionFn, { timeout = 4000, interval = 100 } = {}) => new Promise((resolve, reject) => {
        const start = Date.now();
        (function check() {
            let result = null;
            try {
                result = conditionFn();
            } catch (err) {
                result = null;
            }
            if (result) {
                resolve(result);
                return;
            }
            if (Date.now() - start >= timeout) {
                reject(new Error('Timeout waiting for condition'));
                return;
            }
            setTimeout(check, interval);
        })();
    });

    const waitForTomSelect = (selector, options = {}) =>
        waitForCondition(() => $(selector)[0]?.tomselect, options).then(() => $(selector)[0].tomselect);

    const safeFetchJson = async (url) => {
        if (!url) return null;
        try {
            const resp = await fetch(url, { credentials: 'same-origin' });
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            return await resp.json();
        } catch (err) {
            console.warn('safeFetchJson failed', url, err);
            return null;
        }
    };

    const findTomSelectOptionValue = (tom, text) => {
        if (!tom || !text) return null;
        const target = text.toLowerCase().trim();
        return Object.keys(tom.options || {}).find(value => {
            const optionText = (tom.options[value]?.text || '').toLowerCase().trim();
            return optionText === target;
        }) || null;
    };

    const addDaysToDate = (dateStr, days = 0) => {
        if (!dateStr) return dateStr;
        const parts = dateStr.split('-').map(part => parseInt(part, 10));
        if (parts.length !== 3 || parts.some(num => Number.isNaN(num))) {
            return dateStr;
        }
        const [year, month, day] = parts;
        const base = new Date(year, month - 1, day);
        if (Number.isFinite(days)) {
            base.setDate(base.getDate() + days);
        }
        const yyyy = base.getFullYear();
        const mm = String(base.getMonth() + 1).padStart(2, '0');
        const dd = String(base.getDate()).padStart(2, '0');
        return `${yyyy}-${mm}-${dd}`;
    };

    function updateCdlNavLink(proposalId) {
        if (!proposalId) return;
        const link = $('.proposal-nav .nav-link[data-section="cdl-support"]');
        const url = `/emt/cdl-support/${proposalId}/`;
        link.data('url', url);
        link.attr('data-url', url);
    }

    let resetBtn, formFields;

    function updateResetButtonState() {
        if (!resetBtn || !formFields) return;
        const hasValue = formFields.toArray().some(el => {
            const $el = $(el);
            if (el.type === 'hidden') return false;
            if (el.type === 'checkbox' || el.type === 'radio') {
                return $el.is(':checked');
            }
            return Boolean($el.val());
        });
        resetBtn.prop('disabled', !(hasValue || window.PROPOSAL_ID));
    }

    function resetProposalDraft() {
        if (window.PROPOSAL_ID) {
            if (!confirm('Are you sure you want to reset this draft?')) return;
            const pid = window.PROPOSAL_ID;
            fetch(window.RESET_DRAFT_URL, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.AUTOSAVE_CSRF || ''
                },
                body: JSON.stringify({ proposal_id: pid })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    window.location.href = window.RESET_DRAFT_REDIRECT_URL;
                } else {
                    alert('Failed to reset draft');
                }
            })
            .catch(() => alert('Failed to reset draft'));
            return;
        }

        if (!confirm('Are you sure you want to reset this draft?')) return;

        const form = document.getElementById('proposal-form');
        if (form) {
            const orgTypeInput = $('#org-type-modern-input')[0];
            const orgTypeTS = orgTypeInput ? orgTypeInput.tomselect : null;
            const orgTypeSelect = $('#django-basic-info [name="organization_type"]');
            const preservedOrgType = orgTypeTS ? orgTypeTS.getValue() : orgTypeSelect.val();
            const orgTypeText = orgTypeTS?.options[preservedOrgType]?.text?.toLowerCase().trim() ||
                orgTypeSelect.find(`option[value="${preservedOrgType}"]`).text().toLowerCase().trim();
            const preservedOrg = $('#django-basic-info [name="organization"]').val();
            const preservedAcademicYear = $('#academic-year-modern').val();

            form.reset();
            Array.from(form.elements).forEach(el => {
                el.classList.remove('is-invalid', 'is-valid', 'has-error');
                $(el).siblings('.error-message').remove();
            });

            orgTypeSelect.val(preservedOrgType);
            $('#django-basic-info [name="organization"]').val(preservedOrg);
            $('#django-basic-info [name="academic_year"]').val(preservedAcademicYear);

            if (orgTypeTS && preservedOrgType) {
                orgTypeTS.setValue(preservedOrgType, true);
                if (orgTypeText) {
                    handleOrgTypeChange(orgTypeText, true);
                }
            }

            if (preservedAcademicYear) {
                $('#academic-year-modern').val(preservedAcademicYear).trigger('change');
            }

            $(form).find('input, textarea, select').not('#org-type-modern-input').trigger('change');
        }

        ['section_need_analysis', 'section_objectives', 'section_outcomes', 'section_flow']
            .forEach(key => localStorage.removeItem(key));

        if (window.AutosaveManager && window.AutosaveManager.clearLocal) {
            window.AutosaveManager.clearLocal();
        }

        clearValidationErrors();
        updateResetButtonState();
    }

    initializeDashboard();

    function initializeDashboard() {
        // Initialize navigation state first
        initializeNavigationState();
        
        setupFormHandling();
        updateProgressBar();
        loadExistingData();
        checkForExistingErrors();
        enablePreviouslyVisitedSections();

        resetBtn = $('#reset-draft-btn');
        formFields = $('#proposal-form').find('input, textarea, select');
        formFields.on('change keyup', updateResetButtonState);
        updateResetButtonState();

        if (window.PROPOSAL_ID) {
            updateCdlNavLink(window.PROPOSAL_ID);
        }

        $('#autofill-btn').on('click', () => {
            autofillAllSections().catch(err => {
                console.error('Autofill failed', err);
            });
        });
        resetBtn.on('click', resetProposalDraft);
        if (!$('.form-errors-banner').length) {
            setTimeout(() => {
                activateSection('basic-info');
            }, 250);
        }
    }

    function enablePreviouslyVisitedSections() {
        // Allow free navigation across sections regardless of completion state
        $('.proposal-nav .nav-link').removeClass('disabled');
    }

    function checkForExistingErrors() {
        if ($('.form-errors-banner').length) {
            activateSection('basic-info');
        }
    }

    function setupFormHandling() {
        // Allow navigation between sections without blocking on validation
        $('.proposal-nav .nav-link').on('click', function(e) {
            e.preventDefault();
            const $this = $(this);
            const section = $this.data('section');
            if (!section) return;

            const currentOrder = parseInt($(`.proposal-nav .nav-link[data-section="${currentExpandedCard}"]`).data('order')) || 0;
            const targetOrder = parseInt($this.data('order')) || 0;

            // Always allow navigation to basic-info
            if (section === 'basic-info') {
                activateSection(section);
                return;
            }

            if (targetOrder > currentOrder && currentExpandedCard &&
                !sectionProgress[currentExpandedCard] && currentExpandedCard !== 'basic-info') {
                // Mark current section as in-progress if not completed yet
                markSectionInProgress(currentExpandedCard);
            }

            $this.removeClass('disabled');
            activateSection(section);
        });
        
        $(document).on('click', '.btn-save-section', function(e) {
            e.preventDefault();
            e.stopPropagation();
            saveCurrentSection();
        });
    }

    function activateSection(section) {
        if (currentExpandedCard === section) return;

        persistCurrentSectionState();

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

    function persistCurrentSectionState() {
        if (!currentExpandedCard) return;

        switch (currentExpandedCard) {
            case 'schedule':
                serializeSchedule();
                break;
            case 'speakers':
                serializeSpeakers();
                break;
            case 'expenses':
                serializeExpenses();
                break;
            case 'income':
                serializeIncome();
                break;
            default:
                break;
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

        const formEl = $('#proposal-form');
        if (section === 'cdl-support') {
            const url = $('.proposal-nav .nav-link[data-section="cdl-support"]').data('url');
            if (url) {
                formEl.attr('action', url);
                fetch(url, { credentials: 'same-origin' })
                    .then(res => res.text())
                    .then(html => {
                        const parser = new DOMParser();
                        const doc = parser.parseFromString(html, 'text/html');
                        const cdlForm = doc.querySelector('#cdl-form');
                        $('#form-panel-content').html(cdlForm ? cdlForm.innerHTML : html);
                        
                        // Add submit section after CDL form content
                        addSubmitSection();
                        
                        setupCDLForm();
                        setupFormFieldSync();
                        setupTextSectionStorage();
                        clearValidationErrors();
                        if (window.AutosaveManager && window.AutosaveManager.reinitialize) {
                            window.AutosaveManager.reinitialize();
                        }
                        updateSubmitButton();
                    })
                    .catch(() => {
                        $('#form-panel-content').html('<div class="form-grid"><p>Failed to load CDL Support form.</p></div>');
                        addSubmitSection(); // Still add submit section even if CDL form fails
                    });
            } else {
                $('#form-panel-content').html('<div class="form-grid"><p>CDL Support form not available.</p></div>');
                addSubmitSection(); // Still add submit section
            }
            return;
        } else {
            formEl.attr('action', originalFormAction);
            // Remove submit section if it exists when not in CDL support
            removeSubmitSection();
        }

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
            // Load any saved draft values before initializing widgets
            if (window.AutosaveManager && window.AutosaveManager.reinitialize) {
                window.AutosaveManager.reinitialize();
            }

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
            if (section === 'schedule') {
                setupScheduleSection();
            }
            if (section === 'why-this-event') {
                setupWhyThisEventAI();
            }
            setupFormFieldSync();
            setupTextSectionStorage();
            clearValidationErrors();
            if (window.AutosaveManager && window.AutosaveManager.reinitialize) {
                window.AutosaveManager.reinitialize();
                const actInput = document.getElementById('num-activities-modern');
                if (actInput && actInput.value) {
                    actInput.dispatchEvent(new Event('input'));
                }
            }
            if (autoFillEnabled) {
                Promise.resolve(autofillTestData(section)).catch(err => {
                    console.error('Autofill (query) failed', err);
                });
            }
            if (section === 'schedule') {
                populateTable();
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
            'income': { title: 'Details of Income', subtitle: 'Registration fees, sponsorship, participation rates' },
            'cdl-support': { title: 'CDL Support', subtitle: 'Poster, certificates, other details' }
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
        const academicYearHidden = $('#academic-year-hidden');
        if (academicYearField.length) {
            if (!academicYearField.val()) {
                const currentYear = new Date().getFullYear();
                const currentMonth = new Date().getMonth();
                const startYear = currentMonth >= 6 ? currentYear : currentYear - 1; // Assuming academic year starts in July
                const endYear = startYear + 1;
                academicYearField.val(`${startYear}-${endYear}`);
            }
            academicYearField.on('change', function() {
                if (academicYearHidden.length) {
                    academicYearHidden.val($(this).val());
                }
            }).trigger('change');
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

        const djangoNumActivitiesField = document.querySelector('#django-basic-info [name="num_activities"]');
        const djangoBasicInfoEl = document.getElementById('django-basic-info');
        let activitySeeds = normalizeActivitiesSeed(window.EXISTING_ACTIVITIES);
        if ((!activitySeeds || !activitySeeds.length) && djangoBasicInfoEl) {
            const datasetSeed = normalizeActivitiesSeed(djangoBasicInfoEl.dataset.activities || '');
            if (datasetSeed.length) {
                activitySeeds = datasetSeed;
            }
        }
        if (activitySeeds && activitySeeds.length) {
            window.EXISTING_ACTIVITIES = activitySeeds;
        }
        let isSyncingActivitiesCount = false;

        function reindexActivityRows() {
            const rows = container.querySelectorAll('.activity-row');
            rows.forEach((row, idx) => {
                const num = idx + 1;
                const nameInput = row.querySelector('input[id^="activity_name"]');
                const dateInput = row.querySelector('input[id^="activity_date"]');
                const nameLabel = row.querySelector('label[for^="activity_name"]');
                const dateLabel = row.querySelector('label[for^="activity_date"]');
                if (nameInput && nameLabel) {
                    nameInput.id = nameInput.name = `activity_name_${num}`;
                    nameLabel.setAttribute('for', `activity_name_${num}`);
                    nameLabel.textContent = `${num}. Activity Name`;
                }
                if (dateInput && dateLabel) {
                    dateInput.id = dateInput.name = `activity_date_${num}`;
                    dateLabel.setAttribute('for', `activity_date_${num}`);
                    dateLabel.textContent = `${num}. Activity Date`;
                }
            });
            // Update the visible count and keep the hidden Django field in sync so autosave notices the change
            const newCount = String(rows.length);
            const currentCount = numActivitiesInput.value;
            if (currentCount !== newCount) {
                isSyncingActivitiesCount = true;
                numActivitiesInput.value = newCount;
                isSyncingActivitiesCount = false;
            }
            if (djangoNumActivitiesField && djangoNumActivitiesField.value !== newCount) {
                djangoNumActivitiesField.value = newCount;
                try {
                    djangoNumActivitiesField.dispatchEvent(new Event('change', { bubbles: true }));
                } catch (e) { /* noop */ }
            }
            if (window.AutosaveManager && window.AutosaveManager.reinitialize) {
                // Reinitialize so new rows are tracked by the autosave manager
                window.AutosaveManager.reinitialize();
                // Persist current values immediately so activity fields are saved
                if (window.AutosaveManager.autosaveDraft) {
                    window.AutosaveManager.autosaveDraft().catch(() => {});
                }
            }
        }

        function render(count) {
            if (!container) return;
            container.innerHTML = '';
            if (!isNaN(count) && count > 0) {
                let html = '';
                for (let i = 1; i <= Math.min(count, 50); i++) {
                    html += `
                        <div class="activity-row">
                            <div class="input-group">
                                <label for="activity_name_${i}">${i}. Activity Name</label>
                                <input type="text" id="activity_name_${i}" name="activity_name_${i}" class="proposal-input" required>
                            </div>
                            <div class="input-group">
                                <label for="activity_date_${i}">${i}. Activity Date</label>
                                <input type="date" id="activity_date_${i}" name="activity_date_${i}" class="proposal-input" required>
                            </div>
                            <button type="button" class="remove-activity btn btn-sm btn-outline-danger">×</button>
                        </div>`;
                }
                container.innerHTML = html;
                enhanceProposalInputs();
                if (activitySeeds && activitySeeds.length) {
                    activitySeeds.slice(0, count).forEach((act, idx) => {
                        const index = idx + 1;
                        $(`#activity_name_${index}`).val(act.name);
                        $(`#activity_date_${index}`).val(act.date);
                    });
                } else if (window.AutosaveManager && typeof window.AutosaveManager.getSavedDraft === 'function') {
                    // Prefill from local draft when server hasn't provided activities yet
                    const draft = window.AutosaveManager.getSavedDraft() || {};
                    for (let i = 1; i <= count; i++) {
                        const n = draft[`activity_name_${i}`] || '';
                        const d = draft[`activity_date_${i}`] || '';
                        if (n) {
                            const el = document.getElementById(`activity_name_${i}`);
                            if (el) { el.value = n; el.dispatchEvent(new Event('change', { bubbles: true })); }
                        }
                        if (d) {
                            const el = document.getElementById(`activity_date_${i}`);
                            if (el) { el.value = d; el.dispatchEvent(new Event('change', { bubbles: true })); }
                        }
                    }
                }
                reindexActivityRows();
            }
        }

        container.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove-activity')) {
                const row = e.target.closest('.activity-row');
                if (row) {
                    row.remove();
                    reindexActivityRows();
                }
            }
        });

        numActivitiesInput.addEventListener('input', () => {
            if (isSyncingActivitiesCount) return;
            const count = parseInt(numActivitiesInput.value, 10);
            render(count);
        });
        numActivitiesInput.dataset.listenerAttached = 'true';
        if (activitySeeds && activitySeeds.length) {
            numActivitiesInput.value = activitySeeds.length;
            render(activitySeeds.length);
        } else {
            // Try draft-backed count if input is empty
            let savedCount = parseInt(numActivitiesInput.value, 10);
            if (!savedCount && window.AutosaveManager && typeof window.AutosaveManager.getSavedDraft === 'function') {
                const draft = window.AutosaveManager.getSavedDraft() || {};
                const indices = Object.keys(draft)
                    .map(k => {
                        const m = k.match(/^activity_(?:name|date)_(\d+)$/);
                        return m ? parseInt(m[1], 10) : 0;
                    })
                    .filter(Boolean);
                const inferred = indices.length ? Math.max(...indices) : 0;
                if (inferred > 0) {
                    savedCount = inferred;
                    numActivitiesInput.value = inferred;
                }
            }
            if (savedCount > 0) render(savedCount);
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
                fetch(`${window.API_FACULTY}?org_id=${orgId}&q=${encodeURIComponent(query)}`, { credentials: 'same-origin' })
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
            // Persist faculty selections immediately so autosave tracks them
            // even if the user doesn't interact with other fields afterwards.
            if (window.AutosaveManager && window.AutosaveManager.autosaveDraft) {
                window.AutosaveManager.autosaveDraft().catch(() => {});
            }
        });

        const initialValues = djangoFacultySelect.val();
        if (initialValues && initialValues.length) {
            const missing = initialValues.filter(v => !tomselect.options[v] || tomselect.options[v].text === v);
            if (missing.length) {
                fetch(`${window.API_FACULTY}?ids=${missing.join(',')}`, { credentials: 'same-origin' })
                    .then(r => r.json())
                    .then(data => {
                        data.forEach(opt => {
                            if (tomselect.options[opt.id]) {
                                tomselect.updateOption(opt.id, opt);
                            } else {
                                tomselect.addOption(opt);
                            }
                        });
                        tomselect.setValue(initialValues, true);
                        tomselect.refreshItems();
                    })
                    .catch(() => {
                        tomselect.setValue(initialValues, true);
                        tomselect.refreshItems();
                    });
            } else {
                tomselect.setValue(initialValues);
            }
        }
    }

    function setupCommitteesTomSelect() {
        const select = $('#committees-collaborations-modern');
        const djangoField = $('#django-basic-info [name="committees_collaborations"]');
        const idsField = $('#django-basic-info [name="committees_collaborations_ids"]');
        const orgSelect = $('#django-basic-info [name="organization"]');
        if (!select.length || !djangoField.length || select[0].tomselect) return;

        let existingNames = djangoField.val()
            ? djangoField.val().split(',').map(s => s.trim()).filter(Boolean)
            : [];
        let existingIds = idsField.length && idsField.val()
            ? idsField.val().split(',').map(s => s.trim()).filter(Boolean)
            : [];

        const initSeen = new Set();
        const initPairs = [];
        existingNames.forEach((name, idx) => {
            const key = name.toLowerCase();
            if (!initSeen.has(key)) {
                initSeen.add(key);
                initPairs.push({ id: existingIds[idx] || name, name });
            }
        });
        existingIds = initPairs.map(p => p.id);
        existingNames = initPairs.map(p => p.name);

        const tom = new TomSelect(select[0], {
            plugins: ['remove_button'],
            valueField: 'id',
            labelField: 'text',
            searchField: 'text',
            create: false,
            load: (query, callback) => {
                if (!query.length) return callback();
                const mainOrg = orgSelect.val();
                fetch(`${window.API_ORGANIZATIONS}?q=${encodeURIComponent(query)}`, { credentials: 'same-origin' })
                    .then(r => r.json())
                    .then(data => {
                        if (mainOrg) {
                            data = data.filter(opt => String(opt.id) !== String(mainOrg));
                        }
                        callback(data);
                    })
                    .catch(() => callback());
            }
        });

        tom.on('option_add', (value, data) => {
            const newText = (data.text || '').toLowerCase();
            if (orgSelect.val() && String(orgSelect.val()) === String(value)) {
                tom.removeOption(value);
                return;
            }
            Object.keys(tom.options).forEach(id => {
                if (id === value) return;
                const opt = tom.options[id];
                if ((opt.text || '').toLowerCase() === newText) {
                    tom.removeOption(value);
                }
            });
        });

        const filterMainOrg = () => {
            const main = orgSelect.val();
            if (!main) return;
            let ids = tom.getValue();
            if (!Array.isArray(ids)) ids = [ids].filter(Boolean);
            const filtered = ids.filter(id => String(id) !== String(main));
            if (filtered.length !== ids.length) {
                tom.setValue(filtered, true);
            }
            tom.removeOption(main);
        };

        orgSelect.off('change.committees').on('change.committees', filterMainOrg);

        tom.on('change', () => {
            filterMainOrg();
            let ids = tom.getValue();
            if (!Array.isArray(ids)) ids = [ids];
            const seen = new Set();
            const uniqueIds = [];
            const uniqueNames = [];
            ids.forEach(id => {
                const name = tom.options[id]?.text || id;
                const key = name.toLowerCase();
                if (!seen.has(key)) {
                    seen.add(key);
                    uniqueIds.push(id);
                    uniqueNames.push(name);
                }
            });
            if (uniqueIds.length !== ids.length) {
                tom.setValue(uniqueIds, true);
            }
            djangoField.val(uniqueNames.join(', ')).trigger('change');
            if (idsField.length) {
                idsField.val(uniqueIds.join(', ')).trigger('change');
            }
            clearFieldError(select);
        });

        if (existingIds.length) {
            const main = orgSelect.val();
            const filteredIds = main ? existingIds.filter(id => String(id) !== String(main)) : existingIds;
            if (filteredIds.length) {
                fetch(`${window.API_ORGANIZATIONS}?ids=${filteredIds.join(',')}`, { credentials: 'same-origin' })
                    .then(r => r.json())
                    .then(data => {
                        data.forEach(opt => tom.addOption(opt));
                        tom.setValue(filteredIds);
                    })
                    .catch(() => {
                        if (existingNames.length) {
                            existingNames.forEach((name, idx) => {
                                const id = filteredIds[idx] || name;
                                tom.addOption({ id, text: name });
                            });
                            tom.setValue(filteredIds.length ? filteredIds : existingNames);
                        }
                    });
            }
        } else if (existingNames.length) {
            const main = orgSelect.val();
            const filteredPairs = existingNames.map((name, idx) => ({ name, id: existingIds[idx] || name }))
                .filter(p => !main || String(p.id) !== String(main));
            filteredPairs.forEach(p => tom.addOption({ id: p.id, text: p.name }));
            const filteredIds = filteredPairs.map(p => p.id);
            const filteredNames = filteredPairs.map(p => p.name);
            if (filteredIds.length) {
                tom.setValue(filteredIds);
            } else if (filteredNames.length) {
                tom.setValue(filteredNames);
            }
        }

        filterMainOrg();
    }

    function setupStudentCoordinatorSelect() {
        const select = $('#student-coordinators-modern');
        const djangoField = $('#django-basic-info [name="student_coordinators"]');
        const orgSelect = $('#django-basic-info [name="organization"]');
        const committeesField = $('#django-basic-info [name="committees_collaborations_ids"]');
        const audienceField = $('#target-audience-modern');
        const list = $('#student-coordinators-list');
        if (!select.length || !djangoField.length) return;

        if (select[0].tomselect) {
            select[0].tomselect.destroy();
        }

        if (audienceField.length) {
            audienceField.off('change.studentCoordinatorSync');
        }

        const getAudienceStudentOptions = (query = '') => {
            if (!audienceField.length) return [];
            const q = query.trim().toLowerCase();
            const storedUsers = Array.isArray(audienceField.data('selectedUsers'))
                ? audienceField.data('selectedUsers')
                : [];
            const seen = new Set();
            return storedUsers.reduce((acc, user) => {
                const identifier = String(user?.id || '');
                const rawName = typeof user?.name === 'string' ? user.name.trim() : '';
                if (!identifier.startsWith('stu-') || !rawName) {
                    return acc;
                }
                const nameLower = rawName.toLowerCase();
                if (q && !nameLower.includes(q)) {
                    return acc;
                }
                if (seen.has(nameLower)) {
                    return acc;
                }
                seen.add(nameLower);
                acc.push({ id: identifier, text: rawName });
                return acc;
            }, []);
        };

        const mergeWithAudienceStudents = (options, extras) => {
            const base = Array.isArray(options) ? options.slice() : [];
            if (!Array.isArray(extras) || !extras.length) {
                return base;
            }
            const seen = new Set();
            base.forEach(item => {
                const key = typeof item?.text === 'string' ? item.text.trim().toLowerCase() : '';
                if (key) {
                    seen.add(key);
                }
            });
            extras.forEach(opt => {
                const key = typeof opt?.text === 'string' ? opt.text.trim().toLowerCase() : '';
                if (!key || seen.has(key)) {
                    return;
                }
                seen.add(key);
                base.push({ ...opt, text: opt.text.trim() });
            });
            return base;
        };

        const tom = new TomSelect(select[0], {
            plugins: ['remove_button'],
            valueField: 'text',
            labelField: 'text',
            searchField: 'text',
            create: false,
            placeholder: 'Type a student name…',
            load: function(query, callback) {
                const fallbackOptions = getAudienceStudentOptions(query);
                const ids = [];
                const main = orgSelect.val();
                if (main) ids.push(main);
                if (committeesField.length && committeesField.val()) {
                    committeesField.val().split(',').map(id => id.trim()).filter(Boolean).forEach(id => ids.push(id));
                }
                const orgParam = ids.length ? `&org_ids=${encodeURIComponent(ids.join(','))}` : '';
                const url = `/suite/api/students/?q=${encodeURIComponent(query)}${orgParam}`;
                fetch(url, { credentials: 'same-origin' })
                    .then(response => response.json())
                    .then(json => {
                        callback(mergeWithAudienceStudents(json, fallbackOptions));
                    })
                    .catch(() => {
                        if (fallbackOptions.length) {
                            callback(fallbackOptions);
                        } else {
                            callback();
                        }
                    });
            },
        });

        const syncAudienceStudents = () => {
            if (!audienceField.length) return;
            const extras = getAudienceStudentOptions();
            if (!extras.length) return;
            const valueKey = tom.settings.valueField || 'value';
            extras.forEach(opt => {
                const optionText = typeof opt?.text === 'string' ? opt.text.trim() : '';
                if (!optionText) return;
                const optionValue = valueKey === 'text'
                    ? optionText
                    : (typeof opt[valueKey] === 'string' ? opt[valueKey] : optionText);
                const lookupKey = valueKey === 'text' ? optionText : optionValue;
                if (!tom.options[lookupKey]) {
                    tom.addOption({ ...opt, text: optionText, [valueKey]: optionValue });
                }
            });
        };

        syncAudienceStudents();

        if (audienceField.length) {
            audienceField.on('change.studentCoordinatorSync', () => {
                syncAudienceStudents();
                tom.refreshOptions(false);
            });
        }

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
            const selected = modal
                .find('input[type=checkbox]:checked')
                .map((_, cb) => cb.value)
                .get();

            // Replace existing content with newly selected outcomes
            const value = selected.join(', ');
            posField.val(value).trigger('input').trigger('change');

            if (djangoPosField.length) {
                djangoPosField.val(value).trigger('input').trigger('change');
            }

            modal.removeClass('show');
        });
    }

    function logAudienceAction(action, extra = {}) {
        const audienceField = $('#target-audience-modern');
        const djangoAudienceField = $('#django-basic-info [name="target_audience"]');
        const classIdsField = $('#target-audience-class-ids');
        console.log(`[Audience] ${action}`, {
            ...extra,
            displayValue: audienceField.length ? audienceField.val() : undefined,
            hiddenValue: djangoAudienceField.length ? djangoAudienceField.val() : undefined,
            classIds: classIdsField.length ? classIdsField.val() : undefined
        });
    }

    function applyTargetAudienceSelection({ selectedStudents = [], selectedFaculty = [], userSelected = [] }) {
        const audienceField = $('#target-audience-modern');
        const classIdsField = $('#target-audience-class-ids');
        const djangoAudienceField = $('#django-basic-info [name="target_audience"]');

        if (!audienceField.length) {
            logAudienceAction('selection-skipped-no-field', {
                selectedStudents: selectedStudents.length,
                selectedFaculty: selectedFaculty.length,
                userSelected: userSelected.length
            });
            return;
        }

        const studentNames = selectedStudents.map(it => it?.name).filter(Boolean);
        const facultyNames = selectedFaculty.map(it => it?.name).filter(Boolean);
        const userNames = userSelected.map(it => it?.name).filter(Boolean);
        const names = studentNames.concat(facultyNames, userNames);
        const displayValue = names.join(', ');

        const buildSummary = (items, limit = 200) => {
            const cleanItems = items.filter(Boolean);
            if (!cleanItems.length) {
                return { summary: '', truncated: false, hiddenCount: 0, displayedCount: 0 };
            }

            const included = [];
            let currentLength = 0;

            for (let i = 0; i < cleanItems.length; i += 1) {
                const name = cleanItems[i];
                const separatorLength = included.length ? 2 : 0;
                const additionLength = separatorLength + name.length;
                if (currentLength + additionLength > limit) {
                    break;
                }
                included.push(name);
                currentLength += additionLength;
            }

            let displayedCount = included.length;
            let hiddenCount = cleanItems.length - displayedCount;
            let summary = included.join(', ');
            let truncated = hiddenCount > 0;

            if (hiddenCount > 0) {
                let base = summary;
                let moreText = base.length ? ` +${hiddenCount} more` : `+${hiddenCount} more`;

                while (included.length && base.length + moreText.length > limit) {
                    included.pop();
                    displayedCount = included.length;
                    hiddenCount = cleanItems.length - displayedCount;
                    base = included.join(', ');
                    moreText = base.length ? ` +${hiddenCount} more` : `+${hiddenCount} more`;
                }

                if (!included.length) {
                    const firstName = cleanItems[0] || '';
                    displayedCount = Math.min(cleanItems.length, firstName ? 1 : 0);
                    hiddenCount = cleanItems.length - displayedCount;
                    const moreSuffix = hiddenCount > 0 ? ` +${hiddenCount} more` : '';
                    const availableForName = Math.max(0, limit - moreSuffix.length);
                    const truncatedFirst = firstName.slice(0, availableForName);

                    if (truncatedFirst) {
                        summary = `${truncatedFirst}${moreSuffix}`;
                        truncated = truncated || truncatedFirst.length < firstName.length || Boolean(moreSuffix);
                    } else if (moreSuffix) {
                        summary = moreSuffix.trim();
                        displayedCount = 0;
                        hiddenCount = cleanItems.length;
                    } else {
                        summary = '';
                        truncated = truncated || firstName.length > limit;
                    }
                } else {
                    base = included.join(', ');
                    hiddenCount = cleanItems.length - included.length;
                    const moreSuffix = hiddenCount > 0 ? ` +${hiddenCount} more` : '';
                    summary = `${base}${moreSuffix}`;
                    displayedCount = included.length;
                }

                if (summary.length > limit) {
                    summary = summary.slice(0, limit);
                }
            }

            hiddenCount = Math.max(cleanItems.length - displayedCount, 0);
            truncated = truncated || summary.length < cleanItems.join(', ').length;

            return { summary, truncated, hiddenCount, displayedCount };
        };

        const { summary, truncated, hiddenCount, displayedCount } = buildSummary(names);

        const visibleValue = summary || displayValue;

        audienceField
            .val(visibleValue)
            .data('selectedStudents', [...selectedStudents])
            .data('selectedFaculty', [...selectedFaculty])
            .data('selectedUsers', [...userSelected])
            .data('fullAudience', displayValue)
            .attr('data-full-audience', displayValue)
            .attr('title', displayValue)
            .trigger('change')
            .trigger('input');

        clearFieldError(audienceField);

        const classIds = selectedStudents
            .filter(it => /^\d+$/.test(String(it?.id ?? '')))
            .map(it => String(it.id));

        if (classIdsField.length) {
            classIdsField
                .val(classIds.join(','))
                .trigger('change')
                .trigger('input');
        }

        if (djangoAudienceField.length) {
            const previous = djangoAudienceField.val();
            if (previous !== summary) {
                djangoAudienceField.val(summary).trigger('change');
            } else {
                djangoAudienceField.trigger('change');
            }
            djangoAudienceField
                .data('fullAudience', displayValue)
                .attr('data-full-audience', displayValue);
        }

        if (truncated && typeof showNotification === 'function') {
            const warningMessage = hiddenCount > 0
                ? `Showing the first ${displayedCount} audience${displayedCount === 1 ? '' : 's'}. +${hiddenCount} more saved for editing.`
                : 'Target audience list shortened for display.';
            showNotification(warningMessage, 'warning');
        }

        logAudienceAction('selection-applied', {
            names,
            summary,
            visibleValue,
            classIds,
            studentCount: selectedStudents.length,
            facultyCount: selectedFaculty.length,
            userCount: userSelected.length,
            truncated,
            hiddenCount,
            displayedCount
        });
    }

    function setupAudienceModal() {
        const audienceField = $('#target-audience-modern');
        const djangoOrgSelect = $('#django-basic-info [name="organization"]');
        const modal = $('#audienceModal');

        if (!audienceField.length || !djangoOrgSelect.length || !modal.length) return;

        audienceField.prop('readonly', true).css('cursor', 'pointer');
        $(document).off('click', '#target-audience-modern').on('click', '#target-audience-modern', openAudienceModal);

        $('#audienceCancel').off('click').on('click', () => modal.removeClass('show'));

        logAudienceAction('setup-modal-listeners', {
            hasAudienceField: audienceField.length > 0,
            hasOrgSelect: djangoOrgSelect.length > 0,
            hasModal: modal.length > 0
        });
    }

    function openAudienceModal() {
        const modal = $('#audienceModal');
        const container = $('#audienceOptions');
        const djangoOrgSelect = $('#django-basic-info [name="organization"]');
        const classIdsField = $('#target-audience-class-ids');
        const audienceField = $('#target-audience-modern');
        const preselected = classIdsField.length && classIdsField.val()
            ? classIdsField.val().split(',').map(s => s.trim()).filter(Boolean)
            : [];
        const storedStudents = audienceField.data('selectedStudents') || [];
        const storedFaculty = audienceField.data('selectedFaculty') || [];
        const storedUsers = audienceField.data('selectedUsers') || [];

        modal.addClass('show');

        let available = [];
        let selected = [];
        let selectedStudents = [...storedStudents];
        let selectedFaculty = [...storedFaculty];
        let currentType = null;
        let userSelected = [...storedUsers];

        logAudienceAction('open-modal', {
            orgId: djangoOrgSelect.val(),
            preselected,
            storedStudentCount: storedStudents.length,
            storedFacultyCount: storedFaculty.length,
            storedUserCount: storedUsers.length
        });

        container.html(`
            <div id="audienceStep1">
                <div class="audience-type-selector">
                    <button type="button" data-type="students">Students</button>
                    <button type="button" data-type="faculty">Faculty</button>
                </div>
                <div class="dual-list" id="audienceGroupList" style="display:none;">
                    <div class="dual-list-column">
                        <input type="text" id="audienceAvailableSearch" placeholder="Search available">
                        <select id="audienceAvailable" multiple></select>
                    </div>
                    <div class="dual-list-controls">
                        <button type="button" id="audienceAddAll">&raquo;</button>
                        <button type="button" id="audienceAdd">&gt;</button>
                        <button type="button" id="audienceRemove">&lt;</button>
                        <button type="button" id="audienceRemoveAll">&laquo;</button>
                    </div>
                    <div class="dual-list-column">
                        <input type="text" id="audienceSelectedSearch" placeholder="Search selected">
                        <select id="audienceSelected" multiple></select>
                    </div>
                </div>
                <button type="button" id="audienceContinue" class="btn-continue" style="display:none;">Continue</button>
            </div>
            <div id="audienceStep2" style="display:none;">
                <div class="dual-list user-list" id="audienceUserList">
                    <div class="dual-list-column">
                        <input type="text" id="userAvailableSearch" placeholder="Search available">
                        <select id="userAvailable" multiple></select>
                    </div>
                    <div class="dual-list-controls">
                        <button type="button" id="userAdd">&gt;</button>
                        <button type="button" id="userRemove">&lt;</button>
                    </div>
                    <div class="dual-list-column">
                        <input type="text" id="userSelectedSearch" placeholder="Search selected">
                        <select id="userSelected" multiple></select>
                    </div>
                </div>
                <div class="audience-custom">
                    <select id="audienceCustomInput" placeholder="Add custom audience"></select>
                </div>
                <button type="button" id="audienceAddSelection" class="btn-continue">Add</button>
                <button type="button" id="audienceBack" class="btn-continue">Back</button>
            </div>
        `);

        const listContainer = container.find('#audienceGroupList');
        const availableSelect = container.find('#audienceAvailable');
        const selectedSelect = container.find('#audienceSelected');
        const userListContainer = container.find('#audienceUserList');
        const userAvailableSelect = container.find('#userAvailable');
        const userSelectedSelect = container.find('#userSelected');
        const step1 = container.find('#audienceStep1');
        const step2 = container.find('#audienceStep2');
        const continueBtn = container.find('#audienceContinue');
        const addBtn = container.find('#audienceAddSelection');
        const backBtn = container.find('#audienceBack');

        let classStudentMap = {};
        let departmentFacultyMap = {};
        let userAvailable = [];

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
            filterOptions($('#audienceSelectedSearch'), selectedSelect);
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
            filterOptions($('#userSelectedSearch'), userSelectedSelect);
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
                    (departmentFacultyMap[dept.id] || []).forEach(f => {
                        if (!userSelected.some(u => u.id === `fac-${f.id}`) &&
                            !userAvailable.some(u => u.id === `fac-${f.id}`)) {
                            userAvailable.push({ id: `fac-${f.id}`, name: f.name });
                        }
                    });
                });
            }
            renderUserLists();
        }

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

        function loadAvailable(term = '') {
            available = [];
            const orgIds = collectOrgIds();
            if (!orgIds.length) {
                availableSelect.html('<option>Select an organization first.</option>');
                return;
            }
            if (currentType === 'students') {
                classStudentMap = {};
                Promise.all(orgIds.map(o =>
                    fetch(`${window.API_CLASSES_BASE}${o.id}/?q=${encodeURIComponent(term)}`, { credentials: 'include' })
                        .then(r => r.json().then(data => ({ org: o, data })))
                ))
                .then(results => {
                    results.forEach(res => {
                        const { org, data } = res;
                        if (data.success && data.classes.length) {
                            data.classes.forEach(cls => {
                                classStudentMap[String(cls.id)] = cls.students || [];
                                const item = { id: String(cls.id), name: `${cls.name} (${org.name})` };
                                if (preselected.includes(String(cls.id)) && !selected.some(it => it.id === String(cls.id))) {
                                    selected.push(item);
                                } else if (!selected.some(it => it.id === String(cls.id))) {
                                    available.push(item);
                                }
                            });
                        }
                    });
                    renderLists();
                })
                .catch(() => {
                    availableSelect.html('<option>Error loading</option>');
                });
            } else if (currentType === 'faculty') {
                departmentFacultyMap = {};
                Promise.all(orgIds.map(o =>
                    fetch(`${window.API_FACULTY}?org_id=${o.id}&q=${encodeURIComponent(term)}`, { credentials: 'include' })
                        .then(r => r.json().then(data => ({ org: o, data })))
                ))
                .then(results => {
                    results.forEach(res => {
                        res.data.forEach(f => {
                            const dept = f.department || 'General';
                            if (!departmentFacultyMap[dept]) departmentFacultyMap[dept] = [];
                            departmentFacultyMap[dept].push({ id: f.id, name: f.name });
                        });
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
            selected = currentType === 'students' ? selectedStudents : selectedFaculty;
            listContainer.show();
            continueBtn.show();
            step2.hide();
            addBtn.hide();
            renderLists();
            loadAvailable('');
        });

        container.on('click', '#audienceAdd', function() {
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

        container.on('click', '#audienceAddAll', function() {
            selected.push(...available);
            available = [];
            renderLists();
        });

        container.on('click', '#audienceRemove', function() {
            const ids = selectedSelect.val() || [];
            ids.forEach(id => {
                const idx = selected.findIndex(it => it.id === id);
                if (idx > -1) {
                    const item = selected[idx];
                    if (!item.id.startsWith('custom-')) {
                        available.push(item);
                    }
                    selected.splice(idx, 1);
                }
            });
            renderLists();
        });

        container.on('click', '#audienceRemoveAll', function() {
            available = available.concat(selected.filter(it => !it.id.startsWith('custom-')));
            selected.length = 0;
            renderLists();
        });

        continueBtn.on('click', function() {
            updateUserLists();
            step1.hide();
            step2.show();
            continueBtn.hide();
            addBtn.show();
        });

        backBtn.on('click', function() {
            step2.hide();
            step1.show();
            continueBtn.show();
            addBtn.hide();
        });

        addBtn.on('click', function() {
            step2.hide();
            step1.show();
            listContainer.hide();
            continueBtn.hide();
            addBtn.hide();
            currentType = null;
        });

        const customTS = new TomSelect('#audienceCustomInput', {
            persist: false,
            create: true,
            onItemAdd(value, text) {
                userSelected.push({ id: `custom-${Date.now()}`, name: text });
                customTS.clear();
                renderUserLists();
            }
        });

        container.on('input', '#audienceAvailableSearch', function() {
            const term = $(this).val().trim();
            if (currentType === 'students') {
                loadAvailable(term);
            } else if (currentType === 'faculty') {
                filterOptions($(this), availableSelect);
            }
        });

        container.on('input', '#audienceSelectedSearch', function() {
            filterOptions($(this), selectedSelect);
        });

        container.on('click', '#userAdd', function() {
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

        container.on('click', '#userRemove', function() {
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

        container.on('input', '#userAvailableSearch', function() {
            const term = $(this).val().toLowerCase();
            userAvailableSelect.find('option').each(function() {
                const txt = $(this).text().toLowerCase();
                $(this).toggle(txt.includes(term));
            });
        });

        container.on('input', '#userSelectedSearch', function() {
            filterOptions($(this), userSelectedSelect);
        });

        container.on('dblclick', '#audienceSelected option', function() {
            const id = $(this).val();
            const idx = selected.findIndex(it => it.id === id);
            if (idx > -1) {
                const newName = prompt('Edit name', selected[idx].name);
                if (newName) {
                    selected[idx].name = newName.trim();
                    renderLists();
                }
            }
        });

        if (selectedStudents.length || preselected.length) {
            container.find('button[data-type="students"]').click();
        } else if (selectedFaculty.length) {
            container.find('button[data-type="faculty"]').click();
        }

        $('#audienceConfirm').off('click').on('click', () => {
            logAudienceAction('confirm-click', {
                selectedStudentCount: selectedStudents.length,
                selectedFacultyCount: selectedFaculty.length,
                userSelectionCount: userSelected.length
            });
            applyTargetAudienceSelection({
                selectedStudents: [...selectedStudents],
                selectedFaculty: [...selectedFaculty],
                userSelected: [...userSelected]
            });
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
        fetch(url, { credentials: 'same-origin' })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    container.empty();
                    const selectedCodes = (posField.val().match(/\b(?:PO|PSO)\d+\b/g) || []);
                    data.pos.forEach((po, idx) => {
                        addOption(container, `PO${idx + 1}`, po.description, selectedCodes);
                    });
                    data.psos.forEach((pso, idx) => {
                        addOption(container, `PSO${idx + 1}`, pso.description, selectedCodes);
                    });
                } else {
                    container.text('No data');
                }
            })
            .catch(() => { container.text('Error loading'); });
    }

    function addOption(container, code, description, selectedCodes) {
        const lbl = $('<label>');
        const cb = $('<input type="checkbox">').val(code);
        if (selectedCodes.includes(code)) cb.prop('checked', true);
        lbl.append(cb).append(` ${code}: ${description}`);
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
                djangoField.val(value);
                if (djangoField[0]) {
                    djangoField[0].dispatchEvent(new Event('input', { bubbles: true }));
                    djangoField[0].dispatchEvent(new Event('change', { bubbles: true }));
                }
                clearFieldError($(this));
            });
            // Sync changes from the hidden Django field back to the visible modern field
            djangoField.on('input change', function() {
                const value = $(this).val();
                if (modernField.val() !== value) {
                    modernField.val(value);
                }
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
            window.SDG_GOALS.forEach((goal, idx) => {
                html += `<label><input type="checkbox" value="${goal.id}"> SDG${idx+1} ${goal.name}</label><br>`;
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

        // Allow manual entry in case the modal fails to open or users type values directly.
        // The typed values are matched against the known SDG goal names and the hidden
        // checkboxes (which are part of the actual Django form) are updated accordingly.
        input.prop('readonly', false).css('cursor', 'text');
        input.off('click').on('click', () => modal.addClass('show'));

        // Sync typed SDG names with the hidden checkbox inputs
        input.on('input', () => {
            const typed = input.val().split(/[,;]+/)
                .map(s => s.trim()).filter(Boolean);
            const selected = window.SDG_GOALS
                .filter(g => typed.some(t => t.toLowerCase() === g.name.toLowerCase()))
                .map(g => String(g.id));
            Object.entries(hiddenMap).forEach(([id, el]) => {
                el.prop('checked', selected.includes(id));
            });
            hidden.first().trigger('change');
        });

        $('#sdgCancel').off('click').on('click', () => modal.removeClass('show'));
        $('#sdgSave').off('click').on('click', () => {
            const selected = container.find('input[type=checkbox]:checked')
                .map((_, cb) => cb.value).get();
            Object.entries(hiddenMap).forEach(([id, el]) => {
                el.prop('checked', selected.includes(id));
            });
            hidden.first().trigger('change');
            const names = window.SDG_GOALS
                .filter(g => selected.includes(String(g.id)))
                .map(g => g.name);
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
                    fetch(`${window.API_ORGANIZATIONS}?q=${encodeURIComponent(query)}&org_type=${encodeURIComponent(label)}`, { credentials: 'same-origin' })
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

    function normalizeActivitiesSeed(raw) {
        if (!raw) return [];
        let items = raw;
        if (typeof raw === 'string') {
            try {
                const trimmed = raw.trim();
                if (!trimmed) {
                    return [];
                }
                items = JSON.parse(trimmed);
            } catch (err) {
                console.warn('Failed to parse activity seed payload', err);
                return [];
            }
        }
        if (!Array.isArray(items)) {
            return [];
        }
        return items
            .map((item) => {
                const name = typeof item?.name === 'string' ? item.name.trim() : '';
                let date = typeof item?.date === 'string' ? item.date.trim() : '';
                if (date && !/^\d{4}-\d{2}-\d{2}$/.test(date)) {
                    const parsed = new Date(date);
                    if (!Number.isNaN(parsed.valueOf())) {
                        const month = String(parsed.getMonth() + 1).padStart(2, '0');
                        const day = String(parsed.getDate()).padStart(2, '0');
                        date = `${parsed.getFullYear()}-${month}-${day}`;
                    }
                }
                return { name, date };
            })
            .filter((item) => item.name || item.date);
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
                        <input type="text" id="academic-year-modern" placeholder="2024-2025" disabled>
                        <input type="hidden" name="academic_year" id="academic-year-hidden">
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
                        <input type="number" id="num-activities-modern" name="num_activities" class="proposal-input" min="1" max="50" placeholder="Enter number of activities">
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
            <div class="form-row full-width">
                <!-- <div id="ai-suggestion-status" class="ai-loading">Generating AI suggestions...</div> -->
            </div>
            <div class="form-row full-width">
                <div class="input-group ai-input">
                    <label for="need-analysis-modern">Need Analysis - Why is this event necessary? *</label>
                    <textarea id="need-analysis-modern" rows="4" required placeholder="Explain why this event is necessary, what gap it fills, and its relevance to the target audience..."></textarea>
                    <button type="button" class="ai-fill-btn" data-target="need-analysis-modern" title="Fill with AI">AI</button>
                    <div class="help-text">Provide a detailed explanation of why this event is important.</div>
                </div>
            </div>

            <div class="form-row full-width">
                <div class="input-group ai-input">
                    <label for="objectives-modern">Objectives - What do you aim to achieve? *</label>
                    <textarea id="objectives-modern" rows="4" required placeholder="• Objective 1: ...&#10;• Objective 2: ...&#10;• Objective 3: ..."></textarea>
                    <button type="button" class="ai-fill-btn" data-target="objectives-modern" title="Fill with AI">AI</button>
                    <div class="help-text">List 3-5 clear, measurable objectives.</div>
                </div>
            </div>

            <div class="form-row full-width">
                <div class="input-group ai-input">
                    <label for="outcomes-modern">Expected Learning Outcomes - What results do you expect? *</label>
                    <textarea id="outcomes-modern" rows="4" required placeholder="What specific results, skills, or benefits will participants gain?"></textarea>
                    <button type="button" class="ai-fill-btn" data-target="outcomes-modern" title="Fill with AI">AI</button>
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
                        <label for="need-analysis-single">Describe the need for this event *</label>
                        <textarea id="need-analysis-single" rows="6" required placeholder="Explain why this event is necessary, what gap it fills, and its relevance to the target audience..."></textarea>
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
                        <label for="objectives-single">List the main objectives *</label>
                        <textarea id="objectives-single" rows="6" required placeholder="• Objective 1: ...&#10;• Objective 2: ...&#10;• Objective 3: ..."></textarea>
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
                        <label for="outcomes-single">Describe expected outcomes *</label>
                        <textarea id="outcomes-single" rows="6" required placeholder="What specific results, skills, or benefits will participants gain?"></textarea>
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
                        <textarea id="schedule-modern" name="flow" hidden></textarea>

                        <div id="schedule-rows" class="schedule-rows"></div>
                        <button type="button" id="add-row-btn" class="btn btn-primary btn-block">Add Row</button>
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

    function addRow(time = '', activity = '') {
        if (!scheduleTableBody) return;
        const row = document.createElement('div');
        row.className = 'schedule-row';
        row.innerHTML = `
            <div class="input-group">
                <label>Date & Time *</label>
                <input type="datetime-local" class="time-input proposal-input" value="${time}">
            </div>
            <div class="input-group">
                <label>Activity *</label>
                <input type="text" class="activity-input proposal-input" value="${activity}">
            </div>
            <button type="button" class="btn-remove-row">Remove</button>
        `;
        row.querySelector('.btn-remove-row').addEventListener('click', () => removeRow(row));
        row.querySelectorAll('input').forEach(input => {
            input.addEventListener('input', () => {
                serializeSchedule();
                $(input).removeClass('has-error');
                $(input).siblings('.error-message').remove();
            });
        });
        scheduleTableBody.appendChild(row);
    }

    function removeRow(row) {
        row.remove();
        serializeSchedule();
    }

    function populateTable() {
        if (!scheduleTableBody || !scheduleHiddenField) return;
        scheduleTableBody.innerHTML = '';
        const initial = (scheduleHiddenField.value || '').trim();
        if (initial) {
            initial.split('\n').forEach(line => {
                const parts = line.split('||');
                const time = (parts[0] || '').trim();
                const activity = (parts[1] || '').trim();
                addRow(time, activity);
            });
        } else {
            addRow();
        }
        serializeSchedule();
    }

    function serializeSchedule() {
        if (!scheduleTableBody || !scheduleHiddenField) return;
        const lines = [];
        scheduleTableBody.querySelectorAll('.schedule-row').forEach(row => {
            const time = row.querySelector('.time-input')?.value.trim() || '';
            const activity = row.querySelector('.activity-input')?.value.trim() || '';
            if (time || activity) {
                lines.push(`${time}||${activity}`);
            }
        });
        scheduleHiddenField.value = lines.length ? lines.join('\n') : '';
        scheduleHiddenField.dispatchEvent(new Event('input', { bubbles: true }));
    }

    function setupScheduleSection() {
        scheduleTableBody = document.getElementById('schedule-rows');
        scheduleHiddenField = document.getElementById('schedule-modern');
        const addRowBtn = document.getElementById('add-row-btn');
        if (!scheduleTableBody || !scheduleHiddenField || !addRowBtn) return;
        addRowBtn.addEventListener('click', () => {
            addRow();
            serializeSchedule();
        });
        addRowBtn.dataset.listenerAttached = 'true';
        scheduleTableBody.dataset.initialized = 'true';
    }

    function getSpeakersForm() {
        return `
            <div class="speakers-section">
                <div id="speakers-list" class="speakers-container"></div>

                <div class="add-speaker-section">
                    <button type="button" id="add-speaker-btn" class="btn-add-speaker">
                        Add Speaker
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

    function serializeSpeakers() {
        speakersHiddenField = speakersHiddenField || document.getElementById('speakers-data');
        if (!speakersHiddenField) return;
        const items = [];
        $('#speakers-list .speaker-form-container').each(function() {
            const form = $(this);
            const record = {
                full_name: cleanFieldValue(form.find("input[id^='speaker_full_name_']").val()),
                designation: cleanFieldValue(form.find("input[id^='speaker_designation_']").val()),
                affiliation: cleanFieldValue(form.find("input[id^='speaker_affiliation_']").val()),
                contact_email: cleanFieldValue(form.find("input[id^='speaker_contact_email_']").val()),
                contact_number: cleanFieldValue(form.find("input[id^='speaker_contact_number_']").val()),
                linkedin_url: cleanFieldValue(form.find("input[id^='speaker_linkedin_url_']").val()),
                detailed_profile: cleanFieldValue(form.find("textarea[id^='speaker_detailed_profile_']").val()),
            };
            const hasAny = Object.values(record).some(val => val !== '');
            if (hasAny) {
                items.push(record);
            }
        });
        writeSerializedField(speakersHiddenField, items);
    }

    function getExpensesForm() {
        return `
            <div class="expenses-section">
                <div id="expense-rows" class="expenses-container"></div>

                <div class="add-expense-section">
                    <button type="button" id="add-expense-btn" class="btn-add-expense">
                        Add Expense
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
        speakersHiddenField = document.getElementById('speakers-data');

        function addSpeakerForm() {
            const html = `
                <div class="speaker-form-container" data-index="${index}">
                    <div class="speaker-form-card">
                        <div class="speaker-form-header">
                            <h3 class="speaker-title">Speaker ${index + 1}</h3>
                            <button type="button" class="btn-remove-speaker remove-speaker-btn" data-index="${index}" title="Remove speaker" aria-label="Remove speaker">
                                <i class="fas fa-times" aria-hidden="true"></i>
                                <span class="sr-only">Remove speaker</span>
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
            const newForm = container.children('.speaker-form-container').last();
            newForm.find('input, textarea').on('input change', () => {
                serializeSpeakers();
            });
            index++;
            if (window.AutosaveManager && window.AutosaveManager.reinitialize) {
                window.AutosaveManager.reinitialize();
            }
            serializeSpeakers();
            return newForm;
        }

        function updateSpeakerHeaders() {
            container.children('.speaker-form-container').each(function(i) {
                const form = $(this);
                form.find('.speaker-title').text(`Speaker ${i + 1}`);
                form.attr('data-index', i);
                form.find('.remove-speaker-btn').attr('data-index', i);

                form.find('[id^="speaker_"]').each(function() {
                    const field = $(this);
                    const id = field.attr('id');
                    if (!id) return;
                    const newId = id.replace(/_(\d+)$/, `_${i}`);
                    field.attr('id', newId);
                    const name = field.attr('name');
                    if (name) {
                        const newName = name.replace(/_(\d+)$/, `_${i}`);
                        field.attr('name', newName);
                    }
                });

                form.find('label[for^="speaker_"]').each(function() {
                    const label = $(this);
                    const f = label.attr('for');
                    if (f) {
                        label.attr('for', f.replace(/_(\d+)$/, `_${i}`));
                    }
                });
            });

            const count = container.children('.speaker-form-container').length;
            index = count;
            if (window.AutosaveManager && window.AutosaveManager.reinitialize) {
                window.AutosaveManager.reinitialize();
            }
            serializeSpeakers();
        }

        function showEmptyState() {
            if (container.children('.speaker-form-container').length === 0) {
                container.html(`
                    <div class="speakers-empty-state">
                        <div class="empty-state-icon"><i class="fa-solid fa-microphone"></i></div>
                        <h4>No speakers added yet</h4>
                        <p>Add speakers who will be presenting at your event</p>
                    </div>
                `);
            } else {
                container.find('.speakers-empty-state').remove();
            }
            serializeSpeakers();
        }

        $('#add-speaker-btn').on('click', function() {
            addSpeakerForm();
            showEmptyState();
        });

        container.on('click', '.remove-speaker-btn', function() {
            const idx = $(this).data('index');
            $(this).closest('.speaker-form-container').remove();
            updateSpeakerHeaders();
            showEmptyState();

            const pageKey = `proposal_draft_${window.USER_ID}_${window.location.pathname}_new`;
            try {
                const saved = JSON.parse(localStorage.getItem(pageKey) || '{}');
                const fields = [
                    'full_name',
                    'designation',
                    'affiliation',
                    'contact_email',
                    'detailed_profile',
                    'contact_number',
                    'linkedin_url',
                    'photo',
                ];
                fields.forEach(f => delete saved[`speaker_${f}_${idx}`]);
                if (Array.isArray(saved.speakers)) {
                    saved.speakers.splice(idx, 1);
                }
                localStorage.setItem(pageKey, JSON.stringify(saved));
            } catch (e) { /* ignore */ }

            if (window.AutosaveManager && window.AutosaveManager.autosaveDraft) {
                window.AutosaveManager.autosaveDraft().catch(() => {});
            } else if (window.autosaveDraft) {
                window.autosaveDraft().catch(() => {});
            }
        });

        container.on('change', "input[id^='speaker_linkedin_url_']", async function() {
            const url = $(this).val().trim();
            if (!url) return;
            try {
                const resp = await fetch(window.API_FETCH_LINKEDIN, {
                    method: 'POST',
                    credentials: 'same-origin',
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

        const initialSpeakers = getStoredSectionData('speakers-data', window.EXISTING_SPEAKERS || []);
        if (initialSpeakers.length) {
            container.empty();
            initialSpeakers.forEach(sp => {
                addSpeakerForm();
                const idx = index - 1;
                $(`#speaker_full_name_${idx}`).val(cleanFieldValue(sp.full_name));
                $(`#speaker_designation_${idx}`).val(cleanFieldValue(sp.designation));
                $(`#speaker_affiliation_${idx}`).val(cleanFieldValue(sp.affiliation));
                $(`#speaker_contact_email_${idx}`).val(cleanFieldValue(sp.contact_email));
                $(`#speaker_contact_number_${idx}`).val(cleanFieldValue(sp.contact_number));
                $(`#speaker_linkedin_url_${idx}`).val(cleanFieldValue(sp.linkedin_url));
                $(`#speaker_detailed_profile_${idx}`).val(cleanFieldValue(sp.detailed_profile));
            });
            showEmptyState();
        } else {
            // attempt to restore speakers from autosaved draft
            let restoredFromDraft = false;
            try {
                const key = `proposal_draft_${window.USER_ID}_${window.location.pathname}_new`;
                const saved = JSON.parse(localStorage.getItem(key) || '{}');
                const grouped = {};
                Object.entries(saved).forEach(([k, v]) => {
                    const m = k.match(/^speaker_(.+)_(\d+)$/);
                    if (!m) return;
                    const field = m[1];
                    const idx = parseInt(m[2], 10);
                    (grouped[idx] ||= {})[field] = v;
                });
                const indices = Object.keys(grouped).map(n => parseInt(n, 10)).sort((a, b) => a - b);
                if (indices.length) {
                    container.empty();
                    indices.forEach((savedIdx, pos) => {
                        addSpeakerForm();
                        const data = grouped[savedIdx];
                        Object.entries(data).forEach(([field, val]) => {
                            const el = $(`#speaker_${field}_${pos}`);
                            if (el.length) {
                                el.val(val);
                            }
                        });
                    });
                    restoredFromDraft = true;
                }
            } catch (e) {
                console.warn('Failed to restore speaker autosave', e);
            }

            if (!restoredFromDraft) {
                container.empty();
                addSpeakerForm();
            }
            showEmptyState();
        }

        const addSpeakerBtnEl = document.getElementById('add-speaker-btn');
        if (addSpeakerBtnEl) {
            addSpeakerBtnEl.dataset.listenerAttached = 'true';
        }
        const containerEl = container.get(0);
        if (containerEl) {
            containerEl.dataset.initialized = 'true';
        }
    }

    function serializeExpenses() {
        expensesHiddenField = expensesHiddenField || document.getElementById('expenses-data');
        if (!expensesHiddenField) return;
        const items = [];
        $('#expense-rows .expense-form-container').each(function() {
            const form = $(this);
            const record = {
                sl_no: cleanFieldValue(form.find("input[id^='expense_sl_no_']").val()),
                particulars: cleanFieldValue(form.find("input[id^='expense_particulars_']").val()),
                amount: cleanFieldValue(form.find("input[id^='expense_amount_']").val()),
            };
            if (Object.values(record).some(val => val !== '')) {
                items.push(record);
            }
        });
        writeSerializedField(expensesHiddenField, items);
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
            const newRow = container.children('.expense-form-container').last();
            newRow.find('input').on('input change', () => {
                serializeExpenses();
            });
            index++;
            if (window.AutosaveManager && window.AutosaveManager.reinitialize) {
                window.AutosaveManager.reinitialize();
            }
            serializeExpenses();
        }

        function updateExpenseHeaders() {
            container.children('.expense-form-container').each(function(i) {
                $(this).find('.expense-title').text(`Expense ${i + 1}`);
                $(this).attr('data-index', i);
                $(this).find('.remove-expense-btn').attr('data-index', i);
            });
            serializeExpenses();
        }

        function showEmptyState() {
            if (container.children('.expense-form-container').length === 0) {
                container.html(`
                    <div class="expenses-empty-state">
                        <div class="empty-state-icon"><i class="fa-solid fa-microphone"></i></div>
                        <h4>No expenses added yet</h4>
                        <p>Add all expense items for your event budget</p>
                    </div>
                `);
            } else {
                container.find('.expenses-empty-state').remove();
            }
            serializeExpenses();
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
            serializeExpenses();
        });

        const initialExpenses = getStoredSectionData('expenses-data', window.EXISTING_EXPENSES || []);
        if (initialExpenses.length) {
            container.empty();
            initialExpenses.forEach(ex => {
                addExpenseRow();
                const idx = index - 1;
                $(`#expense_sl_no_${idx}`).val(cleanFieldValue(ex.sl_no));
                $(`#expense_particulars_${idx}`).val(cleanFieldValue(ex.particulars));
                $(`#expense_amount_${idx}`).val(cleanFieldValue(ex.amount));
            });
            showEmptyState();
        } else {
            showEmptyState();
        }

        expensesHiddenField = document.getElementById('expenses-data');
        const addExpenseBtnEl = document.getElementById('add-expense-btn');
        if (addExpenseBtnEl) {
            addExpenseBtnEl.dataset.listenerAttached = 'true';
        }
        const containerEl = container.get(0);
        if (containerEl) {
            containerEl.dataset.initialized = 'true';
        }
    }

    // ===== INCOME SECTION FUNCTIONALITY =====
    function getIncomeForm() {
        return `
            <div class="income-section">
                <div id="income-rows" class="income-container"></div>

                <div class="add-income-section">
                    <button type="button" id="add-income-btn" class="btn-add-income">
                        Add Income
                    </button>
                    <div class="help-text" style="text-align: center; margin-top: 0.5rem;">
                        Add all income items for your event
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

    function serializeIncome() {
        incomeHiddenField = incomeHiddenField || document.getElementById('income-data');
        if (!incomeHiddenField) return;
        const items = [];
        $('#income-rows .income-form-container').each(function() {
            const form = $(this);
            const record = {
                sl_no: cleanFieldValue(form.find("input[id^='income_sl_no_']").val()),
                particulars: cleanFieldValue(form.find("input[id^='income_particulars_']").val()),
                participants: cleanFieldValue(form.find("input[id^='income_participants_']").val()),
                rate: cleanFieldValue(form.find("input[id^='income_rate_']").val()),
                amount: cleanFieldValue(form.find("input[id^='income_amount_']").val()),
            };
            if (Object.values(record).some(val => val !== '')) {
                items.push(record);
            }
        });
        writeSerializedField(incomeHiddenField, items);
    }

    function setupIncomeSection() {
        const container = $('#income-rows');
        let index = 0;

        function addIncomeRow() {
            const html = `
                <div class="income-form-container" data-index="${index}">
                    <div class="income-form-card">
                        <div class="income-form-header">
                            <h3 class="income-title">Income ${index + 1}</h3>
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
                                    <label for="income_participants_${index}">No. of Participants</label>
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
                    serializeIncome();
                }
            }

            participantsInput.on('input change', calculateAmount);
            rateInput.on('input change', calculateAmount);
            $(`#income_sl_no_${index}, #income_particulars_${index}, #income_amount_${index}`).on('input change', () => {
                serializeIncome();
            });
            amountInput.on('input change', () => serializeIncome());

            index++;
            if (window.AutosaveManager && window.AutosaveManager.reinitialize) {
                window.AutosaveManager.reinitialize();
            }
            serializeIncome();
        }

        function updateIncomeHeaders() {
            container.children('.income-form-container').each(function(i) {
                $(this).find('.income-title').text(`Income ${i + 1}`);
                $(this).attr('data-index', i);
                $(this).find('.remove-income-btn').attr('data-index', i);
            });
            serializeIncome();
        }

        function showEmptyState() {
            if (container.children('.income-form-container').length === 0) {
                container.html(`
                    <div class="income-empty-state">
                        <h4>No income added yet</h4>
                        <p>Add all income items for your event budget</p>
                    </div>
                `);
            } else {
                container.find('.income-empty-state').remove();
            }
            serializeIncome();
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
            serializeIncome();
        });

        // Load existing income data if available
        const initialIncome = getStoredSectionData('income-data', window.EXISTING_INCOME || []);
        if (initialIncome.length) {
            container.empty();
            initialIncome.forEach(inc => {
                addIncomeRow();
                const idx = index - 1;
                $(`#income_sl_no_${idx}`).val(cleanFieldValue(inc.sl_no));
                $(`#income_particulars_${idx}`).val(cleanFieldValue(inc.particulars));
                $(`#income_participants_${idx}`).val(cleanFieldValue(inc.participants));
                $(`#income_rate_${idx}`).val(cleanFieldValue(inc.rate));
                $(`#income_amount_${idx}`).val(cleanFieldValue(inc.amount));
            });
            showEmptyState();
        } else {
            showEmptyState();
        }

        incomeHiddenField = document.getElementById('income-data');
        const addIncomeBtnEl = document.getElementById('add-income-btn');
        if (addIncomeBtnEl) {
            addIncomeBtnEl.dataset.listenerAttached = 'true';
        }
        const containerEl = container.get(0);
        if (containerEl) {
            containerEl.dataset.initialized = 'true';
        }
    }

    // ===== CDL SUPPORT SECTION FUNCTIONALITY =====
    function setupCDLForm() {
        const needsSupport = $('#id_needs_support');
        const cdlSections = $('#cdl-services-container');
        const cdlEmptyState = $('#cdl-empty-state');
        const posterRequired = $('#id_poster_required');
        const posterDetails = $('#poster-details');
        const certificatesRequired = $('#id_certificates_required');
        const certificatesDetails = $('#certificates-details');
        const certificateHelp = $('#id_certificate_help');
        const certificateHelpDetails = $('#certificate-help-details');

        function toggle(el, show) {
            if (el && el.length) {
                el.toggle(show);
            }
        }

        // Set up all the toggle functionality
        if (needsSupport.length) {
            needsSupport.on('change', () => {
                const checked = needsSupport.prop('checked');
                toggle(cdlSections, checked);
                toggle(cdlEmptyState, !checked);
            });
            const initial = needsSupport.prop('checked');
            toggle(cdlSections, initial);
            toggle(cdlEmptyState, !initial);
        }

        if (posterRequired.length) {
            posterRequired.on('change', () => toggle(posterDetails, posterRequired.prop('checked')));
            toggle(posterDetails, posterRequired.prop('checked'));
        }

        if (certificatesRequired.length) {
            certificatesRequired.on('change', () => toggle(certificatesDetails, certificatesRequired.prop('checked')));
            toggle(certificatesDetails, certificatesRequired.prop('checked'));
        }

        if (certificateHelp.length) {
            certificateHelp.on('change', () => toggle(certificateHelpDetails, certificateHelp.prop('checked')));
            toggle(certificateHelpDetails, certificateHelp.prop('checked'));
        }

        // Setup CDL auto-fill functionality
        setupCDLAutoFill();
    }

    function setupCDLAutoFill() {
        const autofillBtn = $('#cdl-autofill-btn');
        
        if (autofillBtn.length) {
            autofillBtn.on('click', function() {
                // CDL Auto-fill test data
                const CDL_AUTO_FILL_DATA = {
                    organization_name: "Student Council",
                    poster_time: "10:00 AM - 4:00 PM",
                    poster_date: "2024-03-15",
                    poster_venue: "Main Auditorium",
                    resource_person_name: "Dr. Jane Smith",
                    resource_person_designation: "Professor & Research Director",
                    poster_event_title: "Innovation Summit 2024",
                    poster_summary: "A comprehensive event focusing on emerging technologies and innovation in education.",
                    poster_design_link: "https://example.com/design-reference",
                    certificate_design_link: "https://example.com/certificate-design",
                    other_services: "Need help with social media graphics and event photography coordination.",
                    blog_content: "This innovation summit brings together students, faculty, and industry experts to explore cutting-edge technologies. Participants will engage in workshops, panel discussions, and networking sessions designed to foster creativity and collaboration in the digital age."
                };

                // Enable CDL support
                const needsSupport = $('#id_needs_support');
                if (needsSupport.length) {
                    needsSupport.prop('checked', true);
                    needsSupport.trigger('change');
                }

                // Enable poster support and certificates after a delay
                setTimeout(() => {
                    const posterRequired = $('#id_poster_required');
                    const certificatesRequired = $('#id_certificates_required');
                    
                    if (posterRequired.length) {
                        posterRequired.prop('checked', true);
                        posterRequired.trigger('change');
                    }

                    if (certificatesRequired.length) {
                        certificatesRequired.prop('checked', true);
                        certificatesRequired.trigger('change');
                    }

                    // Enable certificate help after another delay
                    setTimeout(() => {
                        const certificateHelp = $('#id_certificate_help');
                        if (certificateHelp.length) {
                            certificateHelp.prop('checked', true);
                            certificateHelp.trigger('change');
                        }

                        // Fill in all the form fields
                        setTimeout(() => {
                            Object.entries(CDL_AUTO_FILL_DATA).forEach(([key, value]) => {
                                const field = $(`#id_${key}`);
                                if (field.length) {
                                    field.val(value);
                                }
                            });

                            // Show success notification
                            showNotification('CDL test data filled successfully!', 'success');
                        }, 100);
                    }, 100);
                }, 100);
            });
        }
    }

    // ===== SAVE SECTION FUNCTIONALITY - FULLY PRESERVED =====
    function saveCurrentSection() {
        if (!currentExpandedCard) return;

        if (currentExpandedCard === 'schedule') {
            serializeSchedule();
        }
        if (currentExpandedCard === 'speakers') {
            serializeSpeakers();
        }
        if (currentExpandedCard === 'expenses') {
            serializeExpenses();
        }
        if (currentExpandedCard === 'income') {
            serializeIncome();
        }

        // Always validate before saving
        const sectionIsValid = validateCurrentSection();

        if (!sectionIsValid) {
            logValidationIssues(currentExpandedCard, lastValidationIssues);
            markSectionInProgress(currentExpandedCard);
            showNotification('Section has pending issues. You can continue, but resolve them before final submission.', 'warning');

            const nextSection = getNextSection(currentExpandedCard);
            if (nextSection) {
                const nextLink = $(`.proposal-nav .nav-link[data-section="${nextSection}"]`);
                nextLink.removeClass('disabled');
                setTimeout(() => {
                    openFormPanel(nextSection);
                }, 300);
            }
            return;
        }

        showLoadingOverlay();
        if (window.AutosaveManager && window.AutosaveManager.manualSave) {
            window.AutosaveManager.manualSave()
                .then((data) => {
                    hideLoadingOverlay();
                    const futureErrorKeysMap = {
                        'basic-info': ['activities', 'speakers', 'expenses', 'income'],
                        'why-this-event': ['activities', 'speakers', 'expenses', 'income'],
                        'schedule': ['speakers', 'expenses', 'income'],
                        'speakers': ['expenses', 'income'],
                        'expenses': ['income'],
                        'income': []
                    };
                    const ignoreKeys = futureErrorKeysMap[currentExpandedCard] || [];
                    const relevantErrors = {};
                    if (data && data.errors) {
                        Object.entries(data.errors).forEach(([key, val]) => {
                            const isIgnored = ignoreKeys.some(k => key === k || key.startsWith(k + '.'));
                            if (!isIgnored) {
                                relevantErrors[key] = val;
                            }
                        });
                    }
                    if (Object.keys(relevantErrors).length) {
                        handleAutosaveErrors({errors: relevantErrors});
                        // Do not show a toast here; errors are highlighted inline.
                        return;
                    }

                    // Only mark as complete if validation passed and save succeeded
                    markSectionComplete(currentExpandedCard);
                    showNotification('Saved successfully.', 'success');

                    const nextSection = getNextSection(currentExpandedCard);
                    if (nextSection) {
                        const nextLink = $(`.proposal-nav .nav-link[data-section="${nextSection}"]`);
                        nextLink.removeClass('disabled');
                        const nextUrl = nextLink.data('url');
                        setTimeout(() => {
                            if (nextUrl && nextSection !== 'cdl-support') {
                                window.location.href = nextUrl;
                            } else {
                                openFormPanel(nextSection);
                            }
                        }, 1000);
                    }
                })
                .catch(err => {
                    hideLoadingOverlay();
                    console.error('Autosave failed:', err);
                    const hasFieldErrors = err && err.errors && Object.keys(err.errors).length;
                    if (hasFieldErrors) {
                        handleAutosaveErrors(err);
                    } else {
                        // Errors are shown inline or via the autosave indicator; suppress additional toasts.
                    }
                });
        } else {
            hideLoadingOverlay();
            // For cases without AutosaveManager, still mark complete only after validation
            markSectionComplete(currentExpandedCard);
            showNotification('Saved successfully.', 'success');
        }
    }

    // ===== SECTION NAVIGATION - PRESERVED =====
    function getNextSection(currentSection) {
        const sectionOrder = ['basic-info', 'why-this-event', 'schedule', 'speakers', 'expenses', 'income', 'cdl-support'];
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
                if (!djangoField.length) {
                    djangoField = $(`[name="${baseName}"]`);
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
            '#schedule-modern': 'section_flow',
            'textarea[name="flow"]': 'section_flow'
        };

        Object.entries(editorMap).forEach(([selector, key]) => {
            const el = document.querySelector(selector);
            if (!el) return;

            const saved = localStorage.getItem(key);
            if (saved && !el.value) {
                const normalized = saved === '[]' ? '' : saved;
                el.value = normalized;
                if (saved === '[]') {
                    localStorage.setItem(key, '');
                }
            }

            el.addEventListener('input', () => {
                const val = el.value === '[]' ? '' : el.value;
                localStorage.setItem(key, val);
            });
        });
    }

    function collectBasicInfo() {
        const getVal = (modernSelector, djangoName, options = {}) => {
            const { preferDjango = false } = options;
            const modern = $(modernSelector);
            const djangoField = $(`#django-basic-info [name="${djangoName}"]`);
            const modernVal = modern.length ? modern.val() : '';
            const djangoVal = djangoField.length ? djangoField.val() : '';

            if (preferDjango) {
                return djangoVal || modernVal || '';
            }

            return modernVal || djangoVal || '';
        };
        return {
            title: getVal('#event-title-modern', 'event_title'),
            audience: getVal('#target-audience-modern', 'target_audience', { preferDjango: true }),
            focus: getVal('#event-focus-type-modern', 'event_focus_type'),
            venue: getVal('#venue-modern', 'venue')
        };
    }

    function setupWhyThisEventAI() {
        const randomNeed = [
            'This event addresses current challenges and encourages collaborative problem-solving.',
            'The program fills a gap in our curriculum by offering practical, hands-on experience.',
            'Hosting this session promotes interdisciplinary learning and community engagement.'
        ];
        const randomObjectives = [
            '• Objective 1: Enhance participant skills\n• Objective 2: Foster teamwork\n• Objective 3: Share best practices',
            '• Objective 1: Increase awareness of emerging trends\n• Objective 2: Encourage innovation\n• Objective 3: Build professional networks',
            '• Objective 1: Provide experiential learning\n• Objective 2: Promote research thinking\n• Objective 3: Strengthen leadership qualities'
        ];
        const randomOutcomes = [
            '• Outcome 1: Participants gain practical knowledge\n• Outcome 2: Improved problem-solving abilities\n• Outcome 3: Clear action plans',
            '• Outcome 1: Enhanced collaboration skills\n• Outcome 2: Broader professional connections\n• Outcome 3: Increased motivation for projects',
            '• Outcome 1: Greater confidence in the subject\n• Outcome 2: Awareness of best practices\n• Outcome 3: Defined next steps'
        ];
        $('#form-panel-content')
            .off('click', '.ai-fill-btn')
            .on('click', '.ai-fill-btn', function () {
                const target = $(this).data('target');
                let text = '';
                if (target === 'need-analysis-modern') {
                    text = randomNeed[Math.floor(Math.random() * randomNeed.length)];
                } else if (target === 'objectives-modern') {
                    text = randomObjectives[Math.floor(Math.random() * randomObjectives.length)];
                } else if (target === 'outcomes-modern') {
                    text = randomOutcomes[Math.floor(Math.random() * randomOutcomes.length)];
                }
                const el = document.getElementById(target);
                if (el) {
                    el.value = text;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                }
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

    async function loadAndFillSection(section) {
        if (!SECTION_AUTOFILL_ORDER.includes(section)) {
            return;
        }

        if (currentExpandedCard !== section) {
            activateSection(section);
            await delay(450);
        } else {
            await delay(200);
        }

        await autofillTestData(section);
        await delay(300);
    }

    async function fetchOrganizationOption(name, typeLabel = '') {
        if (!name || !window.API_ORGANIZATIONS) return null;
        const params = new URLSearchParams({ q: name });
        if (typeLabel) {
            params.append('org_type', typeLabel);
        }
        const data = await safeFetchJson(`${window.API_ORGANIZATIONS}?${params.toString()}`);
        if (!Array.isArray(data) || !data.length) return null;
        const lower = name.toLowerCase().trim();
        return data.find(opt => (opt.text || '').toLowerCase().trim() === lower) || data[0] || null;
    }

    async function ensureOrganizationSelection() {
        const orgTypeTom = $('#org-type-modern-input')[0]?.tomselect;
        if (orgTypeTom) {
            let desiredValue = findTomSelectOptionValue(orgTypeTom, 'Department');
            if (!desiredValue) {
                const values = Object.keys(orgTypeTom.options || {});
                desiredValue = values.length ? values[0] : null;
            }
            if (desiredValue) {
                orgTypeTom.setValue(desiredValue);
            }
        }

        let orgTom = null;
        try {
            orgTom = await waitForTomSelect('#org-modern-select', { timeout: 5000, interval: 100 });
        } catch (err) {
            orgTom = null;
        }

        let primaryOrgOption = null;
        try {
            primaryOrgOption = await fetchOrganizationOption('Data Science', 'Department');
        } catch (err) {
            primaryOrgOption = null;
        }
        const primaryId = primaryOrgOption ? String(primaryOrgOption.id) : 'data-science';
        const primaryText = primaryOrgOption?.text || 'Data Science';

        if (orgTom) {
            if (!orgTom.options[primaryId]) {
                orgTom.addOption({ id: primaryId, text: primaryText });
            } else if (primaryOrgOption?.text) {
                orgTom.updateOption(primaryId, { id: primaryId, text: primaryOrgOption.text });
            }
            orgTom.setValue(primaryId);
        } else {
            const orgField = $('#django-basic-info [name="organization"]');
            if (orgField.length) {
                orgField.val(primaryId).trigger('change');
            }
        }

        const committeeTom = $('#committees-collaborations-modern')[0]?.tomselect;
        let committeeOption = null;
        try {
            committeeOption = await fetchOrganizationOption('Computer Science');
        } catch (err) {
            committeeOption = null;
        }
        const committeeId = committeeOption ? String(committeeOption.id) : 'computer-science';
        const committeeText = committeeOption?.text || 'Computer Science';
        if (committeeTom) {
            if (!committeeTom.options[committeeId]) {
                committeeTom.addOption({ id: committeeId, text: committeeText });
            }
            const currentValues = new Set(committeeTom.getValue());
            if (!currentValues.has(committeeId)) {
                committeeTom.addItem(committeeId);
            }
        } else {
            const namesField = $('#django-basic-info [name="committees_collaborations"]');
            if (namesField.length) {
                const names = new Set((namesField.val() || '').split(',').map(s => s.trim()).filter(Boolean));
                names.add(committeeText);
                namesField.val(Array.from(names).join(', ')).trigger('change');
            }
            const idsField = $('#committees-collaborations-ids');
            if (idsField.length) {
                const ids = new Set((idsField.val() || '').split(',').map(s => s.trim()).filter(Boolean));
                ids.add(committeeId);
                idsField.val(Array.from(ids).join(',')).trigger('change');
            }
        }

        const primaryOrgId = $('#django-basic-info [name="organization"]').val() || primaryId;
        const primaryOrgName = orgTom?.options?.[primaryOrgId]?.text || primaryText;
        const committeeIds = committeeTom
            ? committeeTom.getValue()
            : (($('#committees-collaborations-ids').val() || '').split(',').map(s => s.trim()).filter(Boolean));
        const committeeNames = committeeTom
            ? committeeIds.map(id => committeeTom.options[id]?.text || committeeText)
            : (($('#django-basic-info [name="committees_collaborations"]').val() || '').split(',').map(s => s.trim()).filter(Boolean));

        return { primaryOrgId, primaryOrgName, committeeIds, committeeNames };
    }

    async function autofillTargetAudienceFromBackend(orgMeta) {
        if (!orgMeta) return;
        const { primaryOrgId, primaryOrgName, committeeIds = [], committeeNames = [] } = orgMeta;
        const orgInfos = [];
        if (primaryOrgId) {
            orgInfos.push({ id: primaryOrgId, name: primaryOrgName || 'Data Science' });
        }
        committeeIds.forEach((id, idx) => {
            if (!id) return;
            orgInfos.push({ id, name: committeeNames[idx] || committeeNames[0] || 'Computer Science' });
        });
        if (!orgInfos.length) return;

        const selectedStudents = [];
        const userSelected = [];
        for (const org of orgInfos) {
            const orgId = String(org.id || '').trim();
            if (!/^[0-9]+$/.test(orgId)) {
                continue;
            }
            const url = `${window.API_CLASSES_BASE}${orgId}/`;
            const data = await safeFetchJson(url);
            if (data?.success && Array.isArray(data.classes)) {
                data.classes.forEach(cls => {
                    const classId = String(cls.id);
                    selectedStudents.push({ id: classId, name: `${cls.name} (${org.name})` });
                    (cls.students || []).forEach(student => {
                        if (student?.id && student?.name) {
                            userSelected.push({ id: `stu-${student.id}`, name: student.name });
                        }
                    });
                });
            }
        }

        const dedupe = (items) => {
            const seen = new Set();
            return items.filter(item => {
                const key = `${item.id}|${item.name}`;
                if (seen.has(key)) return false;
                seen.add(key);
                return true;
            });
        };

        if (!selectedStudents.length) {
            const fallback = orgInfos
                .map((info, idx) => ({ id: `org-${idx + 1}`, name: info.name }))
                .filter(item => item.name);
            if (fallback.length) {
                applyTargetAudienceSelection({ selectedStudents: fallback, selectedFaculty: [], userSelected: [] });
            }
            return;
        }

        applyTargetAudienceSelection({
            selectedStudents: dedupe(selectedStudents),
            selectedFaculty: [],
            userSelected: dedupe(userSelected)
        });
    }

    async function selectFacultyInchargeByEmail(email) {
        if (!email) return;
        const facultyTom = $('#faculty-select')[0]?.tomselect;
        if (!facultyTom) return;

        let orgId = $('#django-basic-info [name="organization"]').val();
        if (!orgId) {
            try {
                await waitForCondition(() => $('#django-basic-info [name="organization"]').val(), { timeout: 3000, interval: 150 });
                orgId = $('#django-basic-info [name="organization"]').val();
            } catch (err) {
                orgId = $('#django-basic-info [name="organization"]').val();
            }
        }

        let option = null;
        if (orgId && /^[0-9]+$/.test(String(orgId))) {
            const url = `${window.API_FACULTY}?org_id=${orgId}&q=${encodeURIComponent(email)}`;
            const results = await safeFetchJson(url);
            if (Array.isArray(results) && results.length) {
                const lowerEmail = email.toLowerCase();
                const preferred = results.find(item => (item.text || '').toLowerCase().includes(lowerEmail) || (item.name || '').toLowerCase().includes('alen'));
                const selected = preferred || results[0];
                option = { id: String(selected.id), text: selected.text || `${selected.name} (${email})` };
            }
        }

        if (!option) {
            option = { id: email, text: `Alen Jinmgi (${email})` };
        }

        if (!facultyTom.options[option.id]) {
            facultyTom.addOption(option);
        } else {
            facultyTom.updateOption(option.id, option);
        }
        facultyTom.clear();
        facultyTom.addItem(option.id);
    }

    async function selectStudentCoordinatorByName(name) {
        if (!name) return;
        let tom = null;
        try {
            tom = await waitForTomSelect('#student-coordinators-modern', { timeout: 2000, interval: 100 });
        } catch (err) {
            tom = $('#student-coordinators-modern')[0]?.tomselect || null;
        }

        const selectEl = document.getElementById('student-coordinators-modern');
        if (!tom && !selectEl) return;

        const trimmedName = String(name).trim();
        if (!trimmedName) return;

        if (tom) {
            const optionId = `autofill-${trimmedName.toLowerCase().replace(/[^a-z0-9]+/g, '-') || 'student'}`;
            const valueKey = tom.settings.valueField || 'value';
            const optionValue = valueKey === 'text' ? trimmedName : optionId;
            if (!tom.options[optionValue]) {
                tom.addOption({ id: optionId, text: trimmedName, [valueKey]: optionValue });
            }
            const current = tom.getValue();
            const values = Array.isArray(current) ? current : (current ? [current] : []);
            if (!values.includes(optionValue)) {
                tom.addItem(optionValue);
            }
            tom.refreshOptions(false);
        } else {
            const existingOption = Array.from(selectEl.options || []).find(opt => opt.value === trimmedName || opt.text === trimmedName);
            if (!existingOption) {
                const option = new Option(trimmedName, trimmedName, true, true);
                selectEl.appendChild(option);
            } else {
                existingOption.selected = true;
            }
            try {
                selectEl.dispatchEvent(new Event('change', { bubbles: true }));
            } catch (e) { /* noop */ }
        }
    }

    async function fillActivityPlan(today) {
        const plan = AUTO_FILL_DATA.activityPlan || [];
        if (!plan.length) return;
        const numInput = document.getElementById('num-activities-modern');
        if (!numInput) return;

        try {
            await waitForCondition(() => numInput.dataset.listenerAttached === 'true', { timeout: 2000, interval: 75 });
        } catch (err) { /* continue even if listener flag not found */ }

        setFieldValue(numInput, String(plan.length));
        try {
            numInput.dispatchEvent(new Event('input', { bubbles: true }));
        } catch (e) { /* noop */ }

        try {
            await waitForCondition(() => {
                return plan.every((_, idx) => document.getElementById(`activity_name_${idx + 1}`));
            }, { timeout: 2000, interval: 75 });
        } catch (err) {
            // If rows failed to render in time, continue and attempt to fill whatever exists
        }

        plan.forEach((activity, idx) => {
            const index = idx + 1;
            setFieldValueById(`activity_name_${index}`, activity.name);
            const dateId = `activity_date_${index}`;
            const dateEl = document.getElementById(dateId);
            if (dateEl) {
                const dateValue = addDaysToDate(today, activity.daysFromStart || 0);
                setFieldValue(dateEl, dateValue);
            }
        });
    }

    async function fillScheduleSection(today) {
        const rows = AUTO_FILL_DATA.scheduleRows || [];
        if (!rows.length) return;
        const addRowBtn = document.getElementById('add-row-btn');
        if (!addRowBtn) return;

        scheduleTableBody = document.getElementById('schedule-rows');
        scheduleHiddenField = document.getElementById('schedule-modern');
        if (!scheduleTableBody) return;

        try {
            await waitForCondition(() => addRowBtn.dataset.listenerAttached === 'true' && scheduleTableBody.dataset.initialized === 'true', { timeout: 2000, interval: 75 });
        } catch (err) { /* proceed regardless */ }

        scheduleTableBody.innerHTML = '';
        rows.forEach(() => addRowBtn.click());

        try {
            await waitForCondition(() => {
                return scheduleTableBody.querySelectorAll('.schedule-row').length >= rows.length;
            }, { timeout: 2000, interval: 75 });
        } catch (err) {
            // proceed even if rows did not fully render in allotted time
        }

        const scheduleRows = scheduleTableBody.querySelectorAll('.schedule-row');
        rows.forEach((row, idx) => {
            const rowEl = scheduleRows[idx];
            if (!rowEl) return;
            const timeInput = rowEl.querySelector('.time-input');
            const activityInput = rowEl.querySelector('.activity-input');
            if (timeInput) {
                setFieldValue(timeInput, `${today}T${row.time}`);
            }
            if (activityInput) {
                setFieldValue(activityInput, row.activity);
            }
        });
        serializeSchedule();
    }

    async function fillSpeakersSection() {
        const profiles = AUTO_FILL_DATA.speakerProfiles || [];
        if (!profiles.length) return;
        const addBtn = document.getElementById('add-speaker-btn');
        if (!addBtn) return;

        try {
            await waitForCondition(() => addBtn.dataset.listenerAttached === 'true', { timeout: 2000, interval: 75 });
        } catch (err) { /* continue even if listener not flagged */ }

        const container = document.getElementById('speakers-list');
        const existing = container ? container.querySelectorAll('.speaker-form-container').length : 0;
        for (let i = existing; i < profiles.length; i += 1) {
            addBtn.click();
        }

        try {
            await waitForCondition(() => document.getElementById('speaker_full_name_0'), { timeout: 2000, interval: 100 });
        } catch (err) { /* ignore timeout */ }

        profiles.forEach((profile, idx) => {
            setFieldValueById(`speaker_full_name_${idx}`, profile.full_name);
            setFieldValueById(`speaker_designation_${idx}`, profile.designation);
            setFieldValueById(`speaker_affiliation_${idx}`, profile.affiliation);
            setFieldValueById(`speaker_contact_email_${idx}`, profile.email);
            setFieldValueById(`speaker_contact_number_${idx}`, profile.phone);
            setFieldValueById(`speaker_linkedin_url_${idx}`, profile.linkedin);
            setFieldValueById(`speaker_detailed_profile_${idx}`, profile.bio);
        });

        serializeSpeakers();
    }

    async function fillExpensesSection() {
        const expenses = AUTO_FILL_DATA.expenseRows || [];
        if (!expenses.length) return;
        const addBtn = document.getElementById('add-expense-btn');
        if (!addBtn) return;

        try {
            await waitForCondition(() => addBtn.dataset.listenerAttached === 'true', { timeout: 2000, interval: 75 });
        } catch (err) { /* continue even if listener flag missing */ }

        const container = $('#expense-rows');
        const existing = container.children('.expense-form-container').length;
        for (let i = existing; i < expenses.length; i += 1) {
            addBtn.click();
        }

        try {
            await waitForCondition(() => {
                return expenses.every((_, idx) => document.getElementById(`expense_particulars_${idx}`));
            }, { timeout: 2000, interval: 75 });
        } catch (err) {
            // continue with whatever rows rendered
        }

        expenses.forEach((expense, idx) => {
            setFieldValueById(`expense_sl_no_${idx}`, expense.sl);
            setFieldValueById(`expense_particulars_${idx}`, expense.particulars);
            setFieldValueById(`expense_amount_${idx}`, expense.amount);
        });

        serializeExpenses();
    }

    async function fillIncomeSection() {
        const incomes = AUTO_FILL_DATA.incomeRows || [];
        if (!incomes.length) return;
        const addBtn = document.getElementById('add-income-btn');
        if (!addBtn) return;

        try {
            await waitForCondition(() => addBtn.dataset.listenerAttached === 'true', { timeout: 2000, interval: 75 });
        } catch (err) { /* proceed regardless */ }

        const container = $('#income-rows');
        const existing = container.children('.income-form-container').length;
        for (let i = existing; i < incomes.length; i += 1) {
            addBtn.click();
        }

        try {
            await waitForCondition(() => {
                return incomes.every((_, idx) => document.getElementById(`income_particulars_${idx}`));
            }, { timeout: 2000, interval: 75 });
        } catch (err) {
            // proceed regardless
        }

        incomes.forEach((income, idx) => {
            setFieldValueById(`income_sl_no_${idx}`, income.sl);
            setFieldValueById(`income_particulars_${idx}`, income.particulars);
            setFieldValueById(`income_participants_${idx}`, income.participants);
            setFieldValueById(`income_rate_${idx}`, income.rate);
            setFieldValueById(`income_amount_${idx}`, income.amount);
        });

        serializeIncome();
    }

    function selectRandomSdgGoal() {
        const sdgInput = document.getElementById('sdg-goals-modern');
        const goals = Array.isArray(window.SDG_GOALS) ? window.SDG_GOALS : [];
        if (!sdgInput || !goals.length) return;
        const goal = goals[Math.floor(Math.random() * goals.length)];
        setFieldValue(sdgInput, goal.name);

        const hidden = $('#django-basic-info [name="sdg_goals"]');
        if (hidden.length) {
            hidden.each(function() {
                const checkbox = $(this);
                checkbox.prop('checked', checkbox.val() === String(goal.id));
            });
            hidden.first().trigger('change');
        }

        $('#sdgOptions input[type=checkbox]').each(function() {
            const cb = $(this);
            cb.prop('checked', cb.val() === String(goal.id));
        });
    }

    async function autofillAllSections() {
        if (isAutofilling) return;
        isAutofilling = true;

        const autofillBtn = $('#autofill-btn');
        const originalLabel = autofillBtn.text();
        autofillBtn.prop('disabled', true).text('Auto-Filling...');

        const originalSection = currentExpandedCard || 'basic-info';

        try {
            for (const section of SECTION_AUTOFILL_ORDER) {
                await loadAndFillSection(section);
            }
        } finally {
            if (originalSection && originalSection !== currentExpandedCard) {
                activateSection(originalSection);
                await delay(350);
            }
            autofillBtn.prop('disabled', false).text(originalLabel);
            isAutofilling = false;
        }
    }

    async function autofillTestData(section) {
        const today = new Date().toISOString().split('T')[0];

        if (section === 'basic-info') {
            const orgMeta = await ensureOrganizationSelection().catch(err => {
                console.warn('autofill: failed to ensure organization selection', err);
                return null;
            });

            const now = new Date();
            const academicYear = now.getMonth() >= 6
                ? `${now.getFullYear()}-${now.getFullYear() + 1}`
                : `${now.getFullYear() - 1}-${now.getFullYear()}`;

            const fields = {
                'event-title-modern': getRandom(AUTO_FILL_DATA.titles),
                'venue-modern': getRandom(AUTO_FILL_DATA.venues),
                'event-focus-type-modern': getRandom(AUTO_FILL_DATA.focusTypes),
                'event-start-date': today,
                'event-end-date': addDaysToDate(today, 1),
                'academic-year-modern': academicYear,
                'pos-pso-modern': 'PO1, PSO2 & PSO3'
            };

            Object.entries(fields).forEach(([id, value]) => setFieldValueById(id, value));

            const djangoAcademicYear = $('#django-basic-info [name="academic_year"]');
            if (djangoAcademicYear.length) {
                djangoAcademicYear.val(academicYear).trigger('change');
            }

            selectRandomSdgGoal();
            await fillActivityPlan(today);

            await autofillTargetAudienceFromBackend(orgMeta);
            await selectFacultyInchargeByEmail('alenjinmgi@gmail.com');
            await selectStudentCoordinatorByName('Alen Jin Shibu');

            const sc = document.getElementById('student-coordinators-modern');
            const scTom = sc?.tomselect;
            const currentCoordinators = scTom ? scTom.getValue() : Array.from(sc?.selectedOptions || []).map(opt => opt.value);
            if (sc && (!currentCoordinators || (Array.isArray(currentCoordinators) && !currentCoordinators.length))) {
                if (!scTom && !sc.options.length) {
                    sc.appendChild(new Option('Data Science Student Lead', '1', true, true));
                    sc.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        }

        if (section === 'why-this-event') {
            setFieldValueById('need-analysis-modern', getRandom(AUTO_FILL_DATA.need));
            setFieldValueById('objectives-modern', getRandom(AUTO_FILL_DATA.objectives));
            setFieldValueById('outcomes-modern', getRandom(AUTO_FILL_DATA.outcomes));
        }

        if (section === 'schedule') {
            await fillScheduleSection(today);
        }

        if (section === 'speakers') {
            await fillSpeakersSection();
        }

        if (section === 'expenses') {
            await fillExpensesSection();
        }

        if (section === 'income') {
            await fillIncomeSection();
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
                // Add visual feedback for newly unlocked section
                nextNavLink.addClass('animate-bounce');
                setTimeout(() => nextNavLink.removeClass('animate-bounce'), 1000);
                console.log('unlockNextSection: nextNavLink unlocked', nextNavLink[0]);
                
                // Notification suppressed: avoid multiple toasts; only show explicit "Saved successfully." on section save.
            } else {
                console.log('unlockNextSection: nextNavLink already enabled', nextNavLink[0]);
            }
        } else {
            // This is expected for the last section - no more sections to unlock
            if (nextOrder <= 7) {
                console.warn('unlockNextSection: nextNavLink not found for order', nextOrder);
            }
        }
    }

    function updateSubmitButton() {
        const btn = $('#submit-proposal-btn');
        if (!btn.length) return;
        const requiredSections = Object.keys(sectionProgress).filter(section => !optionalSections.includes(section));
        const completedSections = requiredSections.filter(section => sectionProgress[section] === true).length;

        if (completedSections === requiredSections.length) {
            btn.prop('disabled', false);
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
        let isValid = true;
        if (!scheduleTableBody) return false;

        scheduleTableBody.querySelectorAll('tr').forEach(tr => {
            const timeInput = $(tr).find('.time-input');
            const activityInput = $(tr).find('.activity-input');
            const time = timeInput.val().trim();
            const activity = activityInput.val().trim();

            if (!time && !activity) {
                return; // Skip completely empty rows
            }

            if (!time) {
                showScheduleError(timeInput, 'Date & time required');
                isValid = false;
            } else if (isNaN(Date.parse(time))) {
                showScheduleError(timeInput, 'Invalid date & time');
                isValid = false;
            }

            if (!activity) {
                showScheduleError(activityInput, 'Activity required');
                isValid = false;
            }
        });

        if (!isValid) {
            const scheduleField = $('#schedule-modern');
            scheduleField.addClass('animate-shake');
            setTimeout(() => scheduleField.removeClass('animate-shake'), 600);
        }

        return isValid;
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
            const field = $(selector).filter(':visible').first();
            if (!field.length) return;
            const id = field.attr('id');

            if (id) {
                if (window.CKEDITOR && CKEDITOR.instances && CKEDITOR.instances[id]) {
                    CKEDITOR.instances[id].updateElement();
                    field.trigger('input').trigger('change');
                } else if (window.ClassicEditor && window._editors && window._editors[id]) {
                    field.val(window._editors[id].getData());
                    field.trigger('input').trigger('change');
                } else if (window.tinymce && tinymce.get(id)) {
                    field.val(tinymce.get(id).getContent());
                    field.trigger('input').trigger('change');
                } else if (window.Quill && window._quills && window._quills[id]) {
                    field.val(window._quills[id].root.innerHTML);
                    field.trigger('input').trigger('change');
                }
                const baseName = selector.replace('#', '').replace('-modern', '').replace(/-/g, '_');
                $(`textarea[name="${baseName}"]`).val(field.val());
            }
            if (!field.val().trim()) {
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

        // Check org type (TomSelect input)
        const orgTypeInput = $('#org-type-modern-input');
        const orgTypeValue = orgTypeInput[0]?.tomselect?.getValue();
        console.log('validateBasicInfo: orgType', {
            id: orgTypeInput.attr('id'),
            name: orgTypeInput.attr('name'),
            value: orgTypeValue
        });
        if (!orgTypeValue) {
            showFieldError(orgTypeInput.parent(), 'Organization type is required');
            isValid = false;
        }

        // Check organization if org type is selected
        if (orgTypeValue) {
            // Try select (TomSelect)
            let orgField = $(`.org-specific-field:visible select`);
            if (orgField.length) {
                console.log('validateBasicInfo: orgField (select)', {
                    id: orgField.attr('id'),
                    name: orgField.attr('name'),
                    value: orgField.val(),
                    tomSelectValue: orgField[0]?.tomselect?.getValue()
                });
                if (!orgField[0].tomselect || !orgField[0].tomselect.getValue()) {
                    showFieldError(orgField.parent(), 'Organization selection is required');
                    isValid = false;
                }
            } else {
                // Fallback: check for input field
                orgField = $(`.org-specific-field:visible input`);
                if (orgField.length) {
                    console.log('validateBasicInfo: orgField (input)', {
                        id: orgField.attr('id'),
                        name: orgField.attr('name'),
                        value: orgField.val()
                    });
                    if (!orgField.val() || !orgField.val().trim()) {
                        showFieldError(orgField.parent(), 'Organization selection is required');
                        isValid = false;
                    }
                }
            }
        }

        const targetAudienceField = $('#target-audience-modern');
        const hiddenTargetAudienceField = $('#django-basic-info [name="target_audience"]');
        const hiddenTargetAudienceValue = hiddenTargetAudienceField.length ? hiddenTargetAudienceField.val() : '';
        const selectedStudents = targetAudienceField.length ? targetAudienceField.data('selectedStudents') || [] : [];
        const selectedFaculty = targetAudienceField.length ? targetAudienceField.data('selectedFaculty') || [] : [];
        const selectedUsers = targetAudienceField.length ? targetAudienceField.data('selectedUsers') || [] : [];

        let targetAudienceValue = targetAudienceField.length ? targetAudienceField.val() : '';
        let hasVisibleValue = typeof targetAudienceValue === 'string' && targetAudienceValue.trim().length > 0;
        const hasHiddenValue = typeof hiddenTargetAudienceValue === 'string' && hiddenTargetAudienceValue.trim().length > 0;
        const hasSelectionData = selectedStudents.length > 0 || selectedFaculty.length > 0 || selectedUsers.length > 0;
        const shouldRehydrateVisible =
            targetAudienceField.length && !hasVisibleValue && (hasHiddenValue || hasSelectionData);
        let rehydratedFromHidden = false;

        if (shouldRehydrateVisible && hasHiddenValue) {
            targetAudienceField
                .val(hiddenTargetAudienceValue)
                .trigger('input')
                .trigger('change');
            targetAudienceValue = hiddenTargetAudienceValue;
            hasVisibleValue = true;
            rehydratedFromHidden = true;
        }

        const hasAudience = hasVisibleValue || hasHiddenValue || hasSelectionData;

        logAudienceAction('validate-basic-info', {
            visibleValue: targetAudienceValue,
            hiddenValue: hiddenTargetAudienceValue,
            selectedStudentCount: selectedStudents.length,
            selectedFacultyCount: selectedFaculty.length,
            selectedUserCount: selectedUsers.length,
            hasVisibleValue,
            hasHiddenValue,
            hasSelectionData,
            hasAudience,
            rehydratedFromHidden
        });

        if (targetAudienceField.length) {
            if (!hasAudience) {
                showFieldError(targetAudienceField, 'Target Audience is required');
                isValid = false;
            } else {
                clearFieldError(targetAudienceField);
            }
        }

        $('#form-panel-content input[required], #form-panel-content textarea[required], #form-panel-content select[required]').each(function() {
            const $field = $(this);
            const fieldInfo = {
                id: $field.attr('id'),
                name: $field.attr('name'),
                value: this.tomselect ? this.tomselect.getValue() : $field.val()
            };
            console.log('validateBasicInfo: field', fieldInfo);

            // Skip fields already handled or special cases
            if (
                fieldInfo.id === 'faculty-select' ||
                fieldInfo.id === 'event-focus-type-modern' ||
                fieldInfo.id === 'target-audience-modern' ||
                $field.closest('.org-specific-field').length ||
                (fieldInfo.id && fieldInfo.id.startsWith('org-type'))
            ) return;

            const valueToCheck = this.tomselect ? this.tomselect.getValue() : $field.val();
            const isEmpty =
                valueToCheck === undefined ||
                valueToCheck === null ||
                (Array.isArray(valueToCheck)
                    ? valueToCheck.length === 0
                    : valueToCheck.trim() === '');

            if (isEmpty) {
                const fieldName = $field.closest('.input-group').find('label').text().replace(' *', '');
                showFieldError($field, `${fieldName} is required`);
                isValid = false;
            } else {
                clearFieldError($field);
            }
        });

        // Special check for faculty select (TomSelect)
        const facultyTomSelect = $('#faculty-select')[0]?.tomselect;
        console.log('validateBasicInfo: faculty-select', {
            id: $('#faculty-select').attr('id'),
            name: $('#faculty-select').attr('name'),
            value: facultyTomSelect ? facultyTomSelect.getValue() : $('#faculty-select').val()
        });
        if (facultyTomSelect && facultyTomSelect.getValue().length === 0) {
            showFieldError(facultyTomSelect.$wrapper, 'At least one Faculty Incharge is required.');
            isValid = false;
        }

        return isValid;
    }

    // ===== LOAD EXISTING DATA - PRESERVED =====
    function loadExistingData() {
        // Don't auto-mark sections as complete during initial load
        // Let user manually validate and save each section
        
        // Check if we have a saved proposal ID - if so, load the saved state from server
        if (window.PROPOSAL_ID) {
            // Load actual completion state from server if available
            loadSavedProgressState();
        } else {
            // For new proposals, ensure only basic-info is unlocked initially
            initializeNavigationState();
        }

        updateProgressBar();
    }
    
    function initializeNavigationState() {
        // Reset navigation without enforcing sequential restrictions
        $('.proposal-nav .nav-link').removeClass('disabled completed in-progress');

        // Reset section progress
        Object.keys(sectionProgress).forEach(section => {
            sectionProgress[section] = false;
        });
    }
    
    function loadSavedProgressState() {
        // This would ideally load the actual completion state from the server
        // For now, we'll be conservative and require re-validation
        initializeNavigationState();
    }

    // ===== KEYBOARD SHORTCUTS - PRESERVED =====
    $(document).on('keydown', function(e) {
        if (e.ctrlKey && e.which === 83) { // Ctrl + S
            e.preventDefault();
            if (window.AutosaveManager && window.AutosaveManager.manualSave) {
                window.AutosaveManager.manualSave().catch(() => {});
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
        const sections = Object.keys(sectionProgress).filter(section => !optionalSections.includes(section));
        const completedSections = sections.filter(section => sectionProgress[section] === true).length;
        const totalSections = sections.length;
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
        lastValidationIssues = [];
        $('.has-error').removeClass('has-error');
        $('.animate-shake').removeClass('animate-shake');
        $('.error-message').remove();
    }

    function showFieldError(field, message) {
        if (field && field.length) {
            field.addClass('has-error');
            field.closest('.input-group').addClass('has-error');

            let targetField;
            if (field[0]?.tomselect) {
                targetField = $(field[0].tomselect.input);
            } else if (field.is('input[id], input[name], select[id], select[name], textarea[id], textarea[name]')) {
                targetField = field;
            } else {
                targetField = field
                    .find('input[id], input[name], select[id], select[name], textarea[id], textarea[name]')
                    .first();
            }
            const fieldData = targetField && targetField.length ? {
                id: targetField.attr('id'),
                name: targetField.attr('name'),
                value: targetField[0]?.tomselect
                    ? targetField[0].tomselect.getValue()
                    : targetField.val(),
            } : {};

            lastValidationIssues.push({ message, field: fieldData });
            console.warn(message, fieldData);
            if (!firstErrorField) {
                firstErrorField = field;
            }
        }
    }

    function showScheduleError(field, message) {
        if (!field || !field.length) return;
        field.addClass('has-error');
        const td = field.closest('td');
        if (!td.length) return;
        let err = td.find('.error-message');
        if (!err.length) {
            err = $('<div class="error-message"></div>');
            td.append(err);
        }
        err.text(message);
        const fieldData = {
            id: field.attr('id'),
            name: field.attr('name'),
            value: typeof field.val === 'function' ? field.val() : undefined,
        };
        lastValidationIssues.push({ message, field: fieldData });
        console.warn(message, fieldData);
        if (!firstErrorField) {
            firstErrorField = field;
        }
    }

    function logValidationIssues(sectionName, issues = []) {
        if (!issues.length) return;
        let sectionLabel = sectionName;
        if (sectionName) {
            const navLink = $(`.proposal-nav .nav-link[data-section="${sectionName}"]`).first();
            if (navLink.length) {
                sectionLabel = navLink.text().trim() || sectionName;
            }
        }
        const groupLabel = sectionLabel
            ? `Validation issues in ${sectionLabel}`
            : 'Validation issues';
        console.group(groupLabel);
        issues.forEach((issue, index) => {
            const prefix = `#${index + 1}: ${issue.message}`;
            if (issue.field && Object.keys(issue.field).length) {
                console.warn(prefix, issue.field);
            } else {
                console.warn(prefix);
            }
        });
        console.groupEnd();
    }

    function handleAutosaveErrors(errorData) {
        const errors = (errorData && typeof errorData === 'object') ? (errorData.errors || errorData) : null;
        if (!errors || typeof errors !== 'object') {
            showNotification('Autosave failed. Please try again.', 'error');
            return;
        }
        if (!Object.keys(errors).length) {
            return;
        }

        clearValidationErrors();
        firstErrorField = null;
        const nonFieldMessages = [];

        const mark = (name, message) => {
            const fieldMap = {
                'organization_type': '#org-type-modern-input',
                'organization': '#org-modern-select'
            };
            let field = $(fieldMap[name] || `#${name.replace(/_/g, '-')}-modern`);
            if (!field.length) {
                field = $(`[name="${name}"]`);
                if (field.length && field.attr('type') === 'hidden') {
                    const alt = $(`#${field.attr('id')}-modern`);
                    if (alt.length) field = alt;
                }
            }
            if (field.length) {
                showFieldError(field, message);
                return true;
            }
            nonFieldMessages.push(message);
            return false;
        };

        Object.entries(errors).forEach(([key, val]) => {
            // During autosave, ignore activities errors to avoid warning spam while user types
            if (key === 'activities' && errorData && errorData.context === 'autosave') {
                return;
            }
            if (key === '__all__' || key === 'non_field_errors') {
                if (Array.isArray(val)) {
                    nonFieldMessages.push(...val);
                } else if (val) {
                    nonFieldMessages.push(val);
                }
                return;
            }
            if (Array.isArray(val)) {
                mark(key, val[0]);
            } else if (typeof val === 'object' && val !== null) {
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
            } else if (val) {
                mark(key, val);
            }
        });

        const firstSpeakerField = $('.speaker-form-container .has-error').filter('input, textarea, select').first();
        if (firstSpeakerField.length) {
            firstSpeakerField.closest('.speaker-form-container').addClass('has-error');
        }
        const focusField = firstSpeakerField.length ? firstSpeakerField : firstErrorField;
        if (focusField && focusField.length) {
            // During autosave or background validations, do not show toasts; just highlight fields.
            // Avoid jarring auto-scroll on autosave; only focus silently when not autosave.
            if (!(errorData && errorData.context === 'autosave')) {
                $('html, body').animate({scrollTop: focusField.offset().top - 100}, 500);
                if (focusField[0]?.tomselect) {
                    focusField[0].tomselect.focus();
                } else {
                    focusField.focus();
                }
            }
        } else if (nonFieldMessages.length) {
            // Suppress toasts; rely on inline highlights/messages.
        } else {
            // Suppress generic autosave failure toast here; dedicated autosave indicator handles this.
        }

        if (nonFieldMessages.length) {
            nonFieldMessages.forEach(message => {
                lastValidationIssues.push({ message, field: {} });
            });
        }
        const sectionSlug = errorData?.section || currentExpandedCard;
        logValidationIssues(sectionSlug, lastValidationIssues);
    }

    // ===== ADD ANIMATIONS CSS - PRESERVED =====
    function addAnimationStyles() {
        const animationStyles = `
            <style>
                @keyframes bounce { 0%, 20%, 53%, 80%, 100% { transform: translate3d(0,0,0); } 40%, 43% { transform: translate3d(0,-10px,0); } 70% { transform: translate3d(0,-5px,0); } 90% { transform: translate3d(0,-2px,0); } }
                @keyframes shake { 0%, 100% { transform: translateX(0); } 25% { transform: translateX(-5px); } 75% { transform: translateX(5px); } }
                .animate-bounce { animation: bounce 0.6s ease-in-out; }
                .animate-shake { animation: shake 0.5s ease-in-out; }
                
                .notification { position: fixed; bottom: 20px; right: 20px; background: white; padding: 1rem 1.5rem; border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.15); z-index: 1001; opacity: 0; transform: translateX(100%); transition: all 0.3s ease; max-width: 320px; }
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
    // Use container-level fallback only when AutosaveManager is NOT present to avoid duplicate triggers
    if (!window.AutosaveManager && window.autosaveDraft) {
        // Trigger autosave on form changes
        $('#form-panel-content').on('input change', 'input, textarea, select', debounce(function() {
            const flowField = document.getElementById('schedule-modern') || document.querySelector('textarea[name="flow"]');
            if (flowField && flowField.value.trim() === '[]') {
                flowField.value = '';
                localStorage.setItem('section_flow', '');
            }
            window.autosaveDraft().catch(() => {});
        }, 1000));
    }

    // ===== FORM SUBMISSION HANDLING - PRESERVED =====
    $('#proposal-form').on('submit', function(e) {
        if (document.getElementById('schedule-modern')) {
            serializeSchedule();
        }
        // Before submit, copy any rich text content into hidden fields
        const needAnalysisContent = localStorage.getItem('section_need_analysis') || $('#need-analysis-modern').val() || '';
        const objectivesContent = localStorage.getItem('section_objectives') || $('#objectives-modern').val() || '';
        const outcomesContent = localStorage.getItem('section_outcomes') || $('#outcomes-modern').val() || '';
        let flowContent = localStorage.getItem('section_flow') || $('#schedule-modern').val() || '';
        if (flowContent.trim() === '[]') {
            flowContent = '';
            localStorage.setItem('section_flow', '');
        }

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

        $(document).on('autosave:success', function(e) {
            const detail = e.originalEvent && e.originalEvent.detail;
            if (detail && detail.proposalId) {
                window.PROPOSAL_ID = detail.proposalId;
                updateCdlNavLink(detail.proposalId);
                $('#reset-draft-btn').prop('disabled', false).removeAttr('disabled');
            }
            if (detail && detail.errors) {
                // Suppress dynamic activities warnings during autosave to prevent spam while typing
                const filtered = { ...detail.errors };
                if (filtered.activities) {
                    delete filtered.activities;
                }
                // Highlight inline without toasts; avoid scroll/focus during autosave
                handleAutosaveErrors({ errors: filtered, context: 'autosave' });
            }
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
            // Inline highlights are enough; suppress toasts during autosave errors.
            setTimeout(() => {
                indicator.removeClass('show');
            }, 3000);
        });
    }

    // Initialize autosave indicators
    initializeAutosaveIndicators();

    // Enhance text inputs with improved interactions
    enhanceProposalInputs();

    console.log('Dashboard initialized successfully.');
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

/*async function generateWhyEvent(){
  const status = document.querySelector('#ai-suggestion-status');
  if(status) status.style.display = 'block';
  try{
    const facts = collectFactsFromForm();
    const body = new URLSearchParams(Object.entries(facts));
    const res = await fetch('/suite/generate-why-event/', {
      method:'POST',
      headers:{
        'X-CSRFToken':getCookie('csrftoken'),
        'Content-Type':'application/x-www-form-urlencoded'
      },
      body
    });
    const data = await res.json();
    if(!res.ok || !data.ok){ alert(data.error || 'Generation failed'); return; }
    applyText('need_analysis', data.need_analysis || '');
    applyBullets('objectives', data.objectives || []);
    applyBullets('learning_outcomes', data.learning_outcomes || []);
    showCard('need-analysis', data.need_analysis || '');
    showCard('objectives', data.objectives || []);
    showCard('learning-outcomes', data.learning_outcomes || []);
    if (typeof window.autosave === 'function') window.autosave();
  }catch(e){ console.error(e); alert('Generation failed'); }
  finally{ if(status) status.style.display = 'none'; }
}

function showCard(field, content){
  const card = document.querySelector(`#ai-${field}`);
  if (!card) return;

  const fieldMap = {
    'need-analysis': 'need-analysis-modern',
    'objectives': 'objectives-modern',
    'learning-outcomes': 'outcomes-modern'
  };
  const target = document.getElementById(fieldMap[field]);

  if (Array.isArray(content)){
    if (!content.length){
      card.innerHTML = '';
      return;
    }
    const listHtml = '<ul>' + content.map(i=>`<li>${i}</li>`).join('') + '</ul>';
    const text = content.map(i=>`• ${i}`).join('\n');
    card.innerHTML = `${listHtml}<button type="button" class="apply-ai-suggestion">Apply</button>`;
    const btn = card.querySelector('button');
    if (btn && target){
      btn.addEventListener('click', () => {
        target.value = text;
        target.dispatchEvent(new Event('input', { bubbles: true }));
      });
    }
  } else {
    if (!content){
      card.textContent = '';
      return;
    }
    card.innerHTML = `<p>${content}</p><button type="button" class="apply-ai-suggestion">Apply</button>`;
    const btn = card.querySelector('button');
    if (btn && target){
      btn.addEventListener('click', () => {
        target.value = content;
        target.dispatchEvent(new Event('input', { bubbles: true }));
      });
    }
  }
}*/

// Inject generated text into the real field/editor and trigger autosave
function applyGeneratedToField(field, text) {
  const id = `id_${field}`;

  function triggerSave() {
    if (window.AutosaveManager && window.AutosaveManager.manualSave) {
      try { window.AutosaveManager.manualSave(); } catch (e) {}
    }
  }

  if (window.CKEDITOR && CKEDITOR.instances[id]) {
    CKEDITOR.instances[id].setData(text);
    triggerSave();
    return;
  }
  if (window.ClassicEditor && window._editors && window._editors[field]) {
    window._editors[field].setData(text);
    triggerSave();
    return;
  }
  if (window.tinymce && tinymce.get(id)) {
    tinymce.get(id).setContent(text);
    triggerSave();
    return;
  }
  if (window.Quill && window._quills && window._quills[field]) {
    const q = window._quills[field];
    q.setText("");
    q.clipboard.dangerouslyPasteHTML(0, text);
    triggerSave();
    return;
  }
  const el = document.getElementById(id);
  if (el) {
    el.value = text;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    triggerSave();
  }
}

/*async function onGenerateNeedAnalysis(e) {
  e?.preventDefault?.();
  const btn = e?.currentTarget;
  const original = btn?.innerHTML;
  if (btn) btn.innerHTML = 'Generating…';

  try {
    const title = document.querySelector('#id_event_title')?.value
               || document.querySelector('#id_title')?.value
               || '';

    const res = await fetch('/suite/generate-need-analysis/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': (document.cookie.match(/csrftoken=([^;]+)/) || [,''])[1],
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({ topic: title })
    });

    const data = await res.json();
    if (!res.ok || !data.ok) {
      throw new Error(data.error || `HTTP ${res.status}`);
    }
    applyGeneratedToField(data.field || 'need_analysis', data.value || data.text || '');
    if (typeof window.autosave === 'function') window.autosave();
  } catch (err) {
    console.error('Generation failed:', err);
    alert(`All AI backends failed: ${err.message || err}`);
  } finally {
    if (btn) btn.innerHTML = original || 'Generate with AI';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const btn = document.querySelector('#btn-generate-need-analysis');
  if (btn && !btn._wired) {
    btn.addEventListener('click', onGenerateNeedAnalysis);
    btn._wired = true;
  }
});*/

// Functions to manage submit section visibility
function addSubmitSection() {
  // Check if submit section already exists
  if (document.querySelector('.submit-section')) {
    return;
  }

  // Find the form content container
  const formContent = document.querySelector('#form-panel-content');
  if (!formContent) {
    console.error('Form content container not found');
    return;
  }

  // Create the submit section HTML with only the final submit action
  const submitSectionHTML = `
    <div class="submit-section">
      <h5 class="mb-3" style="color: var(--primary-blue); font-weight: 600;">Submit Proposal</h5>
      <div class="d-flex gap-3 justify-content-center">
        <button type="submit" class="btn-submit" name="review_submit" id="submit-proposal-btn" disabled>Submit Proposal</button>
      </div>
      <p class="submit-help-text">Review all sections before final submission</p>
    </div>
  `;

  // Add the submit section to the form content
  formContent.insertAdjacentHTML('beforeend', submitSectionHTML);
}

function removeSubmitSection() {
  const submitSection = document.querySelector('.submit-section');
  if (submitSection) {
    submitSection.remove();
  }
}

// Apply focus styling and auto-resize behavior to text inputs
function enhanceProposalInputs() {
  document.querySelectorAll('.proposal-content .input-group .proposal-input').forEach((el) => {
    const group = el.closest('.input-group');
    if (!group) return;

    el.addEventListener('focus', () => group.classList.add('focused'));
    el.addEventListener('blur', () => group.classList.remove('focused'));

    if (el.tagName === 'TEXTAREA') {
      const resize = () => {
        el.style.height = 'auto';
        el.style.height = el.scrollHeight + 'px';
      };
      el.addEventListener('input', resize);
      resize();
    }
  });
}

