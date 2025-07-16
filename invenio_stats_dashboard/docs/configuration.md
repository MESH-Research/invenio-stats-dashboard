# Invenio Stats Dashboard Configuration

This document describes the configuration options available for the Invenio Stats Dashboard.

## Memory and Performance Settings

### STATS_DASHBOARD_REINDEXING_MAX_MEMORY_PERCENT
- **Default**: 75
- **Type**: Integer
- **Description**: Maximum memory usage percentage before stopping reindexing operations
- **Range**: 50-95 (recommended: 70-80)
- **Usage**: When memory usage exceeds this threshold, the reindexing service will stop gracefully to prevent system overload

### STATS_DASHBOARD_REINDEXING_BATCH_SIZE
- **Default**: 1000
- **Type**: Integer
- **Description**: Number of events to process in each batch during reindexing
- **Range**: 100-5000 (recommended: 500-2000)
- **Usage**: Larger batch sizes improve throughput but increase memory usage

## Example Configuration

```python
# In your Flask app configuration
STATS_DASHBOARD_REINDEXING_MAX_MEMORY_PERCENT = 70  # Conservative for production
STATS_DASHBOARD_REINDEXING_BATCH_SIZE = 1500        # Larger batches for high-throughput systems
```

## Recommendations by Environment

### Production (High Memory - 32GB+)
```python
STATS_DASHBOARD_REINDEXING_MAX_MEMORY_PERCENT = 75
STATS_DASHBOARD_REINDEXING_BATCH_SIZE = 2000
```

### Production (Standard Memory - 16GB)
```python
STATS_DASHBOARD_REINDEXING_MAX_MEMORY_PERCENT = 70
STATS_DASHBOARD_REINDEXING_BATCH_SIZE = 1000
```

### Production (Low Memory - 8GB or less)
```python
STATS_DASHBOARD_REINDEXING_MAX_MEMORY_PERCENT = 65
STATS_DASHBOARD_REINDEXING_BATCH_SIZE = 500
```

### Development/Testing
```python
STATS_DASHBOARD_REINDEXING_MAX_MEMORY_PERCENT = 80
STATS_DASHBOARD_REINDEXING_BATCH_SIZE = 1000
```

## Monitoring

The reindexing service logs memory usage and health check results. Monitor these logs to tune the configuration for your specific environment:

```
INFO: Memory usage: 45%
INFO: Health check passed
WARNING: Health check failed: Memory usage too high: 78%
```

## Troubleshooting

### High Memory Usage
- Reduce `STATS_DASHBOARD_REINDEXING_BATCH_SIZE`
- Lower `STATS_DASHBOARD_REINDEXING_MAX_MEMORY_PERCENT`
- Check for memory leaks in other services

### Slow Reindexing
- Increase `STATS_DASHBOARD_REINDEXING_BATCH_SIZE` (if memory allows)
- Check OpenSearch cluster health
- Monitor network connectivity to OpenSearch