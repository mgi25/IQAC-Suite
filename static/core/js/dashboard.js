// --- Tab Navigation ---
document.addEventListener('DOMContentLoaded', function() {
  // Tab switching functionality
  const tabButtons = document.querySelectorAll('.nav-tab[data-tab]');
  const tabContents = document.querySelectorAll('.tab-content');

  tabButtons.forEach(button => {
    button.addEventListener('click', function() {
      const targetTab = this.dataset.tab;
      
      // Remove active class from all tabs and contents
      tabButtons.forEach(btn => btn.classList.remove('active'));
      tabContents.forEach(content => content.classList.remove('active'));
      
      // Add active class to clicked tab and corresponding content
      this.classList.add('active');
      const targetContent = document.getElementById(targetTab);
      if (targetContent) {
        targetContent.classList.add('active');
      }
    });
  });

  // Calendar functionality follows below...
});
// Example: Replace with actual events from backend
const EVENTS = window.DASHBOARD_EVENTS || [
  // { date: '2025-08-16', title: 'test', id: 1 }, ...
];

function getEventsForDate(dateStr) {
  return EVENTS.filter(ev => ev.date === dateStr);
}

function showEventsModal(dateStr, events) {
  let modal = document.createElement('div');
  modal.className = 'calendar-events-modal';
  modal.innerHTML = `<div class="modal-content">
    <button class="modal-close" onclick="this.parentNode.parentNode.remove()">&times;</button>
    <h3>Events on ${dateStr}</h3>
    <div class="events-list">${events.length ? events.map(ev => `
      <div class="event-modal-item">
        <span class="event-title">${ev.title}</span>
        <a href="/admin/proposal/${ev.id}/" class="btn-link" target="_blank">View Details</a>
        <button class="btn-link" onclick="window.open('https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(ev.title)}&dates=${dateStr.replace(/-/g, '')}/${dateStr.replace(/-/g, '')}', '_blank')">Remind Me</button>
      </div>
    `).join('') : '<div>No events.</div>'}
    </div>
  </div>`;
  document.body.appendChild(modal);
}

// --- Calendar Rendering ---
document.addEventListener('DOMContentLoaded', function() {
  const calendarDays = document.getElementById('calendarDays');
  const currentMonthLabel = document.getElementById('currentMonth');
  const prevMonthBtn = document.getElementById('prevMonth');
  const nextMonthBtn = document.getElementById('nextMonth');

  if (!calendarDays || !currentMonthLabel || !prevMonthBtn || !nextMonthBtn) return;

  let today = new Date();
  let currentMonth = today.getMonth();
  let currentYear = today.getFullYear();

  function pad(n) { return n < 10 ? '0' + n : n; }

  function renderCalendar(month, year) {
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    let startDay = (firstDay.getDay() + 6) % 7;
    let daysInMonth = lastDay.getDate();
    currentMonthLabel.textContent = firstDay.toLocaleString('default', { month: 'long', year: 'numeric' });
    let daysHtml = '';
    for (let i = 0; i < startDay; i++) {
      daysHtml += '<div class="calendar-day empty"></div>';
    }
    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = `${year}-${pad(month+1)}-${pad(d)}`;
      const events = getEventsForDate(dateStr);
      const isToday = (d === today.getDate() && month === today.getMonth() && year === today.getFullYear());
      daysHtml += `<div class="calendar-day${isToday ? ' today' : ''}${events.length ? ' has-event' : ''}" data-date="${dateStr}">
        ${d}
        ${events.length ? '<span class="event-dot"></span>' : ''}
      </div>`;
    }
    calendarDays.innerHTML = daysHtml;
    // Add click listeners
    Array.from(calendarDays.querySelectorAll('.calendar-day.has-event')).forEach(day => {
      day.addEventListener('click', function() {
        showEventsModal(this.dataset.date, getEventsForDate(this.dataset.date));
      });
    });
  }

  prevMonthBtn.addEventListener('click', function() {
    currentMonth--;
    if (currentMonth < 0) {
      currentMonth = 11;
      currentYear--;
    }
    renderCalendar(currentMonth, currentYear);
  });
  nextMonthBtn.addEventListener('click', function() {
    currentMonth++;
    if (currentMonth > 11) {
      currentMonth = 0;
      currentYear++;
    }
    renderCalendar(currentMonth, currentYear);
  });

  renderCalendar(currentMonth, currentYear);
});
// Modern Calendar Rendering
document.addEventListener('DOMContentLoaded', function() {
  const calendarDays = document.getElementById('calendarDays');
  const currentMonthLabel = document.getElementById('currentMonth');
  const prevMonthBtn = document.getElementById('prevMonth');
  const nextMonthBtn = document.getElementById('nextMonth');

  if (!calendarDays || !currentMonthLabel || !prevMonthBtn || !nextMonthBtn) return;

  let today = new Date();
  let currentMonth = today.getMonth();
  let currentYear = today.getFullYear();

  function renderCalendar(month, year) {
    // Get first day of the month
    const firstDay = new Date(year, month, 1);
    // Get last day of the month
    const lastDay = new Date(year, month + 1, 0);
    // Get weekday index (0=Sun, 1=Mon...)
    let startDay = (firstDay.getDay() + 6) % 7; // Make Monday=0
    let daysInMonth = lastDay.getDate();

    // Set month label
    currentMonthLabel.textContent = firstDay.toLocaleString('default', { month: 'long', year: 'numeric' });

    // Build days grid
    let daysHtml = '';
    for (let i = 0; i < startDay; i++) {
      daysHtml += '<div class="calendar-day empty"></div>';
    }
    for (let d = 1; d <= daysInMonth; d++) {
      const isToday = (d === today.getDate() && month === today.getMonth() && year === today.getFullYear());
      daysHtml += `<div class="calendar-day${isToday ? ' today' : ''}">${d}</div>`;
    }
    calendarDays.innerHTML = daysHtml;
  }

  prevMonthBtn.addEventListener('click', function() {
    currentMonth--;
    if (currentMonth < 0) {
      currentMonth = 11;
      currentYear--;
    }
    renderCalendar(currentMonth, currentYear);
  });
  nextMonthBtn.addEventListener('click', function() {
    currentMonth++;
    if (currentMonth > 11) {
      currentMonth = 0;
      currentYear++;
    }
    renderCalendar(currentMonth, currentYear);
  });

  renderCalendar(currentMonth, currentYear);
});
// Stat card click handlers for filtering events
    const cardUpcoming = document.getElementById('cardUpcoming');
    const cardOrganized = document.getElementById('cardOrganized');
    const cardThisWeek = document.getElementById('cardThisWeek');

    if (cardUpcoming) {
        cardUpcoming.addEventListener('click', function() {
            // Show all upcoming events (after today)
            document.getElementById('eventTimeFilter').value = '';
            document.getElementById('eventTypeFilter').value = '';
            filterEvents();
        });
    }
    if (cardOrganized) {
        cardOrganized.addEventListener('click', function() {
            // Show only events user proposed (My Events)
            document.getElementById('eventTypeFilter').value = 'my';
            document.getElementById('eventTimeFilter').value = '';
            filterEvents();
        });
    }
    if (cardThisWeek) {
        cardThisWeek.addEventListener('click', function() {
            // Show only events happening this week
            document.getElementById('eventTimeFilter').value = 'week';
            document.getElementById('eventTypeFilter').value = '';
            filterEvents();
        });
    }
console.log('Script loaded!');
// Wait for the DOM to be fully loaded before running scripts
document.addEventListener('DOMContentLoaded', function () {
    // --- STAT CARD CLICK HANDLERS ---
    const cardUpcoming = document.getElementById('cardUpcoming');
    const cardOrganized = document.getElementById('cardOrganized');
    const cardThisWeek = document.getElementById('cardThisWeek');
    const eventsTab = document.querySelector('.nav-tab[data-tab="events"]');

    function switchToEventsTab() {
        if (eventsTab) {
            activateTab(eventsTab);
        }
    }

    if (cardUpcoming) {
        cardUpcoming.addEventListener('click', function() {
            switchToEventsTab();
            document.getElementById('eventTimeFilter').value = '';
            document.getElementById('eventTypeFilter').value = '';
            filterEvents();
        });
    }
    if (cardOrganized) {
        cardOrganized.addEventListener('click', function() {
            switchToEventsTab();
            document.getElementById('eventTypeFilter').value = 'my';
            document.getElementById('eventTimeFilter').value = '';
            filterEvents();
        });
    }
    if (cardThisWeek) {
        cardThisWeek.addEventListener('click', function() {
            switchToEventsTab();
            document.getElementById('eventTimeFilter').value = 'week';
            document.getElementById('eventTypeFilter').value = '';
            filterEvents();
        });
    }
    console.log('Dashboard JavaScript loaded');

    // --- CACHE DOM ELEMENTS ---
    const dashboard = document.querySelector('.user-dashboard');
    const tabs = document.querySelectorAll('.nav-tab');
    const tabContents = document.querySelectorAll('.tab-content');
    const searchInput = document.getElementById('studentSearch');
    const filters = document.querySelectorAll('.filter-select');
    const modal = document.getElementById('dashboardModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');

    // --- MODAL FUNCTIONS ---
    /**
     * Shows the modal with a given title and body content.
     * @param {string} title - The title to display in the modal header.
     * @param {string} body - The HTML content to display in the modal body.
     */
    function showModal(title, body) {
        if (!modal || !modalTitle || !modalBody) return;
        modalTitle.textContent = title;
        modalBody.innerHTML = body;
        modal.classList.add('visible');
        // Attach close handler to cross button (modal-close)
        const closeBtn = modal.querySelector('.modal-close');
        if (closeBtn) {
            closeBtn.onclick = function() {
                hideModal();
            };
        }
    }

    /**
     * Hides the modal.
     */
    function hideModal() {
        if (!modal) return;
        modal.classList.remove('visible');
        // Optionally clear modal content
        modalTitle.textContent = '';
        modalBody.innerHTML = '';
    }

    // --- EVENT HANDLING ---
    if (dashboard) {
        dashboard.addEventListener('click', function(event) {
            const actionTarget = event.target.closest('[data-action]');
            if (!actionTarget) return;

            const action = actionTarget.dataset.action;
            const eventId = actionTarget.dataset.eventId;
            const studentId = actionTarget.dataset.studentId;
            const classId = actionTarget.dataset.classId;

            // Prevent propagation for buttons inside clickable items
            if (['message-student', 'call-student'].includes(action)) {
                event.stopPropagation();
            }

            // Determine which action to take based on the data-action attribute
            switch (action) {
                case 'close-modal':
                    hideModal();
                    break;
                case 'create-event':
                    showModal('Create New Event', `
                        <form id="createEventForm" class="modal-form">
                            <div class="form-group">
                                <label for="eventTitle">Event Title</label>
                                <input type="text" id="eventTitle" name="title" required>
                            </div>
                            <div class="form-group">
                                <label for="eventDate">Date & Time</label>
                                <input type="datetime-local" id="eventDate" name="date" required>
                            </div>
                            <div class="form-group">
                                <label for="eventType">Event Type</label>
                                <select id="eventType" name="event_type" required>
                                    <option value="">Select Type</option>
                                    <option value="academic">Academic</option>
                                    <option value="cultural">Cultural</option>
                                    <option value="sports">Sports</option>
                                    <option value="technical">Technical</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="eventDescription">Description</label>
                                <textarea id="eventDescription" name="description" rows="3"></textarea>
                            </div>
                            <div class="form-group">
                                <label for="maxParticipants">Max Participants</label>
                                <input type="number" id="maxParticipants" name="max_participants" min="1">
                            </div>
                            <div class="form-actions">
                                <button type="button" data-action="close-modal" class="btn-secondary">Cancel</button>
                                <button type="submit" class="btn-primary">Create Event</button>
                            </div>
                        </form>
                    `);
                    break;
                case 'edit-event':
                    showModal('Edit Event', `
                        <div class="modal-content-body">
                            <p>Editing event ID: ${eventId}</p>
                            <p>This would load the event data and show an edit form.</p>
                            <div class="form-actions">
                                <button type="button" data-action="close-modal" class="btn-secondary">Close</button>
                            </div>
                        </div>
                    `);
                    break;
                case 'view-event-details':
                    showModal('Event Details', `
                        <div class="event-details-modal">
                            <p><strong>Event ID:</strong> ${eventId}</p>
                            <p><strong>Description:</strong> Detailed information about the event would be loaded here.</p>
                            <p><strong>Participants:</strong> List of registered participants</p>
                            <p><strong>Resources:</strong> Required resources and materials</p>
                            <div class="form-actions">
                                <button type="button" data-action="close-modal" class="btn-secondary">Close</button>
                            </div>
                        </div>
                    `);
                    break;
                case 'add-student':
                    showModal('Add Student', `
                        <form id="addStudentForm" class="modal-form">
                            <div class="form-group">
                                <label for="studentName">Student Name</label>
                                <input type="text" id="studentName" name="name" required>
                            </div>
                            <div class="form-group">
                                <label for="studentReg">Registration Number</label>
                                <input type="text" id="studentReg" name="registration_number" required>
                            </div>
                            <div class="form-group">
                                <label for="studentEmail">Email</label>
                                <input type="email" id="studentEmail" name="email" required>
                            </div>
                            <div class="form-actions">
                                <button type="button" data-action="close-modal" class="btn-secondary">Cancel</button>
                                <button type="submit" class="btn-primary">Add Student</button>
                            </div>
                        </form>
                    `);
                    break;
                case 'show-student-profile':
                    showModal('Student Profile', `
                        <div class="student-profile-modal">
                            <p><strong>Student ID:</strong> ${studentId}</p>
                            <p>Detailed student information would be loaded here including:</p>
                            <ul>
                                <li>Academic performance</li>
                                <li>Attendance records</li>
                                <li>Meeting history</li>
                                <li>Goals and achievements</li>
                            </ul>
                            <div class="form-actions">
                                <button type="button" data-action="close-modal" class="btn-secondary">Close</button>
                            </div>
                        </div>
                    `);
                    break;
                case 'message-student':
                    showModal('Message Student', `
                        <form id="messageStudentForm" class="modal-form">
                            <p><strong>Send message to Student ID:</strong> ${studentId}</p>
                            <div class="form-group">
                                <label for="messageSubject">Subject</label>
                                <input type="text" id="messageSubject" name="subject" required>
                            </div>
                            <div class="form-group">
                                <label for="messageBody">Message</label>
                                <textarea id="messageBody" name="message" rows="4" required></textarea>
                            </div>
                            <div class="form-actions">
                                <button type="button" data-action="close-modal" class="btn-secondary">Cancel</button>
                                <button type="submit" class="btn-primary">Send Message</button>
                            </div>
                        </form>
                    `);
                    break;
                case 'call-student':
                    showModal('Contact Student', `
                        <div class="contact-student-modal">
                            <p><strong>Contact Student ID:</strong> ${studentId}</p>
                            <p>Contact information would be displayed here:</p>
                            <ul>
                                <li>Phone: +1 (555) 123-4567</li>
                                <li>Email: student@university.edu</li>
                                <li>Emergency Contact: +1 (555) 987-6543</li>
                            </ul>
                            <div class="form-actions">
                                <button type="button" onclick="window.open('tel:+15551234567')" class="btn-primary">Call Now</button>
                                <button type="button" data-action="close-modal" class="btn-secondary">Close</button>
                            </div>
                        </div>
                    `);
                    break;
                case 'edit-profile':
                    showModal('Edit Profile', `
                        <form id="editProfileForm" class="modal-form">
                            <div class="form-group">
                                <label for="firstName">First Name</label>
                                <input type="text" id="firstName" name="first_name" required>
                            </div>
                            <div class="form-group">
                                <label for="lastName">Last Name</label>
                                <input type="text" id="lastName" name="last_name" required>
                            </div>
                            <div class="form-group">
                                <label for="department">Department</label>
                                <input type="text" id="department" name="department">
                            </div>
                            <div class="form-group">
                                <label for="designation">Designation</label>
                                <input type="text" id="designation" name="designation">
                            </div>
                            <div class="form-actions">
                                <button type="button" data-action="close-modal" class="btn-secondary">Cancel</button>
                                <button type="submit" class="btn-primary">Save Changes</button>
                            </div>
                        </form>
                    `);
                    break;
                case 'view-class-details':
                    showModal('Class Details', `
                        <div class="class-details-modal">
                            <p><strong>Class ID:</strong> ${classId}</p>
                            <p>Class information would include:</p>
                            <ul>
                                <li>Student roster</li>
                                <li>Syllabus and curriculum</li>
                                <li>Assignment schedule</li>
                                <li>Grade distribution</li>
                            </ul>
                            <div class="form-actions">
                                <button type="button" data-action="close-modal" class="btn-secondary">Close</button>
                            </div>
                        </div>
                    `);
                    break;
                case 'add-achievement':
                    showModal('Add Achievement', `
                        <form id="addAchievementForm" class="modal-form">
                            <div class="form-group">
                                <label for="achievementTitle">Achievement Title</label>
                                <input type="text" id="achievementTitle" name="title" required>
                            </div>
                            <div class="form-group">
                                <label for="achievementDate">Date Achieved</label>
                                <input type="date" id="achievementDate" name="date" required>
                            </div>
                            <div class="form-group">
                                <label for="achievementDescription">Description</label>
                                <textarea id="achievementDescription" name="description" rows="3"></textarea>
                            </div>
                            <div class="form-actions">
                                <button type="button" data-action="close-modal" class="btn-secondary">Cancel</button>
                                <button type="submit" class="btn-primary">Add Achievement</button>
                            </div>
                        </form>
                    `);
                    break;
                case 'add-goal':
                    showModal('Add Goal', `
                        <form id="addGoalForm" class="modal-form">
                            <div class="form-group">
                                <label for="goalTitle">Goal Title</label>
                                <input type="text" id="goalTitle" name="title" required>
                            </div>
                            <div class="form-group">
                                <label for="goalTarget">Target Date</label>
                                <input type="date" id="goalTarget" name="target_date" required>
                            </div>
                            <div class="form-group">
                                <label for="goalDescription">Description</label>
                                <textarea id="goalDescription" name="description" rows="3"></textarea>
                            </div>
                            <div class="form-actions">
                                <button type="button" data-action="close-modal" class="btn-secondary">Cancel</button>
                                <button type="submit" class="btn-primary">Add Goal</button>
                            </div>
                        </form>
                    `);
                    break;
            }
        });
    }

    // --- TAB SWITCHING ---
    function activateTab(tab) {
        if (!tab) {
            console.warn('activateTab called with null tab');
            return;
        }
        const tabId = tab.dataset.tab;
        const activeContent = document.getElementById(tabId);
        if (!tabId) {
            console.warn('Tab missing data-tab attribute:', tab);
            return;
        }
        if (!activeContent) {
            console.warn('No content found for tabId:', tabId);
        }
        tabs.forEach(t => t.classList.remove('active'));
        tabContents.forEach(c => c.classList.remove('active'));
        tab.classList.add('active');
        if (activeContent) {
            activeContent.classList.add('active');
        }
        console.log('Activated tab:', tabId);
    }

    tabs.forEach(tab => {
        tab.addEventListener('click', function(e) {
            e.preventDefault();
            if (tab.tagName === 'A') return; // Skip admin link
            activateTab(tab);
        });
    });

    // Fallback: If no tab is active, activate the first tab
    if (![...tabs].some(t => t.classList.contains('active'))) {
        activateTab(tabs[0]);
    }

    // Always ensure only one tab-content is visible after DOM loaded
    setTimeout(function() {
        let activeTab = [...tabs].find(t => t.classList.contains('active'));
        let activeContent = null;
        if (activeTab && activeTab.dataset.tab) {
            activeContent = document.getElementById(activeTab.dataset.tab);
        }
        tabs.forEach(t => t.classList.remove('active'));
        tabContents.forEach(c => c.classList.remove('active'));
        if (activeTab) activeTab.classList.add('active');
        if (activeContent) activeContent.classList.add('active');
        else if (tabContents[0]) tabContents[0].classList.add('active');
        console.log('Tab switching DOM sync complete');
    }, 100);

    // --- PROGRESS BAR ANIMATION ---
    setTimeout(function() {
        const progressBars = document.querySelectorAll('.progress-fill');
        progressBars.forEach(bar => {
            const targetWidth = bar.style.width;
            if (targetWidth) {
                bar.style.width = '0%';
                setTimeout(() => {
                    bar.style.transition = 'width 1s ease-in-out';
                    bar.style.width = targetWidth;
                }, 100);
            }
        });
    }, 300);

    // --- SEARCH FUNCTIONALITY ---
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const studentItems = document.querySelectorAll('.student-item');
            studentItems.forEach(item => {
                const studentName = item.querySelector('.student-info h4')?.textContent.toLowerCase() || '';
                const studentReg = item.querySelector('.student-reg')?.textContent.toLowerCase() || '';
                if (studentName.includes(searchTerm) || studentReg.includes(searchTerm)) {
                    item.style.display = 'flex';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }

    // --- FILTER FUNCTIONALITY ---
    // Event filter logic for My Events and Other University Events
    function filterEvents() {
        const type = document.getElementById('eventTypeFilter').value;
        const time = document.getElementById('eventTimeFilter').value;
        const role = document.getElementById('eventRoleFilter').value;
        // For department events, get user's organization name from a global JS variable (set in template)
        const userOrg = window.USER_ORG_NAME ? window.USER_ORG_NAME.toLowerCase() : null;

        // Helper to check if event matches filter
        function matches(event, type, time, role) {
            let match = true;
            // Type filter
            if (type === 'my' && event.dataset.eventType !== 'my') match = false;
            if (type === 'department') {
                // Show only department events the user is part of (my_events)
                if (event.dataset.eventType !== 'my') match = false;
            }
            // Role filter
            if (role && event.dataset.eventRole && !event.dataset.eventRole.toLowerCase().includes(role)) match = false;
            // Time filter
            if (time) {
                const now = new Date();
                let eventDateStr = null;
                // Try to get date from event-details or event-date
                if (event.querySelector('.event-details span')) {
                    // For My Events
                    eventDateStr = event.querySelector('.event-details span').textContent;
                } else if (event.querySelector('.event-date span')) {
                    // For University Events
                    eventDateStr = event.querySelector('.event-date span').textContent;
                } else if (event.querySelector('.event-date')) {
                    eventDateStr = event.querySelector('.event-date').textContent;
                }
                let eventDate = null;
                if (eventDateStr) {
                    // Try to parse date from string (format: 'M d, Y H:i' or 'M d')
                    const parts = eventDateStr.match(/([A-Za-z]+) (\d{1,2})(, (\d{4}))?/);
                    if (parts) {
                        const month = parts[1];
                        const day = parseInt(parts[2]);
                        const year = parts[4] ? parseInt(parts[4]) : now.getFullYear();
                        eventDate = new Date(`${month} ${day}, ${year}`);
                    }
                }
                if (time === 'week' && eventDate) {
                    // Show events in current week
                    const weekStart = new Date(now);
                    weekStart.setDate(now.getDate() - now.getDay());
                    const weekEnd = new Date(weekStart);
                    weekEnd.setDate(weekStart.getDate() + 6);
                    if (eventDate < weekStart || eventDate > weekEnd) match = false;
                } else if (time === 'next_month' && eventDate) {
                    if ((eventDate.getMonth() !== (now.getMonth() + 1) % 12) || eventDate.getFullYear() !== now.getFullYear()) match = false;
                } else if (time === 'this_month' && eventDate) {
                    if (eventDate.getMonth() !== now.getMonth() || eventDate.getFullYear() !== now.getFullYear()) match = false;
                }
            }
            return match;
        }

        // Filter My Events
        document.querySelectorAll('#myEventsList .event-item').forEach(event => {
            if (matches(event, type, time, role) || (type === '' && role === '' && time === '')) {
                event.style.display = '';
            } else {
                event.style.display = 'none';
            }
        });
        // Filter Other University Events
        document.querySelectorAll('#otherEventsList .university-event').forEach(event => {
            if (matches(event, type, time, role) || (type === '' && role === '' && time === '')) {
                event.style.display = '';
            } else {
                event.style.display = 'none';
            }
        });
    }

    filters.forEach(filter => {
        filter.addEventListener('change', filterEvents);
    });
});

document.addEventListener('DOMContentLoaded', function() {
    const tabs = document.querySelectorAll('.nav-tab');
    const tabContents = document.querySelectorAll('.tab-content');
    const calendarDaysContainer = document.querySelector('.calendar-days');
    const monthYearElement = document.getElementById('month-year');
    const prevMonthBtn = document.getElementById('prev-month');
    const nextMonthBtn = document.getElementById('next-month');
    const eventModal = document.getElementById('event-modal');
    const eventModalClose = document.querySelector('.event-modal-close');
    const modalBody = document.querySelector('.event-modal-body');
    const modalTitle = document.getElementById('modal-date-title');

    let currentDate = new Date();
    let events = {}; // Cache for events: { 'YYYY-MM': [event, ...] }
    let selectedDate = null;

    // --- Tab Functionality ---
    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            e.preventDefault();
            const target = tab.getAttribute('data-tab');

            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === target) {
                    content.classList.add('active');
                }
            });
        });
    });

    // --- Calendar Functionality ---
    async function fetchCalendarEvents(year, month) {
        const monthStr = `${year}-${String(month + 1).padStart(2, '0')}`;
        if (events[monthStr]) {
            return events[monthStr];
        }
        try {
            const response = await fetch(`/core/api/calendar-events/?month=${monthStr}`);
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            const data = await response.json();
            events[monthStr] = data.events;
            return data.events;
        } catch (error) {
            console.error('Failed to fetch calendar events:', error);
            return [];
        }
    }

    async function renderCalendar(date) {
        calendarDaysContainer.innerHTML = '';
        const year = date.getFullYear();
        const month = date.getMonth();
        
        monthYearElement.textContent = `${date.toLocaleString('default', { month: 'long' })} ${year}`;

        const monthEvents = await fetchCalendarEvents(year, month);
        const eventDates = new Set(monthEvents.map(e => new Date(e.start_time).getDate()));

        const firstDay = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();

        // Add empty placeholders for days before the 1st
        for (let i = 0; i < firstDay; i++) {
            calendarDaysContainer.innerHTML += `<div class="calendar-day other-month"></div>`;
        }

        // Add days of the month
        for (let day = 1; day <= daysInMonth; day++) {
            const dayEl = document.createElement('div');
            dayEl.classList.add('calendar-day');
            dayEl.textContent = day;
            dayEl.dataset.day = day;

            const today = new Date();
            if (year === today.getFullYear() && month === today.getMonth() && day === today.getDate()) {
                dayEl.classList.add('today');
            }

            if (eventDates.has(day)) {
                dayEl.classList.add('has-event');
            }
            
            dayEl.addEventListener('click', () => {
                selectedDate = new Date(year, month, day);
                document.querySelectorAll('.calendar-day').forEach(d => d.classList.remove('selected'));
                dayEl.classList.add('selected');
                if (eventDates.has(day)) {
                    showEventsForDate(selectedDate, monthEvents);
                }
            });

            calendarDaysContainer.appendChild(dayEl);
        }
    }

    function showEventsForDate(date, monthEvents) {
        modalTitle.textContent = `Events on ${date.toLocaleString('default', { month: 'long' })} ${date.getDate()}`;
        modalBody.innerHTML = '<div class="modal-loading"></div>';
        eventModal.style.display = 'flex';

        const eventsForDay = monthEvents.filter(e => new Date(e.start_time).getDate() === date.getDate());

        setTimeout(() => { // Simulate loading
            if (eventsForDay.length > 0) {
                modalBody.innerHTML = eventsForDay.map(event => `
                    <div class="modal-event-item">
                        <div class="modal-event-info">
                            <h4>${event.title}</h4>
                            <p class="modal-event-time">
                                ${new Date(event.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - 
                                ${new Date(event.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </p>
                            <p class="modal-event-description">${event.description || 'No description available.'}</p>
                        </div>
                        <div class="modal-event-actions">
                            <a href="/events/${event.id}/" class="btn-modal-action btn-view-details">
                                <i class="fas fa-eye"></i> View Details
                            </a>
                            <a href="${event.google_calendar_link}" target="_blank" class="btn-modal-action btn-add-google">
                                <i class="fab fa-google"></i> Add to Google
                            </a>
                        </div>
                    </div>
                `).join('');
            } else {
                modalBody.innerHTML = '<div class="no-events"><p>No events scheduled for this day.</p></div>';
            }
        }, 300);
    }

    prevMonthBtn.addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() - 1);
        renderCalendar(currentDate);
    });

    nextMonthBtn.addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() + 1);
        renderCalendar(currentDate);
    });

    eventModalClose.addEventListener('click', () => {
        eventModal.style.display = 'none';
    });

    window.addEventListener('click', (e) => {
        if (e.target === eventModal) {
            eventModal.style.display = 'none';
        }
    });

    // Initial Load
    renderCalendar(currentDate);
});

// --- OPTIONAL: Make modal functions globally available for debugging ---
window.showModal = window.hideModal = undefined;
