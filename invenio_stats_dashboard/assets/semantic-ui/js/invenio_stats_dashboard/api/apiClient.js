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

export { createAxiosWithCSRF, statsApiClient };
