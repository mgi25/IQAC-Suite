/**
 * Student Profile Page JavaScript
 * Handles student-specific profile functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Student Profile page loaded successfully');
    
    // Initialize student-specific features
    initializeStudentProfile();
    initializeAvatarUpload();
    initializeFormHandlers();
    initializeQuickActions();
    initializeJoinRequests();
    initializeAchievementsModule();
});

let activeModal = null;
let previouslyFocusedElement = null;
let modalEscapeListener = null;
let modalFocusTrapListener = null;
let achievementsCache = [];
let achievementsInitialized = false;
let achievementBeingEdited = null;
let achievementPendingDeletion = null;
let joinRequestsCache = [];
let joinRequestsInitialized = false;

// Student Profile Initialization
function initializeStudentProfile() {
    // Initialize academic info display
    updateAcademicStatus();
    
    // Load participation stats
    loadParticipationStats();
}

// Academic Status Updates
function updateAcademicStatus() {
    const academicCards = document.querySelectorAll('.status-item-large');
    
    academicCards.forEach(card => {
        const description = card.querySelector('.status-description');
        if (description && description.textContent.includes('Not')) {
            card.classList.add('incomplete');
        }
    });
}

// Load Participation Statistics
async function loadParticipationStats() {
    try {
        const response = await fetch('/api/student/participation-stats/', {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        
        if (response.ok) {
            const data = await response.json();
            updateParticipationDisplay(data);
        }
    } catch (error) {
        console.log('Participation stats not available:', error);
    }
}

function updateParticipationDisplay(data) {
    // Update stats in the header
    const statsCards = document.querySelectorAll('.stat-card');

    statsCards.forEach(card => {
        const label = card.querySelector('.stat-label').textContent;
        const numberElement = card.querySelector('.stat-number');
        
        switch (label) {
            case 'EVENTS PARTICIPATED':
                if (data.total_events !== undefined) {
                    numberElement.textContent = data.total_events;
                }
                break;
            case 'ORGANIZATIONS':
                if (data.organizations_count !== undefined) {
                    numberElement.textContent = data.organizations_count;
                }
                break;
            case 'ACHIEVEMENTS':
                if (data.achievements_count !== undefined) {
                    numberElement.textContent = data.achievements_count;
                }
                break;
        }
    });
}

function applyPersonalInfoUpdate(payload) {
    if (!payload || typeof payload !== 'object') {
        return;
    }

    const fullName = payload.full_name || `${payload.first_name || ''} ${payload.last_name || ''}`.trim();
    const usernameFallback = payload.username || document.querySelector('.profile-title')?.dataset.username || '';
    const resolvedName = fullName || usernameFallback || 'Not Set';
    const email = payload.email || '';
    const registration = payload.registration_number || '';

    const fullNameEl = document.querySelector('[data-field="full_name"]');
    if (fullNameEl) {
        fullNameEl.textContent = resolvedName;
        fullNameEl.dataset.firstName = payload.first_name || '';
        fullNameEl.dataset.lastName = payload.last_name || '';
        fullNameEl.dataset.username = usernameFallback;
    }

    const profileTitleEl = document.querySelector('.profile-title');
    if (profileTitleEl) {
        profileTitleEl.textContent = resolvedName;
    }

    const emailEl = document.querySelector('[data-field="email"]');
    if (emailEl) {
        const displayEmail = email || 'Not Set';
        emailEl.textContent = displayEmail;
        emailEl.dataset.value = email;
    }

    const profileSubtitleEl = document.querySelector('.profile-subtitle');
    if (profileSubtitleEl) {
        profileSubtitleEl.textContent = email || 'Not Set';
        profileSubtitleEl.dataset.profileEmail = email;
    }

    const registrationEl = document.querySelector('[data-field="registration_number"]');
    if (registrationEl) {
        registrationEl.textContent = registration || 'Not Set';
        registrationEl.dataset.value = registration;
    }

    const headerRegistrationEl = document.querySelector('.profile-reg-number');
    if (headerRegistrationEl) {
        const textSpan = headerRegistrationEl.querySelector('.registration-number-text');
        headerRegistrationEl.dataset.registrationNumber = registration;
        if (registration) {
            headerRegistrationEl.removeAttribute('hidden');
            if (textSpan) {
                textSpan.textContent = registration;
            }
        } else {
            headerRegistrationEl.setAttribute('hidden', 'hidden');
            if (textSpan) {
                textSpan.textContent = 'Not Set';
            }
        }
    }
}

function initializeJoinRequests() {
    hydrateJoinRequests();
}

function hydrateJoinRequests() {
    if (joinRequestsInitialized) {
        return;
    }

    try {
        const script = document.getElementById('join-requests-data');
        if (!script) {
            renderJoinRequests([]);
            return;
        }
        const parsed = JSON.parse(script.textContent || '[]');
        joinRequestsCache = Array.isArray(parsed) ? parsed : [];
        renderJoinRequests(joinRequestsCache);
    } catch (error) {
        console.error('Failed to hydrate join requests:', error);
        renderJoinRequests([]);
    } finally {
        joinRequestsInitialized = true;
    }
}

function renderJoinRequests(items) {
    const list = document.getElementById('join-requests-list');
    const emptyState = document.getElementById('join-requests-empty');
    if (!list || !emptyState) {
        return;
    }

    if (!items || items.length === 0) {
        list.innerHTML = '';
        list.setAttribute('hidden', 'hidden');
        emptyState.removeAttribute('hidden');
        emptyState.style.display = '';
        applyJoinRequestStates();
        return;
    }

    const markup = items.map(joinRequestCardTemplate).join('');
    list.innerHTML = markup;
    list.removeAttribute('hidden');
    emptyState.setAttribute('hidden', 'hidden');
    emptyState.style.display = 'none';
    applyJoinRequestStates();
}

function joinRequestStatusClass(status) {
    if (!status) {
        return 'pending';
    }
    return String(status).toLowerCase().replace(/[^a-z0-9]+/g, '-');
}

function applyJoinRequestStates() {
    const rows = document.querySelectorAll('#organization-list .organization-list-item');
    rows.forEach(row => {
        row.classList.remove('leave-pending');
        const extra = row.querySelector('.org-extra');
        if (extra) {
            extra.querySelectorAll('.org-pill-pending').forEach(pill => pill.remove());
        }
        const leaveButton = row.querySelector('[data-action="leave"]');
        if (leaveButton) {
            leaveButton.disabled = false;
            leaveButton.title = 'Request to leave';
        }
    });

    if (!Array.isArray(joinRequestsCache) || joinRequestsCache.length === 0) {
        return;
    }

    joinRequestsCache
        .filter(item => {
            if (!item || !item.organization) {
                return false;
            }
            const type = String(item.request_type || '').toLowerCase();
            const status = String(item.status || '');
            return type === 'leave' && status === 'Pending';
        })
        .forEach(item => {
            const orgId = item.organization?.id;
            if (!orgId) {
                return;
            }
            const row = document.querySelector(`#organization-list .organization-list-item[data-org-id="${orgId}"]`);
            if (!row) {
                return;
            }

            row.classList.add('leave-pending');

            const leaveButton = row.querySelector('[data-action="leave"]');
            if (leaveButton) {
                leaveButton.disabled = true;
                leaveButton.title = 'Leave request pending approval';
            }

            const extra = row.querySelector('.org-extra');
            if (extra && !extra.querySelector('.org-pill-pending')) {
                extra.insertAdjacentHTML(
                    'beforeend',
                    '<span class="org-pill org-pill-pending"><i class="fas fa-hourglass-half"></i> Leave request pending</span>'
                );
            }
        });
}

function joinRequestCardTemplate(item) {
    const organizationName = item?.organization?.name ? escapeHtml(item.organization.name) : 'Organization';
    const requestType = String(item?.request_type || 'join').toLowerCase();
    const typeDisplay = item?.request_type_display
        ? escapeHtml(item.request_type_display)
        : requestType === 'leave'
            ? 'Leave'
            : 'Join';

    const rawStatus = item?.status === 'Pending' && item?.is_seen
        ? 'Seen'
        : item?.status_display || item?.status || 'Pending';
    const statusLabel = escapeHtml(rawStatus);
    const badgeClass = joinRequestStatusClass(rawStatus);

    const requestedDisplay = item?.requested_display ? escapeHtml(item.requested_display) : 'Unknown';
    const responseMarkup = item?.response_message
        ? `<div class="join-request-response">${escapeHtml(item.response_message)}</div>`
        : '';

    return `
        <div class="join-request-row" data-request-id="${item.id}" data-organization-id="${item?.organization?.id || ''}" data-request-type="${requestType}">
            <div class="join-request-main">
                <span class="join-request-name">${organizationName}</span>
                <span class="join-request-meta">${typeDisplay} · ${requestedDisplay}</span>
            </div>
            <div class="join-request-status">
                <span class="status-pill status-pill-${badgeClass}">${statusLabel}</span>
            </div>
            ${responseMarkup}
        </div>
    `;
}

function addOrUpdateJoinRequestCard(request) {
    if (!request) {
        return;
    }

    if (!Array.isArray(joinRequestsCache)) {
        joinRequestsCache = [];
    }

    const index = joinRequestsCache.findIndex(item => String(item.id) === String(request.id));
    if (index !== -1) {
        joinRequestsCache[index] = request;
    } else {
        joinRequestsCache = [request, ...joinRequestsCache];
    }

    renderJoinRequests(joinRequestsCache);
}

// Form Handlers for Student-Specific Actions
function initializeFormHandlers() {
    // Personal info edit handler
    window.editPersonalInfo = function() {
        const fullNameEl = document.querySelector('[data-field="full_name"]');
        const emailEl = document.querySelector('[data-field="email"]');
        const registrationEl = document.querySelector('[data-field="registration_number"]');

        const firstName = fullNameEl?.dataset.firstName || '';
        const lastName = fullNameEl?.dataset.lastName || '';
        const email = emailEl?.dataset.value || emailEl?.textContent.trim() || '';
        const registration = registrationEl?.getAttribute('data-value') || '';

        showEditModal('personal-info', {
            title: 'Edit Personal Information',
            description: 'Update your name and registration number so your profile stays current.',
            fields: [
                { name: 'first_name', label: 'First Name', type: 'text', required: true, value: firstName },
                { name: 'last_name', label: 'Last Name', type: 'text', required: true, value: lastName },
                { name: 'email', label: 'Email', type: 'email', required: true, readonly: true, value: email },
                { name: 'registration_number', label: 'Registration Number', type: 'text', required: false, value: registration }
            ]
        });
    };

    // Academic info edit handler
    window.editAcademicInfo = function() {
        const getFieldValue = name => {
            const el = document.querySelector(`[data-field="${name}"]`);
            if (!el) {
                return '';
            }
            return (el.getAttribute('data-value') || el.textContent || '').trim();
        };

        showEditModal('academic-info', {
            title: 'Edit Academic Information',
            fields: [
                { name: 'department', label: 'Department', type: 'text', required: false, value: getFieldValue('department') },
                { name: 'academic_year', label: 'Academic Year', type: 'text', required: false, value: getFieldValue('academic_year') },
                { name: 'current_semester', label: 'Current Semester', type: 'text', required: false, value: getFieldValue('current_semester') },
                { name: 'gpa', label: 'GPA', type: 'number', step: '0.01', min: '0', max: '10', required: false, value: getFieldValue('gpa') },
                { name: 'enrollment_year', label: 'Enrollment Year', type: 'number', required: false, value: getFieldValue('enrollment_year') }
            ]
        });
    };

    // Achievement management
    window.addAchievement = function() {
        showEditModal('add-achievement', {
            title: 'Add Achievement',
            description: 'Keep your achievements up to date to highlight your strengths and growth.',
            fields: [
                { name: 'title', label: 'Achievement Title', type: 'text', placeholder: 'Leadership Excellence Award', required: true, helpText: 'Keep it short and descriptive.' },
                { name: 'description', label: 'Description', type: 'textarea', placeholder: 'Describe the achievement and its impact.', required: false },
                { name: 'date_achieved', label: 'Date Achieved', type: 'date', required: false },
                { name: 'document', label: 'Supporting Document', type: 'file', required: false, accept: 'application/pdf,image/*', helpText: 'Optional. Upload a PDF or image up to 10 MB.' }
            ],
            submitLabel: 'Save Achievement',
            enctype: 'multipart/form-data'
        });
    };

    window.editAchievement = function(achievementId) {
        openAchievementEditor(achievementId);
    };

    window.deleteAchievement = function(achievementId) {
        confirmAchievementDeletion(achievementId);
    };

    // Organization management
    window.joinOrganization = function() {
        showOrganizationSelector();
    };

    window.leaveOrganization = function(orgId) {
        if (confirm('Are you sure you want to leave this organization?')) {
            leaveOrganizationRequest(orgId);
        }
    };

    window.viewOrganization = function(orgId) {
        window.location.href = `/organizations/${orgId}/`;
    };
}

// Quick Actions
function initializeQuickActions() {
    // Export functionality
    window.exportParticipation = function() {
        showNotification('Exporting participation history...', 'info');
        window.location.href = '/api/student/export-participation/';
    };
}

// Modal System for Editing
function showEditModal(type, config = {}) {
    if (activeModal) {
        closeEditModal(true);
    }

    const modal = document.createElement('div');
    modal.className = 'edit-modal';

    const descriptionMarkup = config.description ? `<p class="modal-description">${config.description}</p>` : '';
    const submitLabel = config.submitLabel || 'Save Changes';
    const fieldsMarkup = Array.isArray(config.fields) ? config.fields.map(field => createFormField(field)).join('') : '';

    modal.innerHTML = `
        <div class="modal-backdrop" data-modal-backdrop></div>
        <div class="modal-content" role="dialog" aria-modal="true" aria-labelledby="modal-title-${type}">
            <div class="modal-header">
                <h3 id="modal-title-${type}">${config.title || 'Edit'}</h3>
                <button type="button" class="modal-close" aria-label="Close" onclick="closeEditModal()">&times;</button>
            </div>
            <div class="modal-body">
                ${descriptionMarkup}
                <form id="edit-form-${type}" class="edit-form">
                    ${fieldsMarkup}
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="closeEditModal()">Cancel</button>
                <button type="button" class="btn btn-primary" data-save>${submitLabel}</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    document.body.classList.add('modal-open');
    activeModal = modal;
    previouslyFocusedElement = document.activeElement;

    const form = modal.querySelector('form');
    if (form) {
        if (config.enctype) {
            form.setAttribute('enctype', config.enctype);
        }
        if (config.method) {
            form.setAttribute('method', config.method);
        }
        form.addEventListener('submit', event => event.preventDefault());
    }

    const saveButton = modal.querySelector('[data-save]');
    if (saveButton) {
        saveButton.addEventListener('click', () => window.saveFormData(type));
        if (config.submitLabel) {
            saveButton.textContent = config.submitLabel;
        }
    }

    const backdrop = modal.querySelector('[data-modal-backdrop]');
    if (backdrop) {
        const handleBackdropClick = event => {
            if (event.target === backdrop) {
                closeEditModal();
            }
        };
        backdrop.addEventListener('click', handleBackdropClick);
        modal._backdropHandler = handleBackdropClick;
    }

    modalEscapeListener = event => {
        if (event.key === 'Escape') {
            closeEditModal();
        }
    };
    document.addEventListener('keydown', modalEscapeListener);

    const focusableSelector = 'a[href], area[href], input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), [tabindex]:not([tabindex="-1"])';
    const focusableElements = modal.querySelectorAll(focusableSelector);
    const firstFocusable = focusableElements[0];
    const lastFocusable = focusableElements[focusableElements.length - 1];

    if (focusableElements.length > 0) {
        modalFocusTrapListener = event => {
            if (event.key !== 'Tab') {
                return;
            }

            if (event.shiftKey && document.activeElement === firstFocusable) {
                event.preventDefault();
                lastFocusable.focus();
            } else if (!event.shiftKey && document.activeElement === lastFocusable) {
                event.preventDefault();
                firstFocusable.focus();
            }
        };

        modal.addEventListener('keydown', modalFocusTrapListener);
        setTimeout(() => firstFocusable.focus(), 50);
    }
}

function showConfirmationModal(config = {}) {
    if (activeModal) {
        closeEditModal(true);
    }

    const {
        title = 'Confirm',
        message = 'Are you sure?',
        confirmLabel = 'Confirm',
        cancelLabel = 'Cancel',
        confirmType = 'primary',
        onConfirm,
    } = config;

    const modal = document.createElement('div');
    modal.className = 'edit-modal confirmation-modal';

    const confirmClass = confirmType === 'danger' ? 'btn btn-danger' : 'btn btn-primary';

    modal.innerHTML = `
        <div class="modal-backdrop" data-modal-backdrop></div>
        <div class="modal-content" role="dialog" aria-modal="true" aria-labelledby="modal-title-confirm">
            <div class="modal-header">
                <h3 id="modal-title-confirm">${title}</h3>
                <button type="button" class="modal-close" aria-label="Close" onclick="closeEditModal()">&times;</button>
            </div>
            <div class="modal-body">
                <p>${message}</p>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="closeEditModal()">${cancelLabel}</button>
                <button type="button" class="${confirmClass}" data-confirm>${confirmLabel}</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    document.body.classList.add('modal-open');
    activeModal = modal;
    previouslyFocusedElement = document.activeElement;

    const confirmButton = modal.querySelector('[data-confirm]');
    if (confirmButton) {
        confirmButton.addEventListener('click', () => {
            confirmButton.disabled = true;
            closeEditModal();
            try {
                const result = onConfirm ? onConfirm() : null;
                if (result && typeof result.then === 'function') {
                    result.catch(error => {
                        console.error('Confirmation callback error:', error);
                    });
                }
            } catch (error) {
                console.error('Confirmation callback error:', error);
            }
        });
    }

    const backdrop = modal.querySelector('[data-modal-backdrop]');
    if (backdrop) {
        const handleBackdropClick = event => {
            if (event.target === backdrop) {
                closeEditModal();
            }
        };
        backdrop.addEventListener('click', handleBackdropClick);
        modal._backdropHandler = handleBackdropClick;
    }

    modalEscapeListener = event => {
        if (event.key === 'Escape') {
            closeEditModal();
        }
    };
    document.addEventListener('keydown', modalEscapeListener);

    setTimeout(() => {
        confirmButton?.focus();
    }, 50);
}

function createFormField(field) {
    const value = field.value || '';
    const safeValue = escapeHtml(value);
    const required = field.required ? 'required' : '';
    const readonly = field.readonly ? 'readonly' : '';
    const placeholder = field.placeholder ? `placeholder="${field.placeholder}"` : '';
    const helpText = field.helpText ? `<p class="form-help">${field.helpText}</p>` : '';
    const step = field.step ? `step="${field.step}"` : '';
    const min = field.min ? `min="${field.min}"` : '';
    const max = field.max ? `max="${field.max}"` : '';

    let input = '';

    switch (field.type) {
        case 'textarea':
            input = `<textarea name="${field.name}" ${required} ${readonly} ${placeholder}>${safeValue}</textarea>`;
            break;
        case 'select':
            input = `<select name="${field.name}" ${required} ${readonly}>
                <option value="">Select ${field.label}</option>
            </select>`;
            break;
        case 'file':
            {
                const accept = field.accept ? `accept="${field.accept}"` : '';
                input = `<input type="file" name="${field.name}" ${required} ${accept}>`;
            }
            break;
        default:
            input = `<input type="${field.type}" name="${field.name}" value="${safeValue}" ${required} ${readonly} ${placeholder} ${step} ${min} ${max}>`;
    }

    return `
        <div class="form-group">
            <label for="${field.name}">${field.label}${field.required ? ' <span class="required">*</span>' : ''}</label>
            ${input}
            ${helpText}
        </div>
    `;
}

window.closeEditModal = function(skipFocusRestore = false) {
    if (!activeModal) {
        const existingModal = document.querySelector('.edit-modal');
        if (existingModal) {
            existingModal.remove();
        }
        document.body.classList.remove('modal-open');
        return;
    }

    if (activeModal._backdropHandler) {
        const backdrop = activeModal.querySelector('[data-modal-backdrop]');
        if (backdrop) {
            backdrop.removeEventListener('click', activeModal._backdropHandler);
        }
        delete activeModal._backdropHandler;
    }

    if (modalEscapeListener) {
        document.removeEventListener('keydown', modalEscapeListener);
        modalEscapeListener = null;
    }

    if (modalFocusTrapListener) {
        activeModal.removeEventListener('keydown', modalFocusTrapListener);
        modalFocusTrapListener = null;
    }

    activeModal.remove();
    document.body.classList.remove('modal-open');

    if (!skipFocusRestore && previouslyFocusedElement && typeof previouslyFocusedElement.focus === 'function') {
        previouslyFocusedElement.focus();
    }

    activeModal = null;
    previouslyFocusedElement = null;
    achievementBeingEdited = null;
    achievementPendingDeletion = null;
};

window.saveFormData = function(type) {
    const form = document.querySelector(`#edit-form-${type}`);
    if (!form) return;
    const isMultipart = form.getAttribute('enctype') === 'multipart/form-data';
    const formData = new FormData(form);
    const payload = isMultipart ? formData : Object.fromEntries(formData.entries());

    const saveButton = activeModal?.querySelector('[data-save]');
    const originalText = saveButton ? saveButton.textContent : null;
    if (saveButton) {
        saveButton.textContent = 'Saving…';
        saveButton.disabled = true;
    }

    const submissionOptions = { isMultipart };
    if (type === 'edit-achievement') {
        submissionOptions.achievementId = achievementBeingEdited;
    }

    submitFormData(type, payload, submissionOptions)
        .then(response => {
            if (!response.success) {
                throw new Error(response.message || 'Failed to save changes');
            }

            if (type === 'add-achievement') {
                showNotification(response.message || 'Achievement added successfully!', 'success');
                closeEditModal();
                if (response.achievement) {
                    achievementsCache = [response.achievement, ...achievementsCache];
                    renderAchievements(achievementsCache);
                    updateAchievementsStat(achievementsCache.length);
                } else {
                    loadStudentAchievements(true);
                }
            } else if (type === 'edit-achievement') {
                showNotification(response.message || 'Achievement updated successfully!', 'success');
                closeEditModal();
                if (response.achievement) {
                    const index = achievementsCache.findIndex(item => String(item.id) === String(response.achievement.id));
                    if (index !== -1) {
                        achievementsCache[index] = response.achievement;
                    }
                    renderAchievements(achievementsCache);
                    updateAchievementsStat(achievementsCache.length);
                }
                loadStudentAchievements(true);
                achievementBeingEdited = null;
            } else if (type === 'join-organization') {
                showNotification(response.message || 'Join request submitted successfully!', 'success');
                closeEditModal();
                if (response.join_request) {
                    addOrUpdateJoinRequestCard(response.join_request);
                }
                if (response.organization) {
                    addOrUpdateOrganizationCard(response.organization);
                }
                loadParticipationStats();
            } else {
                showNotification(response.message || 'Changes saved successfully!', 'success');
                closeEditModal();
                if (type === 'academic-info' && response.data) {
                    applyAcademicInfoUpdate(response.data);
                } else if (type === 'personal-info' && response.data) {
                    applyPersonalInfoUpdate(response.data);
                } else {
                    window.location.reload();
                }
            }
        })
        .catch(error => {
            showNotification(error.message || 'Failed to save changes', 'error');
        })
        .finally(() => {
            if (saveButton) {
                saveButton.textContent = originalText || 'Save Changes';
                saveButton.disabled = false;
            }
        });
};

// API Calls
async function submitFormData(type, data, options = {}) {
    const { isMultipart = false, achievementId = null } = options;
    const endpoints = {
        'personal-info': '/api/student/update-personal-info/',
        'academic-info': '/api/student/update-academic-info/',
        'add-achievement': '/api/student/achievements/',
        'edit-achievement': '/api/student/achievements/',
        'join-organization': '/api/student/join-organization/'
    };
    
    let endpoint = endpoints[type];
    if (!endpoint) {
        throw new Error('Unknown form type');
    }

    if (type === 'edit-achievement') {
        if (!achievementId) {
            throw new Error('Missing achievement identifier');
        }
        endpoint = `${endpoint}${achievementId}/`;
    }
    const headers = {
        'X-CSRFToken': getCsrfToken(),
        'X-Requested-With': 'XMLHttpRequest'
    };

    const fetchOptions = {
        method: 'POST',
        headers,
        body: null
    };

    if (isMultipart) {
        fetchOptions.body = data;
    } else {
        headers['Content-Type'] = 'application/json';
        fetchOptions.body = JSON.stringify(data);
    }

    const response = await fetch(endpoint, fetchOptions);

    let payload;
    try {
        payload = await response.json();
    } catch (error) {
        throw new Error('Unexpected server response');
    }

    if (!response.ok) {
        const message = payload?.message || payload?.errors || 'Failed to save changes';
        throw new Error(Array.isArray(message) ? message.join(', ') : message);
    }

    return payload;
}

async function deleteAchievementRequest(achievementId) {
    const response = await fetch(`/api/student/achievements/${achievementId}/`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': getCsrfToken(),
            'X-Requested-With': 'XMLHttpRequest',
        },
    });

    let payload = {};
    try {
        if (response.status !== 204) {
            payload = await response.json();
        }
    } catch (error) {
        // Ignore JSON parse errors for empty bodies
    }

    if (!response.ok || payload.success === false) {
        const message = payload?.message || 'Failed to delete achievement.';
        throw new Error(message);
    }

    return payload;
}

function initializeAchievementsModule() {
    hydrateInitialAchievements();
    loadStudentAchievements(true);
}

function hydrateInitialAchievements() {
    if (achievementsInitialized) {
        return;
    }

    try {
        const script = document.getElementById('student-achievements-data');
        if (!script) {
            return;
        }
        const parsed = JSON.parse(script.textContent || '[]');
        achievementsCache = Array.isArray(parsed) ? parsed : [];
        renderAchievements(achievementsCache);
        updateAchievementsStat(achievementsCache.length);
        achievementsInitialized = true;
    } catch (error) {
        console.error('Failed to hydrate achievements payload:', error);
    }
}

async function loadStudentAchievements(forceRefresh = false) {
    if (achievementsInitialized && !forceRefresh) {
        return;
    }

    try {
        const response = await fetch('/api/student/achievements/', {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });

        if (!response.ok) {
            throw new Error('Unable to load achievements');
        }

        const data = await response.json();
        const items = Array.isArray(data.achievements) ? data.achievements : [];
        achievementsCache = items;
        renderAchievements(achievementsCache);
        updateAchievementsStat(achievementsCache.length);
        achievementsInitialized = true;
    } catch (error) {
        console.error('Failed to load achievements:', error);
        if (!achievementsInitialized) {
            renderAchievements([]);
        }
    }
}

function applyAcademicInfoUpdate(payload) {
    const fieldMap = {
        registration_number: value => value || 'Not Set',
        department: value => value || 'Not Set',
        academic_year: value => value || 'Not Set',
        current_semester: value => value || 'Not Set',
        gpa: value => {
            if (value === null || value === undefined || value === '') {
                return 'Not Set';
            }
            const num = Number(value);
            if (Number.isNaN(num)) {
                return value;
            }
            return num.toFixed(2);
        },
        enrollment_year: value => value || 'Not Set',
    };

    Object.keys(fieldMap).forEach(key => {
        const el = document.querySelector(`[data-field="${key}"]`);
        if (!el) {
            return;
        }
        const rawValue = payload[key];
        const displayValue = fieldMap[key](rawValue);
        el.textContent = displayValue;
        if (rawValue === null || rawValue === undefined) {
            el.setAttribute('data-value', '');
        } else {
            el.setAttribute('data-value', `${rawValue}`);
        }
    });

    updateAcademicStatus();
}

function renderAchievements(items) {
    const list = document.getElementById('achievements-list');
    const emptyState = document.getElementById('achievements-empty');
    if (!list || !emptyState) {
        return;
    }

    if (!items || items.length === 0) {
        list.innerHTML = '';
        list.setAttribute('hidden', 'hidden');
        emptyState.removeAttribute('hidden');
        return;
    }

    const markup = items.map(achievementCardTemplate).join('');
    list.innerHTML = markup;
    list.removeAttribute('hidden');
    emptyState.setAttribute('hidden', 'hidden');
    attachAchievementListeners();
}

function achievementCardTemplate(item) {
    const documentLink = item.document_url
        ? `<div class="achievement-document">
                <a class="achievement-doc-link" href="${item.document_url}" target="_blank" rel="noopener">
                    <i class="fas fa-paperclip"></i>
                    ${item.document_name ? escapeHtml(item.document_name) : 'View Document'}
                </a>
           </div>`
        : '';

    const dateMarkup = item.date_display
        ? `<div class="meta-item">
                <i class="fas fa-calendar"></i>
                <span>${escapeHtml(item.date_display)}</span>
           </div>`
        : '';

    const descriptionMarkup = item.description
        ? `<div class="achievement-description">${escapeHtml(item.description)}</div>`
        : '';

    return `
        <div class="achievement-card-large" data-achievement-id="${item.id}">
            <div class="achievement-header">
                <div class="achievement-icon">
                    <i class="fas fa-trophy"></i>
                </div>
                <div class="achievement-actions">
                    <button type="button" class="action-btn achievement-action-btn" data-edit-button tabindex="0" aria-label="Edit achievement">
                        <i class="fas fa-edit"></i>
                        Edit
                    </button>
                    <button type="button" class="action-btn achievement-delete-btn" data-delete-button tabindex="0" aria-label="Delete achievement">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
            <div class="achievement-content">
                <h4>${escapeHtml(item.title)}</h4>
                <div class="achievement-meta">
                    ${dateMarkup}
                </div>
                ${descriptionMarkup}
                ${documentLink}
            </div>
        </div>
    `;
}

function attachAchievementListeners() {
    const cards = document.querySelectorAll('.achievement-card-large[data-achievement-id]');
    cards.forEach(card => {
        const id = parseInt(card.getAttribute('data-achievement-id'), 10);
        if (Number.isNaN(id)) {
            return;
        }

        const editButton = card.querySelector('[data-edit-button]');
        if (editButton) {
            editButton.addEventListener('click', event => {
                event.preventDefault();
                event.stopPropagation();
                openAchievementEditor(id);
            });
        }

        const deleteButton = card.querySelector('[data-delete-button]');
        if (deleteButton) {
            deleteButton.addEventListener('click', event => {
                event.preventDefault();
                event.stopPropagation();
                confirmAchievementDeletion(id);
            });
        }

        card.addEventListener('click', event => {
            if (event.target.closest('.achievement-doc-link')) {
                return;
            }
            if (event.target.closest('[data-edit-button]')) {
                return;
            }
            openAchievementEditor(id);
        });
    });
}

function openAchievementEditor(achievementId) {
    const achievement = achievementsCache.find(item => String(item.id) === String(achievementId));
    if (!achievement) {
        showNotification('Achievement details could not be loaded.', 'error');
        return;
    }

    achievementBeingEdited = achievementId;

    const documentUrl = achievement.document_url ? encodeURI(achievement.document_url) : null;
    const documentHelp = documentUrl
        ? `Current document: <a href="${documentUrl}" target="_blank" rel="noopener">${escapeHtml(achievement.document_name || 'View document')}</a>`
        : 'Optional. Upload a PDF or image up to 10 MB.';

    showEditModal('edit-achievement', {
        title: 'Edit Achievement',
        description: 'Update the details below and save to keep your achievements current.',
        submitLabel: 'Update Achievement',
        enctype: 'multipart/form-data',
        fields: [
            { name: 'title', label: 'Achievement Title', type: 'text', required: true, value: achievement.title },
            { name: 'description', label: 'Description', type: 'textarea', required: false, value: achievement.description || '' },
            { name: 'date_achieved', label: 'Date Achieved', type: 'date', required: false, value: achievement.date_achieved || '' },
            {
                name: 'document',
                label: 'Supporting Document',
                type: 'file',
                required: false,
                accept: 'application/pdf,image/*',
                helpText: documentHelp
            }
        ]
    });
}

function confirmAchievementDeletion(achievementId) {
    const achievement = achievementsCache.find(item => String(item.id) === String(achievementId));
    if (!achievement) {
        showNotification('Achievement details could not be loaded.', 'error');
        return;
    }

    achievementPendingDeletion = achievementId;

    showConfirmationModal({
        title: 'Delete Achievement',
        message: `Are you sure you want to delete "${escapeHtml(achievement.title)}"? This action cannot be undone.`,
        confirmLabel: 'Delete',
        confirmType: 'danger',
        onConfirm: () => executeAchievementDeletion(achievementId),
    });
}

async function executeAchievementDeletion(achievementId) {
    try {
        await deleteAchievementRequest(achievementId);
        achievementsCache = achievementsCache.filter(item => String(item.id) !== String(achievementId));
        renderAchievements(achievementsCache);
        updateAchievementsStat(achievementsCache.length);
        showNotification('Achievement deleted successfully.', 'success');
    } catch (error) {
        showNotification(error.message || 'Failed to delete achievement.', 'error');
    } finally {
        achievementPendingDeletion = null;
    }
}

function updateAchievementsStat(count) {
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach(card => {
        const label = card.querySelector('.stat-label');
        if (label && label.textContent.trim() === 'ACHIEVEMENTS') {
            const number = card.querySelector('.stat-number');
            if (number) {
                number.textContent = count != null ? count : 0;
            }
        }
    });
}

function escapeHtml(value) {
    if (value == null) {
        return '';
    }
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

async function showOrganizationSelector() {
    showEditModal('join-organization', {
        title: 'Join Organization',
        description: 'Select an organization type to see available groups you can join.',
        fields: [
            { name: 'organization_type_id', label: 'Organization Type', type: 'select', required: true },
            { name: 'organization_id', label: 'Organization', type: 'select', required: true }
        ],
        submitLabel: 'Join Organization'
    });

    const modal = activeModal;
    if (!modal) {
        return;
    }

    const typeSelect = modal.querySelector('select[name="organization_type_id"]');
    const orgSelect = modal.querySelector('select[name="organization_id"]');
    const saveButton = modal.querySelector('[data-save]');

    if (!typeSelect || !orgSelect || !saveButton) {
        showNotification('Unable to build join organization dialog.', 'error');
        closeEditModal();
        return;
    }

    const orgFeedback = document.createElement('p');
    orgFeedback.className = 'form-help';
    orgFeedback.setAttribute('data-join-org-feedback', '');
    orgFeedback.textContent = 'Choose an organization type to continue.';
    orgSelect.parentElement?.appendChild(orgFeedback);

    saveButton.disabled = true;
    orgSelect.disabled = true;

    const setSelectOptions = (selectEl, options, placeholder) => {
        const fragment = document.createDocumentFragment();
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = placeholder;
        fragment.appendChild(defaultOption);

        options.forEach(option => {
            const opt = document.createElement('option');
            opt.value = option.value;
            opt.textContent = option.label;
            fragment.appendChild(opt);
        });

        selectEl.innerHTML = '';
        selectEl.appendChild(fragment);
    };

    const setOrgFeedback = (message, tone = 'info') => {
        if (!orgFeedback) {
            return;
        }
        orgFeedback.textContent = message;
        orgFeedback.dataset.tone = tone;
    };

    const fetchJson = async (url, errorMessage) => {
        try {
            const response = await fetch(url, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            if (!response.ok) {
                throw new Error(errorMessage || 'Request failed');
            }
            return await response.json();
        } catch (error) {
            showNotification(error.message || errorMessage || 'Unable to load data.', 'error');
            throw error;
        }
    };

    const loadOrganizationTypes = async () => {
        setSelectOptions(typeSelect, [], 'Loading types...');
        typeSelect.disabled = true;
        try {
            const payload = await fetchJson('/api/student/organization-types/', 'Failed to load organization types.');
            const options = (payload.types || []).map(item => ({
                value: String(item.id),
                label: item.name
            }));
            if (options.length === 0) {
                setSelectOptions(typeSelect, [], 'No organization types available');
                setOrgFeedback('No organization types are available right now.', 'warning');
                saveButton.disabled = true;
            } else {
                setSelectOptions(typeSelect, options, 'Select organization type');
                typeSelect.disabled = false;
                setOrgFeedback('Select a type to see available organizations.');
            }
        } catch (error) {
            closeEditModal();
        }
    };

    const loadOrganizations = async typeId => {
        if (!typeId) {
            setSelectOptions(orgSelect, [], 'Select organization');
            orgSelect.disabled = true;
            saveButton.disabled = true;
            setOrgFeedback('Select an organization type to continue.');
            return;
        }

        orgSelect.disabled = true;
        saveButton.disabled = true;
        setSelectOptions(orgSelect, [], 'Loading organizations...');
        setOrgFeedback('Loading organizations...', 'info');

        try {
            const payload = await fetchJson(`/api/student/organizations/?type_id=${encodeURIComponent(typeId)}`, 'Failed to load organizations.');
            const orgs = payload.organizations || [];
            if (orgs.length === 0) {
                setSelectOptions(orgSelect, [], 'No organizations available');
                setOrgFeedback('No organizations found for this type.', 'warning');
                return;
            }

            const options = orgs.map(item => ({
                value: String(item.id),
                label: item.name
            }));
            setSelectOptions(orgSelect, options, 'Select organization');
            orgSelect.disabled = false;
            setOrgFeedback('Select an organization to join.');
        } catch (error) {
            setSelectOptions(orgSelect, [], 'Select organization');
            setOrgFeedback('Failed to load organizations. Please try again.', 'error');
        }
    };

    typeSelect.addEventListener('change', event => {
        const selectedType = event.target.value;
        loadOrganizations(selectedType);
    });

    orgSelect.addEventListener('change', () => {
        saveButton.disabled = !orgSelect.value;
    });

    await loadOrganizationTypes();
}

async function leaveOrganizationRequest(orgId) {
    try {
        const response = await fetch(`/api/student/leave-organization/${orgId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        let payload = {};
        try {
            const payloadText = await response.text();
            payload = payloadText ? JSON.parse(payloadText) : {};
        } catch (parseError) {
            payload = {};
        }

        if (!response.ok || payload.success === false) {
            throw new Error(payload.message || 'Failed to submit leave request');
        }

        if (payload.join_request) {
            addOrUpdateJoinRequestCard(payload.join_request);
        }

        showNotification(payload.message || 'Leave request submitted for approval.', 'success');

        const card = document.querySelector(`#organizations .organization-card-large[data-org-id="${orgId}"]`);
        const leaveButton = card?.querySelector('.org-actions [data-action="leave"]');
        if (leaveButton) {
            leaveButton.disabled = true;
            leaveButton.title = 'Leave request pending approval';
        }
    } catch (error) {
        showNotification(error.message || 'Failed to submit leave request', 'error');
    }
}

function getOrganizationList(createIfMissing = false) {
    let list = document.getElementById('organization-list');
    if (list || !createIfMissing) {
        return list;
    }

    const container = document.querySelector('#organizations .organization-panel .card-body');
    if (!container) {
        return null;
    }

    list = document.createElement('div');
    list.id = 'organization-list';
    list.className = 'organization-list';
    container.insertBefore(list, container.firstChild);

    const emptyState = container.querySelector('.empty-state-condensed');
    if (emptyState) {
        emptyState.setAttribute('hidden', 'hidden');
        emptyState.style.display = 'none';
    }

    return list;
}

function getOrganizationCount() {
    return document.querySelectorAll('#organization-list .organization-list-item').length;
}

function organizationCardTemplateFromData(org) {
    const canLeave = Object.prototype.hasOwnProperty.call(org, 'can_leave') ? Boolean(org.can_leave) : true;
    const typeLabel = org.org_type_display || org.type_name || 'Organization';
    const roleLabel = org.membership_role_label || '';
    const academicYear = org.membership_academic_year || '';
    const joinedDisplay = org.joined_display || org.joined_date_display || '';

    const pills = [];
    if (joinedDisplay) {
        pills.push(`<span class="org-pill">Joined ${escapeHtml(joinedDisplay)}</span>`);
    }
    if (academicYear) {
        pills.push(`<span class="org-pill">${escapeHtml(academicYear)}</span>`);
    }
    if (!canLeave) {
        pills.push('<span class="org-pill org-pill-muted">Admin managed</span>');
    }

    const pillsMarkup = pills.join('');
    const meta = roleLabel
        ? `${escapeHtml(typeLabel)} · ${escapeHtml(roleLabel)}`
        : escapeHtml(typeLabel);

    return `
        <div class="organization-list-item" data-org-id="${org.id}" data-can-leave="${canLeave}">
            <div class="org-summary">
                <div class="org-name">${escapeHtml(org.name)}</div>
                <div class="org-meta">${meta}</div>
            </div>
            <div class="org-extra">${pillsMarkup}</div>
            <div class="org-actions">
                <button class="btn btn-icon" type="button" onclick="viewOrganization(${org.id})" title="View organization">
                    <i class="fas fa-eye"></i>
                </button>
                ${canLeave ? `
                <button class="btn btn-icon" type="button" data-action="leave" title="Request to leave" onclick="leaveOrganization(${org.id})">
                    <i class="fas fa-sign-out-alt"></i>
                </button>` : `
                <button class="btn btn-icon" type="button" disabled title="Managed by administrator">
                    <i class="fas fa-lock"></i>
                </button>`}
            </div>
        </div>
    `;
}

function addOrUpdateOrganizationCard(org) {
    const list = getOrganizationList(true);
    if (!list || !org) {
        return;
    }

    const emptyState = document.querySelector('#organizations .empty-state-condensed');
    if (emptyState) {
        emptyState.setAttribute('hidden', 'hidden');
        emptyState.style.display = 'none';
    }

    const existingRow = list.querySelector(`[data-org-id="${org.id}"]`);
    const markup = organizationCardTemplateFromData(org);

    if (existingRow) {
        existingRow.outerHTML = markup;
    } else {
        list.insertAdjacentHTML('afterbegin', markup);
    }

    applyJoinRequestStates();
    updateOrganizationsStat(getOrganizationCount());
}

function removeOrganizationCard(orgId) {
    const row = document.querySelector(`#organization-list .organization-list-item[data-org-id="${orgId}"]`);
    if (!row) {
        return false;
    }

    row.remove();

    const remaining = getOrganizationCount();
    updateOrganizationsStat(remaining);

    if (remaining === 0) {
        const emptyState = document.querySelector('#organizations .empty-state-condensed');
        if (emptyState) {
            emptyState.removeAttribute('hidden');
            emptyState.style.display = '';
        }
    }

    return true;
}

function updateOrganizationsStat(count) {
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach(card => {
        const label = card.querySelector('.stat-label');
        if (label && label.textContent.trim() === 'ORGANIZATIONS') {
            const number = card.querySelector('.stat-number');
            if (number) {
                number.textContent = count != null ? count : 0;
            }
        }
    });
}

// Utility Functions
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
           document.querySelector('meta[name=csrf-token]')?.getAttribute('content') || '';
}

// Enhanced notification system for student profile
function showNotification(message, type = 'info', duration = 5000) {
    // Use the existing notification system from profile.js
    if (window.ProfilePage && window.ProfilePage.showNotification) {
        window.ProfilePage.showNotification(message, type);
    } else {
        // Fallback notification
        console.log(`[${type.toUpperCase()}] ${message}`);
        alert(message);
    }
}

// Enhanced Avatar Upload for Students
function initializeAvatarUpload() {
    const avatarSection = document.querySelector('.profile-avatar-large');
    const editButton = document.querySelector('.avatar-edit-btn');
    
    if (avatarSection && editButton) {
        editButton.addEventListener('click', function(e) {
            e.preventDefault();
            handleStudentAvatarUpload();
        });
    }
}

function handleStudentAvatarUpload() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    
    input.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            // Validate file size (max 2MB for students)
            if (file.size > 2 * 1024 * 1024) {
                showNotification('Image size must be less than 2MB', 'error');
                return;
            }
            
            // Preview and upload
            previewAndUploadAvatar(file);
        }
    });
    
    input.click();
}

function previewAndUploadAvatar(file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        const avatarPlaceholder = document.querySelector('.avatar-placeholder');
        if (avatarPlaceholder) {
            // Show preview
            avatarPlaceholder.style.backgroundImage = `url(${e.target.result})`;
            avatarPlaceholder.style.backgroundSize = 'cover';
            avatarPlaceholder.style.backgroundPosition = 'center';
            avatarPlaceholder.textContent = '';
            
            // Upload to server
            uploadAvatarToServer(file);
        }
    };
    reader.readAsDataURL(file);
}

async function uploadAvatarToServer(file) {
    const formData = new FormData();
    formData.append('avatar', file);
    
    try {
        showNotification('Uploading profile picture...', 'info');
        
        const response = await fetch('/api/student/upload-avatar/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData
        });
        
        if (response.ok) {
            const data = await response.json();
            showNotification('Profile picture updated successfully!', 'success');
        } else {
            throw new Error('Upload failed');
        }
    } catch (error) {
        showNotification('Failed to upload profile picture', 'error');
        console.error('Avatar upload error:', error);
    }
}

// Export for potential external use
window.StudentProfile = {
    editPersonalInfo: () => window.editPersonalInfo(),
    editAcademicInfo: () => window.editAcademicInfo(),
    addAchievement: () => window.addAchievement(),
    joinOrganization: () => window.joinOrganization(),
    exportParticipation: () => window.exportParticipation()
};
