class SearchPageManager {
  constructor(config) {
    const urlParams = new URLSearchParams(window.location.search);

    this.searchQuery = config.initialSearchQuery || '';
    this.searchClauses = config.initialSearchClauses || [];
    this.dataSourceName = config.dataSourceName || '';
    this.apiEndpoint = config.apiEndpoint || '/search/api/search-results-list/';
    this.csrfToken = config.csrfToken || '';
    this.citationStylesEndpoint = config.citationStylesEndpoint || '/search/api/citation-styles/';
    this.citationPreviewEndpoint = config.citationPreviewEndpoint || '/search/api/citation-preview/';
    this.citationCustomStyleEndpoint = config.citationCustomStyleEndpoint || '/search/api/citation-custom-style/';
    this.citationExportEndpoint = config.citationExportEndpoint || '/search/api/citation-export/';
    this.searchableFields = config.searchableFields || [];
    this.currentCitationDocument = null;
    this.citationStylesLoaded = false;
    this.currentSort = urlParams.get('sort') || 'desc';
    this.currentLimit = urlParams.get('limit') || '25';
    this.currentPage = parseInt(urlParams.get('page'), 10) || 1;
    this.currentDisplayMode = window.localStorage.getItem('searchPageDisplayMode') || 'grid';
    this.searchForm = document.getElementById('search-form');
    this.sidebarRoot = document.getElementById('search-sidebar-root');
    this.resultsContainer = document.getElementById('results-container');
    this.layoutRoot = document.getElementById('mainContent');
    this.headerRow = document.getElementById('search-header-row');
    this.sidebarToggleButton = document.getElementById('search-sidebar-toggle');

    this.init();
  }

  async init() {
    this.setupSearchForm();
    this.setupAdvancedSearchUI();
    this.setupSidebarToggle();
    this.setupGlobalResultsControlEvents();
    this.restoreSearchClauses();
    await this.initSidebar();
    this.setupResultsUi();
    this.setupCitationUi();
  }

  get sidebarForm() {
    return document.getElementById('search-filter-form');
  }

  setupSearchForm() {
    if (!this.searchForm) return;
    this.searchForm.addEventListener('submit', event => {
      event.preventDefault();
      this.searchClauses = this.getSearchClauses();
      this.applyFiltersAjax();
    });
  }

  setupAdvancedSearchUI() {
    const btnAdd = document.getElementById('btn-add-field');
    const btnClear = document.getElementById('btn-clear');
    const extraRows = document.getElementById('advanced-search-rows');

    if (btnAdd) {
      btnAdd.addEventListener('click', () => this.addSearchRow());
    }
    if (btnClear) {
      btnClear.addEventListener('click', () => this.clearSearchQuery());
    }
    if (extraRows) {
      extraRows.addEventListener('click', event => {
        if (event.target.closest('.btn-remove-row')) {
          this.removeSearchRow(event.target.closest('.btn-remove-row'));
        }
      });
    }
  }

  setupSidebarToggle() {
    const toggleButton = this.sidebarToggleButton;
    const layoutRoot = this.layoutRoot;
    const headerRow = this.headerRow;
    if (!toggleButton || !layoutRoot) return;

    const hiddenClass = 'sg-layout--filters-hidden';
    const storageKey = 'searchPageFiltersHidden';
    const toggleLabel = toggleButton.querySelector('.search-header-card__toggle-text');

    const applyState = hidden => {
      layoutRoot.classList.toggle(hiddenClass, hidden);
      if (headerRow) {
        headerRow.classList.toggle(hiddenClass, hidden);
      }
      toggleButton.setAttribute('aria-expanded', hidden ? 'false' : 'true');
      if (toggleLabel) {
        toggleLabel.textContent = hidden
          ? (toggleButton.dataset.labelShow || gettext('Mostrar filtros'))
          : (toggleButton.dataset.labelHide || gettext('Ocultar filtros'));
      }
    };

    const storedState = window.localStorage.getItem(storageKey);
    applyState(storedState === 'true');

    toggleButton.addEventListener('click', () => {
      const nextHidden = !layoutRoot.classList.contains(hiddenClass);
      applyState(nextHidden);
      window.localStorage.setItem(storageKey, nextHidden ? 'true' : 'false');
    });
  }

  restoreSearchClauses() {
    if (!Array.isArray(this.searchClauses) || !this.searchClauses.length) return;

    const firstRow = document.querySelector('.advanced-search-row[data-row-index="0"]');
    if (firstRow && this.searchClauses[0]) {
      const clause = this.searchClauses[0];
      const fieldSelect = firstRow.querySelector('.search-field-select');
      const textInput = firstRow.querySelector('.search-text-input');
      if (fieldSelect) fieldSelect.value = clause.field || 'all';
      if (textInput) textInput.value = clause.text || '';
    }

    const container = document.getElementById('advanced-search-rows');
    if (!container) return;

    container.innerHTML = '';
    for (let index = 1; index < this.searchClauses.length; index += 1) {
      this.addSearchRow();
      const row = container.querySelector('.advanced-search-row:last-child');
      const clause = this.searchClauses[index];
      if (!row || !clause) continue;

      const operatorSelect = row.querySelector('.search-operator');
      const fieldSelect = row.querySelector('.search-field-select');
      const textInput = row.querySelector('.search-text-input');
      if (operatorSelect) operatorSelect.value = clause.operator || 'AND';
      if (fieldSelect) fieldSelect.value = clause.field || 'all';
      if (textInput) textInput.value = clause.text || '';
    }
  }

  getSearchClauses() {
    const clauses = [];

    const firstRow = document.querySelector('.advanced-search-row[data-row-index="0"]');
    if (firstRow) {
      const fieldSelect = firstRow.querySelector('.search-field-select');
      const textInput = firstRow.querySelector('.search-text-input');
      const text = textInput ? textInput.value.trim() : '';
      if (text) {
        clauses.push({
          operator: '',
          field: fieldSelect ? fieldSelect.value : 'all',
          text,
        });
      }
    }

    document.querySelectorAll('#advanced-search-rows .advanced-search-row').forEach(row => {
      const operatorSelect = row.querySelector('.search-operator');
      const fieldSelect = row.querySelector('.search-field-select');
      const textInput = row.querySelector('.search-text-input');
      const text = textInput ? textInput.value.trim() : '';
      if (!text) return;
      clauses.push({
        operator: operatorSelect ? operatorSelect.value : 'AND',
        field: fieldSelect ? fieldSelect.value : 'all',
        text,
      });
    });

    return clauses;
  }

  addSearchRow() {
    const template = document.getElementById('advanced-search-row-template');
    const container = document.getElementById('advanced-search-rows');
    if (!template || !container) return;

    const clone = template.content.cloneNode(true);
    const row = clone.querySelector('.advanced-search-row');
    row.dataset.rowIndex = String(container.children.length + 1);
    container.appendChild(clone);
  }

  removeSearchRow(button) {
    const row = button?.closest('.advanced-search-row');
    if (row && row.parentElement?.id === 'advanced-search-rows') {
      row.remove();
    }
  }

  async initSidebar() {
    if (window.SearchGatewayFilterForm) {
      await window.SearchGatewayFilterForm.init(this.sidebarRoot || document);
    }
    this.bindSidebarEvents();
  }

  bindSidebarEvents() {
    const form = this.sidebarForm;
    if (!form) return;

    if (form.dataset.searchPageBound === 'true') return;

    form.addEventListener('submit', event => {
      event.preventDefault();
      this.applyFiltersAjax();
    });

    form.addEventListener('search-gateway:filters-changed', () => {
      this.applyFiltersAjax();
    });

    const resetButton = document.getElementById('search-filter-reset');
    if (resetButton) {
      resetButton.addEventListener('click', () => {
        if (window.SearchGatewayFilterForm) {
          window.SearchGatewayFilterForm.resetForm(form);
        } else {
          form.reset();
        }
        this.applyFiltersAjax();
      });
    }

    form.dataset.searchPageBound = 'true';
  }

  buildSearchParams() {
    const params = new URLSearchParams();
    const clauses = this.getSearchClauses();
    if (clauses.length > 0) {
      params.set('search_clauses', JSON.stringify(clauses));
    } else if (this.searchQuery) {
      params.set('search', this.searchQuery);
    }

    if (this.dataSourceName) {
      params.set('index_name', this.dataSourceName);
    }

    const filters = window.SearchGatewayFilterForm
      ? window.SearchGatewayFilterForm.serializeForm(this.sidebarForm)
      : {};
    Object.entries(filters).forEach(([key, value]) => {
      if (Array.isArray(value)) {
        value.forEach(item => params.append(key, item));
        return;
      }
      params.append(key, value);
    });

    const sortSelect = document.getElementById('results-sort-select');
    const sortValue = sortSelect?.value || this.currentSort;
    if (sortValue) {
      params.set('sort', sortValue);
    }

    const activeLimitButton = document.querySelector(
      '[data-results-limit-option].results-controls__limit-option--active',
    );
    const limitValue = activeLimitButton?.textContent?.trim() || this.currentLimit;
    if (limitValue) {
      params.set('limit', limitValue);
    }

    if (this.currentDisplayMode) {
      params.set('display_mode', this.currentDisplayMode);
    }

    params.set('page', this.currentPage);

    return params;
  }

  showLoading() {
    if (this.resultsContainer) {
      this.resultsContainer.innerHTML = '<div class="text-center p-5"><i class="icon-spinner icon-spin icon-2x"></i></div>';
    }
  }

  async applyFiltersAjax(page = 1) {
    this.currentPage = page;
    this.showLoading();
    const params = this.buildSearchParams();

    try {
      const response = await fetch(`${this.apiEndpoint}?${params.toString()}`);
      if (!response.ok) throw new Error('Network response was not ok');
      const data = await response.json();

      if (this.resultsContainer) {
        this.resultsContainer.innerHTML = data.results_html || `
          <div class="alert alert-info" role="alert">
            ${gettext('No results found. Try adjusting your search or filters.')}
          </div>
        `;
        this.setupResultsUi();
      }

      if (this.sidebarRoot && data.sidebar_html) {
        this.sidebarRoot.innerHTML = data.sidebar_html;
        await this.initSidebar();
      }

      const url = new URL(window.location.href);
      url.search = params.toString();
      window.history.replaceState({}, '', url.toString());
    } catch (error) {
      console.error('Error applying filters:', error);
      if (this.resultsContainer) {
        this.resultsContainer.innerHTML = `
          <div class="alert alert-danger" role="alert">
            ${gettext('Error loading results. Try again.')}
          </div>
        `;
      }
    }
  }

  clearSearchQuery() {
    this.searchQuery = '';
    this.searchClauses = [];

    const firstRow = document.querySelector('.advanced-search-row[data-row-index="0"]');
    if (firstRow) {
      const fieldSelect = firstRow.querySelector('.search-field-select');
      const textInput = firstRow.querySelector('.search-text-input');
      if (fieldSelect) fieldSelect.value = 'all';
      if (textInput) textInput.value = '';
    }

    const extraRows = document.getElementById('advanced-search-rows');
    if (extraRows) extraRows.innerHTML = '';

    this.applyFiltersAjax();
  }

  setupGlobalResultsControlEvents() {
    if (document.body.dataset.searchPageControlsBound === 'true') return;

    document.addEventListener('change', event => {
      const sortSelect = event.target.closest('#results-sort-select');
      if (!sortSelect) return;
      this.currentSort = sortSelect.value || 'desc';
      this.applyFiltersAjax();
    });

    document.addEventListener('click', event => {
      const limitButton = event.target.closest('[data-results-limit-option]');
      if (!limitButton) return;

      document.querySelectorAll('[data-results-limit-option]').forEach(option => {
        option.classList.remove('results-controls__limit-option--active');
      });

      limitButton.classList.add('results-controls__limit-option--active');
      this.currentLimit = limitButton.textContent.trim() || '25';
      this.applyFiltersAjax();
    });

    document.addEventListener('click', event => {
      const pageButton = event.target.closest('[data-page]');
      if (!pageButton || pageButton.disabled) return;
      const page = parseInt(pageButton.dataset.page, 10);
      if (page) this.applyFiltersAjax(page);
    });

    document.addEventListener('click', event => {
      const modeButton = event.target.closest('[data-display-mode]');
      if (!modeButton) return;

      const mode = modeButton.dataset.displayMode;
      if (this.currentDisplayMode === mode) return;

      this.currentDisplayMode = mode;
      window.localStorage.setItem('searchPageDisplayMode', mode);
      this.applyDisplayMode();
      this.setupResultsUi();
      this.syncDisplayModeInUrl();
    });

    document.body.dataset.searchPageControlsBound = 'true';
  }

  setupResultsUi() {
    const sortSelect = document.getElementById('results-sort-select');
    if (sortSelect) {
      sortSelect.value = this.currentSort;
    }

    document.querySelectorAll('[data-results-limit-option]').forEach(option => {
      const isActive = option.textContent.trim() === this.currentLimit;
      option.classList.toggle('results-controls__limit-option--active', isActive);
    });

    document.querySelectorAll('[data-display-mode]').forEach(btn => {
      const isActive = btn.dataset.displayMode === this.currentDisplayMode;
      btn.classList.toggle('results-toolbar__icon-btn--active', isActive);
      btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });

    this.applyDisplayMode();
    this.bindResultsSelectionControls();
  }

  applyDisplayMode() {
    const resultsList = document.getElementById('results-list');
    if (!resultsList) return;

    resultsList.classList.toggle('results-list--lean', this.currentDisplayMode === 'list');
  }

  syncDisplayModeInUrl() {
    const url = new URL(window.location.href);
    if (this.currentDisplayMode) {
      url.searchParams.set('display_mode', this.currentDisplayMode);
    } else {
      url.searchParams.delete('display_mode');
    }

    window.history.replaceState({}, '', url.toString());
  }

  bindResultsSelectionControls() {
    const selectPage = document.getElementById('results-select-page');
    const itemCheckboxes = Array.from(document.querySelectorAll('.result-item__select-input'));
    const selectedCounter = document.getElementById('results-selected-counter');

    if (!selectPage || !selectedCounter) return;

    const singularLabel = selectedCounter.dataset.labelSingular || gettext('selecionado');
    const pluralLabel = selectedCounter.dataset.labelPlural || gettext('selecionados');

    const updateSelectionState = () => {
      const selectedCount = itemCheckboxes.filter(input => input.checked).length;
      const label = selectedCount === 1 ? singularLabel : pluralLabel;
      selectedCounter.textContent = `${selectedCount} ${label}`;

      if (!itemCheckboxes.length) {
        selectPage.checked = false;
        selectPage.indeterminate = false;
        return;
      }

      if (selectedCount === 0) {
        selectPage.checked = false;
        selectPage.indeterminate = false;
        return;
      }

      if (selectedCount === itemCheckboxes.length) {
        selectPage.checked = true;
        selectPage.indeterminate = false;
        return;
      }

      selectPage.checked = false;
      selectPage.indeterminate = true;
    };

    selectPage.addEventListener('change', () => {
      itemCheckboxes.forEach(input => {
        input.checked = selectPage.checked;
      });
      updateSelectionState();
    });

    itemCheckboxes.forEach(input => {
      input.addEventListener('change', updateSelectionState);
    });

    updateSelectionState();
  }

  // ── Citation modal ──────────────────────────────────────

  setupCitationUi() {
    if (document.body.dataset.citationBound === 'true') return;

    document.addEventListener('click', event => {
      const btn = event.target.closest('.js-open-citation-modal');
      if (btn) this.openCitationModal(btn);
    });

    document.addEventListener('click', event => {
      const btn = event.target.closest('.js-citation-export');
      if (btn) this.downloadCitationExport(btn.dataset.exportFormat);
    });

    const customStyleSelect = document.getElementById('citation-custom-style');
    if (customStyleSelect) {
      customStyleSelect.addEventListener('change', () => {
        this.syncCitationStyleDropdownUi();
        this.loadCustomCitation(customStyleSelect.value);
      });
    }

    this.setupCitationStyleSearchDropdown();

    document.addEventListener('click', event => {
      const btn = event.target.closest('.js-citation-copy');
      if (!btn) return;
      const row = btn.closest('.citation-modal__copy-row');
      const ta = row?.querySelector('.js-citation-copy-target');
      if (ta) this.copyCitationToClipboard(ta, btn);
    });

    document.body.dataset.citationBound = 'true';
  }

  async openCitationModal(button) {
    const scriptEl = document.getElementById(button.dataset.citationDocId);
    if (!scriptEl) return;

    try {
      this.currentCitationDocument = JSON.parse(scriptEl.textContent);
    } catch { return; }

    const modalEl = document.getElementById('citation-modal');
    if (!modalEl) return;

    const customField = document.querySelector('.js-citation-custom');
    if (customField) customField.value = '';
    const customStyleSelect = document.getElementById('citation-custom-style');
    if (customStyleSelect) customStyleSelect.value = '';
    const styleFilter = document.querySelector('.citation-style-dropdown__filter');
    if (styleFilter) styleFilter.value = '';
    this.filterCitationStyleList('');
    this.syncCitationStyleDropdownUi();

    this.showModal(modalEl);
    await this.ensureCitationStyleOptions();
    await this.loadCitationPreview();
  }

  showModal(el) {
    if (window.bootstrap?.Modal) {
      const instance = window.bootstrap.Modal.getInstance(el) || new window.bootstrap.Modal(el);
      instance.show();
    } else {
      el.classList.add('show');
      el.style.display = 'block';
      el.removeAttribute('aria-hidden');
    }
  }

  async postJson(endpoint, payload) {
    const resp = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.csrfToken,
      },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.error || 'Request failed');
    }
    return resp;
  }

  async ensureCitationStyleOptions() {
    const sel = document.getElementById('citation-custom-style');
    if (!sel || !this.citationStylesEndpoint || this.citationStylesLoaded) return;
    try {
      const resp = await fetch(this.citationStylesEndpoint);
      if (!resp.ok) return;
      const data = await resp.json();
      const styles = data.styles || [];
      const first = sel.querySelector('option[value=""]');
      const placeholder = first ? first.cloneNode(true) : null;
      sel.innerHTML = '';
      if (placeholder) sel.appendChild(placeholder);
      else {
        const opt = document.createElement('option');
        opt.value = '';
        opt.textContent = gettext('Selecione um formato de citação…');
        sel.appendChild(opt);
      }
      styles.forEach(s => {
        const o = document.createElement('option');
        o.value = s.id;
        o.textContent = s.label || s.id;
        sel.appendChild(o);
      });
      this.rebuildCitationStyleDropdownList();
      this.citationStylesLoaded = true;
    } catch (err) {
      console.error('Citation styles list error:', err);
    }
  }

  async loadCitationPreview() {
    if (!this.currentCitationDocument) return;
    try {
      const resp = await this.postJson(this.citationPreviewEndpoint, {
        documents: [this.currentCitationDocument],
      });
      const data = await resp.json();
      this.renderPresets(data.presets || []);
    } catch (err) {
      console.error('Citation preview error:', err);
    }
  }

  setupCitationStyleSearchDropdown() {
    const toggle = document.getElementById('citation-custom-style-toggle');
    const list = document.querySelector('.citation-style-dropdown__list');
    const filter = document.querySelector('.citation-style-dropdown__filter');
    const sel = document.getElementById('citation-custom-style');
    if (!toggle || !list || !filter || !sel || toggle.dataset.citationDropdownInit === 'true') return;
    toggle.dataset.citationDropdownInit = 'true';

    const stop = e => e.stopPropagation();
    filter.addEventListener('mousedown', stop);
    filter.addEventListener('click', stop);

    filter.addEventListener('input', () => {
      this.filterCitationStyleList(filter.value);
    });

    list.addEventListener('click', event => {
      const item = event.target.closest('.citation-style-dropdown__item');
      if (!item) return;
      event.preventDefault();
      const val = item.dataset.value;
      sel.value = val;
      this.syncCitationStyleDropdownUi();
      this.loadCustomCitation(val);
      this.hideCitationStyleDropdown();
    });

    toggle.addEventListener('shown.bs.dropdown', () => {
      filter.focus({ preventScroll: true });
      if (typeof filter.select === 'function') filter.select();
    });
  }

  rebuildCitationStyleDropdownList() {
    const sel = document.getElementById('citation-custom-style');
    const list = document.querySelector('.citation-style-dropdown__list');
    if (!sel || !list) return;
    list.innerHTML = '';
    [...sel.options].forEach(opt => {
      if (!opt.value) return;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.setAttribute('role', 'option');
      btn.className = 'dropdown-item py-2 px-3 citation-style-dropdown__item text-start text-wrap';
      btn.dataset.value = opt.value;
      btn.textContent = opt.textContent;
      list.appendChild(btn);
    });
    const filter = document.querySelector('.citation-style-dropdown__filter');
    this.filterCitationStyleList(filter?.value || '');
    this.syncCitationStyleDropdownUi();
  }

  filterCitationStyleList(query) {
    const norm = (query || '').trim().toLowerCase();
    document.querySelectorAll('.citation-style-dropdown__item').forEach(el => {
      const hay = `${el.textContent} ${el.dataset.value || ''}`.toLowerCase();
      el.classList.toggle('d-none', Boolean(norm) && !hay.includes(norm));
    });
  }

  syncCitationStyleDropdownUi() {
    const sel = document.getElementById('citation-custom-style');
    const cur = document.querySelector('.citation-style-dropdown__current');
    if (!sel || !cur) return;
    const opt = sel.options[sel.selectedIndex];
    const placeholder = gettext('Selecione um formato de citação…');
    cur.textContent = opt && opt.value ? opt.textContent : placeholder;
    document.querySelectorAll('.citation-style-dropdown__item').forEach(el => {
      const on = el.dataset.value === sel.value;
      el.classList.toggle('active', on);
      el.setAttribute('aria-selected', on ? 'true' : 'false');
    });
  }

  hideCitationStyleDropdown() {
    const toggle = document.getElementById('citation-custom-style-toggle');
    const menu = document.querySelector('.citation-style-dropdown__menu');
    if (!toggle || !menu) return;
    const inst = window.bootstrap?.Dropdown?.getInstance(toggle);
    if (inst) {
      inst.hide();
      return;
    }
    if (menu.classList.contains('show')) {
      menu.classList.remove('show');
      toggle.classList.remove('show');
      toggle.setAttribute('aria-expanded', 'false');
    }
  }

  renderPresets(presets) {
    const container = document.getElementById('citation-modal-presets');
    if (!container) return;
    const copyLabel = gettext('Copiar');
    const copyAria = gettext('Copiar citação');
    container.innerHTML = presets.map(p => `
      <div class="citation-modal__section">
        <h6 class="citation-modal__label">${this.escapeHtml(p.label)}</h6>
        <div class="citation-modal__copy-row">
          <textarea class="form-control citation-modal__textarea js-citation-copy-target" rows="5" readonly>${this.escapeHtml(p.citation)}</textarea>
          <button type="button" class="btn btn-outline-secondary btn-sm citation-modal__copy-btn js-citation-copy" aria-label="${this.escapeHtml(copyAria)}">${this.escapeHtml(copyLabel)}</button>
        </div>
      </div>
    `).join('');
  }

  async copyCitationToClipboard(textarea, button) {
    const text = textarea?.value || '';
    if (!text) return;
    let ok = false;
    try {
      await navigator.clipboard.writeText(text);
      ok = true;
    } catch {
      try {
        textarea.select();
        ok = document.execCommand('copy');
      } catch {
        ok = false;
      }
    }
    if (!button || !ok) return;
    const labelDone = gettext('Copiado!');
    const prev = button.textContent;
    button.textContent = labelDone;
    button.disabled = true;
    clearTimeout(button._copyResetTimer);
    button._copyResetTimer = setTimeout(() => {
      button.textContent = prev;
      button.disabled = false;
    }, 2000);
  }

  escapeHtml(str) {
    const el = document.createElement('span');
    el.textContent = str || '';
    return el.innerHTML;
  }

  async loadCustomCitation(style) {
    const field = document.querySelector('.js-citation-custom');
    if (!field) return;
    if (!style) { field.value = ''; return; }
    try {
      const resp = await this.postJson(this.citationCustomStyleEndpoint, {
        documents: [this.currentCitationDocument],
        style,
      });
      const data = await resp.json();
      field.value = data.citation || '';
    } catch (err) {
      field.value = '';
      console.error('Custom citation error:', err);
    }
  }

  async downloadCitationExport(format) {
    if (!this.currentCitationDocument || !format) return;
    try {
      const resp = await this.postJson(this.citationExportEndpoint, {
        format,
        documents: [this.currentCitationDocument],
      });
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `citation.${format === 'ris' ? 'ris' : 'bib'}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Citation export error:', err);
    }
  }

}

document.addEventListener('DOMContentLoaded', () => {
  if (window.searchPageConfig) {
    window.searchPageManager = new SearchPageManager(window.searchPageConfig);
  }
});
