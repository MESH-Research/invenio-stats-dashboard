/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 */

import pako from 'pako';
import { formatRelativeTimestamp } from './dates';

/**
 * Utility for caching stats data in IndexedDB
 * Distinguishes between requests by community ID and request date
 */

const DB_NAME = 'invenio_stats_dashboard';
const DB_VERSION = 1;
const STORE_NAME = 'stats_cache';
const CACHE_EXPIRY_DAYS = 7; // Cache expires after 7 days

/**
 * Get IndexedDB database connection
 * @returns {Promise<IDBDatabase>} Database instance
 */
const getDB = () => {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'key' });
        store.createIndex('timestamp', 'timestamp', { unique: false });
        store.createIndex('communityId', 'communityId', { unique: false });
      }
    };
  });
};

/**
 * Generate cache key for stats data
 * @param {string} communityId - Community ID
 * @param {string} dashboardType - The dashboard type
 * @param {string} startDate - Start date (optional)
 * @param {string} endDate - End date (optional)
 * @returns {string} Cache key
 */
const generateCacheKey = (communityId, dashboardType, startDate = null, endDate = null) => {
  const communityIdShort = communityId ? communityId.substring(0, 8) : 'global';
  const startDateShort = startDate ? startDate.substring(0, 10) : 'default';
  const endDateShort = endDate ? endDate.substring(0, 10) : 'default';

  const key = `isd_${communityIdShort}_${dashboardType}_${startDateShort}_${endDateShort}`;
  console.log('generateCacheKey input:', { communityId, dashboardType, startDate, endDate });
  console.log('generateCacheKey output:', key);
  return key;
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

  const now = Date.now();
  const cacheAge = now - cachedData.timestamp;
  const maxAge = CACHE_EXPIRY_DAYS * 24 * 60 * 60 * 1000; // Convert days to milliseconds

  return cacheAge < maxAge;
};

/**
 * Format cache timestamp for display
 * @param {number} timestamp - Timestamp in milliseconds
 * @returns {string} Formatted timestamp string
 */
export const formatCacheTimestamp = (timestamp) => {
  if (!timestamp) {
    return 'Unknown';
  }

  return formatRelativeTimestamp(timestamp);
};

/**
 * Store stats data in cache
 * @param {string} communityId - Community ID
 * @param {string} dashboardType - Dashboard type
 * @param {Object} transformedData - Transformed stats data
 * @param {string} startDate - Start date (optional)
 * @param {string} endDate - End date (optional)
 */
export const setCachedStats = async (communityId, dashboardType, transformedData, startDate = null, endDate = null) => {
  try {
    const cacheKey = generateCacheKey(communityId, dashboardType, startDate, endDate);
    const timestamp = Date.now();

    console.log('setCachedStats called with:', { communityId, dashboardType, startDate, endDate });
    console.log('Generated cache key:', cacheKey);

    // Compress the data
    const jsonString = JSON.stringify(transformedData);
    const compressedData = pako.gzip(jsonString);
    const blob = new Blob([compressedData], { type: 'application/gzip' });

    console.log(`Compression: ${jsonString.length} bytes -> ${compressedData.length} bytes (${(compressedData.length / jsonString.length * 100).toFixed(1)}%)`);

    // Store in IndexedDB
    const db = await getDB();
    const transaction = db.transaction([STORE_NAME], 'readwrite');
    const store = transaction.objectStore(STORE_NAME);

    const cacheRecord = {
      key: cacheKey,
      data: blob,
      timestamp,
      communityId,
      dashboardType,
      startDate,
      endDate,
      compressed: true,
      originalSize: jsonString.length,
      compressedSize: compressedData.length,
      version: '1.0'
    };

    await new Promise((resolve, reject) => {
      const request = store.put(cacheRecord);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });

    console.log(`Successfully cached stats data: ${cacheKey}`);
  } catch (error) {
    console.warn('Failed to cache stats data:', error);
  }
};

/**
 * Retrieve stats data from cache
 * @param {string} communityId - Community ID
 * @param {string} dashboardType - Dashboard type
 * @param {string} startDate - Start date (optional)
 * @param {string} endDate - End date (optional)
 * @returns {Object|null} Cached stats data or null if not found/expired
 */
export const getCachedStats = async (communityId, dashboardType, startDate = null, endDate = null) => {
  try {
    const cacheKey = generateCacheKey(communityId, dashboardType, startDate, endDate);

    console.log('getCachedStats called with:', { communityId, dashboardType, startDate, endDate });
    console.log('Generated cache key:', cacheKey);

    // Retrieve from IndexedDB
    const db = await getDB();
    const transaction = db.transaction([STORE_NAME], 'readonly');
    const store = transaction.objectStore(STORE_NAME);

    const record = await new Promise((resolve, reject) => {
      const request = store.get(cacheKey);
      request.onsuccess = () => {
        console.log('IndexedDB get request successful, result:', request.result);
        resolve(request.result);
      };
      request.onerror = () => {
        console.error('IndexedDB get request failed:', request.error);
        reject(request.error);
      };
    });

    if (!record) {
      console.log('No cached data found for key:', cacheKey);
      return null;
    }

    console.log('Found cached record:', record);

    // Check if cache is still valid
    if (!isCacheValid(record)) {
      console.log('Cached data expired, removing...');
      await clearCachedStatsForKey(cacheKey);
      return null;
    }

    // Decompress the data
    const arrayBuffer = await record.data.arrayBuffer();
    const compressedData = new Uint8Array(arrayBuffer);
    const decompressedData = JSON.parse(pako.ungzip(compressedData, { to: 'string' }));

    console.log(`Retrieved and decompressed cached data: ${cacheKey}`);
    return decompressedData;
  } catch (error) {
    console.warn('Failed to retrieve cached stats data:', error);
    return null;
  }
};

/**
 * Clear all cached stats data
 */
export const clearAllCachedStats = async () => {
  try {
    console.log('clearAllCachedStats called');

    const db = await getDB();
    const transaction = db.transaction([STORE_NAME], 'readwrite');
    const store = transaction.objectStore(STORE_NAME);

    await new Promise((resolve, reject) => {
      const request = store.clear();
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });

    console.log('Successfully cleared all cached stats data');
  } catch (error) {
    console.warn('Failed to clear all cached stats data:', error);
  }
};

/**
 * Clear cached stats for a specific key
 * @param {string} baseCacheKey - Base cache key
 */
export const clearCachedStatsForKey = async (baseCacheKey) => {
  try {
    console.log('clearCachedStatsForKey called for:', baseCacheKey);

    const db = await getDB();
    const transaction = db.transaction([STORE_NAME], 'readwrite');
    const store = transaction.objectStore(STORE_NAME);

    await new Promise((resolve, reject) => {
      const request = store.delete(baseCacheKey);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });

    console.log(`Successfully cleared cached stats data for key: ${baseCacheKey}`);
  } catch (error) {
    console.warn('Failed to clear cached stats data for key:', baseCacheKey, error);
  }
};