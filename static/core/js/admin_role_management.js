document.addEventListener('DOMContentLoaded', function() {
    initializeRoleManagement();
    // Selects all forms with the class 'delete-role-form'
    document.querySelectorAll('.delete-role-form').forEach(form => {
        form.addEventListener('submit', e => {
            // Use a clear confirmation message before submitting the form
            if (!confirm('Are you sure you want to delete this role? This action cannot be undone.')) {
                e.preventDefault(); // Stop the form submission if the user clicks 'Cancel'
            }
        });
    });
});

function initializeRoleManagement() {
    const orgTypeSelect = document.getElementById('orgTypeSelect');
    const orgSelect = document.getElementById('orgSelect');
    const quickAddForm = document.getElementById('quickAddRoleForm');

    // Organization type change handler
    if (orgTypeSelect) {
        orgTypeSelect.addEventListener('change', function() {
            const orgTypeId = this.value;
            if (orgTypeId) {
                const currentUrl = new URL(window.location);
                currentUrl.searchParams.set('org_type_id', orgTypeId);
                window.location.href = currentUrl.toString();
            } else {
                window.location.href = window.location.pathname;
            }
        });
    }

    // Organization change handler
    if (orgSelect) {
        orgSelect.addEventListener('change', function() {
            const orgId = this.value;
            if (orgId) {
                // Update URL to include organization_id
                window.location.href = `/admin/roles/manage/${orgId}/`;
            }
        });
    }

    // Quick add form enhancement
    if (quickAddForm) {
        enhanceQuickAddForm(quickAddForm);
    }

    // Initialize tooltips and other Bootstrap components
    initializeBootstrapComponents();
}

function enhanceQuickAddForm(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    const nameInput = form.querySelector('#roleName');
    const descInput = form.querySelector('#roleDescription');

    // Add real-time validation
    nameInput.addEventListener('input', function() {
        validateRoleName(this);
    });

    // Add form submission enhancement
    form.addEventListener('submit', function(e) {
        if (!validateForm(form)) {
            e.preventDefault();
            return false;
        }

        // Add loading state
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...';
        }
    });

    // Add keyboard shortcuts
    nameInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && e.ctrlKey) {
            form.submit();
        }
    });
}

function validateRoleName(input) {
    const value = input.value.trim();
    const isValid = value.length >= 2 && value.length <= 100;
    
    if (isValid) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
    } else {
        input.classList.remove('is-valid');
        input.classList.add('is-invalid');
    }
    
    return isValid;
}

function validateForm(form) {
    const nameInput = form.querySelector('#roleName');
    const isNameValid = validateRoleName(nameInput);
    
    if (!isNameValid) {
        nameInput.focus();
        showNotification('Please enter a valid role name (2-100 characters)', 'error');
        return false;
    }
    
    return true;
}

function editRole(roleId, roleName, roleDescription) {
    const modal = document.getElementById('editRoleModal');
    const form = document.getElementById('editRoleForm');
    const nameInput = document.getElementById('editRoleName');
    const descInput = document.getElementById('editRoleDescription');

    if (!modal || !form || !nameInput || !descInput) {
        console.error('Modal elements not found');
        return;
    }

    // Populate form fields
    nameInput.value = roleName || '';
    descInput.value = roleDescription || '';
    
    // Set form action
    form.action = `/admin/roles/update/${roleId}/`;
    
    // Show modal
    $(modal).modal('show');
    
    // Focus on name input when modal is shown
    $(modal).on('shown.bs.modal', function() {
        nameInput.focus();
        nameInput.select();
    });
}

function deleteRole(roleId, roleName) {
    const confirmMessage = `Are you sure you want to delete the role "${roleName}"?\n\nThis action cannot be undone and may affect users assigned to this role.`;
    
    if (confirm(confirmMessage)) {
        // Create and submit delete form
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/admin/roles/delete/${roleId}/`;
        
        // Add CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = csrfToken;
        form.appendChild(csrfInput);
        
        document.body.appendChild(form);
        form.submit();
    }
}

function toggleRole(roleId, isActive) {
    const action = isActive ? 'deactivate' : 'activate';
    const confirmMessage = `Are you sure you want to ${action} this role?`;
    
    if (confirm(confirmMessage)) {
        // Create and submit toggle form
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/admin/roles/toggle/${roleId}/`;
        
        // Add CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = csrfToken;
        form.appendChild(csrfInput);
        
        document.body.appendChild(form);
        form.submit();
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show notification-toast`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="close" data-dismiss="alert" aria-label="Close">
            <span aria-hidden="true">&times;</span>
        </button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

function initializeBootstrapComponents() {
    // Initialize tooltips
    $('[data-toggle="tooltip"]').tooltip();
    
    // Initialize popovers
    $('[data-toggle="popover"]').popover();
    
    // Handle dropdown submissions
    $(document).on('click', '.dropdown-form button[type="submit"]', function(e) {
        e.preventDefault();
        const form = this.closest('form');
        if (form) {
            form.submit();
        }
    });
}

// Add smooth scrolling for anchor links
function smoothScroll(target) {
    const element = document.querySelector(target);
    if (element) {
        element.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl + N for new role (when organization is selected)
    if (e.ctrlKey && e.key === 'n') {
        const nameInput = document.getElementById('roleName');
        if (nameInput) {
            e.preventDefault();
            nameInput.focus();
        }
    }
    
    // Escape to close modals
    if (e.key === 'Escape') {
        $('.modal').modal('hide');
    }
});

// Enhanced error handling for forms
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    showNotification('An unexpected error occurred. Please try again.', 'error');
});

// AJAX role addition (optional enhancement)
function addRoleAjax(organizationId, roleName, roleDescription) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    return fetch(`/admin/roles/quick-add/${organizationId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            name: roleName,
            description: roleDescription
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            // Optionally refresh the page or add the role to the DOM
            location.reload();
        } else {
            showNotification(data.error, 'error');
        }
        return data;
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Failed to add role. Please try again.', 'error');
    });
}
