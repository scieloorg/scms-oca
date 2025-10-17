/*
    JavaScript for managing the filters menu in the indicators page.
    It dynamically builds filter fields based on the selected data source,
    handles form submissions, and updates the displayed charts accordingly.
    Depends on `helpers.js` for label formatting functions.
    Exposes a function to update the applied filters display.
*/

(function (window, document) {
  'use strict';

  var Indicators = window.Indicators || (window.Indicators = {});

  // Build and display filter fields based on the selected data source
  function buildFields(data, dataSource, countryUnit) {
    var fieldsByIndex = {
      openalex_works: [
        { key: 'source_index', label: 'Source Index' },
        { key: 'source_type', label: 'Source Type' },
        { key: 'publication_year', label: 'Publication Year' },
        { key: 'document_type', label: 'Document Type' },
        { key: 'document_language', label: 'Document Language' },
        { key: 'open_access', label: 'Open Access' },
        { key: 'access_type', label: 'Access Type' },
        { key: 'subject_area_level_0', label: 'Subject Area Level 0' },
        { key: 'subject_area_level_1', label: 'Subject Area Level 1' },
        { key: 'subject_area_level_2', label: 'Subject Area Level 2' },
        { key: 'region_world', label: 'Region - World (Author)' },
        { key: 'country', label: 'Country (Author)' }
      ],
      scielo: [
        { key: 'journal', label: 'Journal' },
        { key: 'publication_year', label: 'Publication Year' },
        { key: 'document_type', label: 'Document Type' },
        { key: 'document_language', label: 'Document Language' },
        { key: 'access_type', label: 'Access Type' },
        { key: 'country', label: 'Country (Author)' }
      ],
      social_production: [
        { key: 'publication_year', label: 'Publication Year' },
        { key: 'directory_type', label: 'Directory Type' },
        { key: 'action', label: 'Action' },
        { key: 'classification', label: 'Classification' },
        { key: 'institutions', label: 'Institutions' },
        { key: 'cities', label: 'Cities' },
        { key: 'states', label: 'States' },
        { key: 'practice', label: 'Practice' }
      ]
    };

    var normalizedDataSource = (dataSource || '').toLowerCase();
    var fields = fieldsByIndex[normalizedDataSource] || [];
    var fieldsContainer = document.getElementById('filters-fields');
    if (!fieldsContainer) return;

    fieldsContainer.innerHTML = '';

    fields.forEach(function (field) {
      if (!data[field.key]) {
        return;
      }

      var wrapper = document.createElement('div');
      var label = document.createElement('label');
      var selectId = field.key;

      if (normalizedDataSource === 'social_production') {
        selectId = field.key + '.enum';
      }

      label.setAttribute('for', selectId);
      label.textContent = field.label;

      var select = document.createElement('select');
      select.id = selectId;
      select.name = field.key;
      select.className = 'form-control';
      select.multiple = true;

      var seenValues = new Set();
      var optionItems = [];

      data[field.key].forEach(function (value) {
        var rawValue = (value === null || typeof value === 'undefined') ? '' : String(value);
        var optionValue = rawValue;
        var optionLabel = rawValue;

        if (field.key === 'open_access') {
          optionLabel = Number(rawValue) === 1 ? 'Yes' : 'No';
        } else if (field.key === 'country') {
          var normalizedCountry = rawValue.toUpperCase();
          optionValue = normalizedCountry;
          optionLabel = Indicators.getCountryLabel(normalizedCountry);
        } else if (field.key === 'document_language') {
          optionValue = rawValue;
          optionLabel = Indicators.getLanguageLabel(rawValue);
        }

        var dedupeKey = optionValue.toLowerCase();
        if (seenValues.has(dedupeKey)) {
          return;
        }
        seenValues.add(dedupeKey);

        optionItems.push({ value: optionValue, label: optionLabel, raw: rawValue });
      });

      if (field.key === 'country' || field.key === 'document_language') {
        optionItems.sort(function (a, b) {
          return a.label.localeCompare(b.label, 'en', { sensitivity: 'base' });
        });
      }

      optionItems.forEach(function (item) {
        var option = document.createElement('option');
        option.value = item.value;
        option.textContent = item.label;

        if (field.key === 'publication_year' && !isNaN(item.raw) && Number(item.raw) >= 2014) {
          option.selected = true;
        }

        select.appendChild(option);
      });

      wrapper.appendChild(label);
      wrapper.appendChild(select);

      if (field.key === 'document_language' || field.key === 'country') {
        var operatorWrapper = document.createElement('div');
        operatorWrapper.className = 'mt-2';

        var operatorLabel = document.createElement('label');
        var operatorId = field.key + '_operator';
        operatorLabel.setAttribute('for', operatorId);
        operatorLabel.textContent = field.key === 'document_language' ? 'Language Match Logic' : 'Country Match Logic';

        var operatorSelect = document.createElement('select');
        operatorSelect.id = operatorId;
        operatorSelect.name = operatorId;
        operatorSelect.className = 'form-control';

        var andOption = document.createElement('option');
        andOption.value = 'and';
        andOption.textContent = field.key === 'document_language'
          ? 'AND (document must include every selected language)'
          : 'AND (document must include every selected country)';
        andOption.selected = field.key === 'document_language';

        var orOption = document.createElement('option');
        orOption.value = 'or';
        orOption.textContent = field.key === 'document_language'
          ? 'OR (document may include any selected language)'
          : 'OR (document may include any selected country)';
        if (field.key === 'country') {
          orOption.selected = true;
        }

        operatorSelect.appendChild(andOption);
        operatorSelect.appendChild(orOption);

        operatorWrapper.appendChild(operatorLabel);
        operatorWrapper.appendChild(operatorSelect);
        wrapper.appendChild(operatorWrapper);
      }

      if (!(normalizedDataSource === 'openalex_works' && countryUnit === 'BR' && field.key === 'country')) {
        fieldsContainer.appendChild(wrapper);
      }

      setTimeout(function () {
        if (field.key === 'journal' || field.key === 'country' || field.key === 'document_language') {
          if (typeof window.$ !== 'undefined' && window.$.fn && window.$.fn.select2) {
            window.$('#' + select.id).select2({
              placeholder: 'Type to search...',
              allowClear: true,
              closeOnSelect: false,
              width: '100%',
              language: {
                noResults: function () { return 'No results found'; },
                searching: function () { return 'Searching...'; }
              }
            });
          }
        }
      }, 500);
    });

    var graphOptionsContainer = document.getElementById('graph-options-menu');
    if (graphOptionsContainer && (normalizedDataSource === 'scielo' || normalizedDataSource === 'social_production')) {
      var citationOption = graphOptionsContainer.querySelector('option[value="unit_citation"]');
      if (citationOption) {
        citationOption.remove();
      }
    }

    var breakdownSelect = document.getElementById('breakdown-variable-select');
    if (breakdownSelect) {
      breakdownSelect.innerHTML = '<option value="">Select a variable</option>';
      var breakdownVars = fields.map(function (item) { return item.key; }).filter(function (key) { return key !== 'publication_year'; });
      if (normalizedDataSource === 'scielo') {
        breakdownVars = breakdownVars.filter(function (key) { return key !== 'journal'; });
      }
      breakdownVars.forEach(function (key) {
        if (!data[key]) return;
        var optionLabel = (fields.find(function (item) { return item.key === key; }) || {}).label || key.replace(/_/g, ' ');
        var value = key;
        if (normalizedDataSource === 'social_production' && key !== 'publication_year') {
          value = key + '.enum';
        }
        breakdownSelect.innerHTML += '<option value="' + value + '">' + optionLabel + '</option>';
      });
    }

    var optionsLoading = document.getElementById('optionsLoading');
    if (optionsLoading) {
      optionsLoading.style.display = 'none';
    }

    Indicators.updateAppliedFiltersFromForm();
  }

  // Collect current filter selections from the form into an object
  function collectFormFilters(form) {
    var formData = new FormData(form);
    var filters = {};

    formData.forEach(function (value, key) {
      if (filters[key]) {
        if (Array.isArray(filters[key])) {
          filters[key].push(value);
        } else {
          filters[key] = [filters[key], value];
        }
      } else {
        filters[key] = value;
      }
    });

    var studyUnitSelect = document.getElementById('study-unit-select');
    if (studyUnitSelect) {
      var studyUnitValue = studyUnitSelect.value;
      if (studyUnitValue === 'unit_citation') {
        filters.study_unit = 'citation';
      } else if (studyUnitValue === 'unit_document') {
        filters.study_unit = 'document';
      }
    }

    var breakdownSelect = document.getElementById('breakdown-variable-select');
    if (breakdownSelect && breakdownSelect.value) {
      filters.breakdown_variable = breakdownSelect.value;
    }

    filters.data_source = window.data_source || '';
    filters.country_unit = window.country_unit || '';

    return filters;
  }

  // Show or hide chart containers based on current filters and render charts as needed
  function toggleChartContainers(filters, data, studyUnit) {
    var applied = document.getElementById('applied-filters');
    var mainDiv = document.getElementById('main-chart-div');
    var innerDiv = document.getElementById('inner-percentage-chart-div');
    var outerDiv = document.getElementById('outer-percentage-chart-div');

    if (applied) applied.classList.remove('d-none');
    if (mainDiv) mainDiv.classList.remove('d-none');

    var hasBreakdown = !!filters.breakdown_variable;
    if (innerDiv) innerDiv.classList.toggle('d-none', !hasBreakdown);

    var ignoredKeys = new Set([
      'publication_year',
      'study_unit',
      'breakdown_variable',
      'data_source',
      'country_unit',
      'document_language_operator',
      'country_operator'
    ]);
    var hasOtherFilters = Object.keys(filters).some(function (key) { return !ignoredKeys.has(key); });

    if (outerDiv) outerDiv.classList.toggle('d-none', !(hasBreakdown && hasOtherFilters));

    if (!hasBreakdown) {
      Indicators.destroyChartInstance(document.getElementById('inner-percentage-chart'));
    }
    if (!hasBreakdown || !hasOtherFilters) {
      Indicators.destroyChartInstance(document.getElementById('outer-percentage-chart'));
    }

    if (typeof Indicators.renderInnerPercentageChart === 'function') {
      Indicators.renderInnerPercentageChart(data, studyUnit);
    }

    if (typeof Indicators.renderOuterPercentageChart === 'function' && hasBreakdown && hasOtherFilters) {
      Indicators.renderOuterPercentageChart(data, studyUnit);
    }

    if (typeof Indicators.resizeVisibleCharts === 'function') {
      Indicators.resizeVisibleCharts();
    }
  }

  // Attach event handlers for form submission and reset button
  function attachEventHandlers() {
    var form = document.getElementById('filters-form');
    if (!form) return;

    var resetButton = document.getElementById('reset-filters-btn');
    if (resetButton) {
      resetButton.addEventListener('click', function () {
        form.reset();

        Array.from(form.querySelectorAll('select')).forEach(function (select) {
          if (typeof window.$ !== 'undefined' && window.$(select).hasClass('select2-hidden-accessible')) {
            window.$(select).val(null).trigger('change');
          } else {
            Array.from(select.options).forEach(function (opt) { opt.selected = false; });
          }
        });

        var pubYearSelect = (window.data_source || '').toLowerCase() === 'social_production'
          ? document.getElementById('publication_year.enum')
          : document.getElementById('publication_year');

        if (pubYearSelect) {
          var selectedYears = [];
          Array.from(pubYearSelect.options).forEach(function (opt) {
            if (!isNaN(opt.value) && Number(opt.value) >= 2014) {
              opt.selected = true;
              selectedYears.push(opt.value);
            }
          });
          if (typeof window.$ !== 'undefined' && window.$(pubYearSelect).hasClass('select2-hidden-accessible')) {
            window.$(pubYearSelect).val(selectedYears).trigger('change');
          }
        }

        var languageOperator = document.getElementById('document_language_operator');
        if (languageOperator) {
          languageOperator.value = 'and';
        }

        var countryOperator = document.getElementById('country_operator');
        if (countryOperator) {
          countryOperator.value = 'or';
        }

        Indicators.updateAppliedFiltersFromForm();
      });
    }

    form.addEventListener('submit', function (event) {
      event.preventDefault();

      var loadingDiv = document.getElementById('optionsLoading');
      var contentDiv = document.getElementById('mainContent');
      if (loadingDiv) loadingDiv.style.display = 'flex';
      if (contentDiv) contentDiv.style.opacity = '0.3';

      var filters = collectFormFilters(form);
      var studyUnit = filters.study_unit || 'document';

      Indicators.updateAppliedFiltersFromForm();

      fetch('/indicators/indicators/?data_source=' + encodeURIComponent(window.data_source || '') + '&country_unit=' + encodeURIComponent(window.country_unit || ''), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(filters)
      })
        .then(function (response) { return response.json(); })
        .then(function (data) {
          if (typeof Indicators.renderChart === 'function') {
            Indicators.renderChart(data, studyUnit);
          }
          toggleChartContainers(filters, data, studyUnit);
        })
        .finally(function () {
          if (loadingDiv) loadingDiv.style.display = 'none';
          if (contentDiv) contentDiv.style.opacity = '1';
        });
    });
  }

  // Initialize the filters menu by fetching available filter options and setting up event handlers
  function initializeFiltersMenu() {
    var dataSource = window.data_source || 'openalex_works';
    var countryUnit = window.country_unit || '';
    var url = '/indicators/filters/?data_source=' + encodeURIComponent(dataSource);

    if (countryUnit) {
      url += '&country_unit=' + encodeURIComponent(countryUnit);
    }

    fetch(url)
      .then(function (response) { return response.json(); })
      .then(function (data) {
        buildFields(data, dataSource, countryUnit);
      });

    attachEventHandlers();
  }

  document.addEventListener('DOMContentLoaded', initializeFiltersMenu);
})(window, document);
