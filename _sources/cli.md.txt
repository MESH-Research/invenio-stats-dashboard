## CLI Commands

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
- `--eager`: Run aggregation eagerly (synchronously) rather than asynchronously.
- `--update-bookmark`: Update the progress bookmark after aggregation (default: True).
- `--ignore-bookmark`: Ignore the progress bookmark and force a full re-aggregation.
- `--verbose`: Show detailed timing information for each aggregator.
- `--force`: Force aggregation even if scheduled tasks are disabled. Bypasses the `COMMUNITY_STATS_SCHEDULED_TASKS_ENABLED` configuration check.

**Examples:**
```bash
# Aggregate stats for all communities and the global instance
invenio community-stats aggregate

# Aggregate stats for specific community
invenio community-stats aggregate --community-id my-community-id

# Aggregate stats for specific date range
invenio community-stats aggregate --start-date 2024-01-01 --end-date 2024-01-31

# Force eager aggregation with verbose output
invenio community-stats aggregate --eager --ignore-bookmark --verbose

# Force aggregation when scheduled tasks are disabled
invenio community-stats aggregate --force --verbose
```

**Configuration Requirements:**

The `aggregate` command requires specific configuration settings to function properly:

- `COMMUNITY_STATS_ENABLED` (default: `True`): Must be set to `True` to enable community stats functionality. When disabled, the command will raise an error.
- `COMMUNITY_STATS_SCHEDULED_TASKS_ENABLED` (default: `True`): Controls whether scheduled aggregation tasks are enabled. When disabled, the command will require the `--force` flag to run.

**Error Handling:**

- If `COMMUNITY_STATS_ENABLED` is `False`, the command will exit with an error message.
- If `COMMUNITY_STATS_SCHEDULED_TASKS_ENABLED` is `False` and `--force` is not provided, the command will exit with an error message suggesting to use `--force`.
- When `--force` is used, the command will log that it's bypassing the scheduled tasks check.

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

#### `cache`

Manage cached statistics data.

```bash
invenio community-stats cache [SUBCOMMAND] [OPTIONS]
```

**Subcommands:**

- `clear-all`: Clear all cached statistics data
- `clear-item`: Clear a specific cached statistics item
- `info`: Show cache information including size and item count
- `list`: List all cached statistics keys
- `test`: Test cache functionality

**Examples:**
```bash
# Clear all cached data
invenio community-stats cache clear-all

# Clear specific cache entry
invenio community-stats cache clear-item global record_snapshots

# Show cache information
invenio community-stats cache info

# List all cache keys
invenio community-stats cache list

# Test cache functionality
invenio community-stats cache test
```

**Configuration Requirements:**

The `cache` commands require the `COMMUNITY_STATS_ENABLED` configuration to be set to `True`. If disabled, the commands will exit with an error message.

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
- `--delete-old-indices`: Delete old indices after migration (default is to keep them).

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
- `--delete-old-indices`: Delete old indices after migration.
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
