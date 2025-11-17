function initIndicatorForm(dataSource) {
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

    // Extract study unit
    const studyUnit = formData.get('study_unit');

    // Extract breakdown variable
    const breakdownVariable = formData.get('breakdown_variable');

    // Prepare payload for the POST request
    const payload = {
      study_unit: studyUnit,
      breakdown_variable: breakdownVariable,
      filters: filters
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
      renderChartsContainer(data, studyUnit, dataSource, formData.get('csrfmiddlewaretoken'));
    })
    .catch(error => console.error('Error:', error))
    .finally(() => {
      submitButton.disabled = false;
    });
  };

  // Handler for the reset button
  const handleFormReset = () => {
    const fieldsToPreserve = {
      study_unit: menuForm.querySelector('select[name="study_unit"]')?.value,
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

// Render charts
function renderChartsContainer(data, studyUnit, dataSource, csrfMiddlewareToken) {
  // Render main chart
  window.Indicators.renderMainChart(data, studyUnit);

  // Render inner percentage chart
  window.Indicators.renderInnerPercentageChart(data, studyUnit);

  // Render outer percentage chart
  window.Indicators.renderOuterPercentageChart(data, studyUnit, dataSource, csrfMiddlewareToken);
}
