# Handling Overlapping Aggregation Runs

## Problem

The community stats aggregation task runs every hour at minute 40. If the previous run takes longer than an hour, the next scheduled run could start while the previous one is still running, leading to:

- **Resource conflicts**: Multiple aggregators trying to access the same data simultaneously
- **Data corruption**: Potential race conditions in bookmark updates
- **Performance degradation**: Overwhelming the search index with concurrent operations
- **Inconsistent results**: Aggregations based on partially processed data

## Solution: Distributed Locking

We've implemented a **distributed lock using Invenio's centralized cache system** to prevent overlapping aggregation runs.

### How It Works

1. **Lock Acquisition**: When the task starts, it tries to acquire a cache-based lock with a unique identifier
2. **Atomic Operation**: The lock is acquired using Flask-Caching's `add()` method which is atomic and only succeeds if the key doesn't exist
3. **Graceful Handling**: If the lock cannot be acquired, the task logs a warning and exits gracefully
4. **Automatic Cleanup**: The lock automatically expires after a configurable timeout (default: 24 hours)

### Configuration

The distributed lock can be configured via the `STATS_DASHBOARD_LOCK_CONFIG` setting:

```python
STATS_DASHBOARD_LOCK_CONFIG = {
    "enabled": True,  # Enable/disable distributed locking
    "lock_timeout": 86400,  # Lock timeout in seconds (24 hours)
    "lock_name": "community_stats_aggregation",  # Lock name
}
```

The lock automatically uses Invenio's centralized cache system, which is configured via the standard Invenio cache settings (e.g., `INVENIO_CACHE_REDIS_URL`).

### Benefits

1. **Prevents Overlaps**: Only one aggregation run can execute at a time
2. **Configurable**: Can be enabled/disabled and timeout adjusted
3. **Graceful Degradation**: Failed lock acquisition doesn't crash the system
4. **Automatic Recovery**: Locks expire automatically, preventing deadlocks
5. **Distributed**: Works across multiple worker instances

### Alternative Solutions Considered

1. **Database-based Locking**: More complex, requires additional tables
2. **File-based Locking**: Not suitable for distributed systems
3. **Celery Task Deduplication**: Limited to single worker, doesn't handle distributed scenarios
4. **Manual Coordination**: Error-prone and difficult to maintain

### Monitoring

The system logs lock acquisition and failure events:

```
INFO: Acquired aggregation lock, starting aggregation...
WARNING: Aggregation task skipped - another instance is already running
```

### Troubleshooting

If aggregation tasks are being skipped frequently:

1. **Check lock timeout**: Increase `lock_timeout` if aggregations take longer than expected
2. **Monitor aggregation performance**: Long-running aggregations may indicate performance issues
3. **Check Redis connectivity**: Ensure Redis is available and accessible
4. **Review logs**: Look for patterns in lock acquisition failures

### Implementation Details

The lock uses Invenio's centralized cache system (`invenio_cache.current_cache`):

- **Acquisition**: Uses `current_cache.add()` which only succeeds if the key doesn't exist
- **Release**: Checks ownership by comparing the stored value with our lock ID before deleting
- **Expiration**: Leverages the cache's built-in TTL mechanism
- **Configuration**: Automatically uses the same cache configuration as the rest of the application

This prevents accidental lock releases by other processes or expired locks.