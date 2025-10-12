/**
 * Modern Profile Page JavaScript
 * Handles tab navigation and interactive features
 */

// Tab Navigation Function
function showTab(tabName) {
    // Remove active class from all tabs and content panels
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content-panel').forEach(panel => panel.classList.remove('active'));
    
    // Add active class to clicked tab
    event.target.closest('.tab-btn').classList.add('active');
    
    // Show corresponding content panel
    const targetPanel = document.getElementById(tabName);
    if (targetPanel) {
        targetPanel.classList.add('active');
    }
}

// Profile Page Initialization
document.addEventListener('DOMContentLoaded', function() {
    console.log('Modern My Profile page loaded successfully');
    
    // Initialize smooth hover effects for cards
    initializeCardEffects();
    
    // Initialize interactive elements
    initializeInteractiveElements();
    
    // Initialize responsive features
    initializeResponsiveFeatures();
});

// Card Hover Effects
function initializeCardEffects() {
    const cards = document.querySelectorAll('.content-card, .achievement-card, .organization-card');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
}

// Interactive Elements
function initializeInteractiveElements() {
    // Edit button functionality
    const editButtons = document.querySelectorAll('.edit-btn');
    editButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            handleEditClick(this);
        });
    });
    
    // Action button functionality
    const actionButtons = document.querySelectorAll('.action-btn');
    actionButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            handleActionClick(this);
        });
    });
    
    // Avatar upload functionality
    const avatarSection = document.querySelector('.profile-avatar-large');
    if (avatarSection) {
        avatarSection.addEventListener('click', function() {
            handleAvatarUpload();
        });
    }
}

// Handle Edit Button Click
function handleEditClick(button) {
    const card = button.closest('.content-card');
    const cardType = card.querySelector('.card-header h2').textContent.trim();
    
    // Add visual feedback
    button.style.transform = 'scale(0.95)';
    setTimeout(() => {
        button.style.transform = 'scale(1)';
    }, 150);
    
    console.log(`Edit clicked for: ${cardType}`);
    // Add your edit logic here
    showNotification(`Editing ${cardType}...`, 'info');
}

// Handle Action Button Click
function handleActionClick(button) {
    const icon = button.querySelector('i');
    const action = getActionType(icon);
    
    // Add visual feedback
    button.style.transform = 'scale(0.9)';
    setTimeout(() => {
        button.style.transform = 'scale(1)';
    }, 150);
    
    console.log(`Action clicked: ${action}`);
    // Add your action logic here
}

// Get Action Type from Icon
function getActionType(icon) {
    if (icon.classList.contains('fa-edit')) return 'edit';
    if (icon.classList.contains('fa-trash')) return 'delete';
    if (icon.classList.contains('fa-eye')) return 'view';
    if (icon.classList.contains('fa-cog')) return 'settings';
    return 'unknown';
}

// Handle Avatar Upload
function handleAvatarUpload() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    
    input.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            handleImageUpload(file);
        }
    });
    
    input.click();
}

// Handle Image Upload
function handleImageUpload(file) {
    if (file.size > 5 * 1024 * 1024) { // 5MB limit
        showNotification('File size must be less than 5MB', 'error');
        return;
    }
    
    const reader = new FileReader();
    reader.onload = function(e) {
        const avatarPlaceholder = document.querySelector('.avatar-placeholder');
        if (avatarPlaceholder) {
            avatarPlaceholder.style.backgroundImage = `url(${e.target.result})`;
            avatarPlaceholder.style.backgroundSize = 'cover';
            avatarPlaceholder.style.backgroundPosition = 'center';
            avatarPlaceholder.textContent = '';
        }
        
        showNotification('Profile picture updated!', 'success');
    };
    
    reader.readAsDataURL(file);
}

// Responsive Features
function initializeResponsiveFeatures() {
    // Handle window resize
    window.addEventListener('resize', debounce(handleResize, 250));
    
    // Initial responsive setup
    handleResize();
}

// Handle Window Resize
function handleResize() {
    const width = window.innerWidth;
    
    // Mobile navigation adjustments
    if (width <= 768) {
        adjustMobileNavigation();
    } else {
        resetDesktopNavigation();
    }
    
    // Stats grid adjustments
    adjustStatsGrid(width);
}

// Adjust Mobile Navigation
function adjustMobileNavigation() {
    const tabsNav = document.querySelector('.profile-tabs-nav');
    if (tabsNav) {
        tabsNav.classList.add('mobile-nav');
    }
}

// Reset Desktop Navigation
function resetDesktopNavigation() {
    const tabsNav = document.querySelector('.profile-tabs-nav');
    if (tabsNav) {
        tabsNav.classList.remove('mobile-nav');
    }
}

// Adjust Stats Grid
function adjustStatsGrid(width) {
    const statsGrid = document.querySelector('.profile-stats-grid');
    if (!statsGrid) return;
    
    if (width <= 480) {
        statsGrid.style.gridTemplateColumns = 'repeat(2, 1fr)';
    } else if (width <= 768) {
        statsGrid.style.gridTemplateColumns = 'repeat(2, 1fr)';
    } else {
        statsGrid.style.gridTemplateColumns = 'repeat(4, 1fr)';
    }
}

// Utility Functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Notification System
function ensureToastContainer() {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        container.setAttribute('aria-live', 'polite');
        container.setAttribute('aria-atomic', 'true');
        document.body.appendChild(container);
    }
    return container;
}

function showNotification(message, type = 'info', duration = 5000) {
    const container = ensureToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast-message ${type}`;
    toast.setAttribute('role', 'alert');
    toast.textContent = message;

    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));

    const dismiss = () => {
        toast.classList.add('hide');
        setTimeout(() => toast.remove(), 250);
    };

    if (duration !== 0) {
        setTimeout(dismiss, duration);
    }

    toast.addEventListener('click', dismiss);
}

// Export functions for potential external use
window.ProfilePage = {
    showTab,
    showNotification,
    handleEditClick,
    handleActionClick
};