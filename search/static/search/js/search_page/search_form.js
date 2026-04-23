/**
 * Controller for the main search form and advanced search rows.
 * Exposed as `window.SearchPage.SearchFormController`.
 */
(function (global) {
  class SearchFormController {
    constructor(ctx) {
      this.ctx = ctx;
      this.searchForm = document.getElementById('search-form');
    }

    setupSearchForm() {
      if (!this.searchForm) return;
      this.searchForm.addEventListener('submit', event => {
        event.preventDefault();
        this.ctx.state.searchClauses = this.getSearchClauses();
        this.ctx.resultsApi.applyFiltersAjax();
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

    restoreSearchClauses() {
      const clauses = this.ctx.state.searchClauses;
      if (!Array.isArray(clauses) || !clauses.length) return;

      const firstRow = document.querySelector('.advanced-search-row[data-row-index="0"]');
      if (firstRow && clauses[0]) {
        const clause = clauses[0];
        const fieldSelect = firstRow.querySelector('.search-field-select');
        const textInput = firstRow.querySelector('.search-text-input');
        if (fieldSelect) fieldSelect.value = clause.field || 'all';
        if (textInput) textInput.value = clause.text || '';
      }

      const container = document.getElementById('advanced-search-rows');
      if (!container) return;

      container.innerHTML = '';
      for (let index = 1; index < clauses.length; index += 1) {
        this.addSearchRow();
        const row = container.querySelector('.advanced-search-row:last-child');
        const clause = clauses[index];
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

    clearSearchQuery() {
      this.ctx.state.searchQuery = '';
      this.ctx.state.searchClauses = [];

      const firstRow = document.querySelector('.advanced-search-row[data-row-index="0"]');
      if (firstRow) {
        const fieldSelect = firstRow.querySelector('.search-field-select');
        const textInput = firstRow.querySelector('.search-text-input');
        if (fieldSelect) fieldSelect.value = 'all';
        if (textInput) textInput.value = '';
      }

      const extraRows = document.getElementById('advanced-search-rows');
      if (extraRows) extraRows.innerHTML = '';

      this.ctx.resultsApi.applyFiltersAjax();
    }
  }

  global.SearchPage = global.SearchPage || {};
  global.SearchPage.SearchFormController = SearchFormController;
})(typeof window !== 'undefined' ? window : this);
