/**
 * Controller for the filter sidebar: toggle visibility and bridge with
 * the SearchGatewayFilterForm module.
 * Exposed as `window.SearchPage.SidebarController`.
 */
(function (global) {
  class SidebarController {
    constructor(ctx) {
      this.ctx = ctx;
      this.sidebarRoot = document.getElementById('search-sidebar-root');
      this.layoutRoot = document.getElementById('mainContent');
      this.headerRow = document.getElementById('search-header-row');
      this.sidebarToggleButton = document.getElementById('search-sidebar-toggle');
    }

    get sidebarForm() {
      return document.getElementById('search-filter-form');
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

      const storedState = global.localStorage.getItem(storageKey);
      applyState(storedState === 'true');

      toggleButton.addEventListener('click', () => {
        const nextHidden = !layoutRoot.classList.contains(hiddenClass);
        applyState(nextHidden);
        global.localStorage.setItem(storageKey, nextHidden ? 'true' : 'false');
      });
    }

    async initSidebar() {
      if (global.SearchGatewayFilterForm) {
        await global.SearchGatewayFilterForm.init(this.sidebarRoot || document);
      }
      this.bindSidebarEvents();
    }

    bindSidebarEvents() {
      const form = this.sidebarForm;
      if (!form) return;

      if (form.dataset.searchPageBound === 'true') return;

      form.addEventListener('submit', event => {
        event.preventDefault();
        this.ctx.resultsApi.applyFiltersAjax();
      });

      form.addEventListener('search-gateway:filters-changed', () => {
        this.ctx.resultsApi.applyFiltersAjax();
      });

      const resetButton = document.getElementById('search-filter-reset');
      if (resetButton) {
        resetButton.addEventListener('click', () => {
          if (global.SearchGatewayFilterForm) {
            global.SearchGatewayFilterForm.resetForm(form);
          } else {
            form.reset();
          }
          this.ctx.resultsApi.applyFiltersAjax();
        });
      }

      form.dataset.searchPageBound = 'true';
    }
  }

  global.SearchPage = global.SearchPage || {};
  global.SearchPage.SidebarController = SidebarController;
})(typeof window !== 'undefined' ? window : this);
