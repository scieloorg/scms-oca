function initializeIndicatorMenu(dataSource) {
  const menuForm = document.getElementById('menu-form');
  if (!menuForm) return;

  const submitButton = document.getElementById('menu-submit');
  const resetButton = document.getElementById('menu-reset');

  // Handler for form submission
  const handleFormSubmit = (event) => {
    event.preventDefault();
    submitButton.disabled = true;

    const formData = new FormData(menuForm);
    const filters = {};

    // Collect filters from the form data
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

    const studyUnit = formData.get('study_unit');
    const breakdownVariable = formData.get('breakdown_variable');

    // Prepare payload for the POST request
    const payload = {
      study_unit: studyUnit,
      breakdown_variable: breakdownVariable,
      filters: filters
    };

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

      // Render main chart
      window.Indicators.renderMainChart(data, studyUnit);

      // Render inner percentage chart
      window.Indicators.renderInnerPercentageChart(data, studyUnit);

      // Render outer percentage chart
      window.Indicators.renderOuterPercentageChart(data, studyUnit, dataSource, formData.get('csrfmiddlewaretoken'));
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

    for (const [name, value] of Object.entries(fieldsToPreserve)) {
        const field = menuForm.querySelector(`select[name="${name}"]`);
        if (field && value !== null) {
            field.value = value;
        }
    }

    // Clear charts area
    clearAppliedFiltersContainer();

    // Clear graphs area
    clearGraphsContainer();
  };

  menuForm.addEventListener('submit', handleFormSubmit);
  if (resetButton) {
    resetButton.addEventListener('click', handleFormReset);
  }
}