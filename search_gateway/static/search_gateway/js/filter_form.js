(function () {
  const lookupInitialOptionsCache = new Map();
  const FACET_REFRESH_ANIMATION_MS = 220;

  function translateText(msgid) {
    if (typeof window !== 'undefined' && typeof window.gettext === 'function') {
      return window.gettext(msgid);
    }
    return msgid;
  }

  function getFormFromNode(node) {
    return node?.form || node?.closest('form') || null;
  }

  function getFilterForms(root) {
    if (!root) {
      return Array.from(document.querySelectorAll('form.data-source-filter-form'));
    }
    if (root.matches?.('form.data-source-filter-form')) {
      return [root];
    }
    return Array.from(root.querySelectorAll('form.data-source-filter-form'));
  }

  function appendValue(payload, name, value) {
    if (value === null || value === undefined || value === '') return;
    if (Object.prototype.hasOwnProperty.call(payload, name)) {
      if (!Array.isArray(payload[name])) {
        payload[name] = [payload[name]];
      }
      payload[name].push(value);
      return;
    }
    payload[name] = value;
  }

  function syncSelectPlaceholderState(select) {
    if (!select) return;

    const hasValue = Array.from(select.selectedOptions || [])
      .some(option => String(option.value || '').trim());
    const allowClear = String(select.dataset.allowClear || '').toLowerCase() === 'true'
      || Array.from(select.options || []).some(option => !String(option.value || '').trim());

    select.classList.toggle('data-source-field--placeholder', allowClear && !hasValue);
  }

  function bindSelectPlaceholderState(root) {
    const container = root || document;
    container.querySelectorAll('select.data-source-field--select').forEach(select => {
      syncSelectPlaceholderState(select);

      if (select.dataset.placeholderBound === 'true') return;
      select.addEventListener('change', () => syncSelectPlaceholderState(select));
      select.dataset.placeholderBound = 'true';
    });
  }

  function syncBooleanToggleState(toggleWrapper) {
    if (!toggleWrapper) return;

    const select = toggleWrapper.querySelector('select.data-source-field--select');
    if (!select) return;

    const selectedValue = String(select.value || '').trim().toLowerCase();
    toggleWrapper.querySelectorAll('[data-boolean-toggle-option]').forEach(button => {
      const buttonValue = String(button.dataset.booleanToggleValue || '').trim().toLowerCase();
      button.classList.toggle('is-active', buttonValue === selectedValue);
      button.setAttribute('aria-pressed', buttonValue === selectedValue ? 'true' : 'false');
    });
  }

  function resolveBooleanToggleSelectValue(select, nextValue) {
    if (!select) return String(nextValue || '');

    const normalizedNextValue = String(nextValue || '').trim().toLowerCase();
    if (!normalizedNextValue) return '';

    const matchingOption = Array.from(select.options || []).find(option => (
      String(option.value || '').trim().toLowerCase() === normalizedNextValue
    ));

    return matchingOption ? String(matchingOption.value || '') : String(nextValue || '');
  }

  function initBooleanToggleFields(root) {
    (root || document).querySelectorAll('[data-boolean-toggle]').forEach(toggleWrapper => {
      const select = toggleWrapper.querySelector('select.data-source-field--select');
      if (!select) return;

      syncBooleanToggleState(toggleWrapper);

      if (toggleWrapper.dataset.booleanToggleReady === 'true') return;

      toggleWrapper.querySelectorAll('[data-boolean-toggle-option]').forEach(button => {
        button.addEventListener('click', event => {
          event.preventDefault();
          event.stopPropagation();

          const nextValue = String(button.dataset.booleanToggleValue || '');
          const resolvedNextValue = resolveBooleanToggleSelectValue(select, nextValue);
          if (String(select.value || '') === resolvedNextValue) {
            syncBooleanToggleState(toggleWrapper);
            return;
          }

          select.value = resolvedNextValue;
          syncSelectPlaceholderState(select);
          syncBooleanToggleState(toggleWrapper);
          select.dispatchEvent(new Event('change', { bubbles: true }));
        });
      });

      select.addEventListener('change', () => {
        syncSelectPlaceholderState(select);
        syncBooleanToggleState(toggleWrapper);
      });

      toggleWrapper.dataset.booleanToggleReady = 'true';
    });
  }

  function handleBooleanToggleOptionClick(event) {
    const button = event.target.closest('[data-boolean-toggle-option]');
    if (!button) return;

    const toggleWrapper = button.closest('[data-boolean-toggle]');
    if (!toggleWrapper) return;

    const select = toggleWrapper.querySelector('select.data-source-field--select');
    if (!select) return;

    event.preventDefault();
    event.stopPropagation();

    const nextValue = String(button.dataset.booleanToggleValue || '');
    const resolvedNextValue = resolveBooleanToggleSelectValue(select, nextValue);
    if (String(select.value || '') === resolvedNextValue) {
      syncSelectPlaceholderState(select);
      syncBooleanToggleState(toggleWrapper);
      return;
    }

    select.value = resolvedNextValue;
    syncSelectPlaceholderState(select);
    syncBooleanToggleState(toggleWrapper);
    select.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function readFieldValues(element) {
    if (!element?.name || element.disabled) return [];

    if (element.type === 'checkbox') {
      return element.checked ? [String(element.value || '').trim()] : [];
    }

    if (element.type === 'radio') {
      return element.checked ? [String(element.value || '').trim()] : [];
    }

    if (element.tagName === 'SELECT' && element.multiple) {
      return Array.from(element.selectedOptions || [])
        .map(option => String(option.value || '').trim())
        .filter(Boolean);
    }

    const value = String(element.value || '').trim();
    return value ? [value] : [];
  }

  function serializeForm(form) {
    const payload = {};
    if (!form) return payload;

    const relatedExternalElements = form.id
      ? Array.from(document.querySelectorAll(`[form="${form.id}"].data-source-field`))
      : [];
    const seenElements = new Set();

    Array.from(form.elements || []).concat(relatedExternalElements).forEach(element => {
      if (seenElements.has(element)) return;
      seenElements.add(element);
      if (!element?.classList?.contains('data-source-field')) return;
      readFieldValues(element).forEach(value => appendValue(payload, element.name, value));
    });

    return payload;
  }

  function collectRelatedFiltersFromForm(form, excludedFieldName) {
    const filters = serializeForm(form);

    getFilterForms(form || document).forEach(filterForm => {
      filterForm.querySelectorAll('.lookup-checkbox-field, .checkbox-field').forEach(wrapper => {
        const name = String(wrapper.dataset.fieldName || '').trim();
        if (!name || name === excludedFieldName) return;

        const state = wrapper.__checkboxState;
        if (!state) return;

        const selected = Array.from(state.selected || []).filter(Boolean);
        if (!selected.length) {
          delete filters[name];
          return;
        }
        filters[name] = selected.length > 1 ? selected : selected[0];
      });
    });

    Object.keys(filters).forEach(key => {
      if (key === excludedFieldName) delete filters[key];
      if (key.endsWith('_operator') || key.endsWith('_bool_not')) delete filters[key];
    });
    return filters;
  }

  function normalizeOptionList(list) {
    const normalized = [];
    const seen = new Set();

    (list || []).forEach(option => {
      const value = String(option?.value ?? option?.key ?? option?.id ?? '').trim();
      if (!value || seen.has(value)) return;
      const optionCount = option?.option_count ?? option?.size ?? option?.doc_count;
      const normalizedOption = {
        value,
        label: String(option?.label ?? option?.text ?? value).trim(),
      };
      if (optionCount !== null && optionCount !== undefined && optionCount !== '') {
        normalizedOption.option_count = optionCount;
      }
      normalized.push(normalizedOption);
      seen.add(value);
    });

    return normalized;
  }

  function buildCheckboxId(fieldName, value, index) {
    const safeValue = String(value || '')
      .toLowerCase()
      .replace(/[^a-z0-9_-]+/gi, '-')
      .replace(/^-+|-+$/g, '');
    return `${fieldName}-${safeValue || 'item'}-${index + 1}`;
  }

  function createCheckboxState(initialOptions, multipleSelection, promoteSelected = false) {
    const allOptions = normalizeOptionList(initialOptions);
    const baseOptions = allOptions.slice();
    const baseValues = new Set(baseOptions.map(item => item.value));
    const allOption = (initialOptions || []).find(item => item.isAllOption) || null;
    const selected = new Set(
      (initialOptions || [])
        .filter(item => !!item.checked)
        .map(item => String(item.value || '').trim())
        .filter(Boolean)
    );
    const pinned = new Map();

    (initialOptions || []).forEach(item => {
      const value = String(item?.value || '').trim();
      if (!value || !item.checked || baseValues.has(value)) return;
      const pinnedOption = { value, label: String(item.label || value) };
      if (item.option_count !== null && item.option_count !== undefined && item.option_count !== '') {
        pinnedOption.option_count = item.option_count;
      }
      pinned.set(value, pinnedOption);
    });

    return {
      allOptions,
      baseOptions,
      baseValues,
      selected,
      pinned,
      query: '',
      searchResults: [],
      multipleSelection: multipleSelection !== false,
      allOptionLabel: allOption ? String(allOption.label || translateText('All')).trim() : '',
      promoteSelected: promoteSelected || selected.size > 0,
    };
  }

  function buildVisibleOptions(state) {
    const sourceList = state.query ? state.searchResults : state.baseOptions;
    const merged = [];
    const seen = new Set();

    Array.from(state.pinned.values())
      .filter(item => state.selected.has(item.value))
      .forEach(item => {
        if (seen.has(item.value)) return;
        merged.push(item);
        seen.add(item.value);
      });

    if (state.promoteSelected) {
      sourceList
        .filter(item => state.selected.has(item.value))
        .forEach(item => {
          if (seen.has(item.value)) return;
          merged.push(item);
          seen.add(item.value);
        });
    }

    sourceList
      .filter(item => !state.promoteSelected || !state.selected.has(item.value))
      .forEach(item => {
        if (seen.has(item.value)) return;
        merged.push(item);
        seen.add(item.value);
      });

    return merged;
  }

  function updatePinnedSelection(state, option, checked) {
    if (option?.isAllOption) {
      if (checked) {
        state.selected.clear();
        state.pinned.clear();
        state.query = '';
        state.searchResults = [];
        state.promoteSelected = false;
      }
      return;
    }

    if (!option?.value) return;

    if (checked) {
      if (!state.multipleSelection) {
        state.selected.clear();
        state.pinned.clear();
      }
      state.selected.add(option.value);
      if (!state.baseValues.has(option.value)) {
        state.pinned.set(option.value, { value: option.value, label: option.label || option.value });
      }
      return;
    }

    state.selected.delete(option.value);
    if (!state.baseValues.has(option.value)) {
      state.pinned.delete(option.value);
    }
    if (!state.selected.size) {
      state.promoteSelected = false;
    }
  }

  function parseRenderedOptions(optionsContainer, selector) {
    return Array.from(optionsContainer.querySelectorAll(selector))
      .map(input => {
        const value = String(input.value || '').trim();
        const label = String(
          input.closest('label')?.querySelector('.lookup-checkbox-field__label, .checkbox-field__label')?.textContent
          || input.closest('label')?.querySelector('span')?.textContent
          || value
        ).trim();
        const isAllOption = String(input.dataset.allOption || '').toLowerCase() === 'true';
        const optionCount = input.dataset.optionCount;
        return {
          value,
          label,
          checked: !!input.checked,
          isAllOption,
          option_count: optionCount,
        };
      })
      .filter(item => item.value || item.isAllOption);
  }

  function createCheckboxNode({ fieldName, option, index, checked, multipleSelection, itemClass, isAllOption = false }) {
    const labelElement = document.createElement('label');
    labelElement.className = itemClass;

    const inputElement = document.createElement('input');
    inputElement.id = isAllOption ? `${fieldName}_all` : buildCheckboxId(fieldName, option.value, index);
    inputElement.type = 'checkbox';
    inputElement.name = fieldName;
    inputElement.value = isAllOption ? '' : option.value;
    inputElement.className = 'data-source-field data-source-field--checkbox';
    inputElement.dataset.fieldName = fieldName;
    inputElement.dataset.fieldWidget = 'checkbox';
    inputElement.dataset.multipleSelection = multipleSelection ? 'true' : 'false';
    if (isAllOption) {
      inputElement.dataset.allOption = 'true';
    }
    inputElement.checked = !!checked;

    const textElement = document.createElement('span');
    textElement.className = itemClass === 'lookup-checkbox-field__item'
      ? 'lookup-checkbox-field__label'
      : 'checkbox-field__label';
    textElement.textContent = option.label;

    labelElement.setAttribute('for', inputElement.id);
    labelElement.appendChild(inputElement);
    labelElement.appendChild(textElement);
    if (option.option_count !== null && option.option_count !== undefined && option.option_count !== '') {
      inputElement.dataset.optionCount = option.option_count;
      const countElement = document.createElement('span');
      countElement.className = itemClass === 'lookup-checkbox-field__item'
        ? 'lookup-checkbox-field__count'
        : 'checkbox-field__count';
      countElement.textContent = option.option_count;
      labelElement.appendChild(countElement);
    }
    return labelElement;
  }

  function syncLocalCheckboxSearchVisibility(wrapper) {
    if (!wrapper || wrapper.classList.contains('lookup-checkbox-field')) return;

    const searchInput = wrapper.querySelector('.checkbox-field__search');
    const state = wrapper.__checkboxState;
    if (!searchInput || !state) return;

    const configuredThreshold = Number.parseInt(wrapper.dataset.searchThreshold || '10', 10);
    const threshold = Number.isFinite(configuredThreshold) ? configuredThreshold : 10;
    const shouldShowSearch = Array.isArray(state.allOptions) && state.allOptions.length > threshold;

    searchInput.hidden = !shouldShowSearch;
    wrapper.classList.toggle('checkbox-field--search-hidden', !shouldShowSearch);
  }

  function promoteSelectedCheckboxOptions(form) {
    if (!form) return;

    form.querySelectorAll('.lookup-checkbox-field, .checkbox-field').forEach(wrapper => {
      const state = wrapper.__checkboxState;
      if (!state || !state.selected?.size) return;

      state.promoteSelected = true;
      renderCheckboxOptions(
        wrapper,
        wrapper.classList.contains('lookup-checkbox-field') ? '.lookup-checkbox-field__options' : '.checkbox-field__options',
        wrapper.classList.contains('lookup-checkbox-field') ? 'lookup-checkbox-field__item' : 'checkbox-field__item'
      );
    });
  }

  function bindPromoteSelectedOnSubmit(root) {
    getFilterForms(root).forEach(form => {
      if (form.dataset.promoteSelectedBound === 'true') return;

      form.addEventListener('submit', () => {
        promoteSelectedCheckboxOptions(form);
      });

      form.dataset.promoteSelectedBound = 'true';
    });
  }

  function getSidebarSummary(form) {
    return form?.closest('.sg-filter-sidebar')?.querySelector('[data-active-filters]') || null;
  }

  function getFieldRowLabel(row) {
    return String(
      row?.querySelector('.form-group__toggle-label')?.textContent
      || row?.querySelector('.form-label')?.textContent
      || row?.dataset?.fieldName
      || ''
    ).trim();
  }

  function formatSummaryRangeValue(startValue, endValue) {
    const start = String(startValue || '').trim();
    const end = String(endValue || '').trim();
    if (start && end) return start === end ? start : `${start} - ${end}`;
    return start || end || '';
  }

  function clearBoolNotIfFieldEmpty(row) {
    if (!row) return;
    const hiddenInput = row.querySelector('input[data-meta-field="bool_not"]');
    if (!hiddenInput) return;

    const hasCheckedCheckbox = Array.from(row.querySelectorAll('input.data-source-field--checkbox[type="checkbox"]'))
      .some(input => input.checked && String(input.value || '').trim());
    const hasCheckedRadio = Array.from(row.querySelectorAll('input.data-source-field[type="radio"]'))
      .some(input => input.checked && String(input.value || '').trim() !== '');
    const hasSelectedOption = Array.from(
      row.querySelectorAll('select.data-source-field:not(.data-source-field--operator)')
    ).some(select => Array.from(select.selectedOptions || []).some(option => String(option.value || '').trim()));
    const hasTypedValue = Array.from(
      row.querySelectorAll('input.data-source-field:not([type="hidden"])')
    ).some(input => {
      if (
        input.type === 'checkbox'
        || input.type === 'radio'
        || input.classList.contains('data-source-field--checkbox')
        || input.classList.contains('year-range-field__input')
        || input.classList.contains('lookup-checkbox-field__search')
        || input.classList.contains('checkbox-field__search')
      ) {
        return false;
      }
      return String(input.value || '').trim() !== '';
    });

    if (!hasCheckedCheckbox && !hasCheckedRadio && !hasSelectedOption && !hasTypedValue) {
      hiddenInput.value = '';
      const toggle = row.querySelector('.sg-not-toggle');
      if (toggle) {
        toggle.classList.remove('is-active');
        toggle.setAttribute('aria-pressed', 'false');
      }
    }
  }

  function collectAppliedFilterItems(form) {
    if (!form) return [];

    const items = [];
    const rows = Array.from(form.querySelectorAll('.form-group[data-field-name]'));

    rows.forEach(row => {
      const fieldName = String(row.dataset.fieldName || '').trim();
      const fieldKind = String(row.dataset.fieldKind || '').trim();
      const fieldWidget = String(row.dataset.fieldWidget || '').trim();
      if (!fieldName || fieldKind === 'control') return;

      const label = getFieldRowLabel(row);
      const isNot = row.querySelector('input[data-meta-field="bool_not"]')?.value === 'true';
      const prefix = isNot ? `${translateText('NOT')} ` : '';

      if (fieldWidget === 'range') {
        const rangeInputs = Array.from(row.querySelectorAll('.year-range-field__input'));
        const value = formatSummaryRangeValue(rangeInputs[0]?.value, rangeInputs[1]?.value);
        if (!value) return;
        items.push({
          fieldName,
          widget: 'range',
          label,
          value: `${prefix}${value}`,
          removeValue: '',
        });
        return;
      }

      const checkedInputs = Array.from(
        row.querySelectorAll('input.data-source-field--checkbox[type="checkbox"]:checked')
      ).filter(input => String(input.value || '').trim());
      if (checkedInputs.length) {
        checkedInputs.forEach(input => {
          const displayValue = String(
            input.closest('label')?.querySelector('span')?.textContent || input.value || ''
          ).trim();
          if (!displayValue) return;
          items.push({
            fieldName,
            widget: 'checkbox',
            label,
            value: `${prefix}${displayValue}`,
            removeValue: String(input.value || '').trim(),
          });
        });
        return;
      }

      const checkedRadio = Array.from(
        row.querySelectorAll('input.data-source-field[type="radio"]:checked')
      ).find(input => String(input.value || '').trim());
      if (checkedRadio) {
        const displayValue = String(
          checkedRadio.closest('label')?.querySelector('span')?.textContent || checkedRadio.value || ''
        ).trim();
        if (!displayValue) return;
        items.push({
          fieldName,
          widget: 'radio',
          label,
          value: `${prefix}${displayValue}`,
          removeValue: String(checkedRadio.value || '').trim(),
        });
        return;
      }

      const select = row.querySelector('select.data-source-field:not(.data-source-field--operator)');
      if (select) {
        const selectedOptions = Array.from(select.selectedOptions || [])
          .filter(option => String(option.value || '').trim())
          .map(option => ({
            value: String(option.value || '').trim(),
            label: String(option.textContent || option.value || '').trim(),
          }));
        selectedOptions.forEach(option => {
          items.push({
            fieldName,
            widget: 'select',
            label,
            value: `${prefix}${option.label}`,
            removeValue: option.value,
          });
        });
        return;
      }

      const typedInput = Array.from(row.querySelectorAll('input.data-source-field:not([type="hidden"])')).find(input => {
        if (
          input.type === 'checkbox'
          || input.type === 'radio'
          || input.classList.contains('data-source-field--checkbox')
          || input.classList.contains('year-range-field__input')
          || input.classList.contains('lookup-checkbox-field__search')
          || input.classList.contains('checkbox-field__search')
        ) {
          return false;
        }
        return String(input.value || '').trim() !== '';
      });
      if (!typedInput) return;

      items.push({
        fieldName,
        widget: fieldWidget || 'input',
        label,
        value: `${prefix}${String(typedInput.value || '').trim()}`,
        removeValue: '',
      });
    });

    return items;
  }

  function buildAppliedFilterItemNode(item) {
    const wrapper = document.createElement('div');
    wrapper.className = 'sg-active-filters__item';

    const text = document.createElement('div');
    text.className = 'sg-active-filters__item-text';

    const label = document.createElement('span');
    label.className = 'sg-active-filters__item-label';
    label.textContent = `${item.label}: `;

    const value = document.createElement('span');
    value.className = 'sg-active-filters__item-value';
    value.textContent = item.value;

    text.appendChild(label);
    text.appendChild(value);

    const removeButton = document.createElement('button');
    removeButton.type = 'button';
    removeButton.className = 'sg-active-filters__remove';
    removeButton.dataset.fieldName = item.fieldName;
    removeButton.dataset.widget = item.widget;
    removeButton.dataset.removeValue = item.removeValue || '';
    removeButton.setAttribute('aria-label', translateText('Remove filter'));
    removeButton.textContent = '×';

    wrapper.appendChild(text);
    wrapper.appendChild(removeButton);
    return wrapper;
  }

  function getAppliedFilterSnapshot(form) {
    const summary = getSidebarSummary(form);
    if (!summary) return [];

    try {
      const items = JSON.parse(summary.dataset.appliedItems || '[]');
      return Array.isArray(items) ? items : [];
    } catch (_error) {
      return [];
    }
  }

  function setAppliedFilterSnapshot(form, items) {
    const summary = getSidebarSummary(form);
    if (!summary) return;
    summary.dataset.appliedItems = JSON.stringify(Array.isArray(items) ? items : []);
  }

  function renderAppliedFiltersSummary(form, itemsOverride) {
    const summary = getSidebarSummary(form);
    if (!summary) return;

    const list = summary.querySelector('.sg-active-filters__list');
    if (!list) return;

    const items = Array.isArray(itemsOverride) ? itemsOverride : getAppliedFilterSnapshot(form);
    list.innerHTML = '';

    if (!items.length) {
      summary.hidden = true;
      return;
    }

    items.forEach(item => {
      list.appendChild(buildAppliedFilterItemNode(item));
    });
    summary.hidden = false;
  }

  function commitAppliedFilters(form) {
    if (!form) return;
    const items = collectAppliedFilterItems(form);
    setAppliedFilterSnapshot(form, items);
    renderAppliedFiltersSummary(form, items);
  }

  function dispatchFiltersChanged(form, detail = {}) {
    if (!form) return;

    form.dispatchEvent(new CustomEvent('search-gateway:filters-changed', {
      bubbles: true,
      detail,
    }));
  }

  function findFieldRow(form, fieldName) {
    return Array.from(form?.querySelectorAll('.form-group[data-field-name]') || [])
      .find(row => String(row.dataset.fieldName || '').trim() === String(fieldName || '').trim()) || null;
  }

  function removeAppliedFilterValue(form, fieldName, widget, removeValue) {
    const row = findFieldRow(form, fieldName);
    if (!row) return false;

    if (widget === 'checkbox') {
      const input = Array.from(
        row.querySelectorAll('input.data-source-field--checkbox[type="checkbox"]')
      ).find(item => String(item.value || '').trim() === String(removeValue || '').trim());
      if (!input) return false;
      input.checked = false;
      clearBoolNotIfFieldEmpty(row);
      input.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    }

    if (widget === 'radio') {
      const radios = Array.from(row.querySelectorAll('input.data-source-field[type="radio"]'));
      if (!radios.length) return false;

      const clearRadio = radios.find(input => String(input.value || '').trim() === '');
      if (clearRadio) {
        clearRadio.checked = true;
        clearBoolNotIfFieldEmpty(row);
        clearRadio.dispatchEvent(new Event('change', { bubbles: true }));
        return true;
      }

      const matchingRadio = radios.find(input => String(input.value || '').trim() === String(removeValue || '').trim());
      if (!matchingRadio) return false;
      matchingRadio.checked = false;
      clearBoolNotIfFieldEmpty(row);
      matchingRadio.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    }

    if (widget === 'range') {
      const rangeInputs = Array.from(row.querySelectorAll('.year-range-field__input'));
      rangeInputs.forEach(input => {
        input.value = '';
      });
      clearBoolNotIfFieldEmpty(row);
      if (rangeInputs[0]) {
        rangeInputs[0].dispatchEvent(new Event('change', { bubbles: true }));
      }
      return true;
    }

    if (widget === 'select') {
      const select = row.querySelector('select.data-source-field:not(.data-source-field--operator)');
      if (!select) return false;

      if (select.multiple) {
        Array.from(select.options || []).forEach(option => {
          if (String(option.value || '').trim() === String(removeValue || '').trim()) {
            option.selected = false;
          }
        });
      } else {
        select.value = '';
      }
      clearBoolNotIfFieldEmpty(row);
      select.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    }

    const input = Array.from(row.querySelectorAll('input.data-source-field:not([type="hidden"])')).find(element => {
      if (
        element.type === 'checkbox'
        || element.type === 'radio'
        || element.classList.contains('data-source-field--checkbox')
        || element.classList.contains('year-range-field__input')
        || element.classList.contains('lookup-checkbox-field__search')
        || element.classList.contains('checkbox-field__search')
      ) {
        return false;
      }
      return true;
    });
    if (!input) return false;

    input.value = '';
    clearBoolNotIfFieldEmpty(row);
    input.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  }

  function bindAppliedFiltersSummary(root) {
    getFilterForms(root).forEach(form => {
      if (form.dataset.summaryBound === 'true') return;

      const summary = getSidebarSummary(form);
      if (!summary) return;

      const syncDraftState = event => {
        const target = event?.target;
        if (target && !target.classList?.contains('data-source-field')) return;
        if (target?.dataset?.metaField !== 'bool_not') {
          const row = target?.closest?.('.form-group[data-field-name]');
          if (row) {
            clearBoolNotIfFieldEmpty(row);
          }
        }
      };

      form.addEventListener('change', syncDraftState);
      form.addEventListener('input', syncDraftState);

      summary.addEventListener('click', event => {
        const clearButton = event.target.closest('.sg-active-filters__clear');
        if (clearButton) {
          const resetButton = summary.closest('.sg-filter-sidebar')?.querySelector('.sg-filter-sidebar__btn--clear');
          if (resetButton) {
            resetButton.click();
            return;
          }
          resetForm(form);
          return;
        }

        const removeButton = event.target.closest('.sg-active-filters__remove');
        if (!removeButton) return;
        const removed = removeAppliedFilterValue(
          form,
          removeButton.dataset.fieldName,
          removeButton.dataset.widget,
          removeButton.dataset.removeValue,
        );
        if (!removed) return;

        commitAppliedFilters(form);
        dispatchFiltersChanged(form, {
          reason: 'remove-applied-filter',
          fieldName: removeButton.dataset.fieldName || '',
          widget: removeButton.dataset.widget || '',
          removeValue: removeButton.dataset.removeValue || '',
        });
      });

      form.dataset.summaryBound = 'true';
      commitAppliedFilters(form);
    });
  }

  function renderCheckboxOptions(wrapper, optionsContainerSelector, itemClass) {
    const state = wrapper.__checkboxState;
    if (!state) return;

    const optionsContainer = wrapper.querySelector(optionsContainerSelector);
    if (!optionsContainer) return;

    const fieldName = String(wrapper.dataset.fieldName || '').trim();
    if (!fieldName) return;

    const visibleOptions = buildVisibleOptions(state);
    optionsContainer.innerHTML = '';

    if (state.allOptionLabel) {
      optionsContainer.appendChild(
        createCheckboxNode({
          fieldName,
          option: { value: '', label: state.allOptionLabel },
          index: -1,
          checked: state.selected.size === 0,
          multipleSelection: state.multipleSelection,
          itemClass,
          isAllOption: true,
        })
      );
    }

    visibleOptions.forEach((option, index) => {
      optionsContainer.appendChild(
        createCheckboxNode({
          fieldName,
          option,
          index,
          checked: state.selected.has(option.value),
          multipleSelection: state.multipleSelection,
          itemClass,
        })
      );
    });

    if (wrapper.classList.contains('checkbox-field')) {
      syncLocalCheckboxSearchVisibility(wrapper);
    }
  }

  async function fetchLookupOptions(wrapper, queryText = '') {
    const dataSource = String(wrapper.dataset.dataSource || '').trim();
    const fieldName = String(wrapper.dataset.fieldName || '').trim();
    if (!dataSource || !fieldName) return [];

    const params = new URLSearchParams({
      data_source: dataSource,
      field_name: fieldName,
      q: String(queryText || '').trim(),
    });

    const form = getFormFromNode(wrapper);
    const relatedFilters = collectRelatedFiltersFromForm(form, fieldName);
    Object.entries(relatedFilters).forEach(([key, value]) => {
      if (value === null || value === undefined) {
        return;
      }
      if (Array.isArray(value)) {
        value.forEach(item => {
          if (item !== null && item !== undefined) {
            params.append(key, item);
          }
        });
      } else {
        params.append(key, value);
      }
    });

    try {
      const response = await fetch(`/search-gateway/search-item/?${params.toString()}`);
      if (!response.ok) return [];
      const data = await response.json();
      return normalizeOptionList(Array.isArray(data?.results) ? data.results : []);
    } catch (error) {
      console.error('Error loading lookup options', error);
      return [];
    }
  }

  async function fetchFilterOptions(element) {
    const dataSource = String(element.dataset.dataSource || '').trim();
    const fieldName = String(element.dataset.fieldName || '').trim();
    if (!dataSource || !fieldName) return [];

    const params = new URLSearchParams({
      data_source: dataSource,
      fields: fieldName,
    });

    const form = getFormFromNode(element);
    const relatedFilters = collectRelatedFiltersFromForm(form, fieldName);
    Object.entries(relatedFilters).forEach(([key, value]) => {
      if (value === null || value === undefined) {
        return;
      }
      if (Array.isArray(value)) {
        value.forEach(item => {
          if (item !== null && item !== undefined) {
            params.append(key, item);
          }
        });
      } else {
        params.append(key, value);
      }
    });

    try {
      const response = await fetch(`/search-gateway/filters/?${params.toString()}`);
      if (!response.ok) return [];
      const data = await response.json();
      return normalizeOptionList(Array.isArray(data?.[fieldName]) ? data[fieldName] : []);
    } catch (error) {
      console.error('Error loading filter options', error);
      return [];
    }
  }

  function parseDependencyNames(element) {
    const fieldName = String(element?.dataset?.fieldName || '').trim();
    const dependencyNames = String(element?.dataset?.dependencies || '')
      .split(',')
      .map(item => item.trim())
      .filter(Boolean)
      .filter(dependencyName => dependencyName !== fieldName);
    return new Set(dependencyNames);
  }

  function setsHaveSameValues(left, right) {
    if (left.size !== right.size) return false;
    return Array.from(left).every(value => right.has(value));
  }

  function getCurrentFieldValue(element, fieldName) {
    if (!element) return '';

    if (element.name === fieldName) {
      return String(element.value || '').trim();
    }

    const checkedInput = Array.from(element.querySelectorAll('input[name]'))
      .find(input => input.name === fieldName && input.checked);
    if (checkedInput) {
      return String(checkedInput.value || '').trim();
    }

    const select = Array.from(element.querySelectorAll('select[name]'))
      .find(item => item.name === fieldName);
    if (select) {
      return String(select.value || '').trim();
    }

    return '';
  }

  function dispatchFieldChange(element, fieldName) {
    if (!element || !fieldName) return;

    const target = element.name === fieldName
      ? element
      : Array.from(element.querySelectorAll('input[name], select[name], textarea[name]'))
        .find(input => input.name === fieldName && !input.disabled);

    if (!target) return;
    target.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function rebuildSelectOptions(select, options) {
    if (!select) return false;

    const selectedValue = String(select.value || '').trim();
    const allowClear = String(select.dataset.allowClear || '').toLowerCase() === 'true';
    const placeholder = String(select.dataset.placeholder || '').trim();
    const availableValues = new Set((options || []).map(option => option.value));

    select.innerHTML = '';

    if (allowClear) {
      const placeholderOption = document.createElement('option');
      placeholderOption.value = '';
      placeholderOption.textContent = placeholder;
      select.appendChild(placeholderOption);
    }

    (options || []).forEach(option => {
      const optionElement = document.createElement('option');
      optionElement.value = option.value;
      optionElement.textContent = option.label;
      select.appendChild(optionElement);
    });

    if (selectedValue && availableValues.has(selectedValue)) {
      select.value = selectedValue;
    } else {
      select.value = allowClear ? '' : (options?.[0]?.value || '');
    }

    syncSelectPlaceholderState(select);
    return selectedValue !== String(select.value || '').trim();
  }

  async function refreshDependentSelectOptions(select, { notifyChange = true } = {}) {
    if (!select) return false;

    const refreshId = (select.__dependentRefreshId || 0) + 1;
    select.__dependentRefreshId = refreshId;
    const options = await fetchFilterOptions(select);
    if (select.__dependentRefreshId !== refreshId) return false;

    const changed = animateFacetRefresh(select, () => rebuildSelectOptions(select, options));
    if (changed && notifyChange) {
      dispatchFieldChange(select, String(select.dataset.fieldName || '').trim());
    }
    return changed;
  }

  function normalizeBooleanOptionValue(value) {
    const normalized = String(value || '').trim().toLowerCase();
    if (['true', '1', 'yes', 'y', 'sim'].includes(normalized)) return 'true';
    if (['false', '0', 'no', 'n', 'nao', 'não'].includes(normalized)) return 'false';
    return normalized;
  }

  async function refreshDependentBooleanOptions(fieldset, { notifyChange = true } = {}) {
    if (!fieldset) return false;

    const fieldName = String(fieldset.dataset.fieldName || '').trim();
    const previousValue = getCurrentFieldValue(fieldset, fieldName);
    const refreshId = (fieldset.__dependentRefreshId || 0) + 1;
    fieldset.__dependentRefreshId = refreshId;
    const options = await fetchFilterOptions(fieldset);
    if (fieldset.__dependentRefreshId !== refreshId) return false;

    const availableValues = new Set(
      (options || []).map(option => normalizeBooleanOptionValue(option.value)).filter(Boolean)
    );
    const shouldRestrictOptions = availableValues.size > 0;

    animateFacetRefresh(fieldset, () => {
      let hasCheckedAvailable = false;
      fieldset.querySelectorAll('input[type="radio"]').forEach(radio => {
        const value = String(radio.value || '').trim();
        const isClearOption = !value;
        const normalizedValue = normalizeBooleanOptionValue(value);
        const isAvailable = !shouldRestrictOptions || isClearOption || availableValues.has(normalizedValue);

        radio.disabled = !isAvailable;

        if (radio.checked && !isAvailable) {
          radio.checked = false;
        } else if (radio.checked && isAvailable) {
          hasCheckedAvailable = true;
        }
      });

      if (!hasCheckedAvailable) {
        const clearRadio = fieldset.querySelector('input[type="radio"][value=""]:not([disabled])');
        if (clearRadio) {
          clearRadio.checked = true;
        }
      }
    });

    const changed = previousValue !== getCurrentFieldValue(fieldset, fieldName);
    if (changed && notifyChange) {
      dispatchFieldChange(fieldset, fieldName);
    }
    return changed;
  }

  async function refreshDependentElement(element, state, options = {}) {
    if (!element) return false;

    if (element.classList.contains('lookup-checkbox-field') || element.classList.contains('checkbox-field')) {
      if (!state) return false;
      return refreshDependentFieldOptions(element, state, options);
    }
    if (element.matches('select.data-source-field--select[data-dependencies]')) {
      return refreshDependentSelectOptions(element, options);
    }
    if (element.matches('fieldset.sg-radio-group--boolean[data-dependencies]')) {
      return refreshDependentBooleanOptions(element, options);
    }
    return false;
  }

  function buildLookupInitialOptionsCacheKey(wrapper) {
    const dataSource = String(wrapper?.dataset?.dataSource || '').trim();
    const fieldName = String(wrapper?.dataset?.fieldName || '').trim();
    if (!dataSource || !fieldName) return '';
    return `${dataSource}::${fieldName}`;
  }

  function getCachedLookupInitialOptions(wrapper) {
    const cacheKey = buildLookupInitialOptionsCacheKey(wrapper);
    if (!cacheKey || !lookupInitialOptionsCache.has(cacheKey)) return [];
    return normalizeOptionList(lookupInitialOptionsCache.get(cacheKey));
  }

  function setCachedLookupInitialOptions(wrapper, options) {
    const cacheKey = buildLookupInitialOptionsCacheKey(wrapper);
    if (!cacheKey) return;
    lookupInitialOptionsCache.set(cacheKey, normalizeOptionList(options));
  }

  function debounce(callback, waitMs = 250) {
    let timerId = null;
    return (...args) => {
      if (timerId) window.clearTimeout(timerId);
      timerId = window.setTimeout(() => callback(...args), waitMs);
    };
  }

  function initLocalCheckboxFields(root) {
    (root || document).querySelectorAll('.checkbox-field').forEach(wrapper => {
      if (wrapper.dataset.checkboxReady === 'true') return;

      const optionsContainer = wrapper.querySelector('.checkbox-field__options');
      const searchInput = wrapper.querySelector('.checkbox-field__search');
      if (!optionsContainer) return;

      const initialOptions = parseRenderedOptions(optionsContainer, '.checkbox-field__item input[type="checkbox"]');
      if (!initialOptions.length) return;

      const state = createCheckboxState(initialOptions, true);
      wrapper.__checkboxState = state;

      const render = () => renderCheckboxOptions(wrapper, '.checkbox-field__options', 'checkbox-field__item');

      optionsContainer.addEventListener('change', event => {
        const checkbox = event?.target;
        if (!checkbox || checkbox.type !== 'checkbox') return;
        const value = String(checkbox.value || '').trim();
        const label = String(checkbox.closest('label')?.querySelector('span')?.textContent || value).trim();
        const isAllOption = String(checkbox.dataset.allOption || '').toLowerCase() === 'true';
        updatePinnedSelection(state, { value, label, isAllOption }, checkbox.checked);
        if (isAllOption && checkbox.checked && searchInput) {
          searchInput.value = '';
        }
        render();
      });

      if (searchInput) {
        searchInput.addEventListener('input', event => {
          const query = String(event?.target?.value || '').trim().toLowerCase();
          state.query = query;
          state.searchResults = query
            ? state.allOptions.filter(option => String(option.label || '').toLowerCase().includes(query))
            : [];
          render();
        });
      }

      render();
      wrapper.dataset.checkboxReady = 'true';
    });
  }

  function initLookupCheckboxFields(root) {
    const pending = [];

    (root || document).querySelectorAll('.lookup-checkbox-field').forEach(wrapper => {
      if (wrapper.dataset.lookupReady === 'true') return;

      const searchInput = wrapper.querySelector('.lookup-checkbox-field__search');
      const optionsContainer = wrapper.querySelector('.lookup-checkbox-field__options');
      if (!searchInput || !optionsContainer) return;

      const initialOptions = parseRenderedOptions(optionsContainer, '.lookup-checkbox-field__item input[type="checkbox"]');
      const multipleSelection = String(wrapper.dataset.multipleSelection || 'true') !== 'false';
      const state = createCheckboxState(initialOptions, multipleSelection);
      wrapper.__checkboxState = state;

      const render = () => renderCheckboxOptions(wrapper, '.lookup-checkbox-field__options', 'lookup-checkbox-field__item');

      optionsContainer.addEventListener('change', event => {
        const checkbox = event?.target;
        if (!checkbox || checkbox.type !== 'checkbox') return;
        const value = String(checkbox.value || '').trim();
        const label = String(checkbox.closest('label')?.querySelector('span')?.textContent || value).trim();
        const isAllOption = String(checkbox.dataset.allOption || '').toLowerCase() === 'true';
        updatePinnedSelection(state, { value, label, isAllOption }, checkbox.checked);
        if (isAllOption && checkbox.checked && searchInput) {
          searchInput.value = '';
        }
        render();
      });

      const doSearch = async rawQuery => {
        const query = String(rawQuery || '').trim();
        state.query = query;
        if (!query) {
          state.searchResults = [];
          render();
          return;
        }
        state.searchResults = await fetchLookupOptions(wrapper, query);
        render();
      };

      const debouncedSearch = debounce(doSearch, 250);
      searchInput.addEventListener('input', event => {
        debouncedSearch(event?.target?.value || '');
      });

      const preload = String(wrapper.dataset.preloadOptions || 'false') === 'true';
      const initTask = async () => {
        // When the sidebar HTML already includes lookup options from the server,
        // reuse them instead of issuing another preload request on init.
        if (state.baseOptions.length) {
          setCachedLookupInitialOptions(wrapper, state.baseOptions);
          render();
          return;
        }

        const cachedInitialOptions = getCachedLookupInitialOptions(wrapper);
        if (cachedInitialOptions.length) {
          state.allOptions = cachedInitialOptions;
          state.baseOptions = cachedInitialOptions.slice();
          state.baseValues = new Set(state.baseOptions.map(item => item.value));
          render();
          return;
        }

        const firstBatch = await fetchLookupOptions(wrapper, '');
        state.allOptions = firstBatch;
        state.baseOptions = firstBatch.slice();
        state.baseValues = new Set(state.baseOptions.map(item => item.value));
        if (preload || firstBatch.length) {
          setCachedLookupInitialOptions(wrapper, firstBatch);
        }
        render();
      };

      pending.push(initTask());
      wrapper.dataset.lookupReady = 'true';
    });

    return Promise.all(pending);
  }

  function pruneSelectedOptions(state, availableValues) {
    const available = availableValues instanceof Set
      ? availableValues
      : new Set(availableValues || []);

    Array.from(state.selected).forEach(value => {
      if (available.has(value)) {
        return;
      }
      state.selected.delete(value);
      if (!state.baseValues.has(value)) {
        state.pinned.delete(value);
      }
    });
  }

  function getFacetRefreshAnimationElement(element) {
    return element?.closest?.('.form-group__body') || element || null;
  }

  function shouldReduceMotion() {
    return window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;
  }

  function animateFacetRefresh(element, renderCallback) {
    const animatedElement = getFacetRefreshAnimationElement(element);
    if (!animatedElement || shouldReduceMotion()) {
      return renderCallback();
    }

    const token = (animatedElement.__facetRefreshToken || 0) + 1;
    animatedElement.__facetRefreshToken = token;
    if (animatedElement.__facetRefreshTimer) {
      window.clearTimeout(animatedElement.__facetRefreshTimer);
    }

    const previousHeight = animatedElement.getBoundingClientRect().height;
    const previousHeightStyle = animatedElement.style.height;
    animatedElement.style.height = `${previousHeight}px`;
    animatedElement.style.overflow = 'hidden';
    animatedElement.classList.add('is-facet-refreshing');

    const result = renderCallback();

    // Measure the natural post-render height. When shrinking, scrollHeight can
    // report the locked old height unless the element is briefly released.
    animatedElement.style.height = 'auto';
    const nextHeight = animatedElement.getBoundingClientRect().height;
    animatedElement.style.height = `${previousHeight}px`;

    const cleanup = () => {
      if (animatedElement.__facetRefreshToken !== token) return;
      animatedElement.classList.remove('is-facet-refreshing');
      animatedElement.style.height = previousHeightStyle;
      animatedElement.style.overflow = '';
      animatedElement.__facetRefreshTimer = null;
    };

    if (Math.abs(previousHeight - nextHeight) < 1) {
      window.requestAnimationFrame(cleanup);
      return result;
    }

    animatedElement.getBoundingClientRect();
    window.requestAnimationFrame(() => {
      if (animatedElement.__facetRefreshToken !== token) return;
      animatedElement.style.height = `${nextHeight}px`;
    });

    const onTransitionEnd = event => {
      if (event.target !== animatedElement || event.propertyName !== 'height') return;
      animatedElement.removeEventListener('transitionend', onTransitionEnd);
      cleanup();
    };
    animatedElement.addEventListener('transitionend', onTransitionEnd);
    animatedElement.__facetRefreshTimer = window.setTimeout(() => {
      animatedElement.removeEventListener('transitionend', onTransitionEnd);
      cleanup();
    }, FACET_REFRESH_ANIMATION_MS + 80);

    return result;
  }

  function animateOptionsRefresh(wrapper, renderCallback) {
    return animateFacetRefresh(wrapper, renderCallback);
  }

  async function refreshDependentFieldOptions(wrapper, state, { clearSearch = true, notifyChange = true } = {}) {
    const isLookupField = wrapper.classList.contains('lookup-checkbox-field');
    const optionsContainerSelector = isLookupField
      ? '.lookup-checkbox-field__options'
      : '.checkbox-field__options';
    const itemClass = isLookupField ? 'lookup-checkbox-field__item' : 'checkbox-field__item';
    const fieldName = String(wrapper.dataset.fieldName || '').trim();
    const previousSelected = new Set(state.selected || []);
    const refreshId = (wrapper.__dependentRefreshId || 0) + 1;
    wrapper.__dependentRefreshId = refreshId;

    if (clearSearch) {
      state.query = '';
      state.searchResults = [];
      const searchInput = wrapper.querySelector(
        isLookupField ? '.lookup-checkbox-field__search' : '.checkbox-field__search'
      );
      if (searchInput) searchInput.value = '';
    }

    const firstBatch = isLookupField
      ? await fetchLookupOptions(wrapper, clearSearch ? '' : state.query)
      : await fetchFilterOptions(wrapper);
    if (wrapper.__dependentRefreshId !== refreshId) return false;

    state.allOptions = firstBatch;
    state.baseOptions = firstBatch.slice();
    state.baseValues = new Set(state.baseOptions.map(item => item.value));
    pruneSelectedOptions(state, state.baseValues);
    animateOptionsRefresh(wrapper, () => {
      renderCheckboxOptions(wrapper, optionsContainerSelector, itemClass);
    });

    const changed = !setsHaveSameValues(previousSelected, state.selected);
    if (changed && notifyChange) {
      dispatchFieldChange(wrapper, fieldName);
    }
    return changed;
  }

  function bindDependentFields(root) {
    const dependentSelectors = [
      '.lookup-checkbox-field',
      '.checkbox-field',
      'select.data-source-field--select[data-dependencies]',
      'fieldset.sg-radio-group--boolean[data-dependencies]',
    ].join(', ');

    (root || document).querySelectorAll(dependentSelectors).forEach(element => {
      if (element.dataset.dependenciesBound === 'true') return;

      const dependencyNames = parseDependencyNames(element);
      if (!dependencyNames.size) {
        element.dataset.dependenciesBound = 'true';
        return;
      }

      const form = getFormFromNode(element);
      const fieldName = String(element.dataset.fieldName || '').trim();

      (form || document).addEventListener('change', event => {
        const dependencyElement = event?.target;
        if (
          !dependencyElement?.name
          || dependencyElement.name === fieldName
          || !dependencyNames.has(dependencyElement.name)
        ) {
          return;
        }

        queueMicrotask(() => {
          void refreshDependentElement(element, element.__checkboxState);
        });
      });

      element.dataset.dependenciesBound = 'true';
    });
  }

  function initCollapsibleFilterGroups(root) {
    (root || document).querySelectorAll('.filter-group-card--collapsible').forEach((card, index) => {
      if (card.dataset.collapsibleReady === 'true') return;

      const titleElement = card.querySelector(':scope > .filter-group-card__title');
      if (!titleElement) return;

      const titleText = titleElement.textContent.trim();
      const expandedByDefault = card.dataset.expanded !== 'false';
      const bodyId = card.id ? `${card.id}-body` : `filter-group-body-${index + 1}`;

      const toggleButton = document.createElement('button');
      toggleButton.type = 'button';
      toggleButton.className = 'filter-group-card__toggle';
      toggleButton.setAttribute('aria-expanded', expandedByDefault ? 'true' : 'false');
      toggleButton.setAttribute('aria-controls', bodyId);
      toggleButton.innerHTML = `
        <span class="filter-group-card__title">${titleText}</span>
        <span class="filter-group-card__chevron" aria-hidden="true"></span>
      `;

      const body = document.createElement('div');
      body.className = 'filter-group-card__body';
      body.id = bodyId;

      let current = titleElement.nextSibling;
      while (current) {
        const nextNode = current.nextSibling;
        body.appendChild(current);
        current = nextNode;
      }

      titleElement.replaceWith(toggleButton);
      card.appendChild(body);

      if (!expandedByDefault) {
        card.classList.add('is-collapsed');
        body.classList.add('is-collapsed');
      }

      toggleButton.addEventListener('click', () => {
        const isExpanded = toggleButton.getAttribute('aria-expanded') === 'true';
        toggleButton.setAttribute('aria-expanded', isExpanded ? 'false' : 'true');
        card.classList.toggle('is-collapsed', isExpanded);
        body.classList.toggle('is-collapsed', isExpanded);
      });

      card.dataset.collapsibleReady = 'true';
    });
  }

  function initCollapsibleFieldRows(root) {
    (root || document).querySelectorAll('.form-group--collapsible').forEach((row, index) => {
      if (row.dataset.fieldCollapsibleReady === 'true') return;

      const labelElement = row.querySelector(':scope > .form-label');
      const controlsElement = row.querySelector(':scope > .form-group__controls');
      if (!labelElement || !controlsElement) return;

      const labelText = labelElement.textContent.trim();
      const expandedByDefault = row.dataset.expanded !== 'false';
      const controlsId = `${row.id || `filter-field-${index + 1}`}-body`;
      controlsElement.id = controlsId;
      controlsElement.classList.add('form-group__body');

      const toggleButton = document.createElement('button');
      toggleButton.type = 'button';
      toggleButton.className = 'form-group__toggle';
      toggleButton.setAttribute('aria-expanded', expandedByDefault ? 'true' : 'false');
      toggleButton.setAttribute('aria-controls', controlsId);
      toggleButton.innerHTML = `
        <span class="form-group__toggle-label">${labelText}</span>
        <span class="form-group__toggle-icon" aria-hidden="true"></span>
      `;

      labelElement.replaceWith(toggleButton);

      if (!expandedByDefault) {
        row.classList.add('is-collapsed');
        controlsElement.classList.add('is-collapsed');
      }

      toggleButton.addEventListener('click', () => {
        const isExpanded = toggleButton.getAttribute('aria-expanded') === 'true';
        toggleButton.setAttribute('aria-expanded', isExpanded ? 'false' : 'true');
        row.classList.toggle('is-collapsed', isExpanded);
        controlsElement.classList.toggle('is-collapsed', isExpanded);
      });

      row.dataset.fieldCollapsibleReady = 'true';
    });
  }

  function initNotToggles(root) {
    (root || document).querySelectorAll('.sg-not-toggle').forEach(button => {
      if (button.dataset.toggleReady === 'true') return;

      button.addEventListener('click', () => {
        const hiddenInput = button.parentElement?.querySelector('input[data-meta-field="bool_not"]');
        if (!hiddenInput) return;
        const active = hiddenInput.value === 'true';
        hiddenInput.value = active ? '' : 'true';
        button.classList.toggle('is-active', !active);
        button.setAttribute('aria-pressed', active ? 'false' : 'true');
        hiddenInput.dispatchEvent(new Event('change', { bubbles: true }));
      });

      button.dataset.toggleReady = 'true';
    });
  }

  function rebuildCheckboxStateFromDom(form) {
    if (!form) return;

    form.querySelectorAll('.lookup-checkbox-field, .checkbox-field').forEach(wrapper => {
      const optionsContainerSelector = wrapper.classList.contains('lookup-checkbox-field')
        ? '.lookup-checkbox-field__options'
        : '.checkbox-field__options';
      const itemSelector = wrapper.classList.contains('lookup-checkbox-field')
        ? '.lookup-checkbox-field__item input[type="checkbox"]'
        : '.checkbox-field__item input[type="checkbox"]';
      const itemClass = wrapper.classList.contains('lookup-checkbox-field')
        ? 'lookup-checkbox-field__item'
        : 'checkbox-field__item';
      const multipleSelection = wrapper.classList.contains('lookup-checkbox-field')
        ? String(wrapper.dataset.multipleSelection || 'true') !== 'false'
        : true;
      const optionsContainer = wrapper.querySelector(optionsContainerSelector);
      if (!optionsContainer) return;

      const initialOptions = parseRenderedOptions(optionsContainer, itemSelector);
      wrapper.__checkboxState = createCheckboxState(initialOptions, multipleSelection);

      const searchInput = wrapper.querySelector('input[type="text"]');
      const isSearchInput = searchInput
        && (
          searchInput.classList.contains('lookup-checkbox-field__search')
          || searchInput.classList.contains('checkbox-field__search')
        );
      if (isSearchInput) {
        searchInput.value = '';
      }

      renderCheckboxOptions(
        wrapper,
        optionsContainerSelector,
        itemClass
      );
    });
  }

  function syncMetaStateFromDom(form) {
    if (!form) return;
    form.querySelectorAll('input[data-meta-field="bool_not"]').forEach(input => {
      const button = input.parentElement?.querySelector('.sg-not-toggle');
      const isActive = input.value === 'true';
      if (!button) return;
      button.classList.toggle('is-active', isActive);
      button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });
  }

  function clearLookupInitialOptionsCache(form) {
    if (!form) return;
    form.querySelectorAll('.lookup-checkbox-field').forEach(wrapper => {
      const cacheKey = buildLookupInitialOptionsCacheKey(wrapper);
      if (cacheKey) {
        lookupInitialOptionsCache.delete(cacheKey);
      }
    });
  }

  async function refreshAllFieldOptions(form) {
    if (!form) return;

    const refreshTasks = [];

    form.querySelectorAll('.lookup-checkbox-field[data-dependencies], .checkbox-field[data-dependencies]').forEach(wrapper => {
      if (!parseDependencyNames(wrapper).size) return;
      const state = wrapper.__checkboxState;
      if (!state) return;
      refreshTasks.push(refreshDependentFieldOptions(wrapper, state, { notifyChange: false }));
    });

    form.querySelectorAll('select.data-source-field--select[data-dependencies]').forEach(select => {
      if (!parseDependencyNames(select).size) return;
      refreshTasks.push(refreshDependentSelectOptions(select, { notifyChange: false }));
    });

    form.querySelectorAll('fieldset.sg-radio-group--boolean[data-dependencies]').forEach(fieldset => {
      if (!parseDependencyNames(fieldset).size) return;
      refreshTasks.push(refreshDependentBooleanOptions(fieldset, { notifyChange: false }));
    });

    await Promise.all(refreshTasks);
  }

  function clearCustomFormState(form, { skipRender = false } = {}) {
    if (!form) return;
    form.querySelectorAll('.lookup-checkbox-field, .checkbox-field').forEach(wrapper => {
      const state = wrapper.__checkboxState;
      if (!state) return;
      state.selected.clear();
      state.pinned.clear();
      state.query = '';
      state.searchResults = [];
      state.promoteSelected = false;

      const searchInput = wrapper.querySelector('input[type="text"]');
      const isSearchInput = searchInput
        && (
          searchInput.classList.contains('lookup-checkbox-field__search')
          || searchInput.classList.contains('checkbox-field__search')
        );
      if (isSearchInput) {
        searchInput.value = '';
      }

      if (!skipRender) {
        renderCheckboxOptions(
          wrapper,
          wrapper.classList.contains('lookup-checkbox-field') ? '.lookup-checkbox-field__options' : '.checkbox-field__options',
          wrapper.classList.contains('lookup-checkbox-field') ? 'lookup-checkbox-field__item' : 'checkbox-field__item'
        );
      }
    });

    form.querySelectorAll('input[data-meta-field="bool_not"]').forEach(input => {
      input.value = '';
    });
    form.querySelectorAll('.sg-not-toggle').forEach(button => {
      button.classList.remove('is-active');
      button.setAttribute('aria-pressed', 'false');
    });
  }

  function resetForm(form) {
    if (!form) return;
    form.dataset.sgInternalReset = 'true';
    form.reset();
    clearLookupInitialOptionsCache(form);
    clearCustomFormState(form);
    void refreshAllFieldOptions(form).finally(() => {
      bindSelectPlaceholderState(form);
      initBooleanToggleFields(form);
      syncMetaStateFromDom(form);
      commitAppliedFilters(form);
      dispatchFiltersChanged(form, { reason: 'reset' });
      delete form.dataset.sgInternalReset;
    });
  }

  function bindNativeResetHandling(root) {
    getFilterForms(root).forEach(form => {
      if (form.dataset.resetBound === 'true') return;

      form.addEventListener('reset', () => {
        if (form.dataset.sgInternalReset === 'true') return;
        window.setTimeout(() => {
          clearLookupInitialOptionsCache(form);
          rebuildCheckboxStateFromDom(form);
          void refreshAllFieldOptions(form).finally(() => {
            syncMetaStateFromDom(form);
            bindSelectPlaceholderState(form);
            initBooleanToggleFields(form);
          });
        }, 0);
      });

      form.dataset.resetBound = 'true';
    });
  }

  function dispatchFiltersReady(root) {
    const forms = getFilterForms(root);
    if (!forms.length) return;

    document.dispatchEvent(new CustomEvent('indicator:filters-ready', {
      detail: {
        formIds: forms.map(form => form.id).filter(Boolean),
      },
    }));
  }

  function syncFilterSidebarStickyOffset() {
    const sidebarHead = document.querySelector('.sg-filter-sidebar__head');
    if (!sidebarHead) return;

    const headerWrap = document.querySelector('#header-wrap') || document.querySelector('#header');
    if (!headerWrap) return;

    const bottom = headerWrap.getBoundingClientRect().bottom;
    const offset = Math.max(0, bottom);
    document.documentElement.style.setProperty('--sg-header-offset', `${offset}px`);
  }

  function initStickySidebarOffset() {
    let syncTimer = null;
    let isSyncing = false;

    function syncLoop() {
      syncFilterSidebarStickyOffset();
      if (isSyncing) {
        window.requestAnimationFrame(syncLoop);
      }
    }

    function handleScroll() {
      if (!isSyncing) {
        isSyncing = true;
        window.requestAnimationFrame(syncLoop);
      }
      clearTimeout(syncTimer);
      syncTimer = setTimeout(() => {
        isSyncing = false;
        // One final sync to ensure pixel-perfect end state
        syncFilterSidebarStickyOffset();
      }, 500);
    }

    window.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('resize', syncFilterSidebarStickyOffset, { passive: true });
    syncFilterSidebarStickyOffset();
  }

  async function init(root) {
    const container = root || document;
    initCollapsibleFilterGroups(container);
    initCollapsibleFieldRows(container);
    initNotToggles(container);
    initBooleanToggleFields(container);
    initLocalCheckboxFields(container);
    const lookupPromise = initLookupCheckboxFields(container);
    bindDependentFields(container);
    bindPromoteSelectedOnSubmit(container);
    bindNativeResetHandling(container);
    bindAppliedFiltersSummary(container);
    bindSelectPlaceholderState(container);
    initStickySidebarOffset();
    await lookupPromise;
    getFilterForms(container).forEach(commitAppliedFilters);
    dispatchFiltersReady(container);
  }

  document.addEventListener('DOMContentLoaded', () => {
    init(document);
  });

  document.addEventListener('click', handleBooleanToggleOptionClick);

  window.SearchGatewayFilterForm = {
    init,
    serializeForm,
    resetForm,
    commitAppliedFilters,
  };
})();
