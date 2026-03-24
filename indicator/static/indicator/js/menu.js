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

  scopeSelect.value = scopeFromUrl;
}

function normalizeStudyUnit(studyUnit, fallback = 'document') {
  const normalized = String(studyUnit || '').trim().toLowerCase();
  if (normalized === 'journal') return 'source';
  if (['document', 'source', 'journal_metrics_by_*'].includes(normalized)) {
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

  const studyUnitForm = document.getElementById('study-unit-form');
  const selectStudyUnit = document.getElementById('selectStudyUnit');
  const menuForm = document.getElementById('indicator-filter-form');
  const currentDataSource = String(scopeControlsRoot.dataset.dataSource || 'scientific_production').trim();
  const isJournalMetricsPage = currentDataSource === 'journal_metrics_by_*';
  const indicatorHomeUrl = scopeControlsRoot.dataset.indicatorHomeUrl || '/indicators/';
  const journalMetricsUrl = scopeControlsRoot.dataset.journalMetricsUrl || '/indicators/journal-metrics/';
  const currentQueryParams = new URLSearchParams(window.location.search);
  const currentScopeFilter = String(currentQueryParams.get('scope') || '').trim();
  const currentStudyUnit = normalizeStudyUnit(
    scopeControlsRoot.dataset.studyUnit,
    isJournalMetricsPage ? 'journal_metrics_by_*' : 'document',
  );

  if (selectStudyUnit) {
    const hasOption = Array.from(selectStudyUnit.options).some(option => option.value === currentStudyUnit);
    if (hasOption) {
      selectStudyUnit.value = currentStudyUnit;
    }
  }

  const getCurrentScopeValue = () => {
    const scopeSelect = menuForm ? menuForm.querySelector('select[name="scope"]') : null;
    const scopeValue = scopeSelect ? String(scopeSelect.value || '').trim() : '';
    return scopeValue || currentScopeFilter;
  };

  if (studyUnitForm && selectStudyUnit) {
    studyUnitForm.addEventListener('submit', event => {
      event.preventDefault();

      const selectedStudyUnit = normalizeStudyUnit(selectStudyUnit.value, currentStudyUnit);
      const selectedScope = getCurrentScopeValue();
      const redirectUrl = selectedStudyUnit === 'journal_metrics_by_*'
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
}

function initIndicatorControlBarSelects() {
  document.querySelectorAll('.indicator-controls-bar__select').forEach(select => {
    const syncPlaceholderState = () => {
      const hasValue = Array.from(select.selectedOptions || [])
        .some(option => String(option.value || '').trim());
      const hasEmptyOption = Array.from(select.options || [])
        .some(option => !String(option.value || '').trim());

      select.classList.toggle('indicator-controls-bar__select--placeholder', hasEmptyOption && !hasValue);
    };

    syncPlaceholderState();

    if (select.dataset.placeholderBound === 'true') return;
    select.addEventListener('change', syncPlaceholderState);
    select.dataset.placeholderBound = 'true';
  });
}

function updateExternalSelectPlaceholderState(select) {
  if (!select) return;

  const hasValue = Array.from(select.selectedOptions || [])
    .some(option => String(option.value || '').trim());
  const hasEmptyOption = Array.from(select.options || [])
    .some(option => !String(option.value || '').trim());

  select.classList.toggle('indicator-controls-bar__select--placeholder', hasEmptyOption && !hasValue);
}

function appendFormFieldParams(params, name, value) {
  if (!name || value === null || value === undefined || value === '') return;

  if (Array.isArray(value)) {
    value.forEach(item => appendFormFieldParams(params, name, item));
    return;
  }

  params.append(name, String(value));
}

function collectJournalMetricsConfigFilters(form, excludeFieldNames = []) {
  const params = new URLSearchParams();
  if (!form) return params;

  const excluded = new Set((excludeFieldNames || []).map(name => String(name || '').trim()).filter(Boolean));
  const relatedExternalElements = form.id
    ? Array.from(document.querySelectorAll(`[form="${form.id}"].data-source-field`))
    : [];
  const seenElements = new Set();

  Array.from(form.elements || []).concat(relatedExternalElements).forEach(element => {
    if (!element?.name || seenElements.has(element)) return;
    seenElements.add(element);
    if (excluded.has(String(element.name || '').trim())) return;
    if (element.disabled) return;

    if (element.type === 'checkbox' || element.type === 'radio') {
      if (element.checked) {
        appendFormFieldParams(params, element.name, element.value);
      }
      return;
    }

    if (element.tagName === 'SELECT' && element.multiple) {
      Array.from(element.selectedOptions || []).forEach(option => {
        appendFormFieldParams(params, element.name, option.value);
      });
      return;
    }

    appendFormFieldParams(params, element.name, element.value);
  });

  return params;
}

async function updateJournalMetricsCategoryOptions(configRoot) {
  const root = configRoot || document.querySelector('[data-journal-metrics-config]');
  if (!root) return;

  const formId = 'journal-metrics-filter-form';
  const form = document.getElementById(formId);
  const categoryLevelSelect = root.querySelector('#indicator-config-category_level');
  const categorySelect = root.querySelector('#indicator-config-category_id');
  const dataSource = String(root.dataset.dataSource || '').trim();

  if (!form || !categoryLevelSelect || !categorySelect || !dataSource) return;

  const params = collectJournalMetricsConfigFilters(form, ['category_id']);
  params.set('data_source', dataSource);
  params.set('field_name', 'category_id');

  const currentValue = String(categorySelect.value || '').trim();
  categorySelect.disabled = true;

  try {
    const response = await fetch(`/search-gateway/search-item/?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`Unable to load category options (${response.status})`);
    }

    const data = await response.json();
    const results = Array.isArray(data?.results) ? data.results : [];
    const allowClear = String(categorySelect.dataset.allowClear || '').toLowerCase() === 'true';
    const placeholderText = window.gettext ? window.gettext('Selecione uma opção') : 'Selecione uma opção';

    categorySelect.innerHTML = '';
    if (allowClear) {
      const placeholderOption = new Option(placeholderText, '', false, false);
      categorySelect.add(placeholderOption);
    }

    const availableValues = [];
    results.forEach(option => {
      const optionValue = String(option?.value ?? option?.key ?? '').trim();
      if (!optionValue) return;
      const optionLabel = String(option?.label ?? optionValue).trim();
      categorySelect.add(new Option(optionLabel, optionValue, false, false));
      availableValues.push(optionValue);
    });

    const fallbackValue = availableValues.includes(currentValue)
      ? currentValue
      : (availableValues[0] || '');
    categorySelect.value = fallbackValue;
    updateExternalSelectPlaceholderState(categorySelect);
    categorySelect.dispatchEvent(new Event('change', { bubbles: true }));
  } catch (error) {
    console.error('Error loading journal metrics category options', error);
  } finally {
    categorySelect.disabled = false;
  }
}

function initJournalMetricsConfigControls() {
  const configRoot = document.querySelector('[data-journal-metrics-config]');
  if (!configRoot) return;

  const categoryLevelSelect = configRoot.querySelector('#indicator-config-category_level');
  if (categoryLevelSelect && categoryLevelSelect.dataset.categoryRefreshBound !== 'true') {
    categoryLevelSelect.addEventListener('change', () => {
      updateJournalMetricsCategoryOptions(configRoot);
    });
    categoryLevelSelect.dataset.categoryRefreshBound = 'true';
  }

  if (categoryLevelSelect && configRoot.dataset.categoryInitialRefreshDone !== 'true') {
    updateJournalMetricsCategoryOptions(configRoot);
    configRoot.dataset.categoryInitialRefreshDone = 'true';
  }
}

function requestIndicatorRefresh(menuForm, submitButton) {
  if (!menuForm) return;

  if (typeof menuForm.requestSubmit === 'function') {
    try {
      if (submitButton && submitButton.form === menuForm) {
        menuForm.requestSubmit(submitButton);
        return;
      }
      menuForm.requestSubmit();
      return;
    } catch (_error) {
      // Fall through to button click / synthetic submit.
    }
  }

  if (submitButton && typeof submitButton.click === 'function' && !submitButton.disabled) {
    submitButton.click();
    return;
  }

  menuForm.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
}

function initBreakdownVariableAutoSubmit(menuForm, submitButton) {
  if (!menuForm) return;

  const breakdownSelect = document.getElementById('indicator-breakdown-variable')
    || document.querySelector('[name="breakdown_variable"][form="indicator-filter-form"]');
  if (!breakdownSelect || breakdownSelect.dataset.autoSubmitBound === 'true') return;

  breakdownSelect.addEventListener('change', () => {
    if (submitButton?.disabled) return;
    requestIndicatorRefresh(menuForm, submitButton);
  });
  breakdownSelect.dataset.autoSubmitBound = 'true';
}

function initIndicatorForm(dataSource, studyUnit) {
  const menuForm = document.getElementById('indicator-filter-form');
  if (!menuForm) return;

  syncScopeFilterIntoForm(menuForm);

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
    const formData = new FormData(menuForm);
    const filters = window.SearchGatewayFilterForm
      ? window.SearchGatewayFilterForm.serializeForm(menuForm)
      : {};
    const scopeFromUrl = getScopeFilterFromUrl();
    const existingScope = filters.scope;
    const hasScopeInFilters = Array.isArray(existingScope)
      ? existingScope.some(value => String(value || '').trim())
      : !!String(existingScope || '').trim();
    if (!hasScopeInFilters && scopeFromUrl) {
      filters.scope = scopeFromUrl;
    }

    // Extract breakdown variable
    const breakdownVariable = Array.isArray(filters.breakdown_variable)
      ? filters.breakdown_variable[0]
      : (filters.breakdown_variable || '');

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

      if (window.SearchGatewayFilterForm) {
        window.SearchGatewayFilterForm.commitAppliedFilters(menuForm);
      }

      clearAppliedFiltersContainer();

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
    if (window.SearchGatewayFilterForm) {
      window.SearchGatewayFilterForm.resetForm(menuForm);
    } else {
      menuForm.reset();
    }
  };

  // Attach event listeners
  menuForm.addEventListener('submit', handleFormSubmit);
  menuForm.addEventListener('search-gateway:filters-changed', () => {
    if (submitButton?.disabled) return;
    requestIndicatorRefresh(menuForm, submitButton);
  });
  if (resetButton) {
    resetButton.addEventListener('click', handleFormReset);
  }
  initBreakdownVariableAutoSubmit(menuForm, submitButton);

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

  const triggerInitialRender = () => {
    if (initialRenderTriggered || hasVisibleCharts()) return;
    initialRenderTriggered = true;
    requestIndicatorRefresh(menuForm, submitButton);
  };

  if (window.SearchGatewayFilterForm) {
    window.SearchGatewayFilterForm.init(menuForm).then(triggerInitialRender);
  } else {
    window.setTimeout(triggerInitialRender, 250);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initIndicatorControlBarSelects();
  initScopeControls();
  initJournalMetricsConfigControls();
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

  const breakdownSelect = document.querySelector('#indicator-filter-form [name="breakdown_variable"]')
    || document.querySelector('[name="breakdown_variable"][form="indicator-filter-form"]');
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
