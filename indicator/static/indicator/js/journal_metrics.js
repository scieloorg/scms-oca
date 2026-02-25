(function () {
  if (typeof window !== 'undefined' && typeof window.gettext !== 'function') {
    window.gettext = function (msgid) { return msgid; };
  }

  const chartInstances = {};
  const profileState = {
    journalTitle: '',
    journalIssn: '',
    selectedCategoryId: '',
    selectedCategoryLevel: '',
    selectedPublicationYear: '',
    appliedFilters: {},
  };
  const journalOptions = [];
  let isHandlingJournalChange = false;
  let isHandlingCategoryChange = false;

  function resizeAllCharts() {
    Object.values(chartInstances).forEach(chart => {
      if (chart && typeof chart.resize === 'function') {
        chart.resize();
      }
    });
  }

  function formatNumber(value, decimals) {
    if (value === null || value === undefined || value === '') return '-';
    const numericValue = Number(value);
    if (Number.isNaN(numericValue)) return '-';

    return new Intl.NumberFormat(undefined, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(numericValue);
  }

  function setBadgeState(id, enabled) {
    const badge = document.getElementById(id);
    if (!badge) return;

    badge.classList.remove('journal-source-badge--active', 'journal-source-badge--inactive');
    badge.classList.add(enabled ? 'journal-source-badge--active' : 'journal-source-badge--inactive');
    badge.setAttribute('aria-pressed', enabled ? 'true' : 'false');
  }

  function setProfileLoading(isLoading) {
    const loadingElement = document.getElementById('journal-profile-loading');

    if (loadingElement) {
      loadingElement.classList.toggle('d-none', !isLoading);
    }
  }

  function collectJournalOptions(tableElement) {
    const rows = Array.from(tableElement.querySelectorAll('tbody tr'));
    const uniqueJournalMap = new Map();

    rows.forEach(row => {
      const title = row.getAttribute('data-journal-title') || '';
      const issn = row.getAttribute('data-journal-issn') || '';
      const categoryId = row.getAttribute('data-category-id') || '';
      if (!title) return;

      const key = `${title}||${issn}`;
      if (!uniqueJournalMap.has(key)) {
        uniqueJournalMap.set(key, { key, title, issn, categoryId });
      }
    });

    journalOptions.length = 0;
    uniqueJournalMap.forEach(option => journalOptions.push(option));
  }

  function initProfileSelect2(modalElement) {
    if (typeof $ === 'undefined' || !$.fn || !$.fn.select2) return;

    const options = {
      theme: 'bootstrap-5',
      width: '100%',
      dropdownParent: modalElement ? $(modalElement) : undefined,
      allowClear: false,
    };

    const journalSelect = $('#journal-profile-journal-select');
    if (journalSelect.length) {
      journalSelect.select2({
        ...options,
        placeholder: gettext('Select a journal'),
      });
    }

    const categorySelect = $('#journal-profile-category-select');
    if (categorySelect.length) {
      categorySelect.select2({
        ...options,
        placeholder: gettext('Select a category'),
      });
    }

  }

  function updateJournalSelect(journalTitle, journalIssn) {
    const selectElement = document.getElementById('journal-profile-journal-select');
    if (!selectElement) return;

    selectElement.innerHTML = '';
    journalOptions.forEach(journal => {
      const option = document.createElement('option');
      option.value = journal.key;
      option.dataset.journalTitle = journal.title;
      option.dataset.journalIssn = journal.issn;
      option.textContent = journal.issn ? `${journal.title} (${journal.issn})` : journal.title;

      if (journal.title === (journalTitle || '') && journal.issn === (journalIssn || '')) {
        option.selected = true;
      }

      selectElement.appendChild(option);
    });

    if (!selectElement.value && selectElement.options.length) {
      selectElement.options[0].selected = true;
    }

    if (typeof $ !== 'undefined' && $.fn && $.fn.select2) {
      $(selectElement).trigger('change.select2');
    }
  }

  function updateCategorySelect(data) {
    const selectElement = document.getElementById('journal-profile-category-select');
    if (!selectElement) return;

    const categories = Array.isArray(data.available_categories) ? data.available_categories : [];
    const selectedCategoryId = data.selected_category_id || '';
    if (data.selected_category_level) {
      profileState.selectedCategoryLevel = data.selected_category_level;
    }

    selectElement.innerHTML = '';
    categories.forEach(category => {
      const option = document.createElement('option');
      option.value = category;
      option.textContent = category;
      if (category === selectedCategoryId) {
        option.selected = true;
      }
      selectElement.appendChild(option);
    });

    if (!categories.length) {
      const option = document.createElement('option');
      option.value = '';
      option.textContent = '-';
      option.selected = true;
      selectElement.appendChild(option);
    }

    if (typeof $ !== 'undefined' && $.fn && $.fn.select2) {
      $(selectElement).trigger('change.select2');
    }
  }

  function parseJournalOption(selectElement) {
    const value = (selectElement && selectElement.value) || '';
    const [journalTitle, journalIssn] = value.split('||');
    return {
      journalTitle: journalTitle || '',
      journalIssn: journalIssn || '',
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
    return {
      title: { text: gettext('Publications and Total Citations per Year') },
      tooltip: { trigger: 'axis' },
      legend: {
        data: [gettext('Publications'), gettext('Total Citations')],
        bottom: 0,
      },
      toolbox: {
        feature: {
          magicType: { type: ['line', 'bar'] },
          dataView: { show: true, readOnly: true },
          saveAsImage: { show: true },
          restore: { show: true },
        },
      },
      grid: { left: 10, right: 10, top: 60, bottom: 60, containLabel: true },
      xAxis: { type: 'category', data: data.years || [] },
      yAxis: [
        { type: 'value', name: gettext('Publications') },
        { type: 'value', name: gettext('Citations') },
      ],
      series: [
        {
          name: gettext('Publications'),
          type: 'bar',
          data: data.journal_publications_count_per_year || [],
        },
        {
          name: gettext('Total Citations'),
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          data: data.journal_citations_total_per_year || [],
        },
      ],
    };
  }

  function buildImpactChart(data) {
    return {
      title: { text: gettext('Cohort Impact and Mean Citations per Year') },
      tooltip: { trigger: 'axis' },
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
      toolbox: {
        feature: {
          magicType: { type: ['line', 'bar'] },
          dataView: { show: true, readOnly: true },
          saveAsImage: { show: true },
          restore: { show: true },
        },
      },
      grid: { left: 10, right: 10, top: 60, bottom: 80, containLabel: true },
      xAxis: { type: 'category', data: data.years || [] },
      yAxis: { type: 'value' },
      series: [
        {
          name: gettext('Cohort Impact (Total)'),
          type: 'line',
          smooth: true,
          data: data.journal_impact_normalized_per_year || [],
        },
        {
          name: gettext('Cohort Impact (2 years)'),
          type: 'line',
          smooth: true,
          data: data.journal_impact_normalized_window_2y_per_year || [],
        },
        {
          name: gettext('Cohort Impact (3 years)'),
          type: 'line',
          smooth: true,
          data: data.journal_impact_normalized_window_3y_per_year || [],
        },
        {
          name: gettext('Cohort Impact (5 years)'),
          type: 'line',
          smooth: true,
          data: data.journal_impact_normalized_window_5y_per_year || [],
        },
        {
          name: gettext('Mean Citations'),
          type: 'line',
          smooth: true,
          data: data.journal_citations_mean_per_year || [],
        },
      ],
    };
  }

  function buildTopShareChart(data) {
    return {
      title: { text: gettext('Top Publications Share (%) per Year') },
      tooltip: { trigger: 'axis' },
      legend: {
        data: [gettext('Top 1%'), gettext('Top 5%'), gettext('Top 10%'), gettext('Top 50%')],
        bottom: 0,
      },
      toolbox: {
        feature: {
          magicType: { type: ['line', 'bar'] },
          dataView: { show: true, readOnly: true },
          saveAsImage: { show: true },
          restore: { show: true },
        },
      },
      grid: { left: 10, right: 10, top: 60, bottom: 60, containLabel: true },
      xAxis: { type: 'category', data: data.years || [] },
      yAxis: { type: 'value', name: '%' },
      series: [
        {
          name: gettext('Top 1%'),
          type: 'line',
          smooth: true,
          data: data.top_1pct_all_time_publications_share_pct_per_year || [],
        },
        {
          name: gettext('Top 5%'),
          type: 'line',
          smooth: true,
          data: data.top_5pct_all_time_publications_share_pct_per_year || [],
        },
        {
          name: gettext('Top 10%'),
          type: 'line',
          smooth: true,
          data: data.top_10pct_all_time_publications_share_pct_per_year || [],
        },
        {
          name: gettext('Top 50%'),
          type: 'line',
          smooth: true,
          data: data.top_50pct_all_time_publications_share_pct_per_year || [],
        },
      ],
    };
  }

  function buildCategoryRadar(data, metric, metricLabel) {
    const entries = Array.isArray(data.category_publications_spider)
      ? data.category_publications_spider
      : [];

    if (!entries.length) {
      return {
        title: { text: `${metricLabel} ${gettext('by Category')}` },
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
      tooltip: {
        trigger: 'item',
        formatter: function () {
          return entries
            .map((item, index) => `${item.category}: ${values[index]}`)
            .join('<br/>');
        },
      },
      radar: {
        radius: '65%',
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

  function renderJournalProfile(data) {
    const panel = document.getElementById('journal-profile-panel');
    if (!panel) return;

    const snapshots = Array.isArray(data.annual_snapshots) ? data.annual_snapshots : [];
    const selectedPublicationYear = String(profileState.selectedPublicationYear || '').trim();
    let selectedYearMetrics = data.latest_year_metrics || {};
    if (selectedPublicationYear) {
      const selectedYearInt = Number.parseInt(selectedPublicationYear, 10);
      const matchedSnapshot = snapshots.find(item => Number(item.publication_year) === selectedYearInt);
      selectedYearMetrics = matchedSnapshot || {};
    }

    profileState.selectedCategoryId = data.selected_category_id || profileState.selectedCategoryId;

    const profileTitle = document.getElementById('journal-profile-title');
    const profileSubtitle = document.getElementById('journal-profile-subtitle');
    const profileYear = document.getElementById('journal-profile-year');

    if (profileTitle) {
      profileTitle.textContent = data.journal_title || gettext('Journal profile');
    }

    const subtitleParts = [];
    if (data.journal_issn) subtitleParts.push(`ISSN: ${data.journal_issn}`);
    if (selectedYearMetrics.country || data.country) {
      subtitleParts.push(selectedYearMetrics.country || data.country);
    }
    if (selectedYearMetrics.publisher_name || data.publisher_name) {
      subtitleParts.push(selectedYearMetrics.publisher_name || data.publisher_name);
    }
    if (selectedYearMetrics.collection || data.collection) {
      subtitleParts.push(selectedYearMetrics.collection || data.collection);
    }

    if (profileSubtitle) {
      profileSubtitle.textContent = subtitleParts.join(' | ');
    }

    if (profileYear) {
      profileYear.textContent = selectedPublicationYear
        ? `${gettext('Publication year')}: ${selectedPublicationYear}`
        : '';
    }

    const setText = (id, value) => {
      const element = document.getElementById(id);
      if (element) element.textContent = value;
    };

    const top10Share = formatNumber(selectedYearMetrics.top_10pct_all_time_publications_share_pct, 1);

    setText('kpi-publications', formatNumber(selectedYearMetrics.journal_publications_count, 0));
    setText('kpi-total-citations', formatNumber(selectedYearMetrics.journal_citations_total, 0));
    setText('kpi-mean-citations', formatNumber(selectedYearMetrics.journal_citations_mean, 1));
    setText('kpi-impact', formatNumber(selectedYearMetrics.journal_impact_normalized, 1));
    setText('kpi-top10', top10Share === '-' ? '-' : `${top10Share}%`);

    setBadgeState('badge-scielo', Boolean(selectedYearMetrics.is_scielo));
    setBadgeState('badge-scopus', Boolean(selectedYearMetrics.is_scopus));
    setBadgeState('badge-wos', Boolean(selectedYearMetrics.is_wos));
    setBadgeState('badge-doaj', Boolean(selectedYearMetrics.is_doaj));
    setBadgeState('badge-openalex', Boolean(selectedYearMetrics.is_openalex));
    setBadgeState('badge-multilingual', Boolean(selectedYearMetrics.is_journal_multilingual));

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

    updateCategorySelect(data);
    updateJournalSelect(data.journal_title, data.journal_issn);

    setProfileLoading(false);
    panel.classList.remove('d-none');
    setTimeout(resizeAllCharts, 100);
  }

  async function fetchJournalTimeseries(baseUrl) {
    const params = new URLSearchParams();

    const passthroughFilters = profileState.appliedFilters || {};
    const excludedKeys = new Set([
      'csrfmiddlewaretoken',
      'journal_title',
      'journal_issn',
      'category_id',
      'category_level',
      'publication_year',
      'year',
      'ranking_metric',
      'limit',
    ]);

    Object.entries(passthroughFilters).forEach(([key, value]) => {
      if (excludedKeys.has(key)) return;
      if (value === null || value === undefined || value === '') return;

      if (Array.isArray(value)) {
        value.forEach(item => {
          if (item === null || item === undefined || item === '') return;
          params.append(key, String(item));
        });
        return;
      }

      params.set(key, String(value));
    });

    if (profileState.journalTitle) params.set('journal_title', profileState.journalTitle);
    if (profileState.journalIssn) params.set('journal_issn', profileState.journalIssn);
    if (profileState.selectedCategoryId) params.set('category_id', profileState.selectedCategoryId);
    if (profileState.selectedCategoryLevel) {
      params.set('category_level', profileState.selectedCategoryLevel);
    }
    if (profileState.selectedPublicationYear) {
      params.set('publication_year', profileState.selectedPublicationYear);
    }

    const response = await fetch(`${baseUrl}?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch timeseries: ${response.status}`);
    }

    return response.json();
  }

  async function loadAndRenderProfile(baseUrl) {
    if (!profileState.journalTitle && !profileState.journalIssn) return;
    setProfileLoading(true);
    try {
      const data = await fetchJournalTimeseries(baseUrl);
      renderJournalProfile(data);
    } finally {
      setProfileLoading(false);
    }
  }

  function markSelectedRow(tableElement) {
    const rows = tableElement.querySelectorAll('tbody tr');
    rows.forEach(row => {
      const rowTitle = row.getAttribute('data-journal-title') || '';
      const rowIssn = row.getAttribute('data-journal-issn') || '';
      row.classList.toggle(
        'table-active',
        rowTitle === profileState.journalTitle && rowIssn === profileState.journalIssn,
      );
    });
  }

  async function selectJournal(baseUrl, journalTitle, journalIssn, categoryId, categoryLevel) {
    profileState.journalTitle = journalTitle || '';
    profileState.journalIssn = journalIssn || '';
    profileState.selectedCategoryId = categoryId || '';
    if (typeof categoryLevel === 'string' && categoryLevel.trim()) {
      profileState.selectedCategoryLevel = categoryLevel.trim();
    }
    await loadAndRenderProfile(baseUrl);
  }

  function attachRowSelection(tableElement, baseUrl, modalInstance) {
    tableElement.addEventListener('click', async event => {
      const row = event.target.closest('tbody tr');
      if (!row) return;

      const journalTitle = row.getAttribute('data-journal-title') || '';
      const journalIssn = row.getAttribute('data-journal-issn') || '';
      const categoryLevel = row.getAttribute('data-category-level') || '';

      try {
        if (modalInstance) {
          modalInstance.show();
        }
        setProfileLoading(true);
        // Let the backend choose the default category (highest publications in selected year).
        await selectJournal(baseUrl, journalTitle, journalIssn, '', categoryLevel);
        markSelectedRow(tableElement);
      } catch (error) {
        console.error(error);
        setProfileLoading(false);
      }
    });
  }

  function initRankingDataTable() {
    const tableContainer = document.getElementById('ranking-container');

    if (typeof $ === 'undefined' || !$.fn || !$.fn.DataTable) {
      if (tableContainer) {
        tableContainer.classList.remove('is-invisible');
      }
      return;
    }

    $('#ranking-table').DataTable({
      columns: [
        { type: 'num' },
        { type: 'num' },
        { type: 'string' },
        { type: 'string' },
        { type: 'string' },
        { type: 'string' },
        { type: 'string' },
        { type: 'string' },
        { type: 'num' },
        { type: 'num' },
        { type: 'num' },
        { type: 'num' },
        { type: 'num' },
        { type: 'num' },
      ],
      order: [[0, 'asc']],
      scrollX: true,
      pageLength: 25,
      layout: {
        topStart: {
          buttons: ['copy', 'csv'],
        },
        bottomStart: 'pageLength',
      },
      initComplete: function () {
        if (tableContainer) {
          tableContainer.classList.remove('is-invisible');
        }
      },
    });
  }

  function getModalController(modalElement) {
    if (!modalElement) return null;

    if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
      if (typeof bootstrap.Modal.getOrCreateInstance === 'function') {
        return bootstrap.Modal.getOrCreateInstance(modalElement);
      }
      if (typeof bootstrap.Modal.getInstance === 'function') {
        return bootstrap.Modal.getInstance(modalElement) || new bootstrap.Modal(modalElement);
      }
      try {
        return new bootstrap.Modal(modalElement);
      } catch (error) {
        console.error(error);
      }
    }

    if (typeof $ !== 'undefined' && $.fn && $.fn.modal) {
      return {
        show: function () {
          $(modalElement).modal('show');
        },
      };
    }

    return null;
  }

  function getFilterConfigAttr(configElement, attrName, fallback = '') {
    if (!configElement) return fallback;
    const value = configElement.getAttribute(attrName);
    if (value === null || value === undefined || value === '') return fallback;
    return value;
  }

  function parseAppliedFilters(rawAppliedFilters) {
    if (!rawAppliedFilters) return {};
    try {
      const parsed = JSON.parse(rawAppliedFilters);
      return parsed && typeof parsed === 'object' ? parsed : {};
    } catch (error) {
      console.error('Error parsing journal metrics filters payload', error);
      return {};
    }
  }

  function focusSelect2SearchInput(event) {
    const targetId = event?.target?.id;
    if (!targetId) return;
    const searchInput = document.querySelector(`[aria-controls="select2-${targetId}-results"]`);
    if (searchInput) {
      searchInput.focus();
    }
  }

  async function initJournalMetricsFilters() {
    const configElement = document.getElementById('journal-metrics-filters-config');
    if (!configElement) return;

    try {
      const appliedFilters = parseAppliedFilters(
        getFilterConfigAttr(configElement, 'data-applied-filters', '{}'),
      );
      const defaultCategoryLevel = String(
        appliedFilters.category_level
        || getFilterConfigAttr(configElement, 'data-default-category-level', 'field'),
      ).trim().toLowerCase() || 'field';

      const placeholders = {
        anyValue: getFilterConfigAttr(configElement, 'data-any-value-placeholder', gettext('Any value')),
        country: getFilterConfigAttr(configElement, 'data-placeholder-country', gettext('Select a country')),
        collection: getFilterConfigAttr(configElement, 'data-placeholder-collection', gettext('Select a collection')),
        categoryLevel: getFilterConfigAttr(
          configElement,
          'data-placeholder-category-level',
          gettext('Select a category type'),
        ),
        rankingMetric: getFilterConfigAttr(
          configElement,
          'data-placeholder-ranking-metric',
          gettext('Select a ranking metric'),
        ),
        selectValue: getFilterConfigAttr(configElement, 'data-placeholder-select-value', gettext('Select a value')),
        journalTitle: getFilterConfigAttr(
          configElement,
          'data-placeholder-journal-title',
          gettext('Type journal name...'),
        ),
        journalIssn: getFilterConfigAttr(configElement, 'data-placeholder-journal-issn', gettext('Type ISSN...')),
        publisherName: getFilterConfigAttr(
          configElement,
          'data-placeholder-publisher-name',
          gettext('Type publisher name...'),
        ),
        categoryId: getFilterConfigAttr(
          configElement,
          'data-placeholder-category-id',
          gettext('Select a category id'),
        ),
        typeToSearch: getFilterConfigAttr(configElement, 'data-placeholder-type-to-search', gettext('Type to search...')),
      };

      const simpleSelectFields = [
        'is_scielo',
        'is_scopus',
        'is_wos',
        'is_doaj',
        'is_openalex',
        'is_journal_multilingual',
        'limit',
      ];

      try {
        simpleSelectFields.forEach(fieldId => {
          const selectElement = document.getElementById(fieldId);
          if (!selectElement || typeof $ === 'undefined' || !$.fn || !$.fn.select2) return;

          $(selectElement).select2({
            placeholder: placeholders.anyValue || '',
            allowClear: true,
            minimumResultsForSearch: Infinity,
            theme: 'bootstrap-5',
          }).on('select2:open', focusSelect2SearchInput);
        });
      } catch (error) {
        console.error('Error initializing basic journal metrics Select2 fields', error);
      }

      setupDatePicker('publication_year', 'yyyy', 'years', 'years', true, '1800', '2100', 'body', 'bottom auto', 2000);

      const searchableSingleSelectFields = [
        'country',
        'collection',
        'category_level',
        'ranking_metric',
      ];

      const searchableSinglePlaceholders = {
        country: placeholders.country,
        collection: placeholders.collection,
        category_level: placeholders.categoryLevel,
        ranking_metric: placeholders.rankingMetric,
      };

      searchableSingleSelectFields.forEach(fieldId => {
        const selectElement = document.getElementById(fieldId);
        if (!selectElement || typeof $ === 'undefined' || !$.fn || !$.fn.select2) return;

        $(selectElement).select2({
          placeholder: searchableSinglePlaceholders[fieldId] || placeholders.selectValue,
          allowClear: fieldId !== 'category_level',
          theme: 'bootstrap-5',
        }).on('select2:open', focusSelect2SearchInput);
      });

      const categoryLevelSelect = document.getElementById('category_level');
      if (categoryLevelSelect && !String(categoryLevelSelect.value || '').trim()) {
        const hasDefaultOption = Array.from(categoryLevelSelect.options || [])
          .some(option => option.value === defaultCategoryLevel);
        if (!hasDefaultOption) {
          categoryLevelSelect.add(new Option(defaultCategoryLevel, defaultCategoryLevel, false, false));
        }
        categoryLevelSelect.value = defaultCategoryLevel;
        if (typeof $ !== 'undefined' && $.fn && $.fn.select2) {
          $(categoryLevelSelect).trigger('change.select2');
        }
      }

      const specialSelectConfig = {
        journal_title: {
          placeholder: placeholders.journalTitle,
          minimumInputLength: 2,
        },
        journal_issn: {
          placeholder: placeholders.journalIssn,
          minimumInputLength: 2,
        },
        publisher_name: {
          placeholder: placeholders.publisherName,
          minimumInputLength: 2,
        },
        category_id: {
          placeholder: placeholders.categoryId,
          minimumInputLength: 0,
        },
      };

      const formatSearchOptionText = item => item.label || item.key;

      const appendOptionIfMissing = (selectElement, value, text, selected = false) => {
        if (!selectElement || !value) return;
        const normalizedValue = String(value);
        const alreadyExists = Array.from(selectElement.options)
          .some(option => option.value === normalizedValue);
        if (!alreadyExists) {
          const option = new Option(text || normalizedValue, normalizedValue, selected, selected);
          selectElement.add(option);
          return;
        }

        if (selected) {
          selectElement.value = normalizedValue;
        }
      };

      const buildSearchItemUrl = (fieldId, queryTerm = '') => {
        const params = new URLSearchParams({
          field_name: fieldId,
          data_source: 'journal_metrics',
          q: queryTerm || '',
        });

        if (fieldId === 'category_id') {
          const categoryLevelElement = document.getElementById('category_level');
          const categoryLevelValue = (categoryLevelElement ? categoryLevelElement.value : '') || defaultCategoryLevel;
          params.set('category_level', categoryLevelValue);
        }

        return `/search-gateway/search-item/?${params.toString()}`;
      };

      const preloadSpecialSelectOptions = async (fieldId, selectedValue = null) => {
        const fieldConfig = specialSelectConfig[fieldId];
        const selectElement = document.getElementById(fieldId);
        if (!fieldConfig || !selectElement) return;

        if (fieldId === 'category_id') {
          selectElement.innerHTML = '<option></option>';
        }

        try {
          const response = await fetch(buildSearchItemUrl(fieldId, ''));
          if (!response.ok) return;

          const data = await response.json();
          const results = Array.isArray(data.results) ? data.results : [];
          results.forEach(item => {
            appendOptionIfMissing(selectElement, item.key, formatSearchOptionText(item));
          });

          if (selectedValue) {
            appendOptionIfMissing(selectElement, selectedValue, selectedValue, true);
          } else if (fieldId === 'category_id') {
            selectElement.value = '';
          }

          if (typeof $ !== 'undefined' && $.fn && $.fn.select2) {
            $(selectElement).trigger('change.select2');
          }
        } catch (error) {
          console.error(`Error preloading options for ${fieldId}`, error);
        }
      };

      Object.entries(specialSelectConfig).forEach(([fieldId, fieldConfig]) => {
        const selectElement = document.getElementById(fieldId);
        if (!selectElement || typeof $ === 'undefined' || !$.fn || !$.fn.select2) return;

        $(selectElement).select2({
          ajax: {
            url: () => '/search-gateway/search-item/',
            dataType: 'json',
            delay: 300,
            data: params => {
              const requestParams = {
                field_name: fieldId,
                data_source: 'journal_metrics',
                q: params.term || '',
              };

              if (fieldId === 'category_id') {
                const categoryLevelElement = document.getElementById('category_level');
                const categoryLevelValue = (categoryLevelElement ? categoryLevelElement.value : '') || defaultCategoryLevel;
                requestParams.category_level = categoryLevelValue;
              }

              return requestParams;
            },
            processResults: data => ({
              results: (data.results || []).map(item => ({
                id: item.key,
                text: formatSearchOptionText(item),
              })),
            }),
          },
          minimumInputLength: fieldConfig.minimumInputLength,
          placeholder: fieldConfig.placeholder || placeholders.typeToSearch,
          theme: 'bootstrap-5',
          allowClear: true,
        }).on('select2:open', focusSelect2SearchInput);

        if (fieldId !== 'category_id' && appliedFilters[fieldId]) {
          appendOptionIfMissing(selectElement, appliedFilters[fieldId], appliedFilters[fieldId], true);
          $(selectElement).trigger('change');
        }
      });

      await preloadSpecialSelectOptions('category_id', appliedFilters.category_id || null);

      const categoryLevelElement = document.getElementById('category_level');
      if (categoryLevelElement) {
        categoryLevelElement.addEventListener('change', function () {
          if (!String(this.value || '').trim()) {
            this.value = defaultCategoryLevel;
            if (typeof $ !== 'undefined' && $.fn && $.fn.select2) {
              $(this).trigger('change.select2');
            }
          }

          const categoryIdElement = document.getElementById('category_id');
          if (categoryIdElement && typeof $ !== 'undefined' && $.fn && $.fn.select2) {
            $(categoryIdElement).val(null).trigger('change');
          } else if (categoryIdElement) {
            categoryIdElement.value = '';
          }

          preloadSpecialSelectOptions('category_id');
        });
      }

      const resetButton = document.getElementById('menu-reset-journal-metrics');
      if (resetButton) {
        resetButton.addEventListener('click', function (event) {
          event.preventDefault();
          const resetUrl = `${window.location.pathname}${window.location.search}`;
          window.location.assign(resetUrl);
        });
      }
    } catch (error) {
      console.error('Error initializing journal metrics filter controls', error);
    } finally {
      document.dispatchEvent(new CustomEvent('indicator:filters-ready', {
        detail: { dataSource: 'journal_metrics' },
      }));
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    initJournalMetricsFilters();

    const rankingTable = document.getElementById('ranking-table');
    const configElement = document.getElementById('journal-metrics-config');
    const modalElement = document.getElementById('journal-profile-modal');

    if (!rankingTable || !configElement) return;

    const baseUrl = configElement.getAttribute('data-timeseries-url');
    const selectedCategoryLevelAttr =
      (configElement.getAttribute('data-selected-category-level') || '').trim().toLowerCase();
    const selectedPublicationYearAttr =
      (configElement.getAttribute('data-selected-publication-year') || '').trim();
    const appliedFiltersRaw = configElement.getAttribute('data-applied-filters') || '{}';
    try {
      profileState.appliedFilters = JSON.parse(appliedFiltersRaw);
    } catch (error) {
      console.error('Error parsing applied filters payload', error);
      profileState.appliedFilters = {};
    }

    profileState.selectedCategoryLevel = selectedCategoryLevelAttr || 'field';
    profileState.selectedPublicationYear = selectedPublicationYearAttr || '2020';
    collectJournalOptions(rankingTable);
    initRankingDataTable();

    const modalInstance = getModalController(modalElement);

    initProfileSelect2(modalElement);
    updateJournalSelect('', '');
    attachRowSelection(rankingTable, baseUrl, modalInstance);

    const journalSelect = document.getElementById('journal-profile-journal-select');
    if (journalSelect) {
      const handleJournalChange = async function () {
        if (isHandlingJournalChange) return;
        isHandlingJournalChange = true;

        try {
          const { journalTitle, journalIssn } = parseJournalOption(this);
          await selectJournal(baseUrl, journalTitle, journalIssn, '');
          markSelectedRow(rankingTable);
        } catch (error) {
          console.error(error);
        } finally {
          isHandlingJournalChange = false;
        }
      };

      journalSelect.addEventListener('change', handleJournalChange);
      if (typeof $ !== 'undefined' && $.fn && $.fn.select2) {
        $(journalSelect).on('select2:select', handleJournalChange);
      }
    }

    const categorySelect = document.getElementById('journal-profile-category-select');
    if (categorySelect) {
      const handleCategoryChange = async function () {
        if (isHandlingCategoryChange) return;
        isHandlingCategoryChange = true;

        try {
          profileState.selectedCategoryId = this.value || '';
          await loadAndRenderProfile(baseUrl);
        } catch (error) {
          console.error(error);
        } finally {
          isHandlingCategoryChange = false;
        }
      };

      categorySelect.addEventListener('change', handleCategoryChange);
      if (typeof $ !== 'undefined' && $.fn && $.fn.select2) {
        $(categorySelect).on('select2:select', handleCategoryChange);
      }
    }

    if (modalElement) {
      modalElement.addEventListener('shown.bs.modal', () => {
        setTimeout(resizeAllCharts, 120);
      });
    }
  });

  window.addEventListener('resize', resizeAllCharts);
})();
