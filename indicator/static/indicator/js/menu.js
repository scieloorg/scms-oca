function getScopeFilterFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const value = params.get('scope');
  return value ? String(value).trim() : '';
}

function syncScopeFilterIntoForm(menuForm) {
  const scopeFromUrl = getScopeFilterFromUrl();
  if (!scopeFromUrl) return;

  const scopeSelect = menuForm.querySelector('select[name="scope"]');
  if (!scopeSelect) return;

  const hasSelectedScope = Array.from(scopeSelect.selectedOptions || []).some(option => option.value);
  if (hasSelectedScope) return;

  const hasScopeOption = Array.from(scopeSelect.options).some(option => option.value === scopeFromUrl);
  if (!hasScopeOption) {
    const dynamicOption = new Option(scopeFromUrl, scopeFromUrl, false, false);
    scopeSelect.add(dynamicOption);
  }

  if (window.jQuery && window.jQuery(scopeSelect).hasClass('select2-hidden-accessible')) {
    window.jQuery(scopeSelect).val([scopeFromUrl]).trigger('change');
  } else {
    scopeSelect.value = scopeFromUrl;
  }
}

function normalizeStudyUnit(studyUnit, fallback = 'document') {
  const normalized = String(studyUnit || '').trim().toLowerCase();
  if (normalized === 'journal') return 'source';
  if (['document', 'source', 'journal_metrics'].includes(normalized)) {
    return normalized;
  }
  return fallback;
}

function buildIndicatorRedirectUrl({ indicatorHomeUrl, isJournalMetricsPage, studyUnit, scopeValue }) {
  const params = isJournalMetricsPage
    ? new URLSearchParams()
    : new URLSearchParams(window.location.search);

  params.set('study_unit', normalizeStudyUnit(studyUnit, 'document'));
  params.delete('return_study_unit');

  if (scopeValue) {
    params.set('scope', scopeValue);
  } else {
    params.delete('scope');
  }

  const query = params.toString();
  return query ? `${indicatorHomeUrl}?${query}` : indicatorHomeUrl;
}

function buildJournalMetricsRedirectUrl({ journalMetricsUrl, currentStudyUnit }) {
  const params = new URLSearchParams();
  params.set('return_study_unit', ['document', 'source'].includes(currentStudyUnit) ? currentStudyUnit : 'source');

  const query = params.toString();
  return query ? `${journalMetricsUrl}?${query}` : journalMetricsUrl;
}

async function populateScopeSelectOptions(selectIndexScope, { scopeDataSource, currentScopeFilter, allScopesLabel }) {
  if (!selectIndexScope) return;

  selectIndexScope.innerHTML = '';
  const allOption = document.createElement('option');
  allOption.value = '';
  allOption.textContent = allScopesLabel || 'All scopes';
  selectIndexScope.appendChild(allOption);

  try {
    const data = await fetchFilters(scopeDataSource, {
      fields: 'scope',
      refresh: '1',
    });
    const scopeOptions = Array.isArray(data?.scope) ? data.scope : [];

    const seen = new Set();
    scopeOptions.forEach(option => {
      const optionValue = String(option?.key ?? '').trim();
      if (!optionValue || seen.has(optionValue)) return;
      seen.add(optionValue);

      const optionLabel = String(option?.label ?? optionValue);
      const selectOption = document.createElement('option');
      selectOption.value = optionValue;
      selectOption.textContent = optionLabel;
      selectIndexScope.appendChild(selectOption);
    });
  } catch (error) {
    console.error('Error loading scope options', error);
  }

  if (!currentScopeFilter) {
    selectIndexScope.value = '';
    return;
  }

  const hasCurrentScope = Array.from(selectIndexScope.options).some(option => option.value === currentScopeFilter);
  if (!hasCurrentScope) {
    const dynamicOption = document.createElement('option');
    dynamicOption.value = currentScopeFilter;
    dynamicOption.textContent = currentScopeFilter;
    selectIndexScope.appendChild(dynamicOption);
  }
  selectIndexScope.value = currentScopeFilter;
}

function initScopeControls() {
  const scopeControlsRoot = document.getElementById('scope-controls');
  if (!scopeControlsRoot) return;

  const scopeFilterForm = document.getElementById('scope-filter-form');
  const selectIndexScope = document.getElementById('selectIndexScope');
  const hasScopeFilterControls = !!(scopeFilterForm && selectIndexScope);

  const studyUnitForm = document.getElementById('study-unit-form');
  const selectStudyUnit = document.getElementById('selectStudyUnit');
  const currentDataSource = String(scopeControlsRoot.dataset.dataSource || 'scientific').trim();
  const isJournalMetricsPage = currentDataSource === 'journal_metrics';
  const scopeDataSource = isJournalMetricsPage ? 'world' : currentDataSource;
  const indicatorHomeUrl = scopeControlsRoot.dataset.indicatorHomeUrl || '/indicators/';
  const journalMetricsUrl = scopeControlsRoot.dataset.journalMetricsUrl || '/indicators/journal-metrics/';
  const allScopesLabel = scopeControlsRoot.dataset.allScopesLabel || 'All scopes';
  const currentQueryParams = new URLSearchParams(window.location.search);
  const currentScopeFilter = String(currentQueryParams.get('scope') || '').trim();
  const returnStudyUnitParam = (currentQueryParams.get('return_study_unit') || '').trim().toLowerCase();
  const returnStudyUnit = ['document', 'source'].includes(returnStudyUnitParam)
    ? returnStudyUnitParam
    : 'source';
  const currentStudyUnit = normalizeStudyUnit(
    scopeControlsRoot.dataset.studyUnit,
    isJournalMetricsPage ? 'journal_metrics' : 'document',
  );

  if (selectStudyUnit) {
    const hasOption = Array.from(selectStudyUnit.options).some(option => option.value === currentStudyUnit);
    if (hasOption) {
      selectStudyUnit.value = currentStudyUnit;
    }
  }

  if (studyUnitForm && selectStudyUnit) {
    studyUnitForm.addEventListener('submit', event => {
      event.preventDefault();

      const selectedStudyUnit = normalizeStudyUnit(selectStudyUnit.value, currentStudyUnit);
      const selectedScope = hasScopeFilterControls
        ? String(selectIndexScope.value || '').trim()
        : currentScopeFilter;
      const redirectUrl = selectedStudyUnit === 'journal_metrics'
        ? buildJournalMetricsRedirectUrl({
            journalMetricsUrl,
            currentStudyUnit,
          })
        : buildIndicatorRedirectUrl({
            indicatorHomeUrl,
            isJournalMetricsPage,
            studyUnit: selectedStudyUnit,
            scopeValue: selectedScope,
          });
      window.location.assign(redirectUrl);
    });

    selectStudyUnit.addEventListener('change', () => {
      studyUnitForm.requestSubmit();
    });
  }

  if (!hasScopeFilterControls) return;

  scopeFilterForm.addEventListener('submit', event => {
    event.preventDefault();

    const selectedScope = String(selectIndexScope.value || '').trim();
    const redirectUrl = isJournalMetricsPage
      ? buildIndicatorRedirectUrl({
          indicatorHomeUrl,
          isJournalMetricsPage,
          studyUnit: returnStudyUnit,
          scopeValue: selectedScope,
        })
      : buildIndicatorRedirectUrl({
          indicatorHomeUrl,
          isJournalMetricsPage,
          studyUnit: currentStudyUnit,
          scopeValue: selectedScope,
        });
    window.location.assign(redirectUrl);
  });

  selectIndexScope.addEventListener('change', () => {
    scopeFilterForm.requestSubmit();
  });

  populateScopeSelectOptions(selectIndexScope, {
    scopeDataSource,
    currentScopeFilter,
    allScopesLabel,
  });
}

function initIndicatorForm(dataSource, studyUnit) {
  const menuForm = document.getElementById('menu-form');
  if (!menuForm) return;

  const submitButton = document.getElementById('menu-submit');
  const resetButton = document.getElementById('menu-reset');
  const chartErrorContainerId = 'indicator-chart-error';

  const removeChartError = () => {
    const existing = document.getElementById(chartErrorContainerId);
    if (existing) {
      existing.remove();
    }
  };

  const showChartError = (message) => {
    const mainContent = document.getElementById('mainContent');
    if (!mainContent) return;

    removeChartError();

    const errorDiv = document.createElement('div');
    errorDiv.id = chartErrorContainerId;
    errorDiv.className = 'alert alert-danger shadow-sm mb-3 mt-2';
    errorDiv.role = 'alert';
    errorDiv.textContent = message || gettext('Error loading indicator data.');
    mainContent.prepend(errorDiv);
  };

  // Handler for form submission
  const handleFormSubmit = (event) => {
    event.preventDefault();
    submitButton.disabled = true;

    syncScopeFilterIntoForm(menuForm);

    // Create FormData object from the form
    const formData = new FormData(menuForm);

    // Collect filters from the form data
    const filters = collectFiltersFromForm(formData);
    const scopeFromUrl = getScopeFilterFromUrl();
    const existingScope = filters.scope;
    const hasScopeInFilters = Array.isArray(existingScope)
      ? existingScope.some(value => String(value || '').trim())
      : !!String(existingScope || '').trim();
    if (!hasScopeInFilters && scopeFromUrl) {
      filters.scope = scopeFromUrl;
    }

    // Extract breakdown variable
    const breakdownVariable = formData.get('breakdown_variable');

    // Prepare payload for the POST request
    const payload = {
      breakdown_variable: breakdownVariable,
      filters: filters,
      study_unit: studyUnit
    };

    // Send POST request to fetch data
    fetch(`/indicators/data/?data_source=${dataSource}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': formData.get('csrfmiddlewaretoken'),
      },
      body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
      if (!data || data.error) {
        showChartError((data && data.error) || gettext('Error loading indicator data.'));
        clearGraphsContainer();
        clearAppliedFiltersContainer();
        return;
      }

      if (!Array.isArray(data.years)) {
        showChartError(gettext('Unexpected response while loading indicator data.'));
        clearGraphsContainer();
        clearAppliedFiltersContainer();
        return;
      }

      removeChartError();

      // Standardize series names before rendering
      standardizeIndicatorSeriesNames(data);

      // Update applied filters display
      updateAppliedFiltersDisplay();

      // Render charts or tables based on data source
      renderChartsContainer(data, dataSource, studyUnit, formData.get('csrfmiddlewaretoken'));
    })
    .catch(error => {
      console.error('Error:', error);
      showChartError(gettext('Error loading indicator data.'));
      clearGraphsContainer();
      clearAppliedFiltersContainer();
    })
    .finally(() => {
      submitButton.disabled = false;
    });
  };

  // Handler for the reset button
  const handleFormReset = (event) => {
    event.preventDefault();
    const resetUrl = `${window.location.pathname}${window.location.search}`;
    window.location.assign(resetUrl);
  };

  // Attach event listeners
  menuForm.addEventListener('submit', handleFormSubmit);
  if (resetButton) {
    resetButton.addEventListener('click', handleFormReset);
  }

  let initialRenderTriggered = false;
  const hasVisibleCharts = () => {
    const chartIds = [
      'periodicals-chart-div',
      'docs-chart-div',
      'citations-chart-div',
      'citations-per-doc-chart-div',
      'cited-docs-chart-div',
      'pct-cited-docs-chart-div',
    ];
    return chartIds.some(id => {
      const el = document.getElementById(id);
      return el && !el.classList.contains('d-none');
    });
  };

  const onFiltersReady = (event) => {
    const readyDataSource = event?.detail?.dataSource;
    if (readyDataSource && readyDataSource !== dataSource) return;
    triggerInitialRender();
  };

  const triggerInitialRender = () => {
    if (initialRenderTriggered || hasVisibleCharts()) return;
    initialRenderTriggered = true;
    document.removeEventListener('indicator:filters-ready', onFiltersReady);
    menuForm.requestSubmit();
  };

  // Prefer waiting for filters/selects initialization; fallback to timeout.
  document.addEventListener('indicator:filters-ready', onFiltersReady);
  window.setTimeout(triggerInitialRender, 1800);
}

document.addEventListener('DOMContentLoaded', () => {
  initScopeControls();
});

// Django JS i18n fallback (jsi18n usually loads this)
if (typeof window !== 'undefined' && typeof window.gettext !== 'function') {
  window.gettext = function (msgid) { return msgid; };
}

function renderChartsContainer(data, dataSource, studyUnit, csrfMiddlewareToken) {
  const breakdownVariable = data.breakdown_variable;
  const isSourceStudyUnit = studyUnit === 'source' || studyUnit === 'journal';
  const relativeMetrics = data.relative_metrics || {};
  const relativeMetricsSection = document.getElementById('relative-metrics-section');
  const relativeChartsDivIds = [
    'periodicals-share-chart-div',
    'docs-share-chart-div',
    'citations-share-chart-div',
    'citations-per-doc-share-chart-div',
    'cited-docs-share-chart-div',
    'pct-cited-docs-share-chart-div',
  ];
  const hideRelativeCharts = () => {
    relativeChartsDivIds.forEach(chartDivId => {
      const el = document.getElementById(chartDivId);
      if (el) {
        el.classList.add('d-none');
      }
    });
  };
  const hasVisibleRelativeCharts = () => relativeChartsDivIds.some(chartDivId => {
    const el = document.getElementById(chartDivId);
    return el && !el.classList.contains('d-none');
  });
  const hasComparativeFilters = Array.isArray(relativeMetrics.compared_filters)
    && relativeMetrics.compared_filters.length > 0;
  const showRelativeMetrics = !!relativeMetrics.enabled && hasComparativeFilters;

  const breakdownSelect = document.querySelector('#menu-form select[name="breakdown_variable"]');
  const breakdownText = breakdownSelect && breakdownSelect.value
    ? (breakdownSelect.options[breakdownSelect.selectedIndex]?.textContent || '').trim()
    : '';
  const breakdownSubtitle = breakdownText
    ? `${gettext('per Year')} ${gettext('by')} ${breakdownText}`
    : '';

  if (isSourceStudyUnit) {
    window.Indicators.renderChart({
      chartId: 'periodicals-chart',
      chartDivId: 'periodicals-chart-div',
      data: data,
      seriesType: 'Periodicals',
      title: gettext('Unique Sources'),
      subtitle: breakdownSubtitle,
    });

    window.Indicators.renderChart({
      chartId: 'docs-chart',
      chartDivId: 'docs-chart-div',
      data: data,
      seriesType: 'Documents per Periodical',
      title: gettext('Avg Documents per Source'),
      subtitle: breakdownSubtitle,
    });

    window.Indicators.renderChart({
      chartId: 'citations-chart',
      chartDivId: 'citations-chart-div',
      data: data,
      seriesType: 'Citations per Periodical',
      title: gettext('Avg Citations per Source'),
      subtitle: breakdownSubtitle,
    });

    window.Indicators.renderChart({
      chartId: 'citations-per-doc-chart',
      chartDivId: 'citations-per-doc-chart-div',
      data: data,
      seriesType: 'Cited Documents per Periodical',
      title: gettext('Avg Cited Documents per Source'),
      subtitle: breakdownSubtitle,
    });

    window.Indicators.renderChart({
      chartId: 'pct-cited-docs-chart',
      chartDivId: 'pct-cited-docs-chart-div',
      data: data,
      seriesType: 'Percent Periodicals With Cited Docs',
      title: gettext('% Sources With ≥1 Cited Document'),
      subtitle: breakdownSubtitle,
    });
  } else {
    // Render documents chart
    window.Indicators.renderChart({
      chartId: 'docs-chart',
      chartDivId: 'docs-chart-div',
      data: data,
      seriesType: 'Documents',
      title: gettext('Total Documents'),
      subtitle: breakdownSubtitle,
    });

    // Render citations chart
    window.Indicators.renderChart({
      chartId: 'citations-chart',
      chartDivId: 'citations-chart-div',
      data: data,
      seriesType: 'Citations',
      title: gettext('Total Citations'),
      subtitle: breakdownSubtitle,
    });

    // Render citations per document chart
    window.Indicators.renderChart({
      chartId: 'citations-per-doc-chart',
      chartDivId: 'citations-per-doc-chart-div',
      data: data,
      seriesType: 'Citations per Document',
      title: gettext('Citations per Document'),
      subtitle: breakdownSubtitle,
    });

    // Render cited documents chart
    window.Indicators.renderChart({
      chartId: 'cited-docs-chart',
      chartDivId: 'cited-docs-chart-div',
      data: data,
      seriesType: 'Cited Documents',
      title: gettext('Cited Documents (≥1 citation)'),
      subtitle: breakdownSubtitle,
    });

    // Render % docs with citations chart
    window.Indicators.renderChart({
      chartId: 'pct-cited-docs-chart',
      chartDivId: 'pct-cited-docs-chart-div',
      data: data,
      seriesType: 'Percent Docs With Citations',
      title: gettext('% Documents With ≥1 Citation'),
      subtitle: breakdownSubtitle,
    });
  }

  hideRelativeCharts();
  if (!showRelativeMetrics) {
    if (relativeMetricsSection) {
      relativeMetricsSection.classList.add('d-none');
    }
    return;
  }

  if (relativeMetricsSection) {
    relativeMetricsSection.classList.remove('d-none');
  }

  const relativeSubtitle = gettext('Per year, filtered vs total baseline');
  if (isSourceStudyUnit) {
    window.Indicators.renderChart({
      chartId: 'periodicals-share-chart',
      chartDivId: 'periodicals-share-chart-div',
      data: data,
      seriesType: 'Periodicals Share',
      title: gettext('Unique Sources Share (%)'),
      subtitle: relativeSubtitle,
      disableBreakdown: true,
      forcePercentAxis: true,
    });

    window.Indicators.renderChart({
      chartId: 'docs-share-chart',
      chartDivId: 'docs-share-chart-div',
      data: data,
      seriesType: 'Documents per Source Share',
      title: gettext('Documents per Source Share (%)'),
      subtitle: relativeSubtitle,
      disableBreakdown: true,
      forcePercentAxis: true,
    });

    window.Indicators.renderChart({
      chartId: 'citations-share-chart',
      chartDivId: 'citations-share-chart-div',
      data: data,
      seriesType: 'Citations per Source Share',
      title: gettext('Citations per Source Share (%)'),
      subtitle: relativeSubtitle,
      disableBreakdown: true,
      forcePercentAxis: true,
    });

    window.Indicators.renderChart({
      chartId: 'citations-per-doc-share-chart',
      chartDivId: 'citations-per-doc-share-chart-div',
      data: data,
      seriesType: 'Cited Documents per Source Share',
      title: gettext('Cited Documents per Source Share (%)'),
      subtitle: relativeSubtitle,
      disableBreakdown: true,
      forcePercentAxis: true,
    });

    window.Indicators.renderChart({
      chartId: 'pct-cited-docs-share-chart',
      chartDivId: 'pct-cited-docs-share-chart-div',
      data: data,
      seriesType: 'Percent Sources With Cited Docs Share',
      title: gettext('% Sources With ≥1 Cited Document Share (%)'),
      subtitle: relativeSubtitle,
      disableBreakdown: true,
      forcePercentAxis: true,
    });
    if (!hasVisibleRelativeCharts() && relativeMetricsSection) {
      relativeMetricsSection.classList.add('d-none');
    }
    return;
  }

  window.Indicators.renderChart({
    chartId: 'docs-share-chart',
    chartDivId: 'docs-share-chart-div',
    data: data,
    seriesType: 'Documents Share',
    title: gettext('Documents Share (%)'),
    subtitle: relativeSubtitle,
    disableBreakdown: true,
    forcePercentAxis: true,
  });

  window.Indicators.renderChart({
    chartId: 'citations-share-chart',
    chartDivId: 'citations-share-chart-div',
    data: data,
    seriesType: 'Citations Share',
    title: gettext('Citations Share (%)'),
    subtitle: relativeSubtitle,
    disableBreakdown: true,
    forcePercentAxis: true,
  });

  window.Indicators.renderChart({
    chartId: 'citations-per-doc-share-chart',
    chartDivId: 'citations-per-doc-share-chart-div',
    data: data,
    seriesType: 'Citations per Document Share',
    title: gettext('Citations per Document Share (%)'),
    subtitle: relativeSubtitle,
    disableBreakdown: true,
    forcePercentAxis: true,
  });

  window.Indicators.renderChart({
    chartId: 'cited-docs-share-chart',
    chartDivId: 'cited-docs-share-chart-div',
    data: data,
    seriesType: 'Cited Documents Share',
    title: gettext('Cited Documents Share (%)'),
    subtitle: relativeSubtitle,
    disableBreakdown: true,
    forcePercentAxis: true,
  });

  window.Indicators.renderChart({
    chartId: 'pct-cited-docs-share-chart',
    chartDivId: 'pct-cited-docs-share-chart-div',
    data: data,
    seriesType: 'Percent Docs With Citations Share',
    title: gettext('% Documents With ≥1 Citation Share (%)'),
    subtitle: relativeSubtitle,
    disableBreakdown: true,
    forcePercentAxis: true,
  });
  if (!hasVisibleRelativeCharts() && relativeMetricsSection) {
    relativeMetricsSection.classList.add('d-none');
  }
}
