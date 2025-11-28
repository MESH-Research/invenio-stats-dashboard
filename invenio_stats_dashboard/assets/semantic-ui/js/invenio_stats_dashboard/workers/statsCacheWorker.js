/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 *
 * Worker manager for async, non-blocking stats cache operations
 */

import { getCsrfTokenFromCookie } from "../api/apiClient";

let worker = null;
let messageIdCounter = 0;
const pendingMessages = new Map();

/**
 * Get or create the Web Worker instance
 */
const getWorker = () => {
  if (!worker) {
    // Create worker from the worker file
    // import.meta.url points to the bundled location at runtime
    try {
      worker = new Worker(new URL("./statsCache.worker.js", import.meta.url), {
        type: "module",
      });
    } catch (error) {
      console.error("Failed to create stats cache worker:", error);
      throw error;
    }

    worker.addEventListener("message", (event) => {
      const { id, type, result, cacheKey } = event.data;

      if (type === "CACHE_UPDATED") {
        if (typeof window !== "undefined" && window.dispatchEvent) {
          window.dispatchEvent(
            new CustomEvent("statsCacheUpdated", {
              detail: result, // Contains cacheKey, data, year, success, error
            }),
          );
        }
        return;
      }

      const pending = pendingMessages.get(id);
      if (pending) {
        pendingMessages.delete(id);
        if (result.success) {
          // GET_CACHED_STATS needs: data, serverFetchTimestamp, year
          // SET_CACHED_STATS needs: cacheKey, compressed (optional), objectSize (optional)
          // CLEAR operations return: success
          pending.resolve(result);
        } else {
          pending.reject(new Error(result.error || "Worker operation failed"));
        }
      }
    });

    worker.addEventListener("error", (error) => {
      console.error("Stats cache worker error:", error);
      // Reject all pending messages
      pendingMessages.forEach((pending) => {
        pending.reject(error);
      });
      pendingMessages.clear();
    });
  }

  return worker;
};

/**
 * Send message to worker and return a promise
 */
const sendMessage = (type, params = {}) => {
  return new Promise((resolve, reject) => {
    const id = ++messageIdCounter;

    // Store pending message
    pendingMessages.set(id, { resolve, reject });

    // Get worker and send message
    const workerInstance = getWorker();
    workerInstance.postMessage({ type, id, params });
  });
};

/**
 * Store stats data in cache (non-blocking, uses Web Worker)
 * @param {string} communityId - Community ID
 * @param {string} dashboardType - Dashboard type
 * @param {Object} transformedData - Transformed stats data (contains all 4 categories)
 * @param {string} dateBasis - Date basis ("added", "created", "published")
 * @param {string} blockStartDate - Start date (optional)
 * @param {string} blockEndDate - End date (optional)
 * @param {number} year - Year for this cache entry (optional, extracted from blockStartDate if not provided)
 * @param {boolean} compressionEnabled - Whether to compress data before caching (optional, default: false)
 * @returns {Promise<void>}
 */
export const setCachedStats = async (
  communityId,
  dashboardType,
  transformedData,
  dateBasis = "added",
  blockStartDate = null,
  blockEndDate = null,
  year = null,
  compressionEnabled = false,
) => {
  try {
    const normalizedCommunityId = communityId || "global";
    const startTime = performance.now();
    console.log("setCachedStats (worker) called with:", {
      communityId: normalizedCommunityId,
      dashboardType,
      dateBasis,
      blockStartDate,
      blockEndDate,
      year,
      compressionEnabled,
    });

    // Transfer the data to the worker - it will cache it (with optional compression)
    const result = await sendMessage("SET_CACHED_STATS", {
      communityId: normalizedCommunityId,
      dashboardType,
      transformedData,
      dateBasis,
      blockStartDate,
      blockEndDate,
      year,
      compressionEnabled,
    });

    if (result.objectSize) {
      console.log(
        `Successfully cached stats data: ${result.cacheKey} (size: ${(result.objectSize / 1024).toFixed(2)} KB)`,
      );
    } else {
      console.log(`Successfully cached stats data: ${result.cacheKey}`);
    }
  } catch (error) {
    console.warn("Failed to cache stats data (worker):", error);
    // Don't throw - caching failures shouldn't break the app
  }
};

/**
 * Retrieve stats data from cache (non-blocking, uses Web Worker)
 * @param {string} communityId - Community ID
 * @param {string} dashboardType - Dashboard type
 * @param {string} dateBasis - Date basis ("added", "created", "published")
 * @param {string} blockStartDate - Start date (optional)
 * @param {string} blockEndDate - End date (optional)
 * @returns {Promise<Object|null>} Cached stats data (contains all 4 categories) or null if not found/expired
 */
export const getCachedStats = async (
  communityId,
  dashboardType,
  dateBasis = "added",
  blockStartDate = null,
  blockEndDate = null,
  requestCompressedJson = false,
  cacheCompressedJson = false,
) => {
  try {
    // Normalize undefined/null communityId to 'global' for consistency
    const normalizedCommunityId = communityId || "global";
    const startTime = performance.now();
    console.log("getCachedStats (worker) called with:", {
      communityId: normalizedCommunityId,
      dashboardType,
      dateBasis,
      blockStartDate,
      blockEndDate,
    });

    // Get CSRF token from cookie (main thread can access cookies)
    const csrfToken = getCsrfTokenFromCookie();

    const result = await sendMessage("GET_CACHED_STATS", {
      communityId: normalizedCommunityId,
      dashboardType,
      dateBasis,
      blockStartDate,
      blockEndDate,
      requestCompressedJson,
      cacheCompressedJson,
      csrfToken, // Pass token so worker can use it for background updates
    });

    const duration = performance.now() - startTime;

    // Worker returns { success, data, serverFetchTimestamp, year, isExpired }
    // We return the full object so API can access serverFetchTimestamp and isExpired
    if (result && result.data) {
      const logMessage = result.isExpired
        ? `Retrieved expired cached data for: ${normalizedCommunityId} ${dashboardType} ${dateBasis} ${blockStartDate}-${blockEndDate} (${duration.toFixed(2)}ms) - background update queued`
        : `Retrieved cached data for: ${normalizedCommunityId} ${dashboardType} ${dateBasis} ${blockStartDate}-${blockEndDate} (${duration.toFixed(2)}ms)`;
      console.log(logMessage);
      return {
        data: result.data,
        serverFetchTimestamp: result.serverFetchTimestamp || null,
        year: result.year || null,
        isExpired: result.isExpired || false,
      };
    } else {
      console.log(
        `No cached data found for: ${normalizedCommunityId} ${dashboardType} ${dateBasis} ${blockStartDate}-${blockEndDate} (${duration.toFixed(2)}ms)`,
      );
      return null;
    }
  } catch (error) {
    console.warn("Failed to retrieve cached stats data (worker):", error);
    return null;
  }
};

/**
 * Clear cached stats for a specific key (non-blocking, uses Web Worker)
 * @param {string} cacheKey - Cache key
 * @returns {Promise<void>}
 */
export const clearCachedStatsForKey = async (cacheKey) => {
  try {
    console.log("clearCachedStatsForKey (worker) called for:", cacheKey);
    await sendMessage("CLEAR_CACHED_STATS_FOR_KEY", { cacheKey });
    console.log(`Successfully cleared cached stats data for key: ${cacheKey}`);
  } catch (error) {
    console.warn(
      "Failed to clear cached stats data for key (worker):",
      cacheKey,
      error,
    );
  }
};

/**
 * Clear all cached stats data (non-blocking, uses Web Worker)
 * @returns {Promise<void>}
 */
export const clearAllCachedStats = async () => {
  try {
    console.log("clearAllCachedStats (worker) called");
    await sendMessage("CLEAR_ALL_CACHED_STATS");
    console.log("Successfully cleared all cached stats data");
  } catch (error) {
    console.warn("Failed to clear all cached stats data (worker):", error);
  }
};

/**
 * Terminate the worker (for cleanup)
 */
export const terminateWorker = () => {
  if (worker) {
    worker.terminate();
    worker = null;
    pendingMessages.clear();
  }
};

// Export formatCacheTimestamp from dates utility (this doesn't need a worker)
export { formatCacheTimestamp } from "../utils/dates";
