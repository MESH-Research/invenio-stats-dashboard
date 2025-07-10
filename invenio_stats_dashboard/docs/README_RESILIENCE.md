# Aggregation Resilience Features

This document describes the resilience features added to the aggregation processes to prevent overwhelming the OpenSearch domain.

## Overview

The aggregation processes make intensive use of OpenSearch queries, including:
- Composite aggregations with pagination
- Scan operations across large datasets
- Bulk indexing operations
- Multiple search queries per aggregation step

To prevent these operations from overwhelming the search index, we've implemented **adaptive resilience mechanisms** that only activate when the cluster is under stress.

## Adaptive Rate Limiting

### AdaptiveRateLimiter Class
Located in `aggregations.py`, the `AdaptiveRateLimiter` class provides:
- **Cluster health monitoring**: Checks OpenSearch cluster status every 60 seconds
- **Stress detection**: Activates rate limiting only when cluster is under stress
- **High throughput by default**: 2000 requests per minute when cluster is healthy
- **Automatic backoff**: When stress is detected, rate limiting activates

### Stress Detection
The system considers the cluster stressed when:
- Cluster status is not "green" (yellow/red)
- High number of relocating shards (>5)
- High number of initializing shards (>5)

### Configuration
Adaptive rate limiting can be configured via `STATS_DASHBOARD_RATE_LIMIT`:

```python
STATS_DASHBOARD_RATE_LIMIT = {
    "max_requests_per_minute": 2000,  # Appropriate for AWS OpenSearch
    "max_concurrent_requests": 50,    # Higher concurrency for production
    "retry_max_attempts": 3,
    "retry_base_delay": 2,
    "bulk_chunk_size": 500,          # Larger chunks for better performance
    "search_timeout": 60,            # Longer timeout for complex aggregations
    "adaptive_rate_limiting": True,   # Enable adaptive approach
    "stress_threshold": 0.8,         # Cluster stress threshold
}
```

## Performance Comparison

### AWS OpenSearch Production Capabilities
- **Typical Mid-Range Cluster**: 3-5 data nodes, 16-32GB RAM per node
- **Search Requests**: 10,000-50,000 requests/minute
- **Bulk Operations**: 1,000-5,000 bulk operations/minute
- **Concurrent Connections**: 100-500

### Your Aggregation Load
- **Peak Load**: ~420,000 requests in 2 hours = 3,500 req/min
- **Normal Load**: ~17,500 requests in 30 minutes = 580 req/min
- **Concurrent**: Sequential processing = 1-5 concurrent

### Rate Limit Strategy
- **Normal Operation**: 2000 req/min (well within cluster capacity)
- **Stress Detection**: Automatic throttling when cluster is under load
- **No Unnecessary Delays**: Full throughput when cluster is healthy

## Retry Logic

### Exponential Backoff
The `with_retry` decorator provides:
- **Configurable retry attempts**: Default 3 attempts
- **Exponential backoff**: Delay increases with each retry (1s, 2s, 4s)
- **Random jitter**: Adds small random delays to prevent thundering herd

### Usage
```python
@with_retry(max_retries=3, base_delay=2)
def search_operation():
    # Your search operation here
    pass
```

## Protected Operations

The following critical search operations are protected with rate limiting and retry logic:

1. **Composite Aggregations**: `search.execute()` with pagination
2. **Count Operations**: `search.count()` for large datasets
3. **Scan Operations**: `search.scan()` for full result sets
4. **Bulk Operations**: `bulk()` with immediate refresh
5. **Metadata Queries**: Multiple search queries for record metadata

## Monitoring

### Logging
The system logs:
- Cluster stress level changes
- Rate limiting activations
- Retry attempts and delays
- Search operation failures

### Metrics to Watch
- **Cluster Health**: Monitor for yellow/red status
- **Request Rate**: Track requests per minute
- **Response Times**: Monitor search operation latency
- **Error Rates**: Watch for failed search operations

## Best Practices

1. **Monitor Cluster Health**: Use OpenSearch Dashboards to monitor cluster status
2. **Adjust Limits**: Tune rate limits based on your specific cluster capacity
3. **Test Under Load**: Verify resilience features work during peak usage
4. **Monitor Performance**: Track aggregation completion times and success rates

## Performance Analysis

### Search Request Count
For a typical aggregation run:
- **~14 search requests per community per day per event type**
- **2 event types** (view, download) = **~28 requests per community per day**
- **30 days** = **~840 requests per community per month**

### For Large Scale (500 communities):
- **840 × 500 = 420,000 requests per month**
- **With adaptive rate limiting (300 req/min)**: ~23 hours total
- **With aggressive rate limiting (60 req/min)**: ~5 days total

### Adaptive vs Aggressive Approach
| Approach | Normal Operation | Under Stress | Total Time (500 communities) |
|----------|------------------|--------------|------------------------------|
| **Adaptive** | 300 req/min | 60 req/min | ~23 hours |
| **Aggressive** | 60 req/min | 60 req/min | ~5 days |

## Benefits of Adaptive Approach

### Performance
- **Normal operation**: Full speed (300 req/min)
- **Under stress**: Automatic throttling (60 req/min)
- **No unnecessary delays** when cluster is healthy

### Resilience
- **Automatic detection** of cluster stress
- **Proactive protection** before cluster becomes overwhelmed
- **Graceful degradation** when needed

### Scalability
- **Handles large communities** efficiently
- **Adapts to cluster capacity** automatically
- **Maintains performance** under normal conditions

## Tuning Recommendations

### For High-Volume Environments
- Increase `max_requests_per_minute` to 400-500
- Monitor cluster health metrics
- Adjust `stress_threshold` based on cluster capacity

### For Development/Testing
- Use default settings (300 req/min)
- Monitor logs for stress detection events
- Test with realistic data volumes

## Integration with Existing Code

The resilience features are implemented as:
1. **Adaptive rate limiting** that only activates under stress
2. **Context managers** for wrapping individual operations
3. **Configuration options** that can be tuned per environment
4. **Transparent operation** - no changes to existing aggregation logic

## Testing

To test the adaptive resilience features:
1. Monitor logs during aggregation runs
2. Look for cluster health status changes
3. Verify that rate limiting only activates under stress
4. Check that aggregations complete efficiently under normal conditions
5. Test cluster stress scenarios to verify adaptive behavior