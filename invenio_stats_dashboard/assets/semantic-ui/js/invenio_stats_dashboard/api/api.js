// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import axios from "axios";
import { DASHBOARD_TYPES } from "../constants";
import { generateTestStatsData } from "../components/test_data";

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

      // Request with plain JSON headers and CSRF token
      const response = await axiosWithCSRF.post(
        `/api/stats-dashboard`,
        requestBody,
        {
          headers: {
            Accept: "application/json", // Request plain JSON
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
 * Fetch stats data without caching
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
}) => {
  try {
    // Start loading state
    if (onStateChange && (!isMounted || isMounted())) {
      onStateChange({
        type: "loading_started",
        stats: null,
        isLoading: true,
        isUpdating: false,
        error: null,
      });
    }

    let rawStats;

    if (useTestData) {
      rawStats = await generateTestStatsData(startDate, endDate);
    } else {
      rawStats = await statsApiClient.getStats(
        communityId,
        dashboardType,
        startDate,
        endDate,
        dateBasis,
      );
    }

    console.log("Stats data fetched and transformed:", {
      communityId,
      dashboardType,
      startDate: startDate?.toISOString?.() || startDate,
      endDate: endDate?.toISOString?.() || endDate,
      dataSize: JSON.stringify(rawStats).length,
      dataKeys: Object.keys(rawStats || {}),
    });

    // Data loaded successfully
    if (onStateChange && (!isMounted || isMounted())) {
      onStateChange({
        type: "data_loaded",
        stats: rawStats,
        isLoading: false,
        isUpdating: false,
        lastUpdated: Date.now(),
        error: null,
      });
    }

    return {
      stats: rawStats,
      lastUpdated: Date.now(),
      error: null,
    };
  } catch (error) {
    console.error("Error fetching stats:", error);

    // Set ui fetching error state
    if (onStateChange && (!isMounted || isMounted())) {
      onStateChange({
        type: "error",
        stats: null,
        isLoading: false,
        isUpdating: false,
        error,
      });
    }

    return {
      stats: null,
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
  downloadStatsSeries,
  downloadStatsSeriesWithFilename,
  SERIALIZATION_FORMATS,
  getFormatExtension,
};
