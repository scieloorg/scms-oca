class SearchPageManager {
  constructor(config) {
    const urlParams = new URLSearchParams(window.location.search);

    this.searchQuery = config.initialSearchQuery || '';
    this.searchClauses = config.initialSearchClauses || [];
    this.dataSourceName = config.dataSourceName || '';
    this.apiEndpoint = config.apiEndpoint || '/search/api/search-results-list/';
    this.currentSort = urlParams.get('sort') || 'desc';
    this.currentLimit = urlParams.get('limit') || '25';
    this.currentPage = 1;
    this.currentDisplayMode = window.localStorage.getItem('searchPageDisplayMode') || 'grid';
    this.searchForm = document.getElementById('search-form');
    this.sidebarRoot = document.getElementById('search-sidebar-root');
    this.resultsContainer = document.getElementById('results-container');
    this.layoutRoot = document.getElementById('mainContent');
    this.headerRow = document.getElementById('search-header-row');
    this.sidebarToggleButton = document.getElementById('search-sidebar-toggle');
    this._filtersFetchAbortController = null;

    this.init();
  }

  async init() {
    this.setupSearchForm();
    this.setupAdvancedSearchUI();
    this.setupSidebarToggle();
    this.setupGlobalResultsControlEvents();
    this.setupResultsSelectionDelegation();
    this.restoreSearchClauses();
    await this.initSidebar();
    this.setupResultsUi();
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

    if (this.currentSort) {
      params.set('sort', this.currentSort);
    }

    if (this.currentLimit) {
      params.set('limit', this.currentLimit);
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
    if (this._filtersFetchAbortController) {
      this._filtersFetchAbortController.abort();
    }
    this._filtersFetchAbortController = new AbortController();
    const { signal } = this._filtersFetchAbortController;

    this.showLoading();
    const params = this.buildSearchParams();

    try {
      const response = await fetch(`${this.apiEndpoint}?${params.toString()}`, { signal });
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

      const sidebarForm = this.sidebarForm;
      if (sidebarForm && window.SearchGatewayFilterForm?.commitAppliedFilters) {
        window.SearchGatewayFilterForm.commitAppliedFilters(sidebarForm);
      }

      const url = new URL(window.location.href);
      url.search = params.toString();
      window.history.replaceState({}, '', url.toString());
    } catch (error) {
      if (error.name === 'AbortError') {
        return;
      }
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
    });

    document.addEventListener('click', event => {
      const printBtn = event.target.closest('[data-results-print-selected]');
      if (!printBtn || printBtn.disabled) return;
      if (window.SearchResultsPrint && typeof window.SearchResultsPrint.printSelectedCards === 'function') {
        window.SearchResultsPrint.printSelectedCards();
      }
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
    this.updateResultsSelectionCounter();
  }

  applyDisplayMode() {
    const resultsList = document.getElementById('results-list');
    if (!resultsList) return;

    resultsList.classList.toggle('results-list--lean', this.currentDisplayMode === 'list');
  }

  setupResultsSelectionDelegation() {
    if (!this.resultsContainer || this.resultsContainer.dataset.searchPageSelectionBound === 'true') {
      return;
    }

    this.resultsContainer.addEventListener('change', event => {
      const { target } = event;

      if (target.id === 'results-select-page') {
        this.resultsContainer.querySelectorAll('.result-item__select-input').forEach(input => {
          input.checked = target.checked;
        });
        this.updateResultsSelectionCounter();
        return;
      }

      if (target.classList.contains('result-item__select-input')) {
        this.updateResultsSelectionCounter();
      }
    });

    this.resultsContainer.dataset.searchPageSelectionBound = 'true';
  }

  updateResultsSelectionCounter() {
    if (!this.resultsContainer) return;

    const selectPage = this.resultsContainer.querySelector('#results-select-page');
    const selectedCounter = this.resultsContainer.querySelector('#results-selected-counter');
    const itemCheckboxes = this.resultsContainer.querySelectorAll('.result-item__select-input');
    const selectedCount = Array.from(itemCheckboxes).filter(input => input.checked).length;

    if (selectPage && selectedCounter) {
      const singularLabel = selectedCounter.dataset.labelSingular || gettext('selecionado');
      const pluralLabel = selectedCounter.dataset.labelPlural || gettext('selecionados');
      const label = selectedCount === 1 ? singularLabel : pluralLabel;
      selectedCounter.textContent = `${selectedCount} ${label}`;

      if (!itemCheckboxes.length || selectedCount === 0) {
        selectPage.checked = false;
        selectPage.indeterminate = false;
      } else if (selectedCount === itemCheckboxes.length) {
        selectPage.checked = true;
        selectPage.indeterminate = false;
      } else {
        selectPage.checked = false;
        selectPage.indeterminate = true;
      }
    }

    const printBtn = this.resultsContainer.querySelector('[data-results-print-selected]');
    if (printBtn) {
      const hasSelection = selectedCount > 0;
      printBtn.disabled = !hasSelection;
      printBtn.classList.toggle('results-toolbar__icon-btn--print-ready', hasSelection);
    }
  }

}

document.addEventListener('DOMContentLoaded', () => {
  if (window.searchPageConfig) {
    window.searchPageManager = new SearchPageManager(window.searchPageConfig);
  }
});
