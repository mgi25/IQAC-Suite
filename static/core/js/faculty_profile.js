/**
 * Faculty Profile Page JavaScript
 * Handles faculty-specific profile functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Faculty Profile page loaded successfully');
    
    // Initialize faculty-specific features
    initializeFacultyProfile();
    initializeClassManagement();
    initializeStudentManagement();
    initializeEventManagement();
    initializeFacultyActions();
});

// Faculty Profile Initialization
function initializeFacultyProfile() {
    // Load faculty dashboard stats
    loadFacultyStats();
    
    // Initialize professional status indicators
    updateProfessionalStatus();
    
    // Check for pending approvals or tasks
    checkPendingTasks();
}

// Load Faculty Statistics
async function loadFacultyStats() {
    try {
        const response = await fetch('/api/faculty/stats/', {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        
        if (response.ok) {
            const data = await response.json();
            updateFacultyStatsDisplay(data);
        }
    } catch (error) {
        console.log('Faculty stats not available:', error);
    }
}

function updateFacultyStatsDisplay(data) {
    const statsCards = document.querySelectorAll('.stat-card');
    
    statsCards.forEach(card => {
        const label = card.querySelector('.stat-label').textContent;
        const numberElement = card.querySelector('.stat-number');
        
        switch (label) {
            case 'STUDENTS':
                if (data.students_count !== undefined) {
                    numberElement.textContent = data.students_count;
                }
                break;
            case 'CLASSES':
                if (data.classes_count !== undefined) {
                    numberElement.textContent = data.classes_count;
                }
                break;
            case 'EVENTS ORGANIZED':
                if (data.events_count !== undefined) {
                    numberElement.textContent = data.events_count;
                }
                break;
        }
    });
}

// Professional Status Updates
function updateProfessionalStatus() {
    const statusItems = document.querySelectorAll('.status-item-large');
    
    statusItems.forEach(item => {
        const title = item.querySelector('.status-title').textContent;
        const indicator = item.querySelector('.status-indicator');
        
        // Add appropriate status classes
        if (title.includes('Faculty Member')) {
            indicator.classList.add('faculty-verified');
        } else if (title.includes('Teaching Access')) {
            indicator.classList.add('teaching-enabled');
        }
    });
}

// Check for Pending Tasks
async function checkPendingTasks() {
    try {
        const response = await fetch('/api/faculty/pending-tasks/', {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.pending_count > 0) {
                showPendingTasksNotification(data.pending_count);
            }
        }
    } catch (error) {
        console.log('Pending tasks check failed:', error);
    }
}

function showPendingTasksNotification(count) {
    showNotification(
        `You have ${count} pending task${count > 1 ? 's' : ''} requiring attention`,
        'warning',
        0 // Don't auto-dismiss
    );
}

// Class Management
function initializeClassManagement() {
    // Class action handlers
    window.viewClass = function(classId) {
        window.location.href = `/classes/${classId}/`;
    };

    window.manageClass = function(classId) {
        window.location.href = `/classes/${classId}/manage/`;
    };

    window.exportClasses = function() {
        showNotification('Exporting class list...', 'info');
        window.location.href = '/api/faculty/export-classes/';
    };

    // Class creation
    window.createClass = function() {
        showEditModal('create-class', {
            title: 'Create New Class',
            fields: [
                { name: 'name', label: 'Class Name', type: 'text', required: true },
                { name: 'code', label: 'Class Code', type: 'text', required: true },
                { name: 'organization', label: 'Department', type: 'select', required: true },
                { name: 'academic_year', label: 'Academic Year', type: 'select', required: true }
            ]
        });
    };
}

// Student Management
function initializeStudentManagement() {
    // Student action handlers
    window.viewStudent = function(studentId) {
        window.location.href = `/students/${studentId}/profile/`;
    };

    window.contactStudent = function(studentId) {
        // Open email client or internal messaging system
        const studentCard = document.querySelector(`[data-student-id="${studentId}"]`);
        const email = studentCard?.querySelector('.student-email')?.textContent;
        
        if (email) {
            window.location.href = `mailto:${email}`;
        } else {
            showNotification('Student email not available', 'error');
        }
    };

    window.exportStudents = function() {
        showNotification('Exporting student list...', 'info');
        window.location.href = '/api/faculty/export-students/';
    };

    // Bulk actions for students
    window.bulkEmailStudents = function() {
        const selectedStudents = getSelectedStudents();
        if (selectedStudents.length === 0) {
            showNotification('Please select students first', 'warning');
            return;
        }
        
        showBulkEmailModal(selectedStudents);
    };
}

// Event Management
function initializeEventManagement() {
    // Event action handlers
    window.viewEvent = function(eventId) {
        window.location.href = `/events/${eventId}/`;
    };

    window.editEvent = function(eventId) {
        window.location.href = `/events/${eventId}/edit/`;
    };

    window.duplicateEvent = function(eventId) {
        if (confirm('Create a copy of this event?')) {
            duplicateEventRequest(eventId);
        }
    };

    window.cancelEvent = function(eventId) {
        if (confirm('Are you sure you want to cancel this event?')) {
            cancelEventRequest(eventId);
        }
    };
}

// Faculty-Specific Actions
function initializeFacultyActions() {
    // Personal info edit handler
    window.editPersonalInfo = function() {
        showEditModal('personal-info', {
            title: 'Edit Personal Information',
            fields: [
                { name: 'first_name', label: 'First Name', type: 'text', required: true },
                { name: 'last_name', label: 'Last Name', type: 'text', required: true },
                { name: 'email', label: 'Email', type: 'email', required: true, readonly: true },
                { name: 'phone', label: 'Phone Number', type: 'tel', required: false }
            ]
        });
    };

    // Professional info edit handler
    window.editProfessionalInfo = function() {
        showEditModal('professional-info', {
            title: 'Edit Professional Information',
            fields: [
                { name: 'designation', label: 'Designation', type: 'text', required: true },
                { name: 'department', label: 'Department', type: 'select', required: true },
                { name: 'qualification', label: 'Highest Qualification', type: 'text', required: false },
                { name: 'specialization', label: 'Specialization', type: 'text', required: false }
            ]
        });
    };

    // Organization management
    window.viewOrganization = function(orgId) {
        window.location.href = `/organizations/${orgId}/`;
    };

    window.manageOrganization = function(orgId) {
        window.location.href = `/organizations/${orgId}/manage/`;
    };
}

// Modal System for Faculty
function showEditModal(type, config) {
    // Remove existing modal
    const existingModal = document.querySelector('.edit-modal');
    if (existingModal) {
        existingModal.remove();
    }

    // Create modal with faculty-specific styling
    const modal = document.createElement('div');
    modal.className = 'edit-modal faculty-modal';
    modal.innerHTML = `
        <div class="modal-backdrop"></div>
        <div class="modal-content">
            <div class="modal-header faculty-header">
                <h3><i class="fas fa-chalkboard-user"></i> ${config.title}</h3>
                <button class="modal-close" onclick="closeEditModal()">&times;</button>
            </div>
            <div class="modal-body">
                <form id="edit-form-${type}" class="edit-form faculty-form">
                    ${config.fields.map(field => createFacultyFormField(field)).join('')}
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="closeEditModal()">Cancel</button>
                <button type="button" class="btn btn-primary faculty-btn" onclick="saveFacultyFormData('${type}')">Save Changes</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    
    // Add event listeners
    modal.querySelector('.modal-backdrop').addEventListener('click', closeEditModal);
    
    // Populate select fields if needed
    populateFacultySelectFields(modal, type);
    
    // Focus first input
    const firstInput = modal.querySelector('input, select, textarea');
    if (firstInput) {
        setTimeout(() => firstInput.focus(), 100);
    }
}

function createFacultyFormField(field) {
    const value = field.value || '';
    const required = field.required ? 'required' : '';
    const readonly = field.readonly ? 'readonly' : '';
    
    let input = '';
    
    switch (field.type) {
        case 'textarea':
            input = `<textarea name="${field.name}" ${required} ${readonly} placeholder="Enter ${field.label.toLowerCase()}" rows="4">${value}</textarea>`;
            break;
        case 'select':
            input = `<select name="${field.name}" ${required} ${readonly}>
                <option value="">Select ${field.label}</option>
                <!-- Options populated dynamically -->
            </select>`;
            break;
        default:
            input = `<input type="${field.type}" name="${field.name}" value="${value}" ${required} ${readonly} placeholder="Enter ${field.label.toLowerCase()}">`;
    }
    
    return `
        <div class="form-group faculty-form-group">
            <label for="${field.name}">${field.label}</label>
            ${input}
            ${field.required ? '<span class="required-indicator">*</span>' : ''}
        </div>
    `;
}

function populateFacultySelectFields(modal, type) {
    const selects = modal.querySelectorAll('select');
    
    selects.forEach(select => {
        const fieldName = select.name;
        
        switch (fieldName) {
            case 'organization':
            case 'department':
                loadDepartmentOptions(select);
                break;
            case 'academic_year':
                loadAcademicYearOptions(select);
                break;
            case 'designation':
                loadDesignationOptions(select);
                break;
        }
    });
}

async function loadDepartmentOptions(select) {
    try {
        const response = await fetch('/api/faculty/departments/', {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        
        if (response.ok) {
            const departments = await response.json();
            departments.forEach(dept => {
                const option = new Option(dept.name, dept.id);
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.log('Failed to load departments:', error);
    }
}

function loadAcademicYearOptions(select) {
    const currentYear = new Date().getFullYear();
    const years = [];
    
    for (let i = -2; i <= 2; i++) {
        const year = currentYear + i;
        const yearString = `${year}-${year + 1}`;
        years.push({ value: yearString, text: yearString });
    }
    
    years.forEach(year => {
        const option = new Option(year.text, year.value);
        select.appendChild(option);
    });
}

function loadDesignationOptions(select) {
    const designations = [
        'Assistant Professor',
        'Associate Professor',
        'Professor',
        'Senior Professor',
        'Head of Department',
        'Dean',
        'Director'
    ];
    
    designations.forEach(designation => {
        const option = new Option(designation, designation);
        select.appendChild(option);
    });
}

window.closeEditModal = function() {
    const modal = document.querySelector('.edit-modal');
    if (modal) {
        modal.remove();
    }
};

window.saveFacultyFormData = function(type) {
    const form = document.querySelector(`#edit-form-${type}`);
    if (!form) return;
    
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    // Validate required fields
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('error');
            isValid = false;
        } else {
            field.classList.remove('error');
        }
    });
    
    if (!isValid) {
        showNotification('Please fill in all required fields', 'error');
        return;
    }
    
    // Show loading state
    const saveButton = document.querySelector('.modal-footer .btn-primary');
    const originalText = saveButton.textContent;
    saveButton.textContent = 'Saving...';
    saveButton.disabled = true;
    
    // Send data to appropriate endpoint
    submitFacultyFormData(type, data)
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

// API Calls for Faculty
async function submitFacultyFormData(type, data) {
    const endpoints = {
        'personal-info': '/api/faculty/update-personal-info/',
        'professional-info': '/api/faculty/update-professional-info/',
        'create-class': '/api/faculty/create-class/'
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

async function duplicateEventRequest(eventId) {
    try {
        const response = await fetch(`/api/faculty/duplicate-event/${eventId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            showNotification('Event duplicated successfully', 'success');
            // Redirect to edit the new event
            if (data.new_event_id) {
                window.location.href = `/events/${data.new_event_id}/edit/`;
            }
        } else {
            throw new Error('Failed to duplicate event');
        }
    } catch (error) {
        showNotification('Failed to duplicate event', 'error');
    }
}

async function cancelEventRequest(eventId) {
    try {
        const response = await fetch(`/api/faculty/cancel-event/${eventId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (response.ok) {
            showNotification('Event cancelled successfully', 'success');
            // Update the event card to show cancelled status
            const eventCard = document.querySelector(`[data-event-id="${eventId}"]`);
            if (eventCard) {
                const statusBadge = eventCard.querySelector('.status-badge');
                if (statusBadge) {
                    statusBadge.textContent = 'Cancelled';
                    statusBadge.className = 'status-badge status-cancelled';
                }
            }
        } else {
            throw new Error('Failed to cancel event');
        }
    } catch (error) {
        showNotification('Failed to cancel event', 'error');
    }
}

// Bulk Actions
function getSelectedStudents() {
    const checkboxes = document.querySelectorAll('.student-checkbox:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

function showBulkEmailModal(studentIds) {
    showEditModal('bulk-email', {
        title: `Send Email to ${studentIds.length} Students`,
        fields: [
            { name: 'subject', label: 'Subject', type: 'text', required: true },
            { name: 'message', label: 'Message', type: 'textarea', required: true }
        ]
    });
}

// Utility Functions
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
           document.querySelector('meta[name=csrf-token]')?.getAttribute('content') || '';
}

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

// Enhanced Avatar Upload for Faculty
function initializeFacultyAvatarUpload() {
    const avatarSection = document.querySelector('.profile-avatar-large');
    const editButton = document.querySelector('.avatar-edit-btn');
    
    if (avatarSection && editButton) {
        editButton.addEventListener('click', function(e) {
            e.preventDefault();
            handleFacultyAvatarUpload();
        });
    }
}

function handleFacultyAvatarUpload() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    
    input.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            // Validate file size (max 5MB for faculty)
            if (file.size > 5 * 1024 * 1024) {
                showNotification('Image size must be less than 5MB', 'error');
                return;
            }
            
            // Preview and upload
            previewAndUploadFacultyAvatar(file);
        }
    });
    
    input.click();
}

async function previewAndUploadFacultyAvatar(file) {
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
            uploadFacultyAvatarToServer(file);
        }
    };
    reader.readAsDataURL(file);
}

async function uploadFacultyAvatarToServer(file) {
    const formData = new FormData();
    formData.append('avatar', file);
    
    try {
        showNotification('Uploading profile picture...', 'info');
        
        const response = await fetch('/api/faculty/upload-avatar/', {
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
        console.error('Faculty avatar upload error:', error);
    }
}

// Initialize faculty avatar upload
initializeFacultyAvatarUpload();

// Export for potential external use
window.FacultyProfile = {
    editPersonalInfo: () => window.editPersonalInfo(),
    editProfessionalInfo: () => window.editProfessionalInfo(),
    createClass: () => window.createClass(),
    viewClass: (id) => window.viewClass(id),
    manageClass: (id) => window.manageClass(id),
    viewStudent: (id) => window.viewStudent(id),
    contactStudent: (id) => window.contactStudent(id),
    viewEvent: (id) => window.viewEvent(id),
    editEvent: (id) => window.editEvent(id)
};
