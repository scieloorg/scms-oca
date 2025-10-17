/*
    JavaScript for updating the display of applied filters in the indicators page.
    It reads the selected options from the filters form and constructs a summary of the applied filters.
    The summary is displayed in a designated container, which is shown or hidden based on whether any filters are applied.
    Depends on `helpers.js` for label formatting functions.
    Exposes a function to update the applied filters display.
*/
(function (window, document) {
  'use strict';

  var Indicators = window.Indicators || (window.Indicators = {});

  // Update the applied filters display based on the current selections in the filters form
  function updateAppliedFiltersFromForm() {
    var container = document.getElementById('applied-filters');
    if (!container) return;

    var form = document.getElementById('filters-form');
    if (!form) return;

    var pieces = [];
    form.querySelectorAll('select').forEach(function (sel) {
      var selectedOptions = Array.from(sel.selectedOptions || []);
      if (!selectedOptions.length) {
        return;
      }

      if (sel.id === 'document_language_operator') {
        var languageSelect = form.querySelector('#document_language');
        var languageCount = languageSelect ? Array.from(languageSelect.selectedOptions || []).length : 0;
        if (languageCount < 2) {
          return;
        }
      }

      if (sel.id === 'country_operator') {
        var countrySelect = form.querySelector('#country');
        var countryCount = countrySelect ? Array.from(countrySelect.selectedOptions || []).length : 0;
        if (countryCount < 2) {
          return;
        }
      }

      var selectedTexts = selectedOptions.map(function (opt) { return opt.textContent; });
      if (!selectedTexts.length) {
        return;
      }

      var labelElement = form.querySelector('label[for="' + sel.id + '"]');
      var label = labelElement ? labelElement.textContent.trim() : sel.name;

      if (label === 'Publication Year') {
        var years = selectedTexts
          .map(function (text) { return parseInt(text, 10); })
          .filter(function (value) { return !isNaN(value); });
        if (years.length) {
          selectedTexts = [Indicators.yearsToRanges(years)];
        }
      }

      pieces.push(label + ': ' + selectedTexts.join(', '));
    });

    if (pieces.length) {
      container.classList.remove('d-none');
      container.innerHTML = '<strong>Applied Filters</strong>' + pieces.join(' | ');
    } else {
      container.classList.add('d-none');
      container.innerHTML = '';
    }
  }

  Indicators.updateAppliedFiltersFromForm = updateAppliedFiltersFromForm;
  window.updateAppliedFiltersFromForm = updateAppliedFiltersFromForm;
})(window, document);
