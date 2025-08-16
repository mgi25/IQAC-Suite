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
    
    // Initialize profile completion animation
    initializeProfileCompletion();
    
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

// Profile Completion Animation
function initializeProfileCompletion() {
    const completionFill = document.querySelector('.completion-fill');
    if (completionFill) {
        // Animate completion bar on load
        const targetWidth = completionFill.style.width;
        completionFill.style.width = '0%';
        
        setTimeout(() => {
            completionFill.style.width = targetWidth;
        }, 500);
    }
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
function showNotification(message, type = 'info') {
    // Remove existing notification
    const existingNotification = document.querySelector('.profile-notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `profile-notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-message">${message}</span>
            <button class="notification-close">&times;</button>
        </div>
    `;
    
    // Add notification styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 1000;
        padding: 12px 16px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        font-family: 'Inter', sans-serif;
        animation: slideIn 0.3s ease;
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Handle close button
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.addEventListener('click', () => {
        notification.remove();
    });
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }
    }, 5000);
}

// Add notification animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .notification-content {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .notification-close {
        background: none;
        border: none;
        color: white;
        font-size: 18px;
        cursor: pointer;
        padding: 0;
        width: 20px;
        height: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        opacity: 0.7;
        transition: opacity 0.2s;
    }
    
    .notification-close:hover {
        opacity: 1;
    }
`;
document.head.appendChild(style);

// Export functions for potential external use
window.ProfilePage = {
    showTab,
    showNotification,
    handleEditClick,
    handleActionClick
};