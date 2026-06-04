(function () {
  if (typeof window !== 'undefined' && typeof window.gettext !== 'function') {
    window.gettext = function (msgid) { return msgid; };
  }

  const chartInstances = {};
  function getConfigAttr(configElement, attrName, fallback = '') {
    if (!configElement) return fallback;
    const value = configElement.getAttribute(attrName);
    if (value === null || value === undefined || value === '') return fallback;
    return value;
  }

  function resizeAllCharts() {
    Object.values(chartInstances).forEach(chart => {
      if (chart && typeof chart.resize === 'function') {
        chart.resize();
      }
    });
  }

  function truncateText(value, maxLength = 18) {
    const normalizedValue = String(value || '').trim();
    if (!normalizedValue || normalizedValue.length <= maxLength) return normalizedValue;
    return `${normalizedValue.slice(0, Math.max(0, maxLength - 3)).trim()}...`;
  }

  function buildProfileTooltip(overrides = {}) {
    return buildTooltip({
      enterable: false,
      transitionDuration: 0,
      extraCssText: 'background:transparent;border:none;box-shadow:none;padding:0;',
      ...overrides,
    });
  }

  function buildRadarTooltipPosition(_point, _params, _dom, _rect, size) {
    const viewWidth = size?.viewSize?.[0] || 0;
    const viewHeight = size?.viewSize?.[1] || 0;
    const contentWidth = size?.contentSize?.[0] || 0;
    const contentHeight = size?.contentSize?.[1] || 0;
    const left = viewWidth ? Math.max(8, viewWidth - contentWidth - 12) : 12;
    const availableHeight = Math.max(8, viewHeight - contentHeight - 12);
    const top = Math.max(8, Math.min(44, availableHeight));
    return [left, top];
  }

  function buildProfileCartesianGrid(overrides = {}) {
    return {
      left: 10,
      right: 92,
      top: 60,
      bottom: 60,
      containLabel: true,
      ...overrides,
    };
  }

  function renderChart(chartId, options) {
    if (typeof echarts === 'undefined') return;

    const element = document.getElementById(chartId);
    if (!element) return;

    let chart = chartInstances[chartId];
    if (!chart) {
      chart = echarts.init(element);
      chartInstances[chartId] = chart;
    }

    chart.setOption(options, true);
  }

  function readJsonScript(scriptId, fallback) {
    const element = document.getElementById(scriptId);
    if (!element) return fallback;

    try {
      return JSON.parse(element.textContent);
    } catch (error) {
      console.error(`Error parsing ${scriptId}`, error);
      return fallback;
    }
  }

  function buildConfiguredSeries(chartConfig, data) {
    return (chartConfig.series || []).map(seriesConfig => {
      const decimals = Number(seriesConfig.decimals || 0);
      const isPercent = Boolean(seriesConfig.is_percent);

      return {
        name: seriesConfig.label || seriesConfig.key || '',
        type: seriesConfig.type || 'line',
        yAxisIndex: Number(seriesConfig.y_axis || 0),
        smooth: seriesConfig.type !== 'bar',
        data: data[seriesConfig.key] || [],
        dataViewFormatter: value => formatDataViewNumber(value, { decimals, isPercent }),
        tooltipFormatter: value => formatTooltipNumber(value, { decimals, isPercent }),
        isPercentSeries: isPercent,
      };
    });
  }

  function buildConfiguredYAxis(chartConfig) {
    const yAxes = Array.isArray(chartConfig.y_axes) ? chartConfig.y_axes : [];
    if (!yAxes.length) {
      return {
        type: 'value',
        axisLabel: { formatter: value => formatChartAxisNumber(value, { decimals: 0 }) },
      };
    }

    return yAxes.map(axisConfig => ({
      type: 'value',
      name: axisConfig.label || '',
      axisLabel: {
        formatter: value => formatChartAxisNumber(value, { decimals: Number(axisConfig.decimals || 0) }),
      },
    }));
  }

  function buildConfiguredTimeSeriesChart(data, chartConfig) {
    const years = Array.isArray(data.years) ? data.years : [];
    const title = chartConfig.title || '';
    const series = buildConfiguredSeries(chartConfig, data);

    return {
      title: { text: title },
      tooltip: buildProfileTooltip({
        trigger: 'axis',
        formatter: buildAxisTooltipFormatter({ series }),
      }),
      legend: {
        data: series.map(item => item.name),
        bottom: 0,
      },
      toolbox: buildToolbox(chartConfig.toolbox_types || ['line', 'bar'], {
        optionToContent: () => buildTimeSeriesDataView({
          title,
          axisValues: years,
          series,
        }),
      }),
      grid: buildProfileCartesianGrid(chartConfig.grid || {}),
      xAxis: { type: 'category', data: years },
      yAxis: buildConfiguredYAxis(chartConfig),
      series,
    };
  }

  function buildCategoryRadar(data, chartConfig) {
    const dataKey = chartConfig.data_key || '';
    const metric = chartConfig.field || '';
    const metricLabel = chartConfig.label || metric;
    const decimals = Number(chartConfig.decimals || 0);
    const entries = Array.isArray(data[dataKey])
      ? data[dataKey]
      : [];

    const buildRadarDataView = () => {
      const rows = entries.map(item => [
        item.category || '-',
        formatDataViewNumber(item[metric], { decimals }),
      ]);

      return buildDataViewTable({
        title: `${metricLabel} ${gettext('by Category')}`,
        columns: [
          { label: gettext('Category') },
          { label: metricLabel, align: 'right' },
        ],
        rows,
        emptyMessage: gettext('No category data available'),
      });
    };

    if (!entries.length) {
      return {
        title: { text: `${metricLabel} ${gettext('by Category')}` },
        toolbox: buildToolbox([], {
          optionToContent: buildRadarDataView,
        }),
        graphic: {
          type: 'text',
          left: 'center',
          top: 'middle',
          style: {
            text: gettext('No category data available'),
            fill: '#667085',
            fontSize: 14,
          },
        },
      };
    }

    const values = entries.map(item => Number(item[metric]) || 0);
    const maxValue = Math.max(...values, 1);

    return {
      title: { text: `${metricLabel} ${gettext('by Category')}` },
      tooltip: buildProfileTooltip({
        trigger: 'item',
        enterable: true,
        hideDelay: 250,
        position: buildRadarTooltipPosition,
        formatter: function () {
          const rowsHtml = entries.map((item, index) => `
            <div class="indicator-tooltip__row">
              <span class="indicator-tooltip__label">${escapeHtml(item.category || '-')}</span>
              <span class="indicator-tooltip__value">${formatTooltipNumber(
                values[index],
                { decimals },
              )}</span>
            </div>
          `).join('');

          return buildTooltipCard(metricLabel, rowsHtml, gettext('No category data available'));
        },
      }),
      toolbox: buildToolbox([], {
        optionToContent: buildRadarDataView,
      }),
      radar: {
        radius: '65%',
        name: {
          color: '#2f4050',
          fontSize: 11,
          lineHeight: 14,
          formatter: value => truncateText(value, 20),
        },
        indicator: entries.map(item => ({
          name: String(item.category),
          max: maxValue,
        })),
      },
      series: [
        {
          type: 'radar',
          data: [
            {
              value: values,
              name: metricLabel,
              areaStyle: { opacity: 0.2 },
              lineStyle: { width: 2 },
            },
          ],
        },
      ],
    };
  }

  function renderJournalProfileCharts(data) {
    if (!data || typeof data !== 'object') return;

    readJsonScript('journal-profile-timeseries-charts', []).forEach(chartConfig => {
      renderChart(chartConfig.chart_id, buildConfiguredTimeSeriesChart(data, chartConfig));
    });

    readJsonScript('journal-profile-category-charts', []).forEach(chartConfig => {
      renderChart(chartConfig.chart_id, buildCategoryRadar(data, chartConfig));
    });

    setTimeout(resizeAllCharts, 100);
  }

  function initJournalProfileCharts() {
    const dataElement = document.getElementById('journal-profile-data');
    if (!dataElement) return;

    try {
      const profileData = JSON.parse(dataElement.textContent);
      window.__journalProfileData = profileData;
      renderJournalProfileCharts(profileData);
    } catch (error) {
      console.error('Error initializing journal profile charts', error);
    }
  }

  function renderGlobalCharts() {
    var data = readJsonScript('journal-profile-global-data', null);
    if (!data || !Array.isArray(data.years) || !data.years.length) return;

    readJsonScript('journal-profile-global-charts', []).forEach(chartConfig => {
      renderChart(chartConfig.chart_id, buildConfiguredTimeSeriesChart(data, chartConfig));
    });

    setTimeout(resizeAllCharts, 100);
  }

  function initJournalProfileTabs() {
    var tabsNav = document.querySelector('.journal-profile-tabs__nav');
    if (!tabsNav) return;

    var tabs = tabsNav.querySelectorAll('.journal-profile-tabs__tab');
    var panels = document.querySelectorAll('.journal-profile-tabs__panel');
    var globalChartsRendered = false;

    function getInitialTab() {
      var urlParams = new URLSearchParams(window.location.search);
      var tab = urlParams.get('_tab') || 'global';
      if (tab === 'global' && !document.querySelector('[data-panel="global"]')) {
        return 'category';
      }
      return tab;
    }

    function activateTab(tabName) {
      var targetPanel = null;
      panels.forEach(function (p) {
        var isActive = p.getAttribute('data-panel') === tabName;
        p.classList.toggle('journal-profile-tabs__panel--active', isActive);
        if (isActive) targetPanel = p;
      });

      tabs.forEach(function (t) {
        var isActive = t.getAttribute('data-tab') === tabName;
        t.classList.toggle('journal-profile-tabs__tab--active', isActive);
        t.setAttribute('aria-selected', isActive ? 'true' : 'false');
      });

      if (tabName === 'global' && !globalChartsRendered) {
        globalChartsRendered = true;
        setTimeout(renderGlobalCharts, 150);
      } else {
        if (targetPanel) {
          requestAnimationFrame(function () {
            requestAnimationFrame(resizeAllCharts);
          });
        }
      }
    }

    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        var tabName = tab.getAttribute('data-tab');
        if (tabName) activateTab(tabName);
      });
    });

    // inject hidden _tab field into category controls form
    var form = document.getElementById('journal-profile-controls-form');
    if (form) {
      var hiddenTab = document.createElement('input');
      hiddenTab.type = 'hidden';
      hiddenTab.name = '_tab';
      hiddenTab.value = 'category';
      form.appendChild(hiddenTab);

      // update hidden field when switching tabs
      tabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
          hiddenTab.value = tab.getAttribute('data-tab') || 'global';
        });
      });
    }

    // activate the tab from URL param (or default)
    var initialTab = getInitialTab();
    var initialPanel = document.querySelector('[data-panel="' + initialTab + '"]');
    if (!initialPanel && initialTab === 'global') {
      initialTab = 'category';
      initialPanel = document.querySelector('[data-panel="category"]');
    }
    // set initial active CSS class
    tabs.forEach(function (t) {
      var name = t.getAttribute('data-tab');
      t.classList.toggle('journal-profile-tabs__tab--active', name === initialTab);
      t.setAttribute('aria-selected', name === initialTab ? 'true' : 'false');
    });
    panels.forEach(function (p) {
      p.classList.toggle('journal-profile-tabs__panel--active', p.getAttribute('data-panel') === initialTab);
    });
    if (initialTab === 'global' && initialPanel && !globalChartsRendered) {
      globalChartsRendered = true;
      setTimeout(renderGlobalCharts, 150);
    } else {
      requestAnimationFrame(function () {
        requestAnimationFrame(resizeAllCharts);
      });
    }
  }

  function setProfileSelectDisabled(selectElement, disabled) {
    if (!selectElement) return;
    selectElement.disabled = Boolean(disabled);
  }

  function bindProfileSelectChange(selectElement, handler) {
    if (!selectElement || typeof handler !== 'function') return;
    selectElement.addEventListener('change', handler);
  }

  function replaceProfileSelectOptions(selectElement, optionValues, selectedValue, fieldName = '') {
    if (!selectElement) return;

    const normalizedValues = Array.isArray(optionValues)
      ? optionValues
        .map(value => String(value || '').trim())
        .filter(Boolean)
      : [];
    const normalizedSelectedValue = String(selectedValue || '').trim();
    const resolvedSelectedValue = normalizedValues.includes(normalizedSelectedValue)
      ? normalizedSelectedValue
      : (normalizedValues[0] || '');

    selectElement.innerHTML = '';

    if (!normalizedValues.length) {
      selectElement.add(new Option('', '', true, true));
    } else {
      normalizedValues.forEach(value => {
        const optionLabel = typeof window.standardizeFieldValue === 'function'
          ? window.standardizeFieldValue(fieldName, value)
          : value;
        selectElement.add(new Option(optionLabel, value, false, value === resolvedSelectedValue));
      });
      selectElement.value = resolvedSelectedValue;
    }

  }

  function initJournalProfileControls() {
    const form = document.getElementById('journal-profile-controls-form');
    const publicationYearSelect = document.getElementById('journal-profile-publication-year-select');
    const categoryLevelSelect = document.querySelector('[data-profile-category-level]');
    const categorySelect = document.querySelector('[data-profile-category-id]');
    let latestCategoryOptionsRequest = 0;

    if (!form || !categoryLevelSelect) return;

    async function refreshProfileCategoryOptions() {
      if (!categorySelect) return;

      const timeseriesUrl = String(form.getAttribute('data-profile-timeseries-url') || '').trim();
      const dataSource = String(form.getAttribute('data-profile-data-source') || '').trim();
      const journalIssn = String(form.getAttribute('data-profile-journal-issn') || '').trim();
      if (!timeseriesUrl || !dataSource || !journalIssn) return;

      const requestId = ++latestCategoryOptionsRequest;
      const formData = new FormData(form);
      setProfileSelectDisabled(categorySelect, true);

      try {
        const url = new URL(timeseriesUrl, window.location.origin);

        formData.forEach((value, key) => {
          const normalizedValue = String(value || '').trim();
          if (!normalizedValue) return;
          url.searchParams.append(key, normalizedValue);
        });

        url.searchParams.set('issn', journalIssn);
        url.searchParams.set('data_source', dataSource);

        const response = await fetch(url.toString());
        if (!response.ok) {
          throw new Error(`Profile category refresh failed with status ${response.status}`);
        }

        const data = await response.json();
        if (requestId !== latestCategoryOptionsRequest) return;

        replaceProfileSelectOptions(
          categorySelect,
          data?.available_categories || [],
          data?.selected_category_id || categorySelect.value,
          'category_id',
        );
      } catch (error) {
        console.error('Error refreshing journal profile category options', error);
      } finally {
        if (requestId === latestCategoryOptionsRequest) {
          setProfileSelectDisabled(categorySelect, false);
        }
      }
    }

    [publicationYearSelect, categoryLevelSelect].forEach(selectElement => {
      bindProfileSelectChange(selectElement, refreshProfileCategoryOptions);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    const configElement = document.getElementById('journal-profile-config');
    setChartNumberLocale(getConfigAttr(configElement, 'data-number-locale', ''));
    initJournalProfileCharts();
    initJournalProfileControls();
    initJournalProfileTabs();
  });

  window.addEventListener('resize', resizeAllCharts);
})();
