class SearchPageManager {
    constructor(config) {
        this.searchQuery = config.initialSearchQuery || '';
        this.searchClauses = config.initialSearchClauses || [];
        this.dataSourceName = config.dataSourceName;
        this.apiEndpoint = config.apiEndpoint || '/search/api/search-results-list/';
        this.filters = config.filters || {};
        this.filterMetadata = config.filterMetadata || {};
        this.searchableFields = config.searchableFields || [];
        this.rangeFields = config.rangeFields || {};
        this.isUpdatingFilterOptions = false;
        
        this.init();
    }
    
    init() {
        this.setupDataSourceSelector();
        this.setupSearchForm();
        this.setupAdvancedSearchUI();
        this.setupFilters();
        this.updateActiveFilters();
        this.preselectFiltersFromURL();
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
        
        // Clear current filters
        this.clearAllFilters();
        
        // Fetch new filters for the selected data source
        await this.loadFiltersForDataSource(newDataSource);
        
        // Apply filters and get new results
        this.applyFiltersAjax();
    }
    
    clearAllFilters() {
        // Destroy all Select2 instances
        Object.keys(this.filters).forEach(key => {
            const selectElement = document.getElementById(key);
            if (selectElement && $(selectElement).data('select2')) {
                $(selectElement).select2('destroy');
            }
        });
        
        // Clear filters container
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

            const response = await fetch(`/search/api/filters/?${params.toString()}`);
            if (!response.ok) throw new Error('Failed to load filters');
            
            const data = await response.json();
            this.filters = data.filters || {};
            this.filterMetadata = data.filter_metadata || {};

            if (optionsOnly) {
                this.updateFilterOptionsOnly(selectedFilters);
            } else {
                // Re-render filters HTML
                this.renderFilters();

                // Re-initialize Select2 for new filters
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
            const options = this.filters[key];
            const metadata = this.filterMetadata[key] || {};
            const label = metadata.label || key;
            
            if (metadata.class_filter === 'range') {
                // Range filters would need special handling
                return;
            }
            
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
                this.applyFiltersAjax();
            });
        }
    }

    setupAdvancedSearchUI() {
        const btnAdd = document.getElementById('btn-add-field');
        const btnClear = document.getElementById('btn-clear');
        if (btnAdd) {
            btnAdd.addEventListener('click', () => this.addSearchRow());
        }
        if (btnClear) {
            btnClear.addEventListener('click', () => this.clearSearchQuery());
        }
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
                clauses.push({
                    operator: '',
                    field: fieldSelect ? fieldSelect.value : 'all',
                    text: text
                });
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
        if (row && row.parentElement?.id === 'advanced-search-rows') {
            row.remove();
        }
    }
    
    setupFilters() {
        Object.keys(this.filters).forEach(key => {
            this.initializeSelect2(key);
        });
    }

    getCurrentSelectedFilters() {
        const selectedFilters = {};

        Object.keys(this.filters).forEach(key => {
            const selectElement = document.getElementById(key);
            if (!selectElement) return;

            const selectedValues = $(selectElement).val();
            const metadata = this.filterMetadata[key] || {};

            if (metadata.multiple_selection === false) {
                if (selectedValues && selectedValues !== '') {
                    selectedFilters[key] = [selectedValues];
                }
            } else if (Array.isArray(selectedValues) && selectedValues.length > 0) {
                const validValues = selectedValues.filter(value => value && value !== '');
                if (validValues.length > 0) {
                    selectedFilters[key] = validValues;
                }
            }
        });

        return selectedFilters;
    }

    updateFilterOptionsOnly(selectedFilters = {}) {
        Object.keys(this.filters).forEach(key => {
            const selectElement = document.getElementById(key);
            if (!selectElement) return;

            const metadata = this.filterMetadata[key] || {};
            const options = this.filters[key] || [];
            const placeholderOption = metadata.multiple_selection === false
                ? `<option value="">${metadata.label || key}</option>`
                : '';
            const selectedLabelsByValue = new Map();
            const preservedValues = selectedFilters[key] || [];

            // Preserve currently selected labels (including async Select2 options)
            // so we can re-add them if they are not returned in refreshed buckets.
            Array.from(selectElement.options).forEach(option => {
                if (option.value !== '') {
                    selectedLabelsByValue.set(option.value, option.text);
                }
            });

            const select2Data = $(selectElement).select2('data') || [];
            select2Data.forEach(item => {
                if (item && item.id !== undefined && item.id !== null) {
                    selectedLabelsByValue.set(String(item.id), item.text || String(item.id));
                }
            });

            selectElement.innerHTML = `
                ${placeholderOption}
                ${options.map(opt => `<option value="${opt.key}">${opt.label}</option>`).join('')}
            `;

            const availableValues = new Set(Array.from(selectElement.options).map(option => option.value));
            preservedValues.forEach(value => {
                if (!value || availableValues.has(value)) return;

                const fallbackLabel = selectedLabelsByValue.get(value) || value;
                const option = new Option(fallbackLabel, value, false, true);
                selectElement.add(option);
                availableValues.add(value);
            });

            // Keep Select2 in sync with updated <option> list
            $(selectElement).trigger('change.select2');
        });

        this.restoreSelectedFilters(selectedFilters);
    }

    restoreSelectedFilters(selectedFilters = {}) {
        Object.keys(selectedFilters).forEach(key => {
            const selectElement = document.getElementById(key);
            if (!selectElement) return;

            const metadata = this.filterMetadata[key] || {};
            const availableValues = new Set(Array.from(selectElement.options).map(option => option.value));
            const validValues = (selectedFilters[key] || []).filter(value => availableValues.has(value));

            if (metadata.multiple_selection === false) {
                $(selectElement).val(validValues[0] || '');
            } else {
                $(selectElement).val(validValues);
            }

            $(selectElement).trigger('change.select2');
        });
    }
    
    initializeSelect2(key) {
        const selectElement = document.getElementById(key);
        if (!selectElement) return;
        
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
                data: (params) => ({
                    q: params.term,
                    field_name: key,
                    index_name: this.dataSourceName
                }),
                processResults: (data) => {
                    const items = Array.isArray(data) ? data : Array.isArray(data?.results) ? data.results : [];
                    return {
                        results: items.map(item => ({
                        id: item.key,
                        text: item.label || item.key
                    }))
                    };
                }
            };
            config.minimumInputLength = 2;
        }
        
        $(selectElement).select2(config);
        
        // Auto-focus
        $(selectElement).on('select2:open', (e) => {
            const searchField = document.querySelector(`[aria-controls="select2-${e.target.id}-results"]`);
            if (searchField) searchField.focus();
        });
        
        // AJAX on change
        $(selectElement).on('change', async () => {
            if (this.isUpdatingFilterOptions) return;

            this.isUpdatingFilterOptions = true;
            try {
                const selectedFilters = this.getCurrentSelectedFilters();
                await this.loadFiltersForDataSource(this.dataSourceName, selectedFilters, { optionsOnly: true });
                this.updateActiveFilters();
                this.applyFiltersAjax();
            } catch (error) {
                console.error('Error updating filter options:', error);
            } finally {
                this.isUpdatingFilterOptions = false;
            }
        });
    }
    
    applyFiltersAjax() {
        const resultsContainer = document.getElementById('results-container');
        const filterStatus = document.getElementById('filter-status');
        
        this.showLoading(filterStatus, resultsContainer);
        
        const params = this.buildSearchParams();
        
        fetch(`${this.apiEndpoint}?${params.toString()}`)
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.json();
            })
            .then(data => this.handleSearchResults(data, resultsContainer, filterStatus))
            .catch(error => this.handleSearchError(error, resultsContainer, filterStatus));
    }
    
    buildSearchParams() {
        const params = new URLSearchParams();
        const clauses = this.getSearchClauses();
        
        if (clauses.length > 0) {
            params.append('search_clauses', JSON.stringify(clauses));
        } else if (this.searchQuery) {
            params.append('search', this.searchQuery);
        }
        
        if (this.dataSourceName) {
            params.append('index_name', this.dataSourceName);
        }
        
        Object.keys(this.filters).forEach(key => {
            const selectElement = document.getElementById(key);
            if (!selectElement) return;
            
            const selectedValues = $(selectElement).val();
            const metadata = this.filterMetadata[key] || {};
            
            if (metadata.multiple_selection === false) {
                if (selectedValues && selectedValues !== '') {
                    params.append(key, selectedValues);
                }
            } else {
                if (selectedValues && selectedValues.length > 0) {
                    selectedValues.forEach(value => {
                        if (value && value !== '') {
                            params.append(key, value);
                        }
                    });
                }
            }
        });
        
        return params;
    }
    
    showLoading(filterStatus, resultsContainer) {
        if (filterStatus) {
            filterStatus.innerHTML = `<i class="icon-spinner icon-spin"></i> ${gettext('Loading...')}`;
        }
        if (resultsContainer) {
            resultsContainer.innerHTML = '<div class="text-center p-5"><i class="icon-spinner icon-spin icon-2x"></i></div>';
        }
    }
    
    handleSearchResults(data, resultsContainer, filterStatus) {
        if (resultsContainer) {
            if (data.results_html) {
                resultsContainer.innerHTML = data.results_html;
            } else {
                resultsContainer.innerHTML = `
                    <div class="alert alert-info" role="alert">
                        <i class="icon-info-sign"></i> 
                        ${gettext('No results found. Try adjusting your search or filters.')}
                    </div>
                `;
            }
        }
        
        if (filterStatus) {
            filterStatus.innerHTML = `<i class="icon-ok text-success"></i> ${gettext('Filters applied')}`;
            setTimeout(() => {
                filterStatus.innerHTML = '';
            }, 2000);
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
        if (resultsContainer) {
            resultsContainer.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    <i class="icon-exclamation-sign"></i> 
                    Erro ao carregar resultados. Tente novamente.
                </div>
            `;
        }
        if (filterStatus) {
            filterStatus.innerHTML = '<i class="icon-exclamation-sign text-danger"></i> Erro';
        }
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
                const badges = clauses.map((c, i) => {
                    const fieldLabel = fieldLabels[c.field] || c.field;
                    const op = c.operator ? ` ${c.operator} ` : '';
                    return `<span class="applied-filter-chip">${i > 0 ? op : ''}<i class="icon-filter"></i> <strong>${this.escapeHtml(fieldLabel)}:</strong> ${this.escapeHtml(c.text)}</span>`;
                }).join('');
                searchBadge.innerHTML = `
                ${badges}
                <span class="applied-filter-chip">
                    <button type="button" class="btn-close btn-close-black ms-1" style="font-size: 0.7rem;" onclick="window.searchPageManager.clearSearchQuery()"></button>
                </span>
                `;
                searchSection.classList.remove('d-none');
            } else {
                searchSection.classList.add('d-none');
            }
        }
        
        // Build filter badges (blue color with filter icon)
        let filterBadgesHtml = '';
        let hasFilters = false;
        let activeFilterCount = 0;
        
        Object.keys(this.filters).forEach(key => {
            const selectElement = document.getElementById(key);
            if (!selectElement) return;
            
            const selectedValues = $(selectElement).val();
            const metadata = this.filterMetadata[key] || {};
            const label = metadata.label || key;
            
            if (selectedValues && selectedValues.length > 0) {
                hasFilters = true;
                
                if (metadata.multiple_selection === false) {
                    // Single selection
                    const selectedOption = $(selectElement).find('option:selected');
                    const selectedText = selectedOption.text();
                    activeFilterCount += 1;
                    
                    filterBadgesHtml += `
                        <span class="applied-filter-chip">
                            <i class="icon-filter"></i> <strong>${this.escapeHtml(label)}:</strong> ${this.escapeHtml(selectedText)}
                            <button type="button" class="btn-close btn-close-black  ms-1" style="font-size: 0.7rem;" onclick="window.searchPageManager.removeFilter('${key}')"></button>
                        </span>
                    `;
                } else {
                    // Multiple selection
                    selectedValues.forEach(value => {
                        const option = $(selectElement).find(`option[value="${this.escapeHtml(value)}"]`);
                        const optionText = option.text() || value;
                        activeFilterCount += 1;
                        
                        filterBadgesHtml += `
                            <span class="applied-filter-chip">
                                <i class="icon-filter"></i> <strong>${this.escapeHtml(label)}:</strong> ${this.escapeHtml(optionText)}
                                <button type="button" class="btn-close btn-close-black  ms-1" style="font-size: 0.7rem;" data-filter-key="${key}" data-filter-value="${this.escapeHtml(value)}"></button>
                            </span>
                        `;
                    });
                }
            }
        });
        
        filtersBadgesContainer.innerHTML = filterBadgesHtml;
        
        // Add event listeners to filter close buttons
        filtersBadgesContainer.querySelectorAll('.btn-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const filterKey = e.target.getAttribute('data-filter-key');
                const filterValue = e.target.getAttribute('data-filter-value');
                if (filterKey && filterValue) {
                    this.removeFilterValue(filterKey, filterValue);
                }
            });
        });
        
        // Show/hide filters section
        if (filtersSection) {
            if (hasFilters) {
                filtersSection.classList.remove('d-none');
            } else {
                filtersSection.classList.add('d-none');
            }
        }
        if (filtersCount) {
            filtersCount.textContent = String(activeFilterCount);
        }
        
        if (hasSearchClauses || hasFilters) {
            container.classList.remove('d-none');
        } else {
            container.classList.add('d-none');
        }
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
        const selectElement = document.getElementById(filterKey);
        if (selectElement) {
            $(selectElement).val(null).trigger('change');
        }
    }
    
    removeFilterValue(filterKey, value) {
        const selectElement = document.getElementById(filterKey);
        if (selectElement) {
            const currentValues = $(selectElement).val() || [];
            const newValues = currentValues.filter(v => v !== value);
            $(selectElement).val(newValues).trigger('change');
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
                        const fieldSelect = firstRow.querySelector('.search-field-select');
                        const textInput = firstRow.querySelector('.search-text-input');
                        if (fieldSelect) fieldSelect.value = c.field || 'all';
                        if (textInput) textInput.value = c.text || '';
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
                                const operatorSelect = row.querySelector('.search-operator');
                                const fieldSelect = row.querySelector('.search-field-select');
                                const textInput = row.querySelector('.search-text-input');
                                if (operatorSelect) operatorSelect.value = c.operator || 'AND';
                                if (fieldSelect) fieldSelect.value = c.field || 'all';
                                if (textInput) textInput.value = c.text || '';
                            }
                        }
                    }
                }
            } catch (e) {
                console.warn('Invalid search_clauses in URL', e);
            }
        }
        
        Object.keys(this.filters).forEach(key => {
            const urlValues = urlParams.getAll(key);
            if (urlValues.length > 0) {
                const selectElement = document.getElementById(key);
                if (selectElement) {
                    const metadata = this.filterMetadata[key] || {};
                    if (metadata.multiple_selection === false) {
                        $(selectElement).val(urlValues[0]).trigger('change.select2');
                    } else {
                        $(selectElement).val(urlValues).trigger('change.select2');
                    }
                }
            }
        });
        
        this.updateActiveFilters();
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (window.searchPageConfig) {
        window.searchPageManager = new SearchPageManager(window.searchPageConfig);
    }
});