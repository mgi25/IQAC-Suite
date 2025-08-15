// AutosaveManager handles autosaving draft proposals including dynamic fields
// and exposing hooks for reinitializing field listeners and manual saves.

window.AutosaveManager = (function() {
    let proposalId = window.PROPOSAL_ID || '';
    let timeoutId = null;
    let fields = [];

    // Unique key for this page's local storage
    const pageKey = `proposal_draft_${window.location.pathname}_new`;

    function getSavedData() {
        try {
            return JSON.parse(localStorage.getItem(pageKey) || '{}');
        } catch (e) {
            console.error('Error parsing saved draft:', e);
            return {};
        }
    }

    function collectFieldData() {
        const grouped = {};
        fields.forEach(f => {
            if (f.disabled || !f.name) return;
            (grouped[f.name] ||= []).push(f);
        });
        const data = {};
        Object.entries(grouped).forEach(([name, inputs]) => {
            const field = inputs[0];
            if (field.type === 'checkbox') {
                if (inputs.length > 1) {
                    data[name] = inputs.filter(i => i.checked).map(i => i.value);
                } else {
                    data[name] = field.checked;
                }
            } else if (field.type === 'radio') {
                const checked = inputs.find(i => i.checked);
                if (checked) data[name] = checked.value;
            } else if (field.multiple) {
                data[name] = Array.from(field.selectedOptions).map(o => o.value);
            } else {
                data[name] = field.value;
            }
        });
        return data;
    }

    function saveLocal() {
        const data = collectFieldData();
        if (proposalId) {
            data._proposal_id = proposalId;
        }
        localStorage.setItem(pageKey, JSON.stringify(data));
    }

    function clearLocal() {
        localStorage.removeItem(pageKey);
    }

    function autosaveDraft() {
        // Don't autosave for submitted proposals
        if (window.PROPOSAL_STATUS && window.PROPOSAL_STATUS !== 'draft') {
            clearLocal();
            return Promise.resolve();
        }

        const formData = collectFieldData();
        if (proposalId) {
            formData['proposal_id'] = proposalId;
        }

        document.dispatchEvent(new Event('autosave:start'));

        return fetch(window.AUTOSAVE_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.AUTOSAVE_CSRF
            },
            body: JSON.stringify(formData)
        })
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
            if (data && data.success && data.proposal_id) {
                proposalId = data.proposal_id;
                saveLocal();
                document.dispatchEvent(new Event('autosave:success'));
                return data;
            }
            return Promise.reject(data);
        })
        .catch(err => {
            document.dispatchEvent(new CustomEvent('autosave:error', {detail: err}));
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
        if (field.tagName === 'SELECT') {
            field.addEventListener('change', handler);
        }
        field.dataset.autosaveBound = 'true';
    }

    function reinitialize() {
        fields = Array.from(document.querySelectorAll('input[name], textarea[name], select[name]'));
        const saved = getSavedData();

        fields.forEach(f => {
            if (saved.hasOwnProperty(f.name)) {
                const val = saved[f.name];
                if (f.type === 'checkbox') {
                    if (Array.isArray(val)) {
                        f.checked = val.includes(f.value);
                    } else {
                        f.checked = !!val;
                    }
                } else if (f.type === 'radio') {
                    f.checked = val === f.value;
                } else if (f.multiple) {
                    const values = Array.isArray(val) ? val : [val];
                    Array.from(f.options).forEach(o => {
                        o.selected = values.includes(o.value);
                    });
                } else if (!f.value) {
                    f.value = val;
                }
            }
            bindField(f);
        });

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
        formEl.addEventListener('submit', clearLocal);
    }

    // Expose helpers globally for legacy code
    window.autosaveDraft = autosaveDraft;
    window.clearLocal = clearLocal;

    return {
        reinitialize,
        manualSave,
        autosaveDraft,
        clearLocal
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
        const res = await fetch('/suite/autosave-proposal/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.AUTOSAVE_CSRF,
            },
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

