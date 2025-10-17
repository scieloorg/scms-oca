/*
    JavaScript for rendering charts in the indicators page.
    It uses ECharts to create dynamic and interactive charts based on the provided data.
    It also ensures that breakdown labels are user-friendly by converting codes to full names where applicable.
    Depends on `helpers.js` for label formatting functions.
    Exposes functions to render main charts and percentage breakdown charts, and to resize charts on window resize events.
*/

(function (window, document) {
  'use strict';

  var Indicators = window.Indicators || (window.Indicators = {});

  var BASE_TOOLTIP_PROPS = {
    confine: true,
    enterable: true,
    extraCssText: 'max-height:50vh; overflow-y:auto;'
  };

  // Build and return a tooltip configuration by merging base properties with overrides
  function buildTooltip(overrides) {
    return Object.assign({}, BASE_TOOLTIP_PROPS, overrides || {});
  }

  // Build and return a grid configuration by merging base properties with overrides
  function buildGrid(overrides) {
    return Object.assign({ top: 110, left: 0, right: 200, bottom: 40, containLabel: true }, overrides || {});
  }

  // Build and return a toolbox configuration with specified magic types
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

  // Build and return a legend configuration if keys are provided
  function buildLegend(keys) {
    if (!Array.isArray(keys) || !keys.length) {
      return null;
    }
    return {
      type: 'scroll',
      data: keys,
      orient: 'horizontal',
      bottom: 0
    };
  }

  // Render the main chart based on the provided data and study unit
  function renderChart(data, studyUnit) {
    Indicators.ensureFriendlyBreakdownLabels(data);

    var chartContainer = document.getElementById('main-chart');
    if (!chartContainer) return;

    var studyUnitSubtitle = (studyUnit === 'citation') ? 'Study Unit: Citation' : 'Study Unit: Document';
    var chartObj = Indicators.initChartInstance(chartContainer);
    Indicators.destroyChartInstance(document.getElementById('inner-percentage-chart'));
    Indicators.destroyChartInstance(document.getElementById('outer-percentage-chart'));
    if (!chartObj) return;

    var chartOpts;

    if (data.breakdown_variable && data.series && data.years) {
      var breakdownLabelElement = document.querySelector('label[for="' + data.breakdown_variable + '"]');
      var breakdownLabel = breakdownLabelElement ? breakdownLabelElement.textContent.trim() : data.breakdown_variable.replace(/_/g, ' ');
      var title = 'Breakdown by ' + breakdownLabel;

      var seriesTotals = (data.series || []).map(function (series) {
        return {
          name: series.name,
          total: (series.data || []).reduce(function (sum, value) { return sum + value; }, 0),
          data: series.data
        };
      }).sort(function (a, b) { return b.total - a.total; });

      var orderedKeys = seriesTotals.map(function (series) { return series.name; });
      var orderedSeries = seriesTotals.map(function (series) {
        return {
          name: series.name,
          type: 'bar',
          stack: 'total',
          data: series.data
        };
      });

      chartOpts = {
        title: { text: title, subtext: studyUnitSubtitle },
        tooltip: buildTooltip({ trigger: 'axis', axisPointer: { type: 'shadow' } }),
        grid: buildGrid(),
        toolbox: buildToolbox(['line', 'bar', 'tiled']),
        xAxis: { type: 'category', data: data.years },
        yAxis: { type: 'value' },
        series: orderedSeries
      };

      var legend = buildLegend(orderedKeys);
      if (legend) {
        chartOpts.legend = legend;
      }
    } else if (studyUnit === 'citation') {
      chartOpts = {
        title: { text: 'Number of Citations per Year', subtext: studyUnitSubtitle },
        tooltip: buildTooltip(),
        grid: buildGrid({ bottom: '10%' }),
        toolbox: buildToolbox(['line', 'bar', 'tiled']),
        xAxis: { type: 'category', data: data.years || [] },
        yAxis: { type: 'value' },
        series: [{ name: 'Citations', type: 'bar', data: data.total_citations_per_year || [] }]
      };
    } else {
      chartOpts = {
        title: { text: 'Number of Documents per Year', subtext: studyUnitSubtitle },
        tooltip: buildTooltip(),
        grid: buildGrid({ bottom: '10%' }),
        toolbox: buildToolbox(['line', 'bar', 'tiled']),
        xAxis: { type: 'category', data: data.years || [] },
        yAxis: { type: 'value' },
        series: [{ name: 'Documents', type: 'bar', data: data.ndocs_per_year || [] }]
      };
    }

    chartObj.setOption(chartOpts);
  }

  // Render the outer percentage chart comparing filtered data to baseline
  function renderOuterPercentageChart(data, studyUnit) {
    Indicators.ensureFriendlyBreakdownLabels(data);

    var percentageChartContainer = document.getElementById('outer-percentage-chart');
    if (!percentageChartContainer) return;

    if (!data || !data.breakdown_variable || !Array.isArray(data.series) || !Array.isArray(data.years)) {
      Indicators.destroyChartInstance(percentageChartContainer);
      return;
    }

    var baselinePayload = {
      study_unit: studyUnit === 'citation' ? 'citation' : 'document',
      breakdown_variable: data.breakdown_variable
    };

    fetch('/indicators/indicators/?data_source=' + encodeURIComponent(window.data_source || '') + '&country_unit=' + encodeURIComponent(window.country_unit || ''), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(baselinePayload)
    })
      .then(function (response) { return response.json(); })
      .then(function (baseline) {
        Indicators.ensureFriendlyBreakdownLabels(baseline);

        var chartObj = Indicators.initChartInstance(percentageChartContainer);
        if (!chartObj) return;

        var filteredYears = data.years || [];
        var filteredSeries = data.series || [];
        var baselineYears = (baseline && baseline.years) ? baseline.years.map(String) : [];
        var baselineSeries = (baseline && baseline.series) ? baseline.series : [];

        var baselineMap = {};
        (baselineSeries || []).forEach(function (series) {
          var name = String(series.name);
          baselineMap[name] = baselineMap[name] || {};
          (series.data || []).forEach(function (value, idx) {
            var year = baselineYears[idx];
            if (typeof year !== 'undefined') {
              baselineMap[name][String(year)] = Number(value || 0);
            }
          });
        });

        var seriesTotals = filteredSeries.map(function (series) {
          return {
            name: String(series.name),
            total: (series.data || []).reduce(function (sum, value) { return sum + value; }, 0),
            data: series.data || []
          };
        }).sort(function (a, b) { return b.total - a.total; });

        var orderedKeys = seriesTotals.map(function (series) { return series.name; });

        var percentSeries = seriesTotals.map(function (series) {
          var baseByYear = baselineMap[series.name] || {};
          var pctData = (series.data || []).map(function (val, idx) {
            var year = String(filteredYears[idx]);
            var baseValue = Number(baseByYear[year] || 0);
            if (!baseValue) return 0;
            return ((Number(val) / baseValue) * 100).toFixed(2);
          });
          return {
            name: series.name,
            type: 'bar',
            stack: 'total',
            emphasis: { focus: 'series' },
            data: pctData
          };
        });

        var breakdownLabelElement = document.querySelector('label[for="' + data.breakdown_variable + '"]');
        var breakdownLabel = breakdownLabelElement ? breakdownLabelElement.textContent.trim() : data.breakdown_variable.replace(/_/g, ' ');
        var studyUnitSubtitle = (studyUnit === 'citation') ? 'Study Unit: Citation' : 'Study Unit: Document';

        var legend = buildLegend(orderedKeys);

        var chartOpts = {
          title: { text: 'Breakdown by ' + breakdownLabel + ' (% relative to unfiltered data)', subtext: studyUnitSubtitle },
          tooltip: buildTooltip({
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: function (params) {
              if (!params || !params.length) return '';
              var yearIdx = params[0].dataIndex;
              var yearLabel = String(filteredYears[yearIdx]);
              var lines = [params[0].axisValueLabel];
              params.forEach(function (item) {
                var name = item.seriesName;
                var baseValue = Number((baselineMap[name] || {})[yearLabel] || 0);
                var filteredSeriesEntry = filteredSeries.find(function (seriesItem) { return String(seriesItem.name) === String(name); }) || { data: [] };
                var filteredValue = filteredSeriesEntry.data[yearIdx] || 0;
                lines.push(item.marker + name + ': ' + item.value + '% (' + filteredValue + ' / ' + baseValue + ')');
              });
              return lines.join('<br/>');
            }
          }),
          grid: buildGrid(),
          toolbox: buildToolbox(['bar', 'tiled']),
          xAxis: { type: 'category', data: filteredYears },
          yAxis: { type: 'value', axisLabel: { formatter: '{value} %' } },
          series: percentSeries
        };

        if (legend) {
          chartOpts.legend = legend;
        }

        chartObj.setOption(chartOpts);
      })
      .catch(function () {
        Indicators.destroyChartInstance(percentageChartContainer);
      });
  }

  // Render the inner percentage chart showing percentage within filtered data
  function renderInnerPercentageChart(data, studyUnit) {
    Indicators.ensureFriendlyBreakdownLabels(data);

    var percentageChartContainer = document.getElementById('inner-percentage-chart');
    if (!percentageChartContainer) return;

    var studyUnitSubtitle = (studyUnit === 'citation') ? 'Study Unit: Citation' : 'Study Unit: Document';

    var chartObj = Indicators.initChartInstance(percentageChartContainer);
    if (!chartObj) return;

    var chartOpts;

    if (data.breakdown_variable && data.series && data.years) {
      var breakdownLabelElement = document.querySelector('label[for="' + data.breakdown_variable + '"]');
      var breakdownLabel = breakdownLabelElement ? breakdownLabelElement.textContent.trim() : data.breakdown_variable.replace(/_/g, ' ');
      var title = 'Breakdown by ' + breakdownLabel + ' (% within filtered data)';

      var seriesTotals = (data.series || []).map(function (series) {
        var total = (series.data || []).reduce(function (sum, value) { return sum + value; }, 0);
        return { name: series.name, total: total, data: series.data || [] };
      }).sort(function (a, b) { return b.total - a.total; });

      var orderedKeys = seriesTotals.map(function (series) { return series.name; });
      var orderedSeries = seriesTotals.map(function (series) {
        return {
          name: series.name,
          type: 'bar',
          stack: 'total',
          emphasis: { focus: 'series' },
          label: {
            show: false,
            position: 'inside',
            formatter: function (params) {
              var totalForYear = 0;
              var yearIndex = params.dataIndex;
              seriesTotals.forEach(function (totalSeries) {
                totalForYear += totalSeries.data[yearIndex];
              });
              var percent = totalForYear ? ((params.value / totalForYear) * 100).toFixed(2) : 0;
              return percent + '%';
            }
          },
          data: (series.data || []).map(function (value, index) {
            var totalForYear = 0;
            seriesTotals.forEach(function (totalSeries) {
              totalForYear += totalSeries.data[index];
            });
            var percent = totalForYear ? ((value / totalForYear) * 100).toFixed(2) : 0;
            return percent;
          })
        };
      });

      chartOpts = {
        title: { text: title, subtext: studyUnitSubtitle },
        tooltip: buildTooltip({ trigger: 'axis', axisPointer: { type: 'shadow' } }),
        grid: buildGrid(),
        toolbox: buildToolbox(['bar', 'tiled']),
        xAxis: { type: 'category', data: data.years || [] },
        yAxis: { type: 'value', axisLabel: { formatter: '{value} %' } },
        series: orderedSeries
      };

      var legend = buildLegend(orderedKeys);
      if (legend) {
        chartOpts.legend = legend;
      }
    } else if (studyUnit === 'citation') {
      chartOpts = {
        title: { text: 'Percentage of Citations per Year', subtext: studyUnitSubtitle },
        tooltip: buildTooltip(),
        grid: buildGrid({ bottom: '10%' }),
        toolbox: buildToolbox(['line', 'bar', 'tiled']),
        xAxis: { type: 'category', data: data.years || [] },
        yAxis: { type: 'value', axisLabel: { formatter: '{value} %' } },
        series: [{
          name: 'Citations',
          type: 'bar',
          data: (data.total_citations_per_year || []).map(function (value) {
            var total = (data.total_citations_per_year || []).reduce(function (sum, val) { return sum + val; }, 0);
            var percent = total ? ((value / total) * 100).toFixed(2) : 0;
            return percent;
          })
        }]
      };
    } else {
      chartOpts = {
        title: { text: 'Percentage of Documents per Year', subtext: studyUnitSubtitle },
        tooltip: buildTooltip(),
        grid: buildGrid({ bottom: '10%' }),
        toolbox: buildToolbox(['line', 'bar', 'tiled']),
        xAxis: { type: 'category', data: data.years || [] },
        yAxis: { type: 'value', axisLabel: { formatter: '{value} %' } },
        series: [{
          name: 'Documents',
          type: 'bar',
          data: (data.ndocs_per_year || []).map(function (value) {
            var total = (data.ndocs_per_year || []).reduce(function (sum, val) { return sum + val; }, 0);
            var percent = total ? ((value / total) * 100).toFixed(2) : 0;
            return percent;
          })
        }]
      };
    }

    chartObj.setOption(chartOpts);
  }

  Indicators.renderChart = renderChart;
  Indicators.renderOuterPercentageChart = renderOuterPercentageChart;
  Indicators.renderInnerPercentageChart = renderInnerPercentageChart;

  // Resize all visible charts to fit their containers
  function resizeVisibleCharts() {
    var ids = ['main-chart', 'inner-percentage-chart', 'outer-percentage-chart'];
    var raf = window.requestAnimationFrame || function (cb) { return setTimeout(cb, 16); };
    raf(function () {
      ids.forEach(function (id) {
        var el = document.getElementById(id);
        if (el && el._chartInstance && typeof el._chartInstance.resize === 'function') {
          el._chartInstance.resize();
        }
      });
    });
  }

  Indicators.resizeVisibleCharts = resizeVisibleCharts;

  window.renderChart = renderChart;
  window.renderOuterPercentageChart = renderOuterPercentageChart;
  window.renderInnerPercentageChart = renderInnerPercentageChart;
})(window, document);
