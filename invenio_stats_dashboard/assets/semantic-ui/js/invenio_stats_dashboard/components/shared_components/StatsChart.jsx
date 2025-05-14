import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { Button, ButtonGroup, Card } from 'semantic-ui-react';
import ReactECharts from "echarts-for-react";

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
  showGranularityControls = true,
  availableGranularities = ["day", "week", "month", "year"],
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
  const [selectedSeries, setSelectedSeries] = useState(data.map(series => series.name));
  const [granularityState, setGranularityState] = useState(granularity);

  const handleSeriesToggle = (seriesName) => {
    setSelectedSeries(prev =>
      prev.includes(seriesName)
        ? prev.filter(name => name !== seriesName)
        : [...prev, seriesName]
    );
  };

  const handleGranularityChange = (newGranularity) => {
    setGranularityState(newGranularity);
  };

  const filteredData = data.filter(series => selectedSeries.includes(series.name));
  const aggregatedData = aggregateData(filteredData, granularityState);

  const option = {
    title: title ? {
      text: title,
      left: "center",
    } : undefined,
    tooltip: showTooltip ? tooltipConfig : undefined,
    legend: showLegend ? {
      data: data.map((series) => series.name),
      bottom: 0,
    } : undefined,
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
    series: aggregatedData.map((series) => ({
      name: series.name,
      type: "line",
      stack: stacked ? "Total" : undefined,
      areaStyle: areaStyle ? {} : undefined,
      data: series.data,
      emphasis: {
        focus: "series",
      },
    })),
  };

  return (
    <Card className="stats-chart" role="region" aria-label={title || "Statistics Chart"}>
      <Card.Content>
        {showControls && (
          <div className="stats-chart-controls">
            {showSeriesControls && (
              <ButtonGroup>
                {data.map(series => (
                  <Button
                    key={series.name}
                    toggle
                    active={selectedSeries.includes(series.name)}
                    onClick={() => handleSeriesToggle(series.name)}
                    aria-pressed={selectedSeries.includes(series.name)}
                  >
                    {series.name}
                  </Button>
                ))}
              </ButtonGroup>
            )}
            {showGranularityControls && (
              <ButtonGroup>
                {availableGranularities.map(gran => (
                  <Button
                    key={gran}
                    toggle
                    active={granularityState === gran}
                    onClick={() => handleGranularityChange(gran)}
                    aria-pressed={granularityState === gran}
                  >
                    {i18next.t(gran.charAt(0).toUpperCase() + gran.slice(1))}
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
            aria-description={`Chart showing ${aggregatedData.map(s => s.name).join(", ")} over time`}
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
  showGranularityControls: PropTypes.bool,
  availableGranularities: PropTypes.arrayOf(PropTypes.oneOf(["day", "week", "month", "year"])),
  gridConfig: PropTypes.object,
  tooltipConfig: PropTypes.object,
};

export { StatsChart };
