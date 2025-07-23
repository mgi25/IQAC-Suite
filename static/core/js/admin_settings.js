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

    // Make sure your Django view passes this!
    const orgsByType = window.orgsByType || JSON.parse('{{ orgs_by_type_json|safe }}');

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

    // --- ADD NEW ENTRY FORM LOGIC ---
    const addForm = document.getElementById('add-form-container');
    const addNewEntryBtn = document.getElementById('addNewEntryBtn');
    const addEntryConfirmBtn = document.getElementById('addEntryConfirmBtn');
    const addEntryCancelBtn = document.getElementById('addEntryCancelBtn');
    const categorySelect = document.getElementById('categorySelect');
    const parentOrgGroup = document.getElementById('parent-organization-group');
    const parentOrgSelect = document.getElementById('parentOrganizationSelect');

    // Dynamic parent select logic
    function handleCategoryChange() {
        if (!categorySelect || !parentOrgGroup) return;
        const selectedOption = categorySelect.options[categorySelect.selectedIndex];
        const canHaveParent = selectedOption.getAttribute('data-can-have-parent') === 'true';
        const parentType = selectedOption.getAttribute('data-parent-type');
        parentOrgGroup.style.display = canHaveParent ? 'block' : 'none';

        // Fill the parentOrgSelect dropdown
        parentOrgSelect.innerHTML = `<option value="" disabled selected>Select Parent</option>`;
        if (canHaveParent && parentType && orgsByType[parentType]) {
            orgsByType[parentType].forEach(org => {
                parentOrgSelect.innerHTML += `<option value="${org.id}">${org.name}</option>`;
            });
        }
    }

    if (categorySelect) {
        categorySelect.addEventListener('change', handleCategoryChange);
        handleCategoryChange(); // on page load
    }

    // Show add form and hide category form
    if (addNewEntryBtn) addNewEntryBtn.addEventListener('click', () => {
        addForm.style.display = 'block';
        document.getElementById("add-category-container").style.display = 'none';
        handleCategoryChange(); // Refresh parent select in case the default changed
    });

    if (addEntryCancelBtn) addEntryCancelBtn.addEventListener('click', () => {
        addForm.style.display = 'none';
        document.getElementById('newEntryName').value = '';
        if (parentOrgSelect) parentOrgSelect.value = '';
        parentOrgSelect.innerHTML = `<option value="" disabled selected>Select Parent</option>`;
    });

    if (addEntryConfirmBtn) addEntryConfirmBtn.addEventListener('click', async () => {
        const name = document.getElementById('newEntryName').value.trim();
        const selectedOption = categorySelect.options[categorySelect.selectedIndex];
        const category = categorySelect.value;
        const canHaveParent = selectedOption.getAttribute('data-can-have-parent') === 'true';
        let parent = null;
        if (canHaveParent) {
            parent = parentOrgSelect.value;
            if (!parent) {
                showToast('Please select the parent organization.', 'error');
                return;
            }
        }
        if (!name) {
            showToast('Please enter a name.', 'error');
            return;
        }
        let postData = { name: name, org_type: category };
        if (parent) postData.parent = parent;

        // Optional: attach academic year if needed in payload
        const currentYear = new URLSearchParams(window.location.search).get('year');
        if (currentYear) postData.academic_year = currentYear;

        const data = await apiRequest("/core-admin/settings/organization/add/", {
            method: "POST",
            body: JSON.stringify(postData)
        });
        if (data.success) {
            window.location.reload();
        } else {
            showToast(data.error || "Failed to add entry.", "error");
        }
    });

    // --- ADD NEW CATEGORY FORM LOGIC (WITH PARENT) ---
    const addNewCategoryBtn = document.getElementById('addNewCategoryBtn');
    const addCategoryConfirmBtn = document.getElementById('addCategoryConfirmBtn');
    const addCategoryCancelBtn = document.getElementById('addCategoryCancelBtn');
    const addCategoryContainer = document.getElementById('add-category-container');
    const hasParentCheckbox = document.getElementById('hasParentCategory');
    const parentCategoryGroup = document.getElementById('parentCategoryGroup');
    const parentCategorySelect = document.getElementById('parentCategorySelect');

    // Toggle parent category dropdown
    hasParentCheckbox.addEventListener('change', function() {
        parentCategoryGroup.style.display = this.checked ? 'block' : 'none';
        if (!this.checked) {
            parentCategorySelect.value = '';
        }
    });

    // Show category form, hide entry form
    addNewCategoryBtn.addEventListener('click', () => {
        addCategoryContainer.style.display = 'block';
        if (addForm) addForm.style.display = 'none';
    });

    addCategoryCancelBtn.addEventListener('click', () => {
        addCategoryContainer.style.display = 'none';
        document.getElementById('newCategoryName').value = '';
        hasParentCheckbox.checked = false;
        parentCategoryGroup.style.display = 'none';
        parentCategorySelect.value = '';
    });

    addCategoryConfirmBtn.addEventListener('click', async () => {
        const name = document.getElementById('newCategoryName').value.trim();
        let parent = null;
        if (hasParentCheckbox.checked) {
            parent = parentCategorySelect.value;
            if (!parent) {
                showToast('Please select a parent category.', 'error');
                return;
            }
        }
        if (!name) {
            showToast('Enter a category name.', 'error');
            return;
        }
        let payload = { name: name };
        if (parent) payload.parent = parent;

        const data = await apiRequest("/core-admin/settings/organization_type/add/", {
            method: "POST",
            body: JSON.stringify(payload)
        });
        if (data.success) {
            window.location.reload();
        } else {
            showToast(data.error || "Failed to add category.", "error");
        }
    });

    // Hide category form if Add New Entry is clicked
    if (addNewEntryBtn) addNewEntryBtn.addEventListener('click', () => {
        if (addForm) addForm.style.display = 'block';
        if (addCategoryContainer) addCategoryContainer.style.display = 'none';
        handleCategoryChange();
    });

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
            addForm.style.display = 'block';
            document.getElementById('newEntryName').value = searchTerm;
            if (notFoundMessage) notFoundMessage.style.display = 'none';
            handleCategoryChange();
        });
    }
});
