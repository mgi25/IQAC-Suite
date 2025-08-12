document.addEventListener('DOMContentLoaded', function() {
    console.log('PSO & PO Management JavaScript loaded');
    // Initialize the page
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
    
    // Add outcome buttons
    setupAddOutcomeListeners();

    // Modal close functionality
    setupModalEvents();
    
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
    
    const modal = document.getElementById('outcomesModal');
    const orgId = modal.dataset.orgId;
    
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
    const currentOrgId = document.getElementById('outcomesModal').dataset.orgId;
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
                        <span class="po-count" data-org-id="${org.id}" onclick="openOutcomesModal(${org.id}, '${org.name}', 'pos')">
                            <span class="count">0</span> POs
                        </span>
                        <span class="pso-count" data-org-id="${org.id}" onclick="openOutcomesModal(${org.id}, '${org.name}', 'psos')">
                            <span class="count">0</span> PSOs
                        </span>
                    </div>
                    <button class="edit-outcomes-btn" data-org-id="${org.id}" data-org-name="${org.name}" onclick="openOutcomesModal(${org.id}, '${org.name}', 'all')">
                        <i class="fas fa-edit"></i> Edit
                    </button>
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
    console.log('Opening outcomes modal for org:', orgId, orgName);
    const modal = document.getElementById('outcomesModal');
    const modalOrgName = document.getElementById('modal-org-name');
    
    if (modalOrgName) {
        modalOrgName.textContent = orgName;
    }
    
    // Store current organization
    modal.dataset.orgId = orgId;
    modal.dataset.orgName = orgName;
    
    // Load outcomes for this organization
    loadOutcomesForOrganization(orgId);
    
    // Show modal
    openModal('outcomesModal');
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
    
    // Load POs
    fetch(`/core/api/program-outcomes/${programId}/?type=PO`)
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
    fetch(`/core/api/program-outcomes/${programId}/?type=PSO`)
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
        item.innerHTML = `
            <div class="outcome-text">${outcome.description}</div>
            <div class="outcome-actions">
                <button class="edit-outcome-btn" data-outcome-id="${outcome.id}" data-description="${outcome.description.replace(/"/g, '&quot;')}" data-type="${type}">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="delete-outcome-btn" data-outcome-id="${outcome.id}" data-type="${type}">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        
        // Add event listeners for the buttons
        const editBtn = item.querySelector('.edit-outcome-btn');
        const deleteBtn = item.querySelector('.delete-outcome-btn');
        
        editBtn.addEventListener('click', function() {
            const outcomeId = this.dataset.outcomeId;
            const description = this.dataset.description.replace(/&quot;/g, '"');
            const type = this.dataset.type;
            editOutcome(outcomeId, description, type);
        });
        
        deleteBtn.addEventListener('click', function() {
            const outcomeId = this.dataset.outcomeId;
            const type = this.dataset.type;
            deleteOutcome(outcomeId, type);
        });
        
        list.appendChild(item);
    });
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

function loadOutcomes(programId, type) {
    const endpoint = type === 'pos' ? 
        `/api/programs/${programId}/pos/` : 
        `/api/programs/${programId}/psos/`;
        
    fetch(endpoint)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayOutcomes(data.outcomes, type);
            }
        })
        .catch(error => {
            console.error(`Error loading ${type}:`, error);
        });
}

function displayOutcomes(outcomes, type) {
    const listId = type === 'pos' ? 'posList' : 'psosList';
    const list = document.getElementById(listId);
    if (!list) return;

    list.innerHTML = '';
    
    outcomes.forEach(outcome => {
        const item = document.createElement('div');
        item.className = 'outcome-item';
        item.innerHTML = `
            <div class="outcome-text">${outcome.description}</div>
            <div class="outcome-actions">
                <button class="edit-outcome-btn" data-outcome-id="${outcome.id}" data-description="${outcome.description.replace(/"/g, '&quot;')}" data-type="${type}">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="delete-outcome-btn" data-outcome-id="${outcome.id}" data-type="${type}">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        
        // Add event listeners for the buttons
        const editBtn = item.querySelector('.edit-outcome-btn');
        const deleteBtn = item.querySelector('.delete-outcome-btn');
        
        editBtn.addEventListener('click', function() {
            const outcomeId = this.dataset.outcomeId;
            const description = this.dataset.description.replace(/&quot;/g, '"');
            const type = this.dataset.type;
            editOutcome(outcomeId, description, type);
        });
        
        deleteBtn.addEventListener('click', function() {
            const outcomeId = this.dataset.outcomeId;
            const type = this.dataset.type;
            deleteOutcome(outcomeId, type);
        });
        
        list.appendChild(item);
    });
    
    // Setup add button
    const addBtn = document.getElementById(type === 'pos' ? 'addPOBtn' : 'addPSOBtn');
    if (addBtn) {
        addBtn.onclick = function() {
            addOutcome(type);
        };
    }
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
    
    if (modalOrgName) {
        modalOrgName.textContent = orgName;
    }
    
    // Reset form
    document.getElementById('userSearch').value = '';
    document.getElementById('selectedUserId').value = '';
    hideUserDropdown();
    
    // Load current assignment
    loadCurrentAssignment(orgId);
    
    // Setup user search
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
    const roleFilterSelect = document.getElementById('roleFilter');
    
    let searchTimeout = null;
    
    // Handle search input
    userSearchInput.addEventListener('input', function() {
        const query = this.value.trim();
        
        // Clear previous timeout
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }
        
        if (query.length < 2) {
            hideUserDropdown();
            return;
        }
        
        // Debounce search
        searchTimeout = setTimeout(() => {
            searchFacultyUsers(orgId, query);
        }, 300);
    });
    
    // Handle role filter change
    roleFilterSelect.addEventListener('change', function() {
        const query = userSearchInput.value.trim();
        if (query.length >= 2) {
            searchFacultyUsers(orgId, query);
        } else {
            // If no search query, show users for selected role
            loadUsersByRole(orgId);
        }
    });
    
    // Hide dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!userSearchInput.contains(e.target) && 
            !userDropdown.contains(e.target) && 
            !roleFilterSelect.contains(e.target)) {
            hideUserDropdown();
        }
    });
}

function loadUsersByRole(orgId) {
    const roleFilter = document.getElementById('roleFilter').value;
    const userDropdown = document.getElementById('userDropdown');
    
    // Show loading
    userDropdown.innerHTML = '<div class="loading">Loading users...</div>';
    showUserDropdown();
    
    let url = `/core/api/faculty-users/${orgId}/`;
    if (roleFilter) {
        url += `?role=${encodeURIComponent(roleFilter)}`;
    }
    
    fetch(url)
        .then(response => response.json())
        .then(users => {
            displayUserOptions(users);
        })
        .catch(error => {
            console.error('Error loading users:', error);
            userDropdown.innerHTML = '<div class="no-users">Error loading users</div>';
        });
}

function searchFacultyUsers(orgId, query) {
    const userDropdown = document.getElementById('userDropdown');
    const roleFilter = document.getElementById('roleFilter').value;
    
    // Show loading
    userDropdown.innerHTML = '<div class="loading">Searching users...</div>';
    showUserDropdown();
    
    let url = `/core/api/faculty-users/${orgId}/?search=${encodeURIComponent(query)}`;
    if (roleFilter) {
        url += `&role=${encodeURIComponent(roleFilter)}`;
    }
    
    fetch(url)
        .then(response => response.json())
        .then(users => {
            displayUserOptions(users);
        })
        .catch(error => {
            console.error('Error searching users:', error);
            userDropdown.innerHTML = '<div class="no-users">Error loading users</div>';
        });
}

function displayUserOptions(users) {
    const userDropdown = document.getElementById('userDropdown');
    
    if (users.length === 0) {
        userDropdown.innerHTML = '<div class="no-users">No faculty users found</div>';
        return;
    }
    
    userDropdown.innerHTML = '';
    
    users.forEach(user => {
        const option = document.createElement('div');
        option.className = 'user-option';
        option.dataset.userId = user.id;
        
        option.innerHTML = `
            <div class="user-info">
                <div class="user-name">${user.full_name}</div>
                <div class="user-details">${user.email} • ${user.roles.join(', ')}</div>
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
    userDropdown.classList.add('show');
}

function hideUserDropdown() {
    const userDropdown = document.getElementById('userDropdown');
    userDropdown.classList.remove('show');
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
    
    if (assignedUser) {
        assignedNameSpan.textContent = assignedUser.full_name;
        assignedUserDiv.classList.add('has-assignment');
        assignBtn.innerHTML = '<i class="fas fa-user-edit"></i> Change';
        assignBtn.classList.add('assigned');
    } else {
        assignedNameSpan.textContent = 'Unassigned';
        assignedUserDiv.classList.remove('has-assignment');
        assignBtn.innerHTML = '<i class="fas fa-user-plus"></i> Assign';
        assignBtn.classList.remove('assigned');
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

    // Modal close functionality
    setupModalEvents();
}
