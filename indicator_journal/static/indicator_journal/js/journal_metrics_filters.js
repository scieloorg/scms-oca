(function () {
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

  function buildColumnsFromTable(tableId) {
    const headerCells = document.querySelectorAll(`#${tableId} thead th`);
    return Array.from(headerCells).map((_, i) => {
      if (i < 2) return { type: 'num' };
      if (i >= 2 && i <= 6) return { type: 'string' };
      return { type: 'num' };
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
      columns: buildColumnsFromTable('ranking-table'),
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

  function buildCleanJournalMetricsQueryParams(form) {
    const params = new URLSearchParams();
    if (!form || !window.SearchGatewayFilterForm || typeof window.SearchGatewayFilterForm.serializeForm !== 'function') {
      return params;
    }

    const payload = window.SearchGatewayFilterForm.serializeForm(form) || {};
    Object.entries(payload).forEach(([key, value]) => {
      if (!key || value === null || value === undefined) return;

      if (Array.isArray(value)) {
        value.forEach(item => {
          const normalized = String(item ?? '').trim();
          if (!normalized) return;
          params.append(key, normalized);
        });
        return;
      }

      const normalized = String(value).trim();
      if (!normalized) return;
      params.append(key, normalized);
    });

    return params;
  }

  function submitJournalMetricsFormWithCleanQuery(form) {
    if (!form) return;

    const action = form.getAttribute('action') || window.location.pathname;
    const params = buildCleanJournalMetricsQueryParams(form);
    const queryString = params.toString();
    const nextUrl = queryString ? `${action}?${queryString}` : action;
    window.location.assign(nextUrl);
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
        if (element.checked) appendFormFieldParams(params, element.name, element.value);
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
    const root = configRoot || document.querySelector('[data-indicator-config]');
    if (!root) return;

    const formId = String(root.dataset.configFormId || '').trim();
    const form = formId ? document.getElementById(formId) : null;
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
      if (!response.ok) throw new Error(`Unable to load category options (${response.status})`);

      const data = await response.json();
      const results = Array.isArray(data?.results) ? data.results : [];
      const allowClear = String(categorySelect.dataset.allowClear || '').toLowerCase() === 'true';
      const placeholderText = window.gettext ? window.gettext('Selecione uma opção') : 'Selecione uma opção';

      categorySelect.innerHTML = '';
      if (allowClear) categorySelect.add(new Option(placeholderText, '', false, false));

      const availableValues = [];
      results.forEach(option => {
        const optionValue = String(option?.value ?? option?.key ?? '').trim();
        if (!optionValue) return;
        const optionLabel = String(option?.label ?? optionValue).trim();
        categorySelect.add(new Option(optionLabel, optionValue, false, false));
        availableValues.push(optionValue);
      });

      const fallbackValue = availableValues.includes(currentValue) ? currentValue : (availableValues[0] || '');
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
    const configRoot = document.querySelector('[data-indicator-config]');
    if (!configRoot) return;

    const categoryLevelSelect = configRoot.querySelector('#indicator-config-category_level');
    if (categoryLevelSelect && categoryLevelSelect.dataset.categoryRefreshBound !== 'true') {
      categoryLevelSelect.addEventListener('change', () => updateJournalMetricsCategoryOptions(configRoot));
      categoryLevelSelect.dataset.categoryRefreshBound = 'true';
    }

    if (categoryLevelSelect && configRoot.dataset.categoryInitialRefreshDone !== 'true') {
      updateJournalMetricsCategoryOptions(configRoot);
      configRoot.dataset.categoryInitialRefreshDone = 'true';
    }
  }

  function initJournalMetricsAppliedFiltersAutoSubmit() {
    const configRoot = document.querySelector('[data-indicator-config]');
    const formId = String(configRoot?.dataset?.configFormId || '').trim();
    const form = formId ? document.getElementById(formId) : null;
    if (!form || form.dataset.appliedFiltersAutoSubmitBound === 'true') return;

    form.addEventListener('submit', event => {
      const method = String(form.getAttribute('method') || 'get').trim().toLowerCase();
      if (method !== 'get') return;
      event.preventDefault();
      submitJournalMetricsFormWithCleanQuery(form);
    });

    form.addEventListener('search-gateway:filters-changed', event => {
      const reason = String(event?.detail?.reason || '').trim();
      if (!['remove-applied-filter', 'reset'].includes(reason)) return;
      submitJournalMetricsFormWithCleanQuery(form);
    });

    form.dataset.appliedFiltersAutoSubmitBound = 'true';
  }

  function initJournalMetricsResetControls() {
    document.querySelectorAll('.sg-filter-sidebar__btn--clear[data-form-id]').forEach(button => {
      if (button.dataset.journalMetricsResetBound === 'true') return;

      button.addEventListener('click', event => {
        const formId = String(button.dataset.formId || '').trim();
        const form = formId ? document.getElementById(formId) : null;
        if (!form) return;

        event.preventDefault();
        if (window.SearchGatewayFilterForm?.resetForm) {
          window.SearchGatewayFilterForm.resetForm(form);
        } else {
          form.reset();
          submitJournalMetricsFormWithCleanQuery(form);
        }
      });

      button.dataset.journalMetricsResetBound = 'true';
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    initRankingDataTable();
    initJournalMetricsConfigControls();
    initJournalMetricsAppliedFiltersAutoSubmit();
    initJournalMetricsResetControls();
  });
})();
