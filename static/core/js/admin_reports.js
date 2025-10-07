(function(){
  const searchInput = document.getElementById('reportSearch');
  const statusSelect = document.getElementById('reportStatusFilter');
  const tableBody = document.getElementById('reportsTableBody');
  const filterButton = document.getElementById('reportFilterButton');

  if(!searchInput || !statusSelect || !tableBody){
    return;
  }

  const emptyText = tableBody.dataset.emptyText || 'No reports found.';
  let debounceTimer = null;
  let activeController = null;

  const escapeHtml = (value) => {
    if(value === null || value === undefined){
      return '';
    }
    return String(value).replace(/[&<>"']/g, (match) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    })[match]);
  };

  const buildActions = (item) => {
    const links = [];
    if(item.is_generated){
      if(item.view_url){
        links.push(`<a href="${item.view_url}" class="report-action-btn">View</a>`);
      }
      if(item.pdf_url){
        links.push(`<a href="${item.pdf_url}" class="report-action-btn">PDF</a>`);
      }
    } else {
      if(item.file_url){
        links.push(`<a href="${item.file_url}" class="report-action-btn" download>Download</a>`);
      }
      if(item.approve_url){
        links.push(`<a href="${item.approve_url}" class="report-action-btn">Approve</a>`);
      }
      if(item.reject_url){
        links.push(`<a href="${item.reject_url}" class="report-action-btn">Reject</a>`);
      }
    }
    return links.length ? links.join(' ') : '-';
  };

  const renderRows = (items) => {
    if(!Array.isArray(items) || !items.length){
      tableBody.innerHTML = `<tr class="no-results-row"><td colspan="8" style="text-align:center;">${escapeHtml(emptyText)}</td></tr>`;
      return;
    }

    const rows = items.map((item, index) => {
      const statusClass = escapeHtml(item.status_class || '');
      const statusLabel = escapeHtml(item.status_label || '-');
      return `<tr>
        <td>${index + 1}</td>
        <td>${escapeHtml(item.title || '-')}</td>
        <td>${escapeHtml(item.type || '-')}</td>
        <td>${escapeHtml(item.organization || '-')}</td>
        <td>${escapeHtml(item.submitted_by || '-')}</td>
        <td>${escapeHtml(item.created_at_display || '')}</td>
        <td><span class="${statusClass}">${statusLabel}</span></td>
        <td>${buildActions(item)}</td>
      </tr>`;
    }).join('');

    tableBody.innerHTML = rows;
  };

  const showLoading = () => {
    tableBody.innerHTML = '<tr class="loading-row"><td colspan="8"><div class="reports-loading"><span class="spinner" aria-hidden="true"></span><span>Loading reports…</span></div></td></tr>';
  };

  const showError = () => {
    tableBody.innerHTML = '<tr class="no-results-row"><td colspan="8" style="text-align:center;">Unable to load reports. Please try again.</td></tr>';
  };

  const fetchReports = () => {
    const params = new URLSearchParams();
    const searchValue = searchInput.value.trim();
    const statusValue = statusSelect.value;

    if(searchValue){
      params.append('search', searchValue);
    }
    if(statusValue){
      params.append('status', statusValue);
    }

    if(activeController){
      activeController.abort();
    }
    const controller = new AbortController();
    activeController = controller;

    const query = params.toString();
    const url = query ? `/core-admin/api/reports/?${query}` : '/core-admin/api/reports/';

    showLoading();

    fetch(url, {
      headers: { 'Accept': 'application/json' },
      signal: controller.signal,
    })
      .then((response) => {
        if(!response.ok){
          throw new Error(`Failed with status ${response.status}`);
        }
        return response.json();
      })
      .then((payload) => {
        renderRows(payload && payload.results ? payload.results : []);
      })
      .catch((error) => {
        if(error.name === 'AbortError'){
          return;
        }
        console.error('Failed to load reports', error);
        showError();
      })
      .finally(() => {
        if(activeController === controller){
          activeController = null;
        }
      });
  };

  const debouncedFetch = () => {
    if(debounceTimer){
      clearTimeout(debounceTimer);
    }
    debounceTimer = setTimeout(fetchReports, 300);
  };

  searchInput.addEventListener('input', debouncedFetch);
  statusSelect.addEventListener('change', fetchReports);
  filterButton && filterButton.addEventListener('click', fetchReports);

  // Provide a hook for other scripts to refresh the table.
  document.addEventListener('reports:refresh', fetchReports);

  fetchReports();
})();
