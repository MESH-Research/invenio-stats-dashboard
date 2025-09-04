# Stats Dashboard Caching Implementation

This document describes the client-side caching implementation for the Invenio Stats Dashboard.

## Overview

The stats dashboard now includes a local storage caching mechanism that:
- Stores transformed data after it has been processed by `dataTransformer` classes
- Distinguishes between requests by community ID and request date parameters
- Displays cached data immediately while fetching fresh data in the background
- Shows appropriate loading states and update messages

## How It Works

### 1. Cache Key Generation
Cache keys are generated based on:
- Community ID (or 'global' for global dashboards)
- Dashboard type (e.g., 'community', 'global')
- Start date (if provided)
- End date (if provided)

Example cache key: `invenio_stats_dashboard_1.0_{"communityId":"test-community","dashboardType":"community","startDate":"2023-01-01","endDate":"2023-12-31"}`

### 2. Data Flow
1. **Initial Load**: Check for cached data
   - If cached data exists and is valid (< 7 days old): Display immediately
   - If no cached data: Show loading state
2. **Background Fetch**: Always fetch fresh data (API or test data)
   - **Production Mode**: Fetch from API
   - **Test Mode**: Generate test data locally
   - Transform data using `dataTransformer` classes
   - Cache the transformed data
   - Update the display with fresh data
   - Show "last updated" timestamp

### 3. Loading States
- **Initial Loading**: Only shown when no cached data is available
- **Updating**: Shown while fetching fresh data in background (when cached data is displayed)
- **Last Updated**: Shows timestamp of most recent data fetch

### 4. Test Data Mode
When `use_test_data: true` is configured:
- Test data is generated at the same point where API calls would occur
- Test data goes through the same transformation pipeline as real data
- Test data is cached in localStorage just like real data
- All loading states and update messages work normally
- This provides a realistic testing environment that mirrors production behavior

## API Reference

### Cache Functions

#### `setCachedStats(communityId, dashboardType, transformedData, startDate?, endDate?)`
Stores transformed stats data in localStorage.

#### `getCachedStats(communityId, dashboardType, startDate?, endDate?)`
Retrieves cached stats data if valid (not expired).

#### `clearCachedStats()`
Removes all cached stats data from localStorage.

#### `getCacheInfo()`
Returns information about cached entries for debugging.

#### `formatCacheTimestamp(timestamp)`
Formats a timestamp for display in the UI.

### API Functions

#### `getCachedStatsData(params)`
High-level function to get cached stats data with parameter handling.

#### `fetchFreshStatsWithCache(params)`
Fetches fresh stats data from the API, transforms it, and caches it.

#### `fetchStats(params)`
Main function that handles the complete caching flow with state management callbacks.

### Components

#### `UpdateStatusMessage`
Displays either:
- "Updating data..." with spinner (when `isUpdating` is true)
- "Last updated: [timestamp]" (when `lastUpdated` is provided)

## Configuration

### Cache Expiry
- Default: 7 days
- Configurable via `CACHE_EXPIRY_DAYS` constant in `statsCache.js`

### Cache Version
- Current version: 1.0
- Used for cache invalidation when data structure changes

## Usage Examples

### Basic Usage
The caching is automatically enabled in `StatsDashboardLayout`. No additional configuration is required.

### Manual Cache Management
```javascript
import { getCachedStats, setCachedStats, clearCachedStats } from './utils/statsCache';
import { getCachedStatsData, fetchFreshStatsWithCache } from './api/api';

// Get cached data (low-level)
const cachedData = getCachedStats('community-id', 'community');

// Get cached data (high-level with parameter handling)
const cachedData = getCachedStatsData({
  communityId: 'community-id',
  dashboardType: 'community'
});

// Fetch fresh data and cache it
const result = await fetchFreshStatsWithCache({
  communityId: 'community-id',
  dashboardType: 'community'
});

// Main function with state management
const result = await fetchStats({
  communityId: 'community-id',
  dashboardType: 'community',
  onStateChange: (state) => {
    // Handle state changes
    console.log('State changed:', state.type, state.stats);
  }
});

// Set cached data (low-level)
setCachedStats('community-id', 'community', transformedData);

// Clear all cache
clearCachedStats();
```

## Testing

The caching functionality includes comprehensive tests:
- `statsCache.test.js`: Unit tests for cache utilities
- `StatsDashboardLayout.test.jsx`: Integration tests for dashboard caching

Run tests with:
```bash
npm test
```

## Browser Compatibility

The caching implementation uses:
- `localStorage` API (supported in all modern browsers)
- `JSON.stringify/parse` for data serialization
- `Date.now()` for timestamp handling

## Performance Considerations

- Cache keys are generated using `JSON.stringify` - consider key length for large parameter objects
- Transformed data is stored as JSON - large datasets may impact localStorage quota
- Cache expiry prevents indefinite storage growth
- Background fetching ensures users always see fresh data

## Troubleshooting

### Cache Not Working
1. Check browser console for localStorage errors
2. Verify cache keys are being generated correctly
3. Check if localStorage quota is exceeded

### Debug Cache State
```javascript
import { getCacheInfo } from './utils/statsCache';
console.log(getCacheInfo());
```

### Clear Cache
```javascript
import { clearCachedStats } from './utils/statsCache';
clearCachedStats();
```
