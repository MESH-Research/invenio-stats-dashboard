/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 *
 * Worker manager for stats cache operations
 * Provides async API that communicates with Web Worker to avoid blocking main thread
 */

let worker = null;
let messageIdCounter = 0;
const pendingMessages = new Map();

/**
 * Get or create the Web Worker instance
 */
const getWorker = () => {
  if (!worker) {
    // Create worker from the worker file
    // Note: In a build system, you may need to adjust this path
    worker = new Worker(
      new URL('./statsCache.worker.js', import.meta.url),
      { type: 'module' }
    );

    // Handle messages from worker
    worker.addEventListener('message', (event) => {
      const { id, result } = event.data;

      const pending = pendingMessages.get(id);
      if (pending) {
        pendingMessages.delete(id);
        if (result.success) {
          pending.resolve(result.data !== undefined ? result.data : result);
        } else {
          pending.reject(new Error(result.error || 'Worker operation failed'));
        }
      }
    });

    // Handle worker errors
    worker.addEventListener('error', (error) => {
      console.error('Stats cache worker error:', error);
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
 * @param {string} startDate - Start date (optional)
 * @param {string} endDate - End date (optional)
 * @param {number} year - Year for this cache entry (optional, extracted from startDate if not provided)
 * @returns {Promise<void>}
 */
export const setCachedStats = async (communityId, dashboardType, transformedData, dateBasis = 'added', startDate = null, endDate = null, year = null) => {
  try {
    const startTime = performance.now();
    console.log('setCachedStats (worker) called with:', { communityId, dashboardType, dateBasis, startDate, endDate, year });
    
    // Transfer the data to the worker - it will compress and cache it
    const result = await sendMessage('SET_CACHED_STATS', {
      communityId,
      dashboardType,
      transformedData,
      dateBasis,
      startDate,
      endDate,
      year,
    });

    if (result.compressedRatio) {
      console.log(`Successfully cached stats data: ${result.cacheKey} (compression: ${(result.compressedRatio * 100).toFixed(1)}%)`);
    } else {
      console.log(`Successfully cached stats data: ${result.cacheKey}`);
    }
  } catch (error) {
    console.warn('Failed to cache stats data (worker):', error);
    // Don't throw - caching failures shouldn't break the app
  }
};

/**
 * Retrieve stats data from cache (non-blocking, uses Web Worker)
 * @param {string} communityId - Community ID
 * @param {string} dashboardType - Dashboard type
 * @param {string} dateBasis - Date basis ("added", "created", "published")
 * @param {string} startDate - Start date (optional)
 * @param {string} endDate - End date (optional)
 * @returns {Promise<Object|null>} Cached stats data (contains all 4 categories) or null if not found/expired
 */
export const getCachedStats = async (communityId, dashboardType, dateBasis = 'added', startDate = null, endDate = null) => {
  try {
    const startTime = performance.now();
    console.log('getCachedStats (worker) called with:', { communityId, dashboardType, dateBasis, startDate, endDate });
    
    const result = await sendMessage('GET_CACHED_STATS', {
      communityId,
      dashboardType,
      dateBasis,
      startDate,
      endDate,
    });

    const duration = performance.now() - startTime;

    // Worker returns { success, data, serverFetchTimestamp, year }
    // We return the full object so API can access serverFetchTimestamp
    if (result && result.data) {
      console.log(`Retrieved cached data for: ${communityId} ${dashboardType} ${dateBasis} ${startDate}-${endDate} (${duration.toFixed(2)}ms)`);
      return {
        data: result.data,
        serverFetchTimestamp: result.serverFetchTimestamp || null,
        year: result.year || null
      };
    } else {
      console.log(`No cached data found for: ${communityId} ${dashboardType} ${dateBasis} ${startDate}-${endDate} (${duration.toFixed(2)}ms)`);
      return null;
    }
  } catch (error) {
    console.warn('Failed to retrieve cached stats data (worker):', error);
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
    console.log('clearCachedStatsForKey (worker) called for:', cacheKey);
    await sendMessage('CLEAR_CACHED_STATS_FOR_KEY', { cacheKey });
    console.log(`Successfully cleared cached stats data for key: ${cacheKey}`);
  } catch (error) {
    console.warn('Failed to clear cached stats data for key (worker):', cacheKey, error);
  }
};

/**
 * Clear all cached stats data (non-blocking, uses Web Worker)
 * @returns {Promise<void>}
 */
export const clearAllCachedStats = async () => {
  try {
    console.log('clearAllCachedStats (worker) called');
    await sendMessage('CLEAR_ALL_CACHED_STATS');
    console.log('Successfully cleared all cached stats data');
  } catch (error) {
    console.warn('Failed to clear all cached stats data (worker):', error);
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

// Export formatCacheTimestamp from the original module (this doesn't need a worker)
export { formatCacheTimestamp } from './statsCache';

