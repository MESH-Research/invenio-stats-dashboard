## Configuration

### Configuration Overrides

The default configuration values are defined in the module's `config.py` file. These defaults can be overridden in the top-level `invenio.cfg` file of
an InvenioRDM instance or as environment variables.

### Module Enable/Disable

The entire community stats dashboard module can be enabled or disabled using the `COMMUNITY_STATS_ENABLED` configuration variable:

```python
# Disable the module completely
COMMUNITY_STATS_ENABLED = False
```

When disabled:
- **Scheduled tasks will not run**: No automatic aggregation or migration tasks
- **CLI commands will fail**: All commands will show an error message
- **Services will not be initialized**: No event tracking or statistics services
- **Menus will not be registered**: No dashboard menu items
- **Components will not be added**: No event tracking components

**Note**: This is a global on/off switch. When disabled, the module will not modify the instance in any way.

### Scheduled Tasks Enable/Disable

Scheduled aggregation tasks can be controlled separately using the `COMMUNITY_STATS_SCHEDULED_TASKS_ENABLED` configuration variable:

```python
# Enable the module but disable scheduled tasks
COMMUNITY_STATS_ENABLED = True
COMMUNITY_STATS_SCHEDULED_TASKS_ENABLED = False
```

When scheduled tasks are disabled:
- **Scheduled aggregation tasks will not run**: No automatic daily/weekly aggregation
- **CLI aggregation commands will fail**: `aggregate` command will show an error unless `--force` is used
- **Manual aggregation with --force**: You can still run aggregation manually using `invenio community-stats aggregate --force`
- **All other functionality remains**: Event tracking, migration, and other features work normally

This allows you to enable the module for manual operations while preventing automatic background tasks. The `--force` flag bypasses the scheduled tasks check and allows manual aggregation even when scheduled tasks are disabled.

### View/Download event migration

The following configuration variables control the default behavior of migration commands:

```python
STATS_DASHBOARD_REINDEXING_MAX_BATCHES = 1000  # Maximum number of batches to process per month
STATS_DASHBOARD_REINDEXING_BATCH_SIZE = 1000  # Number of events to process per batch
STATS_DASHBOARD_REINDEXING_MAX_MEMORY_PERCENT = 75  # Maximum memory usage percentage before stopping
```

These defaults can be overridden using the corresponding CLI options when running the `migrate-events` command.

### Task scheduling and aggregation

The following configuration variables control the scheduling and behavior of aggregation tasks:

```python
from invenio_stats_dashboard.tasks import CommunityStatsAggregationTask

COMMUNITY_STATS_CELERYBEAT_SCHEDULE = {
    "stats-aggregate-community-record-stats": {
        **CommunityStatsAggregationTask,
    },
}
"""Celery beat schedule for aggregation tasks."""

COMMUNITY_STATS_CATCHUP_INTERVAL = 365
"""Maximum number of days to catch up when aggregating historical data."""
```

### Task locking

The following configuration variables control the distributed locking mechanism for stats tasks:

```python
STATS_DASHBOARD_LOCK_CONFIG = {
    "enabled": True,  # Enable/disable distributed locking globally
    "aggregation": {
        "enabled": True,  # Enable/disable locking for aggregation tasks
        "lock_timeout": 86400,  # Lock timeout in seconds (24 hours)
        "lock_name": "community_stats_aggregation",  # Lock name
    },
    "response_caching": {
        "enabled": True,  # Enable/disable locking for cache generation tasks
        "lock_timeout": 3600,  # Lock timeout in seconds (1 hour)
        "lock_name": "community_stats_cache_generation",  # Lock name
    },
}
```

This configuration allows you to:
- **Enable/disable locking globally** with the top-level `enabled` flag
- **Configure each task type independently** with separate timeouts and lock names
- **Allow concurrent execution** of different task types (aggregation and cache generation can run simultaneously)
- **Prevent duplicate instances** of the same task type from running simultaneously

### Cache generation scheduled tasks

When `COMMUNITY_STATS_SCHEDULED_TASKS_ENABLED` is set to `True`, both aggregation and cache generation tasks will run hourly. The cache generation task pre-generates cached responses for the current year for all communities and all data series categories, ensuring that dashboard page loads are fast by having the data ready in advance.

The schedule includes both tasks:

```python
from celery.schedules import crontab
from invenio_stats_dashboard.tasks import CommunityStatsAggregationTask

COMMUNITY_STATS_CELERYBEAT_SCHEDULE = {
    "stats-aggregate-community-record-stats": {
        **CommunityStatsAggregationTask,  # Runs at minute 40
    },
    "stats-cache-hourly-generation": {
        "task": "invenio_stats_dashboard.tasks.generate_hourly_cache_task",
        "schedule": crontab(minute="50", hour="*"),  # Runs at minute 50
    },
}
```

#### Task timing

By default, the cache generation task runs at minute 50 every hour, which is carefully timed to:
- Run **10 minutes after** the stats aggregation task (minute 40) to ensure fresh data is available
- Be **well-spaced** from other InvenioRDM scheduled tasks to avoid resource contention:
  - minute 0: stats-aggregate-events
  - minute 10: reindex-stats
  - minute 25, 55: stats-process-events
  - minute 40: stats-aggregate-community-record-stats
  - minute 50: stats-cache-hourly-generation

You can customize the schedule by overriding `COMMUNITY_STATS_CELERYBEAT_SCHEDULE` in your `invenio.cfg` file:

```python
from celery.schedules import crontab
from invenio_stats_dashboard.tasks import CommunityStatsAggregationTask

COMMUNITY_STATS_CELERYBEAT_SCHEDULE = {
    "stats-aggregate-community-record-stats": {
        **CommunityStatsAggregationTask,
    },
    "stats-cache-hourly-generation": {
        "task": "invenio_stats_dashboard.tasks.generate_hourly_cache_task",
        "schedule": crontab(minute="45", hour="*/2"),  # Run every 2 hours at minute 45
    },
}
```

#### What gets cached

The hourly cache task generates cached responses for:
- **All communities** in your instance
- **The global stats** (instance-wide statistics)
- **The current year** only
- **All data series categories** (resource_types, subjects, languages, rights, funders, periodicals, publishers, affiliations, countries, referrers, file_types, access_statuses)

This covers the most commonly accessed data and ensures that current year dashboard views load quickly. Historical data for previous years is cached on-demand when first accessed.

### Default range options

The following configuration variable controls the default date range options for the dashboard. The keys represent the
available granularity levels for the date range selector and cannot be changed. The values represent the default date
range for each granularity level.

```python
STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS = {
    "day": "30days",
    "week": "12weeks",
    "month": "12months",
    "quarter": "4quarters",
    "year": "5years",
}
```

### Menu configuration

The following configuration variables control the menu integration for the global dashboard:

```python
STATS_DASHBOARD_MENU_ENABLED = True
"""Enable or disable the stats menu item."""

STATS_DASHBOARD_MENU_TEXT = _("Statistics")
"""Text for the stats menu item."""

STATS_DASHBOARD_MENU_ORDER = 1
"""Order of the stats menu item in the menu."""

STATS_DASHBOARD_MENU_ENDPOINT = "invenio_stats_dashboard.global_stats_dashboard"
"""Endpoint for the stats menu item."""

STATS_DASHBOARD_MENU_REGISTRATION_FUNCTION = None
"""Custom function to register the menu item. If None, uses default registration.
Should be a callable that takes the Flask app as its only argument."""
```

### Dashboard layout and components

The layout and components for the dashboard are configured via the `STATS_DASHBOARD_LAYOUT` configuration variable. This is a dictionary that maps dashboard types (currently `global` and `community`) to layout configurations. Each layout configuration is a dictionary that maps dashboard sections to a list of components to display in that section. Rows can be specified to group components together, and component widths can be specified with a "width" key.

For example, the default global layout configuration is:

```python
STATS_DASHBOARD_LAYOUT = {
    "global": {
        "tabs": [
            {
                "name": "content",
                "label": "Content",
                "rows": [
                    {
                        "name": "date-range-selector",
                        "components": [{"component": "DateRangeSelector", "width": 16}],
                    },
                    {
                        "name": "single-stats",
                        "components": [
                            {"component": "SingleStatRecordCount", "width": 3},
                            {"component": "SingleStatUploaders", "width": 3},
                            {"component": "SingleStatDataVolume", "width": 3},
                        ],
                    },
                    {
                        "name": "charts",
                        "components": [
                            {"component": "StatsChart", "width": 8},
                        ],
                    },
                    {
                        "name": "tables",
                        "components": [
                            {"component": "ResourceTypesTable", "width": 8},
                            {"component": "AccessStatusTable", "width": 8},
                            {"component": "RightsTable", "width": 8},
                            {"component": "AffiliationsTable", "width": 8},
                        ],
                    },
                ],
            },
        ],
    },
}
```
If no layout configuration is provided for a dashboard type, the default "global" layout configuration will be used.

Any additional key/value pairs in the dictionary for a component will be passed to the component class as additional props. This allows for some customization of the component without having to subclass and override the component class.

The component labels used for the layout configuration are defined in the `components_map.js` file, where they are mapped to the component classes.

### Routes

The routes for the dashboard are defined by the `STATS_DASHBOARD_ROUTES` configuration variable. This is a dictionary that maps dashboard types (currently `global` and `community`) to route strings.

For example, the default routes are:

```python
STATS_DASHBOARD_ROUTES = {
    "global": "/stats",
    "community": "/communities/<community_id>/stats",
}
```

### Templates

The templates for the dashboard are defined by the `STATS_DASHBOARD_TEMPLATES` configuration variable. This is a dictionary that maps dashboard types (currently `global` and `community`) to template strings.

For example, the default templates are:

```python
STATS_DASHBOARD_TEMPLATES = {
    "macro": "invenio_stats_dashboard/macros/stats_dashboard_macro.html",
    "global": "invenio_stats_dashboard/stats_dashboard.html",
    "community": "invenio_stats_dashboard/community_stats_dashboard.html",
}
```

### UI Configuration

The UI configuration for the dashboard is defined by the `STATS_DASHBOARD_UI_CONFIG` configuration variable. This is a dictionary that maps dashboard types (currently `global` and `community`) to a dictionary of configuration options.

For example, the default UI configuration is:

```python
STATS_DASHBOARD_UI_CONFIG = {
    "global": {
        "title": _("Statistics"),
        "description": _("This is the global stats dashboard."),
        "maxHistoryYears": 15,
        "default_granularity": "month",
        "show_title": True,
        "show_description": False,
    },
    "community": {
        "title": _("Statistics"),
        "description": _("This is the community stats dashboard."),
        "maxHistoryYears": 15,
        "default_granularity": "month",
        "show_title": True,
        "show_description": False,
    },
}
```

#### Title and description display

The title and description display in different places for the global and community dashboards. For the global dashboard, the title and description are displayed in the page subheader, while for the community dashboard they display at the top of the dashboard sidebar.

The `show_title` and `show_description` options can be used to control whether the title and description are displayed for the global and community dashboards.

### Subcount Configuration

The following configuration variables control how subcount breakdowns are generated and displayed:

#### `COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT`

This variable controls the maximum number of items returned in subcount breakdowns (e.g., "Top 20 Resource Types"). This helps prevent overwhelming the UI with too many items and improves performance.

```python
COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT = 20
```

#### `COMMUNITY_STATS_SUBCOUNTS`

This variable defines the configuration for different subcount breakdown types, including field mappings and display options.

```python
COMMUNITY_STATS_SUBCOUNTS = {
    "resource_types": {
        "records": {
            "source_fields": [
                {
                    "field": "metadata.resource_type.id",
                    "label_field": "metadata.resource_type.title",
                    "label_source_includes": ["metadata.resource_type.id", "metadata.resource_type.title"]
                }
            ]
        }
    },
    "subjects": {
        "records": {
            "source_fields": [
                {
                    "field": "metadata.subjects.subject",
                    "label_field": "metadata.subjects.subject",
                    "label_source_includes": ["metadata.subjects.subject"]
                }
            ]
        }
    },
    # ... other subcount configurations
}
```

#### `STATS_DASHBOARD_UI_SUBCOUNTS`

This variable controls which subcount breakdowns are available in the UI and how they are displayed.

```python
STATS_DASHBOARD_UI_SUBCOUNTS = {
    "resource_types": {},
    "subjects": {},
    "languages": {},
    "rights": {},
    "funders": {},
    "periodicals": {},
    "publishers": {},
    "affiliations": {
        "records": {
            "source_fields": [
                {
                    "field": "metadata.creators.affiliations.id",
                    "label_field": "metadata.creators.affiliations.name",
                    "label_source_includes": ["metadata.creators.affiliations.id", "metadata.creators.affiliations.name"],
                    "combine_subfields": ["id", "name.keyword"]
                },
                {
                    "field": "metadata.contributors.affiliations.id",
                    "label_field": "metadata.contributors.affiliations.name",
                    "label_source_includes": ["metadata.contributors.affiliations.id", "metadata.contributors.affiliations.name"],
                    "combine_subfields": ["id", "name.keyword"]
                }
            ]
        }
    },
    "countries": {},
    "referrers": {},
    "file_types": {},
    "access_statuses": {},
}
```

### Bulk Indexing and Request Size Limits

#### 413 Error Risk and Adaptive Chunking

When processing large datasets (such as a full year of catchup data), aggregation documents can become very large due to extensive subcount data. This can cause **TransportError(413)** - "Request size exceeded" errors when bulk indexing to OpenSearch/Elasticsearch.

**Why documents get large:**
- Each aggregation document includes 12+ subcount categories (subjects, affiliations, funders, etc.)
- Each subcount item contains 10+ fields (view/download metrics, unique counts, etc.)
- With `COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT = 20`, documents can contain 1000+ fields
- Large documents (30-60KB each) × 50 documents per bulk request = 10MB+ requests

**Adaptive Chunking Solution:**

The system automatically handles this with adaptive chunk sizing:

```python
# Configuration options for adaptive chunking
COMMUNITY_STATS_INITIAL_CHUNK_SIZE = 50      # Starting chunk size
COMMUNITY_STATS_MIN_CHUNK_SIZE = 1           # Minimum chunk size  
COMMUNITY_STATS_MAX_CHUNK_SIZE = 100         # Maximum chunk size
COMMUNITY_STATS_CHUNK_REDUCTION_FACTOR = 0.7  # Reduce by 30% on 413 error
COMMUNITY_STATS_CHUNK_GROWTH_FACTOR = 1.05   # Increase by 5% on success
```

**How it works:**
1. **Start** with `initial_chunk_size` (50 documents)
2. **Success** → increase chunk size by 5% (up to max limit)
3. **413 Error** → reduce chunk size by 30% and retry
4. **Learning** → adapts to find optimal chunk size for your data

**Example flow:**
```
Try chunk_size=50 → Success → Increase to 52 (50 * 1.05)
Try chunk_size=52 → Success → Increase to 54 (52 * 1.05)
Try chunk_size=54 → Success → Increase to 56 (54 * 1.05)
Try chunk_size=56 → 413 Error → Reduce to 39 (56 * 0.7)
Try chunk_size=39 → Success → Continue with 39
```

**Benefits:**
- **Automatic**: No manual tuning needed
- **Efficient**: Finds optimal chunk size quickly
- **Robust**: Handles any request size limit (AWS OpenSearch, nginx, etc.)
- **Performance**: Uses largest possible chunk size that works

**Reducing document size:**
If you want to reduce document sizes to improve performance:
- Lower `COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT` (from 20 to 10)
- Remove unused subcount categories from `COMMUNITY_STATS_SUBCOUNTS`
- Use fewer subcount fields in your configuration

### Test Data Mode

#### `STATS_DASHBOARD_USE_TEST_DATA`

This variable enables test data mode for development and testing purposes. When enabled, the dashboard will use synthetic data instead of making API calls to the statistics service.

```python
STATS_DASHBOARD_USE_TEST_DATA = True
```

**Note**: This should be set to `False` in production environments to ensure real statistics data is displayed.

### JSON Compression Configuration

#### `STATS_DASHBOARD_COMPRESS_JSON`

This variable controls whether the frontend requests compressed JSON from the API. This is useful for optimizing bandwidth usage and avoiding double compression when server-level compression is already configured.

```python
STATS_DASHBOARD_COMPRESS_JSON = False  # Default: False
```

**Configuration Options:**

- **`False` (Default)**: Frontend requests plain JSON (`application/json`) and lets the server handle compression
  - ✅ **Use when**: Server-level compression is enabled (nginx, Apache, etc.)
  - ✅ **Benefit**: Avoids double compression, more efficient
  - ✅ **Result**: Server compresses the response using HTTP-level compression

- **`True`**: Frontend requests compressed JSON (`application/json+gzip`) from the API
  - ✅ **Use when**: No server-level compression is configured
  - ✅ **Benefit**: Still get compressed responses even without server-level compression
  - ✅ **Result**: API compresses the response using application-level compression

**Important**: When server-level compression is enabled, setting this to `True` can result in double compression, which is inefficient and may cause issues. Always set this to `False` when using nginx, Apache, or other reverse proxies with compression enabled.

### Event Processing Configuration

#### `STATS_EVENTS`

This variable defines the event types and their configurations for statistics processing. It controls which events are tracked and how they are processed.

```python
STATS_EVENTS = {
    "file-download": {
        "processor": "invenio_stats.processors.flag_robots",
        "processor": "invenio_stats.processors.flag_machines",
        "processor": "invenio_stats.processors.anonymize_user",
    },
    "record-view": {
        "processor": "invenio_stats.processors.flag_robots",
        "processor": "invenio_stats.processors.flag_machines",
        "processor": "invenio_stats.processors.anonymize_user",
    },
}
```

### Auto-Generated Configuration

The following configuration variables are automatically generated by the module and typically do not need manual configuration:

#### `COMMUNITY_STATS_AGGREGATIONS`

This variable contains the aggregation configurations for all statistics aggregators. It is automatically populated by the `register_aggregations()` function and includes configurations for record counts, usage statistics, and other metrics.

#### `COMMUNITY_STATS_QUERIES`

This variable contains the query configurations for accessing statistics data. It is automatically populated and includes configurations for different types of statistics queries.

### Configuration Reference

The following table provides a complete reference of all available configuration variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `COMMUNITY_STATS_ENABLED` | `True` | Enable/disable the entire module |
| `COMMUNITY_STATS_SCHEDULED_TASKS_ENABLED` | `False` | Enable/disable scheduled tasks (aggregation and cache generation) |
| `COMMUNITY_STATS_CELERYBEAT_SCHEDULE` | `{...}` | Celery beat schedule for stats tasks (aggregation and cache generation) |
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
| `STATS_DASHBOARD_COMPRESS_JSON` | `False` | Control whether frontend requests compressed JSON from API |
| `STATS_DASHBOARD_REINDEXING_MAX_BATCHES` | `1000` | Maximum batches per month for migration |
| `STATS_DASHBOARD_REINDEXING_BATCH_SIZE` | `5000` | Events per batch for migration. **Note: OpenSearch has a hard limit of 10,000 documents for search results, so this value cannot exceed 10,000.** |
| `STATS_DASHBOARD_REINDEXING_MAX_MEMORY_PERCENT` | `85` | Maximum memory usage percentage before stopping migration |
| `STATS_EVENTS` | `{...}` | Event type configurations for statistics processing |

**Note**: Variables marked with `{...}` contain complex configuration objects that are documented in detail in the sections above.

### Content Negotiation and Response Serializers

The API supports multiple response formats through content negotiation. The `COMMUNITY_STATS_SERIALIZERS` configuration controls which serializers are available for different content types. The frontend's compression behavior is controlled by the `STATS_DASHBOARD_COMPRESS_JSON` configuration variable (see [JSON Compression Configuration](#json-compression-configuration) above).

```python
COMMUNITY_STATS_SERIALIZERS = {
    "application/json": {
        "serializer": "invenio_stats_dashboard.resources.serializers:StatsJSONSerializer",
        "enabled_for": ["community-record-delta-created", ...]
    },
    "application/json+gzip": {
        "serializer": "invenio_stats_dashboard.resources.data_series_serializers:GzipStatsJSONSerializer",
        "enabled_for": ["usage-snapshot-series", "usage-delta-series", ...]
    },
    "application/json+br": {
        "serializer": "invenio_stats_dashboard.resources.data_series_serializers:BrotliStatsJSONSerializer",
        "enabled_for": ["usage-snapshot-series", "usage-delta-series", ...]
    },
    "text/csv": {
        "serializer": "invenio_stats_dashboard.resources.data_series_serializers:DataSeriesCSVSerializer",
        "enabled_for": ["usage-snapshot-series", "usage-delta-series", ...]
    }
}
```

#### Compression Support

- **Gzip**: Widely supported, good compression ratio
- **Brotli**: Better compression (15-25% smaller), preferred when available
- **Automatic fallback**: Brotli falls back to Gzip if the `brotli` package is not available

#### Custom Serializers

You can add custom serializers by extending the configuration:

```python
COMMUNITY_STATS_SERIALIZERS["application/custom"] = {
    "serializer": "your_module.serializers:CustomSerializer",
    "enabled_for": ["usage-snapshot-series"]
}
```


