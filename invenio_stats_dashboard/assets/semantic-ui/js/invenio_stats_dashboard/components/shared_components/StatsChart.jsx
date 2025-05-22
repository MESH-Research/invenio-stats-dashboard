import React, { useState, useEffect, useMemo } from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { Button, Container, Header, Segment } from 'semantic-ui-react';
import ReactECharts from "echarts-for-react";
import { useStatsDashboard } from '../../context/StatsDashboardContext';
import { CHART_COLORS } from '../../constants';
import { formatNumber } from '../../utils';

// Define colors for different series
const SERIES_COLORS = [
  ['red', '#b54f1e'],  // Dark Red
  ['olive', '#6c7839'],  // Dark Green
  ['yellow', '#b29017'],  // Dark Yellow
  ['blue', '#276f86'],  // Dark Teal
  ['green', '#1c4036'],  // Dark Ivy
  ['teal', '#669999'], // Verdigris
  ['purple', '#581c87'],  // Dark Purple
];

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

const formatDate = (date) => {
  // Handle quarter format
  if (date.includes('Q')) {
    const [year, quarter] = date.split('-Q');
    return `${i18next.t('Q')}${quarter} ${year}`;
  }

  // Handle month format
  if (date.match(/^\d{4}-\d{2}$/)) {
    const [year, month] = date.split('-');
    return new Intl.DateTimeFormat(i18next.language, {
      year: 'numeric',
      month: 'long'
    }).format(new Date(year, parseInt(month) - 1));
  }

  // Handle year format
  if (date.match(/^\d{4}$/)) {
    return date;
  }

  // Handle day format
  const d = new Date(date);
  return new Intl.DateTimeFormat(i18next.language, {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  }).format(d);
};

const aggregateData = (data, granularity) => {
  const aggregated = data.map(series => {
    const aggregatedPoints = new Map();

    series.data.forEach(([date, value]) => {
      const d = new Date(date);
      let key;

      switch (granularity) {
        case 'day':
          key = d.toISOString().split('T')[0];
          break;
        case 'week':
          // Get the Monday of the week
          const day = d.getDay();
          const diff = d.getDate() - day + (day === 0 ? -6 : 1);
          const monday = new Date(d.setDate(diff));
          key = monday.toISOString().split('T')[0];
          break;
        case 'month':
          key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
          break;
        case 'quarter':
          const quarter = Math.floor(d.getMonth() / 3) + 1;
          key = `${d.getFullYear()}-Q${quarter}`;
          break;
        case 'year':
          key = d.getFullYear().toString();
          break;
        default:
          key = d.toISOString().split('T')[0];
      }

      if (!aggregatedPoints.has(key)) {
        aggregatedPoints.set(key, { value: 0, readableDate: formatDate(key) });
      }
      aggregatedPoints.get(key).value += value;
    });

    return {
      name: series.name,
      type: series.type || "line",
      notMerge: true,
      data: Array.from(aggregatedPoints.entries())
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([date, { value, readableDate }]) => ({
          date: date,
          value: value,
          readableDate: readableDate
        })),
    };
  });

  return aggregated;
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
    left: "40px",  // Fixed width for y-axis label
    right: "40px", // Fixed width for right margin
    bottom: "10%",
    top: "10%",
    containLabel: true,
  },
  tooltipConfig = {
    trigger: "axis",
    formatter: function (params) {
      const readableDate = params[0].data.readableDate;
      let result = readableDate + "<br/>";
      params.forEach((param) => {
        result +=
          param.marker +
          " " +
          param.seriesName +
          ": " +
          param.data.value[1].toLocaleString() +
          "<br/>";
      });
      return result;
    },
  },
}) => {
  const { granularity } = useStatsDashboard();
  const [selectedSeries, setSelectedSeries] = useState(data[0]?.name || '');
  const [chartInstance, setChartInstance] = useState(null);

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

  const selectedSeriesIndex = useMemo(() =>
    data.findIndex(series => series.name === selectedSeries),
    [data, selectedSeries]
  );

  const seriesYAxisLabel = useMemo(() =>
    SERIES_Y_AXIS_LABELS[selectedSeries] || SERIES_Y_AXIS_LABELS.default,
    [selectedSeries]
  );

  const chartOptions = useMemo(() => ({
    aria: {
      enabled: true
    },
    tooltip: showTooltip ? tooltipConfig : undefined,
    grid: showGrid ? gridConfig : undefined,
    xAxis: {
      type: "time",
      name: showAxisLabels ? xAxisLabel : undefined,
      nameLocation: "middle",
      nameGap: 30,
    },
    yAxis: {
      type: "value",
      name: showAxisLabels ? (yAxisLabel || seriesYAxisLabel) : undefined,
      nameLocation: "middle",
      nameGap: 50,
      axisLabel: {
        formatter: function(value) {
          return formatNumber(value, selectedSeries.name === 'New Data Volume' ? "filesize" : "compact");
        }
      }
    },
    series: aggregatedData.map((series) => ({
      name: series.name,
      type: series.type || "line",
      stack: stacked ? "Total" : undefined,
      areaStyle: areaStyle ? {} : undefined,
      data: series.data.map(point => ({
        value: [point.date, point.value],
        readableDate: point.readableDate
      })),
      emphasis: {
        focus: "series",
      },
      itemStyle: {
        color: CHART_COLORS.secondary[selectedSeriesIndex % CHART_COLORS.secondary.length]
      },
      lineStyle: {
        color: CHART_COLORS.secondary[selectedSeriesIndex % CHART_COLORS.secondary.length]
      },
      areaStyle: areaStyle ? {
        color: CHART_COLORS.secondary[selectedSeriesIndex % CHART_COLORS.secondary.length],
        opacity: 0.3
      } : undefined
    })),
  }), [
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
    selectedSeriesIndex
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
      {title && (
        <Header as="h3" attached="top" fluid textAlign="center" className="rel-mt-1">
          {title}
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
                        color: CHART_COLORS.secondary[index % CHART_COLORS.secondary.length][0],
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
