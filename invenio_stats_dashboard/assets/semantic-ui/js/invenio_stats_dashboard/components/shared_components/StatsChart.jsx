import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { Button, ButtonGroup, Card } from 'semantic-ui-react';
import ReactECharts from "echarts-for-react";
import { useStatsDashboard } from '../../context/StatsDashboardContext';

// Define colors for different series
const SERIES_COLORS = [
  '#5470c6',  // Blue
  '#91cc75',  // Green
  '#fac858',  // Yellow
  '#ee6666',  // Red
  '#73c0de',  // Light Blue
  '#3ba272',  // Dark Green
  '#fc8452',  // Orange
  '#9a60b4',  // Purple
];

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
          key = new Date(d.setDate(diff)).toISOString().split('T')[0];
          break;
        case 'month':
          key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
          break;
        case 'year':
          key = d.getFullYear().toString();
          break;
        default:
          key = d.toISOString().split('T')[0];
      }

      if (!aggregatedPoints.has(key)) {
        aggregatedPoints.set(key, 0);
      }
      aggregatedPoints.set(key, aggregatedPoints.get(key) + value);
    });

    return {
      name: series.name,
      data: Array.from(aggregatedPoints.entries()).map(([date, value]) => [date, value]),
    };
  });

  return aggregated;
};

const StatsChart = ({
  classnames,
  data,
  title,
  xAxisLabel,
  yAxisLabel,
  stacked = false,
  areaStyle = false,
  granularity = "day",
  height = "400px",
  showControls = true,
  showLegend = true,
  showTooltip = true,
  showGrid = true,
  showAxisLabels = true,
  showSeriesControls = true,
  gridConfig = {
    left: "3%",
    right: "4%",
    bottom: "15%",
    top: "15%",
    containLabel: true,
  },
  tooltipConfig = {
    trigger: "axis",
    formatter: function (params) {
      let result = params[0].axisValue + "<br/>";
      params.forEach((param) => {
        result +=
          param.marker +
          " " +
          param.seriesName +
          ": " +
          param.value[1].toLocaleString() +
          "<br/>";
      });
      return result;
    },
  },
}) => {
  const [selectedSeries, setSelectedSeries] = useState(data[0]?.name || '');

  const handleSeriesSelect = (seriesName) => {
    setSelectedSeries(seriesName);
  };

  const filteredData = data.filter(series => series.name === selectedSeries);
  const aggregatedData = aggregateData(filteredData, granularity);

  const option = {
    ...(title && {
      title: {
        text: title,
        left: "center",
      }
    }),
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
      name: showAxisLabels ? yAxisLabel : undefined,
      nameLocation: "middle",
      nameGap: 40,
    },
    series: aggregatedData.map((series, index) => ({
      name: series.name,
      type: "line",
      stack: stacked ? "Total" : undefined,
      areaStyle: areaStyle ? {} : undefined,
      data: series.data,
      emphasis: {
        focus: "series",
      },
      itemStyle: {
        color: SERIES_COLORS[index % SERIES_COLORS.length]
      },
      lineStyle: {
        color: SERIES_COLORS[index % SERIES_COLORS.length]
      },
      areaStyle: areaStyle ? {
        color: SERIES_COLORS[index % SERIES_COLORS.length],
        opacity: 0.3
      } : undefined
    })),
  };

  return (
    <Card className={`stats-chart ${classnames} ml-15 mr-15`} fluid role="region" aria-label={title || "Statistics Chart"}>
      <Card.Content>
        {showControls && (
          <div className="stats-chart-controls" style={{ display: 'flex', justifyContent: 'center', marginBottom: '1rem' }}>
            {showSeriesControls && (
              <ButtonGroup>
                {data.map((series, index) => (
                  <Button
                    key={series.name}
                    toggle
                    active={selectedSeries === series.name}
                    onClick={() => handleSeriesSelect(series.name)}
                    aria-pressed={selectedSeries === series.name}
                    style={{
                      backgroundColor: selectedSeries === series.name ? SERIES_COLORS[index % SERIES_COLORS.length] : undefined,
                      color: selectedSeries === series.name ? 'white' : undefined
                    }}
                  >
                    {series.name}
                  </Button>
                ))}
              </ButtonGroup>
            )}
          </div>
        )}
        <div className="stats-chart-container">
          <ReactECharts
            option={option}
            style={{ height }}
            aria-label={title || "Statistics Chart"}
            aria-description={`Chart showing ${selectedSeries} over time`}
          />
        </div>
      </Card.Content>
    </Card>
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
  granularity: PropTypes.oneOf(["day", "week", "month", "year"]),
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
