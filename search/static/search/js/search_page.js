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
            const response = await fetch(`/search/api/filters/?data_source=${dataSource}`);
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
        $(selectElement).on('change', () => {
            this.updateActiveFilters();
            this.applyFiltersAjax();
        });
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
            if (data.search_results && data.search_results.length > 0) {
                // Renderizar resultados no frontend
                // Use data_source from response or fallback to instance property
                const dataSource = data.data_source || this.dataSourceName;
                resultsContainer.innerHTML = this.renderResults(data.search_results, dataSource);
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
    
    renderResults(results, dataSource) {
        return results.map(doc => this.renderResultItem(doc, dataSource)).join('');
    }
    
    renderResultItem(doc, dataSource) {
        if (dataSource === 'world') {
            return this.renderWorldTemplate(doc);
        } else if (dataSource === 'social_production') {
            return this.renderSocialProductionTemplate(doc);
        } else {
            return this.renderDefaultTemplate(doc);
        }
    }
    
    renderWorldTemplate(doc) {
        const source = doc.source || {};
        const title = source.title || 'Untitled';
        const type = source.type || '';
        const authorships = source.authorships || [];
        const primaryLocation = source.primary_location || {};
        const locationSource = primaryLocation.source || {};
        const biblio = source.biblio || {};
        const locations = source.locations || [];
        const landingPageUrl = locations.length > 0 ? locations[0].landing_page_url : '';
        
        // Build authors list
        let authorsHtml = '';
        if (authorships.length > 0) {
            const authorsText = authorships.map(auth => {
                const author = auth.author || {};
                const displayName = author.display_name || '';
                const orcid = author.orcid || '';
                let authorHtml = this.escapeHtml(displayName);
                if (orcid) {
                    authorHtml += ` <a href="${this.escapeHtml(orcid)}" target="_blank"><img src="/static/images/authorIcon-orcid.png" alt="ORCID" style="height: 16px;"></a>`;
                }
                return authorHtml;
            }).join('; ');
            authorsHtml = `<p class="card-text">${authorsText}</p>`;
        }
        
        // Build publication info
        let publicationInfo = '';
        if (locationSource.display_name) {
            publicationInfo += `
                <p class="card-text">
                    <small class="text-muted">
                        
                        ${locationSource.id ? ` <a href="${this.escapeHtml(locationSource.id)}" target="_blank">${this.escapeHtml(locationSource.display_name)}</a>` : ''}
                    </small>
                </p>
            `;
        }
        
        // Build year/volume/issue info
        let yearVolumeIssue = [];
        if (source.publication_year) yearVolumeIssue.push(this.escapeHtml(source.publication_year));
        if (biblio.volume) yearVolumeIssue.push(`Volume ${this.escapeHtml(biblio.volume)}`);
        if (biblio.issue) yearVolumeIssue.push(`N° ${this.escapeHtml(biblio.issue)}`);
        
        if (yearVolumeIssue.length > 0) {
            publicationInfo += `
                <p class="card-text">
                    <small class="text-muted">${yearVolumeIssue.join(', ')}</small>
                </p>
            `;
        }
        
        // Build DOI link
        let doiHtml = '';
        if (primaryLocation.doi) {
            doiHtml = `
                <p class="card-text mb-0">
                    <small class="text-muted">
                        <a href="https://doi.org/${this.escapeHtml(primaryLocation.doi)}" target="_blank">
                            ${this.escapeHtml(primaryLocation.doi)}
                        </a>
                    </small>
                </p>
            `;
        }
        
        // Build ID link
        let idHtml = '';
        if (doc.id) {
            idHtml = `
                <p class="card-text mb-0">
                    <small class="text-muted">
                        <a href="${this.escapeHtml(doc.id)}" target="_blank">
                            ${this.escapeHtml(doc.id)}
                        </a>
                    </small>
                </p>
            `;
        }
        
        return `
            <div class="card mb-3 result-item">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start gap-2">
                        <h5 class="card-title mb-0" style="flex: 1 1 auto; min-width: 0;">
                            ${landingPageUrl ? 
                                `<a href="${this.escapeHtml(landingPageUrl)}" target="_blank" class="text-decoration-none">${this.escapeHtml(title)}</a>` :
                                `<span>${this.escapeHtml(title)}</span>`
                            }
                        </h5>
                        ${type ? `<span class="badge bg-secondary ms-2 text-muted" style="flex-shrink: 0; white-space: nowrap;">${this.escapeHtml(type)}</span>` : ''}
                    </div>
                    ${authorsHtml}
                    ${publicationInfo}
                    ${doiHtml}
                    ${idHtml}
                </div>
            </div>
        `;
    }
    
    renderSocialProductionTemplate(doc) {
        const source = doc.source || {};
        const title = source.title || 'Untitled';
        const description = source.description || '';
        const link = source.link || '';
        const directoryType = source.directory_type || '';
        const year = source.year || '';
        const institutions = source.institutions || [];
        const cities = source.cities || [];
        const states = source.states || [];
        const practice = source.practice || '';
        const action = source.action || '';
        const classification = source.classification || '';
        const thematicLevel0 = source.thematic_level_0 || [];
        
        return `
            <div class="card mb-3 result-item">
                <div class="card-body">
                    <h5 class="card-title">
                        ${link ? 
                            `<a href="${this.escapeHtml(link)}" target="_blank" class="text-decoration-none">${this.escapeHtml(title)}</a>` :
                            this.escapeHtml(title)
                        }
                    </h5>
                    
                    ${description ? `<p class="card-text">${this.escapeHtml(this.truncateWords(description, 50))}</p>` : ''}
                    
                    ${directoryType ? `
                        <p class="card-text mb-1">
                            <small class="text-muted">
                                <strong>Tipo:</strong> ${this.escapeHtml(directoryType)}
                            </small>
                        </p>
                    ` : ''}
                    
                    ${year ? `
                        <p class="card-text mb-1">
                            <small class="text-muted">
                                <strong>Ano:</strong> ${this.escapeHtml(year)}
                            </small>
                        </p>
                    ` : ''}
                    
                    ${institutions.length > 0 ? `
                        <p class="card-text mb-1">
                            <small class="text-muted">
                                <strong>Instituições:</strong> ${institutions.map(inst => this.escapeHtml(inst)).join(', ')}
                            </small>
                        </p>
                    ` : ''}
                    
                    ${(cities.length > 0 || states.length > 0) ? `
                        <p class="card-text mb-1">
                            <small class="text-muted">
                                <strong>Localização:</strong> 
                                ${cities.map(city => this.escapeHtml(city)).join(', ')}
                                ${cities.length > 0 && states.length > 0 ? ' - ' : ''}
                                ${states.map(state => this.escapeHtml(state)).join(', ')}
                            </small>
                        </p>
                    ` : ''}
                    
                    ${practice ? `
                        <p class="card-text mb-1">
                            <small class="text-muted">
                                <strong>Prática:</strong> ${this.escapeHtml(practice)}
                            </small>
                        </p>
                    ` : ''}
                    
                    ${action ? `
                        <p class="card-text mb-1">
                            <small class="text-muted">
                                <strong>Ação:</strong> ${this.escapeHtml(action)}
                            </small>
                        </p>
                    ` : ''}
                    
                    ${classification ? `
                        <p class="card-text mb-1">
                            <small class="text-muted">
                                <strong>Classificação:</strong> ${this.escapeHtml(classification)}
                            </small>
                        </p>
                    ` : ''}
                    
                    ${thematicLevel0.length > 0 ? `
                        <p class="card-text mb-0">
                            <small class="text-muted">
                                <strong>Áreas Temáticas:</strong> ${thematicLevel0.map(theme => this.escapeHtml(theme)).join(', ')}
                            </small>
                        </p>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    renderDefaultTemplate(doc) {
        const source = doc.source || {};
        const title = source.title || source.name || 'Untitled';
        const description = source.description || '';
        
        return `
            <div class="card mb-3 result-item">
                <div class="card-body">
                    <h5 class="card-title">${this.escapeHtml(title)}</h5>
                    ${description ? `<p class="card-text">${this.escapeHtml(this.truncateWords(description, 50))}</p>` : ''}
                    ${doc.id ? `
                        <p class="card-text mb-0">
                            <small class="text-muted">
                                <strong>ID:</strong> 
                                <a href="${this.escapeHtml(doc.id)}" target="_blank">
                                    ${this.escapeHtml(doc.id)}
                                </a>
                            </small>
                        </p>
                    ` : ''}
                </div>
            </div>
        `;
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }
    
    truncateWords(text, wordCount) {
        if (!text) return '';
        const words = text.split(/\s+/);
        if (words.length <= wordCount) return text;
        return words.slice(0, wordCount).join(' ') + '...';
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