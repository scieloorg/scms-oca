/**
 * Controls the results toolbar UI: sort, limit, pagination, display mode
 * and the print button. Also syncs toolbar state after each render.
 * Exposed as `window.SearchPage.ResultsUiController`.
 */
(function (global) {
  class ResultsUiController {
    constructor(ctx) {
      this.ctx = ctx;
    }

    setupGlobalResultsControlEvents() {
      if (document.body.dataset.searchPageControlsBound === 'true') return;

      document.addEventListener('change', event => {
        const sortSelect = event.target.closest('#results-sort-select');
        if (!sortSelect) return;
        this.ctx.state.currentSort = sortSelect.value || 'desc';
        this.ctx.resultsApi.applyFiltersAjax();
      });

      document.addEventListener('click', event => {
        const limitButton = event.target.closest('[data-results-limit-option]');
        if (!limitButton) return;

        document.querySelectorAll('[data-results-limit-option]').forEach(option => {
          option.classList.remove('results-controls__limit-option--active');
        });

        limitButton.classList.add('results-controls__limit-option--active');
        this.ctx.state.currentLimit = limitButton.textContent.trim() || '25';
        this.ctx.resultsApi.applyFiltersAjax();
      });

      document.addEventListener('click', event => {
        const pageButton = event.target.closest('[data-page]');
        if (!pageButton || pageButton.disabled) return;
        const page = parseInt(pageButton.dataset.page, 10);
        if (page) this.ctx.resultsApi.applyFiltersAjax(page);
      });

      document.addEventListener('click', event => {
        const modeButton = event.target.closest('[data-display-mode]');
        if (!modeButton) return;

        const mode = modeButton.dataset.displayMode;
        if (this.ctx.state.currentDisplayMode === mode) return;

        this.ctx.state.currentDisplayMode = mode;
        global.localStorage.setItem('searchPageDisplayMode', mode);
        this.applyDisplayMode();
        this.setupResultsUi();
      });

      document.addEventListener('click', event => {
        const printBtn = event.target.closest('[data-results-print-selected]');
        if (!printBtn || printBtn.disabled) return;
        if (global.SearchResultsPrint && typeof global.SearchResultsPrint.printSelectedCards === 'function') {
          global.SearchResultsPrint.printSelectedCards();
        }
      });

      document.body.dataset.searchPageControlsBound = 'true';
    }

    setupResultsUi() {
      const state = this.ctx.state;

      const sortSelect = document.getElementById('results-sort-select');
      if (sortSelect) {
        sortSelect.value = state.currentSort;
      }

      document.querySelectorAll('[data-results-limit-option]').forEach(option => {
        const isActive = option.textContent.trim() === state.currentLimit;
        option.classList.toggle('results-controls__limit-option--active', isActive);
      });

      document.querySelectorAll('[data-display-mode]').forEach(btn => {
        const isActive = btn.dataset.displayMode === state.currentDisplayMode;
        btn.classList.toggle('results-toolbar__icon-btn--active', isActive);
        btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
      });

      this.applyDisplayMode();
      this.ctx.selection.updateResultsSelectionCounter({ refresh: true });
    }

    applyDisplayMode() {
      const resultsList = document.getElementById('results-list');
      if (!resultsList) return;

      resultsList.classList.toggle(
        'results-list--lean',
        this.ctx.state.currentDisplayMode === 'list',
      );
    }
  }

  global.SearchPage = global.SearchPage || {};
  global.SearchPage.ResultsUiController = ResultsUiController;
})(typeof window !== 'undefined' ? window : this);
