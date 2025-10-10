(function(window, document) {
    const proposalId = window.PROPOSAL_ID;
    const liveStateUrl = window.PROPOSAL_LIVE_STATE_URL;
    if (!proposalId || !liveStateUrl) {
        return;
    }

    const POLL_INTERVAL = 4000;
    let lastTimestamp = window.PROPOSAL_LAST_UPDATED || null;
    let isPolling = false;
    let timerId = null;

    const ACTIVE_TAGS = new Set(["INPUT", "TEXTAREA"]);

    function modernSelector(name) {
        return `#${name.replace(/_/g, '-')}-modern`;
    }

    function arraysEqual(a, b) {
        if (a.length !== b.length) return false;
        const sortedA = a.slice().sort();
        const sortedB = b.slice().sort();
        for (let i = 0; i < sortedA.length; i += 1) {
            if (sortedA[i] !== sortedB[i]) return false;
        }
        return true;
    }

    function normalizeToArray(value) {
        if (value === null || value === undefined) return [];
        if (Array.isArray(value)) {
            return value.map(v => (v === null || v === undefined) ? '' : String(v));
        }
        const str = String(value);
        return str ? [str] : [];
    }

    function setElementValue(el, value, options = {}) {
        if (!el) return false;
        const { skipActiveCheck = false } = options;
        if (!skipActiveCheck && document.activeElement === el && ACTIVE_TAGS.has(el.tagName)) {
            return false;
        }

        if (el.tomselect) {
            const desired = normalizeToArray(value);
            let current = el.tomselect.getValue();
            if (!Array.isArray(current)) {
                current = current ? [String(current)] : [];
            } else {
                current = current.map(String);
            }
            if (arraysEqual(current, desired)) {
                return false;
            }
            desired.forEach(val => {
                if (!el.tomselect.options[val]) {
                    el.tomselect.addOption({ id: val, value: val, text: val });
                }
            });
            if (el.tomselect.settings.maxItems === 1) {
                el.tomselect.setValue(desired[0] || '', true);
            } else {
                el.tomselect.setValue(desired, true);
            }
            return true;
        }

        if (el.type === 'checkbox') {
            const boolValue = Boolean(value);
            if (el.checked === boolValue) {
                return false;
            }
            el.checked = boolValue;
            el.dispatchEvent(new Event('change', { bubbles: true }));
            return true;
        }

        if (el.multiple) {
            const desired = normalizeToArray(value);
            const current = Array.from(el.selectedOptions || []).map(opt => opt.value);
            if (arraysEqual(current, desired)) {
                return false;
            }
            Array.from(el.options || []).forEach(opt => {
                opt.selected = desired.includes(opt.value);
            });
            el.dispatchEvent(new Event('change', { bubbles: true }));
            return true;
        }

        const strValue = value === null || value === undefined ? '' : String(value);
        if ((el.value ?? '') === strValue) {
            return false;
        }
        el.value = strValue;
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        return true;
    }

    function updateField(name, value) {
        const modern = document.querySelector(modernSelector(name));
        if (modern) {
            setElementValue(modern, value);
        }
        const hiddenSelector = `#django-forms [name="${name}"]`;
        document.querySelectorAll(hiddenSelector).forEach(field => {
            setElementValue(field, value, { skipActiveCheck: true });
        });
        const basicSelector = `#django-basic-info [name="${name}"]`;
        document.querySelectorAll(basicSelector).forEach(field => {
            setElementValue(field, value, { skipActiveCheck: true });
        });
    }

    function updateRichField(field, text) {
        const normalized = text === null || text === undefined ? '' : String(text);
        const fieldId = `id_${field}`;

        if (window.CKEDITOR && CKEDITOR.instances[fieldId]) {
            if (CKEDITOR.instances[fieldId].getData() !== normalized) {
                CKEDITOR.instances[fieldId].setData(normalized);
            }
            return;
        }
        if (window.ClassicEditor && window._editors && window._editors[field]) {
            const editor = window._editors[field];
            if (editor.getData && editor.getData() !== normalized) {
                editor.setData(normalized);
            }
            return;
        }
        if (window.tinymce && tinymce.get(fieldId)) {
            if (tinymce.get(fieldId).getContent({ format: 'raw' }) !== normalized) {
                tinymce.get(fieldId).setContent(normalized);
            }
            return;
        }
        if (window.Quill && window._quills && window._quills[field]) {
            const quill = window._quills[field];
            const current = quill.getText().trim();
            if (current !== normalized.trim()) {
                quill.setText('');
                quill.clipboard.dangerouslyPasteHTML(0, normalized);
            }
            return;
        }

        const el = document.getElementById(fieldId);
        if (el) {
            setElementValue(el, normalized, { skipActiveCheck: true });
        }
    }

    function updateTextSection(name, value) {
        const normalized = value === null || value === undefined ? '' : String(value);
        const modern = document.querySelector(modernSelector(name));
        if (modern) {
            setElementValue(modern, normalized);
        }
        updateRichField(name, normalized);
        if (name === 'flow') {
            const flowTextarea = document.querySelector('textarea[name="flow"]');
            if (flowTextarea) {
                setElementValue(flowTextarea, normalized, { skipActiveCheck: true });
            }
        }
    }

    function applyPayload(payload) {
        if (!payload || typeof payload !== 'object') {
            return;
        }
        if (payload.fields && typeof payload.fields === 'object') {
            Object.entries(payload.fields).forEach(([name, value]) => {
                updateField(name, value);
            });
        }
        if (payload.text_sections && typeof payload.text_sections === 'object') {
            Object.entries(payload.text_sections).forEach(([name, value]) => {
                updateTextSection(name, value);
            });
        }
        if (Array.isArray(payload.activities)) {
            window.EXISTING_ACTIVITIES = payload.activities.map(item => ({ ...item }));
            if (window.ProposalRealtime && typeof window.ProposalRealtime.updateActivities === 'function') {
                window.ProposalRealtime.updateActivities(payload.activities);
            }
        }
        if (Array.isArray(payload.speakers)) {
            window.EXISTING_SPEAKERS = payload.speakers.map(item => ({ ...item }));
            if (window.ProposalRealtime && typeof window.ProposalRealtime.updateSpeakers === 'function') {
                window.ProposalRealtime.updateSpeakers(payload.speakers);
            }
        }
        if (Array.isArray(payload.expenses)) {
            window.EXISTING_EXPENSES = payload.expenses.map(item => ({ ...item }));
            if (window.ProposalRealtime && typeof window.ProposalRealtime.updateExpenses === 'function') {
                window.ProposalRealtime.updateExpenses(payload.expenses);
            }
        }
        if (Array.isArray(payload.income)) {
            window.EXISTING_INCOME = payload.income.map(item => ({ ...item }));
            if (window.ProposalRealtime && typeof window.ProposalRealtime.updateIncome === 'function') {
                window.ProposalRealtime.updateIncome(payload.income);
            }
        }
        if (Array.isArray(payload.sdg_goals)) {
            if (window.ProposalRealtime && typeof window.ProposalRealtime.updateSdgGoals === 'function') {
                window.ProposalRealtime.updateSdgGoals(payload.sdg_goals);
            }
        }
        if (Array.isArray(payload.faculty_incharges)) {
            if (window.ProposalRealtime && typeof window.ProposalRealtime.updateFacultyIncharges === 'function') {
                window.ProposalRealtime.updateFacultyIncharges(payload.faculty_incharges);
            }
        }
    }

    async function poll() {
        if (isPolling || document.hidden) {
            return;
        }
        isPolling = true;
        try {
            const params = new URLSearchParams();
            if (lastTimestamp) {
                params.set('since', lastTimestamp);
            }
            const url = params.toString()
                ? `${liveStateUrl}?${params.toString()}`
                : liveStateUrl;
            const response = await fetch(url, {
                credentials: 'same-origin',
                headers: { Accept: 'application/json' },
            });
            if (!response.ok) {
                throw new Error(`Live sync request failed (${response.status})`);
            }
            const data = await response.json();
            if (data && typeof data === 'object') {
                if (data.updated_at) {
                    lastTimestamp = data.updated_at;
                }
                if (data.changed && data.payload) {
                    applyPayload(data.payload);
                }
            }
        } catch (err) {
            console.warn('Proposal live sync failed:', err);
        } finally {
            isPolling = false;
        }
    }

    function startPolling() {
        if (timerId) {
            clearInterval(timerId);
        }
        timerId = setInterval(poll, POLL_INTERVAL);
        poll();
    }

    function stopPolling() {
        if (!timerId) return;
        clearInterval(timerId);
        timerId = null;
    }

    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            stopPolling();
        } else {
            startPolling();
        }
    });

    document.addEventListener('autosave:success', () => {
        if (!timerId) {
            startPolling();
        }
    });

    startPolling();
})(window, document);
