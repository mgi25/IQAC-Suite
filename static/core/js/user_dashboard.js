// Unified Dashboard Controller

// On page load, fetch user role from backend
document.addEventListener('DOMContentLoaded', () => {
    fetch('/api/auth/me')
        .then(res => res.json())
        .then(user => {
            const role = user.role;
            loadDashboardForRole(role, user);
            setupNavigation();
            setupNotifications();
            setupFab();
            fetchAndRenderData(role, user);
        })
        .catch(() => {
            // fallback: hide everything
            document.body.innerHTML = '<div style="padding:2rem;text-align:center;color:red;">Unable to load dashboard. Please login.</div>';
        });
});

// Show/hide role-specific content
function loadDashboardForRole(role, user) {
    document.querySelectorAll('.faculty-only').forEach(el => el.style.display = (role === 'faculty' ? '' : 'none'));
    document.querySelectorAll('.student-only').forEach(el => el.style.display = (role === 'student' ? '' : 'none'));
    // Set welcome message and avatar
    document.getElementById('welcomeTitle').textContent = `Welcome, ${user.name || 'User'}!`;
    document.getElementById('welcomeSubtitle').textContent = user.subtitle || '';
    document.getElementById('profileAvatar').textContent = user.initials || 'U';
}

// Navigation tab logic
function setupNavigation() {
    const navTabs = document.querySelectorAll('.nav-tab');
    navTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            navTabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            const tabId = this.getAttribute('data-tab');
            document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
            const activeTab = document.getElementById(tabId);
            if (activeTab) activeTab.classList.add('active');
        });
    });
}

// Notification logic
function setupNotifications() {
    const notificationBtn = document.getElementById('notificationBtn');
    const notificationModal = document.getElementById('notificationModal');
    const closeBtn = document.getElementById('closeNotificationBtn');
    notificationBtn.addEventListener('click', () => notificationModal.classList.add('active'));
    closeBtn.addEventListener('click', () => notificationModal.classList.remove('active'));
}

// Floating Action Button logic
function setupFab() {
    const fabBtn = document.getElementById('fabBtn');
    fabBtn.addEventListener('click', () => {
        alert('Quick Action: This would open a modal or menu for quick actions.');
    });
}

// API contract: fetch data and render
function fetchAndRenderData(role, user) {
    if (role === 'faculty') {
        fetch('/api/faculty/overview').then(res => res.json()).then(renderStatsGrid);
        fetch('/api/faculty/events').then(res => res.json()).then(renderFacultyEvents);
        fetch('/api/faculty/students').then(res => res.json()).then(renderStudentsList);
    } else {
        fetch('/api/student/overview').then(res => res.json()).then(data => {
            renderStatsGrid(data.stats);
            renderAttributesSection(data.attributes);
            renderRemarksSection(data.remarks);
        });
        fetch('/api/student/events').then(res => res.json()).then(data => {
            renderStudentEvents(data.participated, data.upcoming);
        });
        fetch('/api/student/achievements').then(res => res.json()).then(data => {
            renderAchievementStats(data.stats);
            renderAchievementsList(data.achievements);
            renderPeerAchievements(data.peers);
        });
    }
}

// --- Render Functions ---
// These functions expect data from the backend and generate HTML as before.
// Use the render functions from the previous answer, but remove any hardcoded data.
// Example:
function renderStatsGrid(stats) {
    const grid = document.getElementById('statsGrid');
    grid.innerHTML = stats.map(stat => `
        <div class="stat-card ${stat.color}">
            <div class="stat-content">
                <div class="stat-text">
                    <p class="stat-label">${stat.label}</p>
                    <p class="stat-value">${stat.value}</p>
                    <p class="stat-subtitle">${stat.subtitle}</p>
                </div>
                <i class="fas fa-${stat.icon} stat-icon"></i>
            </div>
        </div>
    `).join('');
}

// ... (repeat for other render functions, as in previous answer, but all data comes from backend) ...

function renderFacultyEvents(events) { /* ... */ }
function renderStudentsList(students) { /* ... */ }
function renderAttributesSection(attributes) { /* ... */ }
function renderRemarksSection(remarks) { /* ... */ }
function renderStudentEvents(participated, upcoming) { /* ... */ }
function renderAchievementStats(stats) { /* ... */ }
function renderAchievementsList(achievements) { /* ... */ }
function renderPeerAchievements(peers) { /* ... */ }

document.querySelector('.graph-icon').addEventListener('click', function() {
    window.location.href = '/dashboard/';
});