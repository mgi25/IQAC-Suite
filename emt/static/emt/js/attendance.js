document.addEventListener('DOMContentLoaded', function () {
    let rows = Array.isArray(initialRows) ? initialRows : [];
    const perPage = 100;
    let currentPage = 1;
    let activeCategory = 'student';

    const summaryEl = document.getElementById('summary');
    const actionsEl = document.getElementById('actions');
    const categoryNav = document.getElementById('attendance-category-nav');
    const categoryButtons = categoryNav ? Array.from(categoryNav.querySelectorAll('[data-category]')) : [];
    const tableSection = document.getElementById('attendance-table-section');
    const tableBody = tableSection ? tableSection.querySelector('tbody') : null;
    const volunteerHeader = document.getElementById('attendance-volunteer-header');
    const totalEl = document.getElementById('total-count');
    const presentEl = document.getElementById('present-count');
    const absentEl = document.getElementById('absent-count');
    const volunteerEl = document.getElementById('volunteer-count');
    const loadingEl = document.getElementById('loading');

    const categoryDisplayLabels = {
        student: 'Students',
        faculty: 'Faculty',
        external: 'Guests'
    };

    const categoryVolunteerLabels = {
        student: 'Student Volunteer',
        faculty: 'Volunteer',
        external: 'Volunteer'
    };

    const pagination = document.createElement('div');
    pagination.className = 'attendance-pagination d-none';
    const prevBtn = document.createElement('button');
    prevBtn.type = 'button';
    prevBtn.className = 'btn btn-outline-secondary btn-sm';
    prevBtn.textContent = 'Prev';
    const nextBtn = document.createElement('button');
    nextBtn.type = 'button';
    nextBtn.className = 'btn btn-outline-secondary btn-sm';
    nextBtn.textContent = 'Next';
    const pageLabel = document.createElement('span');
    pageLabel.className = 'text-muted align-self-center';

    pagination.appendChild(prevBtn);
    pagination.appendChild(pageLabel);
    pagination.appendChild(nextBtn);
    if (actionsEl && actionsEl.parentNode) {
        actionsEl.parentNode.insertBefore(pagination, actionsEl);
    }

    function normaliseRows() {
        rows.forEach((row, index) => {
            row._index = index;
            const rawCategory = row.category ? String(row.category).toLowerCase() : '';
            if (['student', 'faculty', 'external'].includes(rawCategory)) {
                row.category = rawCategory;
            } else if (['guest', 'guests'].includes(rawCategory)) {
                row.category = 'external';
            } else {
                const hasClass = row.student_class && row.student_class.trim();
                row.category = hasClass ? 'student' : 'external';
            }
            if (!row.affiliation) {
                if (row.category === 'student') {
                    row.affiliation = row.student_class || 'Unknown';
                } else if (row.category === 'faculty') {
                    row.affiliation = row.student_class || 'Unknown';
                } else {
                    row.affiliation = row.student_class || 'Guests';
                }
            }
            if (row.category === 'faculty' && (!row.student_class || !row.student_class.trim())) {
                row.student_class = row.affiliation;
            }
        });
    }

    function updateSummaryVisibility() {
        const hasRows = rows.length > 0;
        summaryEl.classList.toggle('d-none', !hasRows);
        actionsEl.classList.toggle('d-none', !hasRows);
    }

    function updateCounts() {
        const total = rows.length;
        const absent = rows.filter(r => r.absent).length;
        const volunteers = rows.filter(r => r.volunteer).length;
        const present = total - absent;
        totalEl.textContent = total;
        presentEl.textContent = present;
        absentEl.textContent = absent;
        volunteerEl.textContent = volunteers;
    }

    function getPageSlice() {
        const start = (currentPage - 1) * perPage;
        return rows.slice(start, start + perPage);
    }

    function updatePaginationControls(messages = []) {
        if (rows.length === 0) {
            pageLabel.textContent = 'No records';
            prevBtn.disabled = true;
            nextBtn.disabled = true;
            pagination.classList.add('d-none');
            return;
        }

        const totalPages = Math.ceil(rows.length / perPage);
        if (currentPage > totalPages) {
            currentPage = totalPages;
        }
        let label = `Page ${currentPage} of ${totalPages}`;
        if (messages && messages.length > 0) {
            label += ` – ${messages.join(' ')}`;
        }
        pageLabel.textContent = label;
        prevBtn.disabled = currentPage === 1;
        nextBtn.disabled = currentPage >= totalPages;
        pagination.classList.toggle('d-none', rows.length <= perPage);
    }

    function appendRow(tableBody, row, affiliationText) {
        if (!tableBody) {
            return;
        }
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${row.registration_no || ''}</td>
            <td>${row.full_name || ''}</td>
            <td>${affiliationText || ''}</td>
            <td><input type="checkbox" data-index="${row._index}" class="absent" ${row.absent ? 'checked' : ''}></td>
            <td><input type="checkbox" data-index="${row._index}" class="volunteer" ${row.volunteer ? 'checked' : ''}></td>
        `;
        tableBody.appendChild(tr);
    }

    function renderPlaceholderRow(tableBody, message) {
        if (!tableBody) {
            return;
        }
        const table = tableBody.closest('table');
        const columnCount = table ? table.querySelectorAll('thead th').length || 5 : 5;
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = columnCount;
        td.className = 'text-muted text-center';
        td.textContent = message;
        tr.appendChild(td);
        tableBody.appendChild(tr);
    }

    function updateActiveCategoryButtons(visibleButtons) {
        if (!categoryButtons || categoryButtons.length === 0) {
            return;
        }
        const candidates = visibleButtons && visibleButtons.length > 0
            ? visibleButtons
            : categoryButtons.filter(button => {
                const navItem = button.closest('.nav-item') || button.parentElement;
                return !navItem || !navItem.classList.contains('d-none');
            });
        if (candidates.length > 0 && !candidates.some(button => button.dataset.category === activeCategory)) {
            activeCategory = candidates[0].dataset.category;
        }
        categoryButtons.forEach(button => {
            const navItem = button.closest('.nav-item') || button.parentElement;
            const isHidden = navItem ? navItem.classList.contains('d-none') : false;
            const isActive = !isHidden && button.dataset.category === activeCategory;
            button.classList.toggle('active', isActive);
            if (isActive) {
                button.setAttribute('aria-current', 'page');
                button.setAttribute('aria-selected', 'true');
            } else {
                button.removeAttribute('aria-current');
                button.setAttribute('aria-selected', 'false');
            }
        });
    }

    function renderTables() {
        if (!tableBody || !tableSection) {
            return;
        }

        normaliseRows();
        tableBody.innerHTML = '';

        if (rows.length === 0) {
            if (categoryNav) {
                categoryNav.classList.add('d-none');
            }
            tableSection.classList.add('d-none');
            updateActiveCategoryButtons([]);
            updateSummaryVisibility();
            updateCounts();
            updatePaginationControls();
            return;
        }

        const categoryAvailability = {};
        const availableButtons = [];

        if (categoryButtons.length > 0) {
            categoryButtons.forEach(button => {
                const category = button.dataset.category;
                const hasData = rows.some(row => (row.category || 'student') === category);
                categoryAvailability[category] = hasData;
                const navItem = button.closest('.nav-item') || button.parentElement;
                if (navItem) {
                    navItem.classList.toggle('d-none', !hasData);
                }
                if (hasData) {
                    availableButtons.push(button);
                }
            });
            updateActiveCategoryButtons(availableButtons);
            if (categoryNav) {
                categoryNav.classList.toggle('d-none', availableButtons.length === 0);
            }
        }

        const activeButton = categoryButtons.find(button => button.classList.contains('active')) || null;
        const currentCategory = activeButton ? activeButton.dataset.category : activeCategory;
        activeCategory = currentCategory;

        const displayLabel = activeButton
            ? (activeButton.dataset.label || activeButton.textContent.trim())
            : (categoryDisplayLabels[currentCategory] || 'Attendees');
        const lowerLabel = displayLabel.toLowerCase();
        const volunteerLabel = activeButton
            ? (activeButton.dataset.volunteerLabel || categoryVolunteerLabels[currentCategory] || 'Volunteer')
            : (categoryVolunteerLabels[currentCategory] || 'Volunteer');
        if (volunteerHeader) {
            volunteerHeader.textContent = volunteerLabel;
        }

        const slice = getPageSlice();
        const activeSlice = slice.filter(row => (row.category || 'student') === currentCategory);
        const hasCategory = Object.prototype.hasOwnProperty.call(categoryAvailability, currentCategory)
            ? categoryAvailability[currentCategory]
            : rows.some(row => (row.category || 'student') === currentCategory);

        const paginationMessages = [];

        if (activeSlice.length > 0) {
            activeSlice.forEach(row => {
                const affiliationText = currentCategory === 'external'
                    ? `${row.affiliation || 'Guests'} (Guest)`
                    : row.affiliation || '';
                appendRow(tableBody, row, affiliationText);
            });
        } else if (hasCategory) {
            renderPlaceholderRow(tableBody, `No ${lowerLabel} on this page. Use pagination controls to view additional ${lowerLabel}.`);
            paginationMessages.push(`${displayLabel} appear on other pages.`);
        } else {
            renderPlaceholderRow(tableBody, `No attendance records found for ${lowerLabel}.`);
        }

        tableSection.classList.remove('d-none');

        updateSummaryVisibility();
        updateCounts();
        updatePaginationControls(paginationMessages);
    }

    function handleTableChange(e) {
        const idx = parseInt(e.target.getAttribute('data-index'), 10);
        if (Number.isNaN(idx) || !rows[idx]) {
            return;
        }
        if (e.target.classList.contains('absent')) {
            rows[idx].absent = e.target.checked;
        }
        if (e.target.classList.contains('volunteer')) {
            rows[idx].volunteer = e.target.checked;
        }
        updateCounts();
    }

    if (tableBody) {
        tableBody.addEventListener('change', handleTableChange);
    }

    if (categoryButtons.length > 0) {
        categoryButtons.forEach(button => {
            button.addEventListener('click', function (event) {
                event.preventDefault();
                const navItem = button.closest('.nav-item');
                if (navItem && navItem.classList.contains('d-none')) {
                    return;
                }
                const category = button.dataset.category;
                if (!category || category === activeCategory) {
                    return;
                }
                activeCategory = category;
                renderTables();
            });
        });
    }

    document.getElementById('save-event-report').addEventListener('click', function () {
        fetch(saveUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
            body: JSON.stringify({ rows: rows })
        })
        .then(r => r.json())
        .then(() => {
            window.location.href = reportUrl;
        })
        .catch(() => alert('Failed to save attendance.'));
    });

    // Allow the top "Upload" button to save when no CSV is selected.
    // Many users click Upload expecting it to persist the current marks.
    const uploadForm = document.querySelector('.attendance-container form');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function (e) {
            const fileInput = uploadForm.querySelector('input[type="file"][name="csv_file"]');
            const hasFile = fileInput && fileInput.files && fileInput.files.length > 0;
            if (!hasFile) {
                e.preventDefault();
                if (!rows || rows.length === 0) {
                    alert('No rows to save.');
                    return;
                }
                fetch(saveUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
                    body: JSON.stringify({ rows: rows })
                })
                .then(r => r.json())
                .then(() => {
                    window.location.href = reportUrl;
                })
                .catch(() => alert('Failed to save attendance.'));
            }
        });
    }

    document.getElementById('download-csv').addEventListener('click', function () {
        fetch(downloadUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
            body: JSON.stringify({ rows: rows })
        }).then(r => r.blob()).then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = downloadFilename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
        });
    });

    function setupPagination() {
        prevBtn.addEventListener('click', function () {
            if (currentPage > 1) {
                currentPage -= 1;
                renderTables();
            }
        });
        nextBtn.addEventListener('click', function () {
            if (currentPage * perPage < rows.length) {
                currentPage += 1;
                renderTables();
            }
        });
    }

    function fetchRows() {
        if (!dataUrl) {
            renderTables();
            return;
        }
        loadingEl.style.display = 'block';
        fetch(dataUrl)
            .then(r => r.json())
            .then(data => {
                rows = Array.isArray(data.rows) ? data.rows : [];
                currentPage = 1;
                renderTables();
            })
            .finally(() => {
                loadingEl.style.display = 'none';
            });
    }

    setupPagination();
    if (rows.length === 0) {
        fetchRows();
    } else {
        renderTables();
    }
});
