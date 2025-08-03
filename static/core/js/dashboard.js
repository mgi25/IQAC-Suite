console.log('Script loaded!');
// Wait for the DOM to be fully loaded before running scripts
document.addEventListener('DOMContentLoaded', function () {
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
    }

    /**
     * Hides the modal.
     */
    function hideModal() {
        if (!modal) return;
        modal.classList.remove('visible');
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

        // Helper to check if event matches filter
        function matches(event, type, time, role) {
            let match = true;
            if (type === 'my' && event.dataset.eventType !== 'my') match = false;
            if (type === 'department' && event.dataset.eventType !== 'other') match = false;
            if (role && event.dataset.eventRole && !event.dataset.eventRole.toLowerCase().includes(role)) match = false;
            if (time) {
                const now = new Date();
                const eventMonth = event.dataset.eventTime;
                if (time === 'week') {
                    // Only show events in current week
                    // (Assume eventMonth is YYYY-MM, not enough for week, so skip for now)
                } else if (time === 'next_month') {
                    const nextMonth = (now.getMonth() + 2).toString().padStart(2, '0');
                    const nextMonthStr = `${now.getFullYear()}-${nextMonth}`;
                    if (eventMonth !== nextMonthStr) match = false;
                } else if (time === 'this_month') {
                    const thisMonth = (now.getMonth() + 1).toString().padStart(2, '0');
                    const thisMonthStr = `${now.getFullYear()}-${thisMonth}`;
                    if (eventMonth !== thisMonthStr) match = false;
                }
            }
            return match;
        }

        // Filter My Events
        document.querySelectorAll('#myEventsList .event-item').forEach(event => {
            if (matches(event, type, time, role) || type === '' && role === '' && time === '') {
                event.style.display = '';
            } else {
                event.style.display = 'none';
            }
        });
        // Filter Other University Events
        document.querySelectorAll('#otherEventsList .university-event').forEach(event => {
            if (matches(event, type, time, role) || type === '' && role === '' && time === '') {
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

// --- OPTIONAL: Make modal functions globally available for debugging ---
window.showModal = window.hideModal = undefined;
