/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 */

/**
 * Utility for caching stats data in localStorage
 * Distinguishes between requests by community ID and request date
 */

const CACHE_PREFIX = 'invenio_stats_dashboard_';
const CACHE_VERSION = '1.0';
const CACHE_EXPIRY_DAYS = 7; // Cache expires after 7 days

/**
 * Generate a cache key based on community ID and request parameters
 * @param {string} communityId - The community ID (or 'global')
 * @param {string} dashboardType - The dashboard type
 * @param {string} startDate - Start date (optional)
 * @param {string} endDate - End date (optional)
 * @returns {string} Cache key
 */
const generateCacheKey = (communityId, dashboardType, startDate = null, endDate = null) => {
  const params = {
    communityId: communityId || 'global',
    dashboardType,
    startDate: startDate || 'default',
    endDate: endDate || 'default'
  };

  return `${CACHE_PREFIX}${CACHE_VERSION}_${JSON.stringify(params)}`;
};

/**
 * Check if cached data is still valid
 * @param {Object} cachedData - The cached data object
 * @returns {boolean} True if cache is valid, false otherwise
 */
const isCacheValid = (cachedData) => {
  if (!cachedData || !cachedData.timestamp) {
    return false;
  }

  const cacheAge = Date.now() - cachedData.timestamp;
  const maxAge = CACHE_EXPIRY_DAYS * 24 * 60 * 60 * 1000; // Convert days to milliseconds

  return cacheAge < maxAge;
};

/**
 * Store transformed stats data in localStorage
 * @param {string} communityId - The community ID (or 'global')
 * @param {string} dashboardType - The dashboard type
 * @param {Object} transformedData - The transformed data from dataTransformer
 * @param {string} startDate - Start date (optional)
 * @param {string} endDate - End date (optional)
 */
export const setCachedStats = (communityId, dashboardType, transformedData, startDate = null, endDate = null) => {
  try {
    const cacheKey = generateCacheKey(communityId, dashboardType, startDate, endDate);
    const cacheData = {
      data: transformedData,
      timestamp: Date.now(),
      version: CACHE_VERSION
    };

    localStorage.setItem(cacheKey, JSON.stringify(cacheData));
    console.log(`Stats cached for key: ${cacheKey}`);
  } catch (error) {
    console.warn('Failed to cache stats data:', error);
  }
};

/**
 * Retrieve cached stats data from localStorage
 * @param {string} communityId - The community ID (or 'global')
 * @param {string} dashboardType - The dashboard type
 * @param {string} startDate - Start date (optional)
 * @param {string} endDate - End date (optional)
 * @returns {Object|null} Cached data if valid, null otherwise
 */
export const getCachedStats = (communityId, dashboardType, startDate = null, endDate = null) => {
  try {
    const cacheKey = generateCacheKey(communityId, dashboardType, startDate, endDate);
    const cachedString = localStorage.getItem(cacheKey);

    if (!cachedString) {
      return null;
    }

    const cachedData = JSON.parse(cachedString);

    if (!isCacheValid(cachedData)) {
      // Remove expired cache
      localStorage.removeItem(cacheKey);
      return null;
    }

    console.log(`Stats retrieved from cache for key: ${cacheKey}`);
    return cachedData.data;
  } catch (error) {
    console.warn('Failed to retrieve cached stats data:', error);
    return null;
  }
};

/**
 * Clear all cached stats data
 */
export const clearCachedStats = () => {
  try {
    const keys = Object.keys(localStorage);
    const statsKeys = keys.filter(key => key.startsWith(CACHE_PREFIX));

    statsKeys.forEach(key => {
      localStorage.removeItem(key);
    });

    console.log(`Cleared ${statsKeys.length} cached stats entries`);
  } catch (error) {
    console.warn('Failed to clear cached stats data:', error);
  }
};

/**
 * Get cache info for debugging
 * @returns {Object} Cache information
 */
export const getCacheInfo = () => {
  try {
    const keys = Object.keys(localStorage);
    const statsKeys = keys.filter(key => key.startsWith(CACHE_PREFIX));

    const cacheInfo = statsKeys.map(key => {
      try {
        const cachedString = localStorage.getItem(key);
        const cachedData = JSON.parse(cachedString);
        return {
          key,
          timestamp: cachedData.timestamp,
          isValid: isCacheValid(cachedData),
          age: Date.now() - cachedData.timestamp
        };
      } catch (error) {
        return { key, error: error.message };
      }
    });

    return {
      totalEntries: statsKeys.length,
      entries: cacheInfo
    };
  } catch (error) {
    return { error: error.message };
  }
};

/**
 * Format timestamp for display
 * @param {number} timestamp - Unix timestamp
 * @returns {string} Formatted date string
 */
export const formatCacheTimestamp = (timestamp) => {
  const date = new Date(timestamp);
  return date.toLocaleString();
};
