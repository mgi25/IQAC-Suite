let proposalId = window.PROPOSAL_ID || '';
let timeoutId = null;

// Only grab fields with a name attribute (prevents sending unnamed or irrelevant elements)
const fields = Array.from(document.querySelectorAll('input[name], textarea[name], select[name]'));

fields.forEach(field => {
    field.addEventListener('input', () => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(autosaveDraft, 1000); // Save after 1 second idle
    });
});

function autosaveDraft() {
    const formData = {};
    fields.forEach(f => {
        // Only include enabled, not-disabled fields
        if (!f.disabled && f.name) formData[f.name] = f.value;
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
            // Optionally show: "Draft Saved"
        }
    })
    .catch(() => { /* Optionally show: "Draft Not Saved" */ });
}
