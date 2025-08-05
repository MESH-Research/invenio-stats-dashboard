# Monthly Index Migration with EventReindexingService

## Overview

The enhanced `EventReindexingService` now properly handles monthly indices for event statistics. This service migrates existing event indices to enriched versions with additional metadata fields while maintaining zero downtime.

## Monthly Index Structure

The system uses monthly indices for event statistics:

- **View Events**: `{prefix}events-stats-record-view-YYYY-MM`
- **Download Events**: `{prefix}events-stats-file-download-YYYY-MM`

These are aliased to:
- `{prefix}events-stats-record-view`
- `{prefix}events-stats-file-download`

### Migration Naming Pattern

During migration, enriched indices are created with a `-v2` suffix:

- **Original**: `{prefix}events-stats-record-view-2025-06`
- **Enriched**: `{prefix}events-stats-record-view-enriched-2025-06-v2`

For the current month, a write alias is created:
- **Write Alias**: `{prefix}events-stats-record-view-2025-06` → points to enriched index
- This ensures new writes go to the enriched index while maintaining the same index name

## Migration Process

The enhanced service follows a 6-step process for each monthly index:

### 1. Create New Enriched Index
- Creates a new index with the enriched schema and a `-v2` suffix
- Uses the same index template as the original but with additional fields
- Example: `events-stats-record-view-2025-06` → `events-stats-record-view-enriched-2025-06-v2`

### 2. Migrate and Enrich Data
- Processes events in batches to avoid memory issues
- Enriches each event with:
  - `community_id`: The community the record belongs to
  - `resource_type`: Record type information
  - `access_status`: Access status
  - `publisher`: Publisher information
  - `languages`: Language metadata
  - `subjects`: Subject classifications
  - `licenses`: License information
  - `funders`: Funding organization data
  - `affiliations`: Creator/contributor affiliations
  - `periodical`: Journal/periodical information

### 3. Validate Data
- Ensures document counts match between source and target
- Verifies all required enriched fields are present
- Checks data integrity before proceeding

### 4. Update Aliases
- Updates the main alias to point to the new enriched index
- Maintains zero downtime during the switch
- For current month: Creates write alias from old index name to new enriched index

### 5. Handle Current Month Write Alias
- For the current month's index, creates a write alias with the old index name
- This ensures new writes go to the enriched index while maintaining the same index name
- Checks for any new records written during migration

### 6. Clean Up
- Deletes the old index (only for non-current months)
- For current month, keeps old index until write alias is confirmed

## Usage

### Basic Migration

```python
from invenio_stats_dashboard.service import EventReindexingService

service = EventReindexingService(app)

# Migrate all event types
results = service.reindex_events()

# Migrate specific event types
results = service.reindex_events(event_types=["view", "download"])

# Limit batches for testing
results = service.reindex_events(max_batches=10)
```

### Check Progress

```python
# Get current progress
progress = service.get_reindexing_progress()

# Get estimates
estimates = service.estimate_total_events()
```

### Manual Monthly Migration

```python
# Migrate a specific monthly index
results = service.migrate_monthly_index(
    event_type="view",
    source_index="kcworks-events-stats-record-view-2025-06",
    month="2025-06"
)
```

## Key Features

### Zero Downtime
- Uses aliases to switch between old and new indices
- No interruption to read operations during migration

### Current Month Handling
- Special handling for the current month's index
- Creates write aliases to ensure new writes go to enriched index
- Checks for new records written during migration

### Resume Capability
- Uses bookmarks to track progress
- Can resume interrupted migrations
- Per-month bookmark tracking

### Health Monitoring
- Memory usage monitoring
- OpenSearch health checks
- Graceful degradation under load

### Validation
- Document count verification
- Required field validation
- Data integrity checks

## Configuration

The service uses these configuration parameters:

```python
# Batch processing
batch_size = 1000
max_memory_percent = 85
max_retries = 3
retry_delay = 5  # seconds
```

## Error Handling

The service includes comprehensive error handling:

- **Connection Issues**: Retries with exponential backoff
- **Memory Pressure**: Stops processing if memory usage exceeds threshold
- **Validation Failures**: Rolls back changes if validation fails
- **Partial Failures**: Continues with other indices if one fails

## Monitoring

Monitor the migration process through:

- **Logs**: Detailed logging of each step
- **Progress**: `get_reindexing_progress()` method
- **Health**: `check_health_conditions()` method
- **Estimates**: `estimate_total_events()` method

## Best Practices

1. **Test First**: Run with `max_batches=1` to test the process
2. **Monitor Resources**: Watch memory usage during migration
3. **Backup**: Ensure indices are backed up before migration
4. **Off-Peak**: Run migrations during low-traffic periods
5. **Validate**: Check enriched data quality after migration

## Troubleshooting

### Common Issues

1. **Memory Issues**: Reduce `batch_size` or increase `max_memory_percent`
2. **Timeout Errors**: Increase `retry_delay` or check network connectivity
3. **Validation Failures**: Check source data quality and enrichment logic
4. **Alias Issues**: Verify alias permissions and index templates

### Recovery

If migration fails:

1. Check logs for specific error messages
2. Use bookmarks to resume from last successful point
3. Verify index templates are properly registered
4. Check OpenSearch cluster health

## Example Output

```python
{
    "total_processed": 150000,
    "total_errors": 0,
    "event_types": {
        "view": {
            "processed": 100000,
            "errors": 0,
            "months": {
                "2025-06": {
                    "month": "2025-06",
                    "event_type": "view",
                    "source_index": "kcworks-events-stats-record-view-2025-06",
                    "processed": 50000,
                    "errors": 0,
                    "batches": 50,
                    "completed": True,
                    "target_index": "kcworks-events-stats-record-view-enriched-2025-06"
                }
            }
        }
    },
    "completed": True
}
```