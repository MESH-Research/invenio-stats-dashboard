// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import axios from "axios";
import { DASHBOARD_TYPES } from "../constants";
import { generateTestStatsData } from "../components/test_data";
import { findMissingBlocks, mergeYearlyStats } from "./yearlyBlockManager";

import { kebabToCamel } from "../utils";

/**
 * Create axios instance with proper CSRF token configuration
 */
const createAxiosWithCSRF = () => {
  return axios.create({
    withCredentials: true,
    xsrfCookieName: "csrftoken",
    xsrfHeaderName: "X-CSRFToken",
    headers: {
      "Content-Type": "application/json",
    },
  });
};

/**
 * Fetch records from the API with sorting and optional date range filtering
 * @param {string} sort - Sort parameter (e.g., 'mostviewed', 'mostdownloaded')
 * @param {number} page - Page number (default: 1)
 * @param {number} size - Page size (default: 20)
 * @param {Object} dateRange - Date range object with start and end dates
 * @param {string} dateRange.start - Start date in YYYY-MM-DD format
 * @param {string} dateRange.end - End date in YYYY-MM-DD format
 * @returns {Promise} Promise that resolves to the API response
 */
export const fetchRecords = async (sort, page = 1, size = 20, dateRange = null) => {
  try {
    let query = '';

    // Add date range filter if provided
    if (dateRange && dateRange.start && dateRange.end) {
      query = `[${dateRange.start} TO ${dateRange.end}]`;
    }

    const axiosWithCSRF = createAxiosWithCSRF();
    const response = await axiosWithCSRF.get('/api/records', {
      params: {
        q: query,
        l: 'list',
        p: page,
        s: size,
        sort: sort
      }
    });
    return response.data;
  } catch (error) {
    console.error(`Error fetching records with sort=${sort}:`, error);
    throw error;
  }
};

/**
 * Helper function to update component state with clear state names
 */
const updateState = (
  onStateChange,
  isMounted,
  stateName,
  stats,
  additionalProps = {},
) => {
  if (onStateChange && (!isMounted || isMounted())) {
    const baseState = {
      stats,
      error: null,
      ...additionalProps,
    };

    switch (stateName) {
      case "loading_started":
        onStateChange({
          ...baseState,
          isLoading: true,
          isUpdating: false,
        });
        break;
      case "data_loaded":
        onStateChange({
          ...baseState,
          isLoading: false,
          isUpdating: false,
          lastUpdated: Date.now(),
        });
        break;
      case "error":
        onStateChange({
          ...baseState,
          isLoading: false,
          isUpdating: false,
        });
        break;
      default:
        onStateChange(baseState);
    }
  }
};

/**
 * Convert API stat name to ui category name.
 *
 * @param {string} str - The API stat name to convert
 * @param {string} dateBasis - The kind of date being used to
 *   determine the search index to query for the data.
 *
 * @returns {string} The ui category name
 **/
const convertCategoryKey = (str, dateBasis) => {
  let newKey = kebabToCamel(str).replace("Category", "Data");
  if (str.startsWith("record")) {
    newKey = newKey + dateBasis.charAt(0).toUpperCase() + dateBasis.slice(1);
  }
  return newKey;
};

/**
 * API client for requesting stats to populate a stats dashboard.
 *
 * Returns a promise that resolves to an object with the following keys:
 * - record_deltas
 * - record_snapshots
 * - usage_deltas
 * - usage_snapshots
 *
 * Each property is an array of objects, each representing one day of stats.
 *
 * @param {string} communityId - The ID of the community to get stats for.
 * @param {string} dashboardType - The type of dashboard to get stats for.
 * @param {string} startDate - The start date of the stats. If not provided, the stats will begin at the earliest date in the data.
 * @param {string} endDate - The end date of the stats. If not provided, the stats will end at the current date or latest date in the data.
 * @param {string} dateBasis - The date basis for the query ("added", "created", "published"). Defaults to "added".
 *
 * @returns {Promise<Object>} - The stats data.
 */
const statsApiClient = {
  getStats: async (
    communityId,
    dashboardType,
    startDate = null,
    endDate = null,
    dateBasis = "added",
    dashboardConfig = {},
  ) => {
    if (dashboardType === DASHBOARD_TYPES.GLOBAL) {
      communityId = "global";
    }

    const statCategories = [
      "usage-snapshot-category",
      "usage-delta-category",
      "record-snapshot-category",
      "record-delta-category",
    ];

    const responses = {};
    const axiosWithCSRF = createAxiosWithCSRF();

    for (let i = 0; i < statCategories.length; i++) {
      const category = statCategories[i];

      const requestBody = {
        [`${category}`]: {
          stat: `${category}`,
          params: {
            community_id: communityId,
            date_basis: dateBasis,
          },
        },
      };
      if (startDate) {
        requestBody[`${category}`].params.start_date = startDate;
      }
      if (endDate) {
        requestBody[`${category}`].params.end_date = endDate;
      }

      // Determine Accept header based on compression setting
      const compressJson = dashboardConfig.compress_json === true; // Default to false
      const acceptHeader = compressJson
        ? "application/json+gzip"
        : "application/json";

      // Request with appropriate JSON headers and CSRF token
      const response = await axiosWithCSRF.post(
        `/api/stats-dashboard`,
        requestBody,
        {
          headers: {
            Accept: acceptHeader,
          },
        },
      );

      const newKey = convertCategoryKey(category, dateBasis);

      responses[newKey] = response.data[category];
    }
    console.log("API responses:", responses);

    return responses;
  },
};

/**
 * Fetch stats data using yearly blocks for efficient caching
 *
 * Determines which yearly blocks are already in client-side memory and which
 * still need to be loaded from the back-end in order to cover the currently
 * selected date range.
 *
 * @param {Object} params - Parameters for fetching stats
 * @param {string} params.communityId - The community ID (or 'global')
 * @param {string} params.dashboardType - The dashboard type
 * @param {Date} [params.startDate] - Start date (optional)
 * @param {Date} [params.endDate] - End date (optional)
 * @param {string} [params.dateBasis] - Date basis for the query ("added", "created", "published"). Defaults to "added".
 * @param {Array} [params.currentStats] - Array of existing yearly stats objects
 * @param {Function} [params.onStateChange] - Callback for state changes
 * @param {Function} [params.isMounted] - Function to check if component is still mounted
 * @param {boolean} [params.useTestData] - Whether to use test data instead of API
 * @param {Object} [params.dashboardConfig] - Dashboard configuration
 *
 * @returns {Promise<Object>} Object containing:
 *   - stats: Array of yearly stats objects
 *   - lastUpdated: Timestamp of data fetch
 *   - error: Error object if fetch failed
 */
const fetchStatsWithYearlyBlocks = async ({
  communityId,
  dashboardType,
  startDate = null,
  endDate = null,
  dateBasis = "added",
  currentStats = [],
  onStateChange = null,
  isMounted = null,
  dashboardConfig = {},
}) => {
  try {
    updateState(onStateChange, isMounted, "loading_started", currentStats, {
      isUpdating: currentStats.length > 0,
    });

    const missingBlocks = findMissingBlocks(startDate, endDate, currentStats);

    if (missingBlocks.length === 0) {
      updateState(onStateChange, isMounted, "data_loaded", currentStats);
      return {
        stats: currentStats,
        lastUpdated: Date.now(),
        error: null,
      };
    }

    const newYearlyStats = await Promise.all(
      missingBlocks.map(async (block) => {
        return await statsApiClient.getStats(
          communityId,
          dashboardType,
          block.startDate,
          block.endDate,
          dateBasis,
          dashboardConfig,
        );
      }),
    );

    // Add year property to each stats object
    const yearStatsWithYear = newYearlyStats.map((stats, index) => ({
      ...stats,
      year: missingBlocks[index].year,
    }));

    const updatedStats = mergeYearlyStats(currentStats, yearStatsWithYear);

    updateState(onStateChange, isMounted, "data_loaded", updatedStats);

    return {
      stats: updatedStats,
      lastUpdated: Date.now(),
      error: null,
    };
  } catch (error) {
    console.error("Error fetching stats with yearly blocks:", error);

    updateState(onStateChange, isMounted, "error", currentStats, { error });

    return {
      stats: currentStats,
      lastUpdated: null,
      error,
    };
  }
};

/**
 * Fetch stats from back-end API with local caching
 *
 * @param {Object} params - Parameters for fetching stats
 * @param {string} params.communityId - The community ID (or 'global')
 * @param {string} params.dashboardType - The dashboard type
 * @param {Date} [params.startDate] - Start date (optional)
 * @param {Date} [params.endDate] - End date (optional)
 * @param {string} [params.dateBasis] - Date basis for the query ("added", "created", "published"). Defaults to "added".
 * @param {Function} [params.onStateChange] - Callback for state changes
 * @param {Function} [params.isMounted] - Function to check if component is still mounted
 * @param {boolean} [params.useTestData] - Whether to use test data instead of API
 *
 * @returns {Promise<Object>} Object containing:
 *   - stats: Fresh data from API (transformed)
 *   - lastUpdated: Timestamp of data fetch
 *   - error: Error object if fetch failed
 */
const fetchStats = async ({
  communityId,
  dashboardType,
  startDate = null,
  endDate = null,
  dateBasis = "added",
  onStateChange = null,
  isMounted = null,
  useTestData = false,
  dashboardConfig = {},
  currentStats = [], // NEW: Array of yearly stats for yearly block system
}) => {
  try {
    // Use yearly block system for efficient caching
    if (useTestData) {
      // For test data, use legacy approach
      updateState(onStateChange, isMounted, "loading_started", currentStats);

      const rawStats = await generateTestStatsData(startDate, endDate);

      updateState(onStateChange, isMounted, "data_loaded", rawStats);

      return {
        stats: rawStats,
        lastUpdated: Date.now(),
        error: null,
      };
    } else {
      // Use yearly block system for real data
      return await fetchStatsWithYearlyBlocks({
        communityId,
        dashboardType,
        startDate,
        endDate,
        dateBasis,
        currentStats,
        onStateChange,
        isMounted,
        useTestData: false,
        dashboardConfig,
      });
    }
  } catch (error) {
    console.error("Error fetching stats:", error);

    // Set ui fetching error state
    updateState(onStateChange, isMounted, "error", currentStats, { error });

    return {
      stats: currentStats,
      lastUpdated: null,
      error,
    };
  }
};

/**
 * Serialization format constants for download requests
 */
const SERIALIZATION_FORMATS = {
  JSON: "application/json",
  JSON_GZIP: "application/json+gzip",
  JSON_BROTLI: "application/json+br",
  CSV: "text/csv",
  XML: "application/xml",
  EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
};

/**
 * Download stats series sets API client
 *
 * Downloads statistics data in various serialization formats using the current
 * UI display settings (start/end date, community, dateBasis).
 *
 * @param {string} communityId - The ID of the community to get stats for (or 'global')
 * @param {string} dashboardType - The type of dashboard (DASHBOARD_TYPES.GLOBAL or DASHBOARD_TYPES.COMMUNITY)
 * @param {string} format - Serialization format (from SERIALIZATION_FORMATS)
 * @param {string} [startDate] - Start date in YYYY-MM-DD format
 * @param {string} [endDate] - End date in YYYY-MM-DD format
 * @param {string} [dateBasis] - Date basis ("added", "created", "published"). Defaults to "added"
 *
 * @returns {Promise<Blob>} - The downloaded file as a Blob
 */
const downloadStatsSeries = async (
  communityId,
  dashboardType,
  format,
  startDate = null,
  endDate = null,
  dateBasis = "added",
) => {
  if (dashboardType === DASHBOARD_TYPES.GLOBAL) {
    communityId = "global";
  }

  // Validate format
  const validFormats = Object.values(SERIALIZATION_FORMATS);
  if (!validFormats.includes(format)) {
    throw new Error(
      `Invalid format: ${format}. Valid formats are: ${validFormats.join(", ")}`,
    );
  }

  // Build request body for category-wide queries (which return data series sets)
  const requestBody = {
    "usage-snapshot-category": {
      stat: "usage-snapshot-category",
      params: {
        community_id: communityId,
        date_basis: dateBasis,
      },
    },
    "usage-delta-category": {
      stat: "usage-delta-category",
      params: {
        community_id: communityId,
        date_basis: dateBasis,
      },
    },
    "record-snapshot-category": {
      stat: "record-snapshot-category",
      params: {
        community_id: communityId,
        date_basis: dateBasis,
      },
    },
    "record-delta-category": {
      stat: "record-delta-category",
      params: {
        community_id: communityId,
        date_basis: dateBasis,
      },
    },
  };

  if (startDate) {
    Object.values(requestBody).forEach((query) => {
      query.params.start_date = startDate;
    });
  }
  if (endDate) {
    Object.values(requestBody).forEach((query) => {
      query.params.end_date = endDate;
    });
  }

  const headers = {
    Accept: format,
  };

  try {
    const axiosWithCSRF = createAxiosWithCSRF();
    const response = await axiosWithCSRF.post(
      `/api/stats-dashboard`,
      requestBody,
      {
        headers,
        responseType: "blob", // Important for binary file downloads
      },
    );

    return response.data;
  } catch (error) {
    console.error("Error downloading stats series:", error);
    throw error;
  }
};

/**
 * Download stats series sets with automatic filename handling
 *
 * Downloads statistics data and automatically triggers a browser download
 * with an appropriate filename based on the community and format.
 *
 * @param {Object} params - Download parameters
 * @param {string} params.communityId - The ID of the community to get stats for (or 'global')
 * @param {string} params.dashboardType - The type of dashboard (DASHBOARD_TYPES.GLOBAL or DASHBOARD_TYPES.COMMUNITY)
 * @param {string} params.format - Serialization format (from SERIALIZATION_FORMATS)
 * @param {string} [params.startDate] - Start date in YYYY-MM-DD format
 * @param {string} [params.endDate] - End date in YYYY-MM-DD format
 * @param {string} [params.dateBasis] - Date basis ("added", "created", "published"). Defaults to "added"
 * @param {string} [params.filename] - Custom filename (optional, will be auto-generated if not provided)
 *
 * @returns {Promise<void>} - Triggers browser download
 */
const downloadStatsSeriesWithFilename = async ({
  communityId,
  dashboardType,
  format,
  startDate = null,
  endDate = null,
  dateBasis = "added",
  filename = null,
}) => {
  try {
    const blob = await downloadStatsSeries(
      communityId,
      dashboardType,
      format,
      startDate,
      endDate,
      dateBasis,
    );

    // Generate filename if not provided
    if (!filename) {
      const communityPrefix =
        dashboardType === DASHBOARD_TYPES.GLOBAL ? "global" : communityId;
      const datePrefix =
        startDate && endDate ? `_${startDate}_to_${endDate}` : "";
      const formatExtension = getFormatExtension(format);

      filename = `stats_series_${communityPrefix}${datePrefix}${formatExtension}`;
    }

    // Create download link and trigger download
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);

    console.log(`Downloaded stats series: ${filename}`);
  } catch (error) {
    console.error("Error downloading stats series with filename:", error);
    throw error;
  }
};

/**
 * Get file extension for a given format
 *
 * @param {string} format - Serialization format
 * @returns {string} - File extension with leading dot
 */
const getFormatExtension = (format) => {
  switch (format) {
    case SERIALIZATION_FORMATS.JSON:
    case SERIALIZATION_FORMATS.JSON_GZIP:
    case SERIALIZATION_FORMATS.JSON_BROTLI:
      return ".json.gz";
    case SERIALIZATION_FORMATS.CSV:
      return ".tar.gz";
    case SERIALIZATION_FORMATS.XML:
      return ".xml";
    case SERIALIZATION_FORMATS.EXCEL:
      return ".tar.gz";
    default:
      return ".bin";
  }
};

export {
  statsApiClient,
  fetchStats,
  fetchStatsWithYearlyBlocks,
  downloadStatsSeries,
  downloadStatsSeriesWithFilename,
  SERIALIZATION_FORMATS,
  getFormatExtension,
};
