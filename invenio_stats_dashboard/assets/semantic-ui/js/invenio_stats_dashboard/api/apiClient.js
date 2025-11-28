// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

/**
 * Standalone API client module to avoid circular dependencies.
 * This module can be imported by both the main bundle and web workers.
 */

import axios from "axios";
import { DASHBOARD_TYPES } from "../constants";
import { kebabToCamel } from "../utils";

/**
 * Get CSRF token from cookie (works in main thread only)
 * @returns {string|null} CSRF token or null if not found
 */
const getCsrfTokenFromCookie = () => {
  if (typeof document === "undefined") {
    return null;
  }
  const name = "csrftoken";
  const cookies = document.cookie.split(";");
  for (let i = 0; i < cookies.length; i++) {
    const cookie = cookies[i].trim();
    if (cookie.startsWith(name + "=")) {
      const parts = cookie.split("=");
      if (parts.length >= 2) {
        return parts.slice(1).join("=");
      }
    }
  }
  return null;
};

/**
 * Create axios instance with proper CSRF token configuration
 * @param {string|null} csrfToken - Optional CSRF token to use explicitly.
 *   If provided, will be used directly (required for web workers).
 *   If not provided, axios will automatically read from cookie (main thread only).
 */
const createAxiosWithCSRF = (csrfToken = null) => {
  const config = {
    withCredentials: true,
    headers: {
      "Content-Type": "application/json",
    },
  };

  if (csrfToken) {
    config.headers["X-CSRFToken"] = csrfToken;
  } else {
    config.xsrfCookieName = "csrftoken";
    config.xsrfHeaderName = "X-CSRFToken";
  }

  return axios.create(config);
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
 * @param {bool} requestCompressedJson - Whether to request server-side compression of the response data.
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
    requestCompressedJson = false,
    csrfToken = null,
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
    const axiosWithCSRF = createAxiosWithCSRF(csrfToken);

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

      const acceptHeader = requestCompressedJson
        ? "application/json+gzip"
        : "application/json";

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

export { createAxiosWithCSRF, statsApiClient, getCsrfTokenFromCookie };
