import { filterSeriesArrayByDate } from "./filters";
import { readableGranularDate } from "./dates";
import { extractLocalizedLabel } from "../api/dataTransformer";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";

/**
 * ChartDataAggregator class handles all data aggregation and processing for charts
 */
export class ChartDataAggregator {
  /**
   * Creates a date object for readable labels from an aggregation key
   */
  static createDateForReadable(key, granularity) {
    if (granularity === "quarter") {
      const [year, quarter] = key.split("-");
      const month = (parseInt(quarter) - 1) * 3; // Q1=Jan(0), Q2=Apr(3), Q3=Jul(6), Q4=Oct(9)
      return new Date(parseInt(year), month, 1);
    } else if (granularity === "year") {
      return new Date(parseInt(key), 0, 1);
    } else if (granularity === "month") {
      const [year, month] = key.split("-");
      return new Date(parseInt(year), parseInt(month) - 1, 1);
    } else {
      // For day and week, key is already a proper date string
      return key;
    }
  }

  /**
   * Creates a chart date object from an aggregation key
   */
  static createChartDate(key, granularity) {
    if (granularity === "quarter") {
      const [year, quarter] = key.split("-");
      const month = (parseInt(quarter) - 1) * 3; // Q1=Jan(0), Q2=Apr(3), Q3=Jul(6), Q4=Oct(9)
      return new Date(parseInt(year), month, 1);
    } else if (granularity === "month") {
      const [year, month] = key.split("-");
      return new Date(parseInt(year), parseInt(month) - 1, 1);
    } else if (granularity === "year") {
      return new Date(parseInt(key), 0, 1);
    } else {
      // week and day use ISO date strings
      return new Date(key);
    }
  }

  /**
   * Creates an aggregation key from a date based on granularity
   */
  static createAggregationKey(date, granularity) {
    const d = new Date(date);
    switch (granularity) {
      case "year":
        return d.getFullYear().toString();
      case "quarter":
        const quarter = Math.floor(d.getMonth() / 3) + 1;
        return `${d.getFullYear()}-${quarter}`;
      case "month":
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
      case "week":
        // Get the Monday of the week
        const monday = new Date(d);
        monday.setDate(d.getDate() - d.getDay() + 1);
        return monday.toISOString().split("T")[0];
      case "day":
      default:
        return date.toISOString().split("T")[0];
    }
  }

  /**
   * Aggregates a single series based on granularity and cumulative/delta logic
   */
  static aggregateSingleSeries(series, granularity, isCumulative) {
    if (!series.data || series.data.length === 0) {
      return { ...series, data: [] };
    }

    const aggregatedPoints = new Map();

    series.data.forEach((point) => {
      const [date, value] = point.value;

      if (!date || value === undefined) {
        return; // Skip invalid points
      }

      const key = this.createAggregationKey(date, granularity);

      if (!aggregatedPoints.has(key)) {
        const dateForReadable = this.createDateForReadable(key, granularity);
        const readableDate = readableGranularDate(dateForReadable, granularity);
        aggregatedPoints.set(key, {
          value: value,
          readableDate: readableDate,
          lastDate: date,
        });
      } else {
        const current = aggregatedPoints.get(key);
        if (isCumulative) {
          // For cumulative data, take the last value of each time period
          const currentDate = current.lastDate instanceof Date ? current.lastDate : new Date(current.lastDate);
          const pointDate = date instanceof Date ? date : new Date(date);
          if (pointDate > currentDate) {
            current.value = value;
            current.lastDate = date;
          }
        } else {
          // For delta data, sum the values within each aggregation period
          current.value += value;
        }
      }
    });

    return {
      ...series,
      data: Array.from(aggregatedPoints.entries())
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, { value, readableDate }]) => {
          const chartDate = this.createChartDate(key, granularity);
          return {
            value: [chartDate, value],
            readableDate: readableDate,
            valueType: series.valueType || "number",
          };
        }),
    };
  }

  /**
   * Ensures all series have data points for the same time periods
   */
  static alignSeriesTimePeriods(aggregatedSeries, granularity, isCumulative) {
    if (aggregatedSeries.length <= 1) return aggregatedSeries;

    // Collect all unique time periods across all series
    const allTimePeriods = new Set();
    aggregatedSeries.forEach(series => {
      if (series.data) {
        series.data.forEach(point => {
          allTimePeriods.add(point.value[0].getTime());
        });
      }
    });

    // Fill in missing time periods for each series
    return aggregatedSeries.map(series => {
      if (!series.data) return series;

      const existingTimePoints = new Set(series.data.map(p => p.value[0].getTime()));
      const missingTimePoints = Array.from(allTimePeriods).filter(timePoint =>
        !existingTimePoints.has(timePoint)
      );

      // Add values for missing time points
      const filledData = [...series.data];
      missingTimePoints.forEach(timePoint => {
        const missingDate = new Date(timePoint);
        const readableDate = readableGranularDate(missingDate, granularity);

        let fillValue = 0;
        if (isCumulative) {
          // For cumulative data, find the last known value before this time point
          const sortedExistingData = series.data.sort((a, b) => a.value[0].getTime() - b.value[0].getTime());
          const lastKnownValue = sortedExistingData
            .filter(p => p.value[0].getTime() < timePoint)
            .pop();
          fillValue = lastKnownValue ? lastKnownValue.value[1] : 0;
        }

        filledData.push({
          value: [missingDate, fillValue],
          readableDate: readableDate,
          valueType: series.valueType || "number",
        });
      });

      // Sort by date to maintain chronological order
      filledData.sort((a, b) => a.value[0].getTime() - b.value[0].getTime());

      return {
        ...series,
        data: filledData
      };
    });
  }

  /**
   * Main aggregation function that processes data based on granularity
   */
  static aggregateData(data, granularity, isSubcounts = false, isCumulative = false) {
    if (!data) return [];
    if (granularity === "day") {
      return data;
    }

    // First pass: aggregate each series individually
    const aggregatedSeries = data.map(series => this.aggregateSingleSeries(series, granularity, isCumulative));

    console.log("AggregatedSeries:", aggregatedSeries);

    // Debug logging for quarter aggregation issues
    if (granularity === "quarter") {
      console.log("Quarter aggregation debug:");
      aggregatedSeries.forEach((series, index) => {
        console.log(
          `Series ${index} (${series.name}):`,
          series.data.map((point) => ({
            date: point.value[0],
            value: point.value[1],
            readableDate: point.readableDate,
          })),
        );
      });
    }

    // Second pass: align time periods across all series
    const alignedSeries = this.alignSeriesTimePeriods(aggregatedSeries, granularity, isCumulative);

    console.log("AlignedSeries:", alignedSeries);
    return alignedSeries;
  }
}

/**
 * Calculates the minimum value for the y-axis
 */
export const calculateYAxisMin = (data) => {
  if (!data || data.length === 0) return 0;

  const allValues = data.flatMap(
    (series) => series.data.map((point) => point.value[1]), // numeric value from [date, value]
  );

  const [min, max] = [Math.min(...allValues), Math.max(...allValues)];
  const range = max - min;

  if (min < max * 0.01) {
    return 0;
  }

  // Calculate a minimum that's 20% below the lowest value
  const calculatedMin = Math.max(0, min - range * 0.2);
  return calculatedMin;
};

/**
 * Calculates the maximum value for the y-axis based on stacked values
 */
export const calculateYAxisMax = (data) => {
  if (!data || data.length === 0) return undefined;

  // Collect all unique time points across all series
  const timePoints = new Set();
  data.forEach(series => {
    if (series.data) {
      series.data.forEach(point => {
        timePoints.add(point.value[0].getTime()); // Use timestamp for comparison
      });
    }
  });

  // Calculate the maximum cumulative value at any time point
  const maxStackedValue = Math.max(
    ...Array.from(timePoints).map(timePoint => {
      // Sum all series values at this specific time point
      return data.reduce((sum, series) => {
        if (!series.data) return sum;
        const point = series.data.find(p => p.value[0].getTime() === timePoint);
        return sum + (point ? point.value[1] : 0);
      }, 0);
    })
  );

  // Add 10% padding above the maximum stacked value
  return Math.ceil(maxStackedValue * 1.1);
};

/**
 * ChartDataProcessor class handles data extraction and preparation for charts
 */
export class ChartDataProcessor {
  /**
   * Extracts series data for a specific metric from yearly data.
   *
   * @param {Array} data - Array of yearly data objects, each containing global and breakdown metrics
   * @param {string} selectedMetric - The metric to extract (e.g., 'records', 'views', 'downloads')
   * @param {string|null} displaySeparately - Breakdown category to extract from, or null for global data
   * @returns {Array} Array of series objects for the selected metric across all years
   */
  static extractSeriesForMetric(data, selectedMetric, displaySeparately) {
    if (!data || !Array.isArray(data)) return [];

    const yearlySeries = data
      .map((yearlyData) => {
        if (!yearlyData) return [];

        if (displaySeparately && yearlyData[displaySeparately]) {
          return yearlyData[displaySeparately][selectedMetric] || [];
        } else {
          return yearlyData.global?.[selectedMetric] || [];
        }
      })
      .flat(); // Combine all series from all years

    console.log("yearlySeries for metric:", yearlySeries);
    console.log("displaySeparately:", displaySeparately);
    console.log("selectedMetric:", selectedMetric);
    return yearlySeries;
  }

  /**
   * Prepares series data for chart display by merging, filtering, and naming.
   *
   * For global view (displaySeparately = null): merges multiple yearly series into a single series
   * For breakdown view (displaySeparately = category): keeps series separate for stacking
   *
   * @param {Array} seriesArray - Array of series objects extracted from yearly data
   * @param {string|null} displaySeparately - Breakdown category name or null for global view
   * @param {string} selectedMetric - The metric being displayed (used for naming)
   * @param {Object} dateRange - Date range object with start/end dates for filtering
   * @param {number|undefined} maxSeries - Optional limit on number of series to display
   * @returns {Array} Array of processed series ready for aggregation and display
   */
  static prepareDataSeries(seriesArray, displaySeparately, selectedMetric, dateRange, maxSeries = undefined) {
    // Merge series by ID to avoid duplicates
    const mergedSeries = ChartDataProcessor.mergeSeriesById(seriesArray);

    const filteredData = filterSeriesArrayByDate(mergedSeries, dateRange);
    console.log("filteredData", filteredData);

    // Debug: Check data alignment for stacking
    ChartDataProcessor.logSeriesAlignment(filteredData, displaySeparately);

    // Add names to the series based on the breakdown category or metric type
    const namedSeries = ChartDataProcessor.addSeriesNames(filteredData, displaySeparately, selectedMetric);
    console.log("namedSeries", namedSeries);

    // Limit the number of series if maxSeries is specified
    const finalSeries = ChartDataProcessor.limitSeriesByCount(namedSeries, maxSeries);

    return finalSeries;
  }

  /**
   * Merges series by ID to avoid duplicates.
   *
   * @param {Array} seriesArray - Array of series objects to merge
   * @returns {Array} Array of merged series with unique IDs
   */
  static mergeSeriesById(seriesArray) {
    const seriesById = new Map();

    seriesArray.forEach(series => {
      if (!series.id) return;

      if (seriesById.has(series.id)) {
        // Merge data from duplicate series
        const existing = seriesById.get(series.id);
        if (series.data && existing.data) {
          existing.data.push(...series.data);
        }
      } else {
        // First occurrence of this ID
        seriesById.set(series.id, {
          ...series,
          data: series.data ? [...series.data] : []
        });
      }
    });

    return Array.from(seriesById.values());
  }

  /**
   * Logs series alignment information for debugging stacking issues.
   *
   * @param {Array} series - Array of series objects to log
   * @param {string|null} displaySeparately - Whether series are displayed separately
   */
  static logSeriesAlignment(series, displaySeparately) {
    if (displaySeparately && series.length > 1) {
      console.log("Stacking debug - series data alignment:");
      series.forEach((seriesItem, index) => {
        console.log(`Series ${index} (${seriesItem.name}):`, seriesItem.data.map(p => ({
          date: p.value[0],
          value: p.value[1]
        })));
      });
    }
  }

  /**
   * Adds localized names to series based on display mode and metric.
   *
   * @param {Array} series - Array of series objects to name
   * @param {string|null} displaySeparately - Whether series are displayed separately
   * @param {string} selectedMetric - The metric being displayed
   * @returns {Array} Array of series with localized names
   */
  static addSeriesNames(series, displaySeparately, selectedMetric) {
    const currentLanguage = i18next.language || "en";

    return series.map((seriesItem, index) => {
      if (displaySeparately) {
        // For breakdown view, use the breakdown category name
        const seriesName = seriesItem.name || `Series ${index + 1}`;
        const localizedName = extractLocalizedLabel(seriesName, currentLanguage);
        return {
          ...seriesItem,
          name: localizedName,
        };
      } else {
        // For global view, use the metric name
        const seriesName = selectedMetric || `Series ${index + 1}`;
        const localizedName = extractLocalizedLabel(seriesName, currentLanguage);
        return {
          ...seriesItem,
          name: localizedName,
        };
      }
    });
  }

  /**
   * Limits the number of series by selecting the top N series by total value.
   *
   * @param {Array} series - Array of series objects to limit
   * @param {number|undefined} maxSeries - Maximum number of series to return
   * @returns {Array} Limited array of series, sorted by total value (descending)
   */
  static limitSeriesByCount(series, maxSeries) {
    if (!maxSeries || maxSeries <= 0 || series.length <= maxSeries) {
      return series;
    }

    // Sort series by total value (sum of all data points) in descending order
    const sortedSeries = series
      .map(seriesItem => {
        const totalValue = seriesItem.data?.reduce((sum, point) => sum + (point.value[1] || 0), 0) || 0;
        return { ...seriesItem, totalValue };
      })
      .sort((a, b) => b.totalValue - a.totalValue);

    // Take only the top maxSeries series
    const limitedSeries = sortedSeries.slice(0, maxSeries).map(({ totalValue, ...seriesItem }) => seriesItem);

    console.log(`Limited series from ${series.length} to ${limitedSeries.length} (maxSeries: ${maxSeries})`);

    return limitedSeries;
  }
}

/**
 * ChartFormatter class handles formatting of chart elements
 */
export class ChartFormatter {
  /**
   * Formats x-axis labels based on granularity
   */
  static formatXAxisLabel(value, granularity) {
    // value is already a timestamp, use it directly
    const day = new Date(value).getUTCDate();
    const month = new Date(value).toLocaleString("default", {
      month: "short",
      timeZone: "UTC",
    });
    const year = new Date(value).getUTCFullYear();

    switch (granularity) {
      case "day":
      case "week":
        // For day and week granularities, show only month name on first of month
        if (day === 1) {
          return "{month|" + month + "}";
        }
        return "{day|" + day + "}";

      case "month":
        return "{month|" + month + "}";

      case "quarter":
        // We're not actually showing axis labels for quarter
        if (day === 1 && month === "Jan") {
          return "{year|" + year + "}";
        } else if (day === 1) {
          return "{month|" + month + "}";
        } else {
          return "{day|" + day + "}";
        }

      case "year":
        // We're not actually showing axis labels for year
        return "{year|" + year + "}";

      default:
        return "{day|" + day + "}";
    }
  }

  /**
   * Calculates axis intervals based on granularity (deprecated)
   */
  static getAxisIntervals(granularity, aggregatedData) {
    switch (granularity) {
      case "year":
        return [3600 * 1000 * 24 * 365, 3600 * 1000 * 24 * 365];
      case "quarter":
        // Calculate based on data range
        if (aggregatedData.length > 0 && aggregatedData[0].data.length > 0) {
          const dates = aggregatedData[0].data.map((point) =>
            new Date(point.value[0]).getTime(),
          );
          const minDate = Math.min(...dates);
          const maxDate = Math.max(...dates);
          const quarterInMs = 3600 * 1000 * 24 * 90; // 90 days in milliseconds
          const numQuarters = Math.ceil((maxDate - minDate) / quarterInMs);
          // If we have more than 12 quarters, show every 2nd quarter
          const interval = numQuarters > 12 ? quarterInMs * 2 : quarterInMs;
          return [interval, interval];
        }
        return [3600 * 1000 * 24 * 90, 3600 * 1000 * 24 * 90];
      case "month":
        return [3600 * 1000 * 24 * 30, undefined];
      case "week":
        return [3600 * 1000 * 24 * 7, undefined];
      case "day":
        return [3600 * 1000 * 24, undefined];
      default:
        return [undefined, undefined];
    }
  }
}

// Convenience exports for commonly used ChartDataAggregator methods
export const aggregateData = ChartDataAggregator.aggregateData.bind(ChartDataAggregator);
export const createAggregationKey = ChartDataAggregator.createAggregationKey.bind(ChartDataAggregator);

// Convenience exports for ChartDataProcessor methods
export const extractSeriesForMetric = ChartDataProcessor.extractSeriesForMetric.bind(ChartDataProcessor);
export const prepareDataSeries = ChartDataProcessor.prepareDataSeries.bind(ChartDataProcessor);
export const mergeSeriesById = ChartDataProcessor.mergeSeriesById.bind(ChartDataProcessor);
export const logSeriesAlignment = ChartDataProcessor.logSeriesAlignment.bind(ChartDataProcessor);
export const addSeriesNames = ChartDataProcessor.addSeriesNames.bind(ChartDataProcessor);
export const limitSeriesByCount = ChartDataProcessor.limitSeriesByCount.bind(ChartDataProcessor);

// Convenience exports for ChartFormatter methods
export const formatXAxisLabel = ChartFormatter.formatXAxisLabel.bind(ChartFormatter);
export const getAxisIntervals = ChartFormatter.getAxisIntervals.bind(ChartFormatter);
