// Namespace to avoid polluting the global scope
const Indicators = {};

// Builds a tooltip configuration
function buildTooltip(overrides) {
    return { 
        confine: true,
        enterable: true,
        extraCssText: 'max-height:50vh; overflow-y:auto;',
        ...overrides 
    };
}

// Builds a grid configuration
function buildGrid(overrides) {
    return {
        top: 110,
        left: 0,
        right: 200,
        bottom: 40,
        containLabel: true,
        ...overrides 
    };
}

// Builds the chart toolbox
function buildToolbox(magicTypes) {
  return {
    orient: 'vertical',
    feature: {
      magicType: { type: magicTypes || ['line', 'bar', 'tiled'] },
      dataView: { show: true, title: 'Data', readOnly: true, lang: ['', 'Close'] },
      saveAsImage: { show: true },
      restore: { show: true },
      dataZoom: {}
    }
  };
}

// Builds the chart legend
function buildLegend(keys) {
    if (!Array.isArray(keys) || !keys.length) return null;

    return {
        type: 'scroll',
        data: keys,
        orient: 'horizontal',
        bottom: 0
    };
}

// Ensures old chart instances are destroyed
function destroyChartInstance(container) {
    if (container && container._chartInstance) {
        container._chartInstance.dispose();
        container._chartInstance = null;
    }
}

// Clears the charts container and destroys chart instances
function clearGraphsContainer() {
    const mainChartDiv = document.getElementById('main-chart-div');
    const innerPercentageChartDiv = document.getElementById('inner-percentage-chart-div');
    const outerPercentageChartDiv = document.getElementById('outer-percentage-chart-div');

    if (mainChartDiv) mainChartDiv.classList.add('d-none');
    if (innerPercentageChartDiv) innerPercentageChartDiv.classList.add('d-none');
    if (outerPercentageChartDiv) outerPercentageChartDiv.classList.add('d-none');

    const chartInstances = [
        mainChartDiv._chartInstance,
        innerPercentageChartDiv._chartInstance,
        outerPercentageChartDiv._chartInstance
    ];

    chartInstances.forEach(chartInstance => {
        if (chartInstance) {
            destroyChartInstance(chartInstance.getDom());
        }
    });
}

// Initializes a new chart instance
function initChartInstance(container) {
    if (!container) return null;

    // Ensures the previous instance is cleaned up
    destroyChartInstance(container);

    const chart = echarts.init(container);
    container._chartInstance = chart;

    return chart;
}

/**
 * Render the main chart based on the provided data and study unit
 * @param {object} data - The indicator data received from the API.
 * @param {string} studyUnit - The study unit ('journal', 'document', 'citation').
 */
Indicators.renderMainChart = function(data, studyUnit) {
    const chartContainer = document.getElementById('main-chart');
    if (!chartContainer) return;

    const chartContainerParent = document.getElementById('main-chart-div');
    if (!chartContainerParent) return;

    // Remove hidden class to display the chart container
    chartContainerParent.classList.remove('d-none');

    const chartObj = initChartInstance(chartContainer);
    const studyUnitSubtitle = `Study Unit: ${studyUnit.charAt(0).toUpperCase() + studyUnit.slice(1)}`;

    let chartOpts;

    if (data.breakdown_variable && data.series && data.years) {
        const breakdownLabelElement = document.querySelector(`label[for="${data.breakdown_variable}"]`);
        const breakdownLabel = breakdownLabelElement ? breakdownLabelElement.textContent.trim() : data.breakdown_variable.replace(/_/g, ' ');
        const title = `Breakdown by ${breakdownLabel}`;

        const seriesTotals = (data.series || []).map(series => ({
            name: series.name,
            total: (series.data || []).reduce((sum, value) => sum + value, 0),
            data: series.data
        })).sort((a, b) => b.total - a.total);

        const orderedKeys = seriesTotals.map(series => series.name);
        const orderedSeries = seriesTotals.map(series => ({
            name: series.name,
            type: 'bar',
            stack: 'total',
            data: series.data
        }));

        chartOpts = {
            title: { text: title, subtext: studyUnitSubtitle },
            tooltip: buildTooltip({ trigger: 'axis', axisPointer: { type: 'shadow' } }),
            grid: buildGrid(),
            toolbox: buildToolbox(['line', 'bar', 'tiled']),
            xAxis: { type: 'category', data: data.years },
            yAxis: { type: 'value' },
            series: orderedSeries,
            legend: buildLegend(orderedKeys)
        };

    } else {
        const isCitation = studyUnit === 'citation';
        const title = `Number of ${isCitation ? 'Citations' : 'Documents'} per Year`;
        const seriesName = isCitation ? 'Citations' : 'Documents';
        const seriesData = isCitation ? data.total_citations_per_year : data.ndocs_per_year;

        chartOpts = {
            title: { text: title, subtext: studyUnitSubtitle },
            tooltip: buildTooltip(),
            grid: buildGrid({ bottom: '10%' }),
            toolbox: buildToolbox(['line', 'bar']),
            xAxis: { type: 'category', data: data.years || [] },
            yAxis: { type: 'value' },
            series: [{ name: seriesName, type: 'bar', data: seriesData || [] }]
        };
    }
    chartObj.setOption(chartOpts, true);
}

/**
 * Render the inner percentage chart (% within filtered data).
 * @param {object} data - The indicator data received from the API.
 * @param {string} studyUnit - The study unit.
 */
Indicators.renderInnerPercentageChart = function(data, studyUnit) {
    const chartContainer = document.getElementById('inner-percentage-chart');
    if (!chartContainer) return;

    // If there is no breakdown variable, there is nothing to show.
    if (!data.breakdown_variable || !data.series || !data.series.length) {
        destroyChartInstance(chartContainer);
        return;
    }

    const chartContainerParent = document.getElementById('inner-percentage-chart-div');
    if (!chartContainerParent) return;

    // Remove hidden class to display the chart container
    chartContainerParent.classList.remove('d-none');

    const chartObj = initChartInstance(chartContainer);
    const studyUnitSubtitle = `Study Unit: ${studyUnit.charAt(0).toUpperCase() + studyUnit.slice(1)}`;
    const breakdownLabelElement = document.querySelector(`label[for="${data.breakdown_variable}"]`);
    const breakdownLabel = breakdownLabelElement ? breakdownLabelElement.textContent.trim() : data.breakdown_variable.replace(/_/g, ' ');
    const title = `Breakdown by ${breakdownLabel} (% within filtered data)`;

    const years = data.years || [];
    const series = data.series || [];

    // Calculate the total for each year
    const yearlyTotals = years.map((_, yearIndex) =>
        series.reduce((total, s) => total + (s.data[yearIndex] || 0), 0)
    );

    // Calculate the percentage data
    const percentSeries = series.map(s => ({
        name: s.name,
        type: 'bar',
        stack: 'total',
        emphasis: { focus: 'series' },
        data: s.data.map((value, yearIndex) => {
            const total = yearlyTotals[yearIndex];
            return total > 0 ? ((value / total) * 100).toFixed(2) : 0;
        })
    }));

    const chartOpts = {
        title: { text: title, subtext: studyUnitSubtitle },
        tooltip: buildTooltip({
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: (params) => {
                let tooltip = `${params[0].axisValueLabel}<br/>`;
                params.forEach(param => {
                    tooltip += `${param.marker} ${param.seriesName}: ${param.value}%<br/>`;
                });
                return tooltip;
            }
        }),
        grid: buildGrid(),
        toolbox: buildToolbox(['bar', 'tiled']),
        xAxis: { type: 'category', data: years },
        yAxis: { type: 'value', axisLabel: { formatter: '{value} %' } },
        series: percentSeries,
        legend: buildLegend(series.map(s => s.name))
    };

    chartObj.setOption(chartOpts, true);
};

/**
 * Render the outer percentage chart (comparison with unfiltered data).
 * @param {object} data - The indicator data received from the API.
 * @param {string} studyUnit - The study unit.
 * @param {string} dataSource - The data source (e.g., 'world').
 */
Indicators.renderOuterPercentageChart = function(data, studyUnit, dataSource, csrfToken) {
    const chartContainer = document.getElementById('outer-percentage-chart');
    if (!chartContainer) return;

    // If there is no breakdown variable, there is nothing to show.
    if (!data.breakdown_variable || !data.series || !data.series.length) {
        destroyChartInstance(chartContainer);
        return;
    }

    const chartContainerParent = document.getElementById('outer-percentage-chart-div');
    if (!chartContainerParent) return;

    // Remove hidden class to display the chart container
    chartContainerParent.classList.remove('d-none');

    const baselinePayload = {
        study_unit: studyUnit,
        breakdown_variable: data.breakdown_variable,
        filters: {
            study_unit: studyUnit,
            breakdown_variable: data.breakdown_variable
        }
    };

    // Fetch the baseline data (without filters) for comparison
    fetch(`/indicators/data/?data_source=${dataSource}`, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify(baselinePayload)
    })
    .then(response => response.json())
    .then(baselineData => {
        const chartObj = initChartInstance(chartContainer);
        const studyUnitSubtitle = `Study Unit: ${studyUnit.charAt(0).toUpperCase() + studyUnit.slice(1)}`;
        const breakdownLabelElement = document.querySelector(`label[for="${data.breakdown_variable}"]`);
        const breakdownLabel = breakdownLabelElement ? breakdownLabelElement.textContent.trim() : data.breakdown_variable.replace(/_/g, ' ');
        const title = `Breakdown by ${breakdownLabel} (% relative to unfiltered data)`;

        const filteredYears = data.years || [];
        const filteredSeries = data.series || [];
        
        // Create a map for baseline data for quick lookup
        const baselineMap = {};
        (baselineData.series || []).forEach(s => {
            baselineMap[s.name] = {};
            (baselineData.years || []).forEach((year, i) => {
                baselineMap[s.name][year] = s.data[i];
            });
        });

        const percentSeries = filteredSeries.map(s => ({
            name: s.name,
            type: 'bar',
            emphasis: { focus: 'series' },
            data: s.data.map((value, i) => {
                const year = filteredYears[i];
                const baselineValue = baselineMap[s.name] ? baselineMap[s.name][year] : 0;
                return baselineValue > 0 ? ((value / baselineValue) * 100).toFixed(2) : 0;
            })
        }));

        const chartOpts = {
            title: { text: title, subtext: studyUnitSubtitle },
            tooltip: buildTooltip({
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
                formatter: (params) => {
                    let tooltip = `${params[0].axisValueLabel}<br/>`;
                    params.forEach(param => {
                        tooltip += `${param.marker} ${param.seriesName}: ${param.value}%<br/>`;
                    });
                    return tooltip;
                }
            }),
            grid: buildGrid(),
            toolbox: buildToolbox(['bar', 'tiled']),
            xAxis: { type: 'category', data: filteredYears },
            yAxis: { type: 'value', axisLabel: { formatter: '{value} %' } },
            series: percentSeries,
            legend: buildLegend(filteredSeries.map(s => s.name))
        };

        chartObj.setOption(chartOpts, true);
    })
    .catch(error => {
        console.error('Error fetching baseline data for outer percentage chart:', error);
        destroyChartInstance(chartContainer);
    });
};

// Clears all chart instances
Indicators.clearCharts = function() {
    destroyChartInstance(document.getElementById('main-chart'));
    destroyChartInstance(document.getElementById('inner-percentage-chart'));
    destroyChartInstance(document.getElementById('outer-percentage-chart'));
}

// Handle window resize to adjust charts
window.addEventListener('resize', () => {
    ['main-chart', 'inner-percentage-chart', 'outer-percentage-chart'].forEach(id => {
        const el = document.getElementById(id);
        if (el && el._chartInstance) {
            el._chartInstance.resize();
        }
    });
});

// Exporting Indicators namespace
window.Indicators = Indicators;
