document.addEventListener('DOMContentLoaded', () => {

    // --- UTILITY FUNCTIONS ---
    const getCookie = (name) => {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    };
    const CSRF_TOKEN = getCookie('csrftoken');

    const showToast = (message, type = 'success') => {
        const toast = document.getElementById('toast-notification');
        if (!toast) {
            console.error('Toast notification element not found!');
            return;
        }
        toast.textContent = message;
        toast.className = `toast show toast-${type}`;
        setTimeout(() => {
            toast.className = toast.className.replace(' show', '');
        }, 3000);
    };

    // --- API HELPER ---
    const apiRequest = async (url, options) => {
        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN,
                },
                ...options,
            });
            if (!response.ok) {
                let errorData;
                try {
                    errorData = await response.json();
                } catch (e) {
                    errorData = { error: response.statusText };
                }
                if (errorData.error && errorData.error.includes('UNIQUE constraint failed')) {
                   return { success: false, error: 'An entry with this name already exists in this academic year.' };
                }
                return { success: false, error: errorData.error || 'Request failed' };
            }
            return await response.json();
        } catch (error) {
            console.error('API Request Error:', error);
            showToast('A network error occurred.', 'error');
            return { success: false, error: 'Network error' };
        }
    };

    // --- ADD FORM LOGIC ---
    const addForm = document.getElementById('add-form-container');
    const addNewEntryBtn = document.getElementById('addNewEntryBtn');
    const addEntryConfirmBtn = document.getElementById('addEntryConfirmBtn');
    const addEntryCancelBtn = document.getElementById('addEntryCancelBtn');
    const categorySelect = document.getElementById('categorySelect');
    const associationDeptGroup = document.getElementById('association-department-group');

    const toggleAddForm = () => {
        if (!addForm) return;
        const isHidden = addForm.style.display === 'none';
        addForm.style.display = isHidden ? 'flex' : 'none';
    };

    const handleCategoryChange = () => {
        if (!categorySelect || !associationDeptGroup) return;
        associationDeptGroup.style.display = categorySelect.value === 'Association' ? 'block' : 'none';
    };

    const addNewEntry = async () => {
        const category = categorySelect.value;
        const name = document.getElementById('newEntryName').value.trim();
        if (!name) {
            showToast('Please enter a name.', 'error');
            return;
        }

        const payload = { name };
        if (category === 'Association') {
            const departmentId = document.getElementById('associationDepartmentSelect').value;
            if (!departmentId) {
                showToast('Please select a department for the association.', 'error');
                return;
            }
            payload.department_id = departmentId;
        }

        const currentYear = new URLSearchParams(window.location.search).get('year');
        if (currentYear) {
            payload.academic_year = currentYear;
        }

        const data = await apiRequest(`/core-admin/settings/${category.toLowerCase()}/add/`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        if (data.success) {
            location.reload();
        } else {
            showToast(data.error || 'Failed to add entry.', 'error');
        }
    };

    if (addNewEntryBtn) addNewEntryBtn.addEventListener('click', toggleAddForm);
    if (addEntryConfirmBtn) addEntryConfirmBtn.addEventListener('click', addNewEntry);
    if (addEntryCancelBtn) addEntryCancelBtn.addEventListener('click', toggleAddForm);
    if (categorySelect) categorySelect.addEventListener('change', handleCategoryChange);

    // --- INLINE ROW EDITING & DELETION LOGIC (using Event Delegation) ---
    const widgetGrid = document.querySelector('.widget-grid');

    const handleRowAction = (e) => {
        const target = e.target.closest('button');
        if (!target) return;

        if (target.classList.contains('btn-edit')) editRow(target);
        else if (target.classList.contains('btn-row-save')) saveRow(target);
        else if (target.classList.contains('btn-row-cancel')) cancelEdit(target);
    };

    const editRow = (button) => {
        const row = button.closest('tr');
        const currentlyEditing = document.querySelector('.editing-row');
        if (currentlyEditing && currentlyEditing !== row) {
            cancelEdit(currentlyEditing.querySelector('.btn-row-cancel'));
        }

        row.classList.add('editing-row');
        const nameCell = row.cells[0];
        const statusCell = row.cells[1];
        const actionsCell = row.cells[2];

        const originalName = nameCell.innerText.split(' (')[0];
        const originalStatus = statusCell.querySelector('.status-badge').innerText.toLowerCase();
        row.dataset.originalNameHTML = nameCell.innerHTML;
        row.dataset.originalStatus = originalStatus;

        nameCell.innerHTML = `<input type="text" class="inline-edit-input" value="${originalName}">`;
        statusCell.innerHTML = `<select class="inline-edit-select"><option value="active">Active</option><option value="inactive">Inactive</option></select>`;
        statusCell.querySelector('select').value = originalStatus;
        
        actionsCell.innerHTML = `
            <button class="btn btn-row-save"><i class="fas fa-check"></i></button>
            <button class="btn btn-row-cancel"><i class="fas fa-times"></i></button>
        `;
    };

    const saveRow = async (button) => {
        const row = button.closest('tr');
        const model = row.closest('.data-widget').dataset.widgetName.toLowerCase();
        const id = row.dataset.id;
        
        const nameInput = row.querySelector('.inline-edit-input');
        const statusSelect = row.querySelector('.inline-edit-select');
        const newName = nameInput.value.trim();
        const newStatus = statusSelect.value === 'active';

        if (!newName) {
            showToast('Name cannot be empty.', 'error');
            return;
        }

        const data = await apiRequest(`/core-admin/settings/${model}/${id}/edit/`, {
            method: 'POST',
            body: JSON.stringify({ name: newName, is_active: newStatus })
        });

        if(data.success) {
            const nameCell = row.cells[0];
            const statusCell = row.cells[1];
            const actionsCell = row.cells[2];

            if (model === 'association' && data.department_name) {
                 nameCell.innerHTML = `${data.name} (${data.department_name})`;
            } else {
                 nameCell.innerHTML = data.name || newName;
            }
            
            statusCell.innerHTML = `<span class="status-badge status-${newStatus ? 'active' : 'inactive'}">${newStatus ? 'Active' : 'Inactive'}</span>`;
            actionsCell.innerHTML = `<button class="btn btn-edit"><i class="fas fa-pen"></i></button>`;
            row.className = newStatus ? '' : 'inactive-row-display';
            row.classList.remove('editing-row');
            showToast('Changes saved!', 'success');
        } else {
            showToast(data.error || 'Failed to save changes.', 'error');
            cancelEdit(button);
        }
    };

    const cancelEdit = (button) => {
        const row = button.closest('tr');
        row.classList.remove('editing-row');
        const originalNameHTML = row.dataset.originalNameHTML;
        const originalStatus = row.dataset.originalStatus;

        row.cells[0].innerHTML = originalNameHTML;
        row.cells[1].innerHTML = `<span class="status-badge status-${originalStatus}">${originalStatus.charAt(0).toUpperCase() + originalStatus.slice(1)}</span>`;
        row.cells[2].innerHTML = `<button class="btn btn-edit"><i class="fas fa-pen"></i></button>`;
        row.className = originalStatus === 'inactive' ? 'inactive-row-display' : '';
    };

    if(widgetGrid) widgetGrid.addEventListener('click', handleRowAction);
    
    // --- UNIVERSAL SEARCH LOGIC ---
    const universalSearch = document.getElementById('universalSearch');
    const notFoundMessage = document.getElementById('search-not-found');
    const notFoundText = notFoundMessage ? notFoundMessage.querySelector('strong') : null;
    
    const filterAllData = () => {
        const searchTerm = universalSearch.value.toLowerCase();
        const allWidgets = document.querySelectorAll('.data-widget');
        let totalMatches = 0;

        allWidgets.forEach(widget => {
            const rows = widget.querySelectorAll('.data-table tbody tr');
            let widgetHasMatch = false;

            rows.forEach(row => {
                const nameCell = row.cells[0];
                if (nameCell && nameCell.innerText.toLowerCase().includes(searchTerm)) {
                    row.style.display = '';
                    widgetHasMatch = true;
                    totalMatches++;
                } else {
                    row.style.display = 'none';
                }
            });
            widget.style.display = widgetHasMatch || searchTerm === '' ? 'flex' : 'none';
        });

        if (notFoundMessage && totalMatches === 0 && searchTerm !== '') {
            notFoundMessage.style.display = 'block';
            notFoundText.textContent = searchTerm;
        } else if (notFoundMessage) {
            notFoundMessage.style.display = 'none';
        }
    };
    if (universalSearch) universalSearch.addEventListener('keyup', filterAllData);

    const addFromSearchBtn = document.getElementById('addFromSearchBtn');
    if (addFromSearchBtn) {
        addFromSearchBtn.addEventListener('click', () => {
            const searchTerm = universalSearch.value;
            toggleAddForm();
            document.getElementById('newEntryName').value = searchTerm;
            if (notFoundMessage) notFoundMessage.style.display = 'none';
        });
    }

});
