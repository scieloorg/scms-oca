/**
 * Toolbar CSV export: posts selected result rows to the citation-export API
 * with format ``csv``. Depends on ``CitationController`` for collecting
 * documents and posting the file download.
 * Exposed as ``window.SearchPage.ToolbarCsvExportController``.
 */
(function (global) {
  class ToolbarCsvExportController {
    constructor(ctx) {
      this.ctx = ctx;
    }

    setupToolbarCsvExport() {
      document.addEventListener('click', event => {
        const btn = event.target.closest('.js-toolbar-csv-export');
        if (btn) this.exportSelectedToCsv();
      });
    }

    async exportSelectedToCsv() {
      const docs = this.collectSelectedCitationDocuments();
      if (!docs.length) return;
      await this.postCsvFileDownload(docs);
    }

    collectSelectedCitationDocuments() {
      const checked = document.querySelectorAll('.result-item__select-input:checked');
      if (!checked.length) return [];

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

      return docs;
    }

    async postCsvFileDownload(documents) {
      const state = this.ctx.state;
      if (!documents?.length) return;

      const resp = await global.SearchPage.Utils.postJson(
        state.exportFilesEndpoint,
        { format: 'csv', documents },
        state.csrfToken,
      );
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = this.resolveCsvExportFilename(resp);
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    }

    resolveCsvExportFilename(response) {
      const header = response.headers.get('Content-Disposition') || '';
      const utf8Match = header.match(/filename\*=UTF-8''([^;]+)/i);
      if (utf8Match?.[1]) {
        return decodeURIComponent(utf8Match[1]);
      }
      const filenameMatch = header.match(/filename="?([^"]+)"?/i);
      if (filenameMatch?.[1]) return filenameMatch[1];
      return 'citation.csv';
    }
  }

  global.SearchPage = global.SearchPage || {};
  global.SearchPage.ToolbarCsvExportController = ToolbarCsvExportController;
})(typeof window !== 'undefined' ? window : this);
