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
        top: 86,
        left: 0,
        right: 90,
        bottom: 56,
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
function buildLegend(keys, overrides) {
    if (!Array.isArray(keys) || !keys.length) return null;

    return {
        type: 'scroll',
        data: keys,
        orient: 'horizontal',
        bottom: 0,
        ...overrides,
    };
}

function wrapChartTitle(title, containerWidth) {
    const text = String(title || '').trim();
    if (!text) return '';

    const safeWidth = Number(containerWidth) || 640;
    const maxCharsPerLine = Math.max(26, Math.floor((safeWidth - 24) / 8));
    if (text.length <= maxCharsPerLine) return text;

    const words = text.split(/\s+/);
    const lines = [];
    let currentLine = '';

    words.forEach(word => {
        const candidate = currentLine ? `${currentLine} ${word}` : word;
        if (candidate.length <= maxCharsPerLine) {
            currentLine = candidate;
            return;
        }

        if (currentLine) {
            lines.push(currentLine);
            currentLine = '';
        }

        if (word.length <= maxCharsPerLine) {
            currentLine = word;
            return;
        }

        let start = 0;
        while (start < word.length) {
            const chunk = word.slice(start, start + maxCharsPerLine);
            if (chunk.length === maxCharsPerLine) {
                lines.push(chunk);
            } else {
                currentLine = chunk;
            }
            start += maxCharsPerLine;
        }
    });

    if (currentLine) {
        lines.push(currentLine);
    }

    return lines.join('\n');
}

function hasNonZeroSeriesData(series) {
    if (!Array.isArray(series) || !series.length) return false;
    for (const s of series) {
        const data = s && Array.isArray(s.data) ? s.data : [];
        for (const val of data) {
            if (val === null || val === undefined) continue;
            const num = Number(val);
            if (Number.isFinite(num) && Math.abs(num) > 0) {
                return true;
            }
        }
    }
    return false;
}

function hasAnyNonZeroValue(data) {
    if (!Array.isArray(data) || !data.length) return false;
    return data.some(value => {
        const num = Number(value);
        return Number.isFinite(num) && Math.abs(num) > 0;
    });
}

function getSeriesTotal(data) {
    if (!Array.isArray(data) || !data.length) return 0;
    return data.reduce((acc, value) => {
        const num = Number(value);
        if (!Number.isFinite(num)) return acc;
        return acc + num;
    }, 0);
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function formatTooltipNumber(value, isPercent = false) {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) return '-';

    const formatter = new Intl.NumberFormat(undefined, {
        minimumFractionDigits: 0,
        maximumFractionDigits: Math.abs(numericValue) < 100 ? 2 : 1,
    });

    const formatted = formatter.format(numericValue);
    return isPercent ? `${formatted}%` : formatted;
}

function buildBreakdownTooltipFormatter(forcePercentAxis = false) {
    return (params) => {
        const items = Array.isArray(params) ? params : [params];
        if (!items.length) return '';

        const yearValue = items[0]?.axisValueLabel || items[0]?.axisValue || items[0]?.name || '';
        const sortedRows = items
            .map(item => {
                const numericValue = Number(item?.value);
                return {
                    marker: item?.marker || '',
                    seriesName: item?.seriesName || '',
                    value: Number.isFinite(numericValue) ? numericValue : 0,
                };
            })
            .filter(item => Math.abs(item.value) > 0)
            .sort((a, b) => b.value - a.value);

        const rowsHtml = sortedRows.length
            ? sortedRows.map(item => `
                <div class="indicator-tooltip__row">
                    <span class="indicator-tooltip__label">${item.marker}${escapeHtml(item.seriesName)}</span>
                    <span class="indicator-tooltip__value">${formatTooltipNumber(item.value, forcePercentAxis)}</span>
                </div>
            `).join('')
            : `<div class="indicator-tooltip__empty">${escapeHtml(gettext('No non-zero values'))}</div>`;

        return `
            <div class="indicator-tooltip">
                <div class="indicator-tooltip__year">${escapeHtml(yearValue)}</div>
                <div class="indicator-tooltip__rows">
                    ${rowsHtml}
                </div>
            </div>
        `;
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
        'periodicals-chart-div',
        'docs-chart-div',
        'citations-chart-div',
        'citations-per-doc-chart-div',
        'cited-docs-chart-div',
        'pct-cited-docs-chart-div',
        'periodicals-share-chart-div',
        'docs-share-chart-div',
        'citations-share-chart-div',
        'citations-per-doc-share-chart-div',
        'cited-docs-share-chart-div',
        'pct-cited-docs-share-chart-div',
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

    const relativeSection = document.getElementById('relative-metrics-section');
    if (relativeSection) {
        relativeSection.classList.add('d-none');
    }
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
 * @param {string} options.subtitle - Optional secondary title (e.g., breakdown description).
 * @param {boolean} options.disableBreakdown - Forces single-series rendering even when breakdown is selected.
 * @param {boolean} options.forcePercentAxis - Forces y-axis percentage labels.
 */
Indicators.renderChart = function({
    chartId,
    chartDivId,
    data,
    seriesType,
    title,
    subtitle,
    disableBreakdown = false,
    forcePercentAxis = false,
}) {
    const chartContainer = document.getElementById(chartId);
    if (!chartContainer) return false;

    const chartContainerParent = document.getElementById(chartDivId);
    if (!chartContainerParent) return false;

    const chartType = 'bar';
    const hasBreakdown = !!(data.breakdown_variable && !disableBreakdown);
    const relativeMetrics = data.relative_metrics || {};

    let series;
    if (hasBreakdown) {
        if (seriesType === 'Citations per Document') {
            const docSeries = data.series.filter(s => s.name.endsWith('(Documents)'));
            const citSeries = data.series.filter(s => s.name.endsWith('(Citations)'));

            series = docSeries.map(ds => {
                const cs = citSeries.find(cs => cs.name.replace(' (Citations)', '') === ds.name.replace(' (Documents)', ''));
                const cpdData = ds.data.map((ndocs, i) => {
                    const citations = cs && Array.isArray(cs.data) ? cs.data[i] : 0;
                    return ndocs > 0 ? (citations / ndocs).toFixed(2) : 0;
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
        if (seriesType === 'Periodicals') {
            series = [{ name: gettext('Unique Sources'), type: chartType, data: data.nperiodicals_per_year || [] }];
        } else if (seriesType === 'Documents per Periodical') {
            series = [{ name: gettext('Documents per Source'), type: chartType, data: data.docs_per_periodical_per_year || [] }];
        } else if (seriesType === 'Citations per Periodical') {
            series = [{ name: gettext('Citations per Source'), type: chartType, data: data.citations_per_periodical_per_year || [] }];
        } else if (seriesType === 'Cited Documents per Periodical') {
            series = [{ name: gettext('Cited Documents per Source'), type: chartType, data: data.cited_docs_per_periodical_per_year || [] }];
        } else if (seriesType === 'Percent Periodicals With Cited Docs') {
            series = [{ name: gettext('% Sources With ≥1 Cited Document'), type: chartType, data: data.percent_periodicals_with_cited_docs_per_year || [] }];
        } else if (seriesType === 'Periodicals Share') {
            series = [{ name: gettext('Unique Sources Share (%)'), type: chartType, data: relativeMetrics.periodicals_share_pct_per_year || [] }];
        } else if (seriesType === 'Documents per Source Share') {
            series = [{ name: gettext('Documents per Source (share %)'), type: chartType, data: relativeMetrics.docs_per_source_share_pct_per_year || [] }];
        } else if (seriesType === 'Citations per Source Share') {
            series = [{ name: gettext('Citations per Source (share %)'), type: chartType, data: relativeMetrics.citations_per_source_share_pct_per_year || [] }];
        } else if (seriesType === 'Cited Documents per Source Share') {
            series = [{ name: gettext('Cited Documents per Source (share %)'), type: chartType, data: relativeMetrics.cited_docs_per_source_share_pct_per_year || [] }];
        } else if (seriesType === 'Percent Sources With Cited Docs Share') {
            series = [{ name: gettext('% Sources With ≥1 Cited Document Share (%)'), type: chartType, data: relativeMetrics.pct_sources_with_cited_docs_share_pct_per_year || [] }];
        } else if (seriesType === 'Cited Documents') {
            series = [{ name: gettext('Cited Documents'), type: chartType, data: data.docs_with_citations_per_year || [] }];
        } else if (seriesType === 'Documents') {
            series = [{ name: gettext('Documents'), type: chartType, data: data.ndocs_per_year }];
        } else if (seriesType === 'Citations') {
            series = [{ name: gettext('Citations'), type: chartType, data: data.total_citations_per_year }];
        } else if (seriesType === 'Documents Share') {
            series = [{ name: gettext('Documents Share (%)'), type: chartType, data: relativeMetrics.docs_share_pct_per_year || [] }];
        } else if (seriesType === 'Citations Share') {
            series = [{ name: gettext('Citations Share (%)'), type: chartType, data: relativeMetrics.citations_share_pct_per_year || [] }];
        } else if (seriesType === 'Citations per Document') {
            const cpdData = data.ndocs_per_year.map((ndocs, i) => {
                return ndocs > 0 ? (data.total_citations_per_year[i] / ndocs).toFixed(4) : 0;
            });
            series = [{ name: gettext('Citations per Document'), type: chartType, data: cpdData }];
        } else if (seriesType === 'Citations per Document Share') {
            series = [{ name: gettext('Citations per Document Share (%)'), type: chartType, data: relativeMetrics.citations_per_doc_share_pct_per_year || [] }];
        } else if (seriesType === 'Percent Docs With Citations') {
            series = [{ name: gettext('% Docs With ≥1 Citation'), type: chartType, data: data.percent_docs_with_citations_per_year || [] }];
        } else if (seriesType === 'Cited Documents Share') {
            series = [{ name: gettext('Cited Documents Share (%)'), type: chartType, data: relativeMetrics.cited_docs_share_pct_per_year || [] }];
        } else if (seriesType === 'Percent Docs With Citations Share') {
            series = [{ name: gettext('% Docs With ≥1 Citation Share (%)'), type: chartType, data: relativeMetrics.pct_docs_with_citations_share_pct_per_year || [] }];
        }
    }

    series = series || [];
    if (hasBreakdown) {
        series = series.filter(s => hasAnyNonZeroValue(s?.data));
    }

    const years = Array.isArray(data.years) ? data.years : [];
    const hasData = years.length > 0 && hasNonZeroSeriesData(series);
    if (!hasData) {
        chartContainerParent.classList.add('d-none');
        destroyChartInstance(chartContainer);
        return false;
    }

    chartContainerParent.classList.remove('d-none');
    const chartObj = initChartInstance(chartContainer);

    const wrappedTitle = wrapChartTitle(title, chartContainer.clientWidth);
    const wrappedSubtitle = wrapChartTitle(subtitle, chartContainer.clientWidth);
    const titleLineCount = wrappedTitle ? wrappedTitle.split('\n').length : 1;
    const subtitleLineCount = wrappedSubtitle ? wrappedSubtitle.split('\n').length : 0;
    const subtitleHeight = subtitleLineCount ? (18 + ((subtitleLineCount - 1) * 14)) : 0;
    const gridTop = Math.max(86, 86 + ((titleLineCount - 1) * 16) + subtitleHeight);
    const legendNames = hasBreakdown
        ? series
            .slice()
            .sort((a, b) => getSeriesTotal(b?.data) - getSeriesTotal(a?.data))
            .map(s => s.name)
        : series.map(s => s.name);
    const tooltipOptions = hasBreakdown
        ? buildTooltip({
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: buildBreakdownTooltipFormatter(forcePercentAxis),
            extraCssText: 'background:transparent;border:none;box-shadow:none;padding:0;',
        })
        : buildTooltip({ trigger: 'axis', axisPointer: { type: 'shadow' } });

    const chartOpts = {
        title: {
            text: wrappedTitle,
            subtext: wrappedSubtitle || '',
            left: 'center',
            itemGap: 6,
            textStyle: {
                fontSize: 14,
                fontWeight: 600,
                lineHeight: 18,
            },
            subtextStyle: {
                fontSize: 11,
                color: '#5f6e7d',
                lineHeight: 14,
            },
        },
        tooltip: tooltipOptions,
        grid: buildGrid({ top: gridTop }),
        toolbox: buildToolbox(['bar', 'line']),
        xAxis: { type: 'category', data: years },
        yAxis: forcePercentAxis
            ? {
                type: 'value',
                axisLabel: { formatter: '{value}%' }
            }
            : { type: 'value' },
        series: series,
        legend: buildLegend(
            legendNames,
            hasBreakdown ? { left: 0, right: 'auto' } : undefined,
        ),
    };

    chartObj.setOption(chartOpts, true);
    return true;
}

// Handle window resize to adjust charts
window.addEventListener('resize', () => {
    [
        'periodicals-chart',
        'docs-chart',
        'citations-chart',
        'citations-per-doc-chart',
        'cited-docs-chart',
        'pct-cited-docs-chart',
        'periodicals-share-chart',
        'docs-share-chart',
        'citations-share-chart',
        'citations-per-doc-share-chart',
        'cited-docs-share-chart',
        'pct-cited-docs-share-chart',
    ].forEach(id => {
        const el = document.getElementById(id);
        if (el && el._chartInstance) {
            el._chartInstance.resize();
        }
    });
});

// Exporting Indicators namespace
window.Indicators = Indicators;
