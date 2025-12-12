class SearchPageManager {
    constructor(config) {
        this.searchQuery = config.initialSearchQuery || '';
        this.dataSourceName = config.dataSourceName;
        this.apiEndpoint = config.apiEndpoint || '/search/api/search-results-list/';
        this.filters = config.filters || {};
        this.filterMetadata = config.filterMetadata || {};
        this.rangeFields = config.rangeFields || {};
        
        this.init();
    }
    
    init() {
        this.setupSearchForm();
        this.setupFilters();
        this.updateSearchQueryBadge();
        this.preselectFiltersFromURL();
    }
    
    setupSearchForm() {
        const searchForm = document.getElementById('search-form');
        if (searchForm) {
            searchForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const searchInput = document.getElementById('search-input');
                this.searchQuery = searchInput ? searchInput.value : '';
                this.updateSearchQueryBadge();
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
            allowClear: false,
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
                    data_source: this.dataSourceName
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
        $(selectElement).on('change', () => this.applyFiltersAjax());
    }
    
    applyFiltersAjax() {
        const resultsContainer = document.getElementById('results-list');
        const resultsCount = document.getElementById('results-count');
        const filterStatus = document.getElementById('filter-status');
        
        this.showLoading(filterStatus, resultsContainer);
        
        const params = this.buildSearchParams();
        
        fetch(`${this.apiEndpoint}?${params.toString()}`)
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.json();
            })
            .then(data => this.handleSearchResults(data, resultsCount, resultsContainer, filterStatus))
            .catch(error => this.handleSearchError(error, resultsContainer, filterStatus));
    }
    
    buildSearchParams() {
        const params = new URLSearchParams();
        
        if (this.searchQuery) {
            params.append('search', this.searchQuery);
        }
        
        // Add data source
        if (this.dataSourceName) {
            params.append('data_source', this.dataSourceName);
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
            filterStatus.innerHTML = '<i class="icon-spinner icon-spin"></i> Carregando...';
        }
        if (resultsContainer) {
            resultsContainer.innerHTML = '<div class="text-center p-5"><i class="icon-spinner icon-spin icon-2x"></i></div>';
        }
    }
    
    handleSearchResults(data, resultsCount, resultsContainer, filterStatus) {
        if (resultsCount) {
            resultsCount.innerHTML = data.total_results 
                ? `<p class="text-muted"><strong>${data.total_results}</strong> resultado(s) encontrado(s)</p>`
                : '';
        }
        
        if (resultsContainer) {
            if (data.search_results_html) {
                resultsContainer.innerHTML = data.search_results_html;
            } else {
                resultsContainer.innerHTML = `
                    <div class="alert alert-info" role="alert">
                        <i class="icon-info-sign"></i> 
                        Nenhum resultado encontrado. Tente ajustar sua busca ou filtros.
                    </div>
                `;
            }
        }
        
        if (filterStatus) {
            filterStatus.innerHTML = '<i class="icon-ok text-success"></i> Filtros aplicados';
            setTimeout(() => {
                filterStatus.innerHTML = '';
            }, 2000);
        }
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
    
    updateSearchQueryBadge() {
        const badgeContainer = document.getElementById('search-query-container');
        const badge = document.getElementById('search-query-badge');
        
        if (badgeContainer && badge) {
            if (this.searchQuery && this.searchQuery.trim() !== '') {
                badge.textContent = `Busca: "${this.searchQuery}"`;
                badgeContainer.style.display = '';
            } else {
                badgeContainer.style.display = 'none';
            }
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
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (window.searchPageConfig) {
        new SearchPageManager(window.searchPageConfig);
    }
});