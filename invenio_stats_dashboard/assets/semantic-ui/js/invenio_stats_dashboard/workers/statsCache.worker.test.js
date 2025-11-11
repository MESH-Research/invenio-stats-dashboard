/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 */

// Polyfill TextEncoder/TextDecoder for Node.js test environment
global.TextEncoder = global.TextEncoder || class TextEncoder {
  encode(str) {
    return new Uint8Array(Buffer.from(str, 'utf8'));
  }
};

global.TextDecoder = global.TextDecoder || class TextDecoder {
  decode(bytes) {
    return Buffer.from(bytes).toString('utf8');
  }
};

// Mock pako for compression (only used when compression is enabled)
jest.mock('pako', () => ({
  gzip: jest.fn((data) => {
    // Simple mock: return compressed data as Uint8Array
    const encoder = new TextEncoder();
    return encoder.encode(data);
  }),
  ungzip: jest.fn((data, options) => {
    // Simple mock: return decompressed string
    const decoder = new TextDecoder();
    return decoder.decode(data);
  }),
}));

// Mock IndexedDB
const mockIndexedDB = () => {
  const store = new Map();
  const indexes = {
    timestamp: new Map(),
    lastAccessed: new Map(),
    communityId: new Map(),
    year: new Map(),
    dateBasis: new Map(),
  };

  const objectStore = {
    get: jest.fn((key) => ({
      onsuccess: null,
      onerror: null,
      result: store.get(key) || undefined,
    })),
    put: jest.fn((value) => {
      store.set(value.key, value);
      // Update indexes
      if (value.timestamp) indexes.timestamp.set(value.timestamp, value);
      if (value.lastAccessed) indexes.lastAccessed.set(value.lastAccessed, value);
      if (value.communityId) indexes.communityId.set(value.communityId, value);
      if (value.year !== undefined) indexes.year.set(value.year, value);
      if (value.dateBasis) indexes.dateBasis.set(value.dateBasis, value);
      return {
        onsuccess: null,
        onerror: null,
        result: value.key,
      };
    }),
    delete: jest.fn((key) => {
      const value = store.get(key);
      if (value) {
        store.delete(key);
        // Remove from indexes
        if (value.timestamp) indexes.timestamp.delete(value.timestamp);
        if (value.lastAccessed) indexes.lastAccessed.delete(value.lastAccessed);
        if (value.communityId) indexes.communityId.delete(value.communityId);
        if (value.year !== undefined) indexes.year.delete(value.year);
        if (value.dateBasis) indexes.dateBasis.delete(value.dateBasis);
      }
      return {
        onsuccess: null,
        onerror: null,
      };
    }),
    clear: jest.fn(() => {
      store.clear();
      Object.values(indexes).forEach(index => index.clear());
      return {
        onsuccess: null,
        onerror: null,
      };
    }),
    getAll: jest.fn(() => ({
      onsuccess: null,
      onerror: null,
      result: Array.from(store.values()),
    })),
    count: jest.fn(() => ({
      onsuccess: null,
      onerror: null,
      result: store.size,
    })),
    indexNames: {
      contains: jest.fn((name) => Object.keys(indexes).includes(name)),
    },
    createIndex: jest.fn(),
  };

  const transaction = {
    objectStore: jest.fn(() => objectStore),
  };

  const db = {
    objectStoreNames: {
      contains: jest.fn((name) => name === 'stats_cache'),
    },
    transaction: jest.fn(() => transaction),
    createObjectStore: jest.fn(() => objectStore),
  };

  let dbInstance = null;

  const request = {
    onsuccess: null,
    onerror: null,
    onupgradeneeded: null,
    result: db,
  };

  return {
    open: jest.fn((name, version) => {
      // Simulate successful open
      setTimeout(() => {
        if (request.onupgradeneeded && version === 2) {
          request.onupgradeneeded({
            target: { result: db },
            transaction,
          });
        }
        if (request.onsuccess) {
          request.onsuccess({ target: { result: db } });
        }
      }, 0);
      return request;
    }),
    store,
    db,
    transaction,
    objectStore,
  };
};

describe('StatsCache Worker', () => {
  let workerContext;
  let mockIDB;
  let originalIndexedDB;
  let originalSelf;

  beforeEach(() => {
    // Mock IndexedDB
    mockIDB = mockIndexedDB();
    originalIndexedDB = global.indexedDB;
    global.indexedDB = mockIDB;

    // Mock worker context
    originalSelf = global.self;
    global.self = {
      addEventListener: jest.fn(),
      postMessage: jest.fn(),
    };

    // Create a mock worker context that simulates the worker
    workerContext = {
      pendingMessages: new Map(),
      messageHandlers: new Map(),
    };
  });

  afterEach(() => {
    jest.clearAllMocks();
    global.indexedDB = originalIndexedDB;
    global.self = originalSelf;
  });

  describe('Cache Key Generation', () => {
    it('should generate cache keys with community ID and dates', async () => {
      // Import and test the worker logic directly
      // Since we can't easily import a worker file, we'll test the key generation logic
      const generateCacheKey = (communityId, dashboardType, dateBasis = 'added', startDate = null, endDate = null) => {
        const communityIdShort = communityId ? communityId.substring(0, 8) : 'global';
        const startDateShort = startDate ? startDate.substring(0, 10) : 'default';
        const endDateShort = endDate ? endDate.substring(0, 10) : 'default';
        return `isd_${communityIdShort}_${dashboardType}_${dateBasis}_${startDateShort}_${endDateShort}`;
      };

      const key = generateCacheKey('test-community-123', 'community', 'added', '2024-01-01', '2024-01-31');
      expect(key).toBe('isd_test-com_community_added_2024-01-01_2024-01-31');
    });

    it('should handle null dates in cache key generation', () => {
      const generateCacheKey = (communityId, dashboardType, dateBasis = 'added', startDate = null, endDate = null) => {
        const communityIdShort = communityId ? communityId.substring(0, 8) : 'global';
        const startDateShort = startDate ? startDate.substring(0, 10) : 'default';
        const endDateShort = endDate ? endDate.substring(0, 10) : 'default';
        return `isd_${communityIdShort}_${dashboardType}_${dateBasis}_${startDateShort}_${endDateShort}`;
      };

      const key = generateCacheKey('test-community', 'community', 'added', null, null);
      expect(key).toBe('isd_test-com_community_added_default_default');
    });
  });

  describe('Year Extraction', () => {
    it('should extract year from date string', () => {
      const extractYear = (startDate) => {
        if (!startDate) return null;
        const yearMatch = startDate.match(/^(\d{4})/);
        return yearMatch ? parseInt(yearMatch[1], 10) : null;
      };

      expect(extractYear('2024-01-01')).toBe(2024);
      expect(extractYear('2023-12-31')).toBe(2023);
      expect(extractYear(null)).toBeNull();
      expect(extractYear('invalid')).toBeNull();
    });
  });

  describe('Current Year Detection', () => {
    it('should detect current year correctly', () => {
      const isCurrentYear = (year) => {
        if (!year) return false;
        const currentYear = new Date().getUTCFullYear();
        return year === currentYear;
      };

      const currentYear = new Date().getUTCFullYear();
      expect(isCurrentYear(currentYear)).toBe(true);
      expect(isCurrentYear(currentYear - 1)).toBe(false);
      expect(isCurrentYear(currentYear + 1)).toBe(false);
      expect(isCurrentYear(null)).toBe(false);
    });
  });

  describe('Cache Validity', () => {
    it('should return false for invalid cache data', () => {
      const isCacheValid = (cachedData) => {
        if (!cachedData || !cachedData.timestamp) {
          return false;
        }

        const now = Date.now();
        const cacheAge = now - cachedData.timestamp;
        const year = cachedData.year;
        const isCurrent = year === new Date().getUTCFullYear();
        const maxAge = isCurrent
          ? 1 * 60 * 60 * 1000 // 1 hour
          : 1 * 365 * 24 * 60 * 60 * 1000; // 1 year

        return cacheAge < maxAge;
      };

      expect(isCacheValid(null)).toBe(false);
      expect(isCacheValid({})).toBe(false);
    });

    it('should return true for valid current year cache (within 1 hour)', () => {
      const currentYear = new Date().getUTCFullYear();
      const isCacheValid = (cachedData) => {
        if (!cachedData || !cachedData.timestamp) {
          return false;
        }

        const now = Date.now();
        const cacheAge = now - cachedData.timestamp;
        const year = cachedData.year;
        const isCurrent = year === new Date().getUTCFullYear();
        const maxAge = isCurrent
          ? 1 * 60 * 60 * 1000 // 1 hour
          : 1 * 365 * 24 * 60 * 60 * 1000; // 1 year

        return cacheAge < maxAge;
      };

      const cachedData = {
        timestamp: Date.now() - 30 * 60 * 1000, // 30 minutes ago
        year: currentYear,
      };

      expect(isCacheValid(cachedData)).toBe(true);
    });

    it('should return false for expired current year cache (over 1 hour)', () => {
      const currentYear = new Date().getUTCFullYear();
      const isCacheValid = (cachedData) => {
        if (!cachedData || !cachedData.timestamp) {
          return false;
        }

        const now = Date.now();
        const cacheAge = now - cachedData.timestamp;
        const year = cachedData.year;
        const isCurrent = year === new Date().getUTCFullYear();
        const maxAge = isCurrent
          ? 1 * 60 * 60 * 1000 // 1 hour
          : 1 * 365 * 24 * 60 * 60 * 1000; // 1 year

        return cacheAge < maxAge;
      };

      const cachedData = {
        timestamp: Date.now() - 2 * 60 * 60 * 1000, // 2 hours ago
        year: currentYear,
      };

      expect(isCacheValid(cachedData)).toBe(false);
    });

    it('should return true for valid past year cache (within 1 year)', () => {
      const pastYear = new Date().getUTCFullYear() - 1;
      const isCacheValid = (cachedData) => {
        if (!cachedData || !cachedData.timestamp) {
          return false;
        }

        const now = Date.now();
        const cacheAge = now - cachedData.timestamp;
        const year = cachedData.year;
        const isCurrent = year === new Date().getUTCFullYear();
        const maxAge = isCurrent
          ? 1 * 60 * 60 * 1000 // 1 hour
          : 1 * 365 * 24 * 60 * 60 * 1000; // 1 year

        return cacheAge < maxAge;
      };

      const cachedData = {
        timestamp: Date.now() - 30 * 24 * 60 * 60 * 1000, // 30 days ago
        year: pastYear,
      };

      expect(isCacheValid(cachedData)).toBe(true);
    });

    it('should return false for expired past year cache (over 1 year)', () => {
      const pastYear = new Date().getUTCFullYear() - 1;
      const isCacheValid = (cachedData) => {
        if (!cachedData || !cachedData.timestamp) {
          return false;
        }

        const now = Date.now();
        const cacheAge = now - cachedData.timestamp;
        const year = cachedData.year;
        const isCurrent = year === new Date().getUTCFullYear();
        const maxAge = isCurrent
          ? 1 * 60 * 60 * 1000 // 1 hour
          : 1 * 365 * 24 * 60 * 60 * 1000; // 1 year

        return cacheAge < maxAge;
      };

      const cachedData = {
        timestamp: Date.now() - 2 * 365 * 24 * 60 * 60 * 1000, // 2 years ago
        year: pastYear,
      };

      expect(isCacheValid(cachedData)).toBe(false);
    });
  });

  describe('Worker Message Handling', () => {
    // Note: These tests simulate worker message handling since we can't directly test
    // the worker file in Jest. In a real environment, you might use worker-loader or
    // a similar tool to test workers.

    it('should handle SET_CACHED_STATS message type without compression', async () => {
      // Simulate the handleSetCachedStats function
      const handleSetCachedStats = async (params) => {
        const { communityId, dashboardType, transformedData, dateBasis = 'added', startDate, endDate, year, compressionEnabled = false } = params;
        const generateCacheKey = (communityId, dashboardType, dateBasis, startDate, endDate) => {
          const communityIdShort = communityId ? communityId.substring(0, 8) : 'global';
          const startDateShort = startDate ? startDate.substring(0, 10) : 'default';
          const endDateShort = endDate ? endDate.substring(0, 10) : 'default';
          return `isd_${communityIdShort}_${dashboardType}_${dateBasis}_${startDateShort}_${endDateShort}`;
        };

        const cacheKey = generateCacheKey(communityId, dashboardType, dateBasis, startDate, endDate);
        const timestamp = Date.now();
        const cacheYear = year || (startDate ? parseInt(startDate.substring(0, 4), 10) : null);

        // When compression is disabled: store object directly
        const dataToStore = compressionEnabled ? null : transformedData;

        // Store would happen here - mocked for test
        return {
          success: true,
          cacheKey,
          compressed: compressionEnabled,
        };
      };

      const result = await handleSetCachedStats({
        communityId: 'test-community',
        dashboardType: 'community',
        transformedData: { test: 'data' },
        dateBasis: 'added',
        startDate: '2024-01-01',
        endDate: '2024-01-31',
        year: 2024,
        compressionEnabled: false,
      });

      expect(result.success).toBe(true);
      expect(result.cacheKey).toContain('test-com');
      expect(result.cacheKey).toContain('community');
      expect(result.compressed).toBe(false);
    });

    it('should handle SET_CACHED_STATS message type with compression', async () => {
      // Simulate the handleSetCachedStats function
      const handleSetCachedStats = async (params) => {
        const { communityId, dashboardType, transformedData, dateBasis = 'added', startDate, endDate, year, compressionEnabled = false } = params;
        const generateCacheKey = (communityId, dashboardType, dateBasis, startDate, endDate) => {
          const communityIdShort = communityId ? communityId.substring(0, 8) : 'global';
          const startDateShort = startDate ? startDate.substring(0, 10) : 'default';
          const endDateShort = endDate ? endDate.substring(0, 10) : 'default';
          return `isd_${communityIdShort}_${dashboardType}_${dateBasis}_${startDateShort}_${endDateShort}`;
        };

        const cacheKey = generateCacheKey(communityId, dashboardType, dateBasis, startDate, endDate);
        const timestamp = Date.now();
        const cacheYear = year || (startDate ? parseInt(startDate.substring(0, 4), 10) : null);

        // Always calculate object size
        const jsonString = JSON.stringify(transformedData);
        const objectSize = jsonString.length;

        // When compression is enabled: stringify, compress, store as ArrayBuffer
        if (compressionEnabled) {
          const compressedData = new TextEncoder().encode(jsonString); // Mock compression
          const arrayBuffer = compressedData.buffer;
          return {
            success: true,
            cacheKey,
            compressed: true,
            objectSize: objectSize,
          };
        }

        return {
          success: true,
          cacheKey,
          compressed: false,
          objectSize: objectSize,
        };
      };

      const result = await handleSetCachedStats({
        communityId: 'test-community',
        dashboardType: 'community',
        transformedData: { test: 'data' },
        dateBasis: 'added',
        startDate: '2024-01-01',
        endDate: '2024-01-31',
        year: 2024,
        compressionEnabled: true,
      });

      expect(result.success).toBe(true);
      expect(result.cacheKey).toContain('test-com');
      expect(result.cacheKey).toContain('community');
      expect(result.compressed).toBe(true);
      expect(result.objectSize).toBeGreaterThan(0);
    });

    it('should handle GET_CACHED_STATS message type with uncompressed object', async () => {
      // Data is stored as object directly (no compression)
      const mockCachedData = {
        key: 'isd_test-com_community_added_2024-01-01_2024-01-31',
        data: { test: 'data' }, // Stored as object directly
        compressed: false,
        timestamp: Date.now() - 1000,
        lastAccessed: Date.now() - 1000,
        year: 2024,
        serverFetchTimestamp: Date.now() - 1000,
      };

      // Simulate handleGetCachedStats
      const handleGetCachedStats = async (params) => {
        const { communityId, dashboardType, dateBasis = 'added', startDate, endDate } = params;
        const generateCacheKey = (communityId, dashboardType, dateBasis, startDate, endDate) => {
          const communityIdShort = communityId ? communityId.substring(0, 8) : 'global';
          const startDateShort = startDate ? startDate.substring(0, 10) : 'default';
          const endDateShort = endDate ? endDate.substring(0, 10) : 'default';
          return `isd_${communityIdShort}_${dashboardType}_${dateBasis}_${startDateShort}_${endDateShort}`;
        };

        const cacheKey = generateCacheKey(communityId, dashboardType, dateBasis, startDate, endDate);

        // Simulate finding cached data
        if (cacheKey === mockCachedData.key) {
          // Check validity
          const isCacheValid = (cachedData) => {
            if (!cachedData || !cachedData.timestamp) return false;
            const now = Date.now();
            const cacheAge = now - cachedData.timestamp;
            const year = cachedData.year;
            const isCurrent = year === new Date().getUTCFullYear();
            const maxAge = isCurrent ? 1 * 60 * 60 * 1000 : 1 * 365 * 24 * 60 * 60 * 1000;
            return cacheAge < maxAge;
          };

          // Use object directly (no parsing needed)
          const isCompressed = mockCachedData.compressed === true;
          const parsedData = isCompressed ? null : mockCachedData.data;
          const isValid = isCacheValid(mockCachedData);

          return {
            success: true,
            data: parsedData,
            serverFetchTimestamp: mockCachedData.serverFetchTimestamp,
            year: mockCachedData.year,
            isExpired: !isValid,
          };
        }

        return { success: true, data: null };
      };

      const result = await handleGetCachedStats({
        communityId: 'test-community',
        dashboardType: 'community',
        dateBasis: 'added',
        startDate: '2024-01-01',
        endDate: '2024-01-31',
      });

      expect(result.success).toBe(true);
      expect(result.data).toEqual({ test: 'data' });
      expect(result.serverFetchTimestamp).toBeDefined();
      expect(result.year).toBe(2024);
      expect(result.isExpired).toBe(false); // Valid cache should have isExpired: false
    });

    it('should handle GET_CACHED_STATS message type with compressed data', async () => {
      // Data is stored as compressed ArrayBuffer
      const mockCompressedData = new TextEncoder().encode(JSON.stringify({ test: 'data' }));
      const mockCachedData = {
        key: 'isd_test-com_community_added_2024-01-01_2024-01-31',
        data: mockCompressedData.buffer, // Stored as ArrayBuffer
        compressed: true,
        timestamp: Date.now() - 1000,
        lastAccessed: Date.now() - 1000,
        year: 2024,
        serverFetchTimestamp: Date.now() - 1000,
      };

      // Simulate handleGetCachedStats
      const handleGetCachedStats = async (params) => {
        const { communityId, dashboardType, dateBasis = 'added', startDate, endDate } = params;
        const generateCacheKey = (communityId, dashboardType, dateBasis, startDate, endDate) => {
          const communityIdShort = communityId ? communityId.substring(0, 8) : 'global';
          const startDateShort = startDate ? startDate.substring(0, 10) : 'default';
          const endDateShort = endDate ? endDate.substring(0, 10) : 'default';
          return `isd_${communityIdShort}_${dashboardType}_${dateBasis}_${startDateShort}_${endDateShort}`;
        };

        const cacheKey = generateCacheKey(communityId, dashboardType, dateBasis, startDate, endDate);

        // Simulate finding cached data
        if (cacheKey === mockCachedData.key) {
          // Check validity
          const isCacheValid = (cachedData) => {
            if (!cachedData || !cachedData.timestamp) return false;
            const now = Date.now();
            const cacheAge = now - cachedData.timestamp;
            const year = cachedData.year;
            const isCurrent = year === new Date().getUTCFullYear();
            const maxAge = isCurrent ? 1 * 60 * 60 * 1000 : 1 * 365 * 24 * 60 * 60 * 1000;
            return cacheAge < maxAge;
          };

          // Decompress and parse
          const isCompressed = mockCachedData.compressed === true;
          let parsedData;
          if (isCompressed) {
            const compressedData = new Uint8Array(mockCachedData.data);
            const decompressedString = new TextDecoder().decode(compressedData); // Mock decompression
            parsedData = JSON.parse(decompressedString);
          } else {
            parsedData = mockCachedData.data;
          }
          const isValid = isCacheValid(mockCachedData);

          return {
            success: true,
            data: parsedData,
            serverFetchTimestamp: mockCachedData.serverFetchTimestamp,
            year: mockCachedData.year,
            isExpired: !isValid,
          };
        }

        return { success: true, data: null };
      };

      const result = await handleGetCachedStats({
        communityId: 'test-community',
        dashboardType: 'community',
        dateBasis: 'added',
        startDate: '2024-01-01',
        endDate: '2024-01-31',
      });

      expect(result.success).toBe(true);
      expect(result.data).toEqual({ test: 'data' });
      expect(result.serverFetchTimestamp).toBeDefined();
      expect(result.year).toBe(2024);
      expect(result.isExpired).toBe(false); // Valid cache should have isExpired: false
    });

    it('should handle GET_CACHED_STATS message type with legacy JSON string (backward compatibility)', async () => {
      // Legacy data stored as JSON string (for backward compatibility)
      const mockCachedData = {
        key: 'isd_test-com_community_added_2024-01-01_2024-01-31',
        data: JSON.stringify({ test: 'data' }), // Legacy: stored as JSON string
        compressed: false, // or undefined for old entries
        timestamp: Date.now() - 1000,
        lastAccessed: Date.now() - 1000,
        year: 2024,
        serverFetchTimestamp: Date.now() - 1000,
      };

      // Simulate handleGetCachedStats
      const handleGetCachedStats = async (params) => {
        const { communityId, dashboardType, dateBasis = 'added', startDate, endDate } = params;
        const generateCacheKey = (communityId, dashboardType, dateBasis, startDate, endDate) => {
          const communityIdShort = communityId ? communityId.substring(0, 8) : 'global';
          const startDateShort = startDate ? startDate.substring(0, 10) : 'default';
          const endDateShort = endDate ? endDate.substring(0, 10) : 'default';
          return `isd_${communityIdShort}_${dashboardType}_${dateBasis}_${startDateShort}_${endDateShort}`;
        };

        const cacheKey = generateCacheKey(communityId, dashboardType, dateBasis, startDate, endDate);

        // Simulate finding cached data
        if (cacheKey === mockCachedData.key) {
          // Check validity
          const isCacheValid = (cachedData) => {
            if (!cachedData || !cachedData.timestamp) return false;
            const now = Date.now();
            const cacheAge = now - cachedData.timestamp;
            const year = cachedData.year;
            const isCurrent = year === new Date().getUTCFullYear();
            const maxAge = isCurrent ? 1 * 60 * 60 * 1000 : 1 * 365 * 24 * 60 * 60 * 1000;
            return cacheAge < maxAge;
          };

          // Handle backward compatibility: parse JSON string
          const isCompressed = mockCachedData.compressed === true;
          let parsedData;
          if (isCompressed) {
            // Shouldn't happen in this test, but handle it
            parsedData = null;
          } else if (typeof mockCachedData.data === 'string') {
            // Legacy: parse JSON string
            parsedData = JSON.parse(mockCachedData.data);
          } else {
            // New format: use object directly
            parsedData = mockCachedData.data;
          }
          const isValid = isCacheValid(mockCachedData);

          return {
            success: true,
            data: parsedData,
            serverFetchTimestamp: mockCachedData.serverFetchTimestamp,
            year: mockCachedData.year,
            isExpired: !isValid,
          };
        }

        return { success: true, data: null };
      };

      const result = await handleGetCachedStats({
        communityId: 'test-community',
        dashboardType: 'community',
        dateBasis: 'added',
        startDate: '2024-01-01',
        endDate: '2024-01-31',
      });

      expect(result.success).toBe(true);
      expect(result.data).toEqual({ test: 'data' });
      expect(result.serverFetchTimestamp).toBeDefined();
      expect(result.year).toBe(2024);
      expect(result.isExpired).toBe(false); // Valid cache should have isExpired: false
    });

    it('should return null for missing cache', async () => {
      const handleGetCachedStats = async () => {
        return { success: true, data: null };
      };

      const result = await handleGetCachedStats({
        communityId: 'nonexistent',
        dashboardType: 'community',
        dateBasis: 'added',
        startDate: '2024-01-01',
        endDate: '2024-01-31',
      });

      expect(result.success).toBe(true);
      expect(result.data).toBeNull();
    });

    it('should return expired data with isExpired flag when cache is expired', async () => {
      const currentYear = new Date().getUTCFullYear();
      const mockExpiredData = {
        key: 'isd_test-com_community_added_2024-01-01_2024-01-31',
        data: { test: 'expired data' },
        compressed: false,
        timestamp: Date.now() - 2 * 60 * 60 * 1000, // 2 hours ago (expired for current year)
        lastAccessed: Date.now() - 2 * 60 * 60 * 1000,
        year: currentYear,
        serverFetchTimestamp: Date.now() - 2 * 60 * 60 * 1000,
      };

      const messageQueue = [];
      const updateInProgress = (cacheKey) => {
        return messageQueue.some(
          (message) =>
            message.type === 'UPDATE_CACHED_STATS' &&
            message.params.cacheKey === cacheKey,
        );
      };

      const handleGetCachedStats = async (params) => {
        const { communityId, dashboardType, dateBasis = 'added', startDate, endDate } = params;
        const generateCacheKey = (communityId, dashboardType, dateBasis, startDate, endDate) => {
          const communityIdShort = communityId ? communityId.substring(0, 8) : 'global';
          const startDateShort = startDate ? startDate.substring(0, 10) : 'default';
          const endDateShort = endDate ? endDate.substring(0, 10) : 'default';
          return `isd_${communityIdShort}_${dashboardType}_${dateBasis}_${startDateShort}_${endDateShort}`;
        };

        const cacheKey = generateCacheKey(communityId, dashboardType, dateBasis, startDate, endDate);

        if (cacheKey === mockExpiredData.key) {
          const isCacheValid = (cachedData) => {
            if (!cachedData || !cachedData.timestamp) return false;
            const now = Date.now();
            const cacheAge = now - cachedData.timestamp;
            const year = cachedData.year;
            const isCurrent = year === new Date().getUTCFullYear();
            const maxAge = isCurrent ? 1 * 60 * 60 * 1000 : 1 * 365 * 24 * 60 * 60 * 1000;
            return cacheAge < maxAge;
          };

          const isValid = isCacheValid(mockExpiredData);

          // Simulate queuing background update if expired and not already in progress
          if (!isValid && !updateInProgress(cacheKey)) {
            messageQueue.push({
              type: 'UPDATE_CACHED_STATS',
              id: -1,
              params: {
                ...params,
                cacheKey,
              },
            });
          }

          // Return expired data with isExpired flag
          return {
            success: true,
            data: mockExpiredData.data,
            serverFetchTimestamp: mockExpiredData.serverFetchTimestamp,
            year: mockExpiredData.year,
            isExpired: !isValid,
          };
        }

        return { success: true, data: null };
      };

      const result = await handleGetCachedStats({
        communityId: 'test-community',
        dashboardType: 'community',
        dateBasis: 'added',
        startDate: '2024-01-01',
        endDate: '2024-01-31',
      });

      expect(result.success).toBe(true);
      expect(result.data).toEqual({ test: 'expired data' });
      expect(result.isExpired).toBe(true);
      expect(messageQueue.length).toBe(1);
      expect(messageQueue[0].type).toBe('UPDATE_CACHED_STATS');
      expect(messageQueue[0].params.cacheKey).toBe('isd_test-com_community_added_2024-01-01_2024-01-31');
    });

    it('should not queue duplicate background updates for expired cache', async () => {
      const currentYear = new Date().getUTCFullYear();
      const mockExpiredData = {
        key: 'isd_test-com_community_added_2024-01-01_2024-01-31',
        data: { test: 'expired data' },
        compressed: false,
        timestamp: Date.now() - 2 * 60 * 60 * 1000, // 2 hours ago (expired)
        year: currentYear,
      };

      const messageQueue = [
        {
          type: 'UPDATE_CACHED_STATS',
          id: -1,
          params: {
            communityId: 'test-community',
            dashboardType: 'community',
            dateBasis: 'added',
            blockStartDate: '2024-01-01',
            blockEndDate: '2024-01-31',
            cacheKey: 'isd_test-com_community_added_2024-01-01_2024-01-31',
          },
        },
      ];

      const updateInProgress = (cacheKey) => {
        return messageQueue.some(
          (message) =>
            message.type === 'UPDATE_CACHED_STATS' &&
            message.params.cacheKey === cacheKey,
        );
      };

      const handleGetCachedStats = async (params) => {
        const generateCacheKey = (communityId, dashboardType, dateBasis, startDate, endDate) => {
          return `isd_test-com_community_added_2024-01-01_2024-01-31`;
        };

        const cacheKey = generateCacheKey();
        const isCacheValid = () => false; // Expired

        // Should not queue another update since one is already in progress
        if (!isCacheValid() && !updateInProgress(cacheKey)) {
          messageQueue.push({
            type: 'UPDATE_CACHED_STATS',
            id: -2,
            params: { ...params, cacheKey },
          });
        }

        return {
          success: true,
          data: mockExpiredData.data,
          isExpired: true,
        };
      };

      await handleGetCachedStats({
        communityId: 'test-community',
        dashboardType: 'community',
        dateBasis: 'added',
        blockStartDate: '2024-01-01',
        blockEndDate: '2024-01-31',
      });

      // Should still only have one update in queue
      expect(messageQueue.length).toBe(1);
    });

    it('should return isExpired: false for valid cache', async () => {
      const currentYear = new Date().getUTCFullYear();
      const mockValidData = {
        key: 'isd_test-com_community_added_2024-01-01_2024-01-31',
        data: { test: 'valid data' },
        compressed: false,
        timestamp: Date.now() - 30 * 60 * 1000, // 30 minutes ago (still valid)
        year: currentYear,
        serverFetchTimestamp: Date.now() - 30 * 60 * 1000,
      };

      const handleGetCachedStats = async (params) => {
        const isCacheValid = (cachedData) => {
          if (!cachedData || !cachedData.timestamp) return false;
          const now = Date.now();
          const cacheAge = now - cachedData.timestamp;
          const year = cachedData.year;
          const isCurrent = year === new Date().getUTCFullYear();
          const maxAge = isCurrent ? 1 * 60 * 60 * 1000 : 1 * 365 * 24 * 60 * 60 * 1000;
          return cacheAge < maxAge;
        };

        const isValid = isCacheValid(mockValidData);

        return {
          success: true,
          data: mockValidData.data,
          serverFetchTimestamp: mockValidData.serverFetchTimestamp,
          year: mockValidData.year,
          isExpired: !isValid,
        };
      };

      const result = await handleGetCachedStats({
        communityId: 'test-community',
        dashboardType: 'community',
        dateBasis: 'added',
        startDate: '2024-01-01',
        endDate: '2024-01-31',
      });

      expect(result.success).toBe(true);
      expect(result.data).toEqual({ test: 'valid data' });
      expect(result.isExpired).toBe(false);
    });

    it('should send CACHE_UPDATED message when background update completes', async () => {
      const mockUpdatedData = { test: 'updated data' };
      const cacheKey = 'isd_test-com_community_added_2024-01-01_2024-01-31';

      // Mock statsApiClient.getStats to return updated data
      const mockGetStats = jest.fn().mockResolvedValue(mockUpdatedData);

      // Simulate handleUpdateCachedStats
      const handleUpdateCachedStats = async (params) => {
        const transformedData = await mockGetStats(
          params.communityId,
          params.dashboardType,
          params.blockStartDate,
          params.blockEndDate,
          params.dateBasis,
          params.requestCompressedJson,
        );
        const year = parseInt(params.blockStartDate.substring(0, 4));

        return {
          success: true,
          cacheKey: params.cacheKey,
          data: transformedData,
          year,
        };
      };

      const result = await handleUpdateCachedStats({
        communityId: 'test-community',
        dashboardType: 'community',
        dateBasis: 'added',
        blockStartDate: '2024-01-01',
        blockEndDate: '2024-01-31',
        cacheKey,
        requestCompressedJson: false,
        cacheCompressedJson: false,
      });

      // Verify result contains expected data for CACHE_UPDATED message
      expect(result.success).toBe(true);
      expect(result.cacheKey).toBe(cacheKey);
      expect(result.data).toEqual(mockUpdatedData);
      expect(result.year).toBe(2024);
      // This result structure should be sent as CACHE_UPDATED message
    });
  });

  describe('Cache Eviction', () => {
    it('should evict oldest entries when limit is reached', async () => {
      const MAX_CACHE_ENTRIES = 20;
      const entries = [];

      // Create 21 entries (one over limit)
      for (let i = 0; i <= MAX_CACHE_ENTRIES; i++) {
        entries.push({
          key: `key-${i}`,
          timestamp: Date.now() - (MAX_CACHE_ENTRIES - i) * 1000,
          lastAccessed: Date.now() - (MAX_CACHE_ENTRIES - i) * 1000,
        });
      }

      // Sort by lastAccessed (oldest first)
      entries.sort((a, b) => {
        const aTime = a.lastAccessed || a.timestamp || 0;
        const bTime = b.lastAccessed || b.timestamp || 0;
        return aTime - bTime;
      });

      // Should evict the oldest entry
      const toEvict = entries.slice(0, 1);
      expect(toEvict.length).toBe(1);
      expect(toEvict[0].key).toBe('key-0');
    });
  });

  describe('Priority Queue Behavior', () => {
    // Simulate the priority queue logic from the worker
    const MESSAGE_PRIORITY = {
      'GET_CACHED_STATS': 1,
      'CLEAR_CACHED_STATS_FOR_KEY': 2,
      'CLEAR_ALL_CACHED_STATS': 2,
      'SET_CACHED_STATS': 10,
    };

    const simulatePriorityQueue = (messages) => {
      // Sort by priority (lower number = higher priority)
      const sorted = [...messages].sort((a, b) => {
        const priorityA = MESSAGE_PRIORITY[a.type] || 100;
        const priorityB = MESSAGE_PRIORITY[b.type] || 100;
        return priorityA - priorityB;
      });
      return sorted;
    };

    it('should prioritize GET_CACHED_STATS over SET_CACHED_STATS', () => {
      const messages = [
        { type: 'SET_CACHED_STATS', id: 1, params: {} },
        { type: 'GET_CACHED_STATS', id: 2, params: {} },
      ];

      const processed = simulatePriorityQueue(messages);

      // GET should be processed first
      expect(processed[0].type).toBe('GET_CACHED_STATS');
      expect(processed[0].id).toBe(2);
      expect(processed[1].type).toBe('SET_CACHED_STATS');
      expect(processed[1].id).toBe(1);
    });

    it('should process multiple GET messages before SET messages', () => {
      const messages = [
        { type: 'SET_CACHED_STATS', id: 1, params: {} },
        { type: 'GET_CACHED_STATS', id: 2, params: {} },
        { type: 'SET_CACHED_STATS', id: 3, params: {} },
        { type: 'GET_CACHED_STATS', id: 4, params: {} },
        { type: 'SET_CACHED_STATS', id: 5, params: {} },
      ];

      const processed = simulatePriorityQueue(messages);

      // All GETs should come first
      expect(processed[0].type).toBe('GET_CACHED_STATS');
      expect(processed[0].id).toBe(2);
      expect(processed[1].type).toBe('GET_CACHED_STATS');
      expect(processed[1].id).toBe(4);

      // Then SETs
      expect(processed[2].type).toBe('SET_CACHED_STATS');
      expect(processed[3].type).toBe('SET_CACHED_STATS');
      expect(processed[4].type).toBe('SET_CACHED_STATS');
    });

    it('should prioritize CLEAR operations over SET but after GET', () => {
      const messages = [
        { type: 'SET_CACHED_STATS', id: 1, params: {} },
        { type: 'CLEAR_CACHED_STATS_FOR_KEY', id: 2, params: {} },
        { type: 'GET_CACHED_STATS', id: 3, params: {} },
        { type: 'CLEAR_ALL_CACHED_STATS', id: 4, params: {} },
      ];

      const processed = simulatePriorityQueue(messages);

      // Order should be: GET, CLEAR, CLEAR, SET
      expect(processed[0].type).toBe('GET_CACHED_STATS');
      expect(processed[1].type).toBe('CLEAR_CACHED_STATS_FOR_KEY');
      expect(processed[2].type).toBe('CLEAR_ALL_CACHED_STATS');
      expect(processed[3].type).toBe('SET_CACHED_STATS');
    });

    it('should maintain message order for same priority operations', () => {
      // When priority is the same, FIFO order should be maintained
      const messages = [
        { type: 'GET_CACHED_STATS', id: 1, params: { key: 'first' } },
        { type: 'GET_CACHED_STATS', id: 2, params: { key: 'second' } },
        { type: 'GET_CACHED_STATS', id: 3, params: { key: 'third' } },
      ];

      const processed = simulatePriorityQueue(messages);

      // Should maintain original order since all have same priority
      expect(processed[0].id).toBe(1);
      expect(processed[1].id).toBe(2);
      expect(processed[2].id).toBe(3);
    });

    it('should handle unknown message types with lowest priority', () => {
      const messages = [
        { type: 'UNKNOWN_TYPE', id: 1, params: {} },
        { type: 'GET_CACHED_STATS', id: 2, params: {} },
        { type: 'SET_CACHED_STATS', id: 3, params: {} },
      ];

      const processed = simulatePriorityQueue(messages);

      // GET first, then SET, then unknown
      expect(processed[0].type).toBe('GET_CACHED_STATS');
      expect(processed[1].type).toBe('SET_CACHED_STATS');
      expect(processed[2].type).toBe('UNKNOWN_TYPE');
    });

    it('should simulate queue processing order with async operations', async () => {
      // Simulate the actual queue processing behavior
      const messageQueue = [];
      let isProcessing = false;
      const processedOrder = [];

      const processQueue = async () => {
        if (isProcessing || messageQueue.length === 0) {
          return;
        }

        isProcessing = true;

        while (messageQueue.length > 0) {
          // Sort by priority
          messageQueue.sort((a, b) => {
            const priorityA = MESSAGE_PRIORITY[a.type] || 100;
            const priorityB = MESSAGE_PRIORITY[b.type] || 100;
            return priorityA - priorityB;
          });

          const message = messageQueue.shift();

          // Simulate async operation
          await new Promise(resolve => setTimeout(resolve, 10));

          processedOrder.push(message.id);
        }

        isProcessing = false;
      };

      // Add messages in SET-first order
      messageQueue.push({ type: 'SET_CACHED_STATS', id: 1, params: {} });
      messageQueue.push({ type: 'GET_CACHED_STATS', id: 2, params: {} });
      messageQueue.push({ type: 'SET_CACHED_STATS', id: 3, params: {} });
      messageQueue.push({ type: 'GET_CACHED_STATS', id: 4, params: {} });

      await processQueue();

      // GETs should be processed first (ids 2 and 4), then SETs (ids 1 and 3)
      expect(processedOrder[0]).toBe(2); // First GET
      expect(processedOrder[1]).toBe(4); // Second GET
      expect(processedOrder[2]).toBe(1); // First SET
      expect(processedOrder[3]).toBe(3); // Second SET
    });

    it('should handle concurrent message arrival correctly', async () => {
      // Simulate messages arriving before processing starts (most common case)
      const messageQueue = [];
      let isProcessing = false;
      const processedOrder = [];

      const processQueue = async () => {
        if (isProcessing || messageQueue.length === 0) {
          return;
        }

        isProcessing = true;

        while (messageQueue.length > 0) {
          // Sort by priority before each message (like the real implementation)
          messageQueue.sort((a, b) => {
            const priorityA = MESSAGE_PRIORITY[a.type] || 100;
            const priorityB = MESSAGE_PRIORITY[b.type] || 100;
            return priorityA - priorityB;
          });

          const message = messageQueue.shift();

          // Simulate async operation
          await new Promise(resolve => setTimeout(resolve, 5));

          processedOrder.push({ type: message.type, id: message.id });
        }

        isProcessing = false;
      };

      // Simulate receiving messages (like addEventListener would)
      const receiveMessage = (message) => {
        messageQueue.push(message);
        // Don't start processing immediately - simulate batching
        // Use setTimeout 0 to defer execution (similar to setImmediate)
        setTimeout(() => processQueue(), 0);
      };

      // Send SET first (lower priority)
      receiveMessage({ type: 'SET_CACHED_STATS', id: 1, params: {} });

      // Then GET arrives immediately after (higher priority)
      // Both should be in queue before processing starts
      receiveMessage({ type: 'GET_CACHED_STATS', id: 2, params: {} });

      // Wait for processing to complete
      await new Promise(resolve => setTimeout(resolve, 100));

      // Both should be processed, with GET first due to priority
      expect(processedOrder.length).toBe(2);
      expect(processedOrder[0].type).toBe('GET_CACHED_STATS');
      expect(processedOrder[0].id).toBe(2);
      expect(processedOrder[1].type).toBe('SET_CACHED_STATS');
      expect(processedOrder[1].id).toBe(1);
    });

    it('should handle messages arriving during processing', async () => {
      // Test case where a GET arrives while SET is already processing
      const messageQueue = [];
      let isProcessing = false;
      const processedOrder = [];
      let processingStartTime = null;

      const processQueue = async () => {
        if (isProcessing || messageQueue.length === 0) {
          return;
        }

        isProcessing = true;
        processingStartTime = Date.now();

        while (messageQueue.length > 0) {
          // Sort by priority before each message
          messageQueue.sort((a, b) => {
            const priorityA = MESSAGE_PRIORITY[a.type] || 100;
            const priorityB = MESSAGE_PRIORITY[b.type] || 100;
            return priorityA - priorityB;
          });

          const message = messageQueue.shift();

          // Simulate longer async operation (like compression)
          await new Promise(resolve => setTimeout(resolve, 20));

          processedOrder.push({
            type: message.type,
            id: message.id,
            timestamp: Date.now()
          });
        }

        isProcessing = false;
      };

      // Start SET processing immediately
      messageQueue.push({ type: 'SET_CACHED_STATS', id: 1, params: {} });
      processQueue(); // Start processing SET

      // Wait a bit, then GET arrives while SET is processing
      await new Promise(resolve => setTimeout(resolve, 5));
      messageQueue.push({ type: 'GET_CACHED_STATS', id: 2, params: {} });

      // GET will wait for SET to finish, then process
      await new Promise(resolve => setTimeout(resolve, 100));

      // Both should be processed
      expect(processedOrder.length).toBe(2);
      // SET should be first (it started processing first)
      expect(processedOrder[0].type).toBe('SET_CACHED_STATS');
      expect(processedOrder[1].type).toBe('GET_CACHED_STATS');
    });
  });
});

