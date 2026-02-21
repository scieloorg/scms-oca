function getScopeFilterFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const value = params.get('scope') || params.get('source_index_open_alex');
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
