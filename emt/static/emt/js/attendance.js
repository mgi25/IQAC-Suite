document.addEventListener('DOMContentLoaded', function () {
    let rows = Array.isArray(initialRows) ? initialRows : [];
    const perPage = 100;
    let activeCategory = 'student';
    let hasInitialRender = false;

    const categoryPages = {};
    let paginationState = {
        currentPage: 1,
        totalPages: 1,
        totalCount: 0,
        displayLabel: 'Attendees',
    };

    const summaryEl = document.getElementById('summary');
    const actionsEl = document.getElementById('actions');
    const categoryNav = document.getElementById('attendance-category-nav');
    const categoryButtons = categoryNav ? Array.from(categoryNav.querySelectorAll('[data-category]')) : [];
    const tableSection = document.getElementById('attendance-table-section');
    const tableBody = tableSection ? tableSection.querySelector('tbody') : null;
    const volunteerHeader = document.getElementById('attendance-volunteer-header');
    const identifierHeader = document.getElementById('attendance-identifier-header');
    const totalEl = document.getElementById('total-count');
    const presentEl = document.getElementById('present-count');
    const absentEl = document.getElementById('absent-count');
    const volunteerEl = document.getElementById('volunteer-count');
    const loadingEl = document.getElementById('loading');

    const categoryDisplayLabels = {
        student: 'Students',
        faculty: 'Faculty',
    };

    const categoryVolunteerLabels = {
        student: 'Student Volunteer',
        faculty: 'Volunteer',
    };

    const categoryIdentifierLabels = {
        student: 'Registration No',
        faculty: 'Emp ID',
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

    function isRowVisibleInCategory(row, category) {
        const rowCategory = (row.category || 'student').toLowerCase();
        if (category === 'student') {
            return rowCategory === 'student' || rowCategory === 'external';
        }
        return rowCategory === category;
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
        const absent = rows.filter((r) => r.absent).length;
        const volunteers = rows.filter((r) => r.volunteer).length;
        const present = total - absent;
        totalEl.textContent = total;
        presentEl.textContent = present;
        absentEl.textContent = absent;
        volunteerEl.textContent = volunteers;
    }

    function updatePaginationControls() {
        const { totalCount, totalPages, currentPage } = paginationState;
        if (totalCount === 0) {
            pageLabel.textContent = 'No records';
            prevBtn.disabled = true;
            nextBtn.disabled = true;
            pagination.classList.add('d-none');
            return;
        }

        pageLabel.textContent = `Page ${currentPage} of ${totalPages} · ${totalCount} total`;
        prevBtn.disabled = currentPage <= 1;
        nextBtn.disabled = currentPage >= totalPages;
        pagination.classList.toggle('d-none', totalPages <= 1);
    }

    function appendRow(targetBody, row, affiliationText) {
        if (!targetBody) {
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
        targetBody.appendChild(tr);
    }

    function renderPlaceholderRow(targetBody, message) {
        if (!targetBody) {
            return;
        }
        const table = targetBody.closest('table');
        const columnCount = table ? table.querySelectorAll('thead th').length || 5 : 5;
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = columnCount;
        td.className = 'text-muted text-center';
        td.textContent = message;
        tr.appendChild(td);
        targetBody.appendChild(tr);
    }

    function updateActiveCategoryButtons() {
        if (!categoryButtons || categoryButtons.length === 0) {
            return;
        }
        categoryButtons.forEach((button) => {
            const isActive = rows.length > 0 && button.dataset.category === activeCategory;
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
            paginationState = {
                currentPage: 1,
                totalPages: 1,
                totalCount: 0,
                displayLabel: categoryDisplayLabels[activeCategory] || 'Attendees',
            };
            updateActiveCategoryButtons();
            updateSummaryVisibility();
            updateCounts();
            updatePaginationControls();
            return;
        }

        const categoryAvailability = {};
        const availableButtons = [];

        if (categoryButtons.length > 0) {
            categoryButtons.forEach((button) => {
                const category = button.dataset.category;
                const hasData = rows.some((row) => isRowVisibleInCategory(row, category));
                categoryAvailability[category] = hasData;
                if (hasData) {
                    availableButtons.push(button);
                    button.removeAttribute('title');
                    button.classList.remove('no-data');
                } else {
                    button.classList.add('no-data');
                    button.setAttribute('title', 'No attendance records yet for this category');
                }
            });

            if (
                !hasInitialRender &&
                availableButtons.length > 0 &&
                !availableButtons.some((button) => button.dataset.category === activeCategory)
            ) {
                activeCategory = availableButtons[0].dataset.category;
            }
            updateActiveCategoryButtons();
            if (categoryNav) {
                categoryNav.classList.remove('d-none');
            }
        }

        const activeButton = categoryButtons.find((button) => button.classList.contains('active')) || null;
        const currentCategory = activeButton ? activeButton.dataset.category : activeCategory;
        activeCategory = currentCategory;

        const displayLabel = activeButton
            ? activeButton.dataset.label || activeButton.textContent.trim()
            : categoryDisplayLabels[currentCategory] || 'Attendees';
        const volunteerLabel = activeButton
            ? activeButton.dataset.volunteerLabel || categoryVolunteerLabels[currentCategory] || 'Volunteer'
            : categoryVolunteerLabels[currentCategory] || 'Volunteer';
        const identifierLabel = categoryIdentifierLabels[currentCategory] || 'Registration No';
        const lowerLabel = displayLabel.toLowerCase();

        if (volunteerHeader) {
            volunteerHeader.textContent = volunteerLabel;
        }
        if (identifierHeader) {
            identifierHeader.textContent = identifierLabel;
        }

        const viewRows = rows.filter((row) => isRowVisibleInCategory(row, currentCategory));
        const totalForCategory = viewRows.length;

        if (!Object.prototype.hasOwnProperty.call(categoryPages, currentCategory)) {
            categoryPages[currentCategory] = 1;
        }
        let page = categoryPages[currentCategory];
        const totalPages = totalForCategory ? Math.ceil(totalForCategory / perPage) : 1;
        if (page > totalPages) {
            page = totalPages;
        }
        if (page < 1) {
            page = 1;
        }
        categoryPages[currentCategory] = page;

        const start = (page - 1) * perPage;
        const pageRows = viewRows.slice(start, start + perPage);

        if (pageRows.length > 0) {
            pageRows.forEach((row) => {
                const rowCategory = (row.category || 'student').toLowerCase();
                const affiliationText = rowCategory === 'external'
                    ? `${row.affiliation || 'Guests'} (Guest)`
                    : row.affiliation || '';
                appendRow(tableBody, row, affiliationText);
            });
        } else if (totalForCategory === 0) {
            renderPlaceholderRow(tableBody, `No ${lowerLabel} attendance records found.`);
        } else {
            renderPlaceholderRow(
                tableBody,
                `No ${lowerLabel} on this page. Use pagination controls to view additional ${lowerLabel}.`,
            );
        }

        tableSection.classList.remove('d-none');

        updateSummaryVisibility();
        updateCounts();

        paginationState = {
            currentPage: page,
            totalPages,
            totalCount: totalForCategory,
            displayLabel,
        };
        updatePaginationControls();

        hasInitialRender = true;
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
        categoryButtons.forEach((button) => {
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
                categoryPages[category] = 1;
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
        .then((r) => r.json())
        .then(() => {
            window.location.href = reportUrl;
        })
        .catch(() => alert('Failed to save attendance.'));
    });

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
                .then((r) => r.json())
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
        }).then((r) => r.blob()).then((blob) => {
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
            const category = activeCategory;
            const currentPage = categoryPages[category] || 1;
            if (currentPage > 1) {
                categoryPages[category] = currentPage - 1;
                renderTables();
            }
        });
        nextBtn.addEventListener('click', function () {
            const category = activeCategory;
            const currentPage = categoryPages[category] || 1;
            if (currentPage < paginationState.totalPages) {
                categoryPages[category] = currentPage + 1;
                renderTables();
            }
        });
    }

    function resetCategoryPages() {
        ['student', 'faculty', 'external'].forEach((cat) => {
            categoryPages[cat] = 1;
        });
    }

    function fetchRows() {
        if (!dataUrl) {
            renderTables();
            return;
        }
        loadingEl.style.display = 'block';
        fetch(dataUrl)
            .then((r) => r.json())
            .then((data) => {
                rows = Array.isArray(data.rows) ? data.rows : [];
                resetCategoryPages();
                activeCategory = 'student';
                hasInitialRender = false;
                paginationState = {
                    currentPage: 1,
                    totalPages: 1,
                    totalCount: 0,
                    displayLabel: categoryDisplayLabels.student,
                };
                renderTables();
            })
            .finally(() => {
                loadingEl.style.display = 'none';
            });
    }

    setupPagination();
    resetCategoryPages();
    if (rows.length === 0) {
        fetchRows();
    } else {
        renderTables();
    }
});
