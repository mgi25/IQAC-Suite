let proposalId = window.PROPOSAL_ID || '';
let timeoutId = null;

// Only grab fields with a name attribute (prevents sending unnamed or irrelevant elements)
const fields = Array.from(document.querySelectorAll('input[name], textarea[name], select[name]'));

// Unique key for this page's local storage
const pageKey = `proposal_draft_${window.location.pathname}_new`;

// Clear localStorage immediately if this is a submitted proposal
if (window.PROPOSAL_STATUS && window.PROPOSAL_STATUS !== 'draft') {
    localStorage.removeItem(pageKey);
    console.log('Cleared localStorage for submitted proposal');
}

// Load any saved draft from localStorage only if no existing proposal or proposal is still a draft
try {
    const savedData = JSON.parse(localStorage.getItem(pageKey) || '{}');
    // Only load draft data if we don't have a proposal ID (new proposal) or if it's still a draft
    const shouldLoadDraft = !proposalId || (proposalId && window.PROPOSAL_STATUS === 'draft');
    
    console.log('Draft loading check:', {
        proposalId,
        status: window.PROPOSAL_STATUS,
        shouldLoadDraft,
        savedDataKeys: Object.keys(savedData)
    });
    
    if (shouldLoadDraft && Object.keys(savedData).length > 0) {
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
        console.log('Loaded draft data from localStorage');
    } else if (!shouldLoadDraft) {
        // Clear localStorage for submitted proposals
        clearLocal();
        console.log('Cleared localStorage because proposal is not a draft');
    }
} catch (e) { 
    console.error('Error loading draft:', e);
}

fields.forEach(field => {
    // Don't add event listeners for submitted proposals
    if (window.PROPOSAL_STATUS && window.PROPOSAL_STATUS !== 'draft') {
        return;
    }
    
    const handler = () => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
            autosaveDraft();
            saveLocal();
        }, 1000); // Save after 1 second idle
    };

    field.addEventListener('input', handler);
    if (field.tagName === 'SELECT') {
        field.addEventListener('change', handler);
    }
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
    // Don't autosave if this is a submitted proposal
    if (window.PROPOSAL_STATUS && window.PROPOSAL_STATUS !== 'draft') {
        console.log('Skipping autosave - proposal is not a draft');
        return;
    }
    
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
    console.log('Autosave payload:', formData);
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
            console.log('Autosave successful');
        } else {
            console.log('Autosave failed:', data);
        }
    })
    .catch(err => { 
        console.error('Autosave error:', err);
    });
}

// Remove saved draft on form submit
const formEl = document.querySelector('form');
if (formEl) {
    formEl.addEventListener('submit', clearLocal);
}

// Clear localStorage for already submitted proposals
if (window.PROPOSAL_STATUS && window.PROPOSAL_STATUS !== 'draft') {
    clearLocal();
}
