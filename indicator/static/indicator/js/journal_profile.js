(function () {
  if (typeof window !== 'undefined' && typeof window.gettext !== 'function') {
    window.gettext = function (msgid) { return msgid; };
  }

  const chartInstances = {};
  const journalMetricsCommon = window.JournalMetrics || {};

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

  function buildOutputChart(data) {
    const years = Array.isArray(data.years) ? data.years : [];
    const title = gettext('Publications and Total Citations per Year');
    const series = [
      {
        name: gettext('Publications'),
        type: 'bar',
        data: data.journal_publications_count_per_year || [],
        dataViewFormatter: value => formatDataViewNumber(value, { decimals: 0 }),
        tooltipFormatter: value => formatTooltipNumber(value, { decimals: 0 }),
      },
      {
        name: gettext('Total Citations'),
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        data: data.journal_citations_total_per_year || [],
        dataViewFormatter: value => formatDataViewNumber(value, { decimals: 0 }),
        tooltipFormatter: value => formatTooltipNumber(value, { decimals: 0 }),
      },
    ];

    return {
      title: { text: title },
      tooltip: buildProfileTooltip({
        trigger: 'axis',
        formatter: buildAxisTooltipFormatter({ series }),
      }),
      legend: {
        data: [gettext('Publications'), gettext('Total Citations')],
        bottom: 0,
      },
      toolbox: buildToolbox(['line', 'bar'], {
        optionToContent: () => buildTimeSeriesDataView({
          title,
          axisValues: years,
          series,
        }),
      }),
      grid: buildProfileCartesianGrid({ right: 116 }),
      xAxis: { type: 'category', data: years },
      yAxis: [
        {
          type: 'value',
          name: gettext('Publications'),
          axisLabel: { formatter: value => formatChartAxisNumber(value, { decimals: 0 }) },
        },
        {
          type: 'value',
          name: gettext('Citations'),
          axisLabel: { formatter: value => formatChartAxisNumber(value, { decimals: 0 }) },
        },
      ],
      series,
    };
  }

  function buildImpactChart(data) {
    const years = Array.isArray(data.years) ? data.years : [];
    const title = gettext('Cohort Impact and Mean Citations per Year');
    const series = [
      {
        name: gettext('Cohort Impact (Total)'),
        type: 'line',
        smooth: true,
        data: data.journal_impact_cohort_per_year || [],
        dataViewFormatter: value => formatDataViewNumber(value, { decimals: 2 }),
        tooltipFormatter: value => formatTooltipNumber(value, { decimals: 2 }),
      },
      {
        name: gettext('Cohort Impact (2 years)'),
        type: 'line',
        smooth: true,
        data: data.journal_impact_cohort_window_2y_per_year || [],
        dataViewFormatter: value => formatDataViewNumber(value, { decimals: 2 }),
        tooltipFormatter: value => formatTooltipNumber(value, { decimals: 2 }),
      },
      {
        name: gettext('Cohort Impact (3 years)'),
        type: 'line',
        smooth: true,
        data: data.journal_impact_cohort_window_3y_per_year || [],
        dataViewFormatter: value => formatDataViewNumber(value, { decimals: 2 }),
        tooltipFormatter: value => formatTooltipNumber(value, { decimals: 2 }),
      },
      {
        name: gettext('Cohort Impact (5 years)'),
        type: 'line',
        smooth: true,
        data: data.journal_impact_cohort_window_5y_per_year || [],
        dataViewFormatter: value => formatDataViewNumber(value, { decimals: 2 }),
        tooltipFormatter: value => formatTooltipNumber(value, { decimals: 2 }),
      },
      {
        name: gettext('Mean Citations'),
        type: 'line',
        smooth: true,
        data: data.journal_citations_mean_per_year || [],
        dataViewFormatter: value => formatDataViewNumber(value, { decimals: 2 }),
        tooltipFormatter: value => formatTooltipNumber(value, { decimals: 2 }),
      },
    ];

    return {
      title: { text: title },
      tooltip: buildProfileTooltip({
        trigger: 'axis',
        formatter: buildAxisTooltipFormatter({ series }),
      }),
      legend: {
        data: [
          gettext('Cohort Impact (Total)'),
          gettext('Cohort Impact (2 years)'),
          gettext('Cohort Impact (3 years)'),
          gettext('Cohort Impact (5 years)'),
          gettext('Mean Citations'),
        ],
        bottom: 0,
      },
      toolbox: buildToolbox(['line', 'bar'], {
        optionToContent: () => buildTimeSeriesDataView({
          title,
          axisValues: years,
          series,
        }),
      }),
      grid: buildProfileCartesianGrid({ bottom: 80 }),
      xAxis: { type: 'category', data: years },
      yAxis: {
        type: 'value',
        axisLabel: { formatter: value => formatChartAxisNumber(value, { decimals: 2 }) },
      },
      series,
    };
  }

  function buildTopShareChart(data) {
    const years = Array.isArray(data.years) ? data.years : [];
    const title = gettext('Top Publications Share (%) per Year');
    const series = [
      {
        name: gettext('Top 1%'),
        type: 'line',
        smooth: true,
        data: data.top_1pct_all_time_publications_share_pct_per_year || [],
        dataViewFormatter: value => formatDataViewNumber(value, { decimals: 2, isPercent: true }),
        tooltipFormatter: value => formatTooltipNumber(value, { decimals: 2, isPercent: true }),
        isPercentSeries: true,
      },
      {
        name: gettext('Top 5%'),
        type: 'line',
        smooth: true,
        data: data.top_5pct_all_time_publications_share_pct_per_year || [],
        dataViewFormatter: value => formatDataViewNumber(value, { decimals: 2, isPercent: true }),
        tooltipFormatter: value => formatTooltipNumber(value, { decimals: 2, isPercent: true }),
        isPercentSeries: true,
      },
      {
        name: gettext('Top 10%'),
        type: 'line',
        smooth: true,
        data: data.top_10pct_all_time_publications_share_pct_per_year || [],
        dataViewFormatter: value => formatDataViewNumber(value, { decimals: 2, isPercent: true }),
        tooltipFormatter: value => formatTooltipNumber(value, { decimals: 2, isPercent: true }),
        isPercentSeries: true,
      },
      {
        name: gettext('Top 50%'),
        type: 'line',
        smooth: true,
        data: data.top_50pct_all_time_publications_share_pct_per_year || [],
        dataViewFormatter: value => formatDataViewNumber(value, { decimals: 2, isPercent: true }),
        tooltipFormatter: value => formatTooltipNumber(value, { decimals: 2, isPercent: true }),
        isPercentSeries: true,
      },
    ];

    return {
      title: { text: title },
      tooltip: buildProfileTooltip({
        trigger: 'axis',
        formatter: buildAxisTooltipFormatter({ series }),
      }),
      legend: {
        data: [gettext('Top 1%'), gettext('Top 5%'), gettext('Top 10%'), gettext('Top 50%')],
        bottom: 0,
      },
      toolbox: buildToolbox(['line', 'bar'], {
        optionToContent: () => buildTimeSeriesDataView({
          title,
          axisValues: years,
          series,
        }),
      }),
      grid: buildProfileCartesianGrid(),
      xAxis: { type: 'category', data: years },
      yAxis: {
        type: 'value',
        name: '%',
        axisLabel: { formatter: value => formatChartAxisNumber(value, { decimals: 2 }) },
      },
      series,
    };
  }

  function buildCategoryRadar(data, metric, metricLabel) {
    const entries = Array.isArray(data.category_publications_spider)
      ? data.category_publications_spider
      : [];

    const buildRadarDataView = () => {
      const rows = entries.map(item => [
        item.category || '-',
        formatDataViewNumber(item[metric], { decimals: metric === 'citations_mean' ? 1 : 0 }),
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
                { decimals: metric === 'citations_mean' ? 1 : 0 },
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

    renderChart('journal-profile-output-chart', buildOutputChart(data));
    renderChart('journal-profile-impact-chart', buildImpactChart(data));
    renderChart('journal-profile-top-share-chart', buildTopShareChart(data));
    renderChart(
      'journal-profile-category-radar',
      buildCategoryRadar(data, 'publications_total', gettext('Publications')),
    );
    renderChart(
      'journal-profile-category-citations-total-radar',
      buildCategoryRadar(data, 'citations_total', gettext('Total Citations')),
    );
    renderChart(
      'journal-profile-category-citations-mean-radar',
      buildCategoryRadar(data, 'citations_mean', gettext('Mean Citations')),
    );
    setTimeout(resizeAllCharts, 100);
  }

  function initJournalProfileCharts() {
    const dataElement = document.getElementById('journal-profile-data');
    if (!dataElement) return;

    try {
      const profileData = JSON.parse(dataElement.textContent);
      renderJournalProfileCharts(profileData);
    } catch (error) {
      console.error('Error initializing journal profile charts', error);
    }
  }

  function setProfileSelectDisabled(selectElement, disabled) {
    if (!selectElement) return;

    selectElement.disabled = Boolean(disabled);

    if (typeof $ !== 'undefined' && $.fn && $.fn.select2 && $(selectElement).hasClass('select2-hidden-accessible')) {
      $(selectElement).prop('disabled', Boolean(disabled)).trigger('change.select2');
    }
  }

  function bindProfileSelectChange(selectElement, handler) {
    if (!selectElement || typeof handler !== 'function') return;

    if (typeof $ !== 'undefined' && $.fn && $.fn.select2 && $(selectElement).hasClass('select2-hidden-accessible')) {
      $(selectElement).on('change.journalProfileControls', handler);
      return;
    }

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

    if (typeof $ !== 'undefined' && $.fn && $.fn.select2 && $(selectElement).hasClass('select2-hidden-accessible')) {
      $(selectElement).trigger('change.select2');
    }
  }

  function initJournalProfileControls() {
    const form = document.getElementById('journal-profile-controls-form');
    const publicationYearSelect = document.getElementById('journal-profile-publication-year-select');
    const categoryLevelSelect = document.querySelector('[data-profile-category-level]');
    const categorySelect = document.querySelector('[data-profile-category-id]');
    let latestCategoryOptionsRequest = 0;

    if (!form || !categoryLevelSelect) return;

    if (typeof $ !== 'undefined' && $.fn && $.fn.select2) {
      [publicationYearSelect, categoryLevelSelect, categorySelect].forEach(selectElement => {
        if (!selectElement || $(selectElement).hasClass('select2-hidden-accessible')) return;

        $(selectElement).select2({
          theme: 'bootstrap-5',
          width: '100%',
          allowClear: false,
        }).on('select2:open', journalMetricsCommon.focusSelect2SearchInput);
      });
    }

    async function refreshProfileCategoryOptions() {
      if (!categorySelect) return;

      const timeseriesUrl = String(form.getAttribute('data-profile-timeseries-url') || '').trim();
      const journalIssn = String(form.getAttribute('data-profile-journal-issn') || '').trim();
      if (!timeseriesUrl || !journalIssn) return;

      const requestId = ++latestCategoryOptionsRequest;
      const formData = new FormData(form);
      setProfileSelectDisabled(categorySelect, true);

      try {
        const params = new URLSearchParams();

        formData.forEach((value, key) => {
          const normalizedValue = String(value || '').trim();
          if (!normalizedValue) return;
          params.append(key, normalizedValue);
        });

        params.set('issn', journalIssn);

        const response = await fetch(`${timeseriesUrl}?${params.toString()}`);
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
    setChartNumberLocale(journalMetricsCommon.getConfigAttr(configElement, 'data-number-locale', ''));
    initJournalProfileCharts();
    initJournalProfileControls();
  });

  window.addEventListener('resize', resizeAllCharts);
})();
