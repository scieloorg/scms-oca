/**
 * Centralized state for the search page.
 * Reads initial values from config, URL params and localStorage.
 * Exposed as `window.SearchPage.State`.
 */
(function (global) {
  class SearchPageState {
    constructor(config) {
      const urlParams = new URLSearchParams(global.location.search);

      this.config = config || {};
      this.searchQuery = this.config.initialSearchQuery || '';
      this.advancedSearchQuery = this.config.initialAdvancedSearchQuery || '';
      this.advancedSearchError = this.config.initialAdvancedSearchError || '';
      this.searchClauses = this.config.initialSearchClauses || [];
      this.dataSourceName = this.config.dataSourceName || '';
      this.csrfToken = this.config.csrfToken || '';
      this.searchableFields = this.config.searchableFields || [];

      this.apiEndpoint = this.config.apiEndpoint || '/search/api/search-results-list/';
      this.citationStylesEndpoint =
        this.config.citationStylesEndpoint || '/search/api/citation-styles/';
      this.citationPreviewEndpoint =
        this.config.citationPreviewEndpoint || '/search/api/citation-preview/';
      this.citationCustomStyleEndpoint =
        this.config.citationCustomStyleEndpoint || '/search/api/citation-custom-style/';
      this.exportFilesEndpoint =
        this.config.exportFilesEndpoint || '/search/api/export-files/';

      this.currentSort = urlParams.get('sort') || 'desc';
      this.currentLimit = urlParams.get('limit') || '25';
      this.currentPage = parseInt(urlParams.get('page') || '1', 10) || 1;
      this.currentDisplayMode =
        global.localStorage.getItem('searchPageDisplayMode') || 'grid';

      this.currentCitationDocuments = [];
      this.citationDocuments = {};
      this.citationStylesLoaded = false;

      this.resultsSelectionState = {
        checkboxes: [],
        selectedCount: 0,
      };
    }

    syncCitationDocuments(documents) {
      this.citationDocuments =
        documents && typeof documents === 'object' ? documents : {};

      const scriptEl = document.getElementById('search-citation-documents');
      if (scriptEl) {
        scriptEl.textContent = JSON.stringify(this.citationDocuments);
      }
    }

    syncCitationDocumentsFromDom() {
      const scriptEl = document.getElementById('search-citation-documents');
      if (!scriptEl) {
        this.citationDocuments = {};
        return;
      }

      try {
        const parsed = JSON.parse(scriptEl.textContent);
        this.citationDocuments =
          parsed && typeof parsed === 'object' ? parsed : {};
      } catch {
        this.citationDocuments = {};
      }
    }

    getCitationDocument(citationKey) {
      if (citationKey == null) return null;
      const doc = this.citationDocuments[String(citationKey)];
      return doc && typeof doc === 'object' ? doc : null;
    }
  }

  global.SearchPage = global.SearchPage || {};
  global.SearchPage.State = SearchPageState;
})(typeof window !== 'undefined' ? window : this);
