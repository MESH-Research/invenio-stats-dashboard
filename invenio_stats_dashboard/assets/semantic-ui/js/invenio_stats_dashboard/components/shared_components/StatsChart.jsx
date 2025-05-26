import React, { useState, useEffect, useMemo } from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { Button, Container, Header, Segment, Popup, Icon, Form, Checkbox } from 'semantic-ui-react';
import ReactECharts from "echarts-for-react";
import { useStatsDashboard } from '../../context/StatsDashboardContext';
import { CHART_COLORS } from '../../constants';
import { formatNumber } from '../../utils';
import { formatDate } from '../../utils/dates';

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

const FilterSelector = ({ displaySeparately, setDisplaySeparately }) => {
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
            <Form.Field>
              <Checkbox
                radio
                name="resource_types_checkbox"
                label="Work types"
                checked={displaySeparately === 'resourceTypes'}
                onChange={() => setDisplaySeparately('resourceTypes')}
              />
            </Form.Field>
            <Form.Field>
              <Checkbox
                radio
                label="Subject headings"
                name="subject_headings_checkbox"
                checked={displaySeparately === 'subjectHeadings'}
                onChange={() => setDisplaySeparately('subjectHeadings')}
              />
            </Form.Field>
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

const aggregateData = (data, granularity) => {
  const aggregated = data.map(series => {
    const aggregatedPoints = new Map();

    series.data.forEach(([date, value, resourceTypes, subjectHeadings]) => {
      const d = new Date(date);
      let key;

      switch (granularity) {
        case 'day':
          key = d.toISOString().split('T')[0];
          break;
        case 'week':
          // Get the Monday of the week
          const day = d.getUTCDay();
          const diff = d.getUTCDate() - day + (day === 0 ? -6 : 1);
          const monday = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), diff));
          key = monday.toISOString().split('T')[0];
          // Calculate Sunday (end of week)
          const sunday = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), diff + 6));
          break;
        case 'month':
          key = `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}`;
          break;
        case 'quarter':
          // Get the first day of the quarter (1-4)
          const quarter = Math.floor(d.getUTCMonth() / 3) + 1;
          const firstDayOfQuarter = new Date(Date.UTC(d.getUTCFullYear(), (quarter - 1) * 3, 1));
          key = firstDayOfQuarter.toISOString().split('T')[0];
          break;
        case 'year':
          key = d.getUTCFullYear().toString();
          break;
        default:
          key = d.toISOString().split('T')[0];
      }

      if (!aggregatedPoints.has(key)) {
        // Create a UTC date for the readable date
        const readableDate = new Date(key + 'T00:00:00Z').toLocaleString('default', {
          year: 'numeric',
          month: granularity === 'quarter' ? undefined : 'short',
          day: granularity === 'quarter' ? undefined : 'numeric',
          timeZone: 'UTC'
        });

        // For quarters, append the quarter number
        if (granularity === 'quarter') {
          const quarter = Math.floor(new Date(key + 'T00:00:00Z').getUTCMonth() / 3) + 1;
          aggregatedPoints.set(key, {
            value: 0,
            readableDate: `${readableDate} Q${quarter}`,
            resourceTypes: Object.fromEntries(Object.keys(resourceTypes).map(key => [key, {count: 0, label: resourceTypes[key].label}])),
            subjectHeadings: Object.fromEntries(Object.keys(subjectHeadings).map(key => [key, {count: 0, label: subjectHeadings[key].label}]))
          });
        } else if (granularity === 'week') {
          // For weeks, show the date range
          const monday = new Date(key + 'T00:00:00Z');
          const sunday = new Date(Date.UTC(monday.getUTCFullYear(), monday.getUTCMonth(), monday.getUTCDate() + 6));
          const startYear = monday.getUTCFullYear();
          const endYear = sunday.getUTCFullYear();
          aggregatedPoints.set(key, {
            value: 0,
            readableDate: `${monday.toLocaleString('default', {
              month: 'short',
              day: 'numeric',
              timeZone: 'UTC'
            })}${startYear !== endYear ? ', ' + startYear : ''} - ${sunday.toLocaleString('default', {
              month: 'short',
              day: 'numeric',
              timeZone: 'UTC'
            })}, ${endYear}`,
            resourceTypes: Object.fromEntries(Object.keys(resourceTypes).map(key => [key, {count: 0, label: resourceTypes[key].label}])),
            subjectHeadings: Object.fromEntries(Object.keys(subjectHeadings).map(key => [key, {count: 0, label: subjectHeadings[key].label}]))
          });
        } else if (granularity === 'month') {
          const date = new Date(key + 'T00:00:00Z');
          const month = date.toLocaleString('default', { month: 'long', timeZone: 'UTC' });
          const year = date.getUTCFullYear();
          aggregatedPoints.set(key, {
            value: 0,
            readableDate: `${month} ${year}`,
            resourceTypes: Object.fromEntries(Object.keys(resourceTypes).map(key => [key, {count: 0, label: resourceTypes[key].label}])),
            subjectHeadings: Object.fromEntries(Object.keys(subjectHeadings).map(key => [key, {count: 0, label: subjectHeadings[key].label}]))
          });
        } else if (granularity === 'year') {
          const year = new Date(key + 'T00:00:00Z').getUTCFullYear();
          aggregatedPoints.set(key, {
            value: 0,
            readableDate: `${year}`,
            resourceTypes: Object.fromEntries(Object.keys(resourceTypes).map(key => [key, {count: 0, label: resourceTypes[key].label}])),
            subjectHeadings: Object.fromEntries(Object.keys(subjectHeadings).map(key => [key, {count: 0, label: subjectHeadings[key].label}]))
          });
        } else {
          aggregatedPoints.set(key, {
            value: 0,
            readableDate: readableDate,
            resourceTypes: Object.fromEntries(Object.keys(resourceTypes).map(key => [key, {count: 0, label: resourceTypes[key].label}])),
            subjectHeadings: Object.fromEntries(Object.keys(subjectHeadings).map(key => [key, {count: 0, label: subjectHeadings[key].label}]))
          });
        }
      }
      aggregatedPoints.get(key).value += value;
      Object.keys(resourceTypes).forEach(resourceTypeKey => {
        if (aggregatedPoints.get(key)?.resourceTypes?.hasOwnProperty(resourceTypeKey)) {
          aggregatedPoints.get(key).resourceTypes[resourceTypeKey].count += resourceTypes[resourceTypeKey].count;
        } else {
          aggregatedPoints.get(key).resourceTypes[resourceTypeKey] = {count: resourceTypes[resourceTypeKey], label: resourceTypes[resourceTypeKey].label};
        }
      });
      Object.keys(subjectHeadings).forEach(subjectHeadingKey => {
        if (aggregatedPoints.get(key)?.subjectHeadings?.hasOwnProperty(subjectHeadingKey)) {
          aggregatedPoints.get(key).subjectHeadings[subjectHeadingKey].count += subjectHeadings[subjectHeadingKey].count;
        } else {
          aggregatedPoints.get(key).subjectHeadings[subjectHeadingKey] = {count: subjectHeadings[subjectHeadingKey], label: subjectHeadings[subjectHeadingKey].label};
        }
      });
    });

    return {
      name: series.name,
      type: series.type || "line",
      valueType: series.valueType || 'number',
      data: Array.from(aggregatedPoints.entries())
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([date, { value, readableDate, resourceTypes, subjectHeadings }]) => ({
          date: date,
          value: value,
          readableDate: readableDate,
          resourceTypes: resourceTypes,
          subjectHeadings: subjectHeadings,
        })),
    };
  });

  return aggregated;
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

const StatsChart = ({
  classnames,
  data,
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
  const { granularity, dateRange, displaySeparately, setDisplaySeparately } = useStatsDashboard();
  const [selectedSeries, setSelectedSeries] = useState(data[0]?.name || '');
  const [chartInstance, setChartInstance] = useState(null);
  console.log('data in StatsChart', data);

  const handleSeriesSelect = (seriesName) => {
    setSelectedSeries(seriesName);
  };

  const filteredData = useMemo(() =>
    data.filter(series => series.name === selectedSeries),
    [data, selectedSeries]
  );

  const aggregatedData = useMemo(() =>
    aggregateData(filteredData, granularity),
    [filteredData, granularity]
  );

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
      <FilterSelector displaySeparately={displaySeparately} setDisplaySeparately={setDisplaySeparately} />
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
      <Segment className={`stats-chart ${classnames} rel-mb-1 rel-mt-0`} attached="bottom" fluid role="region" aria-label={title || "Statistics Chart"} aria-description={`Chart showing ${selectedSeries} over time`}>
          {showControls && (
            <div className="stats-chart-controls" style={{ display: 'flex', justifyContent: 'center', marginBottom: '1rem' }}>
              {showSeriesControls && (
                <Button.Group className="stats-chart-series-controls separated">
                  {data.map((series, index) => (
                    <Button
                      key={series.name}
                      toggle
                      active={selectedSeries === series.name}
                      onClick={() => handleSeriesSelect(series.name)}
                      aria-pressed={selectedSeries === series.name}
                      {...(selectedSeries === series.name && {
                        color: CHART_COLORS.primary[index % CHART_COLORS.primary.length][0],
                      })}
                    >
                      {series.name}
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
              aria-description={`Chart showing ${selectedSeries} over time`}
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
};

export { StatsChart };
