function initIndicatorForm(dataSource, studyUnit) {
  const menuForm = document.getElementById('menu-form');
  if (!menuForm) return;

  const submitButton = document.getElementById('menu-submit');
  const resetButton = document.getElementById('menu-reset');

  // Handler for form submission
  const handleFormSubmit = (event) => {
    event.preventDefault();
    submitButton.disabled = true;

    // Create FormData object from the form
    const formData = new FormData(menuForm);

    // Collect filters from the form data
    const filters = collectFiltersFromForm(formData);

    // Extract breakdown variable
    const breakdownVariable = formData.get('breakdown_variable');

    // Prepare payload for the POST request
    const payload = {
      breakdown_variable: breakdownVariable,
      filters: filters,
      study_unit: studyUnit
    };

    // Send POST request to fetch data
    fetch(`/indicators/data/?data_source=${dataSource}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': formData.get('csrfmiddlewaretoken'),
      },
      body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
      // Standardize series names before rendering
      standardizeIndicatorSeriesNames(data);

      // Update applied filters display
      updateAppliedFiltersDisplay();

      // Render charts or tables based on data source
      renderChartsContainer(data, dataSource, studyUnit, formData.get('csrfmiddlewaretoken'));
    })
    .catch(error => console.error('Error:', error))
    .finally(() => {
      submitButton.disabled = false;
    });
  };

  // Handler for the reset button
  const handleFormReset = () => {
    const fieldsToPreserve = {
      breakdown_variable: menuForm.querySelector('select[name="breakdown_variable"]')?.value,
      country_operator: menuForm.querySelector('select[name="country_operator"]')?.value,
      document_language_operator: menuForm.querySelector('select[name="document_language_operator"]')?.value,
    };

    menuForm.reset();
    $(menuForm).find('select').val(null).trigger('change');

    // Restore preserved fields with Select2
    for (const [name, value] of Object.entries(fieldsToPreserve)) {
        const field = menuForm.querySelector(`select[name="${name}"]`);
        if (field && value !== null && value !== undefined) {
            // Check if the field is a Select2 element
            if ($(field).hasClass('select2-hidden-accessible')) {
                // Use Select2 API to set the value
                $(field).val(value).trigger('change');
              } else {
                // Regular select field
                field.value = value;
            }
        }
    }

    // Reset 'NOT' toggles
    document.querySelectorAll('.toggle-not').forEach(button => {
        button.closest('.input-group').classList.remove('not-active');
        button.setAttribute('aria-pressed', 'false');
    });

    // Clear charts area
    clearAppliedFiltersContainer();

    // Clear graphs area
    clearGraphsContainer();
  };

  // Attach event listeners
  menuForm.addEventListener('submit', handleFormSubmit);
  if (resetButton) {
    resetButton.addEventListener('click', handleFormReset);
  }
}

function renderChartsContainer(data, dataSource, studyUnit, csrfMiddlewareToken) {
  const breakdownVariable = data.breakdown_variable;
  const breakdownLabel = ` per Year${breakdownVariable ? ` by ${breakdownVariable.replace(/_/g, ' ')}` : ''}`;
  const unitSuffix = '';

  if (studyUnit === 'journal') {
    window.Indicators.renderChart({
      chartId: 'periodicals-chart',
      chartDivId: 'periodicals-chart-div',
      data: data,
      seriesType: 'Periodicals',
      title: `Unique Periodicals (sources)${breakdownLabel}`,
    });

    window.Indicators.renderChart({
      chartId: 'docs-chart',
      chartDivId: 'docs-chart-div',
      data: data,
      seriesType: 'Documents per Periodical',
      title: `Avg Documents per Periodical${breakdownLabel}${unitSuffix}`,
    });

    window.Indicators.renderChart({
      chartId: 'citations-chart',
      chartDivId: 'citations-chart-div',
      data: data,
      seriesType: 'Citations per Periodical',
      title: `Avg Citations per Periodical${breakdownLabel}${unitSuffix}`,
    });

    window.Indicators.renderChart({
      chartId: 'citations-per-doc-chart',
      chartDivId: 'citations-per-doc-chart-div',
      data: data,
      seriesType: 'Cited Documents per Periodical',
      title: `Avg Cited Documents per Periodical${breakdownLabel}${unitSuffix}`,
    });

    window.Indicators.renderChart({
      chartId: 'pct-cited-docs-chart',
      chartDivId: 'pct-cited-docs-chart-div',
      data: data,
      seriesType: 'Percent Periodicals With Cited Docs',
      title: `% Periodicals With ≥1 Cited Document${breakdownLabel}${unitSuffix}`,
    });
  } else {
    // Render documents chart
    window.Indicators.renderChart({
      chartId: 'docs-chart',
      chartDivId: 'docs-chart-div',
      data: data,
      seriesType: 'Documents',
      title: `Total Documents${breakdownLabel}${unitSuffix}`,
    });

    // Render citations chart
    window.Indicators.renderChart({
      chartId: 'citations-chart',
      chartDivId: 'citations-chart-div',
      data: data,
      seriesType: 'Citations',
      title: `Total Citations${breakdownLabel}${unitSuffix}`,
    });

    // Render citations per document chart
    window.Indicators.renderChart({
      chartId: 'citations-per-doc-chart',
      chartDivId: 'citations-per-doc-chart-div',
      data: data,
      seriesType: 'Citations per Document',
      title: `Citations per Document${breakdownLabel}${unitSuffix}`,
    });

    // Render cited documents chart
    window.Indicators.renderChart({
      chartId: 'cited-docs-chart',
      chartDivId: 'cited-docs-chart-div',
      data: data,
      seriesType: 'Cited Documents',
      title: `Cited Documents (≥1 citation)${breakdownLabel}${unitSuffix}`,
    });

    // Render % docs with citations chart
    window.Indicators.renderChart({
      chartId: 'pct-cited-docs-chart',
      chartDivId: 'pct-cited-docs-chart-div',
      data: data,
      seriesType: 'Percent Docs With Citations',
      title: `% Documents With ≥1 Citation${breakdownLabel}${unitSuffix}`,
    });
  }
}