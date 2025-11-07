import { filterSeriesArrayByDate } from "./filters";
import { readableGranularDate } from "./dates";
import { extractLocalizedLabel } from "./i18n";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { getLicenseLabelForms } from "./nameTransformHelpers";
import { OTHER_IDS_BY_CATEGORY } from "../constants";

/**
 * Get the array of IDs that should be treated as "other" for a given category.
 *
 * @param {string} categoryName - The category name (e.g., "publishers", "countries")
 * @returns {string[]} Array of IDs to exclude and treat as "other"
 */
export const getOtherIdsForCategory = (categoryName) => {
  if (!categoryName) return [];
  return OTHER_IDS_BY_CATEGORY[categoryName] || [];
};

/**
 * Check if a given ID should be treated as "other" for a category.
 *
 * @param {string} categoryName - The category name
 * @param {string} id - The ID to check
 * @returns {boolean} True if the ID should be treated as "other"
 */
export const isIdTreatedAsOther = (categoryName, id) => {
  const otherIds = getOtherIdsForCategory(categoryName);
  return otherIds.includes(id);
};

/**
 * ChartDataAggregator class handles all data aggregation and processing for charts
 */
export class ChartDataAggregator {
  /**
   * Creates a date object for readable labels from an aggregation key
   * Uses UTC to avoid timezone issues
   */
  static createDateForReadable(key, granularity) {
    if (granularity === "quarter") {
      const [year, quarter] = key.split("-");
      const month = (parseInt(quarter) - 1) * 3; // Q1=Jan(0), Q2=Apr(3), Q3=Jul(6), Q4=Oct(9)
      return new Date(Date.UTC(parseInt(year), month, 1));
    } else if (granularity === "year") {
      return new Date(Date.UTC(parseInt(key), 0, 1));
    } else if (granularity === "month") {
      const [year, month] = key.split("-");
      return new Date(Date.UTC(parseInt(year), parseInt(month) - 1, 1));
    } else {
      // For day and week, key is already a proper date string
      return key;
    }
  }

  /**
   * Creates a chart date object from an aggregation key
   * Uses UTC to avoid timezone issues
   */
  static createChartDate(key, granularity) {
    if (granularity === "quarter") {
      const [year, quarter] = key.split("-");
      const month = (parseInt(quarter) - 1) * 3; // Q1=Jan(0), Q2=Apr(3), Q3=Jul(6), Q4=Oct(9)
      return new Date(Date.UTC(parseInt(year), month, 1));
    } else if (granularity === "month") {
      const [year, month] = key.split("-");
      return new Date(Date.UTC(parseInt(year), parseInt(month) - 1, 1));
    } else if (granularity === "year") {
      return new Date(Date.UTC(parseInt(key), 0, 1));
    } else {
      // week and day use ISO date strings
      return new Date(key);
    }
  }

  /**
   * Creates an aggregation key from a date based on granularity
   * Uses UTC methods to avoid timezone issues
   */
  static createAggregationKey(date, granularity) {
    const d = new Date(date);
    switch (granularity) {
      case "year":
        return d.getUTCFullYear().toString();
      case "quarter":
        const quarter = Math.floor(d.getUTCMonth() / 3) + 1;
        return `${d.getUTCFullYear()}-${quarter}`;
      case "month":
        return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
      case "week":
        // Get the Monday of the week in UTC
        const monday = new Date(d);
        const dayOfWeek = monday.getUTCDay();
        const daysFromMonday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
        monday.setUTCDate(monday.getUTCDate() + daysFromMonday);
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
 * Calculates the maximum value for the y-axis based on stacked values or individual series
 */
export const calculateYAxisMax = (data, isStacked = true) => {
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

  if (isStacked) {
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
  } else {
    // For overlapping mode, find the maximum individual value across all series
    const allValues = data.flatMap(
      (series) => series.data?.map((point) => point.value[1]) || [],
    );

    if (allValues.length === 0) return undefined;

    const maxValue = Math.max(...allValues);
    // Add 10% padding above the maximum individual value
    return Math.ceil(maxValue * 1.1);
  }
};

/**
 * Helper function to filter out series with only zero values
 *
 * @param {Array} seriesArray - Array of series objects to filter
 * @returns {Array} Array of series that have at least one non-zero value
 */
const filterNonZeroSeries = (seriesArray) => {
  return seriesArray.filter(series => {
    if (!series.data || !Array.isArray(series.data)) return false;
    return series.data.some(point => (point.value[1] || 0) > 0);
  });
};

/**
 * Helper function to select the top N series based on total value
 *
 * @param {Array} seriesArray - Array of series objects to filter
 * @param {number} maxSeries - Maximum number of series to return
 * @param {boolean} isCumulative - Whether data is cumulative/snapshot (affects ranking calculation)
 * @returns {Array} Array of top N series by total value
 */
const selectTopSeries = (seriesArray, maxSeries, isCumulative = false) => {
  const seriesWithTotals = seriesArray.map(series => {
    if (!series.data || series.data.length === 0) {
      return { ...series, totalValue: 0 };
    }

    let totalValue;
    if (isCumulative) {
      // For cumulative data, use the latest value
      totalValue = series.data[series.data.length - 1]?.value?.[1] || 0;
    } else {
      // For delta data, sum all data points
      totalValue = series.data.reduce((sum, point) => sum + (point.value[1] || 0), 0);
    }
    return { ...series, totalValue };
  });

  const sortedSeries = seriesWithTotals.sort((a, b) => b.totalValue - a.totalValue);

  return sortedSeries.slice(0, maxSeries).map(({ totalValue, ...series }) => series);
};

/**
 * Helper function to calculate "other" series by subtracting visible series totals from global totals
 *
 * @param {Array} data - Array of yearly data objects
 * @param {string} selectedMetric - The metric to calculate "other" for
 * @param {string} displaySeparately - The breakdown category being displayed
 * @param {Array} visibleSeries - Array of series that will be displayed
 * @param {Object} dateRange - Date range for filtering
 * @param {boolean} isCumulative - Whether data is cumulative
 * @returns {Object|null} "Other" series object or null if not needed
 */
const calculateOtherSeries = (data, selectedMetric, displaySeparately, visibleSeries, dateRange, isCumulative) => {
  if (!data || !Array.isArray(data) || !displaySeparately || !visibleSeries || visibleSeries.length === 0) {
    return null;
  }

  const globalSeries = data
    .map((yearlyData) => yearlyData?.global?.[selectedMetric] || [])
    .flat();
  if (globalSeries.length === 0) {
    return null;
  }

  const mergedGlobalSeries = ChartDataProcessor.mergeSeriesById(globalSeries);
  if (mergedGlobalSeries.length === 0) {
    return null;
  }

  // Use the first global series as our reference
  const globalSeriesData = mergedGlobalSeries[0];

  if (!globalSeriesData || !globalSeriesData.data || globalSeriesData.data.length === 0) {
    return null;
  }

  // Filter global series by date range (always get all data points, not just latest)
  const filteredGlobalSeries = filterSeriesArrayByDate([globalSeriesData], dateRange, false);

  if (filteredGlobalSeries.length === 0 || !filteredGlobalSeries[0].data) {
    return null;
  }

  let globalDataPoints = filteredGlobalSeries[0].data;

  // Get IDs that should be treated as "other" for this category
  const otherIds = getOtherIdsForCategory(displaySeparately);

  // Subtract values for IDs that should be treated as "other" from global totals
  if (otherIds.length > 0) {
    // Get all series from breakdown data (including those that should be treated as "other")
    const allBreakdownSeries = data
      .map((yearlyData) => yearlyData?.[displaySeparately]?.[selectedMetric] || [])
      .flat();

    const mergedBreakdownSeries = ChartDataProcessor.mergeSeriesById(allBreakdownSeries);

    // Create a combined map of all "other" ID values by date
    const otherValuesByDate = new Map();

    // Process each ID that should be treated as "other"
    otherIds.forEach(otherId => {
      const otherSeries = mergedBreakdownSeries.find(series => series.id === otherId);

      if (otherSeries && otherSeries.data) {
        // Filter series by date range
        const filteredOtherSeries = filterSeriesArrayByDate([otherSeries], dateRange, false);

        if (filteredOtherSeries.length > 0 && filteredOtherSeries[0].data) {
          // Add values to the combined map
          filteredOtherSeries[0].data.forEach(point => {
            const dateKey = point.value[0].getTime ? point.value[0].getTime() : new Date(point.value[0]).getTime();
            const currentValue = otherValuesByDate.get(dateKey) || 0;
            otherValuesByDate.set(dateKey, currentValue + (point.value[1] || 0));
          });
        }
      }
    });

    // Subtract combined "other" values from global data points
    if (otherValuesByDate.size > 0) {
      globalDataPoints = globalDataPoints.map(point => {
        const dateKey = point.value[0].getTime ? point.value[0].getTime() : new Date(point.value[0]).getTime();
        const otherValue = otherValuesByDate.get(dateKey) || 0;
        return {
          ...point,
          value: [point.value[0], Math.max(0, point.value[1] - otherValue)],
        };
      });
    }
  }

  // Create a map of visible series values by date for efficient lookup
  const visibleSeriesValuesByDate = new Map();
  visibleSeries.forEach(series => {
    if (series.data && Array.isArray(series.data)) {
      series.data.forEach(point => {
        const dateKey = point.value[0].getTime ? point.value[0].getTime() : new Date(point.value[0]).getTime();
        const currentValue = visibleSeriesValuesByDate.get(dateKey) || 0;
        visibleSeriesValuesByDate.set(dateKey, currentValue + (point.value[1] || 0));
      });
    }
  });

  // Calculate "other" values by subtracting visible series totals from adjusted global totals
  // IDs configured as "other" have already been subtracted from global
  const otherDataPoints = globalDataPoints.map(point => {
    const dateKey = point.value[0].getTime ? point.value[0].getTime() : new Date(point.value[0]).getTime();
    const adjustedGlobalValue = point.value[1] || 0;
    const visibleSeriesTotal = visibleSeriesValuesByDate.get(dateKey) || 0;

    // "Other" = Adjusted Global - Visible Series
    // Adjusted Global = Global - (sum of all IDs configured as "other"), so "Other" excludes those IDs
    const otherValue = Math.max(0, adjustedGlobalValue - visibleSeriesTotal);

    return {
      value: [point.value[0], otherValue],
      readableDate: point.readableDate,
      valueType: point.valueType || "number",
    };
  });

  // Only create "other" series if there are non-zero values anywhere in the date range
  const hasNonZeroValues = otherDataPoints.some(point => point.value[1] > 0);

  if (!hasNonZeroValues) {
    return null;
  }

  return {
    id: "other",
    name: i18next.t("Other"),
    data: otherDataPoints, // Include all data points, even zero values
    type: "bar", // Default type, will be overridden by chart configuration
    valueType: globalSeriesData.valueType || "number",
  };
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
   * Sorts series data points by date within each series.
   *
   * @param {Array} seriesArray - Array of series objects to sort
   * @returns {Array} Array of series with data points sorted by date
   */
  static sortSeries(seriesArray) {
    return seriesArray.map((series) => {
      if (!series.data || !Array.isArray(series.data)) {
        return series;
      }

      const sortedData = [...series.data].sort((a, b) => {
        const aTime = a.value[0] instanceof Date ? a.value[0].getTime() : new Date(a.value[0]).getTime();
        const bTime = b.value[0] instanceof Date ? b.value[0].getTime() : new Date(b.value[0]).getTime();
        return aTime - bTime;
      });

      return {
        ...series,
        data: sortedData,
      };
    });
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
   * @param {boolean} isCumulative - Whether data is cumulative
   * @param {Array} originalData - Original yearly data array for calculating "other" series
   * @returns {Array} Array of processed series ready for aggregation and display
   */
  static prepareDataSeries(
    seriesArray,
    displaySeparately,
    selectedMetric,
    dateRange,
    maxSeries = 12,
    isCumulative = false,
    originalData = null,
  ) {
    // Merge series items by ID to avoid duplicates
    const mergedSeries = ChartDataProcessor.mergeSeriesById(seriesArray);

    // Don't pass isCumulative to filterSeriesArrayByDate
    // because we want to present data points for each time period,
    // not just the latest data point for each series
    const filteredData = filterSeriesArrayByDate(mergedSeries, dateRange, false);
    console.log("filteredData", filteredData);

    const sortedData = ChartDataProcessor.sortSeries(filteredData);

    // Add names to the series based on the breakdown category or metric type
    const namedSeries = ChartDataProcessor.addSeriesNames(
      sortedData,
      displaySeparately,
      selectedMetric,
    );
    console.log("namedSeries", namedSeries);

    // Filter out series with only zero values (applies to all series processing)
    const nonZeroSeries = filterNonZeroSeries(namedSeries);

    // Prepare series for display (with "other" series if needed)
    let displaySeries = [...nonZeroSeries];
    if (displaySeparately && originalData) {
      // Get IDs that should be treated as "other" for this category
      const otherIds = getOtherIdsForCategory(displaySeparately);

      // Filter out series with IDs that should be treated as "other"
      const seriesForSelection = otherIds.length > 0
        ? nonZeroSeries.filter(series => !otherIds.includes(series.id))
        : nonZeroSeries;

      // Select top N series for display
      // Pass isCumulative so snapshot data uses latest value instead of summing
      const visibleSeries = selectTopSeries(seriesForSelection, maxSeries, isCumulative);

      // Use only the visible series for display
      displaySeries = visibleSeries;

      // Calculate "other" series using visible series
      const otherSeries = calculateOtherSeries(
        originalData,
        selectedMetric,
        displaySeparately,
        visibleSeries,
        dateRange,
        isCumulative,
      );

      if (otherSeries) {
        const existingOtherSeries = displaySeries.find(series => series.id === "other");

        if (!existingOtherSeries) {
          // Insert "other" series at the beginning so it appears at the bottom of the stack
          displaySeries.unshift(otherSeries);
        }
      }
    }

    const finalSeries = ChartDataProcessor.fillMissingPoints(
      displaySeries,
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
        // For breakdown view, use the series name or fall back to the series ID
        const seriesName = seriesItem.name || seriesItem.id || `Series ${index + 1}`;
        const localizedName = extractLocalizedLabel(
          seriesName,
          currentLanguage,
        );

        // Apply license abbreviation for rights data
        const labelForms = displaySeparately === 'rights'
          ? getLicenseLabelForms(seriesItem.id, localizedName)
          : { short: localizedName, long: localizedName, isAbbreviated: false };

        return {
          ...seriesItem,
          name: labelForms.short,
          fullName: labelForms.long, // Store full name for tooltips
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
  static fillMissingPoints(series, dateRange, isCumulative = false) {
    if (!dateRange || !dateRange.start || !dateRange.end) {
      return series; // Only fill zeros when we have a valid date range
    }

    const startDate = new Date(dateRange.start);
    const endDate = new Date(dateRange.end);

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

      if (missingDays.length === 0) {
        return seriesItem;
      }

      const filledData = [];
      let dataPointer = 0;
      let lastValue = 0;

      for (const currentDay of allDays) {
        const currentDate = new Date(currentDay + "T00:00:00.000Z");
        const readableDate = readableGranularDate(currentDate, "day");

        let value = 0;

        while (dataPointer < seriesItem.data.length) {
          const dataPoint = seriesItem.data[dataPointer];
          const dataDay = new Date(dataPoint.value[0]).toISOString().split("T")[0];

          if (dataDay === currentDay) {
            value = dataPoint.value[1];
            lastValue = value;
            dataPointer++;
            break;
          } else if (dataDay < currentDay) {
            dataPointer++;
          } else {
            value = isCumulative ? lastValue : 0;
            break;
          }
        }

        if (dataPointer >= seriesItem.data.length) {
          value = isCumulative ? lastValue : 0;
        }

        filledData.push({
          value: [currentDate, value],
          readableDate: readableDate,
          valueType: seriesItem.valueType || "number",
        });
      }

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
export const fillMissingPoints =
  ChartDataProcessor.fillMissingPoints.bind(ChartDataProcessor);
export const sortSeries =
  ChartDataProcessor.sortSeries.bind(ChartDataProcessor);

// Convenience exports for ChartFormatter methods
export const formatXAxisLabel =
  ChartFormatter.formatXAxisLabel.bind(ChartFormatter);
export const getAxisIntervals =
  ChartFormatter.getAxisIntervals.bind(ChartFormatter);
