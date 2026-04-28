/**
 * Controller for the main search form and advanced search rows.
 * Exposed as `window.SearchPage.SearchFormController`.
 */
(function (global) {
  class SearchFormController {
    constructor(ctx) {
      this.ctx = ctx;
      this.searchForm = document.getElementById('search-form');
      this.modeButtons = document.querySelectorAll('.search-mode-btn');
      this.byFieldContainer = document.getElementById('search-mode-by-field-container');
      this.advancedContainer = document.getElementById('search-mode-advanced-container');
      this.guideWrapper = document.getElementById('advanced-guide-wrapper');
      this.advancedInput = document.getElementById('advanced-search-input');
      this.extraRows = document.getElementById('advanced-search-rows');
    }

    setupSearchForm() {
      if (!this.searchForm) return;

      this.modeButtons.forEach(btn => {
        btn.addEventListener('click', event => {
          this.setSearchMode(event.currentTarget.dataset.mode);
        });
      });

      this.searchForm.addEventListener('submit', event => {
        event.preventDefault();
        this.syncSearchStateFromForm();
        this.ctx.resultsApi.applyFiltersAjax();
      });
    }

    setupAdvancedSearchUI() {
      const btnAdd = document.getElementById('btn-add-field');
      const btnClear = document.getElementById('btn-clear');

      if (btnAdd) {
        btnAdd.addEventListener('click', () => this.addSearchRow());
      }
      if (btnClear) {
        btnClear.addEventListener('click', () => this.clearSearchQuery());
      }

      const btnSyntaxHelp = document.getElementById('btn-syntax-help');
      if (btnSyntaxHelp) {
        btnSyntaxHelp.addEventListener('click', () => this.toggleSyntaxGuide(btnSyntaxHelp));
      }

      this.extraRows.addEventListener('click', event => {
        if (event.target.closest('.btn-remove-row')) {
          this.removeSearchRow(event.target.closest('.btn-remove-row'));
        }
      });
    }

    getActiveSearchMode() {
      return document.querySelector('.search-mode-btn--active')?.dataset.mode || 'by_field';
    }

    setSearchMode(mode) {
      const activeMode = mode === 'advanced' ? 'advanced' : 'by_field';

      this.modeButtons.forEach(button => {
        button.classList.toggle('search-mode-btn--active', button.dataset.mode === activeMode);
      });

      this.byFieldContainer.style.display = activeMode === 'by_field' ? 'block' : 'none';
      this.advancedContainer.style.display = activeMode === 'advanced' ? 'block' : 'none';
      this.guideWrapper.style.display = activeMode === 'advanced' ? 'block' : 'none';
    }

    toggleSyntaxGuide(button) {
      const guide = document.getElementById('advanced-search-guide');

      guide.classList.toggle('advanced-search-guide--active');
      button.classList.toggle('search-header-card__action-link--active');
      this.searchForm.classList.toggle('search-header-card__search--with-guide');
    }

    syncSearchStateFromForm() {
      if (this.getActiveSearchMode() === 'advanced') {
        this.ctx.state.searchClauses = [];
        this.ctx.state.searchQuery = this.advancedInput.value.trim();
        return;
      }

      this.ctx.state.searchClauses = this.getSearchClauses();
      this.ctx.state.searchQuery = '';
    }

    restoreSearchClauses() {
      const clauses = this.ctx.state.searchClauses;
      const query = this.ctx.state.searchQuery;

      if (query && (!clauses || clauses.length === 0)) {
        this.advancedInput.value = (query === '*' || query === 'all') ? '' : query;
        this.setSearchMode('advanced');
        return;
      }

      this.setSearchMode('by_field');

      if (!Array.isArray(clauses) || !clauses.length) return;

      const firstRow = document.querySelector('.advanced-search-row[data-row-index="0"]');
      this.setRowValues(firstRow, clauses[0]);

      this.extraRows.innerHTML = '';
      for (let index = 1; index < clauses.length; index += 1) {
        this.addSearchRow();
        const row = this.extraRows.querySelector('.advanced-search-row:last-child');
        const clause = clauses[index];
        this.setRowValues(row, clause);
      }
    }

    getRowValues(row, defaultOperator = 'AND') {
      const operatorSelect = row.querySelector('.search-operator');
      const fieldSelect = row.querySelector('.search-field-select');
      const textInput = row.querySelector('.search-text-input');
      const text = textInput.value.trim();

      if (!text) return null;

      return {
        operator: operatorSelect ? operatorSelect.value : defaultOperator,
        field: fieldSelect.value,
        text,
      };
    }

    setRowValues(row, clause) {
      const operatorSelect = row.querySelector('.search-operator');
      const fieldSelect = row.querySelector('.search-field-select');
      const textInput = row.querySelector('.search-text-input');

      if (operatorSelect) operatorSelect.value = clause.operator || 'AND';
      fieldSelect.value = clause.field || 'all';
      textInput.value = clause.text || '';
    }

    getSearchClauses() {
      const clauses = [];

      const firstRow = document.querySelector('.advanced-search-row[data-row-index="0"]');
      const firstClause = this.getRowValues(firstRow, '');
      if (firstClause) clauses.push(firstClause);

      document.querySelectorAll('#advanced-search-rows .advanced-search-row').forEach(row => {
        const clause = this.getRowValues(row);
        if (clause) clauses.push(clause);
      });

      return clauses;
    }

    addSearchRow() {
      const template = document.getElementById('advanced-search-row-template');

      const clone = template.content.cloneNode(true);
      const row = clone.querySelector('.advanced-search-row');
      row.dataset.rowIndex = String(this.extraRows.children.length + 1);
      this.extraRows.appendChild(clone);
    }

    removeSearchRow(button) {
      const row = button?.closest('.advanced-search-row');
      if (row && row.parentElement?.id === 'advanced-search-rows') {
        row.remove();
      }
    }

    clearSearchQuery() {
      this.ctx.state.searchQuery = '';
      this.ctx.state.searchClauses = [];

      this.advancedInput.value = '';

      const firstRow = document.querySelector('.advanced-search-row[data-row-index="0"]');
      this.setRowValues(firstRow, { field: 'all', text: '' });

      this.extraRows.innerHTML = '';

      this.ctx.resultsApi.applyFiltersAjax();
    }
  }

  global.SearchPage = global.SearchPage || {};
  global.SearchPage.SearchFormController = SearchFormController;
})(typeof window !== 'undefined' ? window : this);
