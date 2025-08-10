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

    function saveLocal() {
        const data = {};
        fields.forEach(f => {
            if (!f.disabled && f.name) {
                if (f.type === 'checkbox' || f.type === 'radio') {
                    data[f.name] = f.checked;
                } else if (f.multiple) {
                    data[f.name] = Array.from(f.selectedOptions).map(o => o.value);
                } else {
                    data[f.name] = f.value;
                }
            }
        });
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
            return;
        }

        const formData = {};
        fields.forEach(f => {
            if (!f.disabled && f.name) {
                if (f.type === 'checkbox' || f.type === 'radio') {
                    formData[f.name] = f.checked;
                } else if (f.multiple) {
                    formData[f.name] = Array.from(f.selectedOptions).map(o => o.value);
                } else {
                    formData[f.name] = f.value;
                }
            }
        });
        if (proposalId) {
            formData['proposal_id'] = proposalId;
        }

        fetch(window.AUTOSAVE_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.AUTOSAVE_CSRF
            },
            body: JSON.stringify(formData)
        })
        .then(res => res.json())
        .then(data => {
            if (data.success && data.proposal_id) {
                proposalId = data.proposal_id;
                saveLocal();
            }
        })
        .catch(err => console.error('Autosave error:', err));
    }

    function bindField(field) {
        if (field.dataset.autosaveBound) return;
        const handler = () => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                autosaveDraft();
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
            // Load saved data for new fields if empty
            if (saved.hasOwnProperty(f.name)) {
                if (f.type === 'checkbox' || f.type === 'radio') {
                    f.checked = saved[f.name];
                } else if (f.multiple) {
                    const values = saved[f.name] || [];
                    Array.from(f.options).forEach(o => {
                        o.selected = values.includes(o.value);
                    });
                } else if (!f.value) {
                    f.value = saved[f.name];
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
        autosaveDraft();
        saveLocal();
    }

    // Initial setup
    reinitialize();

    const formEl = document.querySelector('form');
    if (formEl) {
        formEl.addEventListener('submit', clearLocal);
    }

    return {
        reinitialize,
        manualSave
    };
})();

