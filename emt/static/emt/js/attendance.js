document.addEventListener('DOMContentLoaded', function () {
    let rows = initialRows || [];
    const perPage = 100;
    let currentPage = 1;

    const tableBody = document.querySelector('#attendance-table tbody');
    const totalEl = document.getElementById('total-count');
    const presentEl = document.getElementById('present-count');
    const absentEl = document.getElementById('absent-count');
    const volunteerEl = document.getElementById('volunteer-count');
    const loadingEl = document.getElementById('loading');

    function renderTable() {
        tableBody.innerHTML = '';
        const start = (currentPage - 1) * perPage;
        const slice = rows.slice(start, start + perPage);
        slice.forEach((row, idx) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${row.registration_no}</td>
                <td>${row.full_name}</td>
                <td>${row.student_class}</td>
                <td><input type="checkbox" data-index="${start + idx}" class="absent" ${row.absent ? 'checked' : ''}></td>
                <td><input type="checkbox" data-index="${start + idx}" class="volunteer" ${row.volunteer ? 'checked' : ''}></td>
            `;
            tableBody.appendChild(tr);
        });
        updateCounts();
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

    tableBody.addEventListener('change', function (e) {
        const idx = parseInt(e.target.getAttribute('data-index'));
        if (isNaN(idx)) return;
        if (e.target.classList.contains('absent')) {
            rows[idx].absent = e.target.checked;
        }
        if (e.target.classList.contains('volunteer')) {
            rows[idx].volunteer = e.target.checked;
        }
        updateCounts();
    });

    document.getElementById('save-event-report').addEventListener('click', function () {
        fetch(saveUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
            body: JSON.stringify({ rows: rows })
        }).then(r => r.json()).then(() => {
            alert('Saved');
        });
    });

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
        const pagination = document.createElement('div');
        pagination.className = 'pagination';
        const prev = document.createElement('button');
        prev.textContent = 'Prev';
        const next = document.createElement('button');
        next.textContent = 'Next';
        pagination.appendChild(prev);
        pagination.appendChild(next);
        document.body.appendChild(pagination);

        prev.addEventListener('click', function () {
            if (currentPage > 1) {
                currentPage -= 1;
                renderTable();
            }
        });
        next.addEventListener('click', function () {
            if (currentPage * perPage < rows.length) {
                currentPage += 1;
                renderTable();
            }
        });
    }

    function fetchRows() {
        if (!dataUrl) {
            renderTable();
            return;
        }
        loadingEl.style.display = 'block';
        fetch(dataUrl)
            .then(r => r.json())
            .then(data => {
                rows = data.rows || [];
                renderTable();
            })
            .finally(() => {
                loadingEl.style.display = 'none';
            });
    }

    setupPagination();
    if (rows.length === 0) {
        fetchRows();
    } else {
        renderTable();
    }
});
