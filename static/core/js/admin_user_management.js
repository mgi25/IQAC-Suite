/**
 * Admin User Management - Unified Interface JavaScript
 * Handles tabbed interface, AJAX uploads, and real-time updates
 */

// Global variables
let currentOrganization = null;
let activeTab = 'students';
let filterStates = { students: 'active', faculty: 'active' };

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', function() {
    initializeUserManagement();
});

function initializeUserManagement() {
    // Get organization info from the template
    const orgInfo = document.querySelector('.organization-info');
    if (orgInfo) {
        currentOrganization = {
            id: orgInfo.dataset.orgId,
            name: orgInfo.dataset.orgName
        };
    }
    
    // Initialize tab functionality
    initializeTabs();

    // Setup academic year dropdowns
    setupAcademicYearSelectors('students');

    // Initialize upload forms
    initializeUploadForms();
    
    // Initialize pane toggles
    initializePaneToggles();
    
    // Initialize filter toggles
    initializeFilterToggles();
    
    // Load initial content
    loadTabContent('students');
    
    console.log('User management initialized', { currentOrganization });
}

// =============================================================================
// TAB FUNCTIONALITY
// =============================================================================

function initializeTabs() {
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const tabName = this.dataset.tab;
            switchTab(tabName);
        });
    });
}

function switchTab(tabName) {
    // Update active tab
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    // Update active content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');

    activeTab = tabName;
    // Sync filter button states for the newly activated tab
    document.querySelectorAll(`#${tabName}-tab .filter-toggle`).forEach(btn => {
        btn.classList.toggle('active', btn.dataset.filter === filterStates[tabName]);
    });
    loadTabContent(tabName);
}

// =============================================================================
// CONTENT LOADING
// =============================================================================

function loadTabContent(tabName) {
    if (!currentOrganization) return;
    
    const resultsContent = document.querySelector(`#${tabName}-tab .results-content`);
    if (!resultsContent) return;
    
    // Show loading state
    resultsContent.innerHTML = '<div class="text-center p-4"><i class="fas fa-spinner fa-spin"></i> Loading...</div>';
    
    // Load content based on tab
    if (tabName === 'students') {
        loadStudentsContent();
    } else if (tabName === 'faculty') {
        loadFacultyContent();
    }
}

function loadStudentsContent() {
    const filter = filterStates['students'];
    const url = filter === 'archived'
        ? `/core-admin/org-users/${currentOrganization.id}/students/?archived=1`
        : `/core-admin/org-users/${currentOrganization.id}/students/`;
    fetch(url)
        .then(response => response.text())
        .then(html => {
            // Extract the classes table from the response
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const table = doc.querySelector('table');
            
            if (table) {
                updateResultsContent('students', table.outerHTML);
            } else {
                updateResultsContent('students', '<div class="empty-state"><div class="empty-icon"><i class="fas fa-users"></i></div><p>No classes uploaded yet</p></div>');
            }
        })
        .catch(error => {
            console.error('Error loading students:', error);
            updateResultsContent('students', '<div class="empty-state"><div class="empty-icon"><i class="fas fa-exclamation-circle"></i></div><p>Error loading students</p></div>');
        });
}

function loadFacultyContent() {
    const filter = filterStates['faculty'];
    const url = filter === 'archived'
        ? `/core-admin/org-users/${currentOrganization.id}/faculty/?archived=1`
        : `/core-admin/org-users/${currentOrganization.id}/faculty/`;
    fetch(url)
        .then(response => response.text())
        .then(html => {
            // Extract the faculty table from the response
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const table = doc.querySelector('table');
            
            if (table) {
                updateResultsContent('faculty', table.outerHTML);
            } else {
                updateResultsContent('faculty', '<div class="empty-state"><div class="empty-icon"><i class="fas fa-chalkboard-teacher"></i></div><p>No faculty uploaded yet</p></div>');
            }
        })
        .catch(error => {
            console.error('Error loading faculty:', error);
            updateResultsContent('faculty', '<div class="empty-state"><div class="empty-icon"><i class="fas fa-exclamation-circle"></i></div><p>Error loading faculty</p></div>');
        });
}

function updateResultsContent(tabName, content) {
    const resultsContent = document.querySelector(`#${tabName}-tab .results-content`);
    if (resultsContent) {
        resultsContent.innerHTML = content;
        
        // Re-initialize table interactions
        initializeTableInteractions(resultsContent);
    }
}

// =============================================================================
// ACADEMIC YEAR SELECTORS
// =============================================================================

function setupAcademicYearSelectors(prefix) {
    const startSelect = document.getElementById(`${prefix}-start-year`);
    const endSelect = document.getElementById(`${prefix}-end-year`);
    const hiddenInput = document.getElementById(`${prefix}-academic-year`);
    if (!startSelect || !endSelect || !hiddenInput) return;

    const currentYear = new Date().getFullYear();

    for (let y = currentYear - 5; y <= currentYear + 5; y++) {
        startSelect.add(new Option(y, y));
    }

    for (let y = currentYear - 4; y <= currentYear + 6; y++) {
        endSelect.add(new Option(y, y));
    }

    startSelect.value = currentYear;
    endSelect.value = currentYear + 1;

    function sync() {
        hiddenInput.value = `${startSelect.value}-${endSelect.value}`;
    }

    startSelect.addEventListener('change', sync);
    endSelect.addEventListener('change', sync);
    sync();
}

// =============================================================================
// UPLOAD FORMS
// =============================================================================

function initializeUploadForms() {
    // Students upload form
    const studentsForm = document.getElementById('students-upload-form');
    if (studentsForm) {
        studentsForm.addEventListener('submit', function(e) {
            e.preventDefault();
            handleFormSubmit(this, 'students');
        });
    }
    
    // Faculty upload form
    const facultyForm = document.getElementById('faculty-upload-form');
    if (facultyForm) {
        facultyForm.addEventListener('submit', function(e) {
            e.preventDefault();
            handleFormSubmit(this, 'faculty');
        });
    }
}

function handleFormSubmit(form, type) {
    // Ensure academic year is combined from dropdowns
    const startYear = form.querySelector(`#${type}-start-year`);
    const endYear = form.querySelector(`#${type}-end-year`);
    const academicYear = form.querySelector(`#${type}-academic-year`);
    if (startYear && endYear && academicYear) {
        academicYear.value = `${startYear.value}-${endYear.value}`;
    }

    const formData = new FormData(form);
    const submitBtn = form.querySelector('.upload-btn');
    const originalText = submitBtn.innerHTML;
    
    // Show loading state
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';
    submitBtn.disabled = true;
    
    // Submit to existing endpoint
    fetch(`/core-admin/org-users/${currentOrganization.id}/upload-csv/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken()
        },
        body: formData
    })
    .then(response => response.text())
    .then(html => {
        // Check if there's a redirect or success message
        if (html.includes('CSV processed') || html.includes('students into')) {
            showToast('Upload successful!', 'success');
            form.reset();
            // Reload the current tab content
            loadTabContent(activeTab);
        } else {
            // Extract error messages if any
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const alerts = doc.querySelectorAll('.alert, .message');
            
            if (alerts.length > 0) {
                alerts.forEach(alert => {
                    showToast(alert.textContent.trim(), 'error');
                });
            } else {
                showToast('Upload completed', 'success');
                loadTabContent(activeTab);
            }
        }
    })
    .catch(error => {
        console.error('Upload error:', error);
        showToast('Upload failed. Please try again.', 'error');
    })
    .finally(() => {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
}

// =============================================================================
// PANE TOGGLES
// =============================================================================

function initializePaneToggles() {
    const toggles = document.querySelectorAll('.pane-toggle');
    toggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            const pane = this.closest('.upload-pane');
            const content = pane.querySelector('.pane-content');
            const icon = this.querySelector('i');
            
            if (content.classList.contains('collapsed')) {
                content.classList.remove('collapsed');
                icon.className = 'fas fa-chevron-up';
                this.setAttribute('title', 'Collapse');
            } else {
                content.classList.add('collapsed');
                icon.className = 'fas fa-chevron-down';
                this.setAttribute('title', 'Expand');
            }
        });
    });
}

// =============================================================================
// FILTER TOGGLES
// =============================================================================

function initializeFilterToggles() {
    document.querySelectorAll('.results-pane').forEach(pane => {
        const tab = pane.closest('.tab-content').id.replace('-tab', '');
        const buttons = pane.querySelectorAll('.filter-toggle');

        buttons.forEach(btn => {
            btn.addEventListener('click', function() {
                buttons.forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                filterStates[tab] = this.dataset.filter;
                loadTabContent(tab);
            });
        });
    });
}

// =============================================================================
// TABLE INTERACTIONS
// =============================================================================

function initializeTableInteractions(container) {
    // Initialize archive/activate buttons
    const toggleBtns = container.querySelectorAll('button[type="submit"]');
    toggleBtns.forEach(btn => {
        const form = btn.closest('form');
        if (form && form.action.includes('toggle')) {
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                handleToggleAction(this);
            });
        }
    });
    
    // Initialize view links to open in modals instead of new pages
    const viewLinks = container.querySelectorAll('a[href*="class_detail"], a[href*="faculty_detail"]');
    viewLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            openDetailModal(this.href);
        });
    });
}

function handleToggleAction(form) {
    const btn = form.querySelector('button[type="submit"]');
    const originalText = btn.textContent;
    
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    btn.disabled = true;
    
    fetch(form.action, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken()
        },
        body: new FormData(form)
    })
    .then(response => response.text())
    .then(() => {
        showToast('Status updated successfully', 'success');
        loadTabContent(activeTab);
    })
    .catch(error => {
        console.error('Toggle error:', error);
        showToast('Failed to update status', 'error');
    })
    .finally(() => {
        btn.textContent = originalText;
        btn.disabled = false;
    });
}

// =============================================================================
// MODAL FUNCTIONALITY
// =============================================================================

function openDetailModal(url) {
    // Create modal if it doesn't exist
    let modal = document.getElementById('detail-modal');
    if (!modal) {
        modal = createDetailModal();
    }
    
    const modalBody = modal.querySelector('.modal-body');
    modalBody.innerHTML = '<div class="text-center p-4"><i class="fas fa-spinner fa-spin"></i> Loading...</div>';
    
    // Show modal
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    
    // Load content
    fetch(url)
        .then(response => response.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const content = doc.querySelector('.admin-dashboard-container');
            
            if (content) {
                modalBody.innerHTML = content.innerHTML;
                initializeTableInteractions(modalBody);
            }
        })
        .catch(error => {
            console.error('Modal loading error:', error);
            modalBody.innerHTML = '<div class="text-center p-4 text-danger">Error loading content</div>';
        });
}

function createDetailModal() {
    const modal = document.createElement('div');
    modal.id = 'detail-modal';
    modal.className = 'modal-overlay';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: none;
        align-items: center;
        justify-content: center;
        z-index: 1000;
        padding: 2rem;
    `;
    
    modal.innerHTML = `
        <div class="modal-content" style="
            background: white;
            border-radius: var(--border-radius);
            max-width: 90vw;
            max-height: 90vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        ">
            <div class="modal-header" style="
                padding: 1rem 1.5rem;
                background: var(--light-grey);
                border-bottom: 1px solid var(--medium-grey);
                display: flex;
                align-items: center;
                justify-content: space-between;
            ">
                <h3 style="margin: 0; color: var(--text-color);">Details</h3>
                <button class="modal-close" style="
                    background: none;
                    border: none;
                    font-size: 1.5rem;
                    cursor: pointer;
                    color: var(--dark-grey);
                    padding: 0.25rem;
                ">&times;</button>
            </div>
            <div class="modal-body" style="
                flex: 1;
                overflow-y: auto;
                padding: 1.5rem;
            "></div>
        </div>
    `;
    
    // Add close functionality
    const closeBtn = modal.querySelector('.modal-close');
    closeBtn.addEventListener('click', () => closeDetailModal(modal));
    
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeDetailModal(modal);
        }
    });
    
    document.body.appendChild(modal);
    return modal;
}

function closeDetailModal(modal) {
    modal.style.display = 'none';
    document.body.style.overflow = '';
}

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

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
window.userManagement = {
    switchTab,
    loadTabContent,
    showToast
};
