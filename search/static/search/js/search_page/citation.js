/**
 * Controls the citation modal: open (single/bulk), style dropdown with
 * search, preview/custom rendering, clipboard copy and export downloads.
 * Exposed as `window.SearchPage.CitationController`.
 */
(function (global) {
  class CitationController {
    constructor(ctx) {
      this.ctx = ctx;
    }

    setupCitationUi() {
      if (document.body.dataset.citationBound === 'true') return;

      document.addEventListener('click', event => {
        const btn = event.target.closest('.js-open-citation-modal');
        if (btn) this.openCitationModal(btn);
      });

      document.addEventListener('click', event => {
        const btn = event.target.closest('.js-toolbar-cite-selected');
        if (btn) this.openBulkCitationModal();
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

    openCitationModal(button) {
      const state = this.ctx.state;
      const doc = state.getCitationDocument(button.dataset.citationKey);
      if (!doc) return;

      const card = button.closest('.result-card__inner');
      state.currentCitationDocuments = [
        this.ctx.selection.citationDocumentWithCardLanguage(doc, card),
      ];

      this.showCitationModal();
    }

    openBulkCitationModal() {
      const checked = document.querySelectorAll('.result-item__select-input:checked');
      if (!checked.length) return;

      const state = this.ctx.state;
      const docs = [];
      checked.forEach(cb => {
        const row = cb.closest('.result-item-row');
        if (!row) return;
        const doc = state.getCitationDocument(row.dataset.citationKey);
        if (!doc) return;
        const card = row.querySelector('.result-card__inner');
        docs.push(this.ctx.selection.citationDocumentWithCardLanguage(doc, card));
      });

      if (!docs.length) return;
      state.currentCitationDocuments = docs;
      this.showCitationModal();
    }

    showCitationModal() {
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

      global.SearchPage.Utils.showModal(modalEl);
      this.ensureCitationStyleOptions();
      this.loadCitationPreview();
    }

    async ensureCitationStyleOptions() {
      const state = this.ctx.state;
      const sel = document.getElementById('citation-custom-style');
      if (!sel || !state.citationStylesEndpoint || state.citationStylesLoaded) return;
      try {
        const resp = await fetch(state.citationStylesEndpoint);
        if (!resp.ok) return;
        const data = await resp.json();
        const styles = data.styles || [];
        const first = sel.querySelector('option[value=""]');
        const placeholder = first ? first.cloneNode(true) : null;
        sel.innerHTML = '';
        if (placeholder) {
          sel.appendChild(placeholder);
        } else {
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
        state.citationStylesLoaded = true;
      } catch (err) {
        console.error('Citation styles list error:', err);
      }
    }

    async loadCitationPreview() {
      const state = this.ctx.state;
      if (!state.currentCitationDocuments.length) return;
      try {
        const resp = await global.SearchPage.Utils.postJson(
          state.citationPreviewEndpoint,
          { documents: state.currentCitationDocuments },
          state.csrfToken,
        );
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
      if (
        !toggle ||
        !list ||
        !filter ||
        !sel ||
        toggle.dataset.citationDropdownInit === 'true'
      ) {
        return;
      }
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
        btn.className =
          'dropdown-item py-2 px-3 citation-style-dropdown__item text-start text-wrap';
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
      const inst = global.bootstrap?.Dropdown?.getInstance(toggle);
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
      const { escapeHtml } = global.SearchPage.Utils;
      const copyLabel = gettext('Copiar');
      const copyAria = gettext('Copiar citação');
      container.innerHTML = presets
        .map(
          p => `
      <div class="citation-modal__section">
        <h6 class="citation-modal__label">${escapeHtml(p.label)}</h6>
        <div class="citation-modal__copy-row">
          <textarea class="form-control citation-modal__textarea js-citation-copy-target" rows="5" readonly>${escapeHtml(p.citation)}</textarea>
          <button type="button" class="btn btn-outline-secondary btn-sm citation-modal__copy-btn js-citation-copy" aria-label="${escapeHtml(copyAria)}">${escapeHtml(copyLabel)}</button>
        </div>
      </div>
    `,
        )
        .join('');
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

    async loadCustomCitation(style) {
      const field = document.querySelector('.js-citation-custom');
      if (!field) return;
      if (!style) {
        field.value = '';
        return;
      }
      const state = this.ctx.state;
      try {
        const resp = await global.SearchPage.Utils.postJson(
          state.citationCustomStyleEndpoint,
          { documents: state.currentCitationDocuments, style },
          state.csrfToken,
        );
        const data = await resp.json();
        field.value = data.citation || '';
      } catch (err) {
        field.value = '';
        console.error('Custom citation error:', err);
      }
    }

    async downloadCitationExport(format) {
      const state = this.ctx.state;
      if (!state.currentCitationDocuments.length || !format) return;
      try {
        const resp = await global.SearchPage.Utils.postJson(
          state.exportFilesEndpoint,
          { format, documents: state.currentCitationDocuments },
          state.csrfToken,
        );
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

  global.SearchPage = global.SearchPage || {};
  global.SearchPage.CitationController = CitationController;
})(typeof window !== 'undefined' ? window : this);
