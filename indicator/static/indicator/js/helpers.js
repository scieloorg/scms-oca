/**
 * Fetch filters from the server for a given data source
 */
async function fetchFilters(dataSource) {
    const url = `/indicators/filters/?data_source=${encodeURIComponent(dataSource)}`;
    const response = await fetch(url);

    if (!response.ok) throw new Error('GET filters has failed');

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
                const optionValue = item?.value ?? item ?? '';
                if (!optionValue) return null;

                const optionLabel = item?.label ?? optionValue;
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

  return filters;
}

// Intl.DisplayNames to standardize country and language codes
var hasIntlDisplay = typeof Intl !== 'undefined' && typeof Intl.DisplayNames === 'function';
var countryDisplay = hasIntlDisplay ? new Intl.DisplayNames(['en'], { type: 'region' }) : null;
var languageDisplay = hasIntlDisplay ? new Intl.DisplayNames(['en'], { type: 'language' }) : null;

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
    var label = countryDisplay ? countryDisplay.of(normalized) : null;

    return label || normalized;
}

/**
 * Standardize language code to full language name (with region if applicable)
 */
function standardizeLanguageCode(langCode) {
    if (!langCode) return '';

    var normalized = String(langCode).trim();
    if (!normalized) return '';

    var bcp47 = normalized.replace(/_/g, '-');
    var parts = bcp47.split('-');
    var languagePart = parts[0].toLowerCase();
    var regionPart = parts.length > 1 ? parts[1].toUpperCase() : null;

    var label = languageDisplay ? languageDisplay.of(languagePart) : null;
    if (!label) label = languagePart.toUpperCase();
    else label = label.charAt(0).toUpperCase() + label.slice(1);

    if (regionPart) {
      var regionLabel = standardizeCountryCode(regionPart);
      label += ' (' + (regionLabel || regionPart) + ')';
    }

    return label;
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
            'study_unit',
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
            filtersToDisplay.push({ label: labelText, values: [value] });
        }
    }

    // Standardize and format filter strings
    filtersToDisplay.forEach(filter => {
        const values = filter.values.map(val => standardizeFieldValue(filter.label, val)).join(', ');
        allFilterStrings.push(`${filter.label}: ${values}`);
    });

    // Handle publication year range separately
    const startVal = formData.get('document_publication_year_start');
    const endVal = formData.get('document_publication_year_end');
    const rangeLabel = formatYearRange(startVal, endVal);
    if (rangeLabel) {
        allFilterStrings.push(`Publication Year: ${rangeLabel}`);
    }

    // Handle country and language query operators
    const countryOp = formData.get('country_operator');
    const languageOp = formData.get('document_language_operator');
    const queryOperators = [];

    const countryFilter = filtersToDisplay.find(f => f.label === 'Country');
    if (countryOp && countryFilter && countryFilter.values.length > 1) {
        queryOperators.push(`<span>Country: <span class="badge">${countryOp.toUpperCase()}</span></span>`);
    }

    const languageFilter = filtersToDisplay.find(f => f.label === 'Document Language');
    if (languageOp && languageFilter && languageFilter.values.length > 1) {
        queryOperators.push(`<span>Document Language: <span class="badge">${languageOp.toUpperCase()}</span></span>`);
    }

    // Build the final HTML string
    let finalHtml = `<strong class="text-primary">Applied Filters</strong><span>${allFilterStrings.join('<span class="badge mx-2">AND</span>')}</span>`;
    if (queryOperators.length > 0) {
        finalHtml += `<strong class="mt-1 text-primary">Search Options</strong>${queryOperators.join(' ')}`;
    }

    // Include study unit if specified
    const studyUnit = formData.get('study_unit');
    if (studyUnit) {
        finalHtml += `<strong class="mt-1 text-primary">Study Unit</strong>${toTitleCase(studyUnit)}`;
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
    
    return `${years[0]} to ${years[years.length - 1]}`;
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

/**
 * Standardize collection code to collection name.
 */
function standardizeCollectionToName(collectionCode) {
    const collectionMap = {
        'arg': 'Argentina',
        'bol': 'Bolivia',
        'chl': 'Chile',
        'cic': 'Science and Culture',
        'col': 'Colombia',
        'cri': 'Costa Rica',
        'cub': 'Cuba',
        'ecu': 'Ecuador',
        'esp': 'Spain',
        'mex': 'Mexico',
        'per': 'Peru',
        'prt': 'Portugal',
        'pry': 'Paraguay',
        'psi': 'PEPSIC',
        'rve': 'REVENF',
        'scl': 'Brazil',
        'spa': 'Public Health',
        'sza': 'South Africa',
        'ury': 'Uruguay',
        'ven': 'Venezuela',
        'wid': 'West Indies',
    };

    return collectionMap[collectionCode] || collectionCode;
}