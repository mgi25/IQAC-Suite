(function () {
  const root = document.querySelector('.report-step');
  if (!root) {
    return;
  }

  const reportId = Number(root.dataset.reportId || 0);
  const uploadUrl = `/suite/report/${reportId}/assets/`;
  const detailUrl = (assetId) => `/suite/report/assets/${assetId}/`;

  const assetDataScript = document.getElementById('asset-initial-data');
  let initialAssets = {};
  if (assetDataScript) {
    try {
      initialAssets = JSON.parse(assetDataScript.textContent);
    } catch (err) {
      console.error('Failed to parse initial assets JSON', err);
    }
  }

  const csrfToken = (() => {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) {
      return meta.getAttribute('content');
    }
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  })();

  const IMAGE_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png', '.webp']);
  const ALLOWED_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png', '.webp', '.pdf']);
  const MAX_UPLOAD_SIZE = 10 * 1024 * 1024;

  const saveBtn = root.querySelector('[data-role="save-btn"]');
  const saveForm = root.querySelector('[data-role="save-form"]');
  const helperTimeouts = new WeakMap();

  let pendingUploads = 0;
  const panelsByCategory = {};
  const panelInstances = [];

  function ensureAnnexures() {
    if (!window.initial_report_data) {
      window.initial_report_data = {};
    }
    if (!window.initial_report_data.annexures) {
      window.initial_report_data.annexures = {};
    }
    const annex = window.initial_report_data.annexures;
    if (!annex.communication) {
      annex.communication = { subject: '', date: '', files: [], volunteer_list: [] };
    } else if (!Array.isArray(annex.communication.files)) {
      annex.communication.files = [];
    }
    return annex;
  }

  function toPreviewItem(asset) {
    const entry = {
      src: asset.src || '',
      caption: asset.caption && asset.caption.trim() ? asset.caption : '—'
    };
    if (asset.meta && typeof asset.meta === 'object') {
      entry.meta = asset.meta;
    }
    return entry;
  }

  function updatePreviewState() {
    const annex = ensureAnnexures();
    const photosPanel = panelsByCategory['photo'];
    const brochurePanel = panelsByCategory['brochure'];
    const communicationPanel = panelsByCategory['communication'];
    const worksheetPanel = panelsByCategory['worksheet'];
    const evaluationPanel = panelsByCategory['evaluation'];
    const feedbackPanel = panelsByCategory['feedback'];

    if (photosPanel) {
      annex.photos = photosPanel.assets.map(toPreviewItem);
    }
    if (brochurePanel) {
      annex.brochure_pages = brochurePanel.assets.map(toPreviewItem);
    }
    if (communicationPanel) {
      annex.communication.files = communicationPanel.assets.map(toPreviewItem);
    }
    if (worksheetPanel) {
      annex.worksheets = worksheetPanel.assets.map(toPreviewItem);
    }
    if (evaluationPanel) {
      annex.evaluation_sheet = evaluationPanel.assets.length
        ? toPreviewItem(evaluationPanel.assets[0])
        : { src: '', caption: '—' };
    }
    if (feedbackPanel) {
      annex.feedback_form = feedbackPanel.assets.length
        ? toPreviewItem(feedbackPanel.assets[0])
        : { src: '', caption: '—' };
    }
  }

  function adjustPending(delta) {
    pendingUploads = Math.max(0, pendingUploads + delta);
    if (!saveBtn) return;
    if (pendingUploads > 0) {
      saveBtn.disabled = true;
      saveBtn.dataset.originalLabel = saveBtn.dataset.originalLabel || saveBtn.textContent;
      saveBtn.textContent = 'Uploading…';
    } else {
      saveBtn.disabled = false;
      if (saveBtn.dataset.originalLabel) {
        saveBtn.textContent = saveBtn.dataset.originalLabel;
      }
    }
  }

  function setHelper(panelEl, message, tone = 'error') {
    const helper = panelEl.querySelector('[data-role="helper"]');
    if (!helper) return;
    helper.textContent = message || '';
    helper.dataset.tone = tone;
    if (helperTimeouts.has(helper)) {
      clearTimeout(helperTimeouts.get(helper));
    }
    if (message) {
      const timeout = setTimeout(() => {
        helper.textContent = '';
        helper.dataset.tone = '';
      }, 5000);
      helperTimeouts.set(helper, timeout);
    }
  }

  function getExtension(filename) {
    if (!filename) return '';
    const dotIndex = filename.lastIndexOf('.');
    return dotIndex === -1 ? '' : filename.slice(dotIndex).toLowerCase();
  }

  async function fetchJson(url, options) {
    const response = await fetch(url, options);
    let data = null;
    try {
      data = await response.json();
    } catch (err) {
      data = null;
    }
    if (!response.ok) {
      const errorMessage = data && data.error ? data.error : `Request failed (${response.status})`;
      throw new Error(errorMessage);
    }
    return data;
  }

  class AssetPanel {
    constructor(element) {
      this.root = element;
      this.category = element.dataset.category;
      this.multiple = element.dataset.multiple === 'true';
      this.maxItems = element.dataset.maxItems ? Number(element.dataset.maxItems) : null;
      this.isSingleton = element.dataset.singleton === 'true';
      this.grid = element.querySelector('[data-role="grid"]');
      this.dropzone = element.querySelector('[data-role="dropzone"]');
      this.counter = element.querySelector('[data-role="counter"]');
      this.fileInput = element.querySelector('[data-role="file-input"]');
      this.assets = [];
      this.draggedCard = null;
      this.captionTimers = new Map();
      this.pendingCaptionSaves = new Map();
      this.initEvents();
    }

    init(initialList) {
      if (Array.isArray(initialList)) {
        this.assets = initialList.slice().sort((a, b) => {
          if (a.order_index === b.order_index) {
            return a.id - b.id;
          }
          return a.order_index - b.order_index;
        });
      }
      this.render();
    }

    initEvents() {
      if (this.dropzone) {
        ['dragenter', 'dragover'].forEach((eventName) => {
          this.dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            this.dropzone.classList.add('drag-over');
          });
        });
        ['dragleave', 'dragend'].forEach((eventName) => {
          this.dropzone.addEventListener(eventName, () => {
            this.dropzone.classList.remove('drag-over');
          });
        });
        this.dropzone.addEventListener('drop', (event) => {
          event.preventDefault();
          this.dropzone.classList.remove('drag-over');
          const items = event.dataTransfer?.files;
          if (items && items.length) {
            this.handleFiles(Array.from(items));
          }
        });
      }

      const browseBtn = this.root.querySelector('[data-role="browse"]');
      if (browseBtn && this.fileInput) {
        browseBtn.addEventListener('click', () => {
          this.fileInput.click();
        });
        this.fileInput.addEventListener('change', () => {
          const files = Array.from(this.fileInput.files || []);
          if (files.length) {
            this.handleFiles(files);
          }
          this.fileInput.value = '';
        });
      }

      if (this.grid) {
        this.grid.addEventListener('dragstart', (event) => {
          const card = event.target.closest('.asset-card');
          if (!card) return;
          if (!event.target.classList.contains('btn-sort') && !event.target.closest('.btn-sort')) {
            event.preventDefault();
            return;
          }
          this.draggedCard = card;
          card.classList.add('dragging');
          event.dataTransfer.effectAllowed = 'move';
        });
        this.grid.addEventListener('dragover', (event) => {
          if (!this.draggedCard) return;
          event.preventDefault();
          const card = event.target.closest('.asset-card');
          if (!card || card === this.draggedCard) return;
          const bounds = card.getBoundingClientRect();
          const after = event.clientY > bounds.top + bounds.height / 2;
          if (after) {
            card.after(this.draggedCard);
          } else {
            card.before(this.draggedCard);
          }
        });
        this.grid.addEventListener('drop', (event) => {
          event.preventDefault();
          if (!this.draggedCard) return;
          this.draggedCard.classList.remove('dragging');
          this.draggedCard = null;
          this.syncOrderFromDom();
        });
        this.grid.addEventListener('dragend', () => {
          if (this.draggedCard) {
            this.draggedCard.classList.remove('dragging');
            this.draggedCard = null;
          }
        });
      }
    }

    render() {
      if (!this.grid) return;
      this.grid.innerHTML = '';
      if (!this.assets.length) {
        const empty = document.createElement('div');
        empty.className = 'asset-empty';
        empty.textContent = 'No files uploaded yet.';
        this.grid.appendChild(empty);
      } else {
        this.assets.forEach((asset) => {
          const card = this.createCard(asset);
          this.grid.appendChild(card);
        });
      }
      this.updateCounter();
      this.updateHelperMessage();
    }

    createCard(asset) {
      const card = document.createElement('div');
      card.className = 'asset-card';
      card.dataset.id = asset.id;
      card.draggable = true;

      const thumb = document.createElement('div');
      thumb.className = 'thumb';
      const isPdf = (asset.meta && typeof asset.meta === 'object' && typeof asset.meta.content_type === 'string'
        && asset.meta.content_type.toLowerCase().includes('pdf')) || getExtension(asset.src) === '.pdf';
      if (isPdf) {
        thumb.classList.add('pdf');
        thumb.textContent = 'PDF';
      } else if (asset.src) {
        const img = document.createElement('img');
        img.src = asset.src;
        img.alt = asset.caption || 'Attachment';
        thumb.appendChild(img);
      } else {
        thumb.textContent = '—';
      }
      card.appendChild(thumb);

      const caption = document.createElement('input');
      caption.type = 'text';
      caption.className = 'caption';
      caption.placeholder = 'Caption…';
      caption.value = asset.caption || '';
      caption.addEventListener('input', () => {
        this.scheduleCaptionUpdate(asset, caption.value);
      });
      card.appendChild(caption);

      const actions = document.createElement('div');
      actions.className = 'asset-actions';

      const sortBtn = document.createElement('button');
      sortBtn.type = 'button';
      sortBtn.className = 'btn-sort';
      sortBtn.title = 'Drag to reorder';
      sortBtn.textContent = '⇅';
      actions.appendChild(sortBtn);

      const delBtn = document.createElement('button');
      delBtn.type = 'button';
      delBtn.className = 'btn-del';
      delBtn.title = 'Remove';
      delBtn.textContent = '✕';
      delBtn.addEventListener('click', () => {
        this.deleteAsset(asset);
      });
      actions.appendChild(delBtn);

      card.appendChild(actions);
      return card;
    }

    updateCounter() {
      if (!this.counter) return;
      const count = this.assets.length;
      if (this.maxItems) {
        const unit = this.category === 'brochure' ? 'pages' : (this.maxItems === 1 ? 'file' : 'files');
        this.counter.textContent = `${count}/${this.maxItems} ${unit}`;
      } else {
        this.counter.textContent = `${count} file${count === 1 ? '' : 's'}`;
      }
    }

    updateHelperMessage() {
      const helper = this.root.querySelector('[data-role="helper"]');
      const hasError = helper && helper.dataset.tone === 'error' && helper.textContent;
      if (hasError) {
        return;
      }
      if (this.maxItems && this.assets.length >= this.maxItems) {
        const noun = this.category === 'brochure' ? 'brochure pages' : 'files';
        setHelper(this.root, `Maximum ${this.maxItems} ${noun} reached.`, 'info');
      } else {
        setHelper(this.root, '');
      }
    }

    sortAssets() {
      this.assets.sort((a, b) => {
        if (a.order_index === b.order_index) {
          return a.id - b.id;
        }
        return a.order_index - b.order_index;
      });
    }

    async handleFiles(files) {
      if (!files.length) return;

      if (this.isSingleton && this.assets.length) {
        const confirmReplace = window.confirm('Replace the existing file?');
        if (!confirmReplace) {
          return;
        }
        await this.deleteAsset(this.assets[0], { silent: true });
      }

      let available = this.maxItems != null ? this.maxItems - this.assets.length : files.length;
      if (this.maxItems != null && available <= 0) {
        this.updateHelperMessage();
        return;
      }

      const accepted = [];
      const rejected = [];
      files.forEach((file) => {
        const ext = getExtension(file.name);
        if (!ALLOWED_EXTENSIONS.has(ext)) {
          rejected.push(`${file.name}: unsupported type`);
          return;
        }
        if (file.size > MAX_UPLOAD_SIZE) {
          rejected.push(`${file.name}: exceeds 10 MB`);
          return;
        }
        if (this.maxItems != null && accepted.length >= available) {
          return;
        }
        accepted.push(file);
      });

      if (rejected.length) {
        setHelper(this.root, rejected.join('\n'));
      }
      if (!accepted.length) {
        return;
      }

      for (const file of accepted) {
        try {
          await this.uploadFile(file);
        } catch (err) {
          setHelper(this.root, err.message || 'Upload failed');
          break;
        }
      }
      this.render();
      updatePreviewState();
    }

    async uploadFile(file) {
      const formData = new FormData();
      formData.append('category', this.category);
      formData.append('file', file);
      adjustPending(1);
      try {
        const data = await fetchJson(uploadUrl, {
          method: 'POST',
          body: formData,
          headers: {
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
          }
        });
        this.assets.push(data);
        // TODO: Trigger future caption suggestions based on uploaded media metadata.
        this.sortAssets();
      } finally {
        adjustPending(-1);
      }
    }

    async deleteAsset(asset, options = {}) {
      const { silent = false } = options;
      if (!silent) {
        const confirmed = window.confirm('Remove this file?');
        if (!confirmed) {
          return;
        }
      }
      try {
        await fetchJson(detailUrl(asset.id), {
          method: 'DELETE',
          headers: {
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
          }
        });
        this.assets = this.assets.filter((item) => item.id !== asset.id);
        await this.reindexOrder();
        this.render();
        updatePreviewState();
      } catch (err) {
        setHelper(this.root, err.message || 'Failed to delete file');
      }
    }

    async reindexOrder() {
      const requests = [];
      this.assets.forEach((asset, index) => {
        if (asset.order_index !== index) {
          asset.order_index = index;
          requests.push(
            fetchJson(detailUrl(asset.id), {
              method: 'PATCH',
              headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
              },
              body: JSON.stringify({ order_index: index })
            })
          );
        }
      });
      if (requests.length) {
        await Promise.allSettled(requests);
      }
    }

    scheduleCaptionUpdate(asset, value) {
      if (this.captionTimers.has(asset.id)) {
        clearTimeout(this.captionTimers.get(asset.id));
      }
      const timer = setTimeout(() => {
        this.captionTimers.delete(asset.id);
        this.persistCaption(asset, value);
      }, 500);
      this.captionTimers.set(asset.id, timer);
      this.pendingCaptionSaves.set(asset.id, value);
    }

    async flushCaptionUpdates() {
      const pending = Array.from(this.pendingCaptionSaves.entries());
      this.pendingCaptionSaves.clear();
      pending.forEach(([assetId, value]) => {
        if (this.captionTimers.has(assetId)) {
          clearTimeout(this.captionTimers.get(assetId));
          this.captionTimers.delete(assetId);
        }
      });
      if (!pending.length) return;
      await Promise.allSettled(
        pending.map(([assetId, value]) => {
          const asset = this.assets.find((item) => item.id === assetId);
          if (!asset) return Promise.resolve();
          return this.persistCaption(asset, value);
        })
      );
    }

    async persistCaption(asset, value) {
      const payload = { caption: value };
      this.pendingCaptionSaves.delete(asset.id);
      try {
        const data = await fetchJson(detailUrl(asset.id), {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: JSON.stringify(payload)
        });
        asset.caption = data.caption;
        updatePreviewState();
      } catch (err) {
        setHelper(this.root, err.message || 'Failed to update caption');
      }
    }

    async syncOrderFromDom() {
      if (!this.grid) return;
      const idOrder = Array.from(this.grid.querySelectorAll('.asset-card')).map((card) => Number(card.dataset.id));
      const currentOrder = this.assets.map((asset) => asset.id);
      const changed = idOrder.some((id, index) => id !== currentOrder[index]);
      if (!changed) {
        return;
      }
      const lookup = new Map(this.assets.map((asset) => [asset.id, asset]));
      this.assets = idOrder.map((id, index) => {
        const asset = lookup.get(id);
        if (asset) {
          asset.order_index = index;
        }
        return asset;
      }).filter(Boolean);
      this.render();
      updatePreviewState();
      await this.reindexOrder();
    }
  }

  const panelElements = Array.from(root.querySelectorAll('.asset-panel'));
  panelElements.forEach((element) => {
    const panel = new AssetPanel(element);
    const category = panel.category;
    panelInstances.push(panel);
    panelsByCategory[category] = panel;
    const initialList = initialAssets[category] || [];
    panel.init(initialList);
  });

  updatePreviewState();

  if (saveForm) {
    saveForm.addEventListener('submit', async (event) => {
      if (pendingUploads > 0) {
        event.preventDefault();
        window.alert('Please wait for uploads to finish.');
        return;
      }
      event.preventDefault();
      await Promise.all(panelInstances.map((panel) => panel.flushCaptionUpdates()));
      updatePreviewState();
      saveForm.submit();
    });
  }
})();
