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
          const currentDate =
            current.lastDate instanceof Date
              ? current.lastDate
              : new Date(current.lastDate);
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
   * Main aggregation function that processes data based on granularity
   */
  static aggregateData(data, granularity, isCumulative = false) {
    if (!data) return [];
    if (granularity === "day") {
      return data;
    }

    const aggregatedSeries = data.map((series) =>
      this.aggregateSingleSeries(series, granularity, isCumulative),
    );

    console.log("AggregatedSeries:", aggregatedSeries);

    return aggregatedSeries;
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

  // Helper function to safely get timestamp from a value
  const getTimestamp = (value) => {
    if (value instanceof Date) {
      return value.getTime();
    }
    if (typeof value === "string" || typeof value === "number") {
      return new Date(value).getTime();
    }
    return null;
  };

  // Collect all unique time points across all series
  const timePoints = new Set();
  data.forEach((series) => {
    if (series.data) {
      series.data.forEach((point) => {
        const timestamp = getTimestamp(point.value[0]);
        if (timestamp !== null) {
          timePoints.add(timestamp);
        }
      });
    }
  });

  // Calculate the maximum cumulative value at any time point
  const maxStackedValue = Math.max(
    ...Array.from(timePoints).map((timePoint) => {
      // Sum all series values at this specific time point
      return data.reduce((sum, series) => {
        if (!series.data) return sum;
        const point = series.data.find((p) => {
          const timestamp = getTimestamp(p.value[0]);
          return timestamp === timePoint;
        });
        return sum + (point ? point.value[1] : 0);
      }, 0);
    }),
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
  static prepareDataSeries(
    seriesArray,
    displaySeparately,
    selectedMetric,
    dateRange,
    maxSeries = undefined,
    isCumulative = false,
  ) {
    // Merge series items by ID to avoid duplicates
    const mergedSeries = ChartDataProcessor.mergeSeriesById(seriesArray);

    const filteredData = filterSeriesArrayByDate(mergedSeries, dateRange);
    console.log("filteredData", filteredData);

    // Add names to the series based on the breakdown category or metric type
    const namedSeries = ChartDataProcessor.addSeriesNames(
      filteredData,
      displaySeparately,
      selectedMetric,
    );
    console.log("namedSeries", namedSeries);

    // Limit the number of series if maxSeries is specified
    const limitedSeries = ChartDataProcessor.limitSeriesByCount(
      namedSeries,
      maxSeries,
    );

    const finalSeries = ChartDataProcessor.fillMissingZeroPoints(
      limitedSeries,
      dateRange,
      isCumulative,
    );

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

    seriesArray.forEach((series) => {
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
          data: series.data ? [...series.data] : [],
        });
      }
    });

    return Array.from(seriesById.values());
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
        const localizedName = extractLocalizedLabel(
          seriesName,
          currentLanguage,
        );
        return {
          ...seriesItem,
          name: localizedName,
        };
      } else {
        // For global view, use the metric name
        const seriesName = selectedMetric || `Series ${index + 1}`;
        const localizedName = extractLocalizedLabel(
          seriesName,
          currentLanguage,
        );
        return {
          ...seriesItem,
          name: localizedName,
        };
      }
    });
  }

  /**
   * Fills missing zero points for delta data series within the date range
   *
   * @param {Array} series - Array of series objects to fill
   * @param {Object} dateRange - Date range object with start/end dates
   * @param {boolean} isCumulative - Whether the data is cumulative (affects fill strategy)
   * @returns {Array} Array of series with missing zero points filled
   */
  static fillMissingZeroPoints(series, dateRange, isCumulative = false) {
    if (!dateRange || !dateRange.start || !dateRange.end || isCumulative) {
      return series; // Only fill zeros for delta data with a valid date range
    }

    const startDate = new Date(dateRange.start);
    const endDate = new Date(dateRange.end);

    // Generate all possible days in the date range
    const allDays = new Set();
    const current = new Date(startDate);
    while (current <= endDate) {
      allDays.add(current.toISOString().split("T")[0]); // YYYY-MM-DD format
      current.setDate(current.getDate() + 1);
    }

    return series.map((seriesItem) => {
      const existingDays = new Set();
      if (seriesItem.data && seriesItem.data.length > 0) {
        seriesItem.data.forEach((point) => {
          const day = new Date(point.value[0]).toISOString().split("T")[0];
          existingDays.add(day);
        });
      }

      const missingDays = Array.from(allDays).filter(
        (day) => !existingDays.has(day),
      );

      // Early return if series already has complete date coverage
      if (missingDays.length === 0) {
        return seriesItem;
      }

      const filledData = seriesItem.data ? [...seriesItem.data] : [];

      missingDays.forEach((day) => {
        const missingDate = new Date(day);
        const readableDate = readableGranularDate(missingDate, "day");

        filledData.push({
          value: [missingDate, 0],
          readableDate: readableDate,
          valueType: seriesItem.valueType || "number",
        });
      });

      filledData.sort((a, b) => {
        const aTime = a.value[0] instanceof Date ? a.value[0].getTime() : new Date(a.value[0]).getTime();
        const bTime = b.value[0] instanceof Date ? b.value[0].getTime() : new Date(b.value[0]).getTime();
        return aTime - bTime;
      });

      return {
        ...seriesItem,
        data: filledData,
      };
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
      .map((seriesItem) => {
        const totalValue =
          seriesItem.data?.reduce(
            (sum, point) => sum + (point.value[1] || 0),
            0,
          ) || 0;
        return { ...seriesItem, totalValue };
      })
      .sort((a, b) => b.totalValue - a.totalValue);

    // Take only the top maxSeries series
    const limitedSeries = sortedSeries
      .slice(0, maxSeries)
      .map(({ totalValue, ...seriesItem }) => seriesItem);

    console.log(
      `Limited series from ${series.length} to ${limitedSeries.length} (maxSeries: ${maxSeries})`,
    );

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
export const aggregateData =
  ChartDataAggregator.aggregateData.bind(ChartDataAggregator);
export const createAggregationKey =
  ChartDataAggregator.createAggregationKey.bind(ChartDataAggregator);

// Convenience exports for ChartDataProcessor methods
export const extractSeriesForMetric =
  ChartDataProcessor.extractSeriesForMetric.bind(ChartDataProcessor);
export const prepareDataSeries =
  ChartDataProcessor.prepareDataSeries.bind(ChartDataProcessor);
export const mergeSeriesById =
  ChartDataProcessor.mergeSeriesById.bind(ChartDataProcessor);
export const addSeriesNames =
  ChartDataProcessor.addSeriesNames.bind(ChartDataProcessor);
export const limitSeriesByCount =
  ChartDataProcessor.limitSeriesByCount.bind(ChartDataProcessor);
export const fillMissingZeroPoints =
  ChartDataProcessor.fillMissingZeroPoints.bind(ChartDataProcessor);

// Convenience exports for ChartFormatter methods
export const formatXAxisLabel =
  ChartFormatter.formatXAxisLabel.bind(ChartFormatter);
export const getAxisIntervals =
  ChartFormatter.getAxisIntervals.bind(ChartFormatter);
