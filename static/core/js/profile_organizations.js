(function (window, document) {
    const defaultEndpoints = {
        types: '/api/student/organization-types/',
        organizations: '/api/student/organizations/',
        join: '/api/student/join-organization/',
        leave(orgId) {
            return `/api/student/leave-organization/${orgId}/`;
        }
    };

    const defaultSelectors = {
        organizationList: '#organization-list',
        organizationListContainer: '#organizations .organization-panel .card-body',
        organizationEmpty: '#organizations .empty-state-condensed',
        joinRequestsList: '#join-requests-list',
        joinRequestsEmpty: '#join-requests-empty'
    };

    const state = {
        initialized: false,
        role: 'student',
        endpoints: { ...defaultEndpoints },
        selectors: { ...defaultSelectors },
        joinRequests: [],
        modal: null,
        previousFocus: null,
        focusTrapHandler: null,
        onMembershipChange: null,
        statLabel: 'ORGANIZATIONS',
        joinRequestsScriptId: 'join-requests-data'
    };

    function initialize(options = {}) {
        state.role = options.role ? String(options.role).toLowerCase() : state.role;
        state.endpoints = {
            ...defaultEndpoints,
            ...(options.endpoints || {})
        };
        state.selectors = {
            ...defaultSelectors,
            ...(options.selectors || {})
        };
        state.statLabel = options.statLabel === null ? null : (options.statLabel || state.statLabel);
        state.onMembershipChange = typeof options.onMembershipChange === 'function' ? options.onMembershipChange : null;
        state.joinRequestsScriptId = options.joinRequestsScriptId || state.joinRequestsScriptId;

        state.organizationListEl = query(options.organizationListSelector || state.selectors.organizationList);
        state.organizationListContainerEl = query(options.organizationListContainerSelector || state.selectors.organizationListContainer);
        state.organizationEmptyEl = query(options.organizationEmptySelector || state.selectors.organizationEmpty);
        state.joinRequestsListEl = query(options.joinRequestsListSelector || state.selectors.joinRequestsList);
        state.joinRequestsEmptyEl = query(options.joinRequestsEmptySelector || state.selectors.joinRequestsEmpty);

        hydrateJoinRequests();
        applyJoinRequestStates();
        updateOrganizationsStat(getOrganizationCount());

        state.initialized = true;
    }

    function query(selector) {
        if (!selector) {
            return null;
        }
        try {
            return document.querySelector(selector);
        } catch (error) {
            console.warn('ProfileOrganizations: invalid selector', selector, error);
            return null;
        }
    }

    function hydrateJoinRequests() {
        const script = document.getElementById(state.joinRequestsScriptId);
        if (!script) {
            renderJoinRequests([]);
            return;
        }

        try {
            const raw = script.textContent || '[]';
            const parsed = JSON.parse(raw);
            state.joinRequests = Array.isArray(parsed) ? parsed : [];
        } catch (error) {
            console.error('ProfileOrganizations: failed to parse join requests payload', error);
            state.joinRequests = [];
        }

        renderJoinRequests(state.joinRequests);
    }

    function renderJoinRequests(items) {
        const listEl = state.joinRequestsListEl;
        const emptyEl = state.joinRequestsEmptyEl;

        if (!listEl || !emptyEl) {
            return;
        }

        if (!items || items.length === 0) {
            listEl.innerHTML = '';
            listEl.setAttribute('hidden', 'hidden');
            emptyEl.removeAttribute('hidden');
            emptyEl.style.display = '';
            applyJoinRequestStates();
            return;
        }

        listEl.innerHTML = items.map(joinRequestCardTemplate).join('');
        listEl.removeAttribute('hidden');
        emptyEl.setAttribute('hidden', 'hidden');
        emptyEl.style.display = 'none';
        applyJoinRequestStates();
    }

    function joinRequestCardTemplate(item) {
        const organizationName = escapeHtml(item?.organization?.name || 'Organization');
        const requestType = (item?.request_type || 'join').toLowerCase();
        const typeDisplay = escapeHtml(
            item?.request_type_display
            || (requestType === 'leave' ? 'Leave' : 'Join')
        );

        const rawStatus = item?.status === 'Pending' && item?.is_seen
            ? 'Seen'
            : (item?.status_display || item?.status || 'Pending');
        const statusLabel = escapeHtml(rawStatus);
        const badgeClass = joinRequestStatusClass(rawStatus);
        const requestedDisplay = escapeHtml(item?.requested_display || 'Unknown');
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

    function joinRequestStatusClass(status) {
        if (!status) {
            return 'pending';
        }
        return String(status).toLowerCase().replace(/[^a-z0-9]+/g, '-');
    }

    function applyJoinRequestStates() {
        const list = ensureOrganizationList(false);
        if (!list) {
            return;
        }

        list.querySelectorAll('.organization-list-item').forEach(row => {
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

        const pendingLeave = (state.joinRequests || []).filter(item => {
            if (!item || !item.organization) {
                return false;
            }
            const type = String(item.request_type || '').toLowerCase();
            const status = String(item.status || '');
            return type === 'leave' && status === 'Pending';
        });

        pendingLeave.forEach(item => {
            const orgId = item.organization?.id;
            if (!orgId) {
                return;
            }
            const row = list.querySelector(`.organization-list-item[data-org-id="${orgId}"]`);
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

    function openJoinModal() {
        if (state.modal) {
            closeModal(true);
        }

        const modal = document.createElement('div');
        modal.className = 'edit-modal join-organization-modal';
        modal.innerHTML = `
            <div class="modal-backdrop" data-modal-backdrop></div>
            <div class="modal-content" role="dialog" aria-modal="true" aria-labelledby="join-organization-title">
                <div class="modal-header">
                    <h3 id="join-organization-title">Join Organization</h3>
                    <button type="button" class="modal-close" data-modal-close aria-label="Close">&times;</button>
                </div>
                <div class="modal-body">
                    <p class="modal-description">Select an organization type to see available groups you can join.</p>
                    <form class="edit-form" data-join-form>
                        <div class="form-group">
                            <label for="organization-type-select">Organization Type</label>
                            <select id="organization-type-select" name="organization_type_id" required>
                                <option value="">Loading types...</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="organization-select">Organization</label>
                            <select id="organization-select" name="organization_id" required disabled>
                                <option value="">Select organization</option>
                            </select>
                            <p class="form-help" data-org-feedback>Choose an organization type to continue.</p>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-modal-cancel>Cancel</button>
                    <button type="button" class="btn btn-primary" data-modal-save disabled>Join Organization</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        document.body.classList.add('modal-open');

        state.modal = modal;
        state.previousFocus = document.activeElement;

        const backdrop = modal.querySelector('[data-modal-backdrop]');
        const closeButton = modal.querySelector('[data-modal-close]');
        const cancelButton = modal.querySelector('[data-modal-cancel]');
        const saveButton = modal.querySelector('[data-modal-save]');
        const form = modal.querySelector('[data-join-form]');
        const typeSelect = form.querySelector('select[name="organization_type_id"]');
        const orgSelect = form.querySelector('select[name="organization_id"]');
        const feedback = form.querySelector('[data-org-feedback]');

        const closeHandler = () => closeModal();
        if (backdrop) {
            backdrop.addEventListener('click', event => {
                if (event.target === backdrop) {
                    closeModal();
                }
            });
        }
        if (closeButton) {
            closeButton.addEventListener('click', closeHandler);
        }
        if (cancelButton) {
            cancelButton.addEventListener('click', closeHandler);
        }

        if (form) {
            form.addEventListener('submit', event => event.preventDefault());
        }

        if (saveButton) {
            saveButton.addEventListener('click', () => submitJoinRequest(orgSelect, saveButton));
        }

        if (modal) {
            const focusableSelector = 'a[href], button:not([disabled]), textarea, input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';
            const focusable = modal.querySelectorAll(focusableSelector);
            const firstFocusable = focusable[0];
            const lastFocusable = focusable[focusable.length - 1];

            state.focusTrapHandler = event => {
                if (event.key !== 'Tab') {
                    if (event.key === 'Escape') {
                        closeModal();
                    }
                    return;
                }
                if (!firstFocusable || !lastFocusable) {
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

            modal.addEventListener('keydown', state.focusTrapHandler);
            setTimeout(() => {
                if (firstFocusable) {
                    firstFocusable.focus();
                }
            }, 60);
        }

        const setOrgFeedback = (message, tone = 'info') => {
            if (!feedback) {
                return;
            }
            feedback.textContent = message;
            feedback.dataset.tone = tone;
        };

        const setSelectOptions = (selectEl, options, placeholder) => {
            if (!selectEl) {
                return;
            }
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

        const loadOrganizationTypes = async () => {
            setSelectOptions(typeSelect, [], 'Loading types...');
            if (typeSelect) {
                typeSelect.disabled = true;
            }
            try {
                const payload = await fetchJson(withRole(state.endpoints.types));
                const options = (payload.types || []).map(item => ({
                    value: String(item.id),
                    label: item.name
                }));
                if (options.length === 0) {
                    setSelectOptions(typeSelect, [], 'No organization types available');
                    setOrgFeedback('No organization types are available right now.', 'warning');
                    if (saveButton) {
                        saveButton.disabled = true;
                    }
                } else {
                    setSelectOptions(typeSelect, options, 'Select organization type');
                    if (typeSelect) {
                        typeSelect.disabled = false;
                    }
                    setOrgFeedback('Select a type to see available organizations.');
                }
            } catch (error) {
                notify(error.message || 'Failed to load organization types.', 'error');
                closeModal();
            }
        };

        const loadOrganizations = async typeId => {
            if (!typeId) {
                setSelectOptions(orgSelect, [], 'Select organization');
                if (orgSelect) {
                    orgSelect.disabled = true;
                }
                if (saveButton) {
                    saveButton.disabled = true;
                }
                setOrgFeedback('Select an organization type to continue.');
                return;
            }

            if (orgSelect) {
                orgSelect.disabled = true;
            }
            if (saveButton) {
                saveButton.disabled = true;
            }
            setSelectOptions(orgSelect, [], 'Loading organizations...');
            setOrgFeedback('Loading organizations...', 'info');

            try {
                const url = withRole(`${state.endpoints.organizations}?type_id=${encodeURIComponent(typeId)}`);
                const payload = await fetchJson(url);
                const organizations = payload.organizations || [];
                if (organizations.length === 0) {
                    setSelectOptions(orgSelect, [], 'No organizations available');
                    setOrgFeedback('No organizations found for this type.', 'warning');
                    return;
                }
                const options = organizations.map(item => ({
                    value: String(item.id),
                    label: item.name
                }));
                setSelectOptions(orgSelect, options, 'Select organization');
                if (orgSelect) {
                    orgSelect.disabled = false;
                }
                setOrgFeedback('Select an organization to join.');
            } catch (error) {
                setSelectOptions(orgSelect, [], 'Select organization');
                setOrgFeedback('Failed to load organizations. Please try again.', 'error');
            }
        };

        if (typeSelect) {
            typeSelect.addEventListener('change', event => {
                loadOrganizations(event.target.value);
            });
        }

        if (orgSelect) {
            orgSelect.addEventListener('change', () => {
                if (saveButton) {
                    saveButton.disabled = !orgSelect.value;
                }
            });
        }

        loadOrganizationTypes();
    }

    function closeModal(skipFocusRestore = false) {
        const modal = state.modal;
        if (!modal) {
            return;
        }

        if (state.focusTrapHandler) {
            modal.removeEventListener('keydown', state.focusTrapHandler);
            state.focusTrapHandler = null;
        }

        modal.remove();
        state.modal = null;
        document.body.classList.remove('modal-open');

        if (!skipFocusRestore && state.previousFocus && typeof state.previousFocus.focus === 'function') {
            try {
                state.previousFocus.focus();
            } catch (error) {
                /* no-op */
            }
        }
        state.previousFocus = null;
    }

    async function submitJoinRequest(orgSelect, saveButton) {
        if (!orgSelect || !orgSelect.value) {
            notify('Please select an organization to join.', 'warning');
            return;
        }

        if (saveButton) {
            saveButton.disabled = true;
        }

        const payload = {
            organization_id: Number(orgSelect.value),
            role: state.role
        };

        try {
            const response = await fetch(state.endpoints.join, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(payload)
            });

            const data = await parseJsonResponse(response);
            if (!response.ok || data.success === false) {
                throw new Error(data.message || 'Failed to submit join request.');
            }

            if (data.join_request) {
                addOrUpdateJoinRequestCard(data.join_request);
            }
            if (data.organization) {
                addOrUpdateOrganizationCard(data.organization);
            }

            notify(data.message || 'Join request submitted for approval.', 'success');
            closeModal();
            if (typeof state.onMembershipChange === 'function') {
                state.onMembershipChange({ action: 'join', data });
            }
        } catch (error) {
            notify(error.message || 'Failed to submit join request.', 'error');
            if (saveButton) {
                saveButton.disabled = false;
            }
        }
    }

    async function requestLeave(orgId) {
        if (!orgId) {
            return;
        }

        const url = withRole(state.endpoints.leave(orgId));
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            const data = await parseJsonResponse(response);
            if (!response.ok || data.success === false) {
                throw new Error(data.message || 'Failed to submit leave request.');
            }

            if (data.join_request) {
                addOrUpdateJoinRequestCard(data.join_request);
            }

            notify(data.message || 'Leave request submitted for approval.', 'success');
            if (typeof state.onMembershipChange === 'function') {
                state.onMembershipChange({ action: 'leave', data });
            }
        } catch (error) {
            notify(error.message || 'Failed to submit leave request.', 'error');
        }
    }

    function addOrUpdateJoinRequestCard(request) {
        if (!request) {
            return;
        }

        if (!Array.isArray(state.joinRequests)) {
            state.joinRequests = [];
        }

        const index = state.joinRequests.findIndex(item => String(item.id) === String(request.id));
        if (index !== -1) {
            state.joinRequests[index] = request;
        } else {
            state.joinRequests = [request, ...state.joinRequests];
        }

        renderJoinRequests(state.joinRequests);
    }

    function addOrUpdateOrganizationCard(org) {
        if (!org) {
            return;
        }

        const list = ensureOrganizationList(true);
        if (!list) {
            return;
        }

        if (state.organizationEmptyEl) {
            state.organizationEmptyEl.setAttribute('hidden', 'hidden');
            state.organizationEmptyEl.style.display = 'none';
        }

        const existingRow = list.querySelector(`[data-org-id="${org.id}"]`);
        const markup = organizationCardTemplate(org);
        if (existingRow) {
            existingRow.outerHTML = markup;
        } else {
            list.insertAdjacentHTML('afterbegin', markup);
        }

        applyJoinRequestStates();
        updateOrganizationsStat(getOrganizationCount());
    }

    function removeOrganizationCard(orgId) {
        const list = ensureOrganizationList(false);
        if (!list) {
            return false;
        }

        const row = list.querySelector(`.organization-list-item[data-org-id="${orgId}"]`);
        if (!row) {
            return false;
        }

        row.remove();
        const remaining = getOrganizationCount();
        updateOrganizationsStat(remaining);

        if (remaining === 0 && state.organizationEmptyEl) {
            state.organizationEmptyEl.removeAttribute('hidden');
            state.organizationEmptyEl.style.display = '';
        }

        return true;
    }

    function organizationCardTemplate(org) {
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

    function ensureOrganizationList(createIfMissing = false) {
        let list = state.organizationListEl;
        if (list) {
            return list;
        }

        if (!createIfMissing) {
            return null;
        }

        const container = state.organizationListContainerEl || query(state.selectors.organizationListContainer);
        if (!container) {
            return null;
        }

        list = document.createElement('div');
        list.id = 'organization-list';
        list.className = 'organization-list';
        container.insertBefore(list, container.firstChild);

        state.organizationListEl = list;
        return list;
    }

    function getOrganizationCount() {
        const list = ensureOrganizationList(false);
        if (!list) {
            return 0;
        }
        return list.querySelectorAll('.organization-list-item').length;
    }

    function updateOrganizationsStat(count) {
        if (!state.statLabel) {
            return;
        }
        document.querySelectorAll('.stat-card').forEach(card => {
            const label = card.querySelector('.stat-label');
            if (label && label.textContent.trim() === state.statLabel) {
                const number = card.querySelector('.stat-number');
                if (number) {
                    number.textContent = count != null ? count : 0;
                }
            }
        });
    }

    function fetchJson(url, options = {}) {
        return fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            ...options
        }).then(async response => {
            const data = await parseJsonResponse(response);
            if (!response.ok || data.success === false) {
                const message = data.message || 'Request failed.';
                const error = new Error(message);
                error.response = data;
                throw error;
            }
            return data;
        });
    }

    async function parseJsonResponse(response) {
        try {
            const payloadText = await response.text();
            return payloadText ? JSON.parse(payloadText) : {};
        } catch (error) {
            return {};
        }
    }

    function withRole(url) {
        if (!state.role) {
            return url;
        }
        const separator = url.includes('?') ? '&' : '?';
        return `${url}${separator}role=${encodeURIComponent(state.role)}`;
    }

    function getCsrfToken() {
        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfInput && csrfInput.value) {
            return csrfInput.value;
        }
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') || '' : '';
    }

    function notify(message, type = 'info', duration = 5000) {
        if (window.ProfilePage && typeof window.ProfilePage.showNotification === 'function') {
            window.ProfilePage.showNotification(message, type, duration);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
            if (type === 'error') {
                alert(message);
            }
        }
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

    window.ProfileOrganizations = {
        initialize,
        openJoinModal,
        closeModal,
        requestLeave,
        addOrUpdateJoinRequestCard,
        addOrUpdateOrganizationCard,
        removeOrganizationCard,
        applyJoinRequestStates,
        getJoinRequests() {
            return Array.isArray(state.joinRequests) ? [...state.joinRequests] : [];
        }
    };
})(window, document);
