/**
 * Student Profile Page JavaScript
 * Handles student-specific profile functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Student Profile page loaded successfully');
    
    // Initialize student-specific features
    initializeStudentProfile();
    initializeAvatarUpload();
    initializeFormHandlers();
    initializeQuickActions();
});

// Student Profile Initialization
function initializeStudentProfile() {
    // Auto-focus on completion improvement suggestions
    checkProfileCompletion();
    
    // Initialize academic info display
    updateAcademicStatus();
    
    // Load participation stats
    loadParticipationStats();
}

// Check Profile Completion and Show Suggestions
function checkProfileCompletion() {
    const completionPercentage = parseInt(document.querySelector('.completion-percentage').textContent);
    
    if (completionPercentage < 80) {
        showCompletionSuggestions(completionPercentage);
    }
}

function showCompletionSuggestions(percentage) {
    const suggestions = [];
    
    // Check what's missing based on DOM content
    const regNumber = document.querySelector('[data-field="registration_number"]')?.textContent;
    const department = document.querySelector('[data-field="department"]')?.textContent;
    const academicYear = document.querySelector('[data-field="academic_year"]')?.textContent;
    
    if (!regNumber || regNumber === 'Not Set') {
        suggestions.push('Add your registration number');
    }
    if (!department || department === 'Not Assigned') {
        suggestions.push('Update your department information');
    }
    if (!academicYear || academicYear === 'Not Set') {
        suggestions.push('Set your academic year');
    }
    
    if (suggestions.length > 0) {
        showNotification(
            `Profile ${percentage}% complete. Consider: ${suggestions.join(', ')}`,
            'info',
            8000
        );
    }
}

// Academic Status Updates
function updateAcademicStatus() {
    const academicCards = document.querySelectorAll('.status-item-large');
    
    academicCards.forEach(card => {
        const description = card.querySelector('.status-description');
        if (description && description.textContent.includes('Not')) {
            card.classList.add('incomplete');
        }
    });
}

// Load Participation Statistics
async function loadParticipationStats() {
    try {
        const response = await fetch('/api/student/participation-stats/', {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        
        if (response.ok) {
            const data = await response.json();
            updateParticipationDisplay(data);
        }
    } catch (error) {
        console.log('Participation stats not available:', error);
    }
}

function updateParticipationDisplay(data) {
    // Update stats in the header
    const statsCards = document.querySelectorAll('.stat-card');
    
    statsCards.forEach(card => {
        const label = card.querySelector('.stat-label').textContent;
        const numberElement = card.querySelector('.stat-number');
        
        switch (label) {
            case 'EVENTS PARTICIPATED':
                if (data.total_events !== undefined) {
                    numberElement.textContent = data.total_events;
                }
                break;
            case 'ORGANIZATIONS':
                if (data.organizations_count !== undefined) {
                    numberElement.textContent = data.organizations_count;
                }
                break;
            case 'ACHIEVEMENTS':
                if (data.achievements_count !== undefined) {
                    numberElement.textContent = data.achievements_count;
                }
                break;
        }
    });
}

// Form Handlers for Student-Specific Actions
function initializeFormHandlers() {
    // Personal info edit handler
    window.editPersonalInfo = function() {
        showEditModal('personal-info', {
            title: 'Edit Personal Information',
            fields: [
                { name: 'first_name', label: 'First Name', type: 'text', required: true },
                { name: 'last_name', label: 'Last Name', type: 'text', required: true },
                { name: 'email', label: 'Email', type: 'email', required: true, readonly: true }
            ]
        });
    };

    // Academic info edit handler
    window.editAcademicInfo = function() {
        showEditModal('academic-info', {
            title: 'Edit Academic Information',
            fields: [
                { name: 'registration_number', label: 'Registration Number', type: 'text', required: true },
                { name: 'department', label: 'Department', type: 'select', required: true },
                { name: 'academic_year', label: 'Academic Year', type: 'select', required: true }
            ]
        });
    };

    // Achievement management
    window.addAchievement = function() {
        showEditModal('add-achievement', {
            title: 'Add New Achievement',
            fields: [
                { name: 'title', label: 'Achievement Title', type: 'text', required: true },
                { name: 'description', label: 'Description', type: 'textarea', required: false },
                { name: 'date_achieved', label: 'Date Achieved', type: 'date', required: true },
                { name: 'issuing_organization', label: 'Issuing Organization', type: 'text', required: true }
            ]
        });
    };

    window.editAchievement = function(achievementId) {
        // Load achievement data and show edit modal
        loadAchievementData(achievementId).then(data => {
            showEditModal('edit-achievement', {
                title: 'Edit Achievement',
                fields: [
                    { name: 'title', label: 'Achievement Title', type: 'text', required: true, value: data.title },
                    { name: 'description', label: 'Description', type: 'textarea', required: false, value: data.description },
                    { name: 'date_achieved', label: 'Date Achieved', type: 'date', required: true, value: data.date_achieved },
                    { name: 'issuing_organization', label: 'Issuing Organization', type: 'text', required: true, value: data.issuing_organization }
                ]
            });
        });
    };

    window.deleteAchievement = function(achievementId) {
        if (confirm('Are you sure you want to delete this achievement?')) {
            deleteAchievementRequest(achievementId);
        }
    };

    // Organization management
    window.joinOrganization = function() {
        showOrganizationSelector();
    };

    window.leaveOrganization = function(orgId) {
        if (confirm('Are you sure you want to leave this organization?')) {
            leaveOrganizationRequest(orgId);
        }
    };

    window.viewOrganization = function(orgId) {
        window.location.href = `/organizations/${orgId}/`;
    };
}

// Quick Actions
function initializeQuickActions() {
    // Export functionality
    window.exportParticipation = function() {
        showNotification('Exporting participation history...', 'info');
        window.location.href = '/api/student/export-participation/';
    };
}

// Modal System for Editing
function showEditModal(type, config) {
    // Remove existing modal
    const existingModal = document.querySelector('.edit-modal');
    if (existingModal) {
        existingModal.remove();
    }

    // Create modal
    const modal = document.createElement('div');
    modal.className = 'edit-modal';
    modal.innerHTML = `
        <div class="modal-backdrop"></div>
        <div class="modal-content">
            <div class="modal-header">
                <h3>${config.title}</h3>
                <button class="modal-close" onclick="closeEditModal()">&times;</button>
            </div>
            <div class="modal-body">
                <form id="edit-form-${type}" class="edit-form">
                    ${config.fields.map(field => createFormField(field)).join('')}
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="closeEditModal()">Cancel</button>
                <button type="button" class="btn btn-primary" onclick="saveFormData('${type}')">Save Changes</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    
    // Add event listeners
    modal.querySelector('.modal-backdrop').addEventListener('click', closeEditModal);
    
    // Focus first input
    const firstInput = modal.querySelector('input, select, textarea');
    if (firstInput) {
        setTimeout(() => firstInput.focus(), 100);
    }
}

function createFormField(field) {
    const value = field.value || '';
    const required = field.required ? 'required' : '';
    const readonly = field.readonly ? 'readonly' : '';
    
    let input = '';
    
    switch (field.type) {
        case 'textarea':
            input = `<textarea name="${field.name}" ${required} ${readonly} placeholder="Enter ${field.label.toLowerCase()}">${value}</textarea>`;
            break;
        case 'select':
            // For select fields, you'd populate options based on the field name
            input = `<select name="${field.name}" ${required} ${readonly}>
                <option value="">Select ${field.label}</option>
                <!-- Options would be populated dynamically -->
            </select>`;
            break;
        default:
            input = `<input type="${field.type}" name="${field.name}" value="${value}" ${required} ${readonly} placeholder="Enter ${field.label.toLowerCase()}">`;
    }
    
    return `
        <div class="form-group">
            <label for="${field.name}">${field.label}</label>
            ${input}
        </div>
    `;
}

window.closeEditModal = function() {
    const modal = document.querySelector('.edit-modal');
    if (modal) {
        modal.remove();
    }
};

window.saveFormData = function(type) {
    const form = document.querySelector(`#edit-form-${type}`);
    if (!form) return;
    
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    // Show loading state
    const saveButton = document.querySelector('.modal-footer .btn-primary');
    const originalText = saveButton.textContent;
    saveButton.textContent = 'Saving...';
    saveButton.disabled = true;
    
    // Send data to appropriate endpoint
    submitFormData(type, data)
        .then(response => {
            if (response.success) {
                showNotification('Changes saved successfully!', 'success');
                closeEditModal();
                // Refresh page to show changes
                window.location.reload();
            } else {
                throw new Error(response.message || 'Failed to save changes');
            }
        })
        .catch(error => {
            showNotification(error.message || 'Failed to save changes', 'error');
        })
        .finally(() => {
            saveButton.textContent = originalText;
            saveButton.disabled = false;
        });
};

// API Calls
async function submitFormData(type, data) {
    const endpoints = {
        'personal-info': '/api/student/update-personal-info/',
        'academic-info': '/api/student/update-academic-info/',
        'add-achievement': '/api/student/add-achievement/',
        'edit-achievement': '/api/student/update-achievement/'
    };
    
    const endpoint = endpoints[type];
    if (!endpoint) {
        throw new Error('Unknown form type');
    }
    
    const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(data)
    });
    
    return await response.json();
}

async function loadAchievementData(achievementId) {
    // Mock data for now - would fetch from API
    return {
        title: 'Sample Achievement',
        description: 'Sample description',
        date_achieved: '2024-01-01',
        issuing_organization: 'Sample Organization'
    };
}

async function deleteAchievementRequest(achievementId) {
    try {
        const response = await fetch(`/api/student/delete-achievement/${achievementId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (response.ok) {
            showNotification('Achievement deleted successfully', 'success');
            // Remove the achievement card from DOM
            const achievementCard = document.querySelector(`[data-achievement-id="${achievementId}"]`);
            if (achievementCard) {
                achievementCard.remove();
            }
        } else {
            throw new Error('Failed to delete achievement');
        }
    } catch (error) {
        showNotification('Failed to delete achievement', 'error');
    }
}

function showOrganizationSelector() {
    showNotification('Organization management coming soon!', 'info');
}

async function leaveOrganizationRequest(orgId) {
    try {
        const response = await fetch(`/api/student/leave-organization/${orgId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (response.ok) {
            showNotification('Left organization successfully', 'success');
            // Remove the organization card from DOM
            const orgCard = document.querySelector(`[data-org-id="${orgId}"]`);
            if (orgCard) {
                orgCard.remove();
            }
        } else {
            throw new Error('Failed to leave organization');
        }
    } catch (error) {
        showNotification('Failed to leave organization', 'error');
    }
}

// Utility Functions
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
           document.querySelector('meta[name=csrf-token]')?.getAttribute('content') || '';
}

// Enhanced notification system for student profile
function showNotification(message, type = 'info', duration = 5000) {
    // Use the existing notification system from profile.js
    if (window.ProfilePage && window.ProfilePage.showNotification) {
        window.ProfilePage.showNotification(message, type);
    } else {
        // Fallback notification
        console.log(`[${type.toUpperCase()}] ${message}`);
        alert(message);
    }
}

// Enhanced Avatar Upload for Students
function initializeAvatarUpload() {
    const avatarSection = document.querySelector('.profile-avatar-large');
    const editButton = document.querySelector('.avatar-edit-btn');
    
    if (avatarSection && editButton) {
        editButton.addEventListener('click', function(e) {
            e.preventDefault();
            handleStudentAvatarUpload();
        });
    }
}

function handleStudentAvatarUpload() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    
    input.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            // Validate file size (max 2MB for students)
            if (file.size > 2 * 1024 * 1024) {
                showNotification('Image size must be less than 2MB', 'error');
                return;
            }
            
            // Preview and upload
            previewAndUploadAvatar(file);
        }
    });
    
    input.click();
}

function previewAndUploadAvatar(file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        const avatarPlaceholder = document.querySelector('.avatar-placeholder');
        if (avatarPlaceholder) {
            // Show preview
            avatarPlaceholder.style.backgroundImage = `url(${e.target.result})`;
            avatarPlaceholder.style.backgroundSize = 'cover';
            avatarPlaceholder.style.backgroundPosition = 'center';
            avatarPlaceholder.textContent = '';
            
            // Upload to server
            uploadAvatarToServer(file);
        }
    };
    reader.readAsDataURL(file);
}

async function uploadAvatarToServer(file) {
    const formData = new FormData();
    formData.append('avatar', file);
    
    try {
        showNotification('Uploading profile picture...', 'info');
        
        const response = await fetch('/api/student/upload-avatar/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData
        });
        
        if (response.ok) {
            const data = await response.json();
            showNotification('Profile picture updated successfully!', 'success');
        } else {
            throw new Error('Upload failed');
        }
    } catch (error) {
        showNotification('Failed to upload profile picture', 'error');
        console.error('Avatar upload error:', error);
    }
}

// Export for potential external use
window.StudentProfile = {
    editPersonalInfo: () => window.editPersonalInfo(),
    editAcademicInfo: () => window.editAcademicInfo(),
    addAchievement: () => window.addAchievement(),
    joinOrganization: () => window.joinOrganization(),
    exportParticipation: () => window.exportParticipation()
};
