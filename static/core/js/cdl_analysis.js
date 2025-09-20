document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
});

let chartInstances = {};
let currentData = null;

function initializeDashboard() {
    loadAnalyticsData();
    initializeFilters();
    initializeViewToggle();
    initializeModals();
}

function loadAnalyticsData() {
    const filters = {
        start_date: document.getElementById('start-date')?.value || '',
        end_date: document.getElementById('end-date')?.value || '',
        department: document.getElementById('department-filter')?.value || '',
        event_type: document.getElementById('event-type-filter')?.value || '',
        sort_by: document.getElementById('sort-filter')?.value || 'date'
    };

    fetch('/api/cdl/analysis/?' + new URLSearchParams(filters))
        .then(response => response.json())
        .then(data => {
            currentData = data;
            updateKPIs(data.kpis);
            updateCharts(data.charts);
            updateEventsList(data.events);
            updateFilterOptions(data.filter_options);
        })
        .catch(error => {
            console.error('Error loading analytics data:', error);
            showError('Failed to load analytics data');
        });
}

function updateFilterOptions(filterOptions) {
    if (!filterOptions) return;
    
    // Update department dropdown
    const deptSelect = document.getElementById('department-filter');
    if (deptSelect && filterOptions.departments) {
        // Keep the "All Departments" option and add others
        const currentValue = deptSelect.value;
        deptSelect.innerHTML = '<option value="">All Departments</option>';
        
        filterOptions.departments.forEach(dept => {
            const option = document.createElement('option');
            option.value = dept;
            option.textContent = dept;
            deptSelect.appendChild(option);
        });
        
        // Restore previous selection
        if (currentValue) {
            deptSelect.value = currentValue;
        }
    }
    
    // Update event type dropdown
    const typeSelect = document.getElementById('event-type-filter');
    if (typeSelect && filterOptions.event_types) {
        // Keep the "All Types" option and add others
        const currentValue = typeSelect.value;
        typeSelect.innerHTML = '<option value="">All Types</option>';
        
        filterOptions.event_types.forEach(type => {
            const option = document.createElement('option');
            option.value = type;
            option.textContent = type;
            typeSelect.appendChild(option);
        });
        
        // Restore previous selection
        if (currentValue) {
            typeSelect.value = currentValue;
        }
    }
}

function updateKPIs(kpis) {
    // Map KPI cards by container IDs
    const totalEl = document.querySelector('#kpiTotalEvents .kpi-number');
    const participantsEl = document.querySelector('#kpiTotalParticipants .kpi-number');
    const certsEl = document.querySelector('#kpiCertificatesIssued .kpi-number');
    const avgEl = document.querySelector('#kpiAvgParticipants .kpi-number');
    if (totalEl) totalEl.textContent = kpis.total_events ?? 0;
    if (participantsEl) participantsEl.textContent = kpis.total_participants ?? 0;
    if (certsEl) certsEl.textContent = kpis.total_certificates ?? 0;
    if (avgEl) avgEl.textContent = kpis.avg_participants ?? 0;
}

function updateCharts(chartData) {
    // Destroy existing charts
    Object.values(chartInstances).forEach(chart => chart.destroy());
    chartInstances = {};

    // Department Distribution Chart
    if (chartData.departments) {
        const deptCtx = document.getElementById('department-chart').getContext('2d');
        chartInstances.department = new Chart(deptCtx, {
            type: 'doughnut',
            data: {
                labels: chartData.departments.labels,
                datasets: [{
                    data: chartData.departments.data,
                    backgroundColor: [
                        '#1e60b1', '#3b82f6', '#6366f1', '#8b5cf6',
                        '#a855f7', '#d946ef', '#ec4899', '#f43f5e'
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
    }

    // Event Type Distribution Chart
    if (chartData.event_types) {
        const typeCtx = document.getElementById('type-chart').getContext('2d');
        chartInstances.eventType = new Chart(typeCtx, {
            type: 'bar',
            data: {
                labels: chartData.event_types.labels,
                datasets: [{
                    label: 'Events',
                    data: chartData.event_types.data,
                    backgroundColor: '#1e60b1',
                    borderColor: '#1e60b1',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }

    // Monthly Trends Chart
    if (chartData.monthly_trends) {
        const trendCtx = document.getElementById('trend-chart').getContext('2d');
        chartInstances.trends = new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: chartData.monthly_trends.labels,
                datasets: [{
                    label: 'Events',
                    data: chartData.monthly_trends.data,
                    borderColor: '#1e60b1',
                    backgroundColor: 'rgba(30, 96, 177, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#1e60b1',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }
}

function updateEventsList(events) {
    const gridView = document.getElementById('events-grid');
    const tableView = document.getElementById('events-table');
    
    if (!events || events.length === 0) {
        gridView.innerHTML = '<div class="empty">No completed events found</div>';
        if (tableView) {
            tableView.innerHTML = '<div class="empty">No completed events found</div>';
        }
        return;
    }

    // Update grid view
    gridView.innerHTML = events.map(event => `
        <div class="event-card">
            <div class="event-title">${event.event_title}</div>
            <div class="event-meta">
                <div class="event-meta-item">
                    <i class="fas fa-calendar"></i>
                    ${new Date(event.event_date).toLocaleDateString()}
                </div>
                <div class="event-meta-item">
                    <i class="fas fa-building"></i>
                    ${event.department}
                </div>
                <div class="event-meta-item">
                    <i class="fas fa-tag"></i>
                    ${event.event_type}
                </div>
            </div>
            <div class="event-stats">
                <div class="stat-item">
                    <div class="stat-number">${event.no_of_participants || 0}</div>
                    <div class="stat-label">Participants</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">${event.certificates_issued || 0}</div>
                    <div class="stat-label">Certificates</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">${event.rating || 'N/A'}</div>
                    <div class="stat-label">Rating</div>
                </div>
            </div>
            <div class="event-actions">
                <button class="btn btn-sm btn-outline-primary" onclick="viewEventDetails(${event.id})">
                    <i class="fas fa-eye"></i> View
                </button>
                <button class="btn btn-sm btn-outline-secondary" onclick="downloadReport(${event.id})">
                    <i class="fas fa-download"></i> Report
                </button>
            </div>
        </div>
    `).join('');

    // Update table view if exists
    if (tableView) {
        const tbody = tableView.querySelector('tbody');
        if (tbody) {
            tbody.innerHTML = events.map(event => `
                <tr>
                    <td>${event.event_title}</td>
                    <td>${new Date(event.event_date).toLocaleDateString()}</td>
                    <td>${event.department}</td>
                    <td>${event.event_type}</td>
                    <td>${event.no_of_participants || 0}</td>
                    <td>${event.certificates_issued || 0}</td>
                    <td>${event.rating || 'N/A'}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="viewEventDetails(${event.id})">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-secondary ml-1" onclick="downloadReport(${event.id})">
                            <i class="fas fa-download"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        }
    }
}

function initializeFilters() {
    // Add event listeners to filter elements
    ['start-date', 'end-date', 'department-filter', 'event-type-filter', 'sort-filter'].forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.addEventListener('change', loadAnalyticsData);
        }
    });

    // Apply and Reset buttons
    const applyBtn = document.getElementById('applyFilters');
    const resetBtn = document.getElementById('resetFilters');
    if (applyBtn) applyBtn.addEventListener('click', loadAnalyticsData);
    if (resetBtn) resetBtn.addEventListener('click', () => {
        const ids = ['start-date', 'end-date', 'department-filter', 'event-type-filter', 'sort-filter'];
        ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        // Reset sort to default
        const sort = document.getElementById('sort-filter');
        if (sort) sort.value = 'date';
        // Re-init default date range
        const startDate = document.getElementById('start-date');
        const endDate = document.getElementById('end-date');
        if (startDate) {
            const sixMonthsAgo = new Date();
            sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);
            startDate.value = sixMonthsAgo.toISOString().split('T')[0];
        }
        if (endDate) {
            endDate.value = new Date().toISOString().split('T')[0];
        }
        loadAnalyticsData();
    });

    // Export button
    const exportBtn = document.getElementById('exportBtn');
    if (exportBtn) exportBtn.addEventListener('click', exportData);

    // Initialize date inputs with default values
    const startDate = document.getElementById('start-date');
    const endDate = document.getElementById('end-date');
    
    if (startDate && !startDate.value) {
        // Default to last 6 months
        const sixMonthsAgo = new Date();
        sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);
        startDate.value = sixMonthsAgo.toISOString().split('T')[0];
    }
    
    if (endDate && !endDate.value) {
        endDate.value = new Date().toISOString().split('T')[0];
    }
}

function initializeViewToggle() {
    const gridBtn = document.getElementById('grid-view-btn');
    const tableBtn = document.getElementById('table-view-btn');
    const gridView = document.getElementById('events-grid');
    const tableView = document.getElementById('events-table');

    if (gridBtn && tableBtn) {
        gridBtn.addEventListener('click', () => {
            gridBtn.classList.add('active');
            tableBtn.classList.remove('active');
            if (gridView) gridView.style.display = 'grid';
            if (tableView) tableView.style.display = 'none';
        });

        tableBtn.addEventListener('click', () => {
            tableBtn.classList.add('active');
            gridBtn.classList.remove('active');
            if (gridView) gridView.style.display = 'none';
            if (tableView) tableView.style.display = 'block';
        });
    }
}

function initializeModals() {
    // Notes modal
    const addNoteBtn = document.getElementById('add-note-btn');
    const notesModal = document.getElementById('notes-modal');
    const closeModal = document.querySelector('.modal-close');
    const saveNoteBtn = document.getElementById('save-note-btn');
    const cancelNoteBtn = document.getElementById('cancel-note-btn');

    if (addNoteBtn && notesModal) {
        addNoteBtn.addEventListener('click', () => {
            notesModal.style.display = 'flex';
            document.getElementById('note-text').value = '';
        });

        [closeModal, cancelNoteBtn].forEach(btn => {
            if (btn) {
                btn.addEventListener('click', () => {
                    notesModal.style.display = 'none';
                });
            }
        });

        if (saveNoteBtn) {
            saveNoteBtn.addEventListener('click', saveNote);
        }

        // Close modal on outside click
        notesModal.addEventListener('click', (e) => {
            if (e.target === notesModal) {
                notesModal.style.display = 'none';
            }
        });
    }
}

function saveNote() {
    const noteText = document.getElementById('note-text').value.trim();
    if (!noteText) {
        alert('Please enter a note');
        return;
    }

    // Here you would typically save to backend
    // For now, just add to the UI
    const notesContainer = document.getElementById('notes-container');
    const noteItem = document.createElement('div');
    noteItem.className = 'note-item';
    noteItem.innerHTML = `
        <div class="note-header">
            <span class="note-author">Current User</span>
            <span class="note-date">${new Date().toLocaleDateString()}</span>
        </div>
        <div class="note-content">${noteText}</div>
    `;
    
    notesContainer.insertBefore(noteItem, notesContainer.firstChild);
    
    // Close modal
    document.getElementById('notes-modal').style.display = 'none';
}

function exportData() {
    if (!currentData || !currentData.events) {
        alert('No data to export');
        return;
    }

    const headers = ['Event Title', 'Date', 'Department', 'Type', 'Participants', 'Certificates', 'Rating'];
    const csvContent = [
        headers.join(','),
        ...currentData.events.map(event => [
            `"${event.event_title}"`,
            new Date(event.event_date).toLocaleDateString(),
            `"${event.department}"`,
            `"${event.event_type}"`,
            event.no_of_participants || 0,
            event.certificates_issued || 0,
            event.rating || 'N/A'
        ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cdl_analysis_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

function viewEventDetails(eventId) {
    // This would typically open a modal or navigate to detailed view
    console.log('View event details:', eventId);
    // Placeholder - implement based on your needs
    alert(`View details for event ID: ${eventId}`);
}

function downloadReport(eventId) {
    // This would download a detailed report for the event
    console.log('Download report for event:', eventId);
    // Placeholder - implement based on your needs
    alert(`Download report for event ID: ${eventId}`);
}

function showError(message) {
    // You can implement a more sophisticated error display
    console.error(message);
    alert(message);
}
