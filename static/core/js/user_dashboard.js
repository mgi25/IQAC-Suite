// Unified Dashboard Controller

// On page load, fetch user role from backend
document.addEventListener('DOMContentLoaded', () => {
    try {
        const el = document.getElementById('calendarEventsJson');
        window.DASHBOARD_EVENTS = el ? JSON.parse(el.textContent) : [];
    } catch {
        window.DASHBOARD_EVENTS = [];
    }
    // Precompute a Set of ISO date strings that contain events for quick lookup
    window.EVENT_DATE_SET = new Set();
    (window.DASHBOARD_EVENTS || []).forEach(ev => {
        if (ev.date) {
            window.EVENT_DATE_SET.add(ev.date);
        } else if (ev.start && ev.end) {
            let cur = new Date(ev.start);
            const end = new Date(ev.end);
            while (cur <= end) {
                window.EVENT_DATE_SET.add(cur.toISOString().split('T')[0]);
                cur.setDate(cur.getDate() + 1);
            }
        }
    });

    fetch('/api/auth/me')
        .then(res => res.json())
        .then(user => {
            const role = user.role;
            loadDashboardForRole(role, user);
            setupNavigation();
            setupNotifications();
            setupFab();
            fetchAndRenderData(role, user);
            initEventContributionChart();
            initCalendar();
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

function initEventContributionChart() {
    const chartCanvas = document.getElementById('eventContributionChart');
    if (!chartCanvas) return;
    fetch('/api/event-contribution/')
        .then(res => res.json())
        .then(data => {
            const pct = parseFloat(data.overall_percentage) || 0;
            new Chart(chartCanvas, {
                type: 'doughnut',
                data: {
                    labels: ['My Contribution', 'Other'],
                    datasets: [{
                        label: 'Event Contribution',
                        data: [pct, 100 - pct],
                        backgroundColor: ['#007bff', '#e9ecef'],
                        borderColor: ['#ffffff'],
                        borderWidth: 4,
                        cutout: '75%'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: { enabled: false }
                    }
                }
            });
        });
}

// Calendar logic
let calRef = new Date();
const fmt2 = v => String(v).padStart(2, '0');
const isSame = (a, b) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();

function buildCalendar() {
    const headTitle = document.getElementById('calTitle');
    const grid = document.getElementById('calGrid');
    if (!grid || !headTitle) return;

    headTitle.textContent = calRef.toLocaleString(undefined, { month: 'long', year: 'numeric' });

    const first = new Date(calRef.getFullYear(), calRef.getMonth(), 1);
    const last = new Date(calRef.getFullYear(), calRef.getMonth() + 1, 0);
    const startIdx = first.getDay();
    const prevLast = new Date(calRef.getFullYear(), calRef.getMonth(), 0).getDate();

    const cells = [];
    for (let i = startIdx - 1; i >= 0; i--) { cells.push({ text: prevLast - i, date: null, muted: true }); }
    for (let d = 1; d <= last.getDate(); d++) {
        const dt = new Date(calRef.getFullYear(), calRef.getMonth(), d);
        cells.push({ text: d, date: dt, muted: false });
    }
    while (cells.length % 7 !== 0) { cells.push({ text: cells.length % 7 + 1, date: null, muted: true }); }

    grid.innerHTML = cells.map(c => {
        const today = c.date && isSame(c.date, new Date());
        const iso = c.date ? `${c.date.getFullYear()}-${fmt2(c.date.getMonth() + 1)}-${fmt2(c.date.getDate())}` : '';
        const hasEvent = iso && window.EVENT_DATE_SET && window.EVENT_DATE_SET.has(iso);
        return `<div class="day${c.muted ? ' muted' : ''}${today ? ' today' : ''}${hasEvent ? ' has-event' : ''}" data-date="${iso}">${c.text}</div>`;
    }).join('');

    grid.querySelectorAll('.day[data-date]').forEach(el => {
        el.addEventListener('click', () => openDay(new Date(el.dataset.date)));
    });
}

function openDay(day) {
    const yyyy = day.getFullYear(), mm = fmt2(day.getMonth() + 1), dd = fmt2(day.getDate());
    const dateStr = `${yyyy}-${mm}-${dd}`;
    const list = document.getElementById('upcomingWrap');
    if (!list) return;
    const items = (window.DASHBOARD_EVENTS || []).filter(e => {
        if (e.date) return e.date === dateStr;
        if (e.start && e.end) return e.start <= dateStr && dateStr <= e.end;
        return false;
    });
    list.innerHTML = items.length
        ? items.map(e => {
            const time = e.datetime
                ? new Date(e.datetime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                : '';
            const meta = [time, e.venue].filter(Boolean).join(' @ ');
            return `<div class="u-item"><div>${e.title}${meta ? ' - ' + meta : ''}</div></div>`;
        }).join('')
        : `<div class="empty">No events for ${day.toLocaleDateString()}</div>`;
}

function initCalendar() {
    buildCalendar();
    document.getElementById('calPrev')?.addEventListener('click', () => { calRef = new Date(calRef.getFullYear(), calRef.getMonth() - 1, 1); buildCalendar(); });
    document.getElementById('calNext')?.addEventListener('click', () => { calRef = new Date(calRef.getFullYear(), calRef.getMonth() + 1, 1); buildCalendar(); });
}