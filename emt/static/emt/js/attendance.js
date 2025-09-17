document.addEventListener('DOMContentLoaded', function () {
    let rows = initialRows || [];
    const perPage = 100;
    let currentPage = 1;

    const summaryEl = document.getElementById('summary');
    const actionsEl = document.getElementById('actions');
    const studentSection = document.getElementById('student-table-section');
    const facultySection = document.getElementById('faculty-table-section');
    const guestSection = document.getElementById('guest-table-section');
    const studentTableBody = document.querySelector('#student-attendance-table tbody');
    const facultyTableBody = document.querySelector('#faculty-attendance-table tbody');
    const guestTableBody = document.querySelector('#guest-attendance-table tbody');
    const totalEl = document.getElementById('total-count');
    const presentEl = document.getElementById('present-count');
    const absentEl = document.getElementById('absent-count');
    const volunteerEl = document.getElementById('volunteer-count');
    const loadingEl = document.getElementById('loading');

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
            if (!row.category) {
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

    function updatePaginationControls() {
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
        pageLabel.textContent = `Page ${currentPage} of ${totalPages}`;
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

    function renderTables() {
        normaliseRows();
        studentTableBody.innerHTML = '';
        facultyTableBody.innerHTML = '';
        if (guestTableBody) {
            guestTableBody.innerHTML = '';
        }

        const slice = getPageSlice();
        const studentSlice = slice.filter(row => (row.category || 'student') === 'student');
        const facultySlice = slice.filter(row => (row.category || 'student') === 'faculty');
        const guestSlice = guestTableBody
            ? slice.filter(row => (row.category || 'student') === 'external')
            : [];

        studentSlice.forEach(row => {
            appendRow(studentTableBody, row, row.affiliation || '');
        });

        facultySlice.forEach(row => {
            appendRow(facultyTableBody, row, row.affiliation || '');
        });

        if (guestTableBody) {
            guestSlice.forEach(row => {
                const affiliationText = `${row.affiliation || 'Guests'} (Guest)`;
                appendRow(guestTableBody, row, affiliationText);
            });
        }

        studentSection.classList.toggle('d-none', studentSlice.length === 0);
        facultySection.classList.toggle('d-none', facultySlice.length === 0);
        if (guestSection) {
            guestSection.classList.toggle('d-none', guestSlice.length === 0);
        }

        updateSummaryVisibility();
        updateCounts();
        updatePaginationControls();
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

    studentTableBody.addEventListener('change', handleTableChange);
    facultyTableBody.addEventListener('change', handleTableChange);
    if (guestTableBody) {
        guestTableBody.addEventListener('change', handleTableChange);
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
                rows = data.rows || [];
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
