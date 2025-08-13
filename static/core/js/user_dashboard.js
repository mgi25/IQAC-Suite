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
    const prettyRole = role.charAt(0).toUpperCase() + role.slice(1);
    document.getElementById('welcomeTitle').textContent = `Welcome (${prettyRole})`;
    document.getElementById('welcomeSubtitle').textContent = user.name || '';
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

function renderFacultyEvents(events) {
    const container = document.getElementById('facultyEventsSection');
    if (!container) return;
    if (!events || !events.length) {
        container.innerHTML = '<p>No events found.</p>';
        return;
    }
    container.innerHTML = events.map(ev => `
        <div class="list-card">
            <h4>${ev.title}</h4>
            <p>${ev.date} - ${ev.status}</p>
        </div>
    `).join('');
}

function renderStudentsList(students) {
    const container = document.getElementById('studentsList');
    if (!container) return;
    if (!students || !students.length) {
        container.innerHTML = '<p>No students assigned.</p>';
        return;
    }
    container.innerHTML = students.map(st => `
        <div class="list-card">
            <span>${st.name}</span>
            <span class="progress">${st.progress}%</span>
        </div>
    `).join('');
}

function renderAttributesSection(attributes) {
    const container = document.getElementById('attributesSection');
    if (!container) return;
    if (!attributes) return;
    container.innerHTML = attributes.map(attr => `
        <div class="list-card">
            <span>${attr.label}</span>
            <span>${attr.level}</span>
        </div>
    `).join('');
}

function renderRemarksSection(remarks) {
    const container = document.getElementById('remarksSection');
    if (!container) return;
    if (!remarks) return;
    container.innerHTML = remarks.map(r => `
        <div class="list-card">${r}</div>
    `).join('');
}

function renderStudentEvents(participated, upcoming) {
    const container = document.getElementById('studentEventsSection');
    if (!container) return;
    let html = '';
    if (participated && participated.length) {
        html += '<h4>Participated</h4>';
        html += participated.map(ev => `
            <div class="list-card"><h5>${ev.title}</h5><p>${ev.date}</p></div>
        `).join('');
    }
    if (upcoming && upcoming.length) {
        html += '<h4>Upcoming</h4>';
        html += upcoming.map(ev => `
            <div class="list-card"><h5>${ev.title}</h5><p>${ev.date}</p></div>
        `).join('');
    }
    container.innerHTML = html || '<p>No events found.</p>';
}

function renderAchievementStats(stats) {
    const container = document.getElementById('achievementStats');
    if (!container) return;
    if (!stats) return;
    container.innerHTML = `
        <div class="stat-card purple">
            <div class="stat-content">
                <div class="stat-text">
                    <p class="stat-label">Total Achievements</p>
                    <p class="stat-value">${stats.total || 0}</p>
                    <p class="stat-subtitle">This Year: ${stats.this_year || 0}</p>
                </div>
                <i class="fas fa-trophy stat-icon"></i>
            </div>
        </div>
    `;
}

function renderAchievementsList(achievements) {
    const container = document.getElementById('achievementsList');
    if (!container) return;
    if (!achievements) return;
    container.innerHTML = achievements.map(a => `
        <div class="list-card">
            <h5>${a.title}</h5>
            <p>${a.year}</p>
        </div>
    `).join('');
}

function renderPeerAchievements(peers) {
    const container = document.getElementById('peerAchievements');
    if (!container) return;
    if (!peers) return;
    container.innerHTML = peers.map(p => `
        <div class="list-card">
            <h5>${p.name}</h5>
            <p>${p.achievement}</p>
        </div>
    `).join('');
}

const graphIcon = document.querySelector('.graph-icon');
if (graphIcon) {
    graphIcon.addEventListener('click', function() {
        window.location.href = '/dashboard/';
    });
}

document.addEventListener('DOMContentLoaded', function () {
    
    // --- Event Contribution Donut Chart ---
    const chartCanvas = document.getElementById('eventContributionChart');
    const percentageSpan = document.getElementById('chartPercentage');

    if (chartCanvas && percentageSpan) {
        // Get the percentage value from the span, remove the '%' and convert to a number
        const contributionPercentage = parseFloat(percentageSpan.textContent) || 0;

        new Chart(chartCanvas, {
            type: 'doughnut',
            data: {
                labels: ['My Contribution', 'Other'],
                datasets: [{
                    label: 'Event Contribution',
                    data: [contributionPercentage, 100 - contributionPercentage],
                    backgroundColor: [
                        '#007bff', // --primary-color
                        '#e9ecef'  // A light grey for the remainder
                    ],
                    borderColor: [
                        '#ffffff' // --card-bg
                    ],
                    borderWidth: 4,
                    cutout: '75%'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false
                    }
                }
            }
        });
    }

    // --- Add other interactive JS here in the future ---
    // For example, handling tab clicks to
});