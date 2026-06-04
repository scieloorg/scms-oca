const Indicators = {};

function buildTooltip(overrides) {
    return {
        confine: true,
        enterable: true,
        extraCssText: 'max-height:50vh; overflow-y:auto;',
        ...overrides
    };
}

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

function buildToolbox(magicTypes, dataViewOptions = {}) {
  const feature = {
    dataView: {
      show: true,
      title: gettext('Data'),
      readOnly: true,
      lang: ['', gettext('Close')],
      ...dataViewOptions,
    },
    saveAsImage: { show: true },
    restore: { show: true },
    dataZoom: {}
  };

  if (magicTypes === undefined || magicTypes === null) {
    feature.magicType = { type: ['bar', 'line'] };
  } else if (magicTypes.length) {
    feature.magicType = { type: magicTypes };
  }

  return {
    orient: 'vertical',
    feature,
  };
}

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

let chartNumberLocale = null;
const chartNumberFormatterCache = new Map();

function normalizeChartNumberLocale(locale) {
    const normalizedLocale = String(locale || '').trim().replace(/_/g, '-');
    if (!normalizedLocale) return null;

    if (typeof Intl !== 'undefined' && typeof Intl.getCanonicalLocales === 'function') {
        try {
            const [canonicalLocale] = Intl.getCanonicalLocales(normalizedLocale);
            return canonicalLocale || normalizedLocale;
        } catch (_error) {
            return normalizedLocale;
        }
    }

    return normalizedLocale;
}

function setChartNumberLocale(locale) {
    const nextLocale = normalizeChartNumberLocale(locale);
    if (nextLocale === chartNumberLocale) return;
    chartNumberLocale = nextLocale;
    chartNumberFormatterCache.clear();
}

function getChartNumberFormatter(options = {}) {
    const formatterLocale = chartNumberLocale || undefined;
    const cacheKey = JSON.stringify([formatterLocale || '', options]);

    if (!chartNumberFormatterCache.has(cacheKey)) {
        chartNumberFormatterCache.set(
            cacheKey,
            new Intl.NumberFormat(formatterLocale, options),
        );
    }

    return chartNumberFormatterCache.get(cacheKey);
}

function formatChartNumber(value, options = {}) {
    if (value === null || value === undefined || value === '') return '-';

    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) return '-';

    return getChartNumberFormatter(options).format(numericValue);
}

function formatChartAxisNumber(value, options = {}) {
    const {
        decimals = null,
        isPercent = false,
    } = options;

    if (value === null || value === undefined || value === '') return '-';

    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) return '-';

    const maximumFractionDigits = Number.isInteger(decimals)
        ? decimals
        : (Number.isInteger(numericValue) ? 0 : 2);

    const formatted = formatChartNumber(numericValue, {
        minimumFractionDigits: 0,
        maximumFractionDigits,
    });

    return isPercent ? `${formatted}%` : formatted;
}

function formatTooltipNumber(value, options = {}) {
    const {
        decimals = null,
        isPercent = false,
    } = typeof options === 'boolean' ? { isPercent: options } : options;

    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) return '-';

    const formatterOptions = {
        minimumFractionDigits: 0,
        maximumFractionDigits: Number.isInteger(decimals)
            ? decimals
            : (Math.abs(numericValue) < 100 ? 2 : 1),
    };

    const formatted = formatChartNumber(numericValue, formatterOptions);
    return isPercent ? `${formatted}%` : formatted;
}

function buildEncodedCopyText(columns, rows) {
    const lines = [
        (columns || []).map(column => String(column.label || '')),
        ...((rows || []).map(row => (row || []).map(cell => String(cell ?? '')))),
    ];
    const copyText = lines.map(line => line.join('\t')).join('\n');
    return encodeURIComponent(copyText);
}

function formatDataViewNumber(value, options = {}) {
    const {
        decimals = null,
        isPercent = false,
    } = options;

    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) return '-';

    const maximumFractionDigits = Number.isInteger(decimals)
        ? decimals
        : (Number.isInteger(numericValue)
            ? 0
            : (Math.abs(numericValue) >= 1 ? 2 : 4));

    const formatterOptions = {
        minimumFractionDigits: 0,
        maximumFractionDigits,
    };

    const formatted = formatChartNumber(numericValue, formatterOptions);

    return isPercent ? `${formatted}%` : formatted;
}

function buildDataViewTable({ title, columns, rows, emptyMessage }) {
    const copyButtonHtml = Array.isArray(rows) && rows.length
        ? `
            <button
                type="button"
                class="indicator-data-view__copy"
                data-copy-text="${buildEncodedCopyText(columns, rows)}"
                data-label-default="${escapeHtml(gettext('Copy'))}"
                data-label-success="${escapeHtml(gettext('Copied'))}"
                data-label-error="${escapeHtml(gettext('Copy failed'))}">
                ${escapeHtml(gettext('Copy'))}
            </button>
        `
        : '';
    const titleHtml = title
        ? `<div class="indicator-data-view__title">${escapeHtml(title)}</div>`
        : '';
    const dataViewHeaderHtml = (titleHtml || copyButtonHtml)
        ? `
            <div class="indicator-data-view__header">
                ${titleHtml || '<div></div>'}
                ${copyButtonHtml ? `<div class="indicator-data-view__actions">${copyButtonHtml}</div>` : ''}
            </div>
        `
        : '';

    if (!Array.isArray(rows) || !rows.length) {
        return `
            <div class="indicator-data-view">
                ${dataViewHeaderHtml}
                <div class="indicator-data-view__empty">${escapeHtml(emptyMessage || gettext('No data available'))}</div>
            </div>
        `;
    }

    const tableHeaderHtml = (columns || []).map(column => {
        const alignClass = column.align === 'right' ? ' indicator-data-view__cell--numeric' : '';
        return `<th class="indicator-data-view__cell${alignClass}">${escapeHtml(column.label)}</th>`;
    }).join('');

    const rowsHtml = rows.map(row => `
        <tr>
            ${(row || []).map((cellValue, index) => {
                const column = columns[index] || {};
                const alignClass = column.align === 'right' ? ' indicator-data-view__cell--numeric' : '';
                return `<td class="indicator-data-view__cell${alignClass}">${escapeHtml(cellValue)}</td>`;
            }).join('')}
        </tr>
    `).join('');

    return `
        <div class="indicator-data-view">
            ${dataViewHeaderHtml}
            <div class="indicator-data-view__scroll">
                <table class="indicator-data-view__table">
                    <thead>
                        <tr>${tableHeaderHtml}</tr>
                    </thead>
                    <tbody>${rowsHtml}</tbody>
                </table>
            </div>
        </div>
    `;
}

function buildTimeSeriesDataView({ title, axisLabel, axisValues, series, forcePercentAxis = false, emptyMessage }) {
    const columns = [{ label: axisLabel || gettext('Year') }, ...(series || []).map(item => ({
        label: item.name,
        align: 'right',
    }))];

    const rows = Array.isArray(axisValues)
        ? axisValues.map((axisValue, index) => [
            axisValue,
            ...(series || []).map(item => {
                const formatter = typeof item.dataViewFormatter === 'function'
                    ? item.dataViewFormatter
                    : (value => formatDataViewNumber(value, { isPercent: forcePercentAxis || Boolean(item.isPercentSeries) }));
                const value = Array.isArray(item.data) ? item.data[index] : null;
                return formatter(value);
            }),
        ])
        : [];

    return buildDataViewTable({
        title,
        columns,
        rows,
        emptyMessage: emptyMessage || gettext('No data available'),
    });
}

function buildTooltipCard(title, rowsHtml, emptyMessage) {
    const contentHtml = rowsHtml || `<div class="indicator-tooltip__empty">${escapeHtml(emptyMessage || gettext('No data available'))}</div>`;

    return `
        <div class="indicator-tooltip">
            <div class="indicator-tooltip__year">${escapeHtml(title)}</div>
            <div class="indicator-tooltip__rows">
                ${contentHtml}
            </div>
        </div>
    `;
}

function buildAxisTooltipFormatter(forcePercentAxis = false) {
    const {
        forcePercentAxis: resolvedForcePercentAxis = false,
        series = [],
        emptyMessage = null,
    } = typeof forcePercentAxis === 'boolean' ? { forcePercentAxis } : (forcePercentAxis || {});

    const seriesFormatterMap = new Map(
        (series || []).map(item => [
            item.name,
            typeof item.tooltipFormatter === 'function'
                ? item.tooltipFormatter
                : (value => formatTooltipNumber(value, {
                    isPercent: resolvedForcePercentAxis || Boolean(item.isPercentSeries),
                })),
        ]),
    );

    return (params) => {
        const items = Array.isArray(params) ? params : [params];
        if (!items.length) return '';

        const axisValue = items[0]?.axisValueLabel || items[0]?.axisValue || items[0]?.name || '';
        const rowsHtml = items.map(item => {
            const formatter = seriesFormatterMap.get(item?.seriesName) || (value => formatTooltipNumber(value, resolvedForcePercentAxis));
            return `
                <div class="indicator-tooltip__row">
                    <span class="indicator-tooltip__label">${item?.marker || ''}${escapeHtml(item?.seriesName || '')}</span>
                    <span class="indicator-tooltip__value">${formatter(item?.value)}</span>
                </div>
            `;
        }).join('');

        return buildTooltipCard(axisValue, rowsHtml, emptyMessage);
    };
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

function destroyChartInstance(container) {
    if (container && container._chartInstance) {
        container._chartInstance.dispose();
        container._chartInstance = null;
    }
}

function clearGraphsContainer() {
    document.querySelectorAll('.indicator-chart-canvas').forEach(canvas => {
        destroyChartInstance(canvas);
        const div = document.getElementById(`${canvas.id}-div`);
        if (div) {
            div.classList.add('d-none');
        }
    });

    const relativeSection = document.getElementById('relative-metrics-section');
    if (relativeSection) {
        relativeSection.classList.add('d-none');
    }
}

function initChartInstance(container) {
    if (!container) return null;

    destroyChartInstance(container);

    const chart = echarts.init(container);
    container._chartInstance = chart;

    return chart;
}

Indicators.renderChart = function({
    chartId,
    chartDivId,
    data,
    title,
    subtitle,
    forcePercentAxis = false,
}) {
    const chartContainer = document.getElementById(chartId);
    if (!chartContainer) return false;

    const chartContainerParent = document.getElementById(chartDivId);
    if (!chartContainerParent) return false;

    const series = data.series || [];
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

    const hasBreakdown = !!data.breakdown_variable;
    const dataViewSeries = hasBreakdown
        ? series.slice().sort((a, b) => getSeriesTotal(b?.data) - getSeriesTotal(a?.data))
        : series;
    const legendNames = dataViewSeries.map(s => s.name);

    const tooltipOptions = hasBreakdown
        ? buildTooltip({
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: buildBreakdownTooltipFormatter(forcePercentAxis),
            extraCssText: 'background:transparent;border:none;box-shadow:none;padding:0;',
        })
        : buildTooltip({
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: buildAxisTooltipFormatter(forcePercentAxis),
            extraCssText: 'background:transparent;border:none;box-shadow:none;padding:0;',
        });

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
        toolbox: buildToolbox(['bar', 'line'], {
            optionToContent: () => buildTimeSeriesDataView({
                title: [title, subtitle].filter(Boolean).join(' - '),
                axisLabel: gettext('Year'),
                axisValues: years,
                series: dataViewSeries,
                forcePercentAxis,
            }),
        }),
        xAxis: { type: 'category', data: years },
        yAxis: forcePercentAxis
            ? {
                type: 'value',
                axisLabel: { formatter: '{value}%' }
            }
            : { type: 'value' },
        series: series.map(s => ({
            name: s.name,
            type: s.type || 'bar',
            data: s.data,
            stack: s.stack || undefined,
        })),
        legend: buildLegend(
            legendNames,
            hasBreakdown ? { left: 0, right: 'auto' } : undefined,
        ),
    };

    chartObj.setOption(chartOpts, true);
    chartObj.resize();
    return true;
}

window.addEventListener('resize', () => {
    document.querySelectorAll('.indicator-chart-canvas').forEach(el => {
        const instance = echarts.getInstanceByDom(el) || el._chartInstance;
        if (instance) {
            instance.resize();
        }
    });
});

Indicators.renderCustomChart = function({
    chartId,
    chartDivId,
    data,
    title,
    xLabel,
    yLabel
}) {
    const chartContainer = document.getElementById(chartId);
    if (!chartContainer) return false;

    const chartContainerParent = document.getElementById(chartDivId);
    if (!chartContainerParent) return false;

    let chart = echarts.getInstanceByDom(chartContainer);
    if (!chart) {
        chart = echarts.init(chartContainer);
        chartContainer._chartInstance = chart;
    }

    const isPie = data.chart_type === 'pie' || (data.datasets && data.datasets.some(d => d.type === 'pie'));

    let option;
    if (isPie) {
        const pieData = [];
        const labels = data.labels || [];
        const seriesData = data.datasets && data.datasets[0] ? (data.datasets[0].data || []) : [];

        labels.forEach((label, index) => {
            pieData.push({
                value: seriesData[index] || 0,
                name: label
            });
        });

        option = {
            title: {
                text: title,
                left: 'center',
                textStyle: {
                    fontSize: 14,
                    fontWeight: 'bold',
                    color: '#333'
                }
            },
            tooltip: {
                trigger: 'item',
                formatter: '{a} <br/>{b} : {c}% ({d}%)'
            },
            legend: {
                orient: 'horizontal',
                bottom: '0',
                data: labels
            },
            series: [
                {
                    name: title,
                    type: 'pie',
                    radius: '55%',
                    center: ['50%', '50%'],
                    data: pieData,
                    emphasis: {
                        itemStyle: {
                            shadowBlur: 10,
                            shadowOffsetX: 0,
                            shadowColor: 'rgba(0, 0, 0, 0.5)'
                        }
                    }
                }
            ]
        };
    } else {
        option = {
            title: {
                text: title,
                left: 'center',
                textStyle: {
                    fontSize: 14,
                    fontWeight: 'bold',
                    color: '#333'
                }
            },
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' }
            },
            legend: {
                data: data.datasets.map(d => d.label || d.name),
                top: 25
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '10%',
                top: '20%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: data.labels,
                name: xLabel,
                nameLocation: 'middle',
                nameGap: 25
            },
            yAxis: {
                type: 'value',
                name: yLabel
            },
            series: data.datasets.map(d => ({
                name: d.label || d.name,
                type: d.type || 'bar',
                data: d.data
            }))
        };
    }

    chart.setOption(option, true);
    chartContainerParent.classList.remove('d-none');
    chart.resize();
    return true;
};

window.Indicators = Indicators;
