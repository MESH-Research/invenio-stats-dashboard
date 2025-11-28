# Cache Configuration for Invenio Stats Dashboard

The invenio-stats-dashboard uses a direct Redis connection for caching prepared data series. This approach bypasses pickling overhead and stores compressed JSON data as raw bytes for maximum performance.

## Default Configuration

The cache uses the existing Invenio cache configuration:

**Environment Variables** (with `INVENIO_` prefix):
```bash
INVENIO_CACHE_TYPE=redis
INVENIO_CACHE_REDIS_URL=redis://localhost:6379/0
```

**Configuration Access** (without prefix):
```python
# In your application code
current_app.config['CACHE_TYPE']  # 'redis'
current_app.config['CACHE_REDIS_URL']  # 'redis://localhost:6379/0'

# Stats-specific configuration
current_app.config['STATS_CACHE_REDIS_DB']  # 6 (default)
current_app.config['STATS_CACHE_PREFIX']  # 'stats_dashboard' (default)
current_app.config['STATS_CACHE_DEFAULT_TTL']  # 3600 (default)
current_app.config['STATS_CACHE_COMPRESSION_METHOD']  # 'brotli' (default)
```

## Redis Configuration

If you want to use a dedicated Redis database for stats caching, you can configure it as follows:

**Environment Variables**:
```bash
INVENIO_CACHE_TYPE=redis
INVENIO_CACHE_REDIS_URL=redis://localhost:6379/5  # Use database 5 for stats
```

**Configuration Access**:
```python
# In your application code
current_app.config['CACHE_TYPE']  # 'redis'
current_app.config['CACHE_REDIS_URL']  # 'redis://localhost:6379/5'
```

## Stats Cache Configuration

The stats dashboard uses several configuration variables for fine-tuning:

**Environment Variables**:
```bash
INVENIO_STATS_CACHE_REDIS_DB=6

INVENIO_STATS_CACHE_PREFIX=stats_dashboard

# Default cache TTL in seconds (default: None - no expiration)
INVENIO_STATS_CACHE_DEFAULT_TTL=None

INVENIO_STATS_CACHE_COMPRESSION_METHOD=brotli
```

**Configuration in invenio.cfg**:
```python
# Stats cache configuration
STATS_CACHE_REDIS_DB = 6
STATS_CACHE_PREFIX = "stats_dashboard"
STATS_CACHE_DEFAULT_TTL = None
STATS_CACHE_COMPRESSION_METHOD = "brotli"
```

## Cache Behavior

**No Automatic Expiration**: Cache entries do not expire automatically. This is intentional because:

1. **Data Consistency**: Statistics data doesn't change frequently
2. **Performance**: Avoids cache misses during peak usage
3. **Scheduled Refresh**: Data is refreshed on a schedule from the back-end
4. **Predictable Performance**: Consistent response times

**Manual Cache Management**: Use the cache invalidation methods to refresh data:

```python
# Clear all stats cache
stats_cache = StatsCache()
stats_cache.invalidate_cache()

# Clear specific cache entry
stats_cache.invalidate_cache(
    community_id="global",
    stat_name="record_snapshots",
    start_date="2024-01-01",
    end_date="2024-12-31",
    date_basis="added"
)
```

## Cache Key Structure

Cache keys are automatically generated using the following pattern:

```
{STATS_CACHE_PREFIX}:{sha256_hash}
```

Where `{STATS_CACHE_PREFIX}` defaults to `"stats_dashboard"` but can be configured.

Where the hash is generated from:
- `community_id`: Community ID or "global"
- `stat_name`: Name of the statistics query
- `start_date`: Start date string (optional)
- `end_date`: End date string (optional)
- `date_basis`: Date basis for the query ("added", "created", "published")

## Cache Behavior

- **Compression**: All cached data is compressed using gzip compression
- **TTL**: Default 1 hour (3600 seconds)
- **Serialization**: Raw bytes (no pickling overhead)
- **Storage**: Dedicated Redis database (database 6)
- **Headers**: Cached responses include `X-Cache: HIT` header

## Manual Cache Management

You can manually manage the cache using the StatsCache class:

```python
from invenio_stats_dashboard.resources.cache_utils import StatsCache

# Initialize cache manager
cache_manager = StatsCache()

# Invalidate specific cache entry
cache_manager.invalidate_cache(
    community_id="global",
    stat_name="record_snapshots"
)

# Get cache information
info = cache_manager.get_cache_info()
```

## Performance Benefits

- **Response Time**: Cached responses are served immediately
- **Resource Usage**: Reduces load on OpenSearch and data transformers
- **Compression**: Reduces memory usage and network transfer
- **Scalability**: Improves performance under high load
- **No Pickling Overhead**: Raw bytes storage eliminates serialization/deserialization costs
- **Direct Redis Access**: Bypasses Flask-Caching layer for maximum speed
- **Dedicated Database**: Uses Redis database 6 to avoid conflicts with other cache data

## Monitoring

Cache hit/miss information is logged at debug level:

```
Cache hit for key: stats_dashboard:abc123...
Cache miss for key: stats_dashboard:def456...
```

## Troubleshooting

If you encounter cache-related issues:

1. **Check Redis connectivity**: Ensure Redis is running and accessible
2. **Verify configuration**: Check `CACHE_TYPE` and `CACHE_REDIS_URL` settings
3. **Check logs**: Look for cache-related error messages
4. **Clear cache**: Use `current_cache.clear()` to clear all cache entries

## Alternative: Direct Redis Connection

If you need more control over the cache, you can create a direct Redis connection:

```python
import redis
from flask import current_app

# Get Redis URL from config
redis_url = current_app.config.get('CACHE_REDIS_URL', 'redis://localhost:6379/0')
redis_client = redis.from_url(redis_url)

# Use directly
redis_client.set('my_key', 'my_value', ex=3600)  # 1 hour expiry
value = redis_client.get('my_key')
```
