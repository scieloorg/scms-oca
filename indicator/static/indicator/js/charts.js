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
      magicType: { type: magicTypes || ['bar', "line"] },
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
    const chartDivs = [
        'docs-chart-div',
        'citations-chart-div',
        'citations-per-doc-chart-div'
    ];

    chartDivs.forEach(divId => {
        const div = document.getElementById(divId);
        if (div) {
            div.classList.add('d-none');
            const chart = document.getElementById(divId.replace('-div', ''));
            if (chart) {
                destroyChartInstance(chart);
            }
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
 * Renders a chart based on the provided data and series type.
 * @param {object} options - The options for rendering the chart.
 * @param {string} options.chartId - The ID of the chart container element.
 * @param {string} options.chartDivId - The ID of the chart div container element.
 * @param {object} options.data - The indicator data received from the API.
 * @param {string} options.seriesType - The type of series to render ('Documents', 'Citations', 'Citations per Document').
 * @param {string} options.title - The title of the chart.
 */
Indicators.renderChart = function({ chartId, chartDivId, data, seriesType, title }) {
    const chartContainer = document.getElementById(chartId);
    if (!chartContainer) return;

    const chartContainerParent = document.getElementById(chartDivId);
    if (!chartContainerParent) return;

    chartContainerParent.classList.remove('d-none');

    const chartObj = initChartInstance(chartContainer);
    const chartType = 'bar';

    let series;
    if (data.breakdown_variable) {
        if (seriesType === 'Citations per Document') {
            const docSeries = data.series.filter(s => s.name.endsWith('(Documents)'));
            const citSeries = data.series.filter(s => s.name.endsWith('(Citations)'));

            series = docSeries.map(ds => {
                const cs = citSeries.find(cs => cs.name.replace(' (Citations)', '') === ds.name.replace(' (Documents)', ''));
                const cpdData = ds.data.map((ndocs, i) => {
                    return ndocs > 0 ? (cs.data[i] / ndocs).toFixed(2) : 0;
                });
                let seriesName = ds.name.replace(' (Documents)', '');
                return { name: seriesName, type: chartType, data: cpdData, stack: 'total' };
            });
        } else {
            series = data.series
                .filter(s => s.name.endsWith(`(${seriesType})`))
                .map(s => {
                    let seriesName = s.name.replace(` (${seriesType})`, '');
                    return { ...s, name: seriesName, type: chartType, stack: 'total' };
                });
        }
    } else {
        if (seriesType === 'Documents') {
            series = [{ name: 'Documents', type: chartType, data: data.ndocs_per_year }];
        } else if (seriesType === 'Citations') {
            series = [{ name: 'Citations', type: chartType, data: data.total_citations_per_year }];
        } else if (seriesType === 'Citations per Document') {
            const cpdData = data.ndocs_per_year.map((ndocs, i) => {
                return ndocs > 0 ? (data.total_citations_per_year[i] / ndocs).toFixed(4) : 0;
            });
            series = [{ name: 'Citations per Document', type: chartType, data: cpdData }];
        }
    }

    const chartOpts = {
        title: { text: title },
        tooltip: buildTooltip({ trigger: 'axis', axisPointer: { type: 'shadow' } }),
        grid: buildGrid(),
        toolbox: buildToolbox(['bar', 'line']),
        xAxis: { type: 'category', data: data.years },
        yAxis: { type: 'value' },
        series: series,
        legend: buildLegend(series.map(s => s.name))
    };

    chartObj.setOption(chartOpts, true);
}

// Handle window resize to adjust charts
window.addEventListener('resize', () => {
    ['docs-chart', 'citations-chart', 'citations-per-doc-chart'].forEach(id => {
        const el = document.getElementById(id);
        if (el && el._chartInstance) {
            el._chartInstance.resize();
        }
    });
});

// Exporting Indicators namespace
window.Indicators = Indicators;