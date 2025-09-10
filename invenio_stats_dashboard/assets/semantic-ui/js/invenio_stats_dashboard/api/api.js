// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import { http } from "react-invenio-forms";
import { DASHBOARD_TYPES } from "../constants";
import { getCachedStats, setCachedStats, clearAllCachedStats } from "../utils/statsCache";
import { transformApiData } from "./dataTransformer";
import { generateTestStatsData } from "../components/test_data";

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
 *
 * @returns {Promise<Object>} - The stats data.
 */
const statsApiClient = {
  getStats: async (communityId, dashboardType, startDate = null, endDate = null) => {
    if (dashboardType === DASHBOARD_TYPES.GLOBAL) {
      communityId = "global";
    }
    let requestBody = {
      [`${dashboardType}-stats`]: {
        "stat": `${dashboardType}-stats`,
        "params": {
          "community_id": communityId,
        }
      },
    };
    if (startDate) {
      requestBody[`${dashboardType}-stats`].params.start_date = startDate;
    }
    if (endDate) {
      requestBody[`${dashboardType}-stats`].params.end_date = endDate;
    }
    const response = await http.post(`/api/stats`, requestBody);
    return response.data;
  }
};

/**
 * Get cached stats data
 *
 * @param {Object} params - Parameters for getting cached stats
 * @param {string} params.communityId - The community ID (or 'global')
 * @param {string} params.dashboardType - The dashboard type
 * @param {Date} [params.startDate] - Start date (optional)
 * @param {Date} [params.endDate] - End date (optional)
 * @param {Function} [params.getStatsParams] - Custom function to get stats parameters
 * @param {Object} [params.community] - Community object (for custom params)
 *
 * @returns {Promise<Object|null>} Cached stats data if available, null otherwise
 */
const getCachedStatsData = async ({
  communityId,
  dashboardType,
  startDate = null,
  endDate = null,
  getStatsParams = null,
  community = null
}) => {
  // Get community ID for caching
  const cacheCommunityId = communityId || community?.id || 'global';

  // Use custom getStatsParams if provided, otherwise use default behavior
  const params = getStatsParams ? getStatsParams(community, dashboardType) : [dashboardType, startDate, endDate];
  const [dashboardTypeParam, paramStartDate, paramEndDate] = params;

  // Try to get cached data
  return await getCachedStats(cacheCommunityId, dashboardTypeParam, paramStartDate, paramEndDate);
};

/**
 * Fetch fresh stats data and cache it
 *
 * @param {Object} params - Parameters for fetching stats
 * @param {string} params.communityId - The community ID (or 'global')
 * @param {string} params.dashboardType - The dashboard type
 * @param {Date} [params.startDate] - Start date (optional)
 * @param {Date} [params.endDate] - End date (optional)
 * @param {Function} [params.getStatsParams] - Custom function to get stats parameters
 * @param {Object} [params.community] - Community object (for custom params)
 * @param {boolean} [params.useTestData] - Whether to use test data instead of API
 *
 * @returns {Promise<Object>} Object containing:
 *   - freshStats: Fresh data from API (transformed)
 *   - lastUpdated: Timestamp of fresh data fetch
 *   - error: Error object if fetch failed
 */
const fetchFreshStatsWithCache = async ({
  communityId,
  dashboardType,
  startDate = null,
  endDate = null,
  getStatsParams = null,
  community = null,
  useTestData = false
}) => {
  try {
    const cacheCommunityId = communityId || community?.id || 'global';
    let rawStats;
    let transformedStats;

    if (useTestData) {
      transformedStats = await generateTestStatsData(startDate, endDate);
    } else {
      rawStats = await statsApiClient.getStats(communityId, dashboardType, startDate, endDate);
      transformedStats = transformApiData(rawStats);
    }

    console.log('Fresh data fetched and transformed:', {
      communityId: cacheCommunityId,
      dashboardType: dashboardType,
      startDate: startDate?.toISOString?.() || startDate,
      endDate: endDate?.toISOString?.() || endDate,
      dataSize: JSON.stringify(transformedStats).length,
      dataKeys: Object.keys(transformedStats || {})
    });

    // Only cache if we have valid dates (not for test data with null dates)
    if (startDate && endDate) {
      console.log('Caching fresh data...');
      await setCachedStats(
        cacheCommunityId,
        dashboardType,
        transformedStats,
        startDate.toISOString(),
        endDate.toISOString()
      );
      console.log('Fresh data cached successfully');
    } else {
      console.log('Skipping cache - no valid dates provided');
    }

    return {
      freshStats: transformedStats,
      lastUpdated: Date.now(),
      error: null
    };
  } catch (error) {
    console.error('Error fetching stats:', error);
    return {
      freshStats: null,
      lastUpdated: null,
      error
    };
  }
};

/**
 * Fetch stats with complete caching and state management
 *
 * This is the main function that handles the complete flow:
 * 1. Check for cached data and return it immediately if available
 * 2. Always fetch fresh data in the background
 * 3. Transform and cache the fresh data
 * 4. Return both cached and fresh data with status information
 *
 * @param {Object} params - Parameters for fetching stats
 * @param {string} params.communityId - The community ID (or 'global')
 * @param {string} params.dashboardType - The dashboard type
 * @param {Date} [params.startDate] - Start date (optional)
 * @param {Date} [params.endDate] - End date (optional)
 * @param {Function} [params.getStatsParams] - Custom function to get stats parameters
 * @param {Object} [params.community] - Community object (for custom params)
 * @param {Function} [params.onStateChange] - Callback for state changes
 * @param {Function} [params.isMounted] - Function to check if component is still mounted
 * @param {boolean} [params.useTestData] - Whether to use test data instead of API
 *
 * @returns {Promise<Object>} Object containing:
 *   - cachedStats: Cached data if available, null otherwise
 *   - freshStats: Fresh data from API (transformed)
 *   - lastUpdated: Timestamp of fresh data fetch
 *   - error: Error object if fetch failed
 */
const fetchStats = async ({
  communityId,
  dashboardType,
  startDate = null,
  endDate = null,
  getStatsParams = null,
  community = null,
  onStateChange = null,
  isMounted = null,
  useTestData = false
}) => {
  const fetchParams = {
    communityId,
    dashboardType,
    startDate,
    endDate,
    getStatsParams,
    community
  };

  try {
    // Check for cached data first
    const cachedStats = await getCachedStatsData(fetchParams);
    console.log('Cache check result:', !!cachedStats);

    if (cachedStats) {
      // State (c): done loading + cached + fetch in process
      console.log('Found cached data, displaying immediately');
      if (onStateChange && (!isMounted || isMounted())) {
        onStateChange({
          type: 'cached_data_loaded',
          stats: cachedStats,
          isLoading: false,
          isUpdating: true,
          error: null
        });
      }
    } else {
      // State (a): loading + no cached + fetch in process
      console.log('No cached data, starting loading state');
      if (onStateChange && (!isMounted || isMounted())) {
        onStateChange({
          type: 'loading_started',
          stats: null,
          isLoading: true,
          isUpdating: false,
          error: null
        });
      }
    }

    // Always fetch fresh data in the background
    const result = await fetchFreshStatsWithCache({
      ...fetchParams,
      useTestData
    });

    // Caching is now handled in fetchFreshStatsWithCache

    // Determine final state based on result
    if (result.freshStats) {
      // State (d): done loading + live data + fetch finished
      console.log('Fresh data loaded successfully');
      if (onStateChange && (!isMounted || isMounted())) {
        onStateChange({
          type: 'fresh_data_loaded',
          stats: result.freshStats,
          isLoading: false,
          isUpdating: false,
          lastUpdated: result.lastUpdated,
          error: null
        });
      }
    } else {
      // State (e): done loading + fetch finished + stats are still null
      console.log('Fetch finished but no data available');
      if (onStateChange && (!isMounted || isMounted())) {
        onStateChange({
          type: 'no_data_available',
          stats: null,
          isLoading: false,
          isUpdating: false,
          lastUpdated: result.lastUpdated,
          error: result.error
        });
      }
    }

    return {
      cachedStats,
      freshStats: result.freshStats,
      lastUpdated: result.lastUpdated,
      error: result.error
    };
  } catch (error) {
    console.error('Error fetching stats:', error);

    if (onStateChange && (!isMounted || isMounted())) {
      onStateChange({
        type: 'error',
        stats: null,
        isLoading: false,
        isUpdating: false,
        error
      });
    }

    return {
      cachedStats: null,
      freshStats: null,
      lastUpdated: null,
      error
    };
  }
};

export { statsApiClient, getCachedStatsData, fetchFreshStatsWithCache, fetchStats };