/*
    JavaScript for helper functions used across the indicators page.
    It includes functions for formatting country and language labels using the Intl API when available,
    as well as fallback mappings for common codes.
    It also provides functions to ensure breakdown labels are user-friendly and to convert lists of years into ranges.
    Exposes these functions via the global `Indicators` object.
*/
(function (window) {
  'use strict';

  var Indicators = window.Indicators || (window.Indicators = {});

  var hasIntlDisplay = typeof Intl !== 'undefined' && typeof Intl.DisplayNames === 'function';
  var countryDisplay = hasIntlDisplay ? new Intl.DisplayNames(['en'], { type: 'region' }) : null;
  var languageDisplay = hasIntlDisplay ? new Intl.DisplayNames(['en'], { type: 'language' }) : null;

  var fallbackCountryNames = {
    BR: 'Brazil', US: 'United States', GB: 'United Kingdom', PT: 'Portugal', ES: 'Spain',
    FR: 'France', DE: 'Germany', AR: 'Argentina', MX: 'Mexico', CA: 'Canada'
  };

  var fallbackLanguageNames = {
    en: 'English', pt: 'Portuguese', es: 'Spanish', fr: 'French', de: 'German'
  };

  // Returns a user-friendly label for a given country code.
  function getCountryLabel(code) {
    if (!code) return '';
    var normalized = String(code).toUpperCase();
    var label = countryDisplay ? countryDisplay.of(normalized) : null;
    return label || fallbackCountryNames[normalized] || normalized;
  }

  // Returns a user-friendly label for a given language code, handling BCP 47 format and region subtags.
  function getLanguageLabel(code) {
    if (!code) return '';
    var normalized = String(code).trim();
    if (!normalized) return '';

    var bcp47 = normalized.replace(/_/g, '-');
    var parts = bcp47.split('-');
    var languagePart = parts[0].toLowerCase();
    var regionPart = parts.length > 1 ? parts[1].toUpperCase() : null;

    var label = languageDisplay ? languageDisplay.of(languagePart) : null;
    if (!label) label = fallbackLanguageNames[languagePart];
    if (!label) label = languagePart.toUpperCase();
    else label = label.charAt(0).toUpperCase() + label.slice(1);

    if (regionPart) {
      var regionLabel = getCountryLabel(regionPart);
      label += ' (' + (regionLabel || regionPart) + ')';
    }

    return label;
  }

  // Formats a breakdown key based on the normalized variable type (e.g., country or language).
  function formatBreakdownLabel(rawKey, normalizedVariable) {
    if (rawKey === null || typeof rawKey === 'undefined') {
      return '';
    }
    var text = String(rawKey);
    if (!text) {
      return '';
    }

    if (normalizedVariable === 'document_language') {
      return getLanguageLabel(text) || text.toUpperCase();
    }

    if (normalizedVariable === 'country') {
      return getCountryLabel(text) || text.toUpperCase();
    }

    return text;
  }

  // Ensures that breakdown keys and series names in the data have user-friendly labels.
  function ensureFriendlyBreakdownLabels(data) {
    if (!data || !data.breakdown_variable || data.__friendlyLabelsApplied) {
      return;
    }

    var normalizedVariable = String(data.breakdown_variable).replace(/\.enum$/, '');
    if (normalizedVariable !== 'document_language' && normalizedVariable !== 'country') {
      data.__friendlyLabelsApplied = true;
      return;
    }

    var friendlyMap = {};
    if (Array.isArray(data.breakdown_keys)) {
      data.breakdown_keys.forEach(function (key) {
        var keyStr = String(key);
        friendlyMap[keyStr] = formatBreakdownLabel(keyStr, normalizedVariable);
      });
      data.breakdown_keys = data.breakdown_keys.map(function (key) {
        var keyStr = String(key);
        return friendlyMap[keyStr] || formatBreakdownLabel(keyStr, normalizedVariable);
      });
    }

    if (Array.isArray(data.series)) {
      data.series = data.series.map(function (series) {
        var nameStr = String(series.name);
        if (!friendlyMap[nameStr]) {
          friendlyMap[nameStr] = formatBreakdownLabel(nameStr, normalizedVariable);
        }
        var cloned = Object.assign({}, series);
        cloned.name = friendlyMap[nameStr];
        return cloned;
      });
    }

    data.__friendlyLabelsApplied = true;
  }

  // Converts a list of years into a string of ranges (e.g., [2001, 2002, 2003, 2005] -> "2001 to 2003, 2005").
  function yearsToRanges(years) {
    if (!Array.isArray(years) || years.length === 0) return '';

    var uniq = Array.from(new Set(years.map(Number))).sort(function (a, b) { return a - b; });

    var ranges = [];
    var start = uniq[0], end = uniq[0];

    for (var i = 1; i < uniq.length; i += 1) {
      var y = uniq[i];
      if (y === end + 1) {
        end = y;
      } else {
        ranges.push(start === end ? String(start) : start + ' to ' + end);
        start = end = y;
      }
    }
    ranges.push(start === end ? String(start) : start + ' to ' + end);
    return ranges.join(', ');
  }

  // Safely disposes of an existing ECharts instance while removing any resize handler.
  function destroyChartInstance(container) {
    if (!container) {
      return;
    }

    if (container._chartResizeHandler) {
      window.removeEventListener('resize', container._chartResizeHandler);
      container._chartResizeHandler = null;
    }

    if (container._chartInstance) {
      container._chartInstance.dispose();
      container._chartInstance = null;
    }
  }

  // Initializes a fresh ECharts instance, keeping a resize handler reference for cleanup.
  function initChartInstance(container) {
    if (!container || typeof window.echarts === 'undefined') {
      return null;
    }

    destroyChartInstance(container);

    var chart = window.echarts.init(container);
    container._chartInstance = chart;

    var resizeHandler = function () { chart.resize(); };
    container._chartResizeHandler = resizeHandler;
    window.addEventListener('resize', resizeHandler);

    return chart;
  }

  Indicators.getCountryLabel = getCountryLabel;
  Indicators.getLanguageLabel = getLanguageLabel;
  Indicators.formatBreakdownLabel = formatBreakdownLabel;
  Indicators.ensureFriendlyBreakdownLabels = ensureFriendlyBreakdownLabels;
  Indicators.yearsToRanges = yearsToRanges;
  Indicators.destroyChartInstance = destroyChartInstance;
  Indicators.initChartInstance = initChartInstance;
})(window);
