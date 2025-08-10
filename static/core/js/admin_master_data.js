/**
 * Admin Master Data JavaScript
 * Handles inline editing, search, and CRUD operations for master data management
 */

// Global variables
let orgsByType = {};
let currentEditingRow = null;

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', function() {
    // Wait a bit for the orgsByType data to be loaded from the template
    setTimeout(initializeMasterData, 100);
});

function initializeMasterData() {
    // Update orgsByType from global scope if it exists
    if (typeof window.orgsByType !== 'undefined') {
        orgsByType = window.orgsByType;
    } else if (typeof orgsByType !== 'undefined' && Object.keys(orgsByType).length === 0) {
        // Try to get from global scope one more time
        setTimeout(() => {
            if (typeof window.orgsByType !== 'undefined') {
                orgsByType = window.orgsByType;
                console.log('Delayed orgsByType initialization:', orgsByType);
            }
        }, 500);
    }
    
    // Initialize search functionality
    initializeSearch();
    
    // Initialize inline editing
    initializeInlineEditing();
    
    // Initialize form handlers
    initializeFormHandlers();
    
    // Initialize academic year functionality
    initializeAcademicYear();
    
    // Show success message if redirected after operation
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('success')) {
        showToast('Operation completed successfully!', 'success');
    }
    
    console.log('Master data initialized', { orgsByType, elementsFound: {
        categorySelect: !!document.getElementById("categorySelect"),
        addNewEntryBtn: !!document.getElementById("addNewEntryBtn"),
        addFormContainer: !!document.getElementById("add-form-container")
    }});
}

// Search functionality
function initializeSearch() {
    const searchInput = document.getElementById('universalSearch');
    const searchNotFound = document.getElementById('search-not-found');
    
    if (!searchInput || !searchNotFound) {
        console.warn('Search elements not found');
        return;
    }
    
    const searchNotFoundText = searchNotFound.querySelector('strong');
    const addFromSearchBtn = document.getElementById('addFromSearchBtn');
    
    searchInput.addEventListener('input', function() {
        const query = this.value.toLowerCase().trim();
        const widgets = document.querySelectorAll('.data-widget');
        let hasResults = false;
        
        widgets.forEach(widget => {
            const rows = widget.querySelectorAll('tbody tr');
            let widgetHasResults = false;
            
            rows.forEach(row => {
                if (row.querySelector('td[colspan]')) return; // Skip empty rows
                
                const nameCell = row.querySelector('td[data-label="Name"]');
                if (nameCell && nameCell.textContent.toLowerCase().includes(query)) {
                    row.style.display = '';
                    widgetHasResults = true;
                    hasResults = true;
                } else {
                    row.style.display = 'none';
                }
            });
            
            // Show/hide widget based on results
            widget.style.display = widgetHasResults || query === '' ? 'block' : 'none';
        });
        
        // Show/hide "not found" message
        if (query && !hasResults) {
            if (searchNotFoundText) searchNotFoundText.textContent = query;
            searchNotFound.style.display = 'block';
            
            if (addFromSearchBtn) {
                addFromSearchBtn.onclick = function() {
                    addNewEntryFromSearch(query);
                };
            }
        } else {
            searchNotFound.style.display = 'none';
        }
    });
}

// Inline editing functionality
function initializeInlineEditing() {
    document.addEventListener('click', function(e) {
        if (e.target.closest('.btn-edit')) {
            e.preventDefault();
            const row = e.target.closest('tr');
            startInlineEdit(row);
        } else if (e.target.closest('.btn-row-save')) {
            e.preventDefault();
            const row = e.target.closest('tr');
            saveInlineEdit(row);
        } else if (e.target.closest('.btn-row-cancel')) {
            e.preventDefault();
            const row = e.target.closest('tr');
            cancelInlineEdit(row);
        }
    });
}

function startInlineEdit(row) {
    if (currentEditingRow && currentEditingRow !== row) {
        cancelInlineEdit(currentEditingRow);
    }
    
    currentEditingRow = row;
    row.classList.add('editing-row');
    
    const nameCell = row.querySelector('td[data-label="Name"]');
    const parentCell = row.querySelector('td[data-label="Parent"]');
    const statusCell = row.querySelector('td[data-label="Status"]');
    const actionsCell = row.querySelector('td[data-label="Actions"]');
    
    // Store original values
    const originalName = nameCell.textContent.trim();
    const originalParent = parentCell ? parentCell.textContent.trim() : null;
    const originalStatus = statusCell.querySelector('.status-badge').classList.contains('status-active');
    
    row.dataset.originalName = originalName;
    row.dataset.originalParent = originalParent || '';
    row.dataset.originalStatus = originalStatus;
    
    // Replace name with input
    nameCell.innerHTML = `<input type="text" class="inline-edit-input" value="${originalName}">`;
    
    // Replace parent with select (if parent cell exists)
    if (parentCell) {
        const widget = row.closest('.data-widget');
        const widgetName = widget.dataset.widgetName;
        const orgTypeName = getOrgTypeFromWidgetName(widgetName);
        
        console.log('Editing row with parent:', { widgetName, orgTypeName, originalParent });
        
        let parentOptions = '<option value="">-- No Parent --</option>';
        
        // Get the parent type for this organization type
        const parentType = getParentTypeForOrgType(orgTypeName);
        console.log('Parent type for', orgTypeName, ':', parentType);
        
        if (parentType && orgsByType[parentType]) {
            orgsByType[parentType].forEach(org => {
                const selected = org.name === originalParent && originalParent !== '-' ? 'selected' : '';
                parentOptions += `<option value="${org.id}" ${selected}>${org.name}</option>`;
            });
        } else if (parentType) {
            console.warn('No organizations found for parent type:', parentType, 'Available types:', Object.keys(orgsByType));
        }
        
        parentCell.innerHTML = `<select class="inline-edit-select">${parentOptions}</select>`;
    }
    
    // Replace status with select
    statusCell.innerHTML = `
        <select class="inline-edit-select">
            <option value="true" ${originalStatus ? 'selected' : ''}>Active</option>
            <option value="false" ${!originalStatus ? 'selected' : ''}>Inactive</option>
        </select>
    `;
    
    // Replace actions
    actionsCell.innerHTML = `
        <button class="btn btn-row-save"><i class="fas fa-check"></i></button>
        <button class="btn btn-row-cancel"><i class="fas fa-times"></i></button>
    `;
}

function saveInlineEdit(row) {
    const id = row.dataset.id;
    const widget = row.closest('.data-widget');
    const modelName = getModelNameFromWidget(widget);
    
    const nameInput = row.querySelector('.inline-edit-input');
    const parentCell = row.querySelector('td[data-label="Parent"]');
    const parentSelect = parentCell ? parentCell.querySelector('.inline-edit-select') : null;
    const statusSelect = row.querySelector('td[data-label="Status"] .inline-edit-select');
    
    const newName = nameInput.value.trim();
    const newParent = parentSelect ? parentSelect.value : null;
    const newStatus = statusSelect.value === 'true';
    
    if (!newName) {
        showToast('Name cannot be empty', 'error');
        return;
    }
    
    // Show loading state
    const actionsCell = row.querySelector('td[data-label="Actions"]');
    actionsCell.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    
    // Prepare the data to send
    const updateData = {
        name: newName,
        is_active: newStatus
    };
    
    // Include parent if this organization type supports it
    if (parentSelect) {
        updateData.parent = newParent || null;
    }
    
    fetch(`/core-admin/settings/${modelName}/${id}/edit/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(updateData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Use the parent name from the response if available, otherwise find it locally
            const parentName = data.parent || (newParent ? getOrgNameById(newParent) : null);
            finishInlineEdit(row, newName, newStatus, parentName);
            showToast('Updated successfully!', 'success');
        } else {
            throw new Error(data.error || 'Failed to update');
        }
    })
    .catch(error => {
        showToast(error.message, 'error');
        cancelInlineEdit(row);
    });
}

function cancelInlineEdit(row) {
    const originalName = row.dataset.originalName;
    const originalParent = row.dataset.originalParent;
    const originalStatus = row.dataset.originalStatus === 'true';
    
    finishInlineEdit(row, originalName, originalStatus, originalParent === '' ? null : originalParent);
    
    delete row.dataset.originalName;
    delete row.dataset.originalParent;
    delete row.dataset.originalStatus;
}

function finishInlineEdit(row, name, isActive, parentName = null) {
    row.classList.remove('editing-row');
    currentEditingRow = null;
    
    const nameCell = row.querySelector('td[data-label="Name"]');
    const parentCell = row.querySelector('td[data-label="Parent"]');
    const statusCell = row.querySelector('td[data-label="Status"]');
    const actionsCell = row.querySelector('td[data-label="Actions"]');
    
    // Restore name
    nameCell.textContent = name;
    
    // Restore parent (if parent cell exists)
    if (parentCell) {
        parentCell.textContent = parentName && parentName !== '-' ? parentName : '-';
    }
    
    // Restore status
    statusCell.innerHTML = `
        <span class="status-badge status-${isActive ? 'active' : 'inactive'}">
            ${isActive ? 'Active' : 'Inactive'}
        </span>
    `;
    
    // Restore actions
    actionsCell.innerHTML = `
        <button class="btn btn-edit"><i class="fas fa-pen"></i></button>
        <a class="btn btn-primary btn-sm" title="Add Users" href="/core-admin/org-users/${row.dataset.id}/">
            <i class="fas fa-user-plus"></i>
        </a>
    `;
    
    // Update row class for inactive display
    if (isActive) {
        row.classList.remove('inactive-row-display');
    } else {
        row.classList.add('inactive-row-display');
    }
}

// Form handlers
function initializeFormHandlers() {
    const categorySelect = document.getElementById("categorySelect");
    const parentOrgGroup = document.getElementById("parent-organization-group");
    const parentOrgSelect = document.getElementById("parentOrganizationSelect");

    function handleCategoryChange() {
        if (!categorySelect || !parentOrgGroup || !parentOrgSelect) {
            console.warn('Category form elements not found');
            return;
        }
        
        const selectedOption = categorySelect.options[categorySelect.selectedIndex];
        if (!selectedOption) return;
        
        const canHaveParent = selectedOption.getAttribute('data-can-have-parent') === 'true';
        const parentType = selectedOption.getAttribute('data-parent-type');
        parentOrgGroup.style.display = canHaveParent ? 'block' : 'none';

        if (canHaveParent && parentType && orgsByType[parentType]) {
            parentOrgSelect.innerHTML = `<option value="" disabled selected>Select Parent</option>`;
            orgsByType[parentType].forEach(org => {
                parentOrgSelect.innerHTML += `<option value="${org.id}">${org.name}</option>`;
            });
        } else {
            parentOrgSelect.innerHTML = `<option value="" disabled selected>Select Parent</option>`;
        }
    }

    if (categorySelect) {
        categorySelect.addEventListener('change', handleCategoryChange);
        // Run initial setup
        setTimeout(handleCategoryChange, 200);
    }

    // Add entry form handlers
    const addNewEntryBtn = document.getElementById("addNewEntryBtn");
    const addEntryCancelBtn = document.getElementById("addEntryCancelBtn");
    const addEntryConfirmBtn = document.getElementById("addEntryConfirmBtn");

    if (addNewEntryBtn) {
        addNewEntryBtn.onclick = function(e) {
            e.preventDefault();
            console.log('Add new entry clicked');
            const addFormContainer = document.getElementById("add-form-container");
            const addCategoryContainer = document.getElementById("add-category-container");
            
            if (addFormContainer) addFormContainer.style.display = "block";
            if (addCategoryContainer) addCategoryContainer.style.display = "none";
            handleCategoryChange();
        };
    } else {
        console.warn('Add new entry button not found');
    }

    if (addEntryCancelBtn) {
        addEntryCancelBtn.onclick = function(e) {
            e.preventDefault();
            const addFormContainer = document.getElementById("add-form-container");
            const newEntryName = document.getElementById("newEntryName");
            
            if (addFormContainer) addFormContainer.style.display = "none";
            if (newEntryName) newEntryName.value = "";
            if (parentOrgSelect) parentOrgSelect.value = "";
        };
    }

    if (addEntryConfirmBtn) {
        addEntryConfirmBtn.onclick = function(e) {
            e.preventDefault();
            addNewEntry();
        };
    }

    // Add category form handlers
    const addNewCategoryBtn = document.getElementById("addNewCategoryBtn");
    const addCategoryCancelBtn = document.getElementById("addCategoryCancelBtn");
    const addCategoryConfirmBtn = document.getElementById("addCategoryConfirmBtn");
    const hasParentCategory = document.getElementById("hasParentCategory");

    if (addNewCategoryBtn) {
        addNewCategoryBtn.onclick = function(e) {
            e.preventDefault();
            const addCategoryContainer = document.getElementById("add-category-container");
            const addFormContainer = document.getElementById("add-form-container");
            
            if (addCategoryContainer) addCategoryContainer.style.display = "block";
            if (addFormContainer) addFormContainer.style.display = "none";
        };
    }

    if (addCategoryCancelBtn) {
        addCategoryCancelBtn.onclick = function(e) {
            e.preventDefault();
            const addCategoryContainer = document.getElementById("add-category-container");
            const newCategoryName = document.getElementById("newCategoryName");
            const hasParentCategory = document.getElementById("hasParentCategory");
            const parentCategoryGroup = document.getElementById("parentCategoryGroup");
            const parentCategorySelect = document.getElementById("parentCategorySelect");
            
            if (addCategoryContainer) addCategoryContainer.style.display = "none";
            if (newCategoryName) newCategoryName.value = "";
            if (hasParentCategory) hasParentCategory.checked = false;
            if (parentCategoryGroup) parentCategoryGroup.style.display = "none";
            if (parentCategorySelect) parentCategorySelect.value = "";
        };
    }

    if (hasParentCategory) {
        hasParentCategory.onchange = function() {
            const parentCategoryGroup = document.getElementById("parentCategoryGroup");
            const parentCategorySelect = document.getElementById("parentCategorySelect");
            
            if (parentCategoryGroup) {
                parentCategoryGroup.style.display = this.checked ? "block" : "none";
            }
            if (!this.checked && parentCategorySelect) {
                parentCategorySelect.value = "";
            }
        };
    }

    if (addCategoryConfirmBtn) {
        addCategoryConfirmBtn.onclick = function(e) {
            e.preventDefault();
            addNewCategory();
        };
    }
}

// Academic Year functionality
function initializeAcademicYear() {
    const academicYearSelect = document.querySelector('#academicYearSelect');
    if (academicYearSelect && academicYearSelect.value) {
        localStorage.setItem('selectedAcademicYear', academicYearSelect.value);
    }
}

function setAcademicYear(year) {
    localStorage.setItem('selectedAcademicYear', year);
    fetch('/core-admin/set-academic-year/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ academic_year: year })
    }).then(() => {
        window.location.href = '?year=' + encodeURIComponent(year);
    }).catch(() => {
        window.location.href = '?year=' + encodeURIComponent(year);
    });
}

function showAddAcademicYearForm() {
    const year = prompt("Enter new academic year (format: YYYY-YYYY):\nExample: 2025-2026");
    if (year && year.match(/^\d{4}-\d{4}$/)) {
        addAcademicYear(year);
    } else if (year) {
        showToast("Please enter academic year in correct format: YYYY-YYYY (e.g., 2025-2026)", 'error');
    }
}

function addAcademicYear(yearString) {
    fetch('/core-admin/add-academic-year/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ academic_year: yearString })
    }).then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.reload();
        } else {
            showToast(data.error || 'Failed to add academic year', 'error');
        }
    }).catch(() => {
        showToast('Error adding academic year', 'error');
    });
}

// CRUD Operations
function addNewEntry() {
    const categorySelect = document.getElementById("categorySelect");
    const parentOrgSelect = document.getElementById("parentOrganizationSelect");
    const name = document.getElementById("newEntryName").value.trim();
    const selectedOption = categorySelect.options[categorySelect.selectedIndex];
    const category = categorySelect.value;
    const canHaveParent = selectedOption.getAttribute('data-can-have-parent') === 'true';
    
    let parent = null;
    if (canHaveParent) {
        parent = parentOrgSelect.value;
        if (!parent) {
            showToast("Please select the parent organization.", 'error');
            return;
        }
    }
    
    if (!name) {
        showToast("Please enter a name.", 'error');
        return;
    }
    
    let postData = { name: name, org_type: category };
    if (parent) postData.parent = parent;

    // Show loading state
    const confirmBtn = document.getElementById("addEntryConfirmBtn");
    const originalText = confirmBtn.innerHTML;
    confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...';
    confirmBtn.disabled = true;

    fetch("/core-admin/settings/organization/add/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken()
        },
        body: JSON.stringify(postData)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast('Entry added successfully!', 'success');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            throw new Error(data.error || "Failed to add entry.");
        }
    })
    .catch(error => {
        showToast(error.message, 'error');
    })
    .finally(() => {
        confirmBtn.innerHTML = originalText;
        confirmBtn.disabled = false;
    });
}

function addNewCategory() {
    const name = document.getElementById("newCategoryName").value.trim();
    const hasParent = document.getElementById("hasParentCategory").checked;
    let parent = null;
    
    if (hasParent) {
        parent = document.getElementById("parentCategorySelect").value;
        if (!parent) {
            showToast("Please select a parent category.", 'error');
            return;
        }
    }
    
    if (!name) {
        showToast("Enter a category name.", 'error');
        return;
    }
    
    let payload = { name: name };
    if (parent) payload.parent = parent;

    // Show loading state
    const confirmBtn = document.getElementById("addCategoryConfirmBtn");
    const originalText = confirmBtn.innerHTML;
    confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...';
    confirmBtn.disabled = true;

    fetch("/core-admin/settings/organization_type/add/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken()
        },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast('Category added successfully!', 'success');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            throw new Error(data.error || "Failed to add category.");
        }
    })
    .catch(error => {
        showToast(error.message, 'error');
    })
    .finally(() => {
        confirmBtn.innerHTML = originalText;
        confirmBtn.disabled = false;
    });
}

function addNewEntryFromSearch(query) {
    document.getElementById("newEntryName").value = query;
    document.getElementById("add-form-container").style.display = "block";
    document.getElementById("search-not-found").style.display = "none";
    document.getElementById("universalSearch").value = "";
    
    // Reset search results
    const widgets = document.querySelectorAll('.data-widget');
    widgets.forEach(widget => {
        widget.style.display = 'block';
        const rows = widget.querySelectorAll('tbody tr');
        rows.forEach(row => {
            row.style.display = '';
        });
    });
}

// Utility functions
function getModelNameFromWidget(widget) {
    const widgetName = widget.dataset.widgetName;
    // Map widget names to model names
    const modelMap = {
        'department': 'organization',
        'club': 'organization',
        'center': 'organization',
        'cell': 'organization',
        'association': 'organization',
        'committee': 'organization'
    };
    return modelMap[widgetName] || 'organization';
}

function getOrgTypeFromWidgetName(widgetName) {
    // Map widget names to organization type names (for finding parent types)
    const orgTypeMap = {
        'department': 'department',
        'club': 'club',
        'center': 'center',
        'cell': 'cell',
        'association': 'association',
        'committee': 'committee'
    };
    return orgTypeMap[widgetName] || widgetName;
}

function getParentTypeForOrgType(orgTypeName) {
    // First, try to get parent type from the category select options in the DOM
    const categorySelect = document.getElementById("categorySelect");
    if (categorySelect) {
        for (let option of categorySelect.options) {
            if (option.value.toLowerCase() === orgTypeName.toLowerCase()) {
                const parentType = option.getAttribute('data-parent-type');
                return parentType ? parentType.toLowerCase() : null;
            }
        }
    }
    
    // Fallback to hardcoded mapping if DOM method fails
    const parentTypeMap = {
        'department': 'school',
        'club': 'department',
        'cell': 'department',
        'committee': 'department',
        'association': 'department'
    };
    return parentTypeMap[orgTypeName.toLowerCase()];
}

function getOrgNameById(orgId) {
    // Search through all organization types to find the organization by ID
    for (const orgType in orgsByType) {
        const org = orgsByType[orgType].find(o => o.id == orgId);
        if (org) {
            return org.name;
        }
    }
    return null;
}

function getCsrfToken() {
    const token = document.querySelector('[name=csrfmiddlewaretoken]');
    if (token) return token.value;
    
    // Try to get from cookie
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') return value;
    }
    
    // Fallback to meta tag if available
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast-notification') || createToastElement();
    
    toast.textContent = message;
    toast.className = `toast toast-${type} show`;
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 4000);
}

function createToastElement() {
    const toast = document.createElement('div');
    toast.id = 'toast-notification';
    toast.className = 'toast';
    document.body.appendChild(toast);
    return toast;
}

// Export functions for global access
window.setAcademicYear = setAcademicYear;
window.showAddAcademicYearForm = showAddAcademicYearForm;
window.addAcademicYear = addAcademicYear;
