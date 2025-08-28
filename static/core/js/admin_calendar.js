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

    function ymdLocal(d){
        const y=d.getFullYear();
        const m=String(d.getMonth()+1).padStart(2,'0');
        const da=String(d.getDate()).padStart(2,'0');
        return `${y}-${m}-${da}`;
    }

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
            const dateStr = ymdLocal(date);
            
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

            // Check for events and add uniform marker class used by dashboard CSS
            const dayEvents = CALENDAR_EVENTS.filter(e => e.date === dateStr);
            if (dayEvents.length > 0) {
                dayEl.classList.add('has-event');
            }

            // Add interactions (click only; remove hover preview)
            dayEl.addEventListener('click', () => showEventDetails(date));
            elements.grid.appendChild(dayEl);
        }
    }

    // Removed ICS builder; only Google Calendar integration is supported

    function showEventDetails(date) {
        selectedDate = date;
        const dateStr = ymdLocal(date);
        const dayEvents = CALENDAR_EVENTS.filter(e => e.date === dateStr);
        
        const formattedDate = date.toLocaleDateString('default', { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });

                elements.details.innerHTML = `
                        <div class="event-date">${formattedDate}</div>
                        ${dayEvents.length ? dayEvents.map(event => `
                                <div class="event-detail-item">
                                    <div class="row">
                                        <h4>${event.title}</h4>
                                        <div class="actions">
                                            ${event.view_url ? `<a href="${event.view_url}" class="chip-btn">View Details</a>` : ''}
                                            ${!event.past && event.gcal_url ? `<a class=\"chip-btn\" target=\"_blank\" rel=\"noopener\" href=\"${event.gcal_url}\">Google</a>` : ''}
                                        </div>
                                    </div>
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

    async function loadCalendarFromAPI(){
        try{
            const res = await fetch('/api/calendar/?category=all', { headers:{'X-Requested-With':'XMLHttpRequest'} });
            const j = await res.json();
            if (Array.isArray(j.items)) CALENDAR_EVENTS = j.items;
        }catch(e){ /* leave fallback CALENDAR_EVENTS */ }
        renderCalendar();
    }

    // Initial render
    loadCalendarFromAPI();
});