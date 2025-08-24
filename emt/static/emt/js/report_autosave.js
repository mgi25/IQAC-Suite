// ReportAutosaveManager handles autosaving event reports including dynamic fields
// and exposing hooks for reinitializing field listeners and manual saves.

window.ReportAutosaveManager = (function() {
    let reportId = window.REPORT_ID || '';
    const proposalId = window.PROPOSAL_ID || '';
    let timeoutId = null;
    let fields = [];

    let storageKey = `report_draft_${reportId || proposalId || 'new'}`;

    function getSavedData() {
        try {
            return JSON.parse(localStorage.getItem(storageKey) || '{}');
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
                const preferred = inputs.find(i => i.type !== 'hidden' && i.value.trim() !== '')
                    || inputs.find(i => i.type !== 'hidden')
                    || inputs.find(i => i.value.trim() !== '')
                    || field;
                data[name] = preferred.value;
            }
        });
        return data;
    }

    function saveLocal() {
        const data = collectFieldData();
        if (reportId) {
            data._report_id = reportId;
        }
        localStorage.setItem(storageKey, JSON.stringify(data));
    }

    function clearLocal() {
        localStorage.removeItem(storageKey);
    }

    function autosaveDraft() {
        if (window.REPORT_STATUS && window.REPORT_STATUS !== 'draft') {
            clearLocal();
            return Promise.resolve();
        }

        const formData = collectFieldData();
        if (proposalId) {
            formData['proposal_id'] = proposalId;
        }
        if (reportId) {
            formData['report_id'] = reportId;
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
            } catch (e) {}
            if (!res.ok) {
                return Promise.reject(data || res.status);
            }
            return data;
        })
        .then(data => {
            if (data && data.success && data.report_id) {
                if (!reportId || reportId !== data.report_id) {
                    const old = getSavedData();
                    clearLocal();
                    reportId = data.report_id;
                    storageKey = `report_draft_${reportId}`;
                    old._report_id = reportId;
                    localStorage.setItem(storageKey, JSON.stringify(old));
                    window.REPORT_ID = reportId;
                } else {
                    saveLocal();
                }
                document.dispatchEvent(new CustomEvent('autosave:success', {detail: {reportId: data.report_id}}));
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
                    Array.from(f.options).forEach(o => { o.selected = values.includes(o.value); });
                } else if (!f.value) {
                    f.value = val;
                }
            }
            bindField(f);
        });

        if (saved._report_id && !reportId) {
            reportId = saved._report_id;
            storageKey = `report_draft_${reportId}`;
            window.REPORT_ID = reportId;
        }

        if (window.REPORT_STATUS && window.REPORT_STATUS !== 'draft') {
            clearLocal();
        }
    }

    function manualSave() {
        saveLocal();
        return autosaveDraft();
    }

    reinitialize();

    const formEl = document.querySelector('form');
    if (formEl) {
        formEl.addEventListener('submit', clearLocal);
    }

    return {
        reinitialize,
        manualSave,
        autosaveDraft,
        clearLocal
    };
})();
