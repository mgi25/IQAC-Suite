document.addEventListener('DOMContentLoaded', function() {
    console.log('PSO & PO Management JavaScript loaded');

    // If we're on the Settings page, skip heavy admin-only bootstrapping
    // and only wire up the minimal pieces used by the modal flows.
    if (window.IS_SETTINGS_PSO_PAGE) {
        try {
            // Minimal init for settings page: only modal open/close wiring.
            // Do NOT attach admin dashboard listeners; the settings page has its own handlers.
            setupModalEvents && setupModalEvents();
        } catch (err) {
            console.error('Settings minimal init error:', err);
        }
        return;
    }

    // Initialize the page (admin dashboard context)
    initializePage();
    setupEventListeners();
    loadOrganizations();
    loadAllAssignments();
});

let currentOrganizations = [];
let currentOrgTypes = [];

function initializePage() {
    console.log('PSO & PO Management page initialized');
}

function setupEventListeners() {
    // Filter buttons
    const filterBtns = document.querySelectorAll('.filter-btn');
    filterBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            filterBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            filterOrganizations(this.dataset.type);
        });
    });

    // Search functionality
    const searchInput = document.getElementById('org-search');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            searchOrganizations(this.value);
        });
    }

    // Edit outcomes buttons from template (static HTML)
    setupEditButtonListeners();

    // Delegated handler for opening outcomes page (redirect)
    document.addEventListener('click', function(e){
        const trigger = e.target.closest('[data-open-outcomes]');
        if (!trigger) return;
        const row = trigger.closest('tr');
        const orgId = Number(trigger.dataset.orgId || row?.dataset.id);
        if (orgId) window.location.href = `/core-admin/pso-po/org/${orgId}/`;
    });
    
    // Add outcome buttons
    setupAddOutcomeListeners();

    // Close handler no longer required on list page.
    
    // Assignment functionality
    setupAssignmentListeners();
}

function setupEditButtonListeners() {
    console.log('Setting up edit button listeners');
    // Add event listeners to existing edit buttons
    const editBtns = document.querySelectorAll('.edit-outcomes-btn');
    console.log('Found edit buttons:', editBtns.length);
    editBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            console.log('Edit button clicked');
            const orgId = this.dataset.orgId;
            const orgName = this.dataset.orgName;
            console.log('Opening modal for org:', orgId, orgName);
            openOutcomesModal(orgId, orgName, 'all');
        });
    });

    // Add event listeners to PO/PSO count spans for direct access
    const poCounts = document.querySelectorAll('.po-count');
    const psoCounts = document.querySelectorAll('.pso-count');
    
    poCounts.forEach(span => {
        span.addEventListener('click', function() {
            const orgId = this.dataset.orgId;
            const orgName = this.closest('tr').querySelector('.org-name').textContent;
            openOutcomesModal(orgId, orgName, 'pos');
        });
        span.style.cursor = 'pointer';
    });

    psoCounts.forEach(span => {
        span.addEventListener('click', function() {
            const orgId = this.dataset.orgId;
            const orgName = this.closest('tr').querySelector('.org-name').textContent;
            openOutcomesModal(orgId, orgName, 'psos');
        });
        span.style.cursor = 'pointer';
    });
}

function setupAddOutcomeListeners() {
    // Add PO button
    const addPOBtn = document.getElementById('addPOBtn');
    if (addPOBtn) {
        addPOBtn.addEventListener('click', function() {
            const input = document.getElementById('newPOInput');
            if (input && input.value.trim()) {
                addNewOutcome(input.value.trim(), 'pos');
                input.value = '';
            }
        });
    }
    
    // Add PSO button  
    const addPSOBtn = document.getElementById('addPSOBtn');
    if (addPSOBtn) {
        addPSOBtn.addEventListener('click', function() {
            const input = document.getElementById('newPSOInput');
            if (input && input.value.trim()) {
                addNewOutcome(input.value.trim(), 'psos');
                input.value = '';
            }
        });
    }
    
    // Enter key support for inputs
    const poInput = document.getElementById('newPOInput');
    const psoInput = document.getElementById('newPSOInput');
    
    if (poInput) {
        poInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                addPOBtn.click();
            }
        });
    }
    
    if (psoInput) {
        psoInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                addPSOBtn.click();
            }
        });
    }
}

function addNewOutcome(description, type) {
    console.log('Adding new outcome:', description, type);
    
    const panel = document.getElementById('outcomesPanel');
    const orgId = panel && panel.dataset ? panel.dataset.orgId : null;
    
    if (!orgId) {
        showNotification('Organization not found', 'error');
        return;
    }
    
    // First, we need to get or create a program for this organization
    // For simplicity, we'll create a default program if none exists
    getOrCreateDefaultProgram(orgId)
        .then(programId => {
            return createOutcome(programId, description, type);
        })
        .then(success => {
            if (success) {
                showNotification(`${type === 'pos' ? 'PO' : 'PSO'} added successfully`, 'success');
                // Reload outcomes to show the new addition
                loadOutcomesForOrganization(orgId);
                // Update the counts in the main table
                updateOutcomeCounts();
            }
        })
        .catch(error => {
            console.error('Error adding outcome:', error);
            showNotification('Error adding outcome: ' + error.message, 'error');
        });
}

function getOrCreateDefaultProgram(orgId) {
    return fetch(`/core/api/programs/${orgId}/`)
        .then(response => response.json())
        .then(programs => {
            if (programs && programs.length > 0) {
                return programs[0].id;
            } else {
                // Create a default program
                return createDefaultProgram(orgId);
            }
        });
}

function createDefaultProgram(orgId) {
    return fetch('/core/api/create-program/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            organization_id: orgId,
            program_name: 'Default Program'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            return data.program.id;
        } else {
            throw new Error('Failed to create default program');
        }
    });
}

function createOutcome(programId, description, type) {
    const endpoint = '/core/api/manage-program-outcomes/';
    
    return fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            program_id: programId,
            description: description,
            type: type === 'pos' ? 'PO' : 'PSO'
        })
    })
    .then(response => response.json())
    .then(data => data.success);
}

function updateOutcomeCounts() {
    // This function refreshes the outcome counts in the main table
    const panelEl = document.getElementById('outcomesPanel');
    const currentOrgId = panelEl ? panelEl.dataset.orgId : null;
    if (currentOrgId) {
        fetch(`/core/api/programs/${currentOrgId}/`)
            .then(response => response.json())
            .then(programs => {
                if (programs && programs.length > 0) {
                    const program = programs[0];
                    
                    // Count POs and PSOs
                    Promise.all([
                        fetch(`/core/api/program-outcomes/${program.id}/?type=PO`).then(r => r.json()),
                        fetch(`/core/api/program-outcomes/${program.id}/?type=PSO`).then(r => r.json())
                    ]).then(([pos, psos]) => {
                        // Update the counts in the table
                        const poCountSpan = document.querySelector(`.po-count[data-org-id="${currentOrgId}"] .count`);
                        const psoCountSpan = document.querySelector(`.pso-count[data-org-id="${currentOrgId}"] .count`);
                        
                        if (poCountSpan) {
                            poCountSpan.textContent = pos ? pos.length : 0;
                        }
                        if (psoCountSpan) {
                            psoCountSpan.textContent = psos ? psos.length : 0;
                        }
                    });
                }
            })
            .catch(error => {
                console.error('Error updating outcome counts:', error);
            });
    }
}

function setupModalEvents() {
    // Close modals when clicking outside or on close button
    const modals = document.querySelectorAll('.modal');
    const closeBtns = document.querySelectorAll('.modal .close');
    
    modals.forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeModal(modal.id);
            }
        });
    });

    closeBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const modal = this.closest('.modal');
            closeModal(modal.id);
        });
    });

    // Cancel buttons
    const cancelBtns = document.querySelectorAll('.btn-cancel');
    cancelBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const modal = this.closest('.modal');
            closeModal(modal.id);
        });
    });
}

function loadOrganizations() {
    // Use the data passed from Django template if available
    if (typeof window.orgOutcomeCounts !== 'undefined') {
        updateOutcomeCounts(window.orgOutcomeCounts);
    }

    // Fetch fresh organization data
    fetch('/api/organizations/')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentOrganizations = data.organizations;
                currentOrgTypes = data.org_types;
                updateFilterButtons(data.org_types);
                displayOrganizations(data.organizations);
                loadOutcomeCounts();
            }
        })
        .catch(error => {
            console.error('Error loading organizations:', error);
            showNotification('Error loading organizations', 'error');
        });
}

function updateFilterButtons(orgTypes) {
    const filterContainer = document.querySelector('.filter-tabs');
    if (!filterContainer) return;

    // Keep the "All" button and add dynamic buttons
    const allBtn = filterContainer.querySelector('[data-type="all"]');
    filterContainer.innerHTML = '';
    filterContainer.appendChild(allBtn);

    orgTypes.forEach(type => {
        const btn = document.createElement('button');
        btn.className = 'filter-btn';
        btn.dataset.type = type.name.toLowerCase();
        btn.textContent = type.name + 's';
        filterContainer.appendChild(btn);

        btn.addEventListener('click', function() {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            filterOrganizations(this.dataset.type);
        });
    });
}

function displayOrganizations(organizations) {
    const tbody = document.getElementById('organizations-list');
    if (!tbody) return;

    tbody.innerHTML = '';

    organizations.forEach((org, index) => {
        const row = document.createElement('tr');
        row.className = 'org-row';
        row.dataset.id = org.id;
        row.dataset.name = org.name;
        row.dataset.type = org.type.toLowerCase();
        row.dataset.parent = org.parent || '';

        row.innerHTML = `
            <td>${org.id}</td>
            <td class="org-name">${org.name}</td>
            <td>${org.type}</td>
            <td>
                <span class="status-badge ${org.is_active ? 'active' : 'inactive'}">
                    ${org.is_active ? 'Active' : 'Inactive'}
                </span>
            </td>
            <td class="parent-name">${org.parent || '-'}</td>
            <td>
                <div class="outcomes-cell">
                    <div class="outcome-counts">
                        <a class="po-count" href="/core-admin/pso-po/org/${org.id}/" data-org-id="${org.id}">
                            <span class="count">0</span> POs
                        </a>
                        <a class="pso-count" href="/core-admin/pso-po/org/${org.id}/" data-org-id="${org.id}">
                            <span class="count">0</span> PSOs
                        </a>
                    </div>
                    <a class="edit-outcomes-btn" href="/core-admin/pso-po/org/${org.id}/">
                        <i class="fas fa-edit"></i> Edit
                    </a>
                </div>
            </td>
        `;

        tbody.appendChild(row);
    });
}

function loadOutcomeCounts() {
    // Load outcome counts for all organizations
    currentOrganizations.forEach(org => {
        fetch(`/api/organizations/${org.id}/outcomes/`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateOrgOutcomeCounts(org.id, data.po_count, data.pso_count);
                }
            })
            .catch(error => {
                console.error(`Error loading outcomes for org ${org.id}:`, error);
            });
    });
}

function updateOrgOutcomeCounts(orgId, poCount, psoCount) {
    const poCountSpan = document.querySelector(`.po-count[data-org-id="${orgId}"] .count`);
    const psoCountSpan = document.querySelector(`.pso-count[data-org-id="${orgId}"] .count`);
    
    if (poCountSpan) poCountSpan.textContent = poCount;
    if (psoCountSpan) psoCountSpan.textContent = psoCount;
}

function updateOutcomeCounts(countsData) {
    Object.keys(countsData).forEach(orgId => {
        const data = countsData[orgId];
        updateOrgOutcomeCounts(orgId, data.po_count, data.pso_count);
    });
}

function filterOrganizations(type) {
    const rows = document.querySelectorAll('.org-row');
    
    rows.forEach(row => {
        if (type === 'all' || row.dataset.type === type) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

function searchOrganizations(searchTerm) {
    const rows = document.querySelectorAll('.org-row');
    const term = searchTerm.toLowerCase();
    
    rows.forEach(row => {
        const orgName = row.dataset.name.toLowerCase();
        const orgType = row.dataset.type.toLowerCase();
        const parent = row.dataset.parent.toLowerCase();
        
        if (orgName.includes(term) || orgType.includes(term) || parent.includes(term)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

function openOutcomesModal(orgId, orgName, tab = 'all') {
    console.log('Opening outcomes panel for org:', orgId, orgName);
    const panel = document.getElementById('outcomesPanel');
    const nameSpan = document.getElementById('modal-org-name');
    if (nameSpan) nameSpan.textContent = orgName;
    if (panel) {
        panel.style.display = 'block';
        panel.dataset.orgId = orgId;
        panel.dataset.orgName = orgName;
    }
    // Load outcomes for this organization
    loadOutcomesForOrganization(orgId);
}

function loadOutcomesForOrganization(orgId) {
    console.log('Loading outcomes for organization:', orgId);
    
    // Clear existing content first
    const posList = document.getElementById('posList');
    const psosList = document.getElementById('psosList');
    
    if (posList) {
        posList.innerHTML = '<div class="loading">Loading POs...</div>';
    }
    if (psosList) {
        psosList.innerHTML = '<div class="loading">Loading PSOs...</div>';
    }
    
    // First get all programs for this organization
    fetch(`/core/api/programs/${orgId}/`)
        .then(response => {
            console.log('Programs API response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(programs => {
            console.log('Found programs:', programs);
            
            if (programs && programs.length > 0) {
                // For simplicity, we'll load outcomes from the first program
                // In the future, you might want to aggregate from all programs
                const firstProgram = programs[0];
                console.log('Loading outcomes for first program:', firstProgram);
                loadProgramOutcomes(firstProgram.id);
            } else {
                // No programs found, show empty state
                console.log('No programs found, showing empty state');
                displayEmptyOutcomes();
            }
        })
        .catch(error => {
            console.error('Error loading programs:', error);
            showNotification('Error loading outcomes: ' + error.message, 'error');
            displayEmptyOutcomes();
        });
}

function loadProgramOutcomes(programId) {
    console.log('Loading outcomes for program:', programId);
    const archived = document.getElementById('showArchivedToggle')?.checked ? '&archived=1' : '';
    
    // Load POs
    fetch(`/core/api/program-outcomes/${programId}/?type=PO${archived}`)
        .then(response => {
            console.log('POs API response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(pos => {
            console.log('Loaded POs:', pos);
            displayOutcomes(pos, 'pos');
        })
        .catch(error => {
            console.error('Error loading POs:', error);
            document.getElementById('posList').innerHTML = '<div class="no-outcomes">Error loading POs: ' + error.message + '</div>';
        });
    
    // Load PSOs
    fetch(`/core/api/program-outcomes/${programId}/?type=PSO${archived}`)
        .then(response => {
            console.log('PSOs API response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(psos => {
            console.log('Loaded PSOs:', psos);
            displayOutcomes(psos, 'psos');
        })
        .catch(error => {
            console.error('Error loading PSOs:', error);
            document.getElementById('psosList').innerHTML = '<div class="no-outcomes">Error loading PSOs: ' + error.message + '</div>';
        });
}

function displayOutcomes(outcomes, type) {
    const listId = type === 'pos' ? 'posList' : 'psosList';
    const list = document.getElementById(listId);
    
    if (!list) {
        console.error(`List element ${listId} not found`);
        return;
    }
    
    list.innerHTML = '';
    
    if (!outcomes || outcomes.length === 0) {
        list.innerHTML = '<div class="no-outcomes">No outcomes added yet.</div>';
        return;
    }
    
    outcomes.forEach(outcome => {
        const item = document.createElement('div');
        item.className = 'outcome-item';
        item.dataset.outcomeId = outcome.id;
        item.dataset.type = type;
        const isArchived = String(outcome.status||'').toLowerCase() === 'archived';
        if (isArchived) item.classList.add('archived');

        const text = document.createElement('div');
        text.className = 'outcome-text';
        text.textContent = outcome.description;
        text.title = 'Click edit to modify';

        const actions = document.createElement('div');
        actions.className = 'outcome-actions';

        const editBtn = document.createElement('button');
        editBtn.className = 'edit-outcome-btn';
        editBtn.innerHTML = '<i class="fas fa-edit"></i>';
        editBtn.addEventListener('click', () => enterInlineEdit(item, text, outcome.id, type));

        const delBtn = document.createElement('button');
        delBtn.className = 'delete-outcome-btn';
        delBtn.title = 'Archive';
        delBtn.innerHTML = '<i class="fas fa-archive"></i>';
        delBtn.addEventListener('click', () => inlineDeleteOutcome(item, outcome.id, type));

        if (isArchived) {
            const restoreBtn = document.createElement('button');
            restoreBtn.className = 'restore-outcome-btn';
            restoreBtn.title = 'Restore';
            restoreBtn.innerHTML = '<i class="fas fa-undo"></i>';
            restoreBtn.addEventListener('click', () => restoreArchivedOutcome(outcome.id, type));
            actions.appendChild(restoreBtn);
        }

        actions.appendChild(editBtn);
        actions.appendChild(delBtn);

        item.appendChild(text);
        item.appendChild(actions);
        list.appendChild(item);
    });
}

function enterInlineEdit(item, textEl, outcomeId, type){
    if(item.classList.contains('editing')) return;
    item.classList.add('editing');
    const original = textEl.textContent;
    const ta = document.createElement('textarea');
    ta.className = 'inline-editor';
    ta.value = original;
    ta.rows = Math.min(6, Math.max(2, Math.ceil(original.length/80)));
    ta.style.width = '100%';
    ta.style.resize = 'vertical';
    textEl.replaceWith(ta);
    ta.focus();

    const actions = item.querySelector('.outcome-actions');
    const prev = actions.innerHTML;
    actions.innerHTML = '';

    const save = document.createElement('button');
    save.className = 'btn-inline-save';
    save.textContent = 'Save';
    const cancel = document.createElement('button');
    cancel.className = 'btn-inline-cancel';
    cancel.textContent = 'Cancel';

    const error = document.createElement('div');
    error.className = 'inline-error';
    error.style.display = 'none';
    error.textContent = 'Description can\'t be empty';
    item.appendChild(error);

    const exitEdit = () => {
        const restored = document.createElement('div');
        restored.className = 'outcome-text';
        restored.textContent = original;
        ta.replaceWith(restored);
        actions.innerHTML = prev;
        item.classList.remove('editing');
        // Rebind handlers on restored buttons
        const editBtn = actions.querySelector('.edit-outcome-btn');
        const delBtn = actions.querySelector('.delete-outcome-btn');
        editBtn?.addEventListener('click', () => enterInlineEdit(item, restored, outcomeId, type));
        delBtn?.addEventListener('click', () => inlineDeleteOutcome(item, outcomeId, type));
        error.remove();
    };

    cancel.addEventListener('click', exitEdit);
    ta.addEventListener('keydown', (e)=>{ if(e.key==='Escape'){ e.preventDefault(); exitEdit(); }});
    save.addEventListener('click', () => {
        const val = (ta.value||'').trim();
        if(!val){ error.style.display='block'; return; }
        // PUT via unified endpoint
        fetch('/core/api/manage-program-outcomes/',{
            method:'PUT', headers:{'Content-Type':'application/json','X-CSRFToken':getCsrfToken()},
            body: JSON.stringify({ outcome_id: outcomeId, type: (type==='pos'?'PO':'PSO'), description: val })
        }).then(r=>r.json()).then(data=>{
            if(data.success){
                const restored = document.createElement('div');
                restored.className = 'outcome-text';
                restored.textContent = data.outcome?.description || val;
                ta.replaceWith(restored);
                actions.innerHTML = prev;
                item.classList.remove('editing');
                const editBtn = actions.querySelector('.edit-outcome-btn');
                const delBtn = actions.querySelector('.delete-outcome-btn');
                editBtn?.addEventListener('click', () => enterInlineEdit(item, restored, outcomeId, type));
                delBtn?.addEventListener('click', () => inlineDeleteOutcome(item, outcomeId, type));
                error.remove();
                showNotification('Outcome updated', 'success');
                updateOutcomeCounts();
            }else{
                error.textContent = data.error || 'Update failed';
                error.style.display='block';
            }
        }).catch(ex=>{
            error.textContent = 'Network error';
            error.style.display='block';
        });
    });

    actions.appendChild(save);
    actions.appendChild(cancel);
}

function inlineDeleteOutcome(item, outcomeId, type){
    // Inline confirmation UI (no blocking popups)
    const actions = item.querySelector('.outcome-actions');
    const prev = actions.innerHTML;
    actions.innerHTML = '';
    const confirmBtn = document.createElement('button');
    confirmBtn.className = 'btn-inline-delete confirm';
    confirmBtn.textContent = 'Confirm Archive';
    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'btn-inline-cancel';
    cancelBtn.textContent = 'Cancel';
    actions.appendChild(confirmBtn);
    actions.appendChild(cancelBtn);

    const restore = () => { actions.innerHTML = prev; };
    cancelBtn.addEventListener('click', restore);
    confirmBtn.addEventListener('click', ()=>{
        fetch('/core/api/manage-program-outcomes/',{
            method:'DELETE', headers:{'Content-Type':'application/json','X-CSRFToken':getCsrfToken()},
            body: JSON.stringify({ outcome_id: outcomeId, type: (type==='pos'?'PO':'PSO') })
        }).then(r=>r.json()).then(data=>{
            if(data.success){
                item.classList.add('archived');
                showNotification('Outcome archived', 'success');
                updateOutcomeCounts();
                // If viewing only active, remove it from the list
                const archived = document.getElementById('showArchivedToggle')?.checked;
                if (!archived) item.remove();
            }else{
                showNotification(data.error || 'Delete failed', 'error');
                restore();
            }
        }).catch(()=> { showNotification('Network error', 'error'); restore(); });
    });
}

function restoreArchivedOutcome(outcomeId, type){
    fetch('/core/api/manage-program-outcomes/',{
        method:'PATCH', headers:{'Content-Type':'application/json','X-CSRFToken':getCsrfToken()},
        body: JSON.stringify({ outcome_id: outcomeId, type: (type==='pos'?'PO':'PSO') })
    }).then(r=>r.json()).then(data=>{
        if(data.success){
            showNotification('Outcome restored', 'success');
            const panel = document.getElementById('outcomesPanel');
            const orgId = panel?.dataset?.orgId;
            if (orgId) loadOutcomesForOrganization(orgId);
        }else{
            showNotification(data.error || 'Restore failed', 'error');
        }
    }).catch(()=> showNotification('Network error', 'error'));
}

function displayEmptyOutcomes() {
    const posList = document.getElementById('posList');
    const psosList = document.getElementById('psosList');
    
    if (posList) {
        posList.innerHTML = '<div class="no-outcomes">No programmes found for this organization.</div>';
    }
    if (psosList) {
        psosList.innerHTML = '<div class="no-outcomes">No programmes found for this organization.</div>';
    }
}

function loadPrograms(orgId, initialTab = 'all') {
    console.log('Loading programs for org:', orgId);
    fetch(`/core/api/programs/${orgId}/`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayPrograms(data.programs, initialTab);
            } else {
                showNotification('Error loading programs', 'error');
            }
        })
        .catch(error => {
            console.error('Error loading programs:', error);
            showNotification('Error loading programs', 'error');
        });
}

function displayPrograms(programs, initialTab) {
    const programsList = document.getElementById('programsList');
    if (!programsList) return;

    if (programs.length === 0) {
        programsList.innerHTML = `
            <div class="no-programs">
                <p>No programs found for this organization.</p>
                <button class="btn-primary" onclick="showAddProgramForm()">Add First Program</button>
            </div>
        `;
        return;
    }

    programsList.innerHTML = '';
    programs.forEach(program => {
        const programCard = document.createElement('div');
        programCard.className = 'program-card';
        programCard.innerHTML = `
            <div class="program-info">
                <h5>${program.name}</h5>
            </div>
            <div class="program-stats">
                <span class="po-stat">${program.po_count || 0} POs</span>
                <span class="pso-stat">${program.pso_count || 0} PSOs</span>
            </div>
            <button class="edit-program-btn" onclick="showProgramOutcomes(${program.id}, '${program.name}', '${initialTab}')">
                <i class="fas fa-arrow-right"></i>
            </button>
        `;
        programsList.appendChild(programCard);
    });

    // If only one program and specific tab requested, go directly to outcomes
    if (programs.length === 1 && initialTab !== 'all') {
        showProgramOutcomes(programs[0].id, programs[0].name, initialTab);
    }
}

function showProgramOutcomes(programId, programName, initialTab = 'pos') {
    const programsSection = document.querySelector('.programs-section');
    const outcomesSection = document.getElementById('outcomesSection');
    const selectedProgramName = document.getElementById('selectedProgramName');
    
    if (programsSection) programsSection.style.display = 'none';
    if (outcomesSection) outcomesSection.style.display = 'block';
    if (selectedProgramName) selectedProgramName.textContent = programName;
    
    // Store current program
    outcomesSection.dataset.programId = programId;
    
    // Set active tab
    switchTab(initialTab);
    
    // Load outcomes
    loadOutcomes(programId, initialTab);
    
    // Setup back button
    const backBtn = document.getElementById('backToPrograms');
    if (backBtn) {
        backBtn.onclick = function() {
            programsSection.style.display = 'block';
            outcomesSection.style.display = 'none';
        };
    }
}

function switchTab(tabName) {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    tabBtns.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
        btn.onclick = function() {
            switchTab(this.dataset.tab);
            const programId = document.getElementById('outcomesSection').dataset.programId;
            loadOutcomes(programId, this.dataset.tab);
        };
    });
    
    tabPanes.forEach(pane => {
        pane.classList.toggle('active', pane.id === `${tabName}Tab`);
    });
}

function displayOutcomes(outcomes, type) {
    const listId = type === 'pos' ? 'posList' : 'psosList';
    const list = document.getElementById(listId);
    
    if (!list) {
        console.error(`List element ${listId} not found`);
        return;
    }
    
    list.innerHTML = '';
    
    if (!outcomes || outcomes.length === 0) {
        list.innerHTML = '<div class="no-outcomes">No outcomes added yet.</div>';
        return;
    }
    
    outcomes.forEach(outcome => {
        const item = document.createElement('div');
        item.className = 'outcome-item';
        item.dataset.outcomeId = outcome.id;
        item.dataset.type = type;

        const text = document.createElement('div');
        text.className = 'outcome-text';
        text.textContent = outcome.description;
        text.title = 'Click edit to modify';

        const actions = document.createElement('div');
        actions.className = 'outcome-actions';

        const editBtn = document.createElement('button');
        editBtn.className = 'edit-outcome-btn';
        editBtn.innerHTML = '<i class="fas fa-edit"></i>';
        editBtn.addEventListener('click', () => enterInlineEdit(item, text, outcome.id, type));

        const delBtn = document.createElement('button');
        delBtn.className = 'delete-outcome-btn';
        delBtn.innerHTML = '<i class="fas fa-trash"></i>';
        delBtn.addEventListener('click', () => inlineDeleteOutcome(item, outcome.id, type));

        actions.appendChild(editBtn);
        actions.appendChild(delBtn);

        item.appendChild(text);
        item.appendChild(actions);
        list.appendChild(item);
    });
}

function addOutcome(type) {
    const modal = document.getElementById('addOutcomeModal');
    const typeSpan = document.getElementById('addOutcomeType');
    const buttonSpan = document.getElementById('addOutcomeButtonText');
    
    if (typeSpan) typeSpan.textContent = type === 'pos' ? 'Programme Outcome' : 'Programme Specific Outcome';
    if (buttonSpan) buttonSpan.textContent = type === 'pos' ? 'PO' : 'PSO';
    
    modal.dataset.type = type;
    openModal('addOutcomeModal');
    
    // Setup form submission
    const form = document.getElementById('addOutcomeForm');
    form.onsubmit = function(e) {
        e.preventDefault();
        saveNewOutcome(type);
    };
}

function editOutcome(outcomeId, description, type) {
    const modal = document.getElementById('editOutcomeModal');
    const typeSpan = document.getElementById('editOutcomeType');
    const textarea = document.getElementById('editOutcomeText');
    
    if (typeSpan) typeSpan.textContent = type === 'pos' ? 'Programme Outcome' : 'Programme Specific Outcome';
    if (textarea) textarea.value = description;
    
    modal.dataset.outcomeId = outcomeId;
    modal.dataset.type = type;
    openModal('editOutcomeModal');
    
    // Setup form submission
    const form = document.getElementById('editOutcomeForm');
    form.onsubmit = function(e) {
        e.preventDefault();
        saveEditedOutcome();
    };
}

function saveNewOutcome(type) {
    const textarea = document.getElementById('addOutcomeText');
    const programId = document.getElementById('outcomesSection').dataset.programId;
    const endpoint = type === 'pos' ? 
        `/api/programs/${programId}/pos/` : 
        `/api/programs/${programId}/psos/`;
    
    fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            description: textarea.value
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            closeModal('addOutcomeModal');
            textarea.value = '';
            loadOutcomes(programId, type);
            showNotification('Outcome added successfully', 'success');
            updateOutcomeCountsInTable();
        } else {
            showNotification('Error adding outcome', 'error');
        }
    })
    .catch(error => {
        console.error('Error saving outcome:', error);
        showNotification('Error adding outcome', 'error');
    });
}

function saveEditedOutcome() {
    const modal = document.getElementById('editOutcomeModal');
    const textarea = document.getElementById('editOutcomeText');
    const outcomeId = modal.dataset.outcomeId;
    const type = modal.dataset.type;
    const programId = document.getElementById('outcomesSection').dataset.programId;
    
    const endpoint = type === 'pos' ? 
        `/api/outcomes/pos/${outcomeId}/` : 
        `/api/outcomes/psos/${outcomeId}/`;
    
    fetch(endpoint, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            description: textarea.value
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            closeModal('editOutcomeModal');
            loadOutcomes(programId, type);
            showNotification('Outcome updated successfully', 'success');
        } else {
            showNotification('Error updating outcome', 'error');
        }
    })
    .catch(error => {
        console.error('Error updating outcome:', error);
        showNotification('Error updating outcome', 'error');
    });
}

function deleteOutcome(outcomeId, type) {
    if (!confirm('Are you sure you want to delete this outcome?')) return;
    
    const programId = document.getElementById('outcomesSection').dataset.programId;
    const endpoint = type === 'pos' ? 
        `/api/outcomes/pos/${outcomeId}/` : 
        `/api/outcomes/psos/${outcomeId}/`;
    
    fetch(endpoint, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            loadOutcomes(programId, type);
            showNotification('Outcome deleted successfully', 'success');
            updateOutcomeCountsInTable();
        } else {
            showNotification('Error deleting outcome', 'error');
        }
    })
    .catch(error => {
        console.error('Error deleting outcome:', error);
        showNotification('Error deleting outcome', 'error');
    });
}

function updateOutcomeCountsInTable() {
    // Refresh outcome counts in the main table
    loadOutcomeCounts();
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-message">${message}</span>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

function getCsrfToken() {
    const tokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
    if (tokenElement) {
        return tokenElement.value;
    }
    
    // Fallback to cookie
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') {
            return value;
        }
    }
    return '';
}

// ==========================================
// USER ASSIGNMENT FUNCTIONALITY
// ==========================================

let currentAssignmentOrgId = null;
let currentAssignmentOrgName = null;
let currentAssignmentOrgType = null;

// Add assignment button listeners in setupEventListeners
function setupAssignmentListeners() {
    // Assignment buttons from template (static HTML)
    const assignBtns = document.querySelectorAll('.assign-user-btn');
    console.log('Found assignment buttons:', assignBtns.length);
    assignBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const orgId = this.dataset.orgId;
            const orgName = this.dataset.orgName;
            const orgType = this.dataset.orgType;
            openAssignmentModal(orgId, orgName, orgType);
        });
    });
}

function openAssignmentModal(orgId, orgName, orgType) {
    console.log('Opening assignment modal for org:', orgId, orgName, orgType);
    
    currentAssignmentOrgId = orgId;
    currentAssignmentOrgName = orgName;
    currentAssignmentOrgType = orgType;
    
    const modal = document.getElementById('assignUserModal');
    const modalOrgName = document.getElementById('assign-org-name');
    const modalOrgNameContext = document.getElementById('assign-org-name-context');
    
    if (modalOrgName) {
        modalOrgName.textContent = orgName;
    }
    
    if (modalOrgNameContext) {
        modalOrgNameContext.textContent = orgName;
    }
    
    // Reset form
    document.getElementById('userSearch').value = '';
    document.getElementById('selectedUserId').value = '';
    hideUserDropdown();
    
    // Load current assignment
    loadCurrentAssignment(orgId);
    
    // Setup user search with organization context
    setupUserSearch(orgId, orgType);
    
    // Show modal
    openModal('assignUserModal');
}

function loadCurrentAssignment(orgId) {
    fetch(`/core/api/popso-assignments/${orgId}/`)
        .then(response => response.json())
        .then(data => {
            const currentAssignmentDiv = document.getElementById('currentAssignment');
            const currentAssignedUserSpan = document.getElementById('currentAssignedUser');
            
            if (data.assigned_user) {
                currentAssignmentDiv.style.display = 'block';
                currentAssignedUserSpan.textContent = `${data.assigned_user.full_name} (${data.assigned_user.email})`;
                
                // Update button text
                const submitBtn = document.querySelector('#assignUserForm .btn-save');
                submitBtn.textContent = 'Update Assignment';
            } else {
                currentAssignmentDiv.style.display = 'none';
                
                // Update button text
                const submitBtn = document.querySelector('#assignUserForm .btn-save');
                submitBtn.textContent = 'Assign User';
            }
        })
        .catch(error => {
            console.error('Error loading current assignment:', error);
        });
}

function setupUserSearch(orgId, orgType) {
    const userSearchInput = document.getElementById('userSearch');
    const userDropdown = document.getElementById('userDropdown');
    const selectedUserIdInput = document.getElementById('selectedUserId');
    let searchTimeout = null;

    // Real-time dynamic search - fires immediately on input
    userSearchInput.addEventListener('input', function() {
        const query = this.value.trim();
        
        // Clear previous timeout
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }
        
        // Show dropdown immediately if there's any input
        if (query.length > 0) {
            userDropdown.innerHTML = '<div class="loading">Searching faculty...</div>';
            showUserDropdown();
            
            // Debounce API calls to prevent too many requests (300ms)
            searchTimeout = setTimeout(() => {
                searchFacultyUsers(orgId, query);
            }, 300);
        } else {
            hideUserDropdown();
        }
    });

    // Show faculty users when focused (no search required)
    userSearchInput.addEventListener('focus', function() {
        const query = this.value.trim();
        if (query.length > 0) {
            showUserDropdown();
            searchFacultyUsers(orgId, query);
        } else {
            // Load all faculty users when focused with empty input
            loadAllFacultyForOrg(orgId);
        }
    });

    // Hide dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!userSearchInput.contains(e.target) && !userDropdown.contains(e.target)) {
            hideUserDropdown();
        }
    });
}

// Removed loadUsersByRole function - no longer needed with strict faculty filtering

function loadAllFacultyForOrg(orgId) {
    const userDropdown = document.getElementById('userDropdown');
    userDropdown.innerHTML = '<div class="loading">Loading faculty...</div>';
    showUserDropdown();
    
    fetch(`/core/api/faculty-users/${orgId}/`)
        .then(response => {
            console.log('Load faculty response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(users => {
            console.log('Faculty users loaded:', users);
            
            // Sort users: department faculty first, then general faculty, then alphabetically
            const sortedUsers = users.sort((a, b) => {
                // First priority: department faculty
                if (a.is_department_faculty && !b.is_department_faculty) return -1;
                if (!a.is_department_faculty && b.is_department_faculty) return 1;
                
                // Second priority: alphabetical by name
                return a.full_name.localeCompare(b.full_name);
            });
            
            displayUserOptions(sortedUsers);
        })
        .catch(error => {
            console.error('Error loading faculty:', error);
            userDropdown.innerHTML = `<div class="no-users">Error loading faculty: ${error.message}</div>`;
        });
}

function searchFacultyUsers(orgId, query) {
    const userDropdown = document.getElementById('userDropdown');
    // Show loading with search context
    userDropdown.innerHTML = `<div class="loading">Searching faculty for "${query}"...</div>`;
    showUserDropdown();
    
    // Search strictly faculty users only - use correct URL pattern with enhanced filtering
    let url = `/core/api/faculty-users/${orgId}/?search=${encodeURIComponent(query)}`;
    
    console.log('Searching FACULTY ONLY with department filtering:', url);
    
    fetch(url)
        .then(response => {
            console.log('Faculty search response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(users => {
            console.log('Found faculty users:', users);
            
            // Sort users: department faculty first, then general faculty
            const sortedUsers = users.sort((a, b) => {
                if (a.is_department_faculty && !b.is_department_faculty) return -1;
                if (!a.is_department_faculty && b.is_department_faculty) return 1;
                return a.full_name.localeCompare(b.full_name);
            });
            
            displayUserOptions(sortedUsers, query);
        })
        .catch(error => {
            console.error('Error searching faculty:', error);
            userDropdown.innerHTML = `<div class="no-users">Error searching faculty: ${error.message}</div>`;
        });
}

function displayUserOptions(users, searchQuery = '') {
    const userDropdown = document.getElementById('userDropdown');
    
    if (users.length === 0) {
        const message = searchQuery ? 
            `No faculty users found for "${searchQuery}"` : 
            'No faculty users found for this organization';
        userDropdown.innerHTML = `<div class="no-users">${message}</div>`;
        showUserDropdown();
        return;
    }
    
    userDropdown.innerHTML = '';
    showUserDropdown();
    
    users.forEach(user => {
        const option = document.createElement('div');
        option.className = 'user-option';
        option.dataset.userId = user.id;
        
        // Enhanced role and organization display
        let rolesText = 'Faculty';
        if (user.roles && Array.isArray(user.roles) && user.roles.length > 0) {
            rolesText = user.roles.join(', ');
        }
        
        // Show organization assignments for better context
        let orgText = '';
        if (user.organizations && Array.isArray(user.organizations) && user.organizations.length > 0) {
            orgText = ` • ${user.organizations.join(', ')}`;
        }
        
        // Highlight department faculty for department organizations
        const isDeptFaculty = user.is_department_faculty;
        const facultyBadge = isDeptFaculty ? 
            '<span class="dept-faculty-badge">Dept Faculty</span>' : 
            '<span class="general-faculty-badge">Faculty</span>';
        
        option.innerHTML = `
            <div class="user-info">
                <div class="user-name">
                    ${user.full_name}
                    ${facultyBadge}
                </div>
                <div class="user-details">${user.email} • ${rolesText}${orgText}</div>
            </div>
        `;
        
        option.addEventListener('click', function() {
            selectUser(user);
        });
        
        userDropdown.appendChild(option);
    });
}

function selectUser(user) {
    const userSearchInput = document.getElementById('userSearch');
    const selectedUserIdInput = document.getElementById('selectedUserId');
    
    userSearchInput.value = user.full_name;
    selectedUserIdInput.value = user.id;
    
    hideUserDropdown();
}

function showUserDropdown() {
    const userDropdown = document.getElementById('userDropdown');
    userDropdown.style.display = 'block';
}

function hideUserDropdown() {
    const userDropdown = document.getElementById('userDropdown');
    userDropdown.style.display = 'none';
}

// Handle assignment form submission
function setupAssignmentFormListeners() {
    const assignForm = document.getElementById('assignUserForm');
    const removeAssignmentBtn = document.getElementById('removeAssignmentBtn');
    
    assignForm.addEventListener('submit', function(e) {
        e.preventDefault();
        submitAssignment();
    });
    
    removeAssignmentBtn.addEventListener('click', function() {
        removeAssignment();
    });
}

function submitAssignment() {
    const selectedUserId = document.getElementById('selectedUserId').value;
    
    if (!selectedUserId) {
        showNotification('Please select a user to assign', 'error');
        return;
    }
    
    fetch('/core/api/popso-assignments/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            organization_id: currentAssignmentOrgId,
            user_id: selectedUserId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('User assigned successfully', 'success');
            closeModal('assignUserModal');
            updateAssignmentDisplay(currentAssignmentOrgId, data.assignment.assigned_user);
        } else {
            showNotification('Error assigning user: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error assigning user:', error);
        showNotification('Error assigning user', 'error');
    });
}

function removeAssignment() {
    if (!confirm('Are you sure you want to remove this assignment?')) {
        return;
    }
    
    fetch(`/core/api/popso-assignments/${currentAssignmentOrgId}/`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Assignment removed successfully', 'success');
            closeModal('assignUserModal');
            updateAssignmentDisplay(currentAssignmentOrgId, null);
        } else {
            showNotification('Error removing assignment: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error removing assignment:', error);
        showNotification('Error removing assignment', 'error');
    });
}

function updateAssignmentDisplay(orgId, assignedUser) {
    const assignedNameSpan = document.querySelector(`.assigned-user[data-org-id="${orgId}"] .assigned-name`);
    const assignedUserDiv = document.querySelector(`.assigned-user[data-org-id="${orgId}"]`);
    const assignBtn = document.querySelector(`.assign-user-btn[data-org-id="${orgId}"]`);
    const userIcon = document.querySelector(`.assigned-user[data-org-id="${orgId}"] .fas`);
    
    if (assignedUser) {
        assignedNameSpan.textContent = assignedUser.full_name;
        assignedUserDiv.classList.add('has-assignment');
        assignedUserDiv.title = `Assigned: ${assignedUser.full_name} (${assignedUser.email})`;
        
        // Update icon to show assigned state
        if (userIcon) {
            userIcon.className = 'fas fa-user-check';
            userIcon.style.color = '#059669';
        }
        
        assignBtn.innerHTML = '<i class="fas fa-user-edit"></i> Change';
        assignBtn.classList.add('assigned');
        assignBtn.title = 'Change assignment';
    } else {
        assignedNameSpan.textContent = 'Unassigned';
        assignedUserDiv.classList.remove('has-assignment');
        assignedUserDiv.title = 'No user assigned for PO/PSO management';
        
        // Reset icon to default state
        if (userIcon) {
            userIcon.className = 'fas fa-user-circle';
            userIcon.style.color = '#6b7280';
        }
        
        assignBtn.innerHTML = '<i class="fas fa-user-plus"></i> Assign';
        assignBtn.classList.remove('assigned');
        assignBtn.title = 'Assign user for PO/PSO management';
    }
}

// Load all assignments on page load
function loadAllAssignments() {
    fetch('/core/api/popso-assignments/')
        .then(response => response.json())
        .then(assignments => {
            Object.keys(assignments).forEach(orgId => {
                const assignment = assignments[orgId];
                updateAssignmentDisplay(orgId, assignment.assigned_user);
            });
        })
        .catch(error => {
            console.error('Error loading assignments:', error);
        });
}

// Update the main setupEventListeners to include assignment functionality
function setupEventListeners() {
    // Filter buttons
    const filterBtns = document.querySelectorAll('.filter-btn');
    filterBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            filterBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            filterOrganizations(this.dataset.type);
        });
    });

    // Search functionality
    const searchInput = document.getElementById('org-search');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            searchOrganizations(this.value);
        });
    }

    // Edit outcomes buttons from template (static HTML)
    setupEditButtonListeners();
    
    // Add outcome buttons
    setupAddOutcomeListeners();
    
    // Assignment buttons
    setupAssignmentListeners();
    
    // Assignment form listeners
    setupAssignmentFormListeners();

    // (No modal events required for outcomes panel)
}
