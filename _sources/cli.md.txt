# CLI Commands

The `invenio-stats-dashboard` module provides CLI commands for managing statistics infrastructure, migrating events, and monitoring progress. All commands are available as subcommands under the `invenio community-stats` command, organized into command groups.

### Core Commands

#### `aggregate`

Manually trigger the aggregation of statistics for a community or instance.

```bash
invenio community-stats aggregate [OPTIONS]
```

**Options:**

- `--community-id`: The UUID or slug of the community to aggregate stats for. Can be specified multiple times. If not specified, aggregates for all communities and the global instance.
- `--start-date`: The start date to aggregate stats for (YYYY-MM-DD). Default: creation/publication/adding of the first record.
- `--end-date`: The end date to aggregate stats for (YYYY-MM-DD). Default: today.
- `--eager/--no-eager`: Run aggregation eagerly (synchronously). Default: True (synchronous). Use `--no-eager` for asynchronous Celery execution (blocks until complete).
- `--update-bookmark`: Update the progress bookmark after aggregation (default: True).
- `--ignore-bookmark`: Ignore the progress bookmark and force a full re-aggregation.
- `--verbose`: Show detailed timing information for each aggregator.
- `--force`: Force aggregation even if scheduled aggregation tasks are disabled. Bypasses the `COMMUNITY_STATS_SCHEDULED_AGG_TASKS_ENABLED` configuration check.

**Examples:**

```bash
# Aggregate stats for all communities and the global instance
invenio community-stats aggregate

# Aggregate stats for specific community
invenio community-stats aggregate --community-id my-community-id

# Aggregate stats for specific date range
invenio community-stats aggregate --start-date 2024-01-01 --end-date 2024-01-31

# Run with verbose output
invenio community-stats aggregate --ignore-bookmark --verbose

# Force aggregation when scheduled tasks are disabled
invenio community-stats aggregate --force --verbose

# Run asynchronously via Celery (blocks until complete, but runs in worker)
invenio community-stats aggregate --no-eager --verbose
```

**Configuration Requirements:**

The `aggregate` command requires specific configuration settings to function properly:

- `COMMUNITY_STATS_ENABLED` (default: `True`): Must be set to `True` to enable community stats functionality. When disabled, the command will raise an error.
- `COMMUNITY_STATS_SCHEDULED_AGG_TASKS_ENABLED` (default: `True`): Controls whether scheduled aggregation tasks are enabled. When disabled, the command will require the `--force` flag to run.

**Error Handling:**

- If `COMMUNITY_STATS_ENABLED` is `False`, the command will exit with an error message.
- If `COMMUNITY_STATS_SCHEDULED_AGG_TASKS_ENABLED` is `False` and `--force` is not provided, the command will exit with an error message suggesting to use `--force`.
- When `--force` is used, the command will log that it's bypassing the scheduled tasks check.

#### `aggregate-background`

Start community statistics aggregation in the background with full process management.

```bash
invenio community-stats aggregate-background [OPTIONS]
```

This command provides the same functionality as `aggregate` but runs in the background as a separate process, allowing you to start long-running aggregations without blocking your terminal. The aggregation runs eagerly (synchronously within the background process), not as a Celery task.

**Options:**

- `--community-id`: The UUID or slug of the community to aggregate stats for. Can be specified multiple times.
- `--start-date`: The start date to aggregate stats for (YYYY-MM-DD).
- `--end-date`: The end date to aggregate stats for (YYYY-MM-DD).
- `--update-bookmark`: Update the progress bookmark after aggregation (default: True).
- `--ignore-bookmark`: Ignore the progress bookmark and force a full re-aggregation.
- `--verbose`: Show detailed timing information for each aggregator.
- `--force`: Force aggregation even if scheduled tasks are disabled.
- `--pid-dir`: Directory to store PID and status files (default: `/tmp`).

**Examples:**

```bash
# Start aggregation in background
invenio community-stats aggregate-background

# Aggregate specific community with verbose output
invenio community-stats aggregate-background --community-id my-community --verbose

# Aggregate with date range
invenio community-stats aggregate-background --start-date 2024-01-01 --end-date 2024-01-31

# Use custom PID directory for production
invenio community-stats aggregate-background --pid-dir /var/run/invenio-community-stats

# Monitor the background process
invenio community-stats processes status aggregation

# View logs from the background process
invenio community-stats processes status aggregation --show-log

# Cancel the background process if needed
invenio community-stats processes cancel aggregation
```

**Process Management:**

After starting a background aggregation, you can:

- Monitor progress: `invenio community-stats processes status aggregation`
- View logs: `invenio community-stats processes status aggregation --show-log`
- Cancel process: `invenio community-stats processes cancel aggregation`

The command creates the following files in the PID directory:

- `invenio-community-stats-aggregation.pid`: Process ID
- `invenio-community-stats-aggregation.status`: JSON status information
- `invenio-community-stats-aggregation.log`: Process output and logs

**When to Use:**

- Use `aggregate` for interactive execution with immediate results
- Use `aggregate-background` for long-running aggregations that you want to monitor separately
- Use `aggregate --no-eager` if you need Celery task execution (though it still blocks)

#### `read`

Read and display statistics data for a community or instance.

```bash
invenio community-stats read [OPTIONS]
```

**Options:**

- `--community-id`: The ID of the community to read stats for (default: "global").
- `--start-date`: The start date to read stats for (default: yesterday).
- `--end-date`: The end date to read stats for (default: today).
- `--query-type`: Specific query type to run instead of the meta-query. Available options:
  - `community-record-delta-created`
  - `community-record-delta-published`
  - `community-record-delta-added`
  - `community-record-snapshot-created`
  - `community-record-snapshot-published`
  - `community-record-snapshot-added`
  - `community-usage-delta`
  - `community-usage-snapshot`

**Examples:**

```bash
# Read global stats for yesterday
invenio community-stats read

# Read stats for specific community and date range
invenio community-stats read --community-id my-community --start-date 2024-01-01 --end-date 2024-01-31

# Read specific query type for a community
invenio community-stats read --community-id my-community --query-type community-usage-delta --start-date 2024-01-01
```

**Configuration Requirements:**

The `read` command requires the `COMMUNITY_STATS_ENABLED` configuration to be set to `True`. If disabled, the command will exit with an error message.

#### `clear-bookmarks`

Clear aggregation bookmarks for community statistics.

```bash
invenio community-stats clear-bookmarks [OPTIONS]
```

**Options:**

- `--community-id`: The UUID or slug of the community to clear bookmarks for. Can be specified multiple times.
- `--aggregation-type`: The aggregation type to clear bookmarks for. Can be specified multiple times.
- `--all-communities`: Clear bookmarks for all communities.
- `--all-aggregation-types`: Clear bookmarks for all aggregation types.
- `--confirm`: Confirm that you want to clear bookmarks without prompting.

**Available Aggregation Types:**

- `community-records-delta-created-agg`
- `community-records-delta-published-agg`
- `community-records-delta-added-agg`
- `community-records-snapshot-created-agg`
- `community-records-snapshot-published-agg`
- `community-records-snapshot-added-agg`
- `community-usage-delta-agg`
- `community-usage-snapshot-agg`

**Examples:**

```bash
# Clear all bookmarks for all communities and aggregation types
invenio community-stats clear-bookmarks --all-communities --all-aggregation-types

# Clear bookmarks for a specific community
invenio community-stats clear-bookmarks --community-id my-community-id

# Clear bookmarks for a specific aggregation type across all communities
invenio community-stats clear-bookmarks --aggregation-type community-records-delta-created-agg

# Clear bookmarks for multiple communities and types
invenio community-stats clear-bookmarks --community-id comm1 --community-id comm2 --confirm

# Clear all bookmarks without prompting
invenio community-stats clear-bookmarks --all-communities --all-aggregation-types --confirm
```

**Configuration Requirements:**

The `clear-bookmarks` command requires the `COMMUNITY_STATS_ENABLED` configuration to be set to `True`. If disabled, the command will exit with an error message.

#### `cache`

Manage cached statistics data and proactively generate cache entries.

```bash
invenio community-stats cache [SUBCOMMAND] [OPTIONS]
```

**Subcommands:**

- `generate`: Generate cached responses for all data series categories
- `clear-all`: Clear all cached statistics data
- `clear-pattern`: Clear cache entries matching a pattern
- `clear-item`: Clear a specific cached statistics item
- `info`: Show cache information including size and item count
- `list`: List all cached statistics keys
- `test`: Test cache functionality

##### `cache generate`

Generate cached stats responses for all data series categories (record_delta, usage_delta, etc.) for specified communities and years.

```bash
invenio community-stats cache generate [OPTIONS]
```

**Options:**

- `--community-id`: Community ID(s) to generate cache for (can be specified multiple times). If not specified, generates for all communities plus global.
- `--community-slug`: Community slug(s) to generate cache for (can be specified multiple times).
- `--year`: Single year to generate cache for.
- `--years`: Year range to generate cache for (e.g., 2020-2023).
- `--all-years`: Generate cache for all years since community creation.
- `--async`: Run cache generation asynchronously using Celery.
- `--force`: Overwrite existing cache entries.
- `--dry-run`: Show what would be done without actually generating cache.

**Description:**
This command generates cached responses for all data series categories, including:

- `record_delta` - Record count changes over time
- `record_snapshot` - Record counts at specific points in time
- `usage_delta` - Usage count changes over time
- `usage_snapshot` - Usage counts at specific points in time
- `record_delta_data_added` - Records added over time
- `record_delta_data_removed` - Records removed over time
- `usage_delta_data_views` - View count changes over time
- `usage_delta_data_downloads` - Download count changes over time

**Examples:**

```bash
# Generate cache for all communities + global for 2023
invenio community-stats cache generate --year 2023

# Generate cache for specific community and year
invenio community-stats cache generate --community-id 123 --year 2023

# Generate cache for multiple communities
invenio community-stats cache generate --community-id 123 --community-id 456 --year 2023

# Generate cache for community by slug
invenio community-stats cache generate --community-slug my-community --year 2023

# Generate cache for year range
invenio community-stats cache generate --community-id 123 --years 2020-2023

# Generate cache for all years since community creation
invenio community-stats cache generate --community-id 123 --all-years

# Generate cache asynchronously using Celery
invenio community-stats cache generate --community-id 123 --year 2023 --async

# Dry run to see what would be done
invenio community-stats cache generate --community-id 123 --year 2023 --dry-run

# Overwrite existing cache entries
invenio community-stats cache generate --community-id 123 --year 2023 --force
```

**Output Examples:**

```bash
# Dry run output
$ invenio community-stats cache generate --year 2023 --dry-run
Would generate cache for:
  Communities: global, 123, 456, 789
  Years: year 2023
  Categories: record_delta, record_snapshot, usage_delta, usage_snapshot, record_delta_data_added, record_delta_data_removed, usage_delta_data_views, usage_delta_data_downloads
  Total combinations: 32

# Synchronous execution
$ invenio community-stats cache generate --community-id 123 --year 2023
Generating cache...
✅ Cache generation completed
📊 Success: 8, Failed: 0

# Asynchronous execution
$ invenio community-stats cache generate --community-id 123 --year 2023 --async
Generating cache...
✅ Cache generation started in background
📋 Task IDs: ['abc123-def456-ghi789', 'jkl012-mno345-pqr678']
📊 Total tasks: 8
```

##### `cache clear-all`

Clear all cached statistics data from Redis.

```bash
invenio community-stats cache clear-all [OPTIONS]
```

**Options:**

- `--force`: Skip confirmation prompt and clear all cache immediately.
- `--yes-i-know`: Bypass confirmation prompt.

**Description:**
This command removes all cached statistics data from Redis. This will force all statistics queries to be recalculated on the next request.

**Examples:**

```bash
# Clear all cached data (interactive)
invenio community-stats cache clear-all

# Clear all cached data (non-interactive)
invenio community-stats cache clear-all --force --yes-i-know
```

##### `cache clear-pattern`

Clear cache entries matching a Redis key pattern.

```bash
invenio community-stats cache clear-pattern <pattern> [OPTIONS]
```

**Arguments:**

- `pattern`: Redis key pattern to match (e.g., "_global_", "_2023_", "_record_delta_").

**Options:**

- `--force`: Skip confirmation prompt and clear immediately.

**Description:**
This command removes all cached statistics entries that match the given Redis key pattern. It shows a preview of what will be cleared before performing the operation. Use with caution as this can delete multiple entries.

**Examples:**

```bash
# Clear all global stats cache entries
invenio community-stats cache clear-pattern "*global*"

# Clear all 2023 data cache entries
invenio community-stats cache clear-pattern "*2023*"

# Clear all record delta cache entries
invenio community-stats cache clear-pattern "*record_delta*"

# Clear without confirmation prompt
invenio community-stats cache clear-pattern "*global*" --force
```

**Pattern Examples:**

- `*global*` - All cache entries containing "global"
- `*2023*` - All cache entries containing "2023"
- `*record_delta*` - All cache entries containing "record_delta"
- `stats_dashboard:*community-123*` - All cache entries for community 123

##### `cache clear-item`

Clear a specific cached statistics item.

```bash
invenio community-stats cache clear-item <community-id> <stat-name> [OPTIONS]
```

**Arguments:**

- `community-id`: The ID of the community (or "global" for global stats). **Required.**
- `stat-name`: The name of the statistics query to clear. **Required.**

**Options:**

- `--start-date`: Start date for the cache entry (YYYY-MM-DD).
- `--end-date`: End date for the cache entry (YYYY-MM-DD).
- `--date-basis`: Date basis for the cache entry (added, created, published). Default: added.
- `--content-type`: Content type for the cache entry.

**Description:**
This command removes a specific cached statistics entry based on the provided parameters. If the exact cache entry is not found, no error will be reported. The `community-id` and `stat-name` arguments are required - Click will display an error message if they are not provided.

**Examples:**

```bash
# Clear specific cache entry (minimal required arguments)
invenio community-stats cache clear-item global record_snapshots

# Clear cache entry with specific date range
invenio community-stats cache clear-item 123 record_delta --start-date 2023-01-01 --end-date 2023-12-31

# Clear cache entry with specific date basis
invenio community-stats cache clear-item 123 record_snapshot --date-basis published

# Clear cache entry with content type
invenio community-stats cache clear-item global usage_delta --content-type application/json
```

**Error Handling:**
If required arguments are missing, Click will display an error message like:

```
Error: Missing argument 'COMMUNITY_ID'.
Usage: invenio community-stats cache clear-item [OPTIONS] COMMUNITY_ID STAT_NAME
```

##### `cache info`

Show cache information including size and item count.

```bash
invenio community-stats cache info
```

**Description:**
This command displays detailed information about the cache, including:

- Cache type and Redis version
- Memory usage (human-readable format)
- Number of connected clients
- Timestamp of the information

**Example Output:**

```bash
$ invenio community-stats cache info
Cache Information:
  Type: Redis (Direct)
  Redis Version: 7.2.5
  Used Memory: 2.5 MB
  Connected Clients: 16
  Timestamp: 2025-01-02T15:30:45.123456
```

##### `cache list`

List all cached statistics keys in Redis.

```bash
invenio community-stats cache list
```

**Description:**
This command lists all cache keys that match the stats dashboard prefix pattern.

**Example Output:**

```bash
$ invenio community-stats cache list
Found 4 cache keys:
  stats_dashboard:a11839c6a5d422d3c4d9648788dee7c1a46e8ac8dc6de08fbe21dca4fcaac710
  stats_dashboard:6cbdeb7e24b466a449e91a779797715e25c64ce238a67a13f7ac66f588121989
  stats_dashboard:c25599406871db725e80bdf58d9ee88edb8d732205787731de8931e851c3b00f
  stats_dashboard:edf486b8ddc331f62e79671a35e7b923c3cfce8c11294ef187ac0f4b89df4ac8
```

##### `cache test`

Test cache functionality by performing a complete cache cycle.

```bash
invenio community-stats cache test
```

**Description:**
This command performs a comprehensive test of the cache functionality by:

1. Creating a test cache entry
2. Retrieving the cached data
3. Verifying the data integrity
4. Clearing the test entry

**Example Output:**

```bash
$ invenio community-stats cache test
Testing cache functionality...
✅ Test cache entry created successfully
✅ Test cache entry retrieved successfully
✅ Data integrity verified
✅ Test cache entry cleaned up

🎉 Cache functionality test completed successfully!
```

**Configuration Requirements:**

The `cache` commands require the `COMMUNITY_STATS_ENABLED` configuration to be set to `True`. If disabled, the commands will exit with an error message.

**Cache Configuration:**

The cache system uses the following configuration variables:

- `STATS_CACHE_REDIS_DB`: Redis database number for stats cache (default: 7)
- `STATS_CACHE_PREFIX`: Cache key prefix (default: "stats_dashboard")
- `STATS_CACHE_DEFAULT_TTL`: Default cache TTL in seconds (default: None for no expiration)
- `STATS_CACHE_COMPRESSION_METHOD`: Compression method (default: "brotli")

#### `status`

Get aggregation status for communities, showing bookmark dates, document counts, and completeness visualization.

```bash
invenio community-stats status [OPTIONS]
```

**Options:**

- `--community-id, -c`: The ID of the community to check status for. Can be specified multiple times to check status for multiple communities. If not provided, checks all communities.
- `--verbose, -v`: Show detailed information for each aggregation.

**Description:**
This command provides a comprehensive overview of the aggregation status for community statistics. It shows:

- **Bookmark dates**: Current progress bookmarks for all aggregators
- **Document counts**: Number of documents in each aggregation index
- **Date ranges**: First and last document dates in each index
- **Days since last document**: How recently each aggregation was updated
- **Completeness visualization**: ASCII bar charts showing the proportion of time covered by each aggregation

The command supports two output modes:

- **Concise mode (default)**: One line per aggregation with abbreviated names and compact completeness bars
- **Verbose mode (`--verbose`)**: Detailed information including all the information listed above.

**Examples:**

```bash
# Check status for all communities (concise view)
invenio community-stats status

# Check status for specific community
invenio community-stats status --community-id my-community-id

# Check status for multiple communities
invenio community-stats status --community-id comm1 --community-id comm2

# Show detailed information for all communities
invenio community-stats status --verbose

# Show detailed information for specific community
invenio community-stats status --community-id my-community-id --verbose
```

**Configuration Requirements:**

The `status` command requires the `COMMUNITY_STATS_ENABLED` configuration to be set to `True`. If disabled, the command will exit with an error message.

#### `destroy-indices`

Destroy all search indices created by the invenio-stats-dashboard package.

```bash
invenio community-stats destroy-indices [OPTIONS]
```

**Options:**

- `--yes-i-know`: Skip confirmation prompt (required for non-interactive use).
- `--force`: Force deletion even if some indices don't exist (ignore 404 errors).

**Description:**
This command permanently deletes all search indices created by the invenio-stats-dashboard package. This includes:

- **Community events indices**: `stats-community-events-*`
- **Aggregation indices for community statistics**:
  - `stats-community-records-delta-*` (created, published, added)
  - `stats-community-records-snapshot-*` (created, published, added)
  - `stats-community-usage-delta-*`
  - `stats-community-usage-snapshot-*`
- **Enriched/migrated view and download indices (v2.0.0 versions only)**:
  - `events-stats-record-view-*-v2.0.0`
  - `events-stats-file-download-*-v2.0.0`

```{warning}
This will permanently delete all statistics data stored in OpenSearch. This data cannot be recovered once deleted. Only run this when you know what you are doing.
```

```{note}
This command will NOT destroy:
- View and download events in non-migrated indices (original usage events)
- Per-record view and download aggregations used for individual record stats

However, if the original view/download indices have been deleted after migration, the raw event data will be lost.
```

**Examples:**

```bash
# Destroy all invenio-stats-dashboard indices (interactive)
invenio community-stats destroy-indices

# Destroy all indices non-interactively
invenio community-stats destroy-indices --yes-i-know

# Force deletion even if some indices don't exist
invenio community-stats destroy-indices --yes-i-know --force
```

**Configuration Requirements:**

The `destroy-indices` command requires the `COMMUNITY_STATS_ENABLED` configuration to be set to `True`. If disabled, the command will exit with an error message.

**Output Examples:**

Concise mode:

```
Community: my-research-community (a1b2c3d4-e5f6-7890-abcd-ef1234567890)
------------------------------------------------------------
delta-created              [██████████████████████████████] 100% (today)
delta-published            [████████████████████████████░░] 95% (1d ago)
delta-added                [No index]
snapshot-created           [██████████████████████████████] 100% (today)
snapshot-published         [████████████████████████████░░] 95% (1d ago)
snapshot-added             [No index]
usage-delta                [██████████████████████████████] 100% (today)
usage-snapshot             [██████████████████████████████] 100% (today)
```

### Community Events Commands

#### `community-events generate`

Generate community add/remove events for all records in the instance or specific records/communities.

```bash
invenio community-stats community-events generate [OPTIONS]
```

**Options:**

- `--community-id`: The ID of the community to generate events for. Can be specified multiple times.
- `--record-ids`: The IDs of the records to generate events for. Can be specified multiple times.
- `--start-date`: Start date for filtering records by creation date (YYYY-MM-DD). If not provided, uses earliest record creation date.
- `--end-date`: End date for filtering records by creation date (YYYY-MM-DD). If not provided, uses current date.
- `--show-progress`: Show progress information during processing (default: True).

**Examples:**

```bash
# Generate events for all records
invenio community-stats community-events generate

# Generate events for specific community
invenio community-stats community-events generate --community-id my-community-slug

# Generate events for specific records
invenio community-stats community-events generate --record-ids abc123 def456 ghi789

# Generate events for specific date range
invenio community-stats community-events generate --start-date 2024-01-01 --end-date 2024-01-31
```

#### `community-events status`

Count records that need community events created and show detailed status information.

```bash
invenio community-stats community-events status [OPTIONS]
```

**Options:**

- `--community-id`: The ID of the community to check. Can be specified multiple times.
- `--record-ids`: The IDs of the records to check. Can be specified multiple times.
- `--start-date`: Start date for filtering records by creation date (YYYY-MM-DD). If not provided, uses earliest record creation date.
- `--end-date`: End date for filtering records by creation date (YYYY-MM-DD). If not provided, uses current date.
- `--community-details`: Show detailed community information.

**Examples:**

```bash
# Check status for all communities
invenio community-stats community-events status

# Check status for specific community with details
invenio community-stats community-events status --community-id my-community --community-details

# Check status for specific date range
invenio community-stats community-events status --start-date 2024-01-01 --end-date 2024-01-31
```

#### `community-events generate-background`

Start community event generation in the background with full process management capabilities.

```bash
invenio community-stats community-events generate-background [OPTIONS]
```

**Options:**

- `--community-id`: The ID of the community to generate events for. Can be specified multiple times.
- `--record-ids`: The IDs of the records to generate events for. Can be specified multiple times.
- `--start-date`: Start date for filtering records by creation date (YYYY-MM-DD). If not provided, uses earliest record creation date.
- `--end-date`: End date for filtering records by creation date (YYYY-MM-DD). If not provided, uses current date.
- `--pid-dir`: Directory to store PID and status files (default: `/tmp`).

**Examples:**

```bash
# Start background event generation for all records
invenio community-stats community-events generate-background

# Start background event generation for specific community
invenio community-stats community-events generate-background --community-id my-community-slug

# Use custom PID directory
invenio community-stats community-events generate-background --pid-dir /var/run/invenio-community-stats
```

**Process Management:**

- Process name: `community-event-generation`
- Monitor progress: `invenio community-stats processes status community-event-generation`
- Cancel process: `invenio community-stats processes cancel community-event-generation`
- View logs: `invenio community-stats processes status community-event-generation --show-log`

### Usage Events Commands

#### `usage-events generate`

Generate synthetic usage events (view/download) for testing purposes using the UsageEventFactory.

```bash
invenio community-stats usage-events generate [OPTIONS]
```

**Options:**

- `--start-date`: Start date for filtering records by creation date (YYYY-MM-DD). If not provided, uses earliest record creation date.
- `--end-date`: End date for filtering records by creation date (YYYY-MM-DD). If not provided, uses current date.
- `--event-start-date`: Start date for event timestamps (YYYY-MM-DD). If not provided, uses start-date.
- `--event-end-date`: End date for event timestamps (YYYY-MM-DD). If not provided, uses end-date.
- `--events-per-record`: Number of events to generate per record (default: 5).
- `--max-records`: Maximum number of records to process (default: 0 = all records).
- `--enrich-events`: Enrich events with additional data matching extended fields.
- `--dry-run`: Generate events but don't index them.
- `--yes-i-know`: Skip confirmation prompt.
- `--use-migrated-indices`: Use migrated indices with -v2.0.0 suffix when they exist.

**Examples:**

```bash
# Generate 5 events per record for all records
invenio community-stats usage-events generate

# Generate events for specific date range
invenio community-stats usage-events generate \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --events-per-record 10

# Dry run to see what would be generated
invenio community-stats usage-events generate --dry-run

# Generate enriched events for limited records
invenio community-stats usage-events generate \
  --max-records 100 \
  --enrich-events \
  --events-per-record 3
```

#### `usage-events generate-background`

Start usage event generation in the background with full process management capabilities.

```bash
invenio community-stats usage-events generate-background [OPTIONS]
```

**Options:**

- `--start-date`: Start date for filtering records by creation date (YYYY-MM-DD). If not provided, uses earliest record creation date.
- `--end-date`: End date for filtering records by creation date (YYYY-MM-DD). If not provided, uses current date.
- `--event-start-date`: Start date for event timestamps (YYYY-MM-DD). If not provided, uses start-date.
- `--event-end-date`: End date for event timestamps (YYYY-MM-DD). If not provided, uses end-date.
- `--events-per-record`: Number of events to generate per record (default: 5).
- `--max-records`: Maximum number of records to process (default: 0 = all records).
- `--enrich-events`: Enrich events with additional data matching extended fields.
- `--pid-dir`: Directory to store PID and status files (default: `/tmp`).

**Examples:**

```bash
# Start background usage event generation
invenio community-stats usage-events generate-background

# Start with custom parameters
invenio community-stats usage-events generate-background \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --events-per-record 10 \
  --enrich-events

# Use custom PID directory
invenio community-stats usage-events generate-background --pid-dir /var/run/invenio-community-stats
```

**Process Management:**

- Process name: `usage-event-generation`
- Monitor progress: `invenio community-stats processes status usage-event-generation`
- Cancel process: `invenio community-stats processes cancel usage-event-generation`
- View logs: `invenio community-stats processes status usage-event-generation --show-log`

#### `usage-events migrate`

Migrate existing usage (view and download) events to enriched indices with community and record metadata.

```bash
invenio community-stats usage-events migrate [OPTIONS]
```

**Options:**

- `--event-types, -e`: Event types to migrate (view, download). Can be specified multiple times. Defaults to both.
- `--max-batches, -b`: Maximum batches to process per month (default from `STATS_DASHBOARD_REINDEXING_MAX_BATCHES`).
- `--batch-size`: Number of events to process per batch (default from `STATS_DASHBOARD_REINDEXING_BATCH_SIZE`; max 10,000).
- `--max-memory-percent`: Maximum memory usage percentage before stopping (default from `STATS_DASHBOARD_REINDEXING_MAX_MEMORY_PERCENT`).
- `--dry-run`: Show what would be migrated without doing it.
- `--async`: Run reindexing asynchronously using Celery.
- `--delete-old-indices`: Delete old indices after migration (default is to keep them). Use `cleanup-old-indices` command to clean up later if needed.

**Examples:**

```bash
# Basic migration for all event types
invenio community-stats usage-events migrate

# Dry run to see what would be migrated
invenio community-stats usage-events migrate --dry-run

# Limit batches for testing
invenio community-stats usage-events migrate --max-batches 10

# Migrate only view events
invenio community-stats usage-events migrate --event-types view

# Run asynchronously with custom settings
invenio community-stats usage-events migrate --async --batch-size 500 --max-memory-percent 70
```

#### `usage-events migrate-background`

Start event migration in the background with full process management capabilities.

```bash
invenio community-stats usage-events migrate-background [OPTIONS]
```

**Options:**

- `--event-types, -e`: Event types to migrate (view, download). Can be specified multiple times. Defaults to both.
- `--max-batches, -b`: Maximum batches to process per month.
- `--batch-size`: Number of events to process per batch (default: 1000).
- `--max-memory-percent`: Maximum memory usage percentage before stopping (default: 85).
- `--delete-old-indices`: Delete old indices after migration. Use `cleanup-old-indices` command to clean up later if needed.
- `--pid-dir`: Directory to store PID and status files (default: `/tmp`).

**Examples:**

```bash
# Start background migration for all event types
invenio community-stats usage-events migrate-background

# Start background migration with custom settings
invenio community-stats usage-events migrate-background \
  --event-types view download \
  --batch-size 500 \
  --max-memory-percent 70 \
  --max-batches 100

# Use custom PID directory
invenio community-stats usage-events migrate-background --pid-dir /var/run/invenio-community-stats
```

**Process Management:**

- Process name: `event-migration`
- Monitor progress: `invenio community-stats processes status event-migration`
- Cancel process: `invenio community-stats processes cancel event-migration`
- View logs: `invenio community-stats processes status event-migration --show-log`

#### `usage-events status`

Show the current migration status and progress across all monthly indices.

```bash
invenio community-stats usage-events status [OPTIONS]
```

**Options:**

- `--show-bookmarks`: Show detailed bookmark information for each month.

**Examples:**

```bash
# Show basic migration status
invenio community-stats usage-events status

# Show detailed status with bookmarks
invenio community-stats usage-events status --show-bookmarks
```

#### `usage-events clear-bookmarks`

Clear migration bookmarks for specific months or all months.

```bash
invenio community-stats usage-events clear-bookmarks [OPTIONS]
```

**Options:**

- `--event-type`: Event type to clear bookmarks for (view, download). Can be specified multiple times.
- `--months`: Months to clear bookmarks for (YYYY-MM). Can be specified multiple times.
- `--fresh-start`: Clear all bookmarks and start fresh.

**Examples:**

```bash
# Clear bookmarks for all months and event types
invenio community-stats usage-events clear-bookmarks --fresh-start

# Clear bookmarks for specific month and event type
invenio community-stats usage-events clear-bookmarks --event-type view --months 2024-01

# Clear bookmarks for multiple months
invenio community-stats usage-events clear-bookmarks --months 2024-01 --months 2024-02
```

#### `usage-events cleanup-old-indices`

Clean up old indices that have been successfully migrated. This command identifies old indices that have corresponding migrated indices and validates that the migration was completed successfully before deleting the old indices.

```bash
invenio community-stats usage-events cleanup-old-indices [OPTIONS]
```

**Options:**

- `--event-types, -e`: Event types to clean up (view, download). Can be specified multiple times. Defaults to both.
- `--dry-run`: Show what would be deleted without actually deleting.

**Validation Checks:**

This command performs multiple validation checks before deleting old indices:

1. **Bookmark Validation**: Checks that the migration bookmark indicates completion
2. **Document Count Validation**: Verifies that at least 95% of events were migrated
3. **Existence Validation**: Ensures the migrated index has events

**Examples:**

```bash
# Preview what would be deleted (recommended first step)
invenio community-stats usage-events cleanup-old-indices --dry-run

# Clean up old indices for all event types
invenio community-stats usage-events cleanup-old-indices

# Clean up only view event indices
invenio community-stats usage-events cleanup-old-indices --event-types view

# Clean up specific event types
invenio community-stats usage-events cleanup-old-indices --event-types view download
```

**Note:** This command is useful when migrations were run with `--delete-old-indices=false` (the default) and you want to clean up old indices after verifying that migrations completed successfully.

### Process Management Commands

These commands provide monitoring and control capabilities for background processes started with the `*-background` commands.

#### `processes status`

Monitor the status of a running background process.

```bash
invenio community-stats processes status <process-name> [OPTIONS]
```

**Arguments:**

- `process-name`: Name of the process to monitor (e.g., `event-migration`, `community-event-generation`, `usage-event-generation`).

**Options:**

- `--show-log`: Show recent log output from the process.
- `--log-lines`: Number of log lines to show (default: 20).
- `--pid-dir`: Directory containing PID and status files (default: `/tmp`).

**Examples:**

```bash
# Check basic status
invenio community-stats processes status event-migration

# Show recent logs
invenio community-stats processes status event-migration --show-log

# Show more log lines
invenio community-stats processes status event-migration --show-log --log-lines 50
```

#### `processes cancel`

Gracefully cancel a running background process.

```bash
invenio community-stats processes cancel <process-name> [OPTIONS]
```

**Arguments:**

- `process-name`: Name of the process to cancel (e.g., `event-migration`, `community-event-generation`, `usage-event-generation`).

**Options:**

- `--timeout`: Seconds to wait for graceful shutdown before force kill (default: 30).
- `--pid-dir`: Directory containing PID files (default: `/tmp`).

**Examples:**

```bash
# Cancel with default timeout
invenio community-stats processes cancel event-migration

# Cancel with custom timeout
invenio community-stats processes cancel event-migration --timeout 60
```

#### `processes list`

List all currently running background processes.

```bash
invenio community-stats processes list [OPTIONS]
```

**Options:**

- `--pid-dir`: Directory containing PID files (default: `/tmp`).
- `--package-only`: Only show processes managed by invenio-stats-dashboard.

**Examples:**

```bash
# List all processes
invenio community-stats processes list

# List only package processes
invenio community-stats processes list --package-only
```
