(function () {
  window.JournalMetrics = window.JournalMetrics || {};

  window.JournalMetrics.getConfigAttr = function (configElement, attrName, fallback = '') {
    if (!configElement) return fallback;
    const value = configElement.getAttribute(attrName);
    if (value === null || value === undefined || value === '') return fallback;
    return value;
  };

  window.JournalMetrics.focusSelect2SearchInput = function (event) {
    const targetId = event?.target?.id;
    if (!targetId) return;

    const searchInput = document.querySelector(`[aria-controls="select2-${targetId}-results"]`);
    if (searchInput) {
      searchInput.focus();
    }
  };
})();
