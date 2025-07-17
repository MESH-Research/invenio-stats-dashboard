import React, { useState, useEffect, useMemo } from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { Button, Container, Header, Segment, Popup, Icon, Form, Checkbox } from 'semantic-ui-react';
import ReactECharts from "echarts-for-react";
import { useStatsDashboard } from '../../context/StatsDashboardContext';
import { CHART_COLORS } from '../../constants';
import { formatNumber, filterByDateRange } from '../../utils';
import { formatDate, createReadableDate } from '../../utils/dates';

// Define y-axis labels for different series
const SERIES_Y_AXIS_LABELS = {
  'Views': i18next.t('Number of Views'),
  'Downloads': i18next.t('Number of Downloads'),
  'Traffic': i18next.t('Downloaded Data Volume (GB)'),
  'Records': i18next.t('Number of Works'),
  'Uploaders': i18next.t('Number of Uploaders'),
  'Data Volume': i18next.t('Uploaded Data Volume (GB)'),
  'default': i18next.t('Value')
};

const FilterSelector = ({ data, displaySeparately, setDisplaySeparately }) => {
  const breakdownOptions = data ? Object.keys(data).filter(k => k !== 'global') : [];

  return (
    <Popup
      trigger={
        <Button
          name="filter"
          floated="right"
          size="small"
          icon={<Icon name="filter" />}
          aria-label="Filter"
          className="stats-chart-filter-selector rel-mt-1 rel-mr-1"
        />
      }
      content={
        <Form>
          <fieldset>
            <Form.Field>
              <label htmlFor="filter">Show separately</label>
            </Form.Field>
            {breakdownOptions.map(key => (
              <Form.Field key={key}>
                <Checkbox
                  radio
                  name={`${key}_checkbox`}
                  label={data[key].name}
                  checked={displaySeparately === key}
                  onChange={() => setDisplaySeparately(key)}
                />
              </Form.Field>
            ))}
            <Form.Field>
              <Button type="submit" icon labelPosition="right" onClick={() => setDisplaySeparately(null)}>Clear<Icon name="close" /></Button>
            </Form.Field>
          </fieldset>
        </Form>
      }
      on="click"
      position="bottom right"
      style={{ zIndex: 1000 }}
    />
  );
};

const createAggregationKey = (date, granularity) => {
  switch (granularity) {
    case 'day':
      return date.toISOString().split('T')[0];
    case 'week':
      const day = date.getUTCDay();
      const diff = date.getUTCDate() - day + (day === 0 ? -6 : 1);
      const monday = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), diff));
      return monday.toISOString().split('T')[0];
    case 'month':
      return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`;
    case 'quarter':
      const quarter = Math.floor(date.getUTCMonth() / 3) + 1;
      const firstDayOfQuarter = new Date(Date.UTC(date.getUTCFullYear(), (quarter - 1) * 3, 1));
      return firstDayOfQuarter.toISOString().split('T')[0];
    case 'year':
      return date.getUTCFullYear().toString();
    default:
      return date.toISOString().split('T')[0];
  }
};



const aggregateData = (data, granularity) => {
  if (!data) return [];
  if (granularity === 'day') {
    return data;
  }

  const aggregatedSeries = data.map(series => {
    if (!series.data || series.data.length === 0) {
      return { ...series, data: [] };
    }

    const aggregatedPoints = new Map();

    series.data.forEach(point => {
      const [date, value] = point.value;

      if (!date || value === undefined) {
        return; // Skip invalid points
      }

      const key = createAggregationKey(date, granularity);

      if (!aggregatedPoints.has(key)) {
        const readableDate = createReadableDate(key, granularity);

        aggregatedPoints.set(key, {
          value: 0,
          readableDate: readableDate
        });
      }

      aggregatedPoints.get(key).value += value;
    });

    return {
      ...series,
      data: Array.from(aggregatedPoints.entries())
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([date, { value, readableDate }]) => ({
          value: [new Date(date), value],
          readableDate: readableDate
        })),
    };
  });

  return aggregatedSeries;
};

const separateAggregatedData = (aggregatedData, displaySeparately) => {
  const separatedData = new Array();
  if (!aggregatedData || aggregatedData.length === 0) return [];
  aggregatedData.data.map(point => {
    if (point[displaySeparately]) {
      Object.keys(point[displaySeparately]).forEach(displaySeparatelyKey => {
        const label = point[displaySeparately][displaySeparatelyKey].label;
        if (!separatedData.find(series => series.name === label)) {
          separatedData.push({
            name: label,
            data: [],
            type: aggregatedData.type || "line",
            valueType: aggregatedData.valueType || 'number'
          });
        }
        separatedData.find(series => series.name === label).data.push({
          key: point.date,
          value: point[displaySeparately][displaySeparatelyKey].count,
          readableDate: point.readableDate,
        });
      });
    }
  });
  return separatedData;
};

const calculateYAxisMin = (data) => {
  if (!data || data.length === 0) return 0;

  // Get all values from all series
  const allValues = data.flatMap(series =>
    series.data.map(point => point.value)
  );

  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const range = max - min;

  // If the minimum value is very close to zero, start from zero
  if (min < max * 0.01) {
    return 0;
  }

  // Calculate a minimum that's 20% below the lowest value
  const calculatedMin = Math.max(0, min - (range * 0.2));
  return calculatedMin;
};

const formatXAxisLabel = (value, granularity) => {
  // value is already a timestamp, use it directly
  const day = new Date(value).getUTCDate();
  const month = new Date(value).toLocaleString('default', { month: 'short', timeZone: 'UTC' });
  const year = new Date(value).getUTCFullYear();

  switch (granularity) {
    case 'day':
    case 'week':
      // For day and week granularities, show only month name on first of month
      if (day === 1) {
        return '{month|' + month + '}';
      }
      return '{day|' + day + '}';

    case 'month':
      return '{month|' + month + '}';

    case 'quarter':
      // We're not actually showing axis labels for quarter
      if (day === 1 && month === 'Jan') {
        return '{year|' + year + '}';
      } else if (day === 1) {
        return '{month|' + month + '}';
      } else {
        return '{day|' + day + '}';
      }

    case 'year':
      // We're not actually showing axis labels for year
      return '{year|' + year + '}';

    default:
      return '{day|' + day + '}';
  }
};

/** deprecated */
const getAxisIntervals = (granularity, aggregatedData) => {
  switch (granularity, aggregatedData) {
    case 'year':
      return [3600 * 1000 * 24 * 365, 3600 * 1000 * 24 * 365];
    case 'quarter':
      // Calculate based on data range
      if (aggregatedData.length > 0 && aggregatedData[0].data.length > 0) {
        const dates = aggregatedData[0].data.map(point => new Date(point.date).getTime());
        const minDate = Math.min(...dates);
        const maxDate = Math.max(...dates);
        const quarterInMs = 3600 * 1000 * 24 * 90; // 90 days in milliseconds
        const numQuarters = Math.ceil((maxDate - minDate) / quarterInMs);
        // If we have more than 12 quarters, show every 2nd quarter
        const interval = numQuarters > 12 ? quarterInMs * 2 : quarterInMs;
        return [interval, interval];
      }
      return [3600 * 1000 * 24 * 90, 3600 * 1000 * 24 * 90];
    case 'month':
      return [3600 * 1000 * 24 * 30, undefined];
    case 'week':
      return [3600 * 1000 * 24 * 7, undefined];
    case 'day':
      return [3600 * 1000 * 24, undefined];
    default:
      return [undefined, undefined];
  }
};

/**
 * Filter chart series data by date range
 * @param {Array} chartSeries - Array of series data (either ChartDataPoint[] or SubcountSeries[])
 * @param {Object} dateRange - Date range object with start and end properties
 * @returns {Array} Filtered series data in the expected format for aggregation
 */
const filterChartSeriesByDate = (chartSeries, dateRange) => {
  if (!chartSeries || chartSeries.length === 0) {
    return [];
  }

  // Check if chartSeries is an array of ChartDataPoint objects (global case)
  // or an array of SubcountSeries objects (breakdown case)
  const isGlobalCase = chartSeries.length > 0 && !chartSeries[0].data;

  if (isGlobalCase) {
    // Global case: chartSeries is an array of ChartDataPoint objects
    // Convert to the expected series format
    return [{
      name: 'Global',
      type: 'line',
      data: chartSeries.filter(point => {
        const date = point.value[0];
        return (!dateRange.start || date >= dateRange.start) &&
               (!dateRange.end || date <= dateRange.end);
      })
    }];
  } else {
    // Breakdown case: chartSeries is an array of SubcountSeries objects
    return chartSeries.map(series => ({
      ...series,
      data: series.data.filter(point => {
        const date = point.value[0];
        return (!dateRange.start || date >= dateRange.start) &&
               (!dateRange.end || date <= dateRange.end);
      }),
    }));
  }
};

const StatsChart = ({
  classnames,
  data,
  seriesSelectorOptions,
  title=undefined,
  xAxisLabel,
  yAxisLabel,
  stacked = false,
  areaStyle = false,
  height = "400px",
  showControls = true,
  showLegend = true,
  showTooltip = true,
  showGrid = true,
  showAxisLabels = true,
  showSeriesControls = true,
  gridConfig = {
    left: "40px",
    right: "40px",
    bottom: "10%",
    top: "10%",
    containLabel: true,
    clip: true
  },
  tooltipConfig = {
    trigger: "axis",
    fontSize: 16,
    formatter: function (params) {
      console.log('params in StatsChart.jsx', params);
      const readableDate = params[0].data.readableDate;
      let result = "<strong>" + readableDate + "</strong><br/>";
      params.forEach((param) => {
        result +=
          param.marker +
          " " +
          param.seriesName +
          ": " +
          formatNumber(param.data.value[1], param.data.valueType === 'filesize' ? 'filesize' : 'compact', { compactThreshold: 100_000_000 }) +
          "<br/>";
      });
      return result;
    },
  },
}) => {
  const { dateRange, granularity } = useStatsDashboard();
  const [selectedMetric, setSelectedMetric] = useState(seriesSelectorOptions?.[0]?.value);
  const [displaySeparately, setDisplaySeparately] = useState(null);
  const [chartInstance, setChartInstance] = useState(null);
  const [aggregatedData, setAggregatedData] = useState([]);

  const chartSeries = useMemo(() => {
    if (!data || !data.global) return [];
    let seriesToProcess;

    if (displaySeparately && data[displaySeparately]) {
      // Breakdown view: get the array of series for the selected metric
      seriesToProcess = data[displaySeparately][selectedMetric] || [];
    } else {
      // Global view: get the single series and wrap it in an array
      const singleSeries = data.global?.[selectedMetric];
      seriesToProcess = singleSeries ? [singleSeries] : [];
    }
    return seriesToProcess;
  }, [data, selectedMetric, displaySeparately]);

  // This effect handles data filtering and aggregation
  useEffect(() => {
    const filteredData = filterChartSeriesByDate(chartSeries, dateRange);
    const aggregatedData = aggregateData(filteredData, granularity);
    setAggregatedData(aggregatedData);
  }, [chartSeries, granularity, dateRange]);

  const [minInterval, maxInterval] = useMemo(() => getAxisIntervals(granularity, aggregatedData), [granularity, aggregatedData]);

  const selectedSeriesIndex = useMemo(() =>
    data.findIndex(series => series.name === selectedSeries),
    [data, selectedSeries]
  );

  const seriesYAxisLabel = useMemo(() =>
    SERIES_Y_AXIS_LABELS[selectedSeries] || SERIES_Y_AXIS_LABELS.default,
    [selectedSeries]
  );

  const yAxisMin = useMemo(() =>
    calculateYAxisMin(aggregatedData),
    [aggregatedData]
  );

  const chartOptions = useMemo(() => {
    const options = {
      aria: {
        enabled: true
      },
      tooltip: showTooltip ? tooltipConfig : undefined,
      legend: {
        show: displaySeparately ? true : false,
        bottom: 0,
      },
      grid: showGrid ? gridConfig : undefined,
      xAxis: {
        type: "time",
        name: showAxisLabels ? xAxisLabel : undefined,
        nameLocation: "middle",
        nameGap: 30,
        axisTick: {
          show: ['quarter', 'year'].includes(granularity) ? false : true,
          alignWithLabel: true,
          length: 8
        },
        axisLabel: {
          show: ['quarter', 'year'].includes(granularity) ? false : true,
          fontSize: 14,
          formatter: (value) => formatXAxisLabel(value, granularity),
          rich: {
            day: {
              fontSize: 14,
              lineHeight: 20
            },
            month: {
              fontSize: 14,
              lineHeight: 20,
              padding: [24, 0, 0, 0]  // Add top padding so month labels are not cut off
            },
            quarter: {
              fontSize: 14,
              lineHeight: 20
            },
            year: {
              fontSize: 14,
              lineHeight: 20,
              padding: [24, 0, 0, 0]  // Add top padding so year labels are not cut off
            }
          }
        },
        minInterval: minInterval,
        maxInterval: maxInterval,
        // min: granularity === 'quarter' ? (value) => {
        //   const date = new Date(value);
        //   const quarter = Math.floor(date.getUTCMonth() / 3) + 1;
        //   return new Date(Date.UTC(date.getUTCFullYear(), quarter * 3, 1)).getTime();
        // } : undefined,
        // max: granularity === 'quarter' ? (value) => {
        //   const date = new Date(value);
        //   const quarter = Math.floor(date.getUTCMonth() / 3) + 1;
        //   return new Date(Date.UTC(date.getUTCFullYear(), quarter * 3, 0)).getTime();
        // } : undefined,
        clip: true
      },
      yAxis: {
        type: "value",
        name: showAxisLabels ? (yAxisLabel || seriesYAxisLabel) : undefined,
        nameLocation: "middle",
        nameGap: 60,
        min: yAxisMin,
        splitLine: {
          show: true
        },
        nameTextStyle: {
          fontSize: 14,
          fontWeight: "bold"
        },
        axisLabel: {
          fontSize: 14,
          formatter: function(value) {
            return formatNumber(value, selectedSeries.name === 'New Data Volume' ? "filesize" : "compact");
          }
        }
      },
      series: displaySeparately ?
        // If displaySeparately is set, show the breakdown series
        separateAggregatedData(aggregatedData[0], displaySeparately).map((series, index) => {
          return {
            name: series.name,
              type: series.type || "line",
              stack: displaySeparately, // Use the breakdown type as the stack identifier
              data: series.data.map(point => ({
                value: [point.key, point.value],
                readableDate: point.readableDate,
                valueType: series.valueType || 'number'
              })),
              emphasis: {
                focus: "series",
              },
              label: {
                show: ['quarter', 'year'].includes(granularity) ? true : false,
                position: series.type === 'bar' ? 'inside' : 'top',
                color: series.type === 'bar' ? "#fff" : CHART_COLORS.primary[index % CHART_COLORS.primary.length][1],
                fontSize: 14,
                fontWeight: 'bold',
                formatter: (params) => {
                  return params.data.readableDate;
                }
              },
              areaStyle: series.type === 'line' ? {
                color: CHART_COLORS.secondary[index % CHART_COLORS.secondary.length][1],
                opacity: 0.7
              } : undefined,
              itemStyle: {
                color: series.type === "bar"
                  ? CHART_COLORS.secondary[index % CHART_COLORS.secondary.length][1]
                  : CHART_COLORS.primary[index % CHART_COLORS.primary.length][1]
              },
              lineStyle: {
                color: CHART_COLORS.primary[index % CHART_COLORS.primary.length][1]
              },
              clip: true,
              barWidth: '60%',
              barGap: '30%'
            }
          })
        :
        // Otherwise show the original series
        aggregatedData.map((series) => ({
          name: series.name,
          type: series.type || "line",
          stack: stacked ? "Total" : undefined,
          areaStyle: areaStyle ? {} : undefined,
          data: series.data.map(point => ({
            value: [point.date, point.value],
            readableDate: point.readableDate,
            valueType: series.valueType || 'number'
          })),
          emphasis: {
            focus: "series",
          },
          label: {
            show: ['quarter', 'year'].includes(granularity) ? true : false,
            position: series.type === 'bar' ? 'inside' : 'top',
            color: series.type === 'bar' ? "#fff" : CHART_COLORS.primary[selectedSeriesIndex % CHART_COLORS.primary.length][1],
            fontSize: 14,
            fontWeight: 'bold',
            formatter: (params) => {
              return params.data.readableDate;
            }
          },
          itemStyle: {
            color: series.type === "bar"
              ? CHART_COLORS.secondary[selectedSeriesIndex % CHART_COLORS.secondary.length][1]
              : CHART_COLORS.primary[selectedSeriesIndex % CHART_COLORS.primary.length][1]
          },
          lineStyle: {
            color: CHART_COLORS.primary[selectedSeriesIndex % CHART_COLORS.primary.length][1]
          },
          areaStyle: areaStyle ? {
            color: CHART_COLORS.primary[selectedSeriesIndex % CHART_COLORS.primary.length][1],
            opacity: 0.3
          } : undefined,
          clip: true,
          barWidth: '60%',
          barGap: '30%'
        })),
    };

    console.log('Chart options:', options);
    return options;
  }, [
    showTooltip,
    tooltipConfig,
    showGrid,
    gridConfig,
    showAxisLabels,
    xAxisLabel,
    yAxisLabel,
    seriesYAxisLabel,
    stacked,
    areaStyle,
    aggregatedData,
    selectedSeriesIndex,
    yAxisMin,
    granularity,
    displaySeparately
  ]);

  const onChartReady = (instance) => {
    setChartInstance(instance);
  };

  useEffect(() => {
    if (chartInstance) {
      chartInstance.setOption(chartOptions);
    }
  }, [chartOptions, chartInstance]);

  return (
    <Container fluid>
      <FilterSelector data={data} displaySeparately={displaySeparately} setDisplaySeparately={setDisplaySeparately} />
      {title && (
        <Header as="h3" attached="top" fluid textAlign="center" className="rel-mt-1">
          <Header.Content>
            {title}
          </Header.Content>
          {dateRange && (
            <Header.Subheader>
              {formatDate(dateRange.start, true, true)} - {formatDate(dateRange.end, true, false)}
            </Header.Subheader>
          )}
        </Header>
      )}
      <Segment className={`stats-chart ${classnames} rel-mb-1 rel-mt-0`} attached="bottom" fluid role="region" aria-label={title || "Statistics Chart"} aria-description={`Chart showing ${selectedMetric} over time`}>
          {showControls && (
            <div className="stats-chart-controls" style={{ display: 'flex', justifyContent: 'center', marginBottom: '1rem' }}>
              {showSeriesControls && (
                <Button.Group className="stats-chart-series-controls separated">
                  {seriesSelectorOptions && seriesSelectorOptions.map((option, index) => (
                     <Button
                       key={option.value}
                       toggle
                       active={selectedMetric === option.value}
                       onClick={() => setSelectedMetric(option.value)}
                       aria-pressed={selectedMetric === option.value}
                       {...(selectedMetric === option.value && {
                         color: CHART_COLORS.primary[index % CHART_COLORS.primary.length][0],
                       })}
                     >
                       {option.text}
                     </Button>
                   ))}
                </Button.Group>
              )}
            </div>
          )}
          <div className="stats-chart-container">
            <ReactECharts
              option={chartOptions}
              style={{ height }}
              onChartReady={onChartReady}
              aria-label={title || "Statistics Chart"}
              aria-description={`Chart showing ${selectedMetric} over time`}
            />
          </div>
      </Segment>
    </Container>
  );
};

StatsChart.propTypes = {
  data: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      data: PropTypes.arrayOf(PropTypes.array).isRequired,
    })
  ).isRequired,
  title: PropTypes.string,
  xAxisLabel: PropTypes.string,
  yAxisLabel: PropTypes.string,
  stacked: PropTypes.bool,
  areaStyle: PropTypes.bool,
  height: PropTypes.string,
  showControls: PropTypes.bool,
  showLegend: PropTypes.bool,
  showTooltip: PropTypes.bool,
  showGrid: PropTypes.bool,
  showAxisLabels: PropTypes.bool,
  showSeriesControls: PropTypes.bool,
  gridConfig: PropTypes.object,
  tooltipConfig: PropTypes.object,
  seriesSelectorOptions: PropTypes.arrayOf(
    PropTypes.shape({
      value: PropTypes.string.isRequired,
      text: PropTypes.string.isRequired,
      valueType: PropTypes.string,
    })
  ),
};

export { StatsChart };
