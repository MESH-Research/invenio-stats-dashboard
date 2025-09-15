## Setup and Migration

```{warning}
This package is waiting for two pull requests to be merged in invenio-requests and invenio-rdm-records (see [Known Issues](./known_issues.md)). In the meantime, a provided bash script is provided to patch the required files in your local site-packages directory. Simply run `bash apply_patches.sh [environment_path]` from the root of the `invenio-stats-dashboard` package directory, where `[environment_path]` is the path to your python environment folder (the parent folder of `site-packages`). You can view the contents of the patched files in the `invenio_stats_dashboard/patches` directory.
```

In future the plan is that setup of `invenio-stats-dashboard` will involve simply installing the python package and restarting the InvenioRDM instance. For now, however, two initial setup tasks are required **only for existing InvenioRDM instances** that already have records and view/download statistics:

- index community addition events for all existing records
- migrate the existing view and download events to the new index templates and enrich them with community and record metadata

These tasks can be performed manually via CLI commands detailed below. They require zero downtime and can be performed in the background on a running InvenioRDM instance.

After these tasks are completed, the extension will be ready to use as normal. The catch-up aggregation of historical statistics will then be performed automatically as part of the scheduled aggregation tasks. Since this can, however, be a long process, especially for large instances, a utility CLI command to perform the catch-up aggregation manually is also provided.

So the full setup process is currently:

1. Install the python package
2. Set config variables for the setup period:
- `COMMUNITY_STATS_ENABLED` = `True`
- `COMMUNITY_STATS_SCHEDULED_TASKS_ENABLED` = `False`
- `STATS_DASHBOARD_MENU_ENABLED` = `False`
3. Restart the InvenioRDM instance
4. Index community addition events for all existing records (via CLI command)
5. Migrate and enrich the existing view and download events (via CLI command)
6. OPTIONAL: Manually run the catch-up aggregation (via CLI command)
7. Set config variables for normal operation:
- `COMMUNITY_STATS_ENABLED` = `True`
- `COMMUNITY_STATS_SCHEDULED_TASKS_ENABLED` = `True`
- `STATS_DASHBOARD_MENU_ENABLED` = `True` (if desired)
8. Set up other configuration and community page templates as desired
9. Restart the InvenioRDM instance

### Search index template registration

If the `invenio-stats-dashboard` extension is installed on a new InvenioRDM instance, the `invenio-stats` module will automatically register the extension's search index templates with the OpenSearch domain. But `invenio-stats` does not automatically do this registration for existing InvenioRDM instances, i.e. if the main OpenSearch index setup has already been performed. So the `invenio-stats-dashboard` extension will check at application startup to ensure that the extension's search index templates are registered with the OpenSearch domain. If they are not, it registers them with the `invenio-search` module and puts them to OpenSearch. The aggregation indices will then be created automatically when the first records are indexed.

Registration of the expanded index templates for view and download events happens automatically as part of the usage event migration process.

```{note}
Since the included search index tamplates all use the new-style index templates, you must ensure that STATS_REGISTER_INDEX_TEMPLATES is set to True. This is currently *not* the default for InvenioRDM instances, but it should not interfere with any other packages. The only other index templates currently registered are those from the `invenio-stats` module, which are overridden by the `invenio-stats-dashboard` extension.
```

### Initial indexing of community addition events

The `invenio-stats-dashboard` requires a dedicated search index to store data about when each record was added to or removed from a community. The `CommunityStatsService.generate_record_community_events` method will create community add/remove events for all records in the instance that do not already have events. This method can be run manually via the `invenio community-stats generate-community-events` CLI command. For details, see the [CLI commands](#cli-commands) section below.

### Initial migration of existing view/download events

The `invenio-stats-dashboard` extension also depends on an expanded field schema for the view and download events, adding to the core `invenio-stats` schema additional fields for community and for any configured record metadata that are to be made available as subcount breakdowns in statistics.

A dedicated CLI command is provided to (a) register the new index templates and (b) migrate and enrich any existing view and download events. For details, see the [CLI commands](#cli-commands) section below.

The migration and enrichment process are handled by the `EventReindexingService`. If there are no existing view or download events, the service's `reindex_events` method will simply register the new index templates and usage events can be indexed normally. If there are existing view or download events, the `reindex_events` method will perform the following steps:

1. Verify that the new index templates are registered with the OpenSearch domain and register them if they are not.
2. Create new monthly view and download indices for each legacy monthly index, adding the suffix `.v2.0.0` to the index names.
3. Copy the events from the legacy monthly indices to the new monthly indices, adding the community and record metadata fields to the events.
4. Confirm that the events have all been copied over accurately.
5. Update the read aliases (`events-stats-record-view` and `events-stats-file-download`) to point to the new monthly indices.
6. Delete the legacy monthly indices for months prior to the current month (if desired).
7. Switch new event writes from the old current-month index to the new current-month index by:
    - creating a temporary backup copy of the old current-month index
    - quickly deleting the old current-month index and creating a write alias to the new current-month index
    - recovering any events that arrived since the original enriched index creation from the backup index to the new enriched index
    - validating the enriched index integrity before (optionally) deleting the temporary backup index

```{warning}
Currently, the `EventReindexingService.reindex_events` method must be run manually to perform the migration. It can be run via the `invenio community-stats migrate-events` CLI command and its associated helper commands. In future, the migration will be integrated automatically as part of the scheduled aggregation tasks, to be completed in the background over a series of scheduled runs before the first aggregations are actually performed.
```

TODO: set up check and automatic migration in aggregator tasks

#### Preventing overload of OpenSearch or memory

The reindexing service is configured to run in batches, to avoid overwhelming the OpenSearch domain with too many concurrent requests. The batch size and maximum number of batches can be configured via the `STATS_DASHBOARD_REINDEXING_BATCH_SIZE` and `STATS_DASHBOARD_REINDEXING_MAX_BATCHES` configuration variables.

```{important}
OpenSearch has a hard limit of 10,000 documents for search results. This means `STATS_DASHBOARD_REINDEXING_BATCH_SIZE` cannot exceed 10,000, and any attempt to count documents after a search_after position will be limited to 10,000 results maximum.
```

The service will also check the memory usage of the OpenSearch domain on starting each batch and exit if the memory usage exceeds the `STATS_DASHBOARD_REINDEXING_MAX_MEMORY_PERCENT` configuration variable. The service will also check the health of the OpenSearch domain on starting each batch and exit if the health is not good.

#### Handling failures

If the reindexing of a particular month fails, the service will leave the original index in place and continue with the next month. It will log a warning and report the failure in the service's output report. The service will reset that index's bookmark to the beginning and try to reindex the month again on the next run. Alternately, you may manually retry the migration of a particular month by running the `invenio community-stats usage-events migrate` CLI command with its `--months` option set to the month in question and its `--event-types` option set to the event type in question.

For more information about failed migrations and how to retry them, you can use the `invenio community-stats usage-events status` CLI command.

#### Handling progress across migration runs

If the service hits the maximum number of batches before a monthly index is completely migrated, it will log a warning and report the progress in the service's output report. The service will set a bookmark to record the last processed event id, so that the next reindexing service run can continue from that point. These bookmarks are stored in the `stats-community-events-reindexing` index and are set independently for each monthly index.

If you wish to clear the bookmarks for a particular month, you can use the `invenio community-stats usage-events clear-bookmarks` CLI command with its `--months` option set to the month in question, and its `--event-types` option set to the event type in question, and the `--fresh-start` flag.

To clear the bookmarks for all months, you can use the `invenio community-stats usage-events clear-bookmarks` CLI command.

### Initial aggregation of historical data

The extension will perform the initial aggregation of historical statistics automatically as part of the scheduled aggregation tasks. This can be a long process, especially for large instances, so a utility CLI command to perform the catch-up aggregation manually is also provided: `invenio community-stats aggregate`. This gives the instance maintainer more control over the process and can still run in the background while the instance is in use. For details, see the [CLI commands](#cli-commands) section below.

```{note}
**Monitoring Progress**: You can monitor the progress of the catch-up aggregation using the `invenio community-stats status` command. This command shows the current state of all aggregation indices, including bookmark dates, document counts, and visual completeness bars. For more details, see the [CLI commands](#cli-commands) section below.
```

