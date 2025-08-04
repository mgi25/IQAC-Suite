let proposalId = window.PROPOSAL_ID || '';
let timeoutId = null;

// Only grab fields with a name attribute (prevents sending unnamed or irrelevant elements)
const fields = Array.from(document.querySelectorAll('input[name], textarea[name], select[name]'));

// Unique key for this page's local storage
const pageKey = `proposal_draft_${window.location.pathname}_new`;

// Load any saved draft from localStorage
try {
    const savedData = JSON.parse(localStorage.getItem(pageKey) || '{}');
    if (savedData._proposal_id && !proposalId) {
        proposalId = savedData._proposal_id;
    }
    fields.forEach(f => {
        if (savedData.hasOwnProperty(f.name)) {
            if (f.type === 'checkbox' || f.type === 'radio') {
                f.checked = savedData[f.name];
            } else if (f.multiple) {
                const values = savedData[f.name] || [];
                Array.from(f.options).forEach(o => {
                    o.selected = values.includes(o.value);
                });
            } else if (!f.value) {
                f.value = savedData[f.name];
            }
        }
    });
} catch (e) { /* ignore JSON errors */ }

fields.forEach(field => {
    field.addEventListener('input', () => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
            autosaveDraft();
            saveLocal();
        }, 1000); // Save after 1 second idle
    });
});

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
    const formData = {};
    fields.forEach(f => {
        // Only include enabled, not-disabled fields
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
    if (proposalId) formData['proposal_id'] = proposalId;
    fetch(window.AUTOSAVE_URL, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": window.AUTOSAVE_CSRF
        },
        body: JSON.stringify(formData)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success && data.proposal_id) {
            proposalId = data.proposal_id;
            saveLocal(); // persist id with draft
        }
    })
    .catch(() => { /* Optionally show: "Draft Not Saved" */ });
}

// Remove saved draft on form submit
const formEl = document.querySelector('form');
if (formEl) {
    formEl.addEventListener('submit', clearLocal);
}
