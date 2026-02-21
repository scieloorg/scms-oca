
/**
 * Fetch filters from the server for a given data source
 */
async function fetchFilters(dataSource, extraParams = {}) {
    let url = `/search-gateway/filters/?data_source=${encodeURIComponent(dataSource)}`;
    if (extraParams && typeof extraParams === 'object') {
        const query = new URLSearchParams();

        Object.entries(extraParams).forEach(([key, value]) => {
            if (value === null || value === undefined || value === '') return;
            if (Array.isArray(value)) {
                value.forEach(item => {
                    if (item === null || item === undefined || item === '') return;
                    query.append(key, String(item));
                });
                return;
            }
            query.set(key, String(value));
        });

        const queryString = query.toString();
        if (queryString) {
            url += `&${queryString}`;
        }
    }
    const response = await fetch(url);

    if (!response.ok) throw new Error(gettext('GET filters has failed'));

    return await response.json();
}

/**
 * Enable open/close behavior for filter group cards.
 * Cards must use `.filter-group-card--collapsible` and include
 * a direct child `.filter-group-card__title`.
 */
function initCollapsibleFilterGroups() {
    const cards = document.querySelectorAll('.filter-group-card--collapsible');

    cards.forEach((card, index) => {
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

document.addEventListener('DOMContentLoaded', () => {
    initCollapsibleFilterGroups();
});

/**
 * Populate select filter elements with options from fetched data
 */
async function populateSelectFilters(data, exclude=[]) {
    for (const [key, value] of Object.entries(data)) {
        const select = document.getElementById(key);
        if (!select || exclude.includes(key)) continue;

        const fragment = document.createDocumentFragment();

        // Prepare and sort options
        const options = (value || [])
            .map(item => {
                // Backend commonly returns buckets as { key, label }.
                // Older/other endpoints may return { value, label } or plain strings.
                const rawValue = item?.value ?? item?.key ?? item?.id ?? item ?? '';
                if (rawValue === null || rawValue === undefined || rawValue === '') return null;

                const optionValue = String(rawValue);
                const optionLabel = item?.label ?? item?.text ?? optionValue;
                const optionLabelStz = standardizeFieldValue(key, optionLabel);
                const optionDocCount = Number(item?.doc_count);

                return {
                    optionValue,
                    optionLabelStz,
                    optionDocCount: Number.isFinite(optionDocCount) ? optionDocCount : null,
                };
            })
            .filter(Boolean)
            .sort((a, b) => a.optionLabelStz.localeCompare(b.optionLabelStz, undefined, { sensitivity: 'base' }));

        // Add sorted options to fragment
        options.forEach(({ optionValue, optionLabelStz, optionDocCount }) => {
            const option = document.createElement('option');
            option.value = optionValue;
            option.textContent = optionDocCount === null
                ? optionLabelStz
                : `${optionLabelStz} (${optionDocCount.toLocaleString()})`;
            fragment.appendChild(option);
        });

        select.appendChild(fragment);
    }
}

/**
 * Collect filters from FormData into an object.
 */
function collectFiltersFromForm(formData) {
  const filters = {};

  for (const [key, value] of formData.entries()) {
    if (Object.prototype.hasOwnProperty.call(filters, key)) {
      if (!Array.isArray(filters[key])) {
        filters[key] = [filters[key]];
      }
      filters[key].push(value);
    } else {
      filters[key] = value;
    }
  }

  // Handle 'NOT' toggles
  document.querySelectorAll('.toggle-not').forEach(button => {
    const group = button.closest('.input-group');
    if (group.classList.contains('not-active')) {
      const select = group.querySelector('select');
      if (select && select.name) {
        filters[`${select.name}_bool_not`] = 'true';
      }
    }
  });

  return filters;
}

// Intl.DisplayNames to standardize country and language codes
var hasIntlDisplay = typeof Intl !== 'undefined' && typeof Intl.DisplayNames === 'function';
var countryDisplay = hasIntlDisplay ? new Intl.DisplayNames(['en'], { type: 'region' }) : null;
var languageDisplay = hasIntlDisplay ? new Intl.DisplayNames(['en'], { type: 'language' }) : null;

function safeDisplayName(display, code) {
    if (!display || !code) return null;
    try {
        return display.of(code);
    } catch (e) {
        return null;
    }
}

/**
 * Standardize country code to full country name
 */
function standardizeCountryCode(countryCode) {
    if (!countryCode) return '';

    // If code is longer than 3 characters, return as-is
    if (countryCode.length > 3) {
        return String(countryCode).trim();
    }

    var normalized = String(countryCode).toUpperCase();
    // Intl.DisplayNames.of throws for invalid region codes.
    var label = safeDisplayName(countryDisplay, normalized);

    return label || normalized;
}

const BREAKDOWN_METRIC_SUFFIXES = new Set([
    'Documents',
    'Citations',
    'Citations per Document',
    'Cited Documents',
    'Percent Docs With Citations',
    'Periodicals',
    'Documents per Periodical',
    'Citations per Periodical',
    'Cited Documents per Periodical',
    'Percent Periodicals With Cited Docs',
]);

function splitMetricSuffix(value) {
    const normalized = String(value ?? '').trim();
    if (!normalized) return { base: '', suffix: '' };

    const match = normalized.match(/^(.*?)\s+\(([^()]+)\)$/);
    if (!match) return { base: normalized, suffix: '' };

    const metricLabel = String(match[2] || '').trim();
    if (!BREAKDOWN_METRIC_SUFFIXES.has(metricLabel)) {
        return { base: normalized, suffix: '' };
    }

    return {
        base: String(match[1] || '').trim(),
        suffix: ` (${metricLabel})`,
    };
}

function splitDocCitSuffix(value) {
    // Backward compatibility: old helper name used by collection standardization.
    return splitMetricSuffix(value);
}

/**
 * Standardize language code to full language name (with region if applicable)
 */
function standardizeLanguageCode(langCode) {
    if (!langCode) return '';

    const { base, suffix } = splitMetricSuffix(langCode);
    let languageOnly = base || String(langCode).trim();
    if (!languageOnly) return '';

    // Some backends send already-localized names (e.g. "Portuguese") or other
    // values that are not valid language tags; in that case, keep as-is.
    languageOnly = String(languageOnly).trim();
    // Keep only the first token to avoid values like "en;fr" or "pt, en".
    languageOnly = languageOnly.split(/[\s,;]+/)[0];
    var bcp47 = languageOnly.replace(/_/g, '-');
    var looksLikeLangTag = /^[A-Za-z]{2,3}([\-][A-Za-z]{2,4})*$/.test(bcp47);
    if (!looksLikeLangTag) {
        return languageOnly + suffix;
    }

    var parts = bcp47.split('-');
    var languagePart = parts[0].toLowerCase();
    var regionPart = parts.length > 1 ? parts[1].toUpperCase() : null;

    // Intl.DisplayNames.of throws for invalid language codes.
    var label = safeDisplayName(languageDisplay, languagePart);
    if (!label) label = languagePart.toUpperCase();
    else label = label.charAt(0).toUpperCase() + label.slice(1);

    if (regionPart) {
      var regionLabel = standardizeCountryCode(regionPart);
      label += ' (' + (regionLabel || regionPart) + ')';
    }

    return label + suffix; // Re-append the original suffix
}

/**
 * Standardize collection code to collection name.
 */
function standardizeCollectionToName(collectionCode) {
    const { base, suffix } = splitDocCitSuffix(collectionCode);
    const collectionMap = {
        'arg': gettext('Argentina'),
        'bol': gettext('Bolivia'),
        'chl': gettext('Chile'),
        'cic': gettext('Science and Culture'),
        'col': gettext('Colombia'),
        'cri': gettext('Costa Rica'),
        'cub': gettext('Cuba'),
        'dom': gettext('Dominican Republic'),
        'ecu': gettext('Ecuador'),
        'esp': gettext('Spain'),
        'mex': gettext('Mexico'),
        'per': gettext('Peru'),
        'prt': gettext('Portugal'),
        'pry': gettext('Paraguay'),
        'psi': gettext('PEPSIC'),
        'rve': gettext('REVENF'),
        'scl': gettext('Brazil'),
        'spa': gettext('Public Health'),
        'sza': gettext('South Africa'),
        'ury': gettext('Uruguay'),
        'ven': gettext('Venezuela'),
        'wid': gettext('West Indies'),
    };

    return (collectionMap[base] || base) + suffix;
}

/**
 * Standardize Open Access values (0 to No, 1 to Yes).
 */
function standardizeOpenAccessValue(value) {
    if (value === '0') return gettext('No');
    if (value === '1') return gettext('Yes');
    return value;
}

/**
 * Standardize field value based on field type
 */
function standardizeFieldValue(field, value) {
    // Standardize labels based on field type
    if (field === 'document_language' || field === 'Document Language') {
        return standardizeLanguageCode(value);
    }

    if (field === 'country' || field === 'Country') {
        return standardizeCountryCode(value);
    }

    if (field === 'collection' || field === 'Collection') {
        return standardizeCollectionToName(value);
    }

    if (field === 'open_access' || field === 'Open Access') {
        return standardizeOpenAccessValue(value);
    }

    return value;
}

/**
 * Clear applied filters display area
 */
function clearAppliedFiltersContainer() {
    const container = document.getElementById('applied-filters');
    if (container) {
        container.classList.add('d-none');
        container.innerHTML = '';
    }
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/**
 * Update applied filters display area
*/
function updateAppliedFiltersDisplay() {
    const container = document.getElementById('applied-filters');
    const form = document.getElementById('menu-form');
    if (!container || !form) return;

    const formData = new FormData(form);
    const filterChips = [];

    // Map field IDs to labels
    const labels = {};
    form.querySelectorAll('label[for]').forEach(label => {
        labels[label.htmlFor] = label.textContent.trim();
    });

    const filtersToDisplay = [];

    // Iterate over form data entries
    for (const [key, value] of formData.entries()) {
        // Ignore fields that shouldn't be displayed or are empty or will be handled separately
        if (!value || [
            'breakdown_variable',
            'country_operator',
            'csrfmiddlewaretoken',
            'document_publication_year_end',
            'document_publication_year_start',
            'document_language_operator',
            'ranking_metric',
        ].includes(key)) {
            continue;
        }

        const element = form.querySelector(`[name="${key}"]`);
        const labelText = element ? (labels[element.id] || key) : key;

        // Group values of 'multiple' fields
        const existing = filtersToDisplay.find(f => f.label === labelText);
        if (existing) {
            existing.values.push(value);
        } else {
            filtersToDisplay.push({ key: key, label: labelText, values: [value] });
        }
    }

    // Standardize and format chips
    filtersToDisplay.forEach(filter => {
        const element = form.querySelector(`[name="${filter.key}"]`);
        const group = element ? element.closest('.input-group') : null;
        const isNot = group && group.querySelector('.toggle-not') && group.classList.contains('not-active');

        const valuesHtml = filter.values.map(val => {
            const standardizedVal = standardizeFieldValue(filter.key, val);
            const safeValue = escapeHtml(standardizedVal);
            return `<span>${safeValue}</span>`;
        }).join('<span>, </span>');
        const notPrefixHtml = isNot
            ? `<span class="applied-filter-chip__not">NOT</span>`
            : '';

        filterChips.push(
            `<span class="applied-filter-chip">` +
                `<span class="applied-filter-chip__label">${escapeHtml(filter.label)}</span>` +
                `<span>:</span>` +
                `<span class="applied-filter-chip__value">${notPrefixHtml}${valuesHtml}</span>` +
            `</span>`
        );
    });

    // Handle publication year range separately
    const startVal = formData.get('document_publication_year_start');
    const endVal = formData.get('document_publication_year_end');
    const rangeLabel = formatYearRange(startVal, endVal);
    if (rangeLabel) {
        filterChips.push(
            `<span class="applied-filter-chip">` +
                `<span class="applied-filter-chip__label">${escapeHtml(gettext('Publication Year'))}</span>` +
                `<span>:</span>` +
                `<span class="applied-filter-chip__value">${escapeHtml(rangeLabel)}</span>` +
            `</span>`
        );
    }

    // Handle country and language query operators
    const countryOp = formData.get('country_operator');
    const languageOp = formData.get('document_language_operator');
    const queryOperators = [];

    const countryFilter = filtersToDisplay.find(f => f.key === 'country');
    if (countryOp && countryFilter && countryFilter.values.length > 1) {
        queryOperators.push({
            label: gettext('Country'),
            value: countryOp.toUpperCase(),
        });
    }

    const languageFilter = filtersToDisplay.find(f => f.key === 'document_language');
    if (languageOp && languageFilter && languageFilter.values.length > 1) {
        queryOperators.push({
            label: gettext('Document Language'),
            value: languageOp.toUpperCase(),
        });
    }

    if (!filterChips.length) {
        container.classList.add('d-none');
        container.innerHTML = '';
        return;
    }

    let queryOperatorsHtml = '';
    if (queryOperators.length > 0) {
        queryOperatorsHtml =
            `<div class="applied-filters-operators">` +
                `<div class="applied-filters-operators__title">${escapeHtml(gettext('Search Options'))}</div>` +
                `<div class="applied-filters-operators__list">` +
                    queryOperators.map(op =>
                        `<span class="applied-filter-operator-chip">` +
                            `<span class="applied-filter-operator-chip__label">${escapeHtml(op.label)}</span>` +
                            `<span class="applied-filter-operator-chip__value">${escapeHtml(op.value)}</span>` +
                        `</span>`
                    ).join('') +
                `</div>` +
            `</div>`;
    }

    container.innerHTML =
        `<div class="applied-filters-head">` +
            `<span class="applied-filters-title">${escapeHtml(gettext('Applied Filters'))}</span>` +
            `<span class="applied-filters-count">${filterChips.length}</span>` +
        `</div>` +
        `<div class="applied-filters-grid">${filterChips.join('')}</div>` +
        queryOperatorsHtml;

    container.classList.remove('d-none');
}

/**
 * Return an inclusive list of years between startYear and endYear.
 * Accepts numbers or numeric strings. Returns an empty array for invalid input.
 */
function generateYearList(startYear, endYear) {
    const s = Number.parseInt(startYear, 10);
    const e = Number.parseInt(endYear, 10);
    if (Number.isNaN(s) || Number.isNaN(e)) return [];

    const start = Math.min(s, e);
    const end = Math.max(s, e);
    const years = [];

    for (let y = start; y <= end; y++) years.push(y);

    return years;
}

/**
 * Format a start/end year into a human-readable range string.
 * Uses generateYearList to validate and normalize inputs.
 * Examples:
 *   formatYearRange(2010, 2015) => "2010 to 2015"
 *   formatYearRange("2020", 2020) => "2020"
 *   formatYearRange(null, 2020) => ""
 */
function formatYearRange(startYear, endYear) {
    const years = generateYearList(startYear, endYear);

    if (!years.length) return '';

    if (years.length === 1) return String(years[0]);

    return `${years[0]} ${gettext('to')} ${years[years.length - 1]}`;
}

/**
 * Convert a string to title case.
 */
function toTitleCase(text) {
    if (text) {
        return text.toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
    }
    return ""
}

/**
 * Standardize series names in indicator data for breakdown charts.
 * @param {object} indicators - The indicator data object from the API.
 */
function standardizeIndicatorSeriesNames(indicators) {
    if (indicators.breakdown_variable && indicators.series) {
        indicators.series.forEach(s => {
            const { base, suffix } = splitMetricSuffix(s.name);
            const standardizedBase = standardizeFieldValue(indicators.breakdown_variable, base);
            s.name = `${standardizedBase}${suffix}`;
        });
    }
}
