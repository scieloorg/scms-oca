/**
 * Delegates result card interactions: language switcher, item/page
 * selection and the selection counter / print button state.
 * Exposed as `window.SearchPage.SelectionController`.
 */
(function (global) {
  class SelectionController {
    constructor(ctx) {
      this.ctx = ctx;
      this.resultsContainer = document.getElementById('results-container');
    }

    setupResultsSelectionDelegation() {
      if (
        !this.resultsContainer ||
        this.resultsContainer.dataset.searchPageSelectionBound === 'true'
      ) {
        return;
      }

      this.resultsContainer.addEventListener('click', event => {
        const languageButton = event.target.closest('[data-result-language]');
        if (!languageButton) return;

        const card = languageButton.closest('.result-card__inner');
        const languageCode = languageButton.dataset.resultLanguage;
        if (!card || !languageCode) return;

        this.setCardLanguage(card, languageCode);
      });

      this.resultsContainer.addEventListener('change', event => {
        const { target } = event;
        const selectionState = this.ctx.state.resultsSelectionState;

        if (target.id === 'results-select-page') {
          const itemCheckboxes = selectionState.checkboxes;
          itemCheckboxes.forEach(input => {
            input.checked = target.checked;
          });
          selectionState.selectedCount = target.checked ? itemCheckboxes.length : 0;
          this.updateResultsSelectionCounter();
          return;
        }

        if (target.classList.contains('result-item__select-input')) {
          const delta = target.checked ? 1 : -1;
          const nextCount = selectionState.selectedCount + delta;
          selectionState.selectedCount = Math.max(
            0,
            Math.min(nextCount, selectionState.checkboxes.length),
          );
          this.updateResultsSelectionCounter();
        }
      });

      this.resultsContainer.dataset.searchPageSelectionBound = 'true';
    }

    getActiveCardLanguage(card) {
      if (!card) return null;
      const active = card.querySelector(
        '[data-result-language].result-card__language--active',
      );
      const code = active?.dataset?.resultLanguage?.trim();
      return code || null;
    }

    citationDocumentWithCardLanguage(doc, card) {
      const languageCode = this.getActiveCardLanguage(card);
      if (!languageCode) return { ...doc };
      return { ...doc, language_code: languageCode };
    }

    setCardLanguage(card, languageCode) {
      card.querySelectorAll('[data-result-language]').forEach(button => {
        const isActive = button.dataset.resultLanguage === languageCode;
        button.classList.toggle('result-card__language--active', isActive);
        button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
      });

      const groups = new Map();
      card.querySelectorAll('[data-result-lang-variant]').forEach(node => {
        const key = node.parentElement;
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(node);
      });

      groups.forEach(nodes => {
        const hasMatch = nodes.some(n => n.dataset.resultLangVariant === languageCode);
        if (!hasMatch) return;
        nodes.forEach(n => {
          n.hidden = n.dataset.resultLangVariant !== languageCode;
        });
      });
    }

    refreshResultsSelectionState() {
      if (!this.resultsContainer) return;

      const itemCheckboxes = Array.from(
        this.resultsContainer.querySelectorAll('.result-item__select-input'),
      );
      const selectedCount = itemCheckboxes.filter(input => input.checked).length;
      this.ctx.state.resultsSelectionState = {
        checkboxes: itemCheckboxes,
        selectedCount,
      };
    }

    updateResultsSelectionCounter({ refresh = false } = {}) {
      if (!this.resultsContainer) return;
      if (refresh) {
        this.refreshResultsSelectionState();
      }

      const selectionState = this.ctx.state.resultsSelectionState;
      const selectPage = this.resultsContainer.querySelector('#results-select-page');
      const selectedCounter = this.resultsContainer.querySelector('#results-selected-counter');
      const itemCheckboxes = selectionState.checkboxes;
      const selectedCount = selectionState.selectedCount;

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

      const toolbarCiteBtn = this.resultsContainer.querySelector('.js-toolbar-cite-selected');
      if (toolbarCiteBtn) {
        toolbarCiteBtn.disabled = selectedCount === 0;
      }
    }
  }

  global.SearchPage = global.SearchPage || {};
  global.SearchPage.SelectionController = SelectionController;
})(typeof window !== 'undefined' ? window : this);
