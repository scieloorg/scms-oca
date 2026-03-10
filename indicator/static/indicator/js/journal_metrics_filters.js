(function () {
  if (typeof window !== 'undefined' && typeof window.gettext !== 'function') {
    window.gettext = function (msgid) { return msgid; };
  }

  const journalMetricsCommon = window.JournalMetrics || {};

  function initRankingTopScroll(dataTableContainer) {
    if (!dataTableContainer) return;

    const scrollBody = dataTableContainer.querySelector('.dt-scroll-body');
    const scrollWrapper = dataTableContainer.querySelector('.dt-scroll');
    if (!scrollBody || !scrollWrapper) return;

    const existingTopScroll = dataTableContainer.querySelector('.dt-scroll-top');
    if (existingTopScroll) {
      existingTopScroll.remove();
    }

    const topScroll = document.createElement('div');
    topScroll.className = 'dt-scroll-top';

    const topScrollContent = document.createElement('div');
    topScrollContent.className = 'dt-scroll-top__content';
    topScroll.appendChild(topScrollContent);

    scrollWrapper.parentNode.insertBefore(topScroll, scrollWrapper);

    let isSyncing = false;

    const syncTopFromBody = () => {
      if (isSyncing) return;
      isSyncing = true;
      topScroll.scrollLeft = scrollBody.scrollLeft;
      isSyncing = false;
    };

    const syncBodyFromTop = () => {
      if (isSyncing) return;
      isSyncing = true;
      scrollBody.scrollLeft = topScroll.scrollLeft;
      isSyncing = false;
    };

    const updateTopScroll = () => {
      const tableElement = scrollBody.querySelector('table');
      const scrollWidth = tableElement ? tableElement.scrollWidth : scrollBody.scrollWidth;
      topScrollContent.style.width = `${scrollWidth}px`;
      topScroll.classList.toggle('dt-scroll-top--hidden', scrollWidth <= scrollBody.clientWidth);
      topScroll.scrollLeft = scrollBody.scrollLeft;
    };

    topScroll.addEventListener('scroll', syncBodyFromTop);
    scrollBody.addEventListener('scroll', syncTopFromBody);

    if (typeof ResizeObserver !== 'undefined') {
      const resizeObserver = new ResizeObserver(updateTopScroll);
      resizeObserver.observe(scrollBody);
      const tableElement = scrollBody.querySelector('table');
      if (tableElement) {
        resizeObserver.observe(tableElement);
      }
    } else {
      window.addEventListener('resize', updateTopScroll, { passive: true });
    }

    updateTopScroll();
    window.requestAnimationFrame(updateTopScroll);
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
        initRankingTopScroll(this.api().table().container());
        if (tableContainer) {
          tableContainer.classList.remove('is-invisible');
        }
      },
    });
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

  async function initJournalMetricsFilters() {
    const configElement = document.getElementById('journal-metrics-filters-config');
    if (!configElement) return;

    try {
      const appliedFilters = parseAppliedFilters(
        journalMetricsCommon.getConfigAttr(configElement, 'data-applied-filters', '{}'),
      );
      const defaultCategoryLevel = String(
        appliedFilters.category_level
        || journalMetricsCommon.getConfigAttr(configElement, 'data-default-category-level', 'field'),
      ).trim().toLowerCase() || 'field';
      const defaultCategoryId = String(
        appliedFilters.category_id
        || journalMetricsCommon.getConfigAttr(configElement, 'data-default-category-id', ''),
      ).trim();

      const placeholders = {
        anyValue: journalMetricsCommon.getConfigAttr(configElement, 'data-any-value-placeholder', gettext('Any value')),
        country: journalMetricsCommon.getConfigAttr(configElement, 'data-placeholder-country', gettext('Select a country')),
        collection: journalMetricsCommon.getConfigAttr(configElement, 'data-placeholder-collection', gettext('Select a collection')),
        categoryLevel: journalMetricsCommon.getConfigAttr(
          configElement,
          'data-placeholder-category-level',
          gettext('Select a category type'),
        ),
        rankingMetric: journalMetricsCommon.getConfigAttr(
          configElement,
          'data-placeholder-ranking-metric',
          gettext('Select a ranking metric'),
        ),
        selectValue: journalMetricsCommon.getConfigAttr(configElement, 'data-placeholder-select-value', gettext('Select a value')),
        journalTitle: journalMetricsCommon.getConfigAttr(
          configElement,
          'data-placeholder-journal-title',
          gettext('Type journal name...'),
        ),
        journalIssn: journalMetricsCommon.getConfigAttr(
          configElement,
          'data-placeholder-journal-issn',
          gettext('Type ISSN...'),
        ),
        publisherName: journalMetricsCommon.getConfigAttr(
          configElement,
          'data-placeholder-publisher-name',
          gettext('Type publisher name...'),
        ),
        categoryId: journalMetricsCommon.getConfigAttr(
          configElement,
          'data-placeholder-category-id',
          gettext('Select a category id'),
        ),
        typeToSearch: journalMetricsCommon.getConfigAttr(
          configElement,
          'data-placeholder-type-to-search',
          gettext('Type to search...'),
        ),
      };

      const simpleSelectFields = [
        'is_scielo',
        'is_scopus',
        'is_wos',
        'is_doaj',
        'is_journal_oa',
        'is_openalex',
        'is_journal_multilingual',
        'limit',
      ];

      try {
        simpleSelectFields.forEach(fieldId => {
          const selectElement = document.getElementById(fieldId);
          if (!selectElement || selectElement.tagName !== 'SELECT' || typeof $ === 'undefined' || !$.fn || !$.fn.select2) return;

          $(selectElement).select2({
            placeholder: placeholders.anyValue || '',
            allowClear: true,
            minimumResultsForSearch: Infinity,
            theme: 'bootstrap-5',
          }).on('select2:open', journalMetricsCommon.focusSelect2SearchInput);
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
        }).on('select2:open', journalMetricsCommon.focusSelect2SearchInput);
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
        }).on('select2:open', journalMetricsCommon.focusSelect2SearchInput);

        if (fieldId !== 'category_id' && appliedFilters[fieldId]) {
          appendOptionIfMissing(selectElement, appliedFilters[fieldId], appliedFilters[fieldId], true);
          $(selectElement).trigger('change');
        }
      });

      await preloadSpecialSelectOptions('category_id', appliedFilters.category_id || defaultCategoryId || null);

      if (categoryLevelSelect) {
        categoryLevelSelect.addEventListener('change', function () {
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

    if (document.getElementById('ranking-table')) {
      initRankingDataTable();
    }
  });
})();
