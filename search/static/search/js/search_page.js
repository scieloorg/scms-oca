class SearchPageManager {
    constructor(config) {
        this.searchQuery = config.initialSearchQuery || '';
        this.dataSourceName = config.dataSourceName;
        this.apiEndpoint = config.apiEndpoint || '/search/api/search-results-list/';
        this.filters = config.filters || {};
        this.filterMetadata = config.filterMetadata || {};
        this.rangeFields = config.rangeFields || {};
        this.i18n = config.i18n || {
            loading: 'Carregando...',
            resultsCountSingular: 'resultado encontrado',
            resultsCountPlural: 'resultados encontrados',
            noResults: 'Nenhum resultado encontrado. Tente ajustar sua busca ou filtros.',
            filtersApplied: 'Filtros aplicados',
            labelType: 'Tipo',
            labelYear: 'Ano',
            labelInstitutions: 'Instituições',
            labelLocation: 'Localização',
            labelPractice: 'Prática',
            labelAction: 'Ação',
            labelClassification: 'Classificação',
            labelThematicAreas: 'Áreas Temáticas',
        };
        
        this.init();
    }
    
    init() {
        this.setupDataSourceSelector();
        this.setupSearchForm();
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
    
    async loadFiltersForDataSource(dataSource) {
        try {
            const response = await fetch(`/search/api/filters/?index_name=${dataSource}`);
            if (!response.ok) throw new Error('Failed to load filters');
            
            const data = await response.json();
            this.filters = data.filters || {};
            this.filterMetadata = data.filter_metadata || {};
            
            // Re-render filters HTML
            this.renderFilters();
            
            // Re-initialize Select2 for new filters
            this.setupFilters();
        } catch (error) {
            console.error('Error loading filters:', error);
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
                const searchInput = document.getElementById('search-input');
                this.searchQuery = searchInput ? searchInput.value : '';
                this.updateActiveFilters();
                this.applyFiltersAjax();
            });
        }
    }
    
    setupFilters() {
        Object.keys(this.filters).forEach(key => {
            this.initializeSelect2(key);
        });
    }
    
    initializeSelect2(key) {
        const selectElement = document.getElementById(key);
        if (!selectElement) return;
        
        const metadata = this.filterMetadata[key] || {};
        const config = {
            placeholder: 'Start typing to search...',
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
                processResults: (data) => ({
                    results: data.map(item => ({
                        id: item.key,
                        text: item.label || item.key
                    }))
                })
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
        $(selectElement).on('change', () => {
            this.updateActiveFilters();
            this.applyFiltersAjax();
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
        
        if (this.searchQuery) {
            params.append('search', this.searchQuery);
        }
        
        // Add index name
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
            filterStatus.innerHTML = `<i class="icon-spinner icon-spin"></i> ${this.i18n.loading}`;
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
                        ${this.i18n.noResults}
                    </div>
                `;
            }
        }
        
        if (filterStatus) {
            filterStatus.innerHTML = `<i class="icon-ok text-success"></i> ${this.i18n.filtersApplied}`;
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
        
        if (!container || !filtersBadgesContainer) return;
        
        // Update search query badge (cyan/info color)
        const hasSearchQuery = this.searchQuery && this.searchQuery.trim() !== '';
        if (searchBadge && searchSection) {
            if (hasSearchQuery) {
                searchBadge.innerHTML = `
                    <i class="icon-search"></i> ${this.escapeHtml(this.searchQuery)}
                    <button type="button" class="btn-close btn-close-white ms-1" style="font-size: 0.7rem;" onclick="window.searchPageManager.clearSearchQuery()"></button>
                `;
                searchSection.style.display = 'block';
            } else {
                searchSection.style.display = 'none';
            }
        }
        
        // Build filter badges (blue color with filter icon)
        let filterBadgesHtml = '';
        let hasFilters = false;
        
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
                    
                    filterBadgesHtml += `
                        <span class="badge" style="background-color: #5b9bd5; color: white; font-size: 0.85rem;">
                            <i class="icon-filter"></i> <strong>${this.escapeHtml(label).toUpperCase()}:</strong> ${this.escapeHtml(selectedText)}
                            <button type="button" class="btn-close btn-close-white ms-1" style="font-size: 0.7rem;" onclick="window.searchPageManager.removeFilter('${key}')"></button>
                        </span>
                    `;
                } else {
                    // Multiple selection
                    selectedValues.forEach(value => {
                        const option = $(selectElement).find(`option[value="${this.escapeHtml(value)}"]`);
                        const optionText = option.text() || value;
                        
                        filterBadgesHtml += `
                            <span class="badge" style="background-color: #5b9bd5; color: white; font-size: 0.85rem;">
                                <i class="icon-filter"></i> <strong>${this.escapeHtml(label).toUpperCase()}:</strong> ${this.escapeHtml(optionText)}
                                <button type="button" class="btn-close btn-close-white ms-1" style="font-size: 0.7rem;" data-filter-key="${key}" data-filter-value="${this.escapeHtml(value)}"></button>
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
                filtersSection.style.display = 'block';
            } else {
                filtersSection.style.display = 'none';
            }
        }
        
        // Show/hide main container based on whether there are active filters or search
        if (hasSearchQuery || hasFilters) {
            container.style.display = 'block';
        } else {
            container.style.display = 'none';
        }
    }
    
    clearSearchQuery() {
        this.searchQuery = '';
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.value = '';
        }
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
        
        // Update active filters display after preselecting from URL
        this.updateActiveFilters();
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (window.searchPageConfig) {
        window.searchPageManager = new SearchPageManager(window.searchPageConfig);
    }
});