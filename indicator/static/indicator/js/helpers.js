
/**
 * Fetch filters from the server for a given data source
 */
async function fetchFilters(dataSource) {
    const url = `/search-gateway/filters/?data_source=${encodeURIComponent(dataSource)}`;
    const response = await fetch(url);

    if (!response.ok) throw new Error(gettext('GET filters has failed'));

    return await response.json();
}

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

                return { optionValue, optionLabelStz };
            })
            .filter(Boolean)
            .sort((a, b) => a.optionLabelStz.localeCompare(b.optionLabelStz, undefined, { sensitivity: 'base' }));

        // Add sorted options to fragment
        options.forEach(({ optionValue, optionLabelStz }) => {
            const option = document.createElement('option');
            option.value = optionValue;
            option.textContent = optionLabelStz;
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

/**
 * Standardize language code to full language name (with region if applicable)
 */
function standardizeLanguageCode(langCode) {
    if (!langCode) return '';

    var normalized = String(langCode).trim();
    if (!normalized) return '';

    // Extract the language part and any suffix like " (Documents)" or " (Citations)"
    const suffixMatch = normalized.match(/^(.*?)\s+\((Documents|Citations)\)$/i);
    let languageOnly = normalized;
    let suffix = '';

    if (suffixMatch) {
        languageOnly = suffixMatch[1];
        suffix = ` (${suffixMatch[2]})`;
    }

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

/**
 * Update applied filters display area
*/
function updateAppliedFiltersDisplay() {
    const container = document.getElementById('applied-filters');
    const form = document.getElementById('menu-form');
    if (!container || !form) return;

    const formData = new FormData(form);
    const allFilterStrings = [];

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
        const labelText = labels[element.id] || key;

        // Group values of 'multiple' fields
        const existing = filtersToDisplay.find(f => f.label === labelText);
        if (existing) {
            existing.values.push(value);
        } else {
            filtersToDisplay.push({ key: key, label: labelText, values: [value] });
        }
    }

    // Standardize and format filter strings
    filtersToDisplay.forEach(filter => {
        const element = form.querySelector(`[name="${filter.key}"]`);
        const group = element.closest('.input-group');
        const isNot = group && group.querySelector('.toggle-not') && group.classList.contains('not-active');

        const values = filter.values.map(val => {
            const standardizedVal = standardizeFieldValue(filter.label, val);
            if (isNot) {
                return `<span class="badge badge-oca-light bg-danger text-white">NOT</span> ${standardizedVal}`;
            }
            return standardizedVal;
        }).join(', ');

        allFilterStrings.push(`<span class="fw-bold">${filter.label}:</span> ${values}`);
    });

    // Handle publication year range separately
    const startVal = formData.get('document_publication_year_start');
    const endVal = formData.get('document_publication_year_end');
    const rangeLabel = formatYearRange(startVal, endVal);
    if (rangeLabel) {
        allFilterStrings.push(`<span class="fw-bold">${gettext('Publication Year')}:</span> ${rangeLabel}`);
    }
    // Handle country and language query operators
    const countryOp = formData.get('country_operator');
    const languageOp = formData.get('document_language_operator');
    const queryOperators = [];

    const countryFilter = filtersToDisplay.find(f => f.key === 'country');
    if (countryOp && countryFilter && countryFilter.values.length > 1) {
        queryOperators.push(`<span><span class="fw-bold">${gettext('Country')}:</span> <span class="badge badge-oca-light bg-secondary">${countryOp.toUpperCase()}</span></span>`);
    }

    const languageFilter = filtersToDisplay.find(f => f.key === 'document_language');
    if (languageOp && languageFilter && languageFilter.values.length > 1) {
        queryOperators.push(`<span><span class="fw-bold">${gettext('Document Language')}:</span> <span class="badge badge-oca-light bg-secondary">${languageOp.toUpperCase()}</span></span>`);
    }

    // Build the final HTML string
    let finalHtml = `<strong class="text-primary">${gettext('Applied Filters')}</strong><div>${allFilterStrings.join('<span class="badge badge-oca-light bg-secondary mx-2">AND</span>')}</div>`;
    if (queryOperators.length > 0) {
        finalHtml += `<strong class="mt-1 text-primary">${gettext('Search Options')}</strong><div>${queryOperators.join(' ')}</div>`;
    }

    // Join and display all filter strings
    if (allFilterStrings.length) {
        container.innerHTML = finalHtml;
        container.classList.remove('d-none');
    } else {
        container.classList.add('d-none');
        container.innerHTML = '';
    }
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
            s.name = standardizeFieldValue(indicators.breakdown_variable, s.name);
        });
    }
}