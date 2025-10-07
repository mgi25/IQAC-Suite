// AutosaveManager handles autosaving draft proposals including dynamic fields
// and exposing hooks for reinitializing field listeners and manual saves.

window.AutosaveManager = (function() {
    let proposalId = window.PROPOSAL_ID || '';
    let timeoutId = null;
    let fields = [];
    // Sequence tracking to prevent out-of-order responses from overriding newer state
    let saveSeq = 0;
    let lastHandledSeq = 0;
    let isRestoringDynamic = false;

    // Always read the freshest CSRF value to avoid mismatches when the token
    // rotates after a login or in another tab. Prefer cookie, then <meta>,
    // then any hidden input on the page, finally fall back to window.AUTOSAVE_CSRF.
    function getCSRFToken() {
        try {
            const name = 'csrftoken=';
            const parts = document.cookie.split('; ').filter(p => p.startsWith(name));
            if (parts.length) {
                return decodeURIComponent(parts[0].slice(name.length));
            }
        } catch { /* ignore */ }
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta && meta.content) return meta.content;
        const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (input && input.value) return input.value;
        return window.AUTOSAVE_CSRF || '';
    }

    // Unique key for this page's local storage scoped per-user
    const pageKey = `proposal_draft_${window.USER_ID}_${window.location.pathname}_new`;
    const legacyPageKey = `proposal_draft_${window.location.pathname}_new`;

    function getSavedData() {
        // Read current key
        let current = {};
        try {
            current = JSON.parse(localStorage.getItem(pageKey) || '{}');
        } catch (e) {
            console.error('Error parsing saved draft:', e);
            current = {};
        }

        // If current looks fine, return it
        const hasActivities = Object.keys(current).some(k => /^activity_(?:name|date)_\d+$/.test(k));
        if (Object.keys(current).length && (hasActivities || current._proposal_id)) {
            return current;
        }

        // Fallback: search for drafts saved under a different pathname (e.g., before/after ID)
        try {
            const keys = Object.keys(localStorage);
            const prefix = `proposal_draft_${window.USER_ID}_`;
            const candidates = keys.filter(k => k.startsWith(prefix) && k.endsWith('_new') && k.includes('/emt/submit_proposal'));
            let best = null;
            for (const k of candidates) {
                if (k === pageKey) continue;
                try {
                    const data = JSON.parse(localStorage.getItem(k) || '{}');
                    if (!data || typeof data !== 'object') continue;
                    const hasAct = Object.keys(data).some(x => /^activity_(?:name|date)_\d+$/.test(x));
                    const matchesPid = data._proposal_id && window.PROPOSAL_ID && String(data._proposal_id) === String(window.PROPOSAL_ID);
                    if (!best) best = data;
                    if (matchesPid) { best = data; break; }
                    if (hasAct && !Object.keys(best).some(x => /^activity_(?:name|date)_\d+$/.test(x))) {
                        best = data;
                    }
                } catch { /* ignore */ }
            }
            if (best) {
                // Migrate to current key for consistency
                try { localStorage.setItem(pageKey, JSON.stringify(best)); } catch {}
                return best;
            }
        } catch { /* ignore */ }
        return current || {};
    }

    function migrateLegacyDraft() {
        if (legacyPageKey === pageKey) return;
        const legacyData = localStorage.getItem(legacyPageKey);
        if (legacyData) {
            if (!localStorage.getItem(pageKey)) {
                localStorage.setItem(pageKey, legacyData);
            }
            localStorage.removeItem(legacyPageKey);
        }
    }

    function collectFieldData() {
        const saved = getSavedData();
        const grouped = {};
        fields.forEach(f => {
            if (f.disabled || !f.name) return;
            if (f.closest('.speaker-item')) return; // handled separately
            (grouped[f.name] ||= []).push(f);
        });
        const data = {};
        Object.entries(grouped).forEach(([name, inputs]) => {
            const field = inputs[0];
            if (field.type === 'file') {
                return; // handled separately when sending FormData
            } else if (field.type === 'checkbox') {
                if (inputs.length > 1) {
                    const values = inputs.filter(i => i.checked).map(i => i.value);
                    if (values.length) {
                        data[name] = values;
                    }
                } else if (field.checked) {
                    data[name] = true;
                }
            } else if (field.type === 'radio') {
                const checked = inputs.find(i => i.checked);
                if (checked) data[name] = checked.value;
            } else if (field.multiple) {
                const selected = Array.from(field.selectedOptions).map(o => o.value).filter(v => v !== '');
                if (selected.length) {
                    data[name] = selected;
                }
            } else {
                // When multiple inputs share the same name (e.g. hidden Django field
                // and visible modern field), prefer a visible, non-empty value.
                const preferred = inputs.find(i => i.type !== 'hidden' && i.value.trim() !== '')
                    || inputs.find(i => i.type !== 'hidden')
                    || inputs.find(i => i.value.trim() !== '')
                    || field;
                const value = preferred.value;
                if (String(value).trim() !== '') {
                    data[name] = value;
                }
            }
        });

        // Serialize speaker groups
        const speakerEls = document.querySelectorAll('.speaker-item');
        if (speakerEls.length) {
            const speakers = Array.from(speakerEls).map(sp => ({
                name: sp.querySelector("input[name*='full_name']")?.value.trim() || '',
                designation: sp.querySelector("input[name*='designation']")?.value.trim() || '',
                bio: sp.querySelector("textarea[name*='detailed_profile']")?.value.trim() || '',
                linkedin: sp.querySelector("input[name*='linkedin_url']")?.value.trim() || '',
            })).filter(sp => Object.values(sp).some(v => v !== ''));
            if (speakers.length) {
                data.speakers = speakers;
            }
        } else if (Array.isArray(saved.speakers) && saved.speakers.length) {
            data.speakers = saved.speakers;
        }

        // Merge any previously saved values for fields not currently present
        Object.entries(saved).forEach(([key, val]) => {
            if (!['_proposal_id', 'speakers'].includes(key) && data[key] === undefined) {
                const prefixes = ['speaker_', 'activity_', 'expense_', 'income_'];
                if (prefixes.some(p => key.startsWith(p)) && !document.querySelector(`[name="${key}"]`)) {
                    return; // ignore stale dynamic field data
                }
                data[key] = val;
            }
        });

        // Map generic 'content' field to a specific section if configured.
        if (data.content !== undefined && window.AUTOSAVE_SECTION) {
            data[window.AUTOSAVE_SECTION] = data.content;
        }
        return data;
    }

    function saveLocal() {
        const data = collectFieldData();
        if (data.hasOwnProperty('flow') && data.flow === '[]') {
            data.flow = '';
        }
        if (proposalId) {
            data._proposal_id = proposalId;
        }
        localStorage.setItem(pageKey, JSON.stringify(data));
    }

    function clearLocal() {
        localStorage.removeItem(pageKey);
        localStorage.removeItem(legacyPageKey);
    }

    function autosaveDraft() {
        const seq = ++saveSeq;
        // Don't autosave for submitted proposals
        if (window.PROPOSAL_STATUS && window.PROPOSAL_STATUS !== 'draft') {
            clearLocal();
            return Promise.resolve();
        }

        const formData = collectFieldData();
        if (proposalId) {
            formData['proposal_id'] = proposalId;
        }

        const formEl = document.querySelector('form');
        const hasFile = formEl && Array.from(formEl.querySelectorAll('input[type="file"]')).some(f => f.files.length > 0);

    document.dispatchEvent(new Event('autosave:start'));

        const headers = { 'X-CSRFToken': getCSRFToken() };
        const options = {
            method: 'POST',
            headers,
            credentials: 'same-origin',
        };

        if (hasFile) {
            const body = new FormData();
            Object.entries(formData).forEach(([k, v]) => {
                if (Array.isArray(v)) {
                    v.forEach(val => body.append(k, val));
                } else {
                    body.append(k, v);
                }
            });
            Array.from(formEl.querySelectorAll('input[type="file"]')).forEach(inp => {
                if (inp.files.length > 0) {
                    body.append(inp.name, inp.files[0]);
                }
            });
            options.body = body;
        } else {
            headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(formData);
        }

        return fetch(window.AUTOSAVE_URL, options)
        .then(async res => {
            let data = null;
            try {
                data = await res.json();
            } catch (e) {
                // ignore JSON parse errors
            }
            if (!res.ok) {
                return Promise.reject(data || res.status);
            }
            return data;
        })
        .then(data => {
            if (data && data.proposal_id) {
                // Only update UI/events if this response is not stale
                if (seq >= lastHandledSeq) {
                    lastHandledSeq = seq;
                    proposalId = data.proposal_id;
                    window.PROPOSAL_ID = data.proposal_id;
                    saveLocal();
                    document.dispatchEvent(new CustomEvent('autosave:success', {
                        detail: { proposalId: data.proposal_id, errors: data.errors, success: data.success }
                    }));
                }
                return data;
            }
            return Promise.reject(data);
        })
        .catch(err => {
            // Only dispatch error if this response is not stale
            if (seq >= lastHandledSeq) {
                lastHandledSeq = seq;
                document.dispatchEvent(new CustomEvent('autosave:error', {detail: err}));
            }
            return Promise.reject(err);
        });
    }

    function bindField(field) {
        if (field.dataset.autosaveBound) return;
        const handler = () => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                autosaveDraft().catch(() => {});
                saveLocal();
            }, 1000);
        };
        field.addEventListener('input', handler);
        // Some inputs (e.g. date pickers or custom widgets) may not fire
        // `input` events reliably when their value changes. Bind to the
        // `change` event for all fields so autosave is triggered even when
        // users select a date or pick values via a custom UI like TomSelect.
        field.addEventListener('change', handler);
        field.dataset.autosaveBound = 'true';
    }

    function ensureDynamicFieldGroups(saved) {
        const dynamicGroups = [
            {
                regex: /^expense_[^_]+_(\d+)$/,
                addButtonId: 'add-expense-btn',
                containerSelector: '#expense-rows',
                rowSelector: '.expense-form-container'
            },
            {
                regex: /^income_[^_]+_(\d+)$/,
                addButtonId: 'add-income-btn',
                containerSelector: '#income-rows',
                rowSelector: '.income-form-container'
            }
        ];

        dynamicGroups.forEach(group => {
            const { regex, addButtonId, containerSelector, rowSelector } = group;
            const keys = Object.keys(saved);
            let maxIndex = -1;
            keys.forEach(key => {
                const match = key.match(regex);
                if (!match) return;
                const idx = parseInt(match[1], 10);
                if (!Number.isNaN(idx)) {
                    maxIndex = Math.max(maxIndex, idx);
                }
            });

            if (maxIndex < 0) {
                return;
            }

            const addBtn = document.getElementById(addButtonId);
            const container = document.querySelector(containerSelector);
            if (!addBtn || !container) {
                return;
            }

            const required = maxIndex + 1;
            let existing = container.querySelectorAll(rowSelector).length;
            if (existing >= required) {
                return;
            }

            // Ensure the section scripts finished wiring up the add button before we trigger it.
            if (addBtn.dataset.listenerAttached !== 'true') {
                return;
            }

            isRestoringDynamic = true;
            try {
                while (existing < required) {
                    addBtn.click();
                    existing += 1;
                }
            } finally {
                isRestoringDynamic = false;
            }
        });
    }

    function reinitialize() {
        if (isRestoringDynamic) {
            return;
        }
        migrateLegacyDraft();
        const saved = getSavedData();

        ensureDynamicFieldGroups(saved);
        fields = Array.from(document.querySelectorAll('input[name], textarea[name], select[name]'));

        fields.forEach(f => {
            if (f.closest('.speaker-item')) {
                bindField(f);
                return; // speaker fields handled separately
            }
            if (saved.hasOwnProperty(f.name)) {
                const val = saved[f.name];
                if (f.name === 'flow' && (val === '' || val === '[]')) {
                    f.value = '';
                } else if (f.type === 'checkbox') {
                    if (Array.isArray(val)) {
                        f.checked = val.includes(f.value);
                    } else {
                        f.checked = !!val;
                    }
                } else if (f.type === 'radio') {
                    f.checked = val === f.value;
                } else if (f.multiple) {
                    const values = Array.isArray(val) ? val : [val];
                    if (f.options.length === 0) {
                        values.forEach(v => {
                            // create option placeholders so value persists even without preset options
                            const opt = new Option(v, v, true, true);
                            f.add(opt);
                        });
                    } else {
                        Array.from(f.options).forEach(o => {
                            o.selected = values.includes(o.value);
                        });
                    }
                } else {
                    f.value = val;
                }
                f.dispatchEvent(new Event('change', { bubbles: true }));
            }
            bindField(f);
        });

        if (Array.isArray(saved.speakers) && saved.speakers.length) {
            const addSpeaker = window.addSpeaker;
            let speakerEls = document.querySelectorAll('.speaker-item');
            for (let i = speakerEls.length; i < saved.speakers.length; i++) {
                if (typeof addSpeaker === 'function') addSpeaker();
            }
            speakerEls = document.querySelectorAll('.speaker-item');
            speakerEls.forEach((el, idx) => {
                const sp = saved.speakers[idx];
                if (!sp) return;
                const setVal = (selector, val) => {
                    const field = el.querySelector(selector);
                    if (field) {
                        field.value = val || '';
                        field.dispatchEvent(new Event('change', { bubbles: true }));
                        bindField(field);
                    }
                };
                setVal("input[name*='full_name']", sp.name);
                setVal("input[name*='designation']", sp.designation);
                setVal("textarea[name*='detailed_profile']", sp.bio);
                setVal("input[name*='linkedin_url']", sp.linkedin);
            });
        }

        if (saved._proposal_id && !proposalId) {
            proposalId = saved._proposal_id;
        }

        // Clear local storage immediately if this is a submitted proposal
        if (window.PROPOSAL_STATUS && window.PROPOSAL_STATUS !== 'draft') {
            clearLocal();
        }
    }

    function manualSave() {
        saveLocal();
        return autosaveDraft();
    }

    // Initial setup
    reinitialize();

    const formEl = document.querySelector('form');
    if (formEl) {
        formEl.addEventListener('submit', () => {
            // Sync hidden input with freshest cookie token just before submit
            const csrfInput = formEl.querySelector('input[name="csrfmiddlewaretoken"]');
            if (csrfInput) csrfInput.value = getCSRFToken();
            clearLocal();
        });
    }

    // Expose helpers globally for legacy code
    window.autosaveDraft = autosaveDraft;
    window.clearLocal = clearLocal;

    return {
        reinitialize,
        manualSave,
        autosaveDraft,
        clearLocal,
        // Expose a read-only snapshot of saved draft values so other modules
        // (e.g., dynamic field renderers) can hydrate UI when the server
        // hasn't yet persisted those values.
        getSavedDraft: () => {
            try { return JSON.parse(localStorage.getItem(pageKey) || '{}'); }
            catch { return {}; }
        }
    };
})();

// Simple autosave helper used by AI generation
async function autosave() {
    try {
        const form = document.querySelector('form');
        const formData = new FormData(form);
        const payload = {};
        formData.forEach((value, key) => {
            if (payload[key] !== undefined) {
                if (!Array.isArray(payload[key])) {
                    payload[key] = [payload[key]];
                }
                payload[key].push(value);
            } else {
                payload[key] = value;
            }
        });
        const res = await fetch(window.AUTOSAVE_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': (typeof getCSRFToken === 'function' ? getCSRFToken() : (window.AUTOSAVE_CSRF || '')),
            },
            credentials: 'same-origin',
            body: JSON.stringify(payload),
        });
        if (!res.ok) {
            console.warn('autosave failed', res.status);
        }
    } catch (e) {
        console.warn('autosave exception', e);
    }
}
window.autosave = autosave;

