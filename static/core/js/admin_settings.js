// CSRF helper for Django
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        let cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            let cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// ADD logic for all models
document.querySelectorAll('.add-btn').forEach(btn => {
    btn.onclick = function() {
        const model = btn.dataset.model;
        let nameField = document.getElementById('new-' + model + '-name');
        let name = nameField.value.trim();
        if (!name) return alert('Enter a name');
        let data = new FormData();
        data.append('name', name);

        if (model === 'association') {
            let dept = document.getElementById('new-association-dept').value;
            data.append('department', dept);
        }

        fetch(`/core-admin/settings/${model}/add/`, {
            method: 'POST',
            headers: {'X-CSRFToken': getCookie('csrftoken')},
            body: data
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) location.reload();
            else alert(result.error || "Failed");
        });
    };
});

// DELETE logic
document.querySelectorAll('.delete-btn').forEach(btn => {
    btn.onclick = function() {
        if (!confirm("Are you sure you want to delete this?")) return;
        const model = btn.dataset.model;
        const id = btn.dataset.id;
        fetch(`/core-admin/settings/${model}/${id}/delete/`, {
            method: 'POST',
            headers: {'X-CSRFToken': getCookie('csrftoken')},
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) location.reload();
            else alert(result.error || "Delete failed");
        });
    };
});

// EDIT logic (prompt-based)
document.querySelectorAll('.edit-btn').forEach(btn => {
    btn.onclick = function() {
        const model = btn.dataset.model;
        const id = btn.dataset.id;
        let currentName = btn.parentNode.parentNode.querySelector('td').textContent.trim();

        let newName = prompt("Edit name:", currentName);
        if (!newName || newName === currentName) return;

        let data = new FormData();
        data.append('name', newName);

        if (model === 'association') {
            let deptId = '';
            try {
                deptId = prompt("Enter Department ID (leave blank for no department):", "");
            } catch { deptId = ''; }
            data.append('department', deptId);
        }

        fetch(`/core-admin/settings/${model}/${id}/edit/`, {
            method: 'POST',
            headers: {'X-CSRFToken': getCookie('csrftoken')},
            body: data
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) location.reload();
            else alert(result.error || "Edit failed");
        });
    };
});

// DataTable Initialization (robust, no warning, no popup)
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.datatable').forEach(table => {
        try {
            // Try to initialize. If already initialized, DataTables v2+ will throw and we'll silently ignore.
            new DataTable(table, {
                paging: false,
                info: false,
                searching: true,
                language: { search: "🔍 " }
            });
        } catch (e) {
            if (String(e).includes('Cannot reinitialise DataTable')) {
                // Silently ignore this specific error!
            } else {
                // For any other error, re-throw (helps debugging unexpected bugs)
                throw e;
            }
        }
    });
});
