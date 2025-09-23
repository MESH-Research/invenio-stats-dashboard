# Reference

## Configuration Variables

The following table provides a complete reference of all available configuration variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `COMMUNITY_STATS_ENABLED` | `True` | Enable/disable the entire module |
| `COMMUNITY_STATS_SCHEDULED_TASKS_ENABLED` | `False` | Enable/disable scheduled aggregation tasks |
| `COMMUNITY_STATS_CELERYBEAT_SCHEDULE` | `{...}` | Celery beat schedule for aggregation tasks |
| `COMMUNITY_STATS_CATCHUP_INTERVAL` | `365` | Maximum days to catch up when aggregating historical data |
| `COMMUNITY_STATS_AGGREGATIONS` | `{...}` | Aggregation configurations (auto-generated) |
| `COMMUNITY_STATS_QUERIES` | `{...}` | Query configurations (auto-generated) |
| `COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT` | `20` | Maximum number of items to return in subcount breakdowns |
| `COMMUNITY_STATS_SUBCOUNTS` | `{...}` | Configuration for subcount breakdowns and field mappings |
| `STATS_DASHBOARD_UI_SUBCOUNTS` | `{...}` | UI subcount configuration for different breakdown types |
| `STATS_DASHBOARD_LOCK_CONFIG` | `{...}` | Distributed locking configuration for aggregation tasks |
| `STATS_DASHBOARD_TEMPLATES` | `{...}` | Template paths for dashboard views |
| `STATS_DASHBOARD_ROUTES` | `{...}` | URL routes for dashboard pages |
| `STATS_DASHBOARD_UI_CONFIG` | `{...}` | UI configuration for dashboard appearance and behavior |
| `STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS` | `{...}` | Default date range options for different granularities |
| `STATS_DASHBOARD_LAYOUT` | `{...}` | Dashboard layout and component configuration |
| `STATS_DASHBOARD_MENU_ENABLED` | `True` | Enable/disable menu integration |
| `STATS_DASHBOARD_MENU_TEXT` | `_("Statistics")` | Menu item text |
| `STATS_DASHBOARD_MENU_ORDER` | `1` | Menu item order |
| `STATS_DASHBOARD_MENU_ENDPOINT` | `"invenio_stats_dashboard.global_stats_dashboard"` | Menu item endpoint |
| `STATS_DASHBOARD_MENU_REGISTRATION_FUNCTION` | `None` | Custom menu registration function |
| `STATS_DASHBOARD_USE_TEST_DATA` | `True` | Enable/disable test data mode for development |
| `STATS_DASHBOARD_REINDEXING_MAX_BATCHES` | `1000` | Maximum batches per month for migration |
| `STATS_DASHBOARD_REINDEXING_BATCH_SIZE` | `5000` | Events per batch for migration. **Note: OpenSearch has a hard limit of 10,000 documents for search results, so this value cannot exceed 10,000.** |
| `STATS_DASHBOARD_REINDEXING_MAX_MEMORY_PERCENT` | `85` | Maximum memory usage percentage before stopping migration |
| `STATS_EVENTS` | `{...}` | Event type configurations for statistics processing |

> **Note**: Variables marked with `{...}` contain complex configuration objects that are documented in detail in the :doc:`configuration` section.

## Service Classes

### CommunityStatsService

Main service class for managing community statistics.

```python
from invenio_stats_dashboard.services import CommunityStatsService

service = CommunityStatsService()
```

**Methods:**
- `generate_record_community_events()`: Generate community add/remove events
- `get_community_stats()`: Retrieve statistics for a community
- `aggregate_community_stats()`: Aggregate statistics for a community

### EventReindexingService

Service for migrating existing usage events to the enriched format.

```python
from invenio_stats_dashboard.services import EventReindexingService

service = EventReindexingService()
```

**Methods:**
- `reindex_events()`: Migrate events to new format
- `get_migration_status()`: Check migration progress
- `clear_bookmarks()`: Clear migration bookmarks

### CommunityEventService

Service for managing community membership events.

```python
from invenio_stats_dashboard.services import CommunityEventService

service = CommunityEventService()
```

**Methods:**
- `create_event()`: Create a community membership event
- `get_events()`: Retrieve community events
- `delete_events()`: Delete community events

## Aggregator Classes

### CommunityRecordDeltaAggregator

Aggregates daily record changes for communities.

```python
from invenio_stats_dashboard.aggregators import CommunityRecordDeltaAggregator

aggregator = CommunityRecordDeltaAggregator()
```

### CommunityRecordSnapshotAggregator

Aggregates daily record totals for communities.

```python
from invenio_stats_dashboard.aggregators import CommunityRecordSnapshotAggregator

aggregator = CommunityRecordSnapshotAggregator()
```

### CommunityUsageDeltaAggregator

Aggregates daily usage changes for communities.

```python
from invenio_stats_dashboard.aggregators import CommunityUsageDeltaAggregator

aggregator = CommunityUsageDeltaAggregator()
```

### CommunityUsageSnapshotAggregator

Aggregates daily usage totals for communities.

```python
from invenio_stats_dashboard.aggregators import CommunityUsageSnapshotAggregator

aggregator = CommunityUsageSnapshotAggregator()
```

## Query Classes

### CommunityStatsQuery

Query class for retrieving community statistics.

```python
from invenio_stats_dashboard.queries import CommunityStatsQuery

query = CommunityStatsQuery()
```

### GlobalStatsQuery

Query class for retrieving global statistics.

```python
from invenio_stats_dashboard.queries import GlobalStatsQuery

query = GlobalStatsQuery()
```

## Celery Tasks

### aggregate_community_record_stats

Main aggregation task for community statistics.

```python
from invenio_stats_dashboard.tasks import aggregate_community_record_stats

# Run asynchronously
result = aggregate_community_record_stats.delay(community_id="my-community")

# Run synchronously
result = aggregate_community_record_stats(community_id="my-community")
```

### reindex_events_with_metadata

Task for migrating usage events to enriched format.

```python
from invenio_stats_dashboard.tasks import reindex_events_with_metadata

# Run asynchronously
result = reindex_events_with_metadata.delay()

# Run synchronously
result = reindex_events_with_metadata()
```

### get_reindexing_progress

Task for checking migration progress.

```python
from invenio_stats_dashboard.tasks import get_reindexing_progress

# Run asynchronously
result = get_reindexing_progress.delay()

# Run synchronously
result = get_reindexing_progress()
```

## React Components

### Single Statistics Components

- `SingleStatRecordCount`: Number of records added during a period
- `SingleStatUploaders`: Number of active uploaders during a period
- `SingleStatDataVolume`: Volume of downloaded data during a period
- `SingleStatViews`: Number of unique views during a period
- `SingleStatDownloads`: Number of unique downloads during a period
- `SingleStatTraffic`: Volume of data downloaded during a period
- `SingleStatRecordCountCumulative`: Cumulative total number of records added by a given date
- `SingleStatUploadersCumulative`: Cumulative total number of unique uploaders by a date
- `SingleStatDataVolumeCumulative`: Cumulative total volume of data downloaded by a date
- `SingleStatViewsCumulative`: Cumulative total number of unique views by a date
- `SingleStatDownloadsCumulative`: Cumulative total number of unique downloads by a date
- `SingleStatTrafficCumulative`: Cumulative total volume of data downloaded by a date

### Chart Components

- `ContentStatsChart`: Record counts over time
- `TrafficStatsChart`: Download traffic over time
- `TrafficStatsChartCumulative`: Cumulative download traffic over time
- `UploaderStatsChart`: Uploader activity over time
- `UploaderStatsChartCumulative`: Cumulative uploader activity over time

### Multi-Display Components

- `ResourceTypesMultiDisplay`: Breakdown by resource type
- `AccessStatusMultiDisplay`: Breakdown by access status
- `LanguagesMultiDisplay`: Breakdown by language
- `PublishersMultiDisplay`: Breakdown by publisher
- `SubjectsMultiDisplay`: Breakdown by subject classification
- `TopCountriesMultiDisplay`: Top countries by traffic
- `TopReferrersMultiDisplay`: Top referrers by traffic
- `MostDownloadedRecordsMultiDisplay`: Most downloaded records
- `MostViewedRecordsMultiDisplay`: Most viewed records

### Map Components

- `StatsMap`: Interactive world map showing geographic distribution

## Event Types

### Community Events

Community membership events are stored in the `stats-community-events` index:

```json
{
    "timestamp": "2021-01-01T00:00:00Z",
    "community_id": "global",
    "record_id": "1234567890",
    "event_type": "add",
    "event_date": "2021-01-01",
    "record_created_date": "2020-01-01",
    "record_published_date": "2020-01-01",
    "is_deleted": true,
    "deleted_date": "2021-01-04",
    "updated_timestamp": "2021-01-01T00:00:00Z"
}
```

### Usage Events

Enriched usage events include community and metadata information:

```json
{
    "timestamp": "2021-01-01T00:00:00Z",
    "record_id": "1234567890",
    "community_ids": ["community-1", "community-2"],
    "resource_type": "publication-article",
    "access_status": "open",
    "languages": ["en"],
    "subjects": ["Computer Science"],
    "publisher": "Example Publisher",
    "funders": ["National Science Foundation"],
    "affiliations": ["University of Example"]
}
```

## Search Indices

### Aggregation Indices

- `stats-community-records-delta-created-YYYY`
- `stats-community-records-delta-published-YYYY`
- `stats-community-records-delta-added-YYYY`
- `stats-community-records-snapshot-created-YYYY`
- `stats-community-records-snapshot-published-YYYY`
- `stats-community-records-snapshot-added-YYYY`
- `stats-community-usage-delta-YYYY`
- `stats-community-usage-snapshot-YYYY`

### Event Indices

- `stats-community-events-YYYY`
- `events-stats-record-view-YYYY-MM`
- `events-stats-file-download-YYYY-MM`

## Error Handling

The module provides comprehensive error handling for:

- **Migration failures**: Automatic retry with exponential backoff
- **Aggregation errors**: Graceful degradation with error reporting
- **Service failures**: Fallback to cached data when available
- **Configuration errors**: Validation with helpful error messages

## Logging

The module uses Python's standard logging framework with the following loggers:

- `invenio_stats_dashboard`: Main module logger
- `invenio_stats_dashboard.aggregators`: Aggregator-specific logging
- `invenio_stats_dashboard.services`: Service-specific logging
- `invenio_stats_dashboard.tasks`: Task-specific logging
### Configuration Reference

The following table provides a complete reference of all available configuration variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `COMMUNITY_STATS_ENABLED` | `True` | Enable/disable the entire module |
| `COMMUNITY_STATS_SCHEDULED_TASKS_ENABLED` | `False` | Enable/disable scheduled aggregation tasks |
| `COMMUNITY_STATS_CELERYBEAT_SCHEDULE` | `{...}` | Celery beat schedule for aggregation tasks |
| `COMMUNITY_STATS_CATCHUP_INTERVAL` | `365` | Maximum days to catch up when aggregating historical data |
| `COMMUNITY_STATS_AGGREGATIONS` | `{...}` | Aggregation configurations (auto-generated) |
| `COMMUNITY_STATS_QUERIES` | `{...}` | Query configurations (auto-generated) |
| `COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT` | `20` | Maximum number of items to return in subcount breakdowns |
| `COMMUNITY_STATS_SUBCOUNTS` | `{...}` | Configuration for subcount breakdowns and field mappings |
| `STATS_DASHBOARD_UI_SUBCOUNTS` | `{...}` | UI subcount configuration for different breakdown types |
| `STATS_DASHBOARD_LOCK_CONFIG` | `{...}` | Distributed locking configuration for aggregation tasks |
| `STATS_DASHBOARD_TEMPLATES` | `{...}` | Template paths for dashboard views |
| `STATS_DASHBOARD_ROUTES` | `{...}` | URL routes for dashboard pages |
| `STATS_DASHBOARD_UI_CONFIG` | `{...}` | UI configuration for dashboard appearance and behavior |
| `STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS` | `{...}` | Default date range options for different granularities |
| `STATS_DASHBOARD_LAYOUT` | `{...}` | Dashboard layout and component configuration |
| `STATS_DASHBOARD_MENU_ENABLED` | `True` | Enable/disable menu integration |
| `STATS_DASHBOARD_MENU_TEXT` | `_("Statistics")` | Menu item text |
| `STATS_DASHBOARD_MENU_ORDER` | `1` | Menu item order |
| `STATS_DASHBOARD_MENU_ENDPOINT` | `"invenio_stats_dashboard.global_stats_dashboard"` | Menu item endpoint |
| `STATS_DASHBOARD_MENU_REGISTRATION_FUNCTION` | `None` | Custom menu registration function |
| `STATS_DASHBOARD_USE_TEST_DATA` | `True` | Enable/disable test data mode for development |
| `STATS_DASHBOARD_REINDEXING_MAX_BATCHES` | `1000` | Maximum batches per month for migration |
| `STATS_DASHBOARD_REINDEXING_BATCH_SIZE` | `5000` | Events per batch for migration. **Note: OpenSearch has a hard limit of 10,000 documents for search results, so this value cannot exceed 10,000.** |
| `STATS_DASHBOARD_REINDEXING_MAX_MEMORY_PERCENT` | `85` | Maximum memory usage percentage before stopping migration |
| `STATS_EVENTS` | `{...}` | Event type configurations for statistics processing |

**Note**: Variables marked with `{...}` contain complex configuration objects that are documented in detail in the sections above.


