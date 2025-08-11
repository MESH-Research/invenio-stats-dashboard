import React, { useState, useEffect, useMemo } from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { Button, Container, Header, Segment, Popup, Icon, Form, Checkbox } from 'semantic-ui-react';
import ReactECharts from "echarts-for-react";
import { useStatsDashboard } from '../../context/StatsDashboardContext';
import { CHART_COLORS } from '../../constants';
import { formatNumber, filterSeriesArrayByDate } from '../../utils';
import { formatDateRange, readableGranularDate } from '../../utils/dates';

// Define y-axis labels for different series
const SERIES_Y_AXIS_LABELS = {
  'dataVolume': i18next.t('Uploaded Data Volume (GB)'),
  'default': i18next.t('Value'),
  'downloads': i18next.t('Number of Downloads'),
  'files': i18next.t('Number of Files'),
  'records': i18next.t('Number of Works'),
  'traffic': i18next.t('Downloaded Data Volume (GB)'),
  'uploaders': i18next.t('Number of Uploaders'),
  'views': i18next.t('Number of Views'),
};

// Define breakdown category names for display
const BREAKDOWN_NAMES = {
  'resourceTypes': 'Work Types',
  'subjects': 'Subjects',
  'accessStatus': 'Access Status',
  'licenses': 'Licenses',
  'affiliations': 'Affiliations',
  'funders': 'Funders',
  'countries': 'Countries',
  'referrers': 'Referrer Domains',
  'fileTypes': 'File Types',
  'languages': 'Languages',
  'periodicals': 'Periodicals',
  'publishers': 'Publishers',
  'byFilePresence': 'With/Without Files'
};

// Chart configuration constants
const CHART_CONFIG = {
  aria: {
    enabled: true
  },
  xAxis: {
    type: "time",
    nameLocation: "middle",
    nameGap: 30,
    clip: true,
    axisTick: {
      alignWithLabel: true,
      length: 8
    },
    axisLabel: {
      fontSize: 14,
      rich: {
        day: {
          fontSize: 14,
          lineHeight: 20
        },
        month: {
          fontSize: 14,
          lineHeight: 20,
          padding: [24, 0, 0, 0]
        },
        quarter: {
          fontSize: 14,
          lineHeight: 20
        },
        year: {
          fontSize: 14,
          lineHeight: 20,
          padding: [24, 0, 0, 0]
        }
      }
    }
  },
  yAxis: {
    type: "value",
    nameLocation: "middle",
    nameGap: 60,
    splitLine: {
      show: true
    },
    nameTextStyle: {
      fontSize: 14,
      fontWeight: "bold"
    },
    axisLabel: {
      fontSize: 14
    }
  },
  series: {
    label: {
      fontSize: 14,
      fontWeight: 'bold',
      formatter: (params) => params.data.readableDate
    },
    emphasis: {
      focus: "series"
    },
    barWidth: '60%',
    barGap: '30%',
    clip: true,
    areaStyle: {
      opacity: 0.7
    }
  }
};

// Grid configuration constants
const GRID_CONFIG = {
  left: "40px",
  right: "40px",
  bottom: "10%",
  top: "10%",
  containLabel: true,
  clip: true
};

// Tooltip configuration constants
const TOOLTIP_CONFIG = {
  trigger: "axis",
  fontSize: 16,
  formatter: function (params) {
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
};

// Chart configuration builder
class ChartConfigBuilder {
  constructor(config) {
    this.config = { ...config };
  }

  withTooltip(showTooltip, tooltipConfig) {
    if (showTooltip) {
      this.config.tooltip = tooltipConfig || TOOLTIP_CONFIG;
    } else {
      this.config.tooltip = undefined;
    }
    return this;
  }

  withGrid(showGrid, gridConfig) {
    if (showGrid) {
      this.config.grid = gridConfig || GRID_CONFIG;
    } else {
      this.config.grid = undefined;
    }
    return this;
  }

  withAxisLabels(showAxisLabels, xAxisLabel, yAxisLabel, seriesYAxisLabel, granularity, minXInterval, maxXInterval, yAxisMin, selectedMetric) {
    this.config.xAxis = {
      ...CHART_CONFIG.xAxis,
      name: showAxisLabels ? xAxisLabel : undefined,
      axisTick: {
        ...CHART_CONFIG.xAxis.axisTick,
        show: ['quarter', 'year'].includes(granularity) ? false : true
      },
      axisLabel: {
        ...CHART_CONFIG.xAxis.axisLabel,
        show: ['quarter', 'year'].includes(granularity) ? false : true,
        formatter: (value) => formatXAxisLabel(value, granularity)
      },
      minInterval: minXInterval,
      maxInterval: maxXInterval
    };

    this.config.yAxis = {
      ...CHART_CONFIG.yAxis,
      name: showAxisLabels ? (yAxisLabel || seriesYAxisLabel) : undefined,
      min: yAxisMin,
      axisLabel: {
        ...CHART_CONFIG.yAxis.axisLabel,
        formatter: (value) => formatNumber(value, selectedMetric === 'New Data Volume' ? "filesize" : "compact")
      }
    };

    return this;
  }

  withLegend(showLegend, displaySeparately) {
    if (displaySeparately) {
      // For breakdown view, always show legend with individual series names
      this.config.legend = {
        show: true,
        type: 'scroll', // Allow scrolling if there are many series
        orient: 'horizontal',
        bottom: 0,
        textStyle: {
          fontSize: 12
        }
      };
    } else {
      // For global view, respect the showLegend prop
      this.config.legend = {
        show: showLegend,
        bottom: 0
      };
    }
    return this;
  }

  withSeries(displaySeparately, aggregatedData, seriesColorIndex, areaStyle, granularity, stacked) {
    if (displaySeparately) {
      this.config.series = aggregatedData.map((series, index) => ({
        ...this.config.series,
        name: series.name,
        type: series.type || "line",
        stack: displaySeparately, // Use the breakdown type as the stack identifier
        data: series.data,
        label: {
          ...this.config.series.label,
          show: ['quarter', 'year'].includes(granularity) ? true : false,
          position: series.type === 'bar' ? 'inside' : 'top',
          color: series.type === 'bar' ? "#fff" : CHART_COLORS.primary[index % CHART_COLORS.primary.length][1]
        },
        areaStyle: series.type === 'line' ? {
          ...this.config.series.areaStyle,
          color: CHART_COLORS.secondary[index % CHART_COLORS.secondary.length][1]
        } : undefined,
        itemStyle: {
          color: series.type === "bar"
            ? CHART_COLORS.secondary[index % CHART_COLORS.secondary.length][1]
            : CHART_COLORS.primary[index % CHART_COLORS.primary.length][1]
        },
        lineStyle: {
          color: CHART_COLORS.primary[index % CHART_COLORS.primary.length][1]
        }
      }));
    } else {
      this.config.series = aggregatedData.map((series) => ({
        ...this.config.series,
        name: series.name,
        type: series.type || "line",
        stack: stacked ? "Total" : undefined,
        data: series.data,
        label: {
          ...this.config.series.label,
          show: ['quarter', 'year'].includes(granularity) ? true : false,
          position: series.type === 'bar' ? 'inside' : 'top',
          color: series.type === 'bar' ? "#fff" : CHART_COLORS.primary[seriesColorIndex % CHART_COLORS.primary.length][1]
        },
        itemStyle: {
          color: series.type === "bar"
            ? CHART_COLORS.secondary[seriesColorIndex % CHART_COLORS.secondary.length][1]
            : CHART_COLORS.primary[seriesColorIndex % CHART_COLORS.primary.length][1]
        },
        lineStyle: {
          color: CHART_COLORS.primary[seriesColorIndex % CHART_COLORS.primary.length][1]
        },
        areaStyle: areaStyle ? {
          ...this.config.series.areaStyle,
          color: CHART_COLORS.primary[seriesColorIndex % CHART_COLORS.primary.length][1]
        } : undefined
      }));
    }

    return this;
  }

  build() {
    return this.config;
  }
}

// Separate config for displaySeparately case (different areaStyle opacity)
const SEPARATE_CHART_CONFIG = {
  ...CHART_CONFIG,
  series: {
    ...CHART_CONFIG.series,
    areaStyle: {
      opacity: 0.3  // Different opacity for non-displaySeparately case
    }
  }
};

const FilterSelector = ({ data, displaySeparately, setDisplaySeparately }) => {
  const breakdownOptions = data ? Object.keys(data).filter(k => k !== 'global') : [];

  return (
    <Popup
      trigger={
        <Button
          name="stats-chart-filter"
          floated="right"
          size="small"
          icon={<Icon name="filter" />}
          aria-label="Stats Chart Filter"
          className="stats-chart-filter-selector rel-mt-1 rel-mr-1"
        />
      }
      content={
        <Form>
          <fieldset>
            <Form.Field>
              <label htmlFor="stats-chart-filter">Show separately</label>
            </Form.Field>
            {breakdownOptions.map(key => (
              <Form.Field key={key}>
                <Checkbox
                  radio
                  label={BREAKDOWN_NAMES[key] || key}
                  name={`${key}_checkbox`}
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
      className="stats-chart-filter-selector"
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
        const readableDate = readableGranularDate(key, granularity);

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
          readableDate: readableDate,
          valueType: series.valueType || 'number'
        })),
    };
  });

  return aggregatedSeries;
};

const calculateYAxisMin = (data) => {
  if (!data || data.length === 0) return 0;

  const allValues = data.flatMap(series =>
    series.data.map(point => point.value[1])  // numeric value from [date, value]
  );

  const [min, max] = [Math.min(...allValues), Math.max(...allValues)];
  const range = max - min;

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
  switch (granularity) {
    case 'year':
      return [3600 * 1000 * 24 * 365, 3600 * 1000 * 24 * 365];
    case 'quarter':
      // Calculate based on data range
      if (aggregatedData.length > 0 && aggregatedData[0].data.length > 0) {
        const dates = aggregatedData[0].data.map(point => new Date(point.value[0]).getTime());
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
 * Main component for rendering the stats chart
 *
 * Each property of the data object is a RecordMetrics or UsageMetrics object.
 * The data object is structured as follows:
 * {
 *   global: RecordMetrics or UsageMetrics,
 *   [breakdownCategory]: RecordMetrics or UsageMetrics
 * }
 *
 * Each RecordMetrics object has the following properties:
 * {
 *   records: DataSeries[],
 *   parents: DataSeries[],
 *   uploaders: DataSeries[],
 *   fileCount: DataSeries[],
 *   dataVolume: DataSeries[]
 * }
 *
 * Each UsageMetrics object has the following properties:
 * {
 *   views: DataSeries[],
 *   downloads: DataSeries[],
 *   visitors: DataSeries[],
 *   dataVolume: DataSeries[]
 * }
 *
 * Each DataSeries object has the following properties:
 * {
 *   id: string,
 *   name: string,
 *   data: DataPoint[],
 *   type: string,
 *   valueType: string
 * }
 *
 * Each DataPoint object has the following properties:
 * {
 *   value: [Date, number],
 *   readableDate: string,
 *   valueType: string
 * }
 *
 * @param {Object} props - Component props
 * @param {string} props.classnames - CSS class names
 * @param {Object} props.data - Chart data from transformer
 * @param {Object} props.data.global - Global RecordMetrics or UsageMetrics
 * @param {Object} props.data[breakdownCategory] - Breakdown RecordMetrics or UsageMetrics object
 * @param {Array} props.seriesSelectorOptions - Options for selecting the metric to display
 */
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
  showLegend = false,  // Always true with displaySeparately
  showTooltip = true,
  showGrid = true,
  showAxisLabels = true,
  showSeriesControls = true,
  gridConfig,
  tooltipConfig,
}) => {
  const { dateRange, granularity } = useStatsDashboard();
  const [selectedMetric, setSelectedMetric] = useState(seriesSelectorOptions?.[0]?.value);
  const [displaySeparately, setDisplaySeparately] = useState(null);

  const [aggregatedData, setAggregatedData] = useState([]);

  const seriesArray = useMemo(() => {
    if (!data || !data.global) return [];
    let seriesToProcess;

    if (displaySeparately && data[displaySeparately]) {
      // Breakdown view: get the array of series for the selected metric
      seriesToProcess = data[displaySeparately][selectedMetric] || [];
    } else {
      // Global view: get the array of series for the selected metric
      seriesToProcess = data.global?.[selectedMetric] || [];
    }
    return seriesToProcess;
  }, [data, selectedMetric, displaySeparately]);

    useEffect(() => {
    const filteredData = filterSeriesArrayByDate(seriesArray, dateRange);

    // Add names to the series based on the breakdown category or metric type
    const namedSeries = filteredData.map((series, index) => {
      if (displaySeparately) {
        // For breakdown view, use the breakdown category name
        return {
          ...series,
          name: series.name || `Series ${index + 1}`
        };
      } else {
        // For global view, use the metric name
        return {
          ...series,
          name: selectedMetric || `Series ${index + 1}`
        };
      }
    });

    const aggregatedData = aggregateData(namedSeries, granularity);
    setAggregatedData(aggregatedData);
  }, [seriesArray, granularity, dateRange, displaySeparately, selectedMetric]);

  const seriesColorIndex = useMemo(() =>
    seriesSelectorOptions?.findIndex(option => option.value === selectedMetric) || 0,
    [seriesSelectorOptions, selectedMetric]
  );

  const [minXInterval, maxXInterval] = useMemo(() => getAxisIntervals(granularity, aggregatedData), [granularity, aggregatedData]);

  const yAxisMin = useMemo(() =>
    calculateYAxisMin(aggregatedData),
    [aggregatedData]
  );

  const seriesYAxisLabel = useMemo(() =>
    SERIES_Y_AXIS_LABELS[selectedMetric] || SERIES_Y_AXIS_LABELS.default,
    [selectedMetric]
  );

  const chartOptions = useMemo(() => {
    const baseConfig = displaySeparately ? SEPARATE_CHART_CONFIG : CHART_CONFIG;

    // Build the config using the builder pattern
    const finalConfig = new ChartConfigBuilder(baseConfig)
      .withTooltip(showTooltip, tooltipConfig)
      .withGrid(showGrid, gridConfig)
      .withAxisLabels(showAxisLabels, xAxisLabel, yAxisLabel, seriesYAxisLabel, granularity, minXInterval, maxXInterval, yAxisMin, selectedMetric)
      .withLegend(showLegend, displaySeparately)
      .withSeries(displaySeparately, aggregatedData, seriesColorIndex, areaStyle, granularity, stacked)
      .build();

    const options = {
      ...finalConfig,
    };

    return options;
  }, [
    showTooltip,
    tooltipConfig,
    showGrid,
    gridConfig,
    showAxisLabels,
    showLegend,
    xAxisLabel,
    yAxisLabel,
    seriesYAxisLabel,
    stacked,
    areaStyle,
    aggregatedData,
    seriesColorIndex,
    selectedMetric,
    yAxisMin,
    granularity,
    displaySeparately
  ]);

  // ReactECharts handles option updates automatically when props change
  // No need for manual chart instance management

  return (
    <Container fluid>
      <FilterSelector data={data} aggregatedData={aggregatedData} displaySeparately={displaySeparately} setDisplaySeparately={setDisplaySeparately} />
      {title && (
        <Header as="h3" attached="top" fluid textAlign="center" className="rel-mt-1">
          <Header.Content>
            {title}
          </Header.Content>
          {dateRange && (
            <Header.Subheader>
              {formatDateRange({start: dateRange.start, "end": dateRange.end}, 'day', true)}
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
              key={`${selectedMetric}-${displaySeparately}-${granularity}`}
              option={chartOptions}
              notMerge={true}
              style={{ height }}
              aria-label={title || "Statistics Chart"}
              aria-description={`Chart showing ${selectedMetric} over time`}
            />
          </div>
      </Segment>
    </Container>
  );
};

StatsChart.propTypes = {
  data: PropTypes.shape({
    global: PropTypes.shape({
      records: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.string.isRequired,
        name: PropTypes.string.isRequired,
        data: PropTypes.arrayOf(PropTypes.shape({
          value: PropTypes.array.isRequired, // [Date, number]
          readableDate: PropTypes.string.isRequired,
          valueType: PropTypes.string.isRequired,
        })).isRequired,
        type: PropTypes.string,
        valueType: PropTypes.string,
      })),
      parents: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.string.isRequired,
        name: PropTypes.string.isRequired,
        data: PropTypes.arrayOf(PropTypes.shape({
          value: PropTypes.array.isRequired,
          readableDate: PropTypes.string.isRequired,
          valueType: PropTypes.string.isRequired,
        })).isRequired,
        type: PropTypes.string,
        valueType: PropTypes.string,
      })),
      uploaders: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.string.isRequired,
        name: PropTypes.string.isRequired,
        data: PropTypes.arrayOf(PropTypes.shape({
          value: PropTypes.array.isRequired,
          readableDate: PropTypes.string.isRequired,
          valueType: PropTypes.string.isRequired,
        })).isRequired,
        type: PropTypes.string,
        valueType: PropTypes.string,
      })),
      fileCount: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.string.isRequired,
        name: PropTypes.string.isRequired,
        data: PropTypes.arrayOf(PropTypes.shape({
          value: PropTypes.array.isRequired,
          readableDate: PropTypes.string.isRequired,
          valueType: PropTypes.string.isRequired,
        })).isRequired,
        type: PropTypes.string,
        valueType: PropTypes.string,
      })),
      dataVolume: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.string.isRequired,
        name: PropTypes.string.isRequired,
        data: PropTypes.arrayOf(PropTypes.shape({
          value: PropTypes.array.isRequired,
          readableDate: PropTypes.string.isRequired,
          valueType: PropTypes.string.isRequired,
        })).isRequired,
        type: PropTypes.string,
        valueType: PropTypes.string,
      })),
      // Usage metrics
      views: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.string.isRequired,
        name: PropTypes.string.isRequired,
        data: PropTypes.arrayOf(PropTypes.shape({
          value: PropTypes.array.isRequired,
          readableDate: PropTypes.string.isRequired,
          valueType: PropTypes.string.isRequired,
        })).isRequired,
        type: PropTypes.string,
        valueType: PropTypes.string,
      })),
      downloads: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.string.isRequired,
        name: PropTypes.string.isRequired,
        data: PropTypes.arrayOf(PropTypes.shape({
          value: PropTypes.array.isRequired,
          readableDate: PropTypes.string.isRequired,
          valueType: PropTypes.string.isRequired,
        })).isRequired,
        type: PropTypes.string,
        valueType: PropTypes.string,
      })),
      visitors: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.string.isRequired,
        name: PropTypes.string.isRequired,
        data: PropTypes.arrayOf(PropTypes.shape({
          value: PropTypes.array.isRequired,
          readableDate: PropTypes.string.isRequired,
          valueType: PropTypes.string.isRequired,
        })).isRequired,
        type: PropTypes.string,
        valueType: PropTypes.string,
      })),
    }),
    // Allow additional breakdown categories
    [PropTypes.string]: PropTypes.object,
  }),
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
