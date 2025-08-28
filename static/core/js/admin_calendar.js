document.addEventListener('DOMContentLoaded', () => {
    // Initialize calendar events from server data
    let CALENDAR_EVENTS = [];
    try {
        CALENDAR_EVENTS = JSON.parse(document.getElementById('events-data').textContent);
    } catch {
        CALENDAR_EVENTS = [];
    }

    // Calendar elements
    const elements = {
        calendar: document.getElementById('miniCalendar'),
        title: document.getElementById('calTitle'),
        grid: document.getElementById('calGrid'),
        prev: document.getElementById('calPrev'),
        next: document.getElementById('calNext'),
        details: document.getElementById('eventDetailsContent'),
        clearDetails: document.getElementById('clearEventDetails')
    };

    // Calendar state
    let currentDate = new Date();
    let selectedDate = null;

    function renderCalendar() {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        
        // Update title
        elements.title.textContent = currentDate.toLocaleString('default', { 
            month: 'long', 
            year: 'numeric' 
        });

        // Calculate calendar days
        const firstDay = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        
        // Clear grid
        elements.grid.innerHTML = '';

        // Add empty cells for days before month starts
        for (let i = 0; i < firstDay; i++) {
            const emptyCell = document.createElement('div');
            emptyCell.className = 'day muted';
            elements.grid.appendChild(emptyCell);
        }

        // Add days
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        for (let day = 1; day <= daysInMonth; day++) {
            const date = new Date(year, month, day);
            const dateStr = date.toISOString().split('T')[0];
            
            const dayEl = document.createElement('button');
            dayEl.className = 'day';
            dayEl.textContent = day;
            
            // Add classes for today and selected
            if (date.getTime() === today.getTime()) {
                dayEl.classList.add('today');
            }
            if (selectedDate && date.getTime() === selectedDate.getTime()) {
                dayEl.classList.add('selected');
            }

            // Check for events
            const dayEvents = CALENDAR_EVENTS.filter(e => e.date === dateStr);
            if (dayEvents.length > 0) {
                dayEl.classList.add('has-events');
            }

            // Add click handler for all days
            dayEl.addEventListener('click', () => showEventDetails(date));
            elements.grid.appendChild(dayEl);
        }
    }

    function showEventDetails(date) {
        // Adjust for timezone offset
        const adjustedDate = new Date(date.getTime() - (date.getTimezoneOffset() * 60000));
        selectedDate = adjustedDate;
        const dateStr = adjustedDate.toISOString().split('T')[0];
        const dayEvents = CALENDAR_EVENTS.filter(e => e.date === dateStr);
        
        const formattedDate = adjustedDate.toLocaleDateString('default', { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });

        // Debug log to check event data
        console.log('Events for date:', dayEvents);

        elements.details.innerHTML = `
            <div class="event-date">${formattedDate}</div>
            ${dayEvents.length ? dayEvents.map(event => `
                <div class="event-item">
                    <div class="event-title">${event.title}</div>
                    <a href="/emt/proposal-status/${event.event_id || event.id}/" class="view-details-btn">
                        View Details <i class="fas fa-arrow-right"></i>
                    </a>
                </div>
            `).join('') : '<div class="empty">No events scheduled for this date</div>'}
        `;
        
        elements.clearDetails.style.display = 'block';
        renderCalendar();
    }


    // Event Listeners
    elements.prev.addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() - 1);
        renderCalendar();
    });

    elements.next.addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() + 1);
        renderCalendar();
    });

    elements.clearDetails.addEventListener('click', () => {
        selectedDate = null;
        elements.details.innerHTML = '<div class="empty">Click an event in the calendar to view details</div>';
        elements.clearDetails.style.display = 'none';
        renderCalendar();
    });

    // Initial render
    renderCalendar();
});