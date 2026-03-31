/**
 * Observation search page JS - duplicated from search.
 * Uses config.apiEndpoint and config.filtersApiEndpoint for observation APIs.
 */
class SearchPageManager {
    constructor(config) {
        this.searchQuery = config.initialSearchQuery || '';
        this.searchClauses = config.initialSearchClauses || [];
        this.dataSourceName = config.dataSourceName;
        this.apiEndpoint = config.apiEndpoint || '/observation/api/search-results-list/';
        this.filtersApiEndpoint = config.filtersApiEndpoint || '/observation/api/filters/';
        this.filters = config.filters || {};
        this.filterMetadata = config.filterMetadata || {};
        this.searchableFields = config.searchableFields || [];
        this.rangeFields = config.rangeFields || {};
        this.isUpdatingFilterOptions = false;
        config.getSearchClauses = () => this.getSearchClauses();

        this.init();
    }

    init() {
        this.setupDataSourceSelector();
        this.setupSearchForm();
        this.setupAdvancedSearchUI();
        this.setupFilters();
        this.setupObservationFilterButtons();
        this.updateActiveFilters();
        this.preselectFiltersFromURL();
    }

    isSelect2Available() {
        return typeof $ !== 'undefined' && $.fn && typeof $.fn.select2 === 'function';
    }

    setupDataSourceSelector() {
        const dataSourceSelect = document.getElementById('data-source-select');
        if (dataSourceSelect) {
            dataSourceSelect.addEventListener('change', (e) => {
                this.handleDataSourceChange(e.target.value);
            });
        }
    }

    async handleDataSourceChange(newDataSource) {
        this.dataSourceName = newDataSource;
        this.clearAllFilters();
        await this.loadFiltersForDataSource(newDataSource);
    }

    clearAllFilters() {
        Object.keys(this.filters).forEach(key => {
            const selectElement = document.getElementById(key);
            if (
                this.isSelect2Available() &&
                selectElement &&
                selectElement.tagName === 'SELECT' &&
                $(selectElement).data('select2')
            ) {
                $(selectElement).select2('destroy');
            }
        });
        const filtersContainer = document.getElementById('filters-container');
        if (filtersContainer) {
            filtersContainer.innerHTML = '<div class="text-center p-3"><i class="icon-spinner icon-spin"></i> Carregando filtros...</div>';
        }
    }

    async loadFiltersForDataSource(dataSource, selectedFilters = {}, options = {}) {
        const { optionsOnly = false } = options;
        try {
            const params = new URLSearchParams();
            params.append('index_name', dataSource);
            Object.entries(selectedFilters).forEach(([filterKey, values]) => {
                (values || []).forEach(value => {
                    if (value !== null && value !== undefined && value !== '') {
                        params.append(filterKey, value);
                    }
                });
            });
            const response = await fetch(`${this.filtersApiEndpoint}?${params.toString()}`);
            if (!response.ok) throw new Error('Failed to load filters');
            const data = await response.json();
            this.filters = data.filters || {};
            this.filterMetadata = data.filter_metadata || {};
            if (optionsOnly) {
                this.updateFilterOptionsOnly(selectedFilters);
            } else {
                this.renderFilters();
                this.setupFilters();
            }
        } catch (error) {
            console.error('Error loading filters:', error);
            if (optionsOnly) return;
            const filtersContainer = document.getElementById('filters-container');
            if (filtersContainer) {
                filtersContainer.innerHTML = `
                    <div class="alert alert-danger" role="alert">
                        <i class="icon-exclamation-sign"></i>
                        Erro ao carregar filtros.
                    </div>
                `;
            }
        }
    }

    renderFilters() {
        const filtersContainer = document.getElementById('filters-container');
        if (!filtersContainer) return;
        let html = '';
        Object.keys(this.filters).forEach(key => {
            const options = Array.isArray(this.filters[key]) ? this.filters[key] : [];
            const metadata = this.filterMetadata[key] || {};
            const label = metadata.label || key;
            if (metadata.class_filter === 'range') return;
            const multiple = metadata.multiple_selection !== false ? 'multiple' : '';
            html += `
                <div class="form-group mb-3">
                    <label class="form-label" for="${key}">${label}</label>
                    <select ${multiple} id="${key}" name="${key}" class="form-control filter-select" data-filter-key="${key}" aria-label="${label}">
                        ${metadata.multiple_selection === false ? `<option value="">${label}</option>` : ''}
                        ${options.map(opt => `<option value="${opt.key}">${opt.label}</option>`).join('')}
                    </select>
                </div>
            `;
        });
        filtersContainer.innerHTML = html;
    }

    setupSearchForm() {
        const searchForm = document.getElementById('search-form');
        if (searchForm) {
            searchForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.searchClauses = this.getSearchClauses();
                this.updateActiveFilters();
            });
        }
    }

    setupAdvancedSearchUI() {
        const btnAdd = document.getElementById('btn-add-field');
        const btnClear = document.getElementById('btn-clear');
        if (btnAdd) btnAdd.addEventListener('click', () => this.addSearchRow());
        if (btnClear) btnClear.addEventListener('click', () => this.clearSearchQuery());
        document.getElementById('advanced-search-rows')?.addEventListener('click', (e) => {
            if (e.target.closest('.btn-remove-row')) {
                this.removeSearchRow(e.target.closest('.btn-remove-row'));
            }
        });
    }

    getSearchClauses() {
        const clauses = [];
        const firstRow = document.querySelector('.advanced-search-row[data-row-index="0"]');
        if (firstRow) {
            const fieldSelect = firstRow.querySelector('.search-field-select');
            const textInput = firstRow.querySelector('.search-text-input');
            const text = textInput ? textInput.value.trim() : '';
            if (text) {
                clauses.push({ operator: '', field: fieldSelect ? fieldSelect.value : 'all', text: text });
            }
        }
        document.querySelectorAll('#advanced-search-rows .advanced-search-row').forEach(row => {
            const operatorSelect = row.querySelector('.search-operator');
            const fieldSelect = row.querySelector('.search-field-select');
            const textInput = row.querySelector('.search-text-input');
            const text = textInput ? textInput.value.trim() : '';
            if (text) {
                clauses.push({
                    operator: operatorSelect ? operatorSelect.value : 'AND',
                    field: fieldSelect ? fieldSelect.value : 'all',
                    text: text
                });
            }
        });
        return clauses;
    }

    addSearchRow() {
        const template = document.getElementById('advanced-search-row-template');
        const container = document.getElementById('advanced-search-rows');
        if (!template || !container) return;
        const clone = template.content.cloneNode(true);
        const row = clone.querySelector('.advanced-search-row');
        row.dataset.rowIndex = String(container.children.length + 1);
        container.appendChild(clone);
    }

    removeSearchRow(btn) {
        const row = btn?.closest('.advanced-search-row');
        if (row && row.parentElement?.id === 'advanced-search-rows') row.remove();
    }

    setupFilters() {
        Object.keys(this.filters).forEach(key => {
            const metadata = this.filterMetadata[key] || {};
            if (metadata.class_filter === 'range') return;
            this.initializeSelect2(key);
        });
    }

    getCurrentSelectedFilters() {
        const selectedFilters = {};
        Object.keys(this.filters).forEach(key => {
            const selectElement = document.getElementById(key);
            if (!selectElement || selectElement.tagName !== 'SELECT') return;
            const selectedValues = $(selectElement).val();
            const metadata = this.filterMetadata[key] || {};
            if (metadata.multiple_selection === false) {
                if (selectedValues && selectedValues !== '') selectedFilters[key] = [selectedValues];
            } else if (Array.isArray(selectedValues) && selectedValues.length > 0) {
                const validValues = selectedValues.filter(value => value && value !== '');
                if (validValues.length > 0) selectedFilters[key] = validValues;
            }
        });
        return selectedFilters;
    }

    updateFilterOptionsOnly(selectedFilters = {}) {
        Object.keys(this.filters).forEach(key => {
            const selectElement = document.getElementById(key);
            if (!selectElement || selectElement.tagName !== 'SELECT' || !selectElement.options) return;
            const metadata = this.filterMetadata[key] || {};
            const options = Array.isArray(this.filters[key]) ? this.filters[key] : [];
            const placeholderOption = metadata.multiple_selection === false ? `<option value="">${metadata.label || key}</option>` : '';
            const selectedLabelsByValue = new Map();
            const preservedValues = selectedFilters[key] || [];
            Array.from(selectElement.options).forEach(option => {
                if (option.value !== '') selectedLabelsByValue.set(option.value, option.text);
            });
            if (this.isSelect2Available()) {
                ($(selectElement).select2('data') || []).forEach(item => {
                    if (item && item.id != null) selectedLabelsByValue.set(String(item.id), item.text || String(item.id));
                });
            }
            selectElement.innerHTML = placeholderOption + options.map(opt => `<option value="${opt.key}">${opt.label}</option>`).join('');
            const availableValues = new Set(Array.from(selectElement.options).map(o => o.value));
            preservedValues.forEach(value => {
                if (!value || availableValues.has(value)) return;
                selectElement.add(new Option(selectedLabelsByValue.get(value) || value, value, false, true));
            });
            if (this.isSelect2Available()) {
                $(selectElement).trigger('change.select2');
            } else {
                selectElement.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });
        this.restoreSelectedFilters(selectedFilters);
    }

    restoreSelectedFilters(selectedFilters = {}) {
        Object.keys(selectedFilters).forEach(key => {
            const selectElement = document.getElementById(key);
            if (!selectElement || selectElement.tagName !== 'SELECT' || !selectElement.options) return;
            const metadata = this.filterMetadata[key] || {};
            const availableValues = new Set(Array.from(selectElement.options).map(o => o.value));
            const validValues = (selectedFilters[key] || []).filter(value => availableValues.has(value));
            if (this.isSelect2Available()) {
                $(selectElement).val(metadata.multiple_selection === false ? (validValues[0] || '') : validValues).trigger('change.select2');
            } else if (metadata.multiple_selection === false) {
                selectElement.value = validValues[0] || '';
                selectElement.dispatchEvent(new Event('change', { bubbles: true }));
            } else {
                Array.from(selectElement.options).forEach(option => {
                    option.selected = validValues.includes(option.value);
                });
                selectElement.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });
    }

    initializeSelect2(key) {
        const selectElement = document.getElementById(key);
        if (!selectElement || selectElement.tagName !== 'SELECT') return;
        const metadata = this.filterMetadata[key] || {};
        const config = {
            placeholder: gettext('Type to filter'),
            theme: 'bootstrap-5',
            allowClear: metadata.multiple_selection == false,
            multiple: metadata.multiple_selection !== false
        };
        if (metadata.support_search_as_you_type) {
            config.ajax = {
                url: '/search-gateway/search-as-you-type/',
                dataType: 'json',
                delay: 300,
                data: (params) => ({ q: params.term, field_name: key, index_name: this.dataSourceName }),
                processResults: (data) => {
                    const items = Array.isArray(data) ? data : Array.isArray(data?.results) ? data.results : [];
                    return { results: items.map(item => ({ id: item.key, text: item.label || item.key })) };
                }
            };
            config.minimumInputLength = 2;
        }
        const onFilterChange = async () => {
            if (this.isUpdatingFilterOptions) return;
            this.isUpdatingFilterOptions = true;
            try {
                const selectedFilters = this.getCurrentSelectedFilters();
                await this.loadFiltersForDataSource(this.dataSourceName, selectedFilters, { optionsOnly: true });
                this.updateActiveFilters();
            } catch (error) {
                console.error('Error updating filter options:', error);
            } finally {
                this.isUpdatingFilterOptions = false;
            }
        };

        if (this.isSelect2Available()) {
            $(selectElement).select2(config);
            $(selectElement).on('select2:open', (e) => {
                const searchField = document.querySelector(`[aria-controls="select2-${e.target.id}-results"]`);
                if (searchField) searchField.focus();
            });
            $(selectElement).on('change', onFilterChange);
        } else {
            // Graceful fallback when Select2 assets are unavailable.
            selectElement.addEventListener('change', onFilterChange);
        }
    }

    setupObservationFilterButtons() {
        const resetBtn = document.getElementById('observation-filter-reset');
        const generateBtn = document.getElementById('observation-filter-generate');
        const filterForm = document.getElementById('observation-filter-form');
        if (resetBtn) {
            resetBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (filterForm) {
                    if (window.SearchGatewayFilterForm) {
                        window.SearchGatewayFilterForm.resetForm(filterForm);
                    } else {
                        filterForm.reset();
                    }
                } else {
                    this.restoreSelectedFilters({});
                    document.querySelectorAll('.range-filter').forEach(el => { el.value = ''; });
                }
                this.searchQuery = '';
                this.searchClauses = [];
                this.updateActiveFilters();
                this.applyFiltersAjax();
            });
        }
        if (generateBtn) {
            generateBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.applyFiltersAjax();
            });
        }

        if (filterForm) {
            const syncAppliedSummary = () => {
                if (window.SearchGatewayFilterForm?.commitAppliedFilters) {
                    window.SearchGatewayFilterForm.commitAppliedFilters(filterForm);
                }
            };
            filterForm.addEventListener('change', syncAppliedSummary);
            filterForm.addEventListener('input', syncAppliedSummary);
            filterForm.addEventListener('search-gateway:filters-changed', () => {
                syncAppliedSummary();
                this.applyFiltersAjax();
            });
            syncAppliedSummary();
        }
    }

    applyFiltersAjax() {
        const resultsContainer = document.getElementById('results-container');
        const filterStatus = document.getElementById('filter-status');
        this.showLoading(filterStatus, resultsContainer);
        const params = this.buildSearchParams();
        fetch(`${this.apiEndpoint}?${params.toString()}`)
            .then(response => { if (!response.ok) throw new Error('Network response was not ok'); return response.json(); })
            .then(data => {
                this.handleSearchResults(data, resultsContainer, filterStatus);
                if (typeof window.loadAndInitObservationTable === 'function') {
                    window.loadAndInitObservationTable();
                }
            })
            .catch(error => this.handleSearchError(error, resultsContainer, filterStatus));
    }

    buildSearchParams() {
        const params = new URLSearchParams();
        const clauses = this.getSearchClauses();
        if (clauses.length > 0) params.append('search_clauses', JSON.stringify(clauses));
        else if (this.searchQuery) params.append('search', this.searchQuery);
        if (this.dataSourceName) params.append('index_name', this.dataSourceName);

        const filterForm = document.getElementById('observation-filter-form');
        if (filterForm) {
            const formData = new FormData(filterForm);
            formData.forEach((value, key) => {
                if (
                    key === 'csrfmiddlewaretoken' ||
                    key === 'search' ||
                    key === 'search_clauses' ||
                    key === 'index_name'
                ) {
                    return;
                }
                if (value !== null && value !== undefined && String(value).trim() !== '') {
                    params.append(key, value);
                }
            });
        }

        return params;
    }

    showLoading(filterStatus, resultsContainer) {
        if (filterStatus) filterStatus.innerHTML = `<i class="icon-spinner icon-spin"></i> ${gettext('Loading...')}`;
        if (resultsContainer) resultsContainer.innerHTML = '<div class="text-center p-5"><i class="icon-spinner icon-spin icon-2x"></i></div>';
    }

    handleSearchResults(data, resultsContainer, filterStatus) {
        if (resultsContainer) {
            resultsContainer.innerHTML = data.results_html || `<div class="alert alert-info"><i class="icon-info-sign"></i> ${gettext('No results found. Try adjusting your search or filters.')}</div>`;
        }
        if (filterStatus) {
            filterStatus.innerHTML = `<i class="icon-ok text-success"></i> ${gettext('Filters applied')}`;
            setTimeout(() => { filterStatus.innerHTML = ''; }, 2000);
        }
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }

    handleSearchError(error, resultsContainer, filterStatus) {
        console.error('Error applying filters:', error);
        if (resultsContainer) resultsContainer.innerHTML = `<div class="alert alert-danger"><i class="icon-exclamation-sign"></i> Erro ao carregar resultados. Tente novamente.</div>`;
        if (filterStatus) filterStatus.innerHTML = '<i class="icon-exclamation-sign text-danger"></i> Erro';
    }

    updateActiveFilters() {
        const container = document.getElementById('active-filters-container');
        const searchSection = document.getElementById('search-query-section');
        const searchBadge = document.getElementById('search-query-badge');
        const filtersSection = document.getElementById('filters-section');
        const filtersBadgesContainer = document.getElementById('selected-filters-badges');
        const filtersCount = document.getElementById('active-filters-count');
        if (!container || !filtersBadgesContainer) return;
        const clauses = this.searchClauses.length > 0 ? this.searchClauses : this.getSearchClauses();
        const hasSearchClauses = clauses.length > 0;
        const fieldLabels = Object.fromEntries((this.searchableFields || []).map(f => [f.value, f.label]));
        if (searchBadge && searchSection) {
            if (hasSearchClauses) {
                searchBadge.innerHTML = clauses.map((c, i) => {
                    const fieldLabel = fieldLabels[c.field] || c.field;
                    return `<span class="applied-filter-chip">${i > 0 ? ' ' + (c.operator || 'AND') + ' ' : ''}<i class="icon-filter"></i> <strong>${this.escapeHtml(fieldLabel)}:</strong> ${this.escapeHtml(c.text)}</span>`;
                }).join('') + `<span class="applied-filter-chip"><button type="button" class="btn-close btn-close-black ms-1" style="font-size: 0.7rem;" onclick="window.searchPageManager.clearSearchQuery()"></button></span>`;
                searchSection.classList.remove('d-none');
            } else searchSection.classList.add('d-none');
        }
        let filterBadgesHtml = '';
        let hasFilters = false;
        let activeFilterCount = 0;
        Object.keys(this.filters).forEach(key => {
            const selectElement = document.getElementById(key);
            if (!selectElement || selectElement.tagName !== 'SELECT') return;
            const selectedValues = $(selectElement).val();
            const metadata = this.filterMetadata[key] || {};
            const label = metadata.label || key;
            const vals = metadata.multiple_selection === false
                ? (selectedValues && selectedValues !== '' ? [selectedValues] : [])
                : (Array.isArray(selectedValues) ? selectedValues : []);
            if (vals.length > 0) {
                hasFilters = true;
                vals.forEach(value => {
                    activeFilterCount++;
                    const option = $(selectElement).find(`option[value="${this.escapeHtml(value)}"]`);
                    const text = (option.length ? option.text() : null) || value;
                    filterBadgesHtml += `<span class="applied-filter-chip"><i class="icon-filter"></i> <strong>${this.escapeHtml(label)}:</strong> ${this.escapeHtml(text)}<button type="button" class="btn-close btn-close-black ms-1" style="font-size: 0.7rem;" data-filter-key="${key}" data-filter-value="${this.escapeHtml(value)}"></button></span>`;
                });
            }
        });
        filtersBadgesContainer.innerHTML = filterBadgesHtml;
        filtersBadgesContainer.querySelectorAll('.btn-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const k = e.target.getAttribute('data-filter-key');
                const v = e.target.getAttribute('data-filter-value');
                if (k && v) this.removeFilterValue(k, v);
            });
        });
        if (filtersSection) filtersSection.classList.toggle('d-none', !hasFilters);
        if (filtersCount) filtersCount.textContent = String(activeFilterCount);
        container.classList.toggle('d-none', !hasSearchClauses && !hasFilters);
    }

    clearSearchQuery() {
        this.searchQuery = '';
        this.searchClauses = [];
        const firstRow = document.querySelector('.advanced-search-row[data-row-index="0"]');
        if (firstRow) {
            const fieldSelect = firstRow.querySelector('.search-field-select');
            const textInput = firstRow.querySelector('.search-text-input');
            if (fieldSelect) fieldSelect.value = 'all';
            if (textInput) textInput.value = '';
        }
        const extraRows = document.getElementById('advanced-search-rows');
        if (extraRows) extraRows.innerHTML = '';
        this.updateActiveFilters();
        this.applyFiltersAjax();
    }

    removeFilter(filterKey) {
        const el = document.getElementById(filterKey);
        if (el) $(el).val(null).trigger('change');
    }

    removeFilterValue(filterKey, value) {
        const el = document.getElementById(filterKey);
        if (el) {
            const current = $(el).val() || [];
            $(el).val(current.filter(v => v !== value)).trigger('change');
        }
    }

    preselectFiltersFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        const searchClausesParam = urlParams.get('search_clauses');
        if (searchClausesParam) {
            try {
                const clauses = JSON.parse(searchClausesParam);
                if (Array.isArray(clauses) && clauses.length > 0) {
                    this.searchClauses = clauses;
                    const firstRow = document.querySelector('.advanced-search-row[data-row-index="0"]');
                    if (firstRow && clauses[0]) {
                        const c = clauses[0];
                        const fs = firstRow.querySelector('.search-field-select');
                        const ti = firstRow.querySelector('.search-text-input');
                        if (fs) fs.value = c.field || 'all';
                        if (ti) ti.value = c.text || '';
                    }
                    const container = document.getElementById('advanced-search-rows');
                    if (container) {
                        container.innerHTML = '';
                        for (let i = 1; i < clauses.length; i++) {
                            this.addSearchRow();
                            const rows = container.querySelectorAll('.advanced-search-row');
                            const row = rows[rows.length - 1];
                            if (row && clauses[i]) {
                                const c = clauses[i];
                                const os = row.querySelector('.search-operator');
                                const fs = row.querySelector('.search-field-select');
                                const ti = row.querySelector('.search-text-input');
                                if (os) os.value = c.operator || 'AND';
                                if (fs) fs.value = c.field || 'all';
                                if (ti) ti.value = c.text || '';
                            }
                        }
                    }
                }
            } catch (e) { console.warn('Invalid search_clauses in URL', e); }
        }
        Object.keys(this.filters).forEach(key => {
            const urlValues = urlParams.getAll(key);
            if (urlValues.length > 0) {
                const el = document.getElementById(key);
                if (el && el.tagName === 'SELECT') {
                    const meta = this.filterMetadata[key] || {};
                    $(el).val(meta.multiple_selection === false ? urlValues[0] : urlValues).trigger('change.select2');
                }
            }
        });
        this.updateActiveFilters();
    }
}

document.addEventListener('DOMContentLoaded', function() {
    if (window.searchPageConfig) {
        window.searchPageManager = new SearchPageManager(window.searchPageConfig);
    }
});
