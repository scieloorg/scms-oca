/**
 * Handles network requests for search results: builds query params,
 * manages loading overlay, renders response fragments and syncs state.
 * Exposed as `window.SearchPage.ResultsApi`.
 */
(function (global) {
  class ResultsApi {
    constructor(ctx) {
      this.ctx = ctx;
      this.resultsContainer = document.getElementById('results-container');
      this._filtersFetchAbortController = null;
    }

    buildSearchParams() {
      const params = new URLSearchParams();
      const state = this.ctx.state;

      if (this.ctx.searchForm.getActiveSearchMode() === 'advanced') {
        const advancedQuery = this.ctx.searchForm.getAdvancedSearchQuery();
        state.advancedSearchQuery = advancedQuery;
        if (advancedQuery) {
          params.set('advanced_search', advancedQuery);
        }
      } else {
        const clauses = this.ctx.searchForm.getSearchClauses();
        if (clauses.length > 0) {
          params.set('search_clauses', JSON.stringify(clauses));
        } else if (state.searchQuery) {
          params.set('search', state.searchQuery);
        }
      }

      if (state.dataSourceName) {
        params.set('index_name', state.dataSourceName);
      }

      const sidebarForm = this.ctx.sidebar.sidebarForm;
      const filters = global.SearchGatewayFilterForm
        ? global.SearchGatewayFilterForm.serializeForm(sidebarForm)
        : {};
      Object.entries(filters).forEach(([key, value]) => {
        if (Array.isArray(value)) {
          value.forEach(item => params.append(key, item));
          return;
        }
        params.append(key, value);
      });

      if (state.currentSort) {
        params.set('sort', state.currentSort);
      }

      if (state.currentLimit) {
        params.set('limit', state.currentLimit);
      }

      params.set('page', state.currentPage);

      return params;
    }

    ensureLoadingOverlay() {
      if (!this.resultsContainer) return null;
      let overlay = this.resultsContainer.querySelector('.results-container__loading');
      if (overlay) return overlay;

      overlay = document.createElement('div');
      overlay.className = 'results-container__loading';
      overlay.hidden = true;
      overlay.setAttribute('role', 'status');
      overlay.setAttribute('aria-live', 'polite');
      overlay.innerHTML = `
        <div class="results-container__loading-inner text-center p-4">
          <span class="search-loading-spinner search-loading-spinner--large" aria-hidden="true"></span>
          <p class="results-container__loading-text mb-0 mt-3">${this.getLoadingMessage()}</p>
        </div>`;
      this.resultsContainer.appendChild(overlay);
      return overlay;
    }

    getLoadingMessage() {
      if (typeof gettext === 'function') {
        return gettext('Loading...');
      }
      return 'Buscando...';
    }

    toggleSearchSubmitLoading(active) {
      const submitButtons = document.querySelectorAll('#search-form .search-header-card__submit');
      submitButtons.forEach(submitBtn => {
        if (active) {
          if (submitBtn.dataset.loadingOriginalHtml === undefined) {
            submitBtn.dataset.loadingOriginalHtml = submitBtn.innerHTML.trim();
          }
          submitBtn.disabled = true;
          submitBtn.setAttribute('aria-busy', 'true');
          const label = submitBtn.dataset.loadingOriginalHtml;
          submitBtn.innerHTML = `<span class="search-loading-spinner" aria-hidden="true"></span><span class="search-header-card__submit-label">${label}</span>`;
          return;
        }
        submitBtn.disabled = false;
        submitBtn.removeAttribute('aria-busy');
        if (submitBtn.dataset.loadingOriginalHtml !== undefined) {
          submitBtn.innerHTML = submitBtn.dataset.loadingOriginalHtml;
        }
      });
    }

    showLoading() {
      this.toggleSearchSubmitLoading(true);
      const overlay = this.ensureLoadingOverlay();
      if (!this.resultsContainer || !overlay) return;
      this.resultsContainer.classList.add('results-container--loading');
      this.resultsContainer.setAttribute('aria-busy', 'true');
      overlay.hidden = false;
    }

    hideLoading() {
      if (!this.resultsContainer) return;
      this.resultsContainer.classList.remove('results-container--loading');
      this.resultsContainer.setAttribute('aria-busy', 'false');
      const overlay = this.resultsContainer.querySelector('.results-container__loading');
      if (overlay) overlay.hidden = true;
      this.toggleSearchSubmitLoading(false);
    }

    renderResultsFragments(data) {
      const { replaceResultsRegion } = global.SearchPage.Utils;
      replaceResultsRegion(this.resultsContainer, 'results-toolbar-region', data.toolbar_html);
      replaceResultsRegion(this.resultsContainer, 'results-controls-region', data.controls_html);
      replaceResultsRegion(this.resultsContainer, 'results-list-region', data.results_list_html);
      replaceResultsRegion(
        this.resultsContainer,
        'results-pagination-region',
        data.pagination_html,
      );
    }

    async applyFiltersAjax(page = 1) {
      const state = this.ctx.state;
      state.currentPage = page;

      if (this._filtersFetchAbortController) {
        this._filtersFetchAbortController.abort();
      }
      this._filtersFetchAbortController = new AbortController();
      const { signal } = this._filtersFetchAbortController;

      this.showLoading();
      const params = this.buildSearchParams();

      try {
        const response = await fetch(`${state.apiEndpoint}?${params.toString()}`, { signal });
        const data = await response.json();

        if (!response.ok) {
          if (response.status === 400 && data.error_type === 'advanced_query') {
            this.ctx.searchForm.showAdvancedSearchError(data.error);
            return;
          }
          throw new Error(data.error || 'Network response was not ok');
        }

        this.ctx.searchForm.clearAdvancedSearchError();
        this.renderResultsFragments(data);
        state.syncCitationDocuments(data.citation_documents);
        this.ctx.resultsUi.setupResultsUi();

        const sidebarForm = this.ctx.sidebar.sidebarForm;
        if (sidebarForm && global.SearchGatewayFilterForm?.commitAppliedFilters) {
          global.SearchGatewayFilterForm.commitAppliedFilters(sidebarForm);
        }

        const url = new URL(global.location.href);
        url.search = params.toString();
        global.history.replaceState({}, '', url.toString());
      } catch (error) {
        if (error.name === 'AbortError') {
          return;
        }
        console.error('Error applying filters:', error);
        this.renderResultsFragments({
          toolbar_html: '',
          controls_html: '',
          results_list_html: `
            <div class="alert alert-danger" role="alert">
              ${gettext('Error loading results. Try again.')}
            </div>
          `,
          pagination_html: '',
        });
        state.syncCitationDocuments({});
      } finally {
        this.hideLoading();
      }
    }
  }

  global.SearchPage = global.SearchPage || {};
  global.SearchPage.ResultsApi = ResultsApi;
})(typeof window !== 'undefined' ? window : this);
