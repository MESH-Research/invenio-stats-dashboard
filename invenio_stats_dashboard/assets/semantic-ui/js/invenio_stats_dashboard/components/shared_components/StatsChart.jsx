// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React, { useState, useEffect, useMemo, useRef } from "react";
import PropTypes from "prop-types";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import {
  Button,
  Container,
  Header,
  Segment,
  Popup,
  Icon,
  Form,
  Checkbox,
  Loader,
  Message,
} from "semantic-ui-react";
import ReactECharts from "echarts-for-react";
import { useStatsDashboard } from "../../context/StatsDashboardContext";
import { CHART_COLORS, getSubcountKeyMapping } from "../../constants";
import { formatNumber, filterSeriesArrayByDate } from "../../utils";
import { formatDateRange, readableGranularDate } from "../../utils/dates";
import { extractLocalizedLabel } from "../../utils/i18n";
import {
  ChartDataAggregator,
  ChartDataProcessor,
  ChartFormatter,
  calculateYAxisMin,
  calculateYAxisMax,
} from "../../utils/chartHelpers";
import { getAvailableBreakdowns } from "../../utils/breakdownHelpers";

// Define y-axis labels for different series
const SERIES_Y_AXIS_LABELS = {
  dataVolume: i18next.t("Uploaded Data Volume (GB)"),
  default: i18next.t("Value"),
  downloads: i18next.t("Number of Downloads"),
  fileCount: i18next.t("Number of Files"),
  records: i18next.t("Number of Works"),
  traffic: i18next.t("Downloaded Data Volume (GB)"),
  uploaders: i18next.t("Number of Uploaders"),
  views: i18next.t("Number of Views"),
};

// Define breakdown category names for display
const BREAKDOWN_NAMES = {
  resourceTypes: "Top Work Types",
  subjects: "Top Subjects",
  accessStatuses: "Access Status",
  rights: "Top Rights",
  affiliations: "Top Affiliations",
  funders: "Top Funders",
  countries: "Top Countries",
  referrers: "Top Referrer Domains",
  fileTypes: "Top File Types",
  languages: "Top Languages",
  periodicals: "Top Periodicals",
  publishers: "Top Publishers",
  byFilePresence: "With/Without Files",
};

// Chart configuration constants
const CHART_CONFIG = {
  aria: {
    enabled: true,
  },
  xAxis: {
    type: "time",
    nameLocation: "middle",
    nameGap: 30,
    clip: true,
    axisTick: {
      alignWithLabel: true,
      length: 8,
    },
    axisLabel: {
      fontSize: 14,
      rich: {
        day: {
          fontSize: 14,
          lineHeight: 20,
        },
        month: {
          fontSize: 14,
          lineHeight: 20,
          padding: [24, 0, 0, 0],
        },
        quarter: {
          fontSize: 14,
          lineHeight: 20,
        },
        year: {
          fontSize: 14,
          lineHeight: 20,
          padding: [24, 0, 0, 0],
        },
      },
    },
  },
  yAxis: {
    type: "value",
    nameLocation: "middle",
    nameGap: 60,
    splitLine: {
      show: true,
    },
    nameTextStyle: {
      fontSize: 14,
      fontWeight: "bold",
    },
    axisLabel: {
      fontSize: 14,
      margin: 12,
    },
  },
  series: {
    label: {
      fontSize: 14,
      fontWeight: "bold",
      formatter: (params) => params.data.readableDate,
    },
    emphasis: {
      focus: "series",
    },
    barWidth: "60%",
    barGap: "30%",
    clip: true,
    areaStyle: {
      opacity: 0.7,
    },
  },
};

// Grid configuration constants
const GRID_CONFIG = {
  left: "80px", // Fixed width - big enough for both tick labels AND title
  right: "20px",
  // bottom: not set - let ECharts auto-calculate space for x-axis labels
  top: "10%",
  containLabel: false, // Turn off automatic adjustment to prevent y-axis title from moving
  clip: true,
};

// Tooltip configuration constants
const TOOLTIP_CONFIG = {
  trigger: "axis",
  fontSize: 16,
  formatter: function (params) {
    const readableDate = params[0].data.readableDate;
    let result = "<strong>" + readableDate + "</strong><br/>";

    // Sort params so that "other" series appears last in the tooltip
    const sortedParams = [...params].sort((a, b) => {
      const aIsOther = a.seriesName === i18next.t("Other");
      const bIsOther = b.seriesName === i18next.t("Other");

      if (aIsOther && !bIsOther) return 1;
      if (!aIsOther && bIsOther) return -1;
      return 0;
    });

    sortedParams.forEach((param) => {
      const displayName = param.data?.fullName || param.seriesName;
      const value = param.data.value[1];
      const valueType = param.data.valueType || "number";
      result +=
        param.marker +
        " " +
        displayName +
        ": " +
        formatNumber(
          value,
          valueType === "filesize" ? "filesize" : "compact",
          { compactThreshold: 100_000_000 },
        ) +
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

  withGrid(showGrid, gridConfig, valueType) {
    const gridLeft = (valueType === "filesize") ? "100px" : "80px";
    if (showGrid) {
      this.config.grid = gridConfig || {...GRID_CONFIG, left: gridLeft};
    } else {
      this.config.grid = undefined;
    }
    return this;
  }

  withAxisLabels(
    showAxisLabels,
    xAxisLabel,
    yAxisLabel,
    seriesYAxisLabel,
    granularity,
    minXInterval,
    maxXInterval,
    yAxisMin,
    yAxisMax,
    selectedMetric,
    seriesSelectorOptions,
    valueType,
  ) {
    this.config.xAxis = {
      ...CHART_CONFIG.xAxis,
      name: showAxisLabels ? xAxisLabel : undefined,
      axisTick: {
        ...CHART_CONFIG.xAxis.axisTick,
        show: ["quarter", "year"].includes(granularity) ? false : true,
      },
      axisLabel: {
        ...CHART_CONFIG.xAxis.axisLabel,
        show: ["quarter", "year"].includes(granularity) ? false : true,
        formatter: (value) =>
          ChartFormatter.formatXAxisLabel(value, granularity),
      },
      minInterval: minXInterval,
      maxInterval: maxXInterval,
    };

    this.config.yAxis = {
      ...CHART_CONFIG.yAxis,
      name: showAxisLabels ? yAxisLabel || seriesYAxisLabel : undefined,
      ...(valueType === "filesize" ? {nameGap: 80} : {}),
      min: yAxisMin,
      max: yAxisMax,
      splitLine: {
        show: false, // Disable horizontal grid lines
      },
      axisTick: {
        show: true,
        data: [yAxisMin, yAxisMax], // Explicitly set tick positions
      },
      axisLabel: {
        ...CHART_CONFIG.yAxis.axisLabel,
        formatter: (value) => {
          const valueType = valueType || 'number';

          return formatNumber(
            value,
            valueType === "filesize" ? "filesize" : "compact",
          );
        },
      },
    };

    return this;
  }

  withLegend(showLegend, displaySeparately) {
    if (displaySeparately) {
      // For breakdown view, always show legend with individual series names
      this.config.legend = {
        show: true,
        type: "scroll", // Allow scrolling if there are many series
        orient: "horizontal",
        bottom: 0,
        textStyle: {
          fontSize: 12,
        },
      };
    } else {
      // For global view, respect the showLegend prop
      this.config.legend = {
        show: showLegend,
        bottom: 0,
      };
    }
    return this;
  }

  withSeries(
    displaySeparately,
    aggregatedData,
    seriesColorIndex,
    areaStyle,
    granularity,
    stacked,
    chartType,
    isStackedLine,
  ) {
    if (displaySeparately) {
      // Helper function to determine which series should show labels
      const shouldShowLabel = (seriesIndex, allSeries) => {
        // Only show labels for quarter/year granularity
        if (!["quarter", "year"].includes(granularity)) {
          return false;
        }

        // For stacked series, only show labels on the top series (last in the array)
        // This ensures only the top of each stack shows a label
        return seriesIndex === allSeries.length - 1;
      };

      // Determine stacking behavior based on chart type
      const effectiveChartType = chartType || aggregatedData[0]?.type || "bar";
      const shouldStack = effectiveChartType === "bar"
        ? true // For bar charts: always stack by default
        : isStackedLine; // For line charts: use isStackedLine state

      this.config.series = aggregatedData.map((series, index) => {
        // Special handling for "other" series
        const isOtherSeries = series.id === "other";
        const colorIndex = isOtherSeries
          ? CHART_COLORS.secondary.length - 1 // Use last color for "other"
          : index % CHART_COLORS.secondary.length;

        return {
          ...this.config.series,
          name: series.name,
          type: chartType || series.type || "bar", // Use chartType if provided, otherwise fall back to series.type, then "bar"
          stack: shouldStack ? displaySeparately : undefined,
          data: series.data,
          label: {
            ...this.config.series.label,
            show: shouldShowLabel(index, aggregatedData),
            position: "top", // Always position labels above the series for stacked subcount
            color:
              CHART_COLORS.primary[
                seriesColorIndex % CHART_COLORS.primary.length
              ][1], // Use the same color as the metric selector button
          },
          areaStyle:
            (chartType || series.type || "bar") === "line"
              ? {
                  ...this.config.series.areaStyle,
                  color:
                    CHART_COLORS.secondary[colorIndex][1],
                  opacity: shouldStack ? 0.7 : 0, // Hide fill for overlapping lines, show for stacked
                }
              : undefined,
          itemStyle: {
            color:
              (chartType || series.type || "bar") === "bar"
                ? CHART_COLORS.secondary[colorIndex][1]
                : CHART_COLORS.primary[index % CHART_COLORS.primary.length][1],
          },
          lineStyle: {
            color: CHART_COLORS.primary[index % CHART_COLORS.primary.length][1],
          },
          emphasis: {
            focus: "series",
            areaStyle:
              !shouldStack && (chartType || series.type || "bar") === "line"
                ? {
                    opacity: 0.3, // Show fill on hover for overlapping lines
                    color:
                      CHART_COLORS.secondary[colorIndex][1],
                  }
                : undefined,
          },
        };
      });
    } else {
      const isSingleSeries = aggregatedData.length === 1;
      const effectiveChartType = chartType || aggregatedData[0]?.type || "bar";

      // Determine stacking behavior for non-displaySeparately case
      const shouldStack = effectiveChartType === "bar"
        ? true // For bar charts: always stack by default
        : stacked; // For line charts: use stacked prop

      this.config.series = aggregatedData.map((series) => ({
        ...this.config.series,
        name: series.name,
        type: chartType || series.type || "bar", // Use chartType if provided, otherwise fall back to series.type, then "bar"
        // Give single series bars a stack identifier to center them like stacked bars
        stack: shouldStack
          ? "Total"
          : isSingleSeries && effectiveChartType === "bar"
            ? "single"
            : undefined,
        data: series.data,
        label: {
          ...this.config.series.label,
          show: ["quarter", "year"].includes(granularity) ? true : false,
          position: "top",
          color: CHART_COLORS.secondary[seriesColorIndex % CHART_COLORS.secondary.length][1],
        },
        itemStyle: {
          color:
            (chartType || series.type || "bar") === "bar"
              ? CHART_COLORS.secondary[
                  seriesColorIndex % CHART_COLORS.secondary.length
                ][1]
              : CHART_COLORS.primary[
                  seriesColorIndex % CHART_COLORS.primary.length
                ][1],
        },
        lineStyle: {
          color:
            CHART_COLORS.primary[
              seriesColorIndex % CHART_COLORS.primary.length
            ][1],
        },
        areaStyle:
          areaStyle && (chartType || series.type || "bar") === "line"
            ? {
                ...this.config.series.areaStyle,
                color:
                  CHART_COLORS.primary[
                    seriesColorIndex % CHART_COLORS.primary.length
                  ][1],
              }
            : undefined,
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
      opacity: 0.3, // Different opacity for non-displaySeparately case
    },
  },
};

const FilterSelector = ({
  data,
  displaySeparately,
  setDisplaySeparately,
  display_subcounts,
  global_subcounts,
  isStackedLine,
  setIsStackedLine,
  chartType,
  dateRange,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const triggerRef = useRef(null);
  const popupRef = useRef(null);
  const clearButtonRef = useRef(null);

  // Get available breakdown options from data
  // Filter out empty subcounts and only include breakdowns from yearly blocks
  // that overlap with the selected date range
  const availableBreakdowns = getAvailableBreakdowns(data, dateRange);

  const allowedSubcounts = display_subcounts || global_subcounts || {};
  const allowedSubcountsArray = Object.keys(allowedSubcounts);
  const globalSubcountsArray = Object.keys(global_subcounts || {});
  const subcountMapping = availableBreakdowns
    ? getSubcountKeyMapping(availableBreakdowns, globalSubcountsArray)
    : {};

  const breakdownOptions = !availableBreakdowns
    ? []
    : availableBreakdowns.filter((key) => {
        // If no subcounts config is provided, show all available breakdowns
        if (!allowedSubcountsArray || allowedSubcountsArray.length === 0) {
          return true;
        }

        const backendKey = subcountMapping[key];

        return allowedSubcountsArray.includes(backendKey);
      });

  const handleClose = () => {
    setIsOpen(false);
    if (triggerRef?.current) {
      triggerRef.current.focus();
    }
  };

  // Focus the clear button when popup opens
  useEffect(() => {
    if (isOpen && clearButtonRef?.current) {
      setTimeout(() => {
        clearButtonRef.current.focus();
      }, 100);
    }
  }, [isOpen]);

  // Don't render filter if no data available
  if (!data) {
    return null;
  }

  return (
    <>
      {/* Filter Popup */}
      <Popup
        ref={popupRef}
        open={isOpen}
        onClose={handleClose}
        on="click"
        position="bottom right"
        trigger={
          <Button
            ref={triggerRef}
            name="stats-chart-filter"
            size="small"
            aria-label={i18next.t("Stats Chart Filter")}
            className="stats-chart-filter-selector"
            toggle
            onClick={() => setIsOpen(true)}
          >
            <Icon name="filter fitted" />
          </Button>
        }
        className="stats-chart-filter-selector"
      >
        <Form role="menu" aria-label={i18next.t("Filter Options")}>
          <fieldset>
            <legend className="rel-mb-1">
              <label htmlFor="stats-chart-filter">Show separately</label>
            </legend>
            {breakdownOptions.map((key) => (
              <Form.Field key={key} className="rel-mb-0">
                <Checkbox
                  radio
                  label={BREAKDOWN_NAMES[key] || key}
                  name={`${key}_checkbox`}
                  checked={displaySeparately === key}
                  onChange={() => setDisplaySeparately(key)}
                />
              </Form.Field>
            ))}
            <Form.Field className="rel-mt-1">
              <Button
                ref={clearButtonRef}
                type="submit"
                icon
                labelPosition="right"
                onClick={() => setDisplaySeparately(null)}
              >
                Clear
                <Icon name="close" />
              </Button>
            </Form.Field>
          </fieldset>
        </Form>
      </Popup>

      {/* Stack Toggle Buttons - only show for line charts with multiple series */}
      {chartType === "line" && displaySeparately && (
        <Popup
          trigger={
            <Button.Group size="small">
              <Button
                toggle
                active={isStackedLine}
                onClick={() => setIsStackedLine(true)}
                aria-label="Stacked Line Chart Selector"
                title="Stacked Line Chart Selector"
              >
                <Icon name="bars icon fitted" />
              </Button>
              <Button
                toggle
                active={!isStackedLine}
                onClick={() => setIsStackedLine(false)}
                aria-label="Overlapping Line Chart Selector"
                title="Overlapping Line Chart Selector"
              >
                <Icon name="object ungroup outline icon fitted" />
              </Button>
            </Button.Group>
          }
          content={i18next.t("Choose stacked or overlapping line chart view")}
          position="top center"
          inverted
        />
      )}
    </>
  );
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
  title = undefined,
  xAxisLabel,
  yAxisLabel,
  stacked = false,
  areaStyle = false,
  height = "400px",
  showControls = true,
  showLegend = false, // Always true with displaySeparately
  showTooltip = true,
  showGrid = true,
  showAxisLabels = true,
  showSeriesControls = true,
  gridConfig,
  tooltipConfig,
  chartType = undefined, // Optional prop to override chart type consistently
  display_subcounts = undefined, // Optional prop to override global subcounts config
  isCumulative = false, // Explicit prop to signal whether data is cumulative
  maxSeries = 12, // Maximum number of series to display (default: 12)
  defaultLineDisplay = undefined, // Optional prop to set default line display mode ("stacked" or "overlapping")
}) => {
  const { dateRange, granularity, isLoading, ui_subcounts } =
    useStatsDashboard();
  const [selectedMetric, setSelectedMetric] = useState(
    seriesSelectorOptions?.[0]?.value,
  );
  const [displaySeparately, setDisplaySeparately] = useState(null);
  const chartRef = useRef(null);

  // Determine effective default line display mode
  const getEffectiveDefaultLineDisplay = useMemo(() => {
    // If displaySeparately is set, check for per-subcount default
    if (displaySeparately && display_subcounts && display_subcounts[displaySeparately]) {
      const subcountConfig = display_subcounts[displaySeparately];
      if (subcountConfig.defaultLineDisplay) {
        return subcountConfig.defaultLineDisplay === "stacked";
      }
    }

    // Fall back to chart-level default
    if (defaultLineDisplay) {
      return defaultLineDisplay === "stacked";
    }

    // Ultimate fallback: overlapping (false)
    return false;
  }, [displaySeparately, display_subcounts, defaultLineDisplay]);

  const [isStackedLine, setIsStackedLine] = useState(getEffectiveDefaultLineDisplay);

  // Update isStackedLine when displaySeparately changes to use the new effective default
  useEffect(() => {
    setIsStackedLine(getEffectiveDefaultLineDisplay);
  }, [getEffectiveDefaultLineDisplay]);

  const [aggregatedData, setAggregatedData] = useState([]);

  const seriesArray = useMemo(() => {
    return ChartDataProcessor.extractSeriesForMetric(
      data,
      selectedMetric,
      displaySeparately,
    );
  }, [data, selectedMetric, displaySeparately]);

  // Check if there's any data to display
  const hasData = useMemo(() => {
    if (isLoading) return true; // Don't show no-data state while loading
    return (
      seriesArray.length > 0 &&
      seriesArray.some((series) => series.data && series.data.length > 0)
    );
  }, [seriesArray, isLoading]);

  useEffect(() => {
    const preparedSeries = ChartDataProcessor.prepareDataSeries(
      seriesArray,
      displaySeparately,
      selectedMetric,
      dateRange,
      maxSeries,
      isCumulative,
      data, // Pass original data for "other" series calculation
    );

    const aggregatedData = ChartDataAggregator.aggregateData(
      preparedSeries,
      granularity,
      isCumulative,
    );

    setAggregatedData(aggregatedData);
  }, [
    seriesArray,
    granularity,
    dateRange,
    displaySeparately,
    selectedMetric,
    isCumulative,
    maxSeries,
    data, // Add data to dependencies
  ]);

  const seriesColorIndex = useMemo(
    () =>
      seriesSelectorOptions?.findIndex(
        (option) => option.value === selectedMetric,
      ) || 0,
    [seriesSelectorOptions, selectedMetric],
  );

  const [minXInterval, maxXInterval] = useMemo(
    () => ChartFormatter.getAxisIntervals(granularity, aggregatedData),
    [granularity, aggregatedData],
  );

  const yAxisMin = useMemo(
    () => calculateYAxisMin(aggregatedData),
    [aggregatedData],
  );

  const yAxisMax = useMemo(
    () => {
      if (!displaySeparately) return undefined;

      // Determine if we should use stacked calculation
      const effectiveChartType = chartType || aggregatedData[0]?.type || "bar";
      const shouldStack = effectiveChartType === "bar"
        ? true // For bar charts: always stack by default
        : isStackedLine; // For line charts: use isStackedLine state

      return calculateYAxisMax(aggregatedData, shouldStack);
    },
    [aggregatedData, displaySeparately, isStackedLine, chartType, isCumulative, stacked],
  );

  const seriesYAxisLabel = useMemo(
    () => SERIES_Y_AXIS_LABELS[selectedMetric] || SERIES_Y_AXIS_LABELS.default,
    [selectedMetric],
  );

  const chartOptions = useMemo(() => {
    const baseConfig = displaySeparately ? SEPARATE_CHART_CONFIG : CHART_CONFIG;

    const finalConfig = new ChartConfigBuilder(baseConfig)
      .withTooltip(showTooltip, tooltipConfig)
      .withGrid(showGrid, gridConfig, aggregatedData[0]?.valueType)
      .withAxisLabels(
        showAxisLabels,
        xAxisLabel,
        yAxisLabel,
        seriesYAxisLabel,
        granularity,
        minXInterval,
        maxXInterval,
        yAxisMin,
        yAxisMax,
        selectedMetric,
        seriesSelectorOptions,
        aggregatedData[0]?.valueType,
      )
      .withLegend(showLegend, displaySeparately)
      .withSeries(
        displaySeparately,
        aggregatedData,
        seriesColorIndex,
        areaStyle,
        granularity,
        stacked,
        chartType,
        isStackedLine,
      )
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
    displaySeparately,
    chartType,
    isStackedLine,
  ]);

  // ReactECharts handles option updates automatically when props change
  // No need for manual chart instance management

  // Cleanup: dispose chart instance on unmount
  useEffect(() => {
    return () => {
      if (chartRef.current) {
        try {
          const chartInstance = chartRef.current.getEchartsInstance();
          if (chartInstance && !chartInstance.isDisposed()) {
            chartInstance.dispose();
          }
        } catch (error) {
          console.debug("Chart dispose error:", error);
        }
      }
    };
  }, []);

  return (
    <Container fluid>
      {title && (
        <Header
          as="h3"
          attached="top"
          fluid
          textAlign="center"
          className="rel-mt-1"
        >
          <FilterSelector
            data={data}
            aggregatedData={aggregatedData}
            displaySeparately={displaySeparately}
            setDisplaySeparately={setDisplaySeparately}
            display_subcounts={display_subcounts}
            global_subcounts={ui_subcounts}
            isStackedLine={isStackedLine}
            setIsStackedLine={setIsStackedLine}
            chartType={chartType}
            dateRange={dateRange}
          />
          <Header.Content>{title}</Header.Content>
          {dateRange && !isLoading && (
            <Header.Subheader>
              {formatDateRange(
                { start: dateRange.start, end: dateRange.end },
                "day",
                true,
              )}
            </Header.Subheader>
          )}
        </Header>
      )}
      <Segment
        className={`stats-chart ${classnames} rel-mb-1 rel-mt-0`}
        attached="bottom"
        fluid
        role="region"
        aria-label={title || "Statistics Chart"}
        aria-description={`Chart showing ${selectedMetric} over time`}
      >
        {showControls && !isLoading && (
          <div
            className="stats-chart-controls"
            style={{
              display: "flex",
              justifyContent: "center",
              marginBottom: "1rem",
            }}
          >
            {showSeriesControls && (
              <Button.Group className="stats-chart-series-controls separated">
                {seriesSelectorOptions &&
                  seriesSelectorOptions.map((option, index) => (
                    <Button
                      key={option.value}
                      toggle
                      active={selectedMetric === option.value}
                      onClick={() => setSelectedMetric(option.value)}
                      aria-pressed={selectedMetric === option.value}
                      {...(selectedMetric === option.value && {
                        color:
                          CHART_COLORS.primary[
                            index % CHART_COLORS.primary.length
                          ][0],
                      })}
                    >
                      {option.text}
                    </Button>
                  ))}
              </Button.Group>
            )}
          </div>
        )}
        <div className="stats-chart-container" style={{ height: height }}>
          {isLoading ? (
            <div className="stats-chart-loading-container">
              <Loader active size="large" />
            </div>
          ) : !hasData ? (
            <div className="stats-chart-no-data-container">
              <Message info>
                <Message.Header>
                  {i18next.t("No Data Available")}
                </Message.Header>
                <p>
                  {i18next.t(
                    "No data is available for the selected time period.",
                  )}
                </p>
              </Message>
            </div>
          ) : (
            <ReactECharts
              ref={chartRef}
              key={`${selectedMetric}-${displaySeparately}-${granularity}`}
              option={chartOptions}
              notMerge={true}
              style={{ height }}
              aria-label={title || "Statistics Chart"}
              aria-description={`Chart showing ${selectedMetric} over time`}
            />
          )}
        </div>
      </Segment>
    </Container>
  );
};

StatsChart.propTypes = {
  data: PropTypes.shape({
    global: PropTypes.shape({
      records: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.string.isRequired,
          name: PropTypes.string.isRequired,
          data: PropTypes.arrayOf(
            PropTypes.shape({
              value: PropTypes.array.isRequired, // [Date, number]
              readableDate: PropTypes.string.isRequired,
              valueType: PropTypes.string.isRequired,
            }),
          ).isRequired,
          type: PropTypes.string,
          valueType: PropTypes.string,
        }),
      ),
      parents: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.string.isRequired,
          name: PropTypes.string.isRequired,
          data: PropTypes.arrayOf(
            PropTypes.shape({
              value: PropTypes.array.isRequired,
              readableDate: PropTypes.string.isRequired,
              valueType: PropTypes.string.isRequired,
            }),
          ).isRequired,
          type: PropTypes.string,
          valueType: PropTypes.string,
        }),
      ),
      uploaders: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.string.isRequired,
          name: PropTypes.string.isRequired,
          data: PropTypes.arrayOf(
            PropTypes.shape({
              value: PropTypes.array.isRequired,
              readableDate: PropTypes.string.isRequired,
              valueType: PropTypes.string.isRequired,
            }),
          ).isRequired,
          type: PropTypes.string,
          valueType: PropTypes.string,
        }),
      ),
      fileCount: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.string.isRequired,
          name: PropTypes.string.isRequired,
          data: PropTypes.arrayOf(
            PropTypes.shape({
              value: PropTypes.array.isRequired,
              readableDate: PropTypes.string.isRequired,
              valueType: PropTypes.string.isRequired,
            }),
          ).isRequired,
          type: PropTypes.string,
          valueType: PropTypes.string,
        }),
      ),
      dataVolume: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.string.isRequired,
          name: PropTypes.string.isRequired,
          data: PropTypes.arrayOf(
            PropTypes.shape({
              value: PropTypes.array.isRequired,
              readableDate: PropTypes.string.isRequired,
              valueType: PropTypes.string.isRequired,
            }),
          ).isRequired,
          type: PropTypes.string,
          valueType: PropTypes.string,
        }),
      ),
      // Usage metrics
      views: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.string.isRequired,
          name: PropTypes.string.isRequired,
          data: PropTypes.arrayOf(
            PropTypes.shape({
              value: PropTypes.array.isRequired,
              readableDate: PropTypes.string.isRequired,
              valueType: PropTypes.string.isRequired,
            }),
          ).isRequired,
          type: PropTypes.string,
          valueType: PropTypes.string,
        }),
      ),
      downloads: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.string.isRequired,
          name: PropTypes.string.isRequired,
          data: PropTypes.arrayOf(
            PropTypes.shape({
              value: PropTypes.array.isRequired,
              readableDate: PropTypes.string.isRequired,
              valueType: PropTypes.string.isRequired,
            }),
          ).isRequired,
          type: PropTypes.string,
          valueType: PropTypes.string,
        }),
      ),
      visitors: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.string.isRequired,
          name: PropTypes.string.isRequired,
          data: PropTypes.arrayOf(
            PropTypes.shape({
              value: PropTypes.array.isRequired,
              readableDate: PropTypes.string.isRequired,
              valueType: PropTypes.string.isRequired,
            }),
          ).isRequired,
          type: PropTypes.string,
          valueType: PropTypes.string,
        }),
      ),
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
    }),
  ),
  chartType: PropTypes.oneOf(["bar", "line"]),
  display_subcounts: PropTypes.object,
  defaultLineDisplay: PropTypes.oneOf(["stacked", "overlapping"]),
};

export { StatsChart };
