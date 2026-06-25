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
    scopeSelect.add(new Option(scopeFromUrl, scopeFromUrl, false, false));
  }

  scopeSelect.value = scopeFromUrl;
}

function getConfiguredStudyUnitValues(selectStudyUnit) {
  return new Set(
    Array.from(selectStudyUnit?.options || [])
      .map(option => String(option.value || '').trim().toLowerCase())
      .filter(Boolean)
  );
}

function normalizeStudyUnit(studyUnit, fallback = '', allowedValues = null) {
  const normalized = String(studyUnit || '').trim().toLowerCase();
  if (!normalized) return fallback;
  if (!allowedValues || allowedValues.has(normalized)) {
    return normalized;
  }
  return fallback;
}

function buildAnalysisUnitRedirectUrl({ targetUrl, fallbackUrl, studyUnit, scopeValue, resetQuery }) {
  const params = resetQuery ? new URLSearchParams() : new URLSearchParams(window.location.search);

  params.set('study_unit', studyUnit);
  params.delete('return_study_unit');

  if (scopeValue) {
    params.set('scope', scopeValue);
  } else {
    params.delete('scope');
  }

  const query = params.toString();
  const baseUrl = targetUrl || fallbackUrl || window.location.pathname;
  return query ? `${baseUrl}?${query}` : baseUrl;
}

function buildReturnToSourceRedirectUrl({ targetUrl, currentStudyUnit }) {
  const params = new URLSearchParams();
  if (currentStudyUnit) {
    params.set('return_study_unit', currentStudyUnit);
  }

  const query = params.toString();
  return query ? `${targetUrl}?${query}` : targetUrl;
}

async function populateScopeSelectOptions(selectIndexScope, { scopeDataSource, currentScopeFilter, allScopesLabel }) {
  if (!selectIndexScope) return;

  selectIndexScope.innerHTML = '';
  const allOption = document.createElement('option');
  allOption.value = '';
  allOption.textContent = allScopesLabel || 'All scopes';
  selectIndexScope.appendChild(allOption);

  try {
    const data = await fetchFilters(scopeDataSource, { fields: 'scope', refresh: '1' });
    const scopeOptions = Array.isArray(data?.scope) ? data.scope : [];

    const seen = new Set();
    scopeOptions.forEach(option => {
      const optionValue = String(option?.key ?? '').trim();
      if (!optionValue || seen.has(optionValue)) return;
      seen.add(optionValue);

      const selectOption = document.createElement('option');
      selectOption.value = optionValue;
      selectOption.textContent = String(option?.label ?? optionValue);
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
  const indicatorHomeUrl = scopeControlsRoot.dataset.indicatorHomeUrl || window.location.pathname;
  const allowedStudyUnits = getConfiguredStudyUnitValues(selectStudyUnit);
  const currentQueryParams = new URLSearchParams(window.location.search);
  const currentScopeFilter = String(currentQueryParams.get('scope') || '').trim();
  const currentStudyUnit = normalizeStudyUnit(
    scopeControlsRoot.dataset.studyUnit,
    Array.from(allowedStudyUnits)[0] || '',
    allowedStudyUnits,
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

      const selectedOption = selectStudyUnit.selectedOptions?.[0];
      const selectedStudyUnit = normalizeStudyUnit(selectStudyUnit.value, currentStudyUnit, allowedStudyUnits);
      const selectedScope = getCurrentScopeValue();
      const targetUrl = String(selectedOption?.dataset?.targetUrl || '').trim();
      const returnToSource = String(selectedOption?.dataset?.returnToSource || '').toLowerCase() === 'true';
      let redirectUrl = '';

      if (targetUrl && returnToSource) {
        redirectUrl = buildReturnToSourceRedirectUrl({ targetUrl, currentStudyUnit });
      } else {
        redirectUrl = buildAnalysisUnitRedirectUrl({
          targetUrl,
          fallbackUrl: targetUrl ? targetUrl : window.location.pathname || indicatorHomeUrl,
          studyUnit: selectedStudyUnit,
          scopeValue: selectedScope,
          resetQuery: Boolean(targetUrl),
        });
      }

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

function requestIndicatorRefresh(menuForm, submitButton) {
  if (!menuForm) return;
  try {
    if (submitButton && submitButton.form === menuForm) {
      menuForm.requestSubmit(submitButton);
    } else {
      menuForm.requestSubmit();
    }
  } catch (_error) {
    if (submitButton && typeof submitButton.click === 'function' && !submitButton.disabled) {
      submitButton.click();
    } else {
      menuForm.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    }
  }
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

function getIndicatorResultsCol() {
  return document.querySelector('.indicator-results-col');
}

var indicatorLoadingOptions = {
  overlayClass: 'indicator-results-loading',
  innerClass: 'indicator-results-loading-inner',
  textClass: 'indicator-results-loading-text',
  loadingClass: 'indicator-results-col--loading',
  message: getLoadingMessage(),
};

var indicatorLoading = createLoadingOverlay(getIndicatorResultsCol, indicatorLoadingOptions);

function positionIndicatorLoadingOverlay() {
  var col = indicatorLoading.getContainer();

  if (!col) {
    return;
  }

  var overlay = indicatorLoading.getOverlay();

  if (!overlay) {
    return;
  }

  var inner = overlay.querySelector('.indicator-results-loading-inner');

  if (!inner) {
    return;
  }

  var rect = col.getBoundingClientRect();

  inner.style.left = (rect.left + rect.width / 2) + 'px';
}

var indicatorLoadingResizeBound = false;

function showIndicatorLoading() {
  var col = indicatorLoading.getContainer();

  if (!col) {
    return;
  }

  indicatorLoading.show();

  positionIndicatorLoadingOverlay();

  if (!indicatorLoadingResizeBound) {
    window.addEventListener('resize', positionIndicatorLoadingOverlay);
    indicatorLoadingResizeBound = true;
  }
}

function hideIndicatorLoading() {
  indicatorLoading.hide();
}

if (typeof window !== 'undefined') {
  window.IndicatorLoading = {
    show: showIndicatorLoading,
    hide: hideIndicatorLoading,
  };
}

function initIndicatorForm(dataSource, studyUnit) {
  const menuForm = document.getElementById('indicator-filter-form');
  if (!menuForm) return;

  syncScopeFilterIntoForm(menuForm);

  const submitButton = document.getElementById('menu-submit');
  const resetButton = document.getElementById('menu-reset');
  const chartErrorContainerId = 'indicator-chart-error';

  const removeChartError = () => {
    document.getElementById(chartErrorContainerId)?.remove();
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

  const handleFormSubmit = (event) => {
    event.preventDefault();
    submitButton.disabled = true;
    showIndicatorLoading();

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

    const breakdownVariable = Array.isArray(filters.breakdown_variable)
      ? filters.breakdown_variable[0]
      : (filters.breakdown_variable || '');

    const payload = {
      data_source: dataSource,
      chart_id: 'timeseries_documents',
      filters,
      study_unit: studyUnit,
    };

    fetch('/api/v1/chart-data/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': formData.get('csrfmiddlewaretoken'),
      },
      body: JSON.stringify(payload),
    })
    .then(response => response.json())
    .then(data => {
      if (!data || data.error) {
        showChartError((data && data.error) || gettext('Error loading indicator data.'));
        clearGraphsContainer();
        clearAppliedFiltersContainer();
        return;
      }

      if (!Array.isArray(data.charts)) {
        console.error('Invalid chart data format (missing charts list):', data);
        showChartError(gettext('Unexpected response while loading indicator data.'));
        clearGraphsContainer();
        clearAppliedFiltersContainer();
        return;
      }

      removeChartError();

      if (window.SearchGatewayFilterForm) {
        window.SearchGatewayFilterForm.commitAppliedFilters(menuForm);
      }

      clearAppliedFiltersContainer();
      renderChartsContainer(data, dataSource, studyUnit, formData.get('csrfmiddlewaretoken'));

      const firstChart = Array.isArray(data.charts) && data.charts.find(c => !c.is_relative);
      if (firstChart) {
        const total = (firstChart.series || []).reduce(
          (sum, s) => sum + (s.data || []).reduce((a, b) => a + (Number(b) || 0), 0), 0
        );
        updateSearchButtonTotal(total);
      }
    })
    .catch(error => {
      console.error('Error:', error);
      showChartError(gettext('Error loading indicator data.'));
      clearGraphsContainer();
      clearAppliedFiltersContainer();
    })
    .finally(() => {
      hideIndicatorLoading();
      submitButton.disabled = false;
    });
  };

  const handleFormReset = (event) => {
    event.preventDefault();
    if (window.SearchGatewayFilterForm) {
      window.SearchGatewayFilterForm.resetForm(menuForm);
    } else {
      menuForm.reset();
    }
  };

  menuForm.addEventListener('submit', handleFormSubmit);
  menuForm.addEventListener('search-gateway:filters-changed', () => {
    if (submitButton?.disabled) return;
    requestIndicatorRefresh(menuForm, submitButton);
  });
  if (resetButton) resetButton.addEventListener('click', handleFormReset);

  initBreakdownVariableAutoSubmit(menuForm, submitButton);

  const triggerInitialRender = () => requestIndicatorRefresh(menuForm, submitButton);

  if (window.SearchGatewayFilterForm) {
    window.SearchGatewayFilterForm.init(menuForm)
      .then(triggerInitialRender)
      .catch(error => {
        console.error('Filter form initialization failed:', error);
        triggerInitialRender();
      });
  } else {
    window.setTimeout(triggerInitialRender, 250);
  }
}

function updateSearchButtonTotal(total) {
  const el = document.getElementById('indicator-search-total');
  if (!el) return;
  el.textContent = typeof total === 'number' ? total.toLocaleString() : total;
}

function initGoToSearchButton() {
  const btn = document.getElementById('indicator-go-to-search');
  if (!btn) return;

  btn.addEventListener('click', (event) => {
    event.preventDefault();

    const searchUrl = (btn.dataset.searchUrl || '').trim();
    if (!searchUrl) return;

    const menuForm = document.getElementById('indicator-filter-form');
    const filters = menuForm && window.SearchGatewayFilterForm
      ? window.SearchGatewayFilterForm.serializeForm(menuForm)
      : {};

    const scopeFromUrl = getScopeFilterFromUrl();
    const existingScope = filters.scope;
    const hasScopeInFilters = Array.isArray(existingScope)
      ? existingScope.some(v => String(v || '').trim())
      : !!String(existingScope || '').trim();
    if (!hasScopeInFilters && scopeFromUrl) {
      filters.scope = scopeFromUrl;
    }

    delete filters.breakdown_variable;

    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value == null || value === '') return;
      if (Array.isArray(value)) {
        value.forEach(v => { if (v != null && v !== '') params.append(key, v); });
      } else {
        params.append(key, value);
      }
    });

    const query = params.toString();
    window.open(query ? `${searchUrl}?${query}` : searchUrl, '_blank');
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initIndicatorControlBarSelects();
  initScopeControls();
  initGoToSearchButton();
});

if (typeof window !== 'undefined' && typeof window.gettext !== 'function') {
  window.gettext = function (msgid) { return msgid; };
}

function renderChartsContainer(data, dataSource, studyUnit, csrfMiddlewareToken) {
  if (!Array.isArray(data.charts) || !data.charts.length) {
    clearGraphsContainer();
    return;
  }

  clearGraphsContainer();

  const relativeMetricsSection = document.getElementById('relative-metrics-section');

  const hasRelativeCharts = data.charts.some(chart => chart.is_relative);
  if (hasRelativeCharts && relativeMetricsSection) {
    relativeMetricsSection.classList.remove('d-none');
  }

  const breakdownSelect = document.querySelector('#indicator-filter-form [name="breakdown_variable"]')
    || document.querySelector('[name="breakdown_variable"][form="indicator-filter-form"]');
  const breakdownText = breakdownSelect && breakdownSelect.value
    ? (breakdownSelect.options[breakdownSelect.selectedIndex]?.textContent || '').trim()
    : '';
  const breakdownSubtitle = breakdownText
    ? `${gettext('per Year')} ${gettext('by')} ${breakdownText}`
    : '';
  const relativeSubtitle = gettext('Per year, filtered vs total baseline');

  let hasVisibleRelative = false;

  data.charts.forEach(chart => {
    const success = window.Indicators.renderChart({
      chartId: `${chart.id}-chart`,
      chartDivId: `${chart.id}-chart-div`,
      data: {
        years: chart.years,
        series: chart.series,
        breakdown_variable: data.breakdown_variable,
      },
      title: chart.title,
      subtitle: chart.is_relative ? relativeSubtitle : breakdownSubtitle,
      forcePercentAxis: chart.is_relative,
    });

    if (success && chart.is_relative) hasVisibleRelative = true;
  });

  if (relativeMetricsSection) {
    relativeMetricsSection.classList.toggle('d-none', !hasVisibleRelative);
  }
}
