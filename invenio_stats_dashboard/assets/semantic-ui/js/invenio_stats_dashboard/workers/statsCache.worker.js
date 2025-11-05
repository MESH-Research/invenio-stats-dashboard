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

// Import pako for compression/decompression
// Note: This requires pako to be available as an ES module in your build system
// If using webpack/vite, ensure pako is bundled for the worker context
import pako from 'pako';

const DB_NAME = 'invenio_stats_dashboard';
const DB_VERSION = 2; // Increment version to add new indices
const STORE_NAME = 'stats_cache';
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
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'key' });
        store.createIndex('timestamp', 'timestamp', { unique: false });
        store.createIndex('lastAccessed', 'lastAccessed', { unique: false });
        store.createIndex('communityId', 'communityId', { unique: false });
        store.createIndex('year', 'year', { unique: false });
        store.createIndex('dateBasis', 'dateBasis', { unique: false });
      } else {
        // Upgrade existing store - add new indices if they don't exist
        const store = transaction.objectStore(STORE_NAME);
        
        // Check and create indices safely - wrap in try-catch to handle if index already exists
        try {
          if (!store.indexNames.contains('year')) {
            store.createIndex('year', 'year', { unique: false });
          }
        } catch (e) {
          // Index might already exist, ignore
          console.warn('Index "year" may already exist:', e);
        }
        
        try {
          if (!store.indexNames.contains('dateBasis')) {
            store.createIndex('dateBasis', 'dateBasis', { unique: false });
          }
        } catch (e) {
          // Index might already exist, ignore
          console.warn('Index "dateBasis" may already exist:', e);
        }
        
        try {
          if (!store.indexNames.contains('lastAccessed')) {
            store.createIndex('lastAccessed', 'lastAccessed', { unique: false });
          }
        } catch (e) {
          // Index might already exist, ignore
          console.warn('Index "lastAccessed" may already exist:', e);
        }
      }
    };
  });
};

/**
 * Generate cache key for stats data
 * Includes: communityId, dashboardType, dateBasis, startDate, endDate
 */
const generateCacheKey = (communityId, dashboardType, dateBasis = 'added', startDate = null, endDate = null) => {
  const communityIdShort = communityId ? communityId.substring(0, 8) : 'global';
  const startDateShort = startDate ? startDate.substring(0, 10) : 'default';
  const endDateShort = endDate ? endDate.substring(0, 10) : 'default';

  return `isd_${communityIdShort}_${dashboardType}_${dateBasis}_${startDateShort}_${endDateShort}`;
};

/**
 * Extract year from date string (YYYY-MM-DD format)
 */
const extractYear = (startDate) => {
  if (!startDate) return null;
  const yearMatch = startDate.match(/^(\d{4})/);
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
    const evictTransaction = db.transaction([STORE_NAME], 'readwrite');
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
      const toDelete = allEntries.slice(0, Math.min(countToEvict, allEntries.length));

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
 * Handle setCachedStats message
 */
const handleSetCachedStats = async (params) => {
  try {
    const { communityId = 'global', dashboardType, transformedData, dateBasis = 'added', startDate, endDate, year } = params;
    const cacheKey = generateCacheKey(communityId, dashboardType, dateBasis, startDate, endDate);
    console.log('[SET] Generated cache key:', cacheKey, 'from params:', { communityId, dashboardType, dateBasis, startDate, endDate });
    const timestamp = Date.now();
    
    const cacheYear = year || extractYear(startDate);

    const jsonString = JSON.stringify(transformedData);
    const compressedData = pako.gzip(jsonString);
    const arrayBuffer = compressedData.buffer.slice(
      compressedData.byteOffset,
      compressedData.byteOffset + compressedData.byteLength
    );

    const db = await getDB();
    
    const checkTransaction = db.transaction([STORE_NAME], 'readonly');
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
      })
    ]);

    // If adding new entry (not updating existing) and at limit, evict oldest first
    if (!existingRecord && totalEntries >= MAX_CACHE_ENTRIES) {
      const countToEvict = totalEntries - MAX_CACHE_ENTRIES + 1; // +1 for the new entry
      await evictOldestEntries(db, countToEvict);
    }

    // Store the entry (separate transaction)
    const storeTransaction = db.transaction([STORE_NAME], 'readwrite');
    const store = storeTransaction.objectStore(STORE_NAME);
    const isCurrent = isCurrentYear(cacheYear);
    
    const cacheRecord = {
      key: cacheKey,
      data: arrayBuffer,
      timestamp,
      lastAccessed: timestamp, // Update lastAccessed when storing
      communityId,
      dashboardType,
      dateBasis,
      startDate,
      endDate,
      year: cacheYear,
      compressed: true,
      originalSize: jsonString.length,
      compressedSize: compressedData.length,
      version: '2.0',
      // Store server fetch time for current year (used for "last updated" display)
      serverFetchTimestamp: isCurrent ? timestamp : null
    };

    await new Promise((resolve, reject) => {
      const request = store.put(cacheRecord);
      request.onsuccess = () => {
        console.log('[SET] Successfully stored cache key:', cacheKey);
        resolve();
      };
      request.onerror = () => {
        console.error('[SET] Failed to store cache key:', cacheKey, 'Error:', request.error);
        reject(request.error);
      };
    });

    return { success: true, cacheKey, compressedRatio: compressedData.length / jsonString.length };
  } catch (error) {
    return { success: false, error: error.message };
  }
};

/**
 * Handle getCachedStats
 */
const handleGetCachedStats = async (params) => {
  try {
    const { communityId = 'global', dashboardType, dateBasis = 'added', startDate, endDate } = params;
    const cacheKey = generateCacheKey(communityId, dashboardType, dateBasis, startDate, endDate);
    console.log('[GET] Generated cache key:', cacheKey, 'from params:', { communityId, dashboardType, dateBasis, startDate, endDate });

    const db = await getDB();
    const getTransaction = db.transaction([STORE_NAME], 'readonly');
    const getStore = getTransaction.objectStore(STORE_NAME);

    const record = await new Promise((resolve, reject) => {
      const request = getStore.get(cacheKey);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });

    if (!record) {
      // Debug: List all keys to see what's actually stored
      const getAllKeysRequest = getStore.getAllKeys();
      getAllKeysRequest.onsuccess = () => {
        console.warn('[GET] No record found for key:', cacheKey);
        console.warn('[GET] Available keys in store:', getAllKeysRequest.result);
        // Check if any keys are similar (might indicate a mismatch)
        const similarKeys = getAllKeysRequest.result.filter(key => 
          typeof key === 'string' && key.includes(dashboardType) && key.includes(dateBasis)
        );
        if (similarKeys.length > 0) {
          console.warn('[GET] Similar keys found:', similarKeys);
        }
      };
      return { success: true, data: null };
    }

    // Extract metadata before transaction completes (record is still valid after transaction)
    const serverFetchTimestamp = record.serverFetchTimestamp || null;
    const year = record.year || null;
    // data is stored as ArrayBuffer (for Safari compatibility), not Blob
    const recordData = record.data;

    if (!isCacheValid(record)) {
      // Delete expired cache
      const deleteTransaction = db.transaction([STORE_NAME], 'readwrite');
      const deleteStore = deleteTransaction.objectStore(STORE_NAME);
      await new Promise((resolve, reject) => {
        const request = deleteStore.delete(cacheKey);
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
      return { success: true, data: null };
    }

    // Decompress the data
    // Handle both ArrayBuffer (new format, Safari-compatible) and Blob (old format, for backward compatibility)
    // FIXME: Remove legacy Blob handling 
    let arrayBuffer;
    if (recordData instanceof ArrayBuffer) {
      arrayBuffer = recordData;
    } else if (recordData && typeof recordData.arrayBuffer === 'function') {
      // Old format: stored as Blob (convert to ArrayBuffer)
      try {
        arrayBuffer = await recordData.arrayBuffer();
      } catch (error) {
        console.warn('Failed to read Blob data (Safari compatibility issue), cache entry will be re-fetched:', error);
        return { success: true, data: null };
      }
    } else {
      // Fallback: try to use as-is (shouldn't happen)
      arrayBuffer = recordData;
    }
    const compressedData = new Uint8Array(arrayBuffer);
    const decompressedData = JSON.parse(pako.ungzip(compressedData, { to: 'string' }));

    const updateLastAccessed = async () => {
      try {
        const updateDb = await getDB();
        const updateTransaction = updateDb.transaction([STORE_NAME], 'readwrite');
        const updateStore = updateTransaction.objectStore(STORE_NAME);
        
        // Get fresh record to ensure we have all properties including ArrayBuffer
        const freshRecord = await new Promise((resolve, reject) => {
          const getRequest = updateStore.get(cacheKey);
          getRequest.onsuccess = () => resolve(getRequest.result);
          getRequest.onerror = () => reject(getRequest.error);
        });

        if (freshRecord) {
          const updatedRecord = {
            ...freshRecord,
            lastAccessed: Date.now()
          };
          
          await new Promise((resolve, reject) => {
            const updateRequest = updateStore.put(updatedRecord);
            updateRequest.onsuccess = () => resolve();
            updateRequest.onerror = () => reject(updateRequest.error);
          });
        }
      } catch (error) {
        // Silently fail - LRU update is not critical for returning cached data
        console.warn('Failed to update lastAccessed timestamp:', error);
      }
    };
    
    // Fire off the update but don't wait for it
    updateLastAccessed();

    // Return data immediately along with metadata for current year's server fetch time
    return { 
      success: true, 
      data: decompressedData,
      serverFetchTimestamp: serverFetchTimestamp,
      year: year
    };
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

    const db = await getDB();
    const transaction = db.transaction([STORE_NAME], 'readwrite');
    const store = transaction.objectStore(STORE_NAME);

    await new Promise((resolve, reject) => {
      const request = store.delete(cacheKey);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });

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
    const transaction = db.transaction([STORE_NAME], 'readwrite');
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

// Priority: Lower number = higher priority
const MESSAGE_PRIORITY = {
  'GET_CACHED_STATS': 1,           // Highest priority - users are waiting
  'CLEAR_CACHED_STATS_FOR_KEY': 2,
  'CLEAR_ALL_CACHED_STATS': 2,
  'SET_CACHED_STATS': 10,          // Lowest priority - can wait
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
        case 'SET_CACHED_STATS':
          result = await handleSetCachedStats(params);
          break;
        case 'GET_CACHED_STATS':
          result = await handleGetCachedStats(params);
          break;
        case 'CLEAR_CACHED_STATS_FOR_KEY':
          result = await handleClearCachedStatsForKey(params);
          break;
        case 'CLEAR_ALL_CACHED_STATS':
          result = await handleClearAllCachedStats();
          break;
        default:
          result = { success: false, error: `Unknown message type: ${type}` };
      }

      // Send result back to main thread
      self.postMessage({ id, type, result });
    } catch (error) {
      self.postMessage({ 
        id, 
        type, 
        result: { success: false, error: error.message } 
      });
    }
  }

  isProcessing = false;
};

// Listen for messages from the main thread
self.addEventListener('message', (event) => {
  const { type, id, params } = event.data;

  // Add message to queue
  messageQueue.push({ type, id, params });

  // Process queue (will handle priority sorting)
  processQueue();
});

