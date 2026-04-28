/**
 * Search page entrypoint.
 *
 * Assembles the per-responsibility controllers under `window.SearchPage.*`
 * into a single orchestrator. Each controller receives the manager as `ctx`
 * to share state and invoke peers. Public API preserved:
 *   - window.searchPageConfig (input)
 *   - window.searchPageManager (output)
 */
(function (global) {
  const SP = global.SearchPage || {};

  class SearchPageManager {
    constructor(config) {
      this.config = config || {};

      this.state = new SP.State(this.config);

      this.searchForm = new SP.SearchFormController(this);
      this.sidebar = new SP.SidebarController(this);
      this.resultsApi = new SP.ResultsApi(this);
      this.resultsUi = new SP.ResultsUiController(this);
      this.selection = new SP.SelectionController(this);
      this.citation = new SP.CitationController(this);
      this.csvExport = new SP.ToolbarCsvExportController(this);

      this.init();
    }

    async init() {
      this.searchForm.setupSearchForm();
      this.searchForm.setupAdvancedSearchUI();
      this.sidebar.setupSidebarToggle();
      this.resultsUi.setupGlobalResultsControlEvents();
      this.selection.setupResultsSelectionDelegation();
      this.state.syncCitationDocumentsFromDom();
      this.searchForm.restoreSearchClauses();
      await this.sidebar.initSidebar();
      this.resultsUi.setupResultsUi();
      this.citation.setupCitationUi();
      this.csvExport.setupToolbarCsvExport();
    }
  }

  global.SearchPage = SP;
  global.SearchPage.Manager = SearchPageManager;

  document.addEventListener('DOMContentLoaded', () => {
    if (global.searchPageConfig) {
      global.searchPageManager = new SearchPageManager(global.searchPageConfig);
    }
  });
})(typeof window !== 'undefined' ? window : this);
