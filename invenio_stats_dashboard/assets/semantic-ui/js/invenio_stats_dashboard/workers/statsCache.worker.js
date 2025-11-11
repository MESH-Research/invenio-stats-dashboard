/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 *
 * Web Worker for handling IndexedDB cache operations off the main thread
 */

/* eslint-disable no-restricted-globals */
// In Web Workers, 'self' is the global object (equivalent to 'window' in main thread)
// This is the standard and correct way to access the worker's global scope

// Import pako for compression/decompression (conditional based on config)
// Note: This requires pako to be available as an ES module in your build system
// If using webpack/vite, ensure pako is bundled for the worker context
import pako from "pako";

import { statsApiClient } from "../api/apiClient";

const DB_NAME = "invenio_stats_dashboard";
const DB_VERSION = 2; // Increment version to add new indices
const STORE_NAME = "stats_cache";
const CACHE_EXPIRY_HOURS_CURRENT_YEAR = 1; // 1 hour TTL for current year (data changes hourly)
const CACHE_EXPIRY_YEARS_PAST = 1; // 1 year TTL for past years (historical data is static)
const MAX_CACHE_ENTRIES = 20; // Maximum number of cached year blocks across all communities/dashboards

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
      const transaction = event.target.transaction;

      if (!db.objectStoreNames.contains(STORE_NAME)) {
        // Create new store
        const store = db.createObjectStore(STORE_NAME, { keyPath: "key" });
        store.createIndex("timestamp", "timestamp", { unique: false });
        store.createIndex("lastAccessed", "lastAccessed", { unique: false });
        store.createIndex("communityId", "communityId", { unique: false });
        store.createIndex("year", "year", { unique: false });
        store.createIndex("dateBasis", "dateBasis", { unique: false });
      } else {
        // Upgrade existing store - add new indices if they don't exist
        const store = transaction.objectStore(STORE_NAME);

        // Check and create indices safely - wrap in try-catch to handle if index already exists
        try {
          if (!store.indexNames.contains("year")) {
            store.createIndex("year", "year", { unique: false });
          }
        } catch (e) {
          console.warn('Index "year" may already exist:', e);
        }

        try {
          if (!store.indexNames.contains("dateBasis")) {
            store.createIndex("dateBasis", "dateBasis", { unique: false });
          }
        } catch (e) {
          console.warn('Index "dateBasis" may already exist:', e);
        }

        try {
          if (!store.indexNames.contains("lastAccessed")) {
            store.createIndex("lastAccessed", "lastAccessed", {
              unique: false,
            });
          }
        } catch (e) {
          console.warn('Index "lastAccessed" may already exist:', e);
        }
      }
    };
  });
};

/**
 * Generate cache key for stats data
 * Includes: communityId, dashboardType, dateBasis, blockStartDate, blockEndDate
 */
const generateCacheKey = (
  communityId,
  dashboardType,
  dateBasis = "added",
  blockStartDate = null,
  blockEndDate = null,
) => {
  const communityIdShort = communityId ? communityId.substring(0, 8) : "global";
  const startDateShort = blockStartDate
    ? blockStartDate.substring(0, 10)
    : "default";
  const endDateShort = blockEndDate ? blockEndDate.substring(0, 10) : "default";

  return `isd_${communityIdShort}_${dashboardType}_${dateBasis}_${startDateShort}_${endDateShort}`;
};

/**
 * Extract year from date string (YYYY-MM-DD format)
 */
const extractYear = (blockStartDate) => {
  if (!blockStartDate) return null;
  const yearMatch = blockStartDate.match(/^(\d{4})/);
  return yearMatch ? parseInt(yearMatch[1], 10) : null;
};

/**
 * Check if a year is the current year
 */
const isCurrentYear = (year) => {
  if (!year) return false;
  const currentYear = new Date().getUTCFullYear();
  return year === currentYear;
};

/**
 * Check if cached data is still valid
 * Uses different TTLs: 1 hour for current year, 1 year for past years
 */
const isCacheValid = (cachedData) => {
  if (!cachedData || !cachedData.timestamp) {
    return false;
  }

  const now = Date.now();
  const cacheAge = now - cachedData.timestamp;

  // Determine TTL based on whether it's current year or past year
  const year = cachedData.year;
  const isCurrent = isCurrentYear(year);

  const maxAge = isCurrent
    ? CACHE_EXPIRY_HOURS_CURRENT_YEAR * 60 * 60 * 1000 // 1 hour in milliseconds
    : CACHE_EXPIRY_YEARS_PAST * 365 * 24 * 60 * 60 * 1000; // 1 year in milliseconds

  return cacheAge < maxAge;
};

/**
 * Evict oldest cache entries if we exceed MAX_CACHE_ENTRIES
 * Uses a separate transaction to avoid conflicts
 */
const evictOldestEntries = async (db, countToEvict) => {
  return new Promise((resolve, reject) => {
    const evictTransaction = db.transaction([STORE_NAME], "readwrite");
    const evictStore = evictTransaction.objectStore(STORE_NAME);

    // Get all entries - we'll sort by lastAccessed in memory
    const getAllRequest = evictStore.getAll();
    const entriesToDelete = [];

    getAllRequest.onsuccess = async () => {
      const allEntries = getAllRequest.result;

      // Sort by lastAccessed (oldest first), fallback to timestamp if lastAccessed missing
      allEntries.sort((a, b) => {
        const aTime = a.lastAccessed || a.timestamp || 0;
        const bTime = b.lastAccessed || b.timestamp || 0;
        return aTime - bTime;
      });

      // Select the oldest entries to delete
      const toDelete = allEntries.slice(
        0,
        Math.min(countToEvict, allEntries.length),
      );

      // Delete them in the same transaction
      let deleted = 0;
      if (toDelete.length === 0) {
        resolve();
        return;
      }

      toDelete.forEach((entry) => {
        const deleteRequest = evictStore.delete(entry.key);
        deleteRequest.onsuccess = () => {
          deleted++;
          if (deleted === toDelete.length) {
            resolve();
          }
        };
        deleteRequest.onerror = () => {
          deleted++;
          if (deleted === toDelete.length) {
            resolve(); // Continue even if some deletes fail
          }
        };
      });
    };

    getAllRequest.onerror = () => reject(getAllRequest.error);
  });
};

/**
 * Handle updateCachedStats message
 * @param {Object} params
 * @param {string} params.communityId
 * @param {string} params.dashboardType: one of "global", "community"
 * @param {string} params.blockStartDate: start date of the block
 *   in YYYY-MM-DD format
 * @param {string} params.blockEndDate: end date of the block
 *   in YYYY-MM-DD format
 * @param {string} params.dateBasis: date basis used to calculate record counts
 *   ("added", "created", "published")
 * @param {boolean} params.requestCompressedJson: whether to request compressed json from the API
 * @param {boolean} params.cacheCompressedJson: whether to cache compressed json
 * @returns {Promise<Object>} result of the setCachedStats operation
 *   {
 *     success: true,
 *     cacheKey: string,
 *     compressed: boolean,
 *     objectSize: number,
 *   }
 *   or
 *   { success: false, error: string }
 */
const handleUpdateCachedStats = async (params) => {
  const {
    communityId,
    dashboardType,
    blockStartDate,
    blockEndDate,
    dateBasis,
    requestCompressedJson,
    cacheCompressedJson,
  } = params;

  const transformedData = await statsApiClient.getStats(
    communityId,
    dashboardType,
    blockStartDate,
    blockEndDate,
    dateBasis,
    requestCompressedJson,
  );
  const year = extractYear(blockStartDate);

  const result = await handleSetCachedStats({
    ...params,
    transformedData,
    year,
  });

  // Return both the cache operation result and the actual data
  return {
    ...result,
    data: transformedData,
    year,
  };
};

/**
 * Handle setCachedStats message
 * @param {Object} params
 * @param {string} params.communityId: community ID
 * @param {string} params.dashboardType: one of "global", "community"
 * @param {Object} params.transformedData: transformed stats data (contains all 4 categories)
 * @param {string} params.dateBasis: date basis used to calculate record counts
 *   ("added", "created", "published")
 * @param {string} params.blockStartDate: start date of the block
 *   in YYYY-MM-DD format
 * @param {string} params.blockEndDate: end date of the block
 *   in YYYY-MM-DD format
 * @param {number} params.year: year of the block
 * @param {boolean} params.cacheCompressedJson: whether to cache compressed json
 * @returns {Promise<Object>} result of the setCachedStats operation
 *   {
 *     success: true,
 *     cacheKey: string,
 *     compressed: boolean,
 *     objectSize: number,
 *   }
 *   or
 *   { success: false, error: string }
 */
const handleSetCachedStats = async (params) => {
  try {
    const {
      communityId = "global",
      dashboardType,
      transformedData,
      dateBasis = "added",
      blockStartDate,
      blockEndDate,
      year,
      cacheCompressedJson = false,
    } = params;
    const cacheKey = generateCacheKey(
      communityId,
      dashboardType,
      dateBasis,
      blockStartDate,
      blockEndDate,
    );
    console.log("[SET] Generated cache key:", cacheKey, "from params:", {
      communityId,
      dashboardType,
      dateBasis,
      blockStartDate,
      blockEndDate,
      cacheCompressedJson,
    });
    const timestamp = Date.now();

    const cacheYear = year || extractYear(blockStartDate);

    // Conditionally compress based on config
    let dataToStore;
    let compressed = false;
    let objectSize = null;

    // Always calculate object size for storage tracking
    const jsonString = JSON.stringify(transformedData);
    objectSize = jsonString.length;

    if (cacheCompressedJson) {
      // When compression is enabled: stringify, compress, store as ArrayBuffer
      const compressedData = pako.gzip(jsonString);
      const arrayBuffer = compressedData.buffer.slice(
        compressedData.byteOffset,
        compressedData.byteOffset + compressedData.byteLength,
      );
      dataToStore = arrayBuffer;
      compressed = true;
    } else {
      // When compression is disabled: store object directly (IndexedDB handles it natively)
      dataToStore = transformedData;
      compressed = false;
    }

    const db = await getDB();

    const checkTransaction = db.transaction([STORE_NAME], "readonly");
    const checkStore = checkTransaction.objectStore(STORE_NAME);

    const [existingRecord, totalEntries] = await Promise.all([
      new Promise((resolve, reject) => {
        const request = checkStore.get(cacheKey);
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      }),
      new Promise((resolve, reject) => {
        const countRequest = checkStore.count();
        countRequest.onsuccess = () => resolve(countRequest.result);
        countRequest.onerror = () => reject(countRequest.error);
      }),
    ]);

    // If adding new entry (not updating existing) and at limit, evict oldest first
    if (!existingRecord && totalEntries >= MAX_CACHE_ENTRIES) {
      const countToEvict = totalEntries - MAX_CACHE_ENTRIES + 1; // +1 for the new entry
      await evictOldestEntries(db, countToEvict);
    }

    // Store the entry (separate transaction)
    const storeTransaction = db.transaction([STORE_NAME], "readwrite");
    const store = storeTransaction.objectStore(STORE_NAME);
    const isCurrent = isCurrentYear(cacheYear);

    const cacheRecord = {
      key: cacheKey,
      data: dataToStore, // Store as object (when uncompressed) or compressed ArrayBuffer (when compressed)
      timestamp,
      lastAccessed: timestamp, // Update lastAccessed when storing
      communityId,
      dashboardType,
      dateBasis,
      blockStartDate,
      blockEndDate,
      year: cacheYear,
      compressed: compressed, // Flag to indicate if data is compressed
      objectSize: objectSize, // Size of the JSON-serialized object (always stored)
      version: "2.0",
      // Store server fetch time for current year (used for "last updated" display)
      serverFetchTimestamp: isCurrent ? timestamp : null,
    };

    await new Promise((resolve, reject) => {
      const request = store.put(cacheRecord);
      request.onsuccess = () => {
        console.log("[SET] Successfully stored cache key:", cacheKey);
        resolve();
      };
      request.onerror = () => {
        console.error(
          "[SET] Failed to store cache key:",
          cacheKey,
          "Error:",
          request.error,
        );
        reject(request.error);
      };
    });

    return {
      success: true,
      cacheKey,
      compressed: compressed,
      objectSize: objectSize,
    };
  } catch (error) {
    return { success: false, error: error.message };
  }
};

/**
 * Check if an update is in progress for a given cache key
 * @param {string} cacheKey - The cache key to check
 * @returns {boolean} true if an update is in progress, false otherwise
 */
const updateInProgress = (cacheKey) => {
  return messageQueue.some(
    (message) =>
      message.type === "UPDATE_CACHED_STATS" &&
      message.params.cacheKey === cacheKey,
  );
};

/**
 * Helper function to process retrieved data
 *
 * Decompresses compressed data if isCompressed is true and
 * validates the data is a valid JSON object.
 *
 * @param {Object} recordData - The data to process
 * @param {boolean} isCompressed - Whether the data is compressed
 * @param {string} cacheKey - The cache key (for error logging and deletion)
 * @returns {Promise<Object>} { parsedData: object, errorMsg: string }
 */
const processRetrievedData = async (recordData, isCompressed, cacheKey) => {
  let parsedData = null;
  let errorMsg = null;
  try {
    if (isCompressed) {
      if (recordData instanceof ArrayBuffer) {
        const compressedData = new Uint8Array(recordData);
        const decompressedString = pako.ungzip(compressedData, {
          to: "string",
        });
        parsedData = JSON.parse(decompressedString);
      } else {
        errorMsg = `Unexpected recordData type for compressed data: ${typeof recordData}. Expected ArrayBuffer.`;
        console.error(
          "handleGetCachedStats:",
          errorMsg,
          "Invalidating cache entry:",
          cacheKey,
        );
      }
    } else {
      // Handle uncompressed data
      if (
        typeof recordData === "object" &&
        recordData !== null &&
        !(recordData instanceof ArrayBuffer)
      ) {
        parsedData = recordData;
      } else {
        errorMsg = `Unexpected recordData type for uncompressed data: ${typeof recordData}. Expected object.`;
        console.error(
          "handleGetCachedStats:",
          errorMsg,
          "Invalidating cache entry:",
          cacheKey,
        );
      }
    }
  } catch (error) {
    console.error(
      "handleGetCachedStats: Error during parsing/decompression. Invalidating cache entry:",
      cacheKey,
      error,
    );
    errorMsg = error.message;
  }

  if (!parsedData) {
    console.error(
      "handleGetCachedStats: Parsed data is null/undefined! Invalidating cache entry:",
      cacheKey,
    );
  }

  if (errorMsg || !parsedData) {
    await deleteCacheEntry(cacheKey);
  }

  return { parsedData, errorMsg };
};

/**
 * Helper function to delete a cache entry by key
 * @param {string} cacheKey - The cache key to delete
 * @returns {Promise<void>}
 */
const deleteCacheEntry = async (cacheKey) => {
  const db = await getDB();
  const transaction = db.transaction([STORE_NAME], "readwrite");
  const store = transaction.objectStore(STORE_NAME);
  await new Promise((resolve, reject) => {
    const request = store.delete(cacheKey);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
};

/**
 * Update the lastAccessed timestamp for a given cache key
 * @param {string} cacheKey - The cache key to update
 * @returns {Promise<void>}
 */
const updateLastAccessed = async (cacheKey) => {
  try {
    const updateDb = await getDB();
    const updateTransaction = updateDb.transaction(
      [STORE_NAME],
      "readwrite",
    );
    const updateStore = updateTransaction.objectStore(STORE_NAME);

    // Get fresh record to ensure we have all properties
    const freshRecord = await new Promise((resolve, reject) => {
      const getRequest = updateStore.get(cacheKey);
      getRequest.onsuccess = () => resolve(getRequest.result);
      getRequest.onerror = () => reject(getRequest.error);
    });

    if (freshRecord) {
      const updatedRecord = {
        ...freshRecord,
        lastAccessed: Date.now(),
      };

      await new Promise((resolve, reject) => {
        const updateRequest = updateStore.put(updatedRecord);
        updateRequest.onsuccess = () => resolve();
        updateRequest.onerror = () => reject(updateRequest.error);
      });
    }
  } catch (error) {
    // Silently fail - LRU update is not critical for returning cached data
    console.warn("Failed to update lastAccessed timestamp:", error);
  }
};


/**
 * Handle getCachedStats
 * @param {Object} params
 * @param {string} params.communityId: community ID
 * @param {string} params.dashboardType: one of "global", "community"
 * @param {string} params.dateBasis: date basis used to calculate record counts
 *   ("added", "created", "published")
 * @param {string} params.blockStartDate: start date of the block
 *   in YYYY-MM-DD format
 * @param {string} params.blockEndDate: end date of the block
 *   in YYYY-MM-DD format
 * @param {boolean} params.requestCompressedJson: whether to request compressed json from the API
 * @param {boolean} params.cacheCompressedJson: whether to cache compressed json
 * @returns {Promise<Object>} result of the getCachedStats operation
 *   {
 *     success: true,
 *     data: object,
 *     serverFetchTimestamp: number,
 *     year: number,
 *     isExpired: boolean,
 *   } or
 *   {
 *     success: false,
 *     error: string,
 *     data: null,
 *   }
 */
const handleGetCachedStats = async (params) => {
  try {
    const {
      communityId = "global",
      dashboardType,
      dateBasis = "added",
      blockStartDate,
      blockEndDate,
      requestCompressedJson,
      cacheCompressedJson,
    } = params;
    const cacheKey = generateCacheKey(
      communityId,
      dashboardType,
      dateBasis,
      blockStartDate,
      blockEndDate,
    );

    const db = await getDB();
    const getTransaction = db.transaction([STORE_NAME], "readonly");
    const getStore = getTransaction.objectStore(STORE_NAME);

    const record = await new Promise((resolve, reject) => {
      const request = getStore.get(cacheKey);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    if (!record) {
      return { success: true, data: null };
    }

    const serverFetchTimestamp = record.serverFetchTimestamp || null;
    const year = record.year || null;
    const recordData = record.data;
    const isCompressed = record.compressed === true; // Check compression flag (backward compatible with old records)

    const isValid = isCacheValid(record);

    if (!isValid && !updateInProgress(cacheKey)) {
      // Cache is expired - queue background update but still return expired data
      // negative id numbers to avoid collision with main thread ids
      const updateId = --backgroundUpdateIdCounter;
      messageQueue.push({
        type: "UPDATE_CACHED_STATS",
        id: updateId,
        params: {
          ...params,
          cacheKey,
        },
      });
      processQueue();

      // Continue to return the expired data so it can be displayed
      // The UI will show stale data while the background update happens
    }

    const { parsedData, errorMsg } = await processRetrievedData(
      recordData,
      isCompressed,
      cacheKey,
    );
    if (!parsedData) {
      return { success: true, data: null };
    } else if (errorMsg) {
      return { success: false, error: errorMsg, data: null };
    }
    updateLastAccessed(cacheKey);

    const result = {
      success: true,
      data: parsedData,
      serverFetchTimestamp: serverFetchTimestamp,
      year: year,
      isExpired: !isValid,
    };
    return result;
  } catch (error) {
    return { success: false, error: error.message, data: null };
  }
};

/**
 * Handle clearCachedStatsForKey message
 */
const handleClearCachedStatsForKey = async (params) => {
  try {
    const { cacheKey } = params;
    await deleteCacheEntry(cacheKey);
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
};

/**
 * Handle clearAllCachedStats message
 */
const handleClearAllCachedStats = async () => {
  try {
    const db = await getDB();
    const transaction = db.transaction([STORE_NAME], "readwrite");
    const store = transaction.objectStore(STORE_NAME);

    await new Promise((resolve, reject) => {
      const request = store.clear();
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });

    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
};

// Message queue with priority (GET operations processed before SET)
const messageQueue = [];
let isProcessing = false;
let backgroundUpdateIdCounter = 0; // Counter for background update IDs (uses negative numbers to avoid collision with main thread IDs)

// Priority: Lower number = higher priority
const MESSAGE_PRIORITY = {
  GET_CACHED_STATS: 1, // Highest priority - users are waiting
  CLEAR_CACHED_STATS_FOR_KEY: 2,
  CLEAR_ALL_CACHED_STATS: 2,
  SET_CACHED_STATS: 10, // Lowest priority - can wait
  UPDATE_CACHED_STATS: 10,
};

// Process messages from queue (prioritizes GET over SET)
const processQueue = async () => {
  if (isProcessing || messageQueue.length === 0) {
    return;
  }

  isProcessing = true;

  while (messageQueue.length > 0) {
    // Sort queue by priority (GETs first)
    messageQueue.sort((a, b) => {
      const priorityA = MESSAGE_PRIORITY[a.type] || 100;
      const priorityB = MESSAGE_PRIORITY[b.type] || 100;
      return priorityA - priorityB;
    });

    const { type, id, params } = messageQueue.shift();
    let result;

    try {
      switch (type) {
        case "SET_CACHED_STATS":
          result = await handleSetCachedStats(params);
          break;
        case "GET_CACHED_STATS":
          result = await handleGetCachedStats(params);
          break;
        case "UPDATE_CACHED_STATS":
          result = await handleUpdateCachedStats(params);
          break;
        case "CLEAR_CACHED_STATS_FOR_KEY":
          result = await handleClearCachedStatsForKey(params);
          break;
        case "CLEAR_ALL_CACHED_STATS":
          result = await handleClearAllCachedStats();
          break;
        default:
          result = { success: false, error: `Unknown message type: ${type}` };
      }

      // Send result back to main thread (skip for background UPDATE_CACHED_STATS)
      // UPDATE_CACHED_STATS is triggered internally and doesn't need a response
      if (type !== "UPDATE_CACHED_STATS") {
        self.postMessage({ id, type, result });
      } else {
        self.postMessage({ type: "CACHE_UPDATED", result });
      }
    } catch (error) {
      self.postMessage({
        id,
        type,
        result: { success: false, error: error.message },
      });
    }
  }

  isProcessing = false;
};

// Listen for messages from the main thread
self.addEventListener("message", (event) => {
  const { type, id, params } = event.data;

  messageQueue.push({ type, id, params });

  processQueue();
});
