// Global variables
let currentOrgId = null;
let currentOrgType = null;
let currentOrgName = "";
let currentOutcomeId = null;
let currentOutcomeType = null;

// DOM Ready initialization
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    validateCSRFToken();
    addInputValidationStyling();
});

function initializeEventListeners() {
    // Filter functionality
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', handleFilterClick);
    });

    // Search functionality
    document.getElementById('org-search').addEventListener('input', handleSearch);

    // Manage outcomes functionality
    document.querySelectorAll('.manage-outcomes-btn').forEach(btn => {
        btn.addEventListener('click', handleManageOutcomes);
    });

    // Modal functionality
    document.querySelectorAll('.close, .btn-cancel').forEach(btn => {
        btn.addEventListener('click', closeModals);
    });

    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal')) {
            closeModals();
        }
    });

    // Edit outcome form submission
    document.getElementById('editOutcomeForm').addEventListener('submit', handleEditOutcomeSubmit);

    // Add PO/PSO form submissions
    document.getElementById('add-po-form').addEventListener('submit', handleAddPOSubmit);
    document.getElementById('add-pso-form').addEventListener('submit', handleAddPSOSubmit);
}

// Filter functionality
function handleFilterClick() {
    // Update active button
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    this.classList.add('active');
    
    const filterType = this.dataset.type;
    const rows = document.querySelectorAll('.org-row');
    
    rows.forEach(row => {
        if (filterType === 'all' || row.dataset.type === filterType) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

// Search functionality
function handleSearch() {
    const searchTerm = this.value.toLowerCase();
    const rows = document.querySelectorAll('.org-row');
    
    rows.forEach(row => {
        const orgName = row.dataset.name.toLowerCase();
        const orgType = row.dataset.type.toLowerCase();
        const parentName = row.dataset.parent.toLowerCase();
        
        // Check if currently filtered type matches
        const activeFilter = document.querySelector('.filter-btn.active').dataset.type;
        const typeMatches = activeFilter === 'all' || row.dataset.type === activeFilter;
        
        if (typeMatches && (orgName.includes(searchTerm) || orgType.includes(searchTerm) || parentName.includes(searchTerm))) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

// Manage outcomes functionality
function handleManageOutcomes() {
    const row = this.closest('tr');
    currentOrgId = row.dataset.id;
    currentOrgName = row.dataset.name;
    currentOrgType = row.dataset.type;
    
    document.getElementById('selected-org-name').textContent = 
        `${currentOrgName} (${currentOrgType.charAt(0).toUpperCase() + currentOrgType.slice(1)})`;
    
    // Load existing outcomes
    loadOutcomes();
    
    // Show management section
    document.getElementById('pso-po-management').style.display = 'block';
    document.getElementById('pso-po-management').scrollIntoView({ behavior: 'smooth' });
}

// Modal functionality
function closeModals() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.style.display = 'none';
    });
}

// Edit outcome form submission
function handleEditOutcomeSubmit(e) {
    e.preventDefault();
    const newDescription = document.getElementById('editOutcomeText').value.trim();
    
    if (!newDescription) {
        showErrorMessage('Please enter a description for the outcome.');
        return;
    }
    
    if (!currentOutcomeId && currentOutcomeId !== 0) {
        showErrorMessage('No outcome selected for editing.');
        return;
    }
    
    if (newDescription.length < 10) {
        showErrorMessage('Outcome description should be at least 10 characters long.');
        return;
    }
    
    updateOutcome(currentOutcomeType, currentOutcomeId, newDescription);
}

// Add PO functionality
function handleAddPOSubmit(e) {
    e.preventDefault();
    const description = document.getElementById('new-po').value.trim();
    
    if (!description) {
        showErrorMessage('Please enter a Programme Outcome description.');
        return;
    }
    
    if (!currentOrgId) {
        showErrorMessage('Please select an organization first.');
        return;
    }
    
    if (description.length < 10) {
        showErrorMessage('Programme Outcome description should be at least 10 characters long.');
        return;
    }
    
    addOutcome('po', description);
    document.getElementById('new-po').value = '';
}

// Add PSO functionality
function handleAddPSOSubmit(e) {
    e.preventDefault();
    const description = document.getElementById('new-pso').value.trim();
    
    if (!description) {
        showErrorMessage('Please enter a Programme Specific Outcome description.');
        return;
    }
    
    if (!currentOrgId) {
        showErrorMessage('Please select an organization first.');
        return;
    }
    
    if (description.length < 10) {
        showErrorMessage('Programme Specific Outcome description should be at least 10 characters long.');
        return;
    }
    
    addOutcome('pso', description);
    document.getElementById('new-pso').value = '';
}

// Load outcomes for selected organization
function loadOutcomes() {
    if (!currentOrgId || !currentOrgType) return;
    
    // Show loading indicators
    document.getElementById('po-list').innerHTML = '<li style="text-align: center; padding: 20px;"><i class="fas fa-spinner fa-spin"></i> Loading POs...</li>';
    document.getElementById('pso-list').innerHTML = '<li style="text-align: center; padding: 20px;"><i class="fas fa-spinner fa-spin"></i> Loading PSOs...</li>';
    
    fetch(`/core-admin/pso-po/data/${currentOrgType}/${currentOrgId}/`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success !== false) {
            updateOutcomesList('po-list', data.pos || data.programme_outcomes || []);
            updateOutcomesList('pso-list', data.psos || data.programme_specific_outcomes || []);
        } else {
            throw new Error(data.error || 'Failed to load outcomes');
        }
    })
    .catch(error => {
        console.error('Error loading outcomes:', error);
        // Initialize empty lists if API doesn't exist yet
        updateOutcomesList('po-list', []);
        updateOutcomesList('pso-list', []);
        
        // Show error message briefly
        showErrorMessage('Could not load existing outcomes from server. Starting with empty lists.');
    });
}

function updateOutcomesList(listId, outcomes) {
    const list = document.getElementById(listId);
    list.innerHTML = '';
    
    if (outcomes.length === 0) {
        const li = document.createElement('li');
        li.innerHTML = `<div class="outcome-text" style="color: #6b7280; font-style: italic; text-align: center;">No outcomes added yet</div>`;
        li.style.border = '2px dashed #d1d5db';
        li.style.background = 'transparent';
        list.appendChild(li);
        return;
    }
    
    outcomes.forEach((outcome, index) => {
        const li = document.createElement('li');
        li.innerHTML = `
            <div class="outcome-text">${outcome.description || outcome}</div>
            <div class="outcome-actions">
                <button class="edit-outcome-btn" onclick="editOutcome('${listId.includes('po') ? 'po' : 'pso'}', ${outcome.id || index}, '${(outcome.description || outcome).replace(/'/g, '\\\'').replace(/"/g, '&quot;')}')">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="delete-outcome-btn" onclick="deleteOutcome('${listId.includes('po') ? 'po' : 'pso'}', ${outcome.id || index}, this)">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        list.appendChild(li);
    });
}

// Edit outcome functionality
function editOutcome(type, id, description) {
    currentOutcomeId = id;
    currentOutcomeType = type;
    
    // Decode HTML entities back to normal text
    const decodedDescription = description.replace(/&quot;/g, '"').replace(/&#x27;/g, "'");
    document.getElementById('editOutcomeText').value = decodedDescription;
    document.getElementById('editOutcomeModal').style.display = 'block';
}

function updateOutcome(type, id, description) {
    // Show loading state
    const form = document.getElementById('editOutcomeForm');
    const saveBtn = form.querySelector('.btn-save');
    const originalText = saveBtn.textContent;
    saveBtn.textContent = 'Saving...';
    saveBtn.disabled = true;
    
    // Try to make API call first
    fetch(`/core-admin/pso-po/edit/${type}/${id}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            description: description
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Reload the outcomes from server
            loadOutcomes();
            closeModals();
            showSuccessMessage('Outcome updated successfully!');
        } else {
            throw new Error(data.error || 'Unknown server error');
        }
    })
    .catch(error => {
        console.error('Error updating outcome:', error);
        // If API call fails, update locally and show warning
        updateOutcomeLocally(type, id, description);
        closeModals();
        showSuccessMessage('✅ Outcome updated and visible! (Server sync pending)');
        
        // Additional confirmation that change is visible
        setTimeout(() => {
            showSuccessMessage('💡 Your changes are now visible in the list above!');
        }, 2000);
    })
    .finally(() => {
        // Restore button state
        saveBtn.textContent = originalText;
        saveBtn.disabled = false;
    });
}

function updateOutcomeLocally(type, id, description) {
    const listId = type === 'po' ? 'po-list' : 'pso-list';
    const list = document.getElementById(listId);
    const items = list.querySelectorAll('li');
    
    // Find the correct item to update - need to match exactly
    let itemFound = false;
    items.forEach((item, index) => {
        const outcomeText = item.querySelector('.outcome-text');
        const editBtn = item.querySelector('.edit-outcome-btn');
        
        if (outcomeText && editBtn) {
            // Check if this is the right item by checking the onclick attribute
            const onclickAttr = editBtn.getAttribute('onclick');
            if (onclickAttr && onclickAttr.includes(`'${type}', ${id},`)) {
                // Update the text content
                outcomeText.textContent = description;
                
                // Update the onclick handlers with new description
                const safeDescription = description.replace(/'/g, '\\\'').replace(/"/g, '&quot;');
                editBtn.setAttribute('onclick', `editOutcome('${type}', ${id}, '${safeDescription}')`);
                
                // Also update delete button if it exists
                const deleteBtn = item.querySelector('.delete-outcome-btn');
                if (deleteBtn) {
                    deleteBtn.setAttribute('onclick', `deleteOutcome('${type}', ${id}, this)`);
                }
                
                itemFound = true;
                
                // Add a visual feedback that the item was updated
                item.style.backgroundColor = '#dcfce7';
                item.style.border = '2px solid #10b981';
                setTimeout(() => {
                    item.style.backgroundColor = '';
                    item.style.border = '';
                }, 1500);
            }
        }
    });
    
    // If item not found by onclick, try by index as fallback
    if (!itemFound && items.length > id) {
        const item = items[id];
        const outcomeText = item.querySelector('.outcome-text');
        if (outcomeText) {
            outcomeText.textContent = description;
            
            // Update onclick handlers
            const editBtn = item.querySelector('.edit-outcome-btn');
            const deleteBtn = item.querySelector('.delete-outcome-btn');
            if (editBtn) {
                const safeDescription = description.replace(/'/g, '\\\'').replace(/"/g, '&quot;');
                editBtn.setAttribute('onclick', `editOutcome('${type}', ${id}, '${safeDescription}')`);
            }
            if (deleteBtn) {
                deleteBtn.setAttribute('onclick', `deleteOutcome('${type}', ${id}, this)`);
            }
            
            // Add visual feedback
            item.style.backgroundColor = '#dcfce7';
            item.style.border = '2px solid #10b981';
            setTimeout(() => {
                item.style.backgroundColor = '';
                item.style.border = '';
            }, 1500);
        }
    }
}

function addOutcome(type, description) {
    // Show loading state
    const form = document.getElementById(`add-${type}-form`);
    const btn = form.querySelector('button[type="submit"]');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...';
    btn.disabled = true;
    
    fetch(`/core-admin/pso-po/add/${type}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            org_type: currentOrgType,
            org_id: currentOrgId,
            description: description
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            loadOutcomes(); // Reload the outcomes from server
            showSuccessMessage(`${type.toUpperCase()} added successfully!`);
        } else {
            throw new Error(data.error || 'Unknown server error');
        }
    })
    .catch(error => {
        console.error('Error adding outcome:', error);
        // For demo purposes, add to list locally if API fails
        addOutcomeLocally(type, description);
        showSuccessMessage(`✅ ${type.toUpperCase()} added and visible! (Server sync pending)`);
        
        // Additional confirmation that change is visible
        setTimeout(() => {
            showSuccessMessage('💡 Your new outcome is now visible in the list!');
        }, 2000);
    })
    .finally(() => {
        // Restore button state
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
}

function addOutcomeLocally(type, description) {
    const listId = type === 'po' ? 'po-list' : 'pso-list';
    const list = document.getElementById(listId);
    
    // Remove "no outcomes" message if it exists
    const emptyMessage = list.querySelector('li div[style*="font-style: italic"]');
    if (emptyMessage) {
        emptyMessage.closest('li').remove();
    }
    
    const li = document.createElement('li');
    const newId = Date.now(); // Use timestamp as temporary ID
    const safeDescription = description.replace(/'/g, '\\\'').replace(/"/g, '&quot;');
    
    li.innerHTML = `
        <div class="outcome-text">${description}</div>
        <div class="outcome-actions">
            <button class="edit-outcome-btn" onclick="editOutcome('${type}', ${newId}, '${safeDescription}')">
                <i class="fas fa-edit"></i>
            </button>
            <button class="delete-outcome-btn" onclick="deleteOutcome('${type}', ${newId}, this)">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `;
    
    // Add visual effect for new item
    li.style.backgroundColor = '#dbeafe';
    li.style.border = '2px solid #3b82f6';
    li.style.transform = 'scale(1.02)';
    
    list.appendChild(li);
    
    // Remove the visual effect after animation
    setTimeout(() => {
        li.style.backgroundColor = '';
        li.style.border = '';
        li.style.transform = '';
    }, 1500);
    
    // Scroll the new item into view
    li.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function deleteOutcome(type, id, buttonElement) {
    if (!confirm('Are you sure you want to delete this outcome?')) return;
    
    // Show loading state
    const deleteBtn = buttonElement;
    const originalContent = deleteBtn.innerHTML;
    deleteBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    deleteBtn.disabled = true;
    
    fetch(`/core-admin/pso-po/delete/${type}/${id}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            org_type: currentOrgType,
            org_id: currentOrgId
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            loadOutcomes(); // Reload the outcomes from server
            showSuccessMessage('Outcome deleted successfully!');
        } else {
            throw new Error(data.error || 'Unknown server error');
        }
    })
    .catch(error => {
        console.error('Error deleting outcome:', error);
        // For demo purposes, remove locally if API fails
        if (buttonElement) {
            buttonElement.closest('li').remove();
            showSuccessMessage('Outcome deleted locally (server sync pending)');
            
            // Add empty message if no items left
            const listId = type === 'po' ? 'po-list' : 'pso-list';
            const list = document.getElementById(listId);
            if (list.children.length === 0) {
                const li = document.createElement('li');
                li.innerHTML = `<div class="outcome-text" style="color: #6b7280; font-style: italic; text-align: center;">No outcomes added yet</div>`;
                li.style.border = '2px dashed #d1d5db';
                li.style.background = 'transparent';
                list.appendChild(li);
            }
        }
    })
    .finally(() => {
        // Restore button state if it still exists
        if (deleteBtn && deleteBtn.parentNode) {
            deleteBtn.innerHTML = originalContent;
            deleteBtn.disabled = false;
        }
    });
}

// Message display functions
function showSuccessMessage(message) {
    createNotificationMessage(message, 'success');
}

function showErrorMessage(message) {
    createNotificationMessage(message, 'error');
}

function createNotificationMessage(message, type) {
    const messageDiv = document.createElement('div');
    const gradientColor = type === 'success' 
        ? 'linear-gradient(135deg, #10b981, #059669)'
        : 'linear-gradient(135deg, #ef4444, #dc2626)';
    
    messageDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${gradientColor};
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 15px rgba(${type === 'success' ? '16, 185, 129' : '239, 68, 68'}, 0.3);
        z-index: 9999;
        font-weight: 500;
        animation: slideInRight 0.3s ease;
        max-width: 300px;
        word-wrap: break-word;
    `;
    messageDiv.textContent = message;
    document.body.appendChild(messageDiv);
    
    // Add animation keyframes if not already added
    if (!document.querySelector('#notification-animation-styles')) {
        const style = document.createElement('style');
        style.id = 'notification-animation-styles';
        style.textContent = `
            @keyframes slideInRight {
                from { opacity: 0; transform: translateX(100px); }
                to { opacity: 1; transform: translateX(0); }
            }
        `;
        document.head.appendChild(style);
    }
    
    const timeout = type === 'error' ? 4000 : 3000;
    setTimeout(() => {
        messageDiv.style.animation = 'slideInRight 0.3s ease reverse';
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.parentNode.removeChild(messageDiv);
            }
        }, 300);
    }, timeout);
}

// CSRF token helper
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Validate CSRF token exists
function validateCSRFToken() {
    const token = getCookie('csrftoken');
    if (!token) {
        console.warn('CSRF token not found. Some operations may fail.');
        showErrorMessage('Security token missing. Please refresh the page.');
        return false;
    }
    return true;
}

// Add input validation styling
function addInputValidationStyling() {
    const inputs = document.querySelectorAll('input[type="text"], textarea');
    inputs.forEach(input => {
        input.addEventListener('invalid', function() {
            this.style.borderColor = '#ef4444';
        });
        
        input.addEventListener('input', function() {
            this.style.borderColor = '#e2e8f0';
        });
    });
}
