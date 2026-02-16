# Setup and Migration

```{warning}
This package depends on pull requests that were merged into invenio-requests and invenio-rdm-records for InvenioRDM version 13. For version 12 instances, a bash script is provided to patch the required files in your local site-packages directory. Simply run `bash apply_patches.sh [environment_path]` from the root of the `invenio-stats-dashboard` package directory, where `[environment_path]` is the path to your python environment folder (the parent folder of `site-packages`). You can view the contents of the patched files in the `invenio_stats_dashboard/patches` directory.
```

## Setup overview

1. Install the python package.
2. Set initial config variables for the setup period (and restart the InvenioRDM instance).
3. Execute manual CLI commands
   a. Initialize the community custom field (via CLI command).
   b. Index community addition events for all existing records (via CLI command)
   c. Migrate and enrich the existing view and download events (via CLI command)
4. OPTIONAL: Manually run the catch-up aggregations (via CLI command)
5. Configure package settings and page templates as desired.
6. Set config variables to begin normal operation
7. Restart the InvenioRDM instance

## 1. Install the python package.

In your InvenioRDM instance directory run one of the following commands, depending on whether you are using `pipenv` or `uv` for environment management:

```shell
pipenv install invenio-stats-dashboard
```

```shell
uv add invenio-stats-dashboard
```

## 2. Initial configuration for setup

The first step is to ensure that the following config variables are set to their default settings as follows:

- `COMMUNITY_STATS_ENABLED = True`
- `COMMUNITY_STATS_SCHEDULED_AGG_TASKS_ENABLED = False`
- `COMMUNITY_STATS_SCHEDULED_CACHE_TASKS_ENABLED = False`
- `STATS_DASHBOARD_MENU_ENABLED = False`
- `STATS_DASHBOARD_ENABLED_GLOBAL = False`
- `STATS_DASHBOARD_ENABLED_COMMUNITY = False`

These settings allow the initial setup to proceed without yet displaying the dashboards or their menu links.

```{note}
Since the included search index tamplates all use the new-style index templates, you must ensure that STATS_REGISTER_INDEX_TEMPLATES is set to True. This is currently *not* the default for InvenioRDM instances, but it should not interfere with any other packages. The only other index templates currently registered are those from the `invenio-stats` module, which are overridden by the `invenio-stats-dashboard` extension.
```

## 3. Manual CLI steps

Three setup tasks must be performed manually via CLI commands. The first must be performed for any installation. The second and third are necessary **only for existing InvenioRDM instances** that already have records and view/download statistics:

a. initialize the stats-dashboard custom fields
b. index community addition events for all existing records
c. migrate the existing view and download events to the new index templates and enrich them with community and record metadata

These tasks must be performed manually via CLI commands detailed below. They require zero downtime and can be performed in the background on a running InvenioRDM instance.

### Initialize community custom fields

The extension adds two custom fields to the community metadata schema:

- `stats:dashboard_layout` allows communities to store dashboard layout configurations.
- `stats:dashboard_enabled` allows communities to enable or disable their dashboards on an individual basis (if the package is configured to allow it).

These fields must be initialized in the search index before they can be used:

```bash
# Initialize the custom field
invenio custom-fields communities init stats:dashboard_layout

# Verify the field exists
invenio custom-fields communities exists stats:dashboard_layout
```

The toggle for enabling and disabling a community's dashboard is automatically integrated into community creation and editing forms _if_ you have configured community dashboards to be opt-in (
`STATS_DASHBOARD_COMMUNITY_OPT_IN = True`). ???

### Initial indexing of community addition events

The `invenio-stats-dashboard` requires a dedicated search index to store data about when each record was added to or removed from a community. If an InvenioRDM instance already has records included, these community add/remove events must be created retroactively for existing records by running this CLI command inside the instance's running ui app container:

```shell
invenio community-stats community-events generate
```

For details, see the section on [CLI community-event commands](./cli.html#community-events-generate).

This process is usually relatively fast, but can still take several minutes on a large instance. So the `community-evenst status` CLI command is available to check the progress of the operation and ensure that it has completed successfully.

```{warning}
Note that this command must be run even if the existing records are not yet placed in communities. The global instance statistics aggregations also rely on "add" events from this index.
```

```{note}
This command by default runs as a live process in the container (usually the ui container) in which it is executed. The `generate-background` command runs the migration as a background process, detached from the user's shell session, with output recorded in a log file.
```

### Initial migration of existing view/download events

Before any statistics can be aggregated, the `invenio-stats-dashboard` package must also migrate all existing view and download events in the search index to new indices, using expanded field mappings. These schemas provided by the `invenio-stats` package (and customized by the `invenio-app-rdm` package ???) are expanded with additional fields for

- record community inclusion (at the time of the event), and
- record metadata to be made available as subcount breakdowns in statistics (as configured).

This index migration and enrichment is performed by running the following command inside the instance's running ui app container:

```shell
invenio community-stats usage-events migrate
```

For details, see the section on [CLI usage event commands](./cli.html#usage-events-migrate).

This reindexing process can take a signficant amount of time for large instances. So it is again accompanied by CLI commands to check the status of the operation, clear the migration bookmarks, and clean up old duplicate indices if necessary.

```{note}
This command by default runs as a live process in the container (usually the ui container) in which it is executed. The `migrate-background` command runs the migration as a background process, detached from the user's shell session, with output recorded in a log file.
```

#### The index migration process

The migration and enrichment process are handled by the `EventReindexingService`. If there are no existing view or download events, the service's `reindex_events` method will simply register the new index templates and usage events can be indexed normally. If there are existing view or download events, the `reindex_events` method will perform the following steps:

1. Verify that the new index templates are registered with the OpenSearch domain and register them if they are not.
2. Create new monthly view and download indices for each legacy monthly index, adding the suffix `.v2.0.0` to the index names.
3. Copy the events from the legacy monthly indices to the new monthly indices, adding the community and record metadata fields to the events.
4. Confirm that the events have all been copied over accurately.
5. Update the read aliases (`events-stats-record-view` and `events-stats-file-download`) to point to the new monthly indices.
6. Delete the legacy monthly indices for months prior to the current month (if desired).
7. Switch new event writes from the old current-month index to the new current-month index by:
   - creating a temporary backup copy of the old current-month index (named `backup-{old_index}`)
   - quickly deleting the old current-month index and creating a write alias to the new current-month index
   - recovering any events that arrived since the original enriched index creation from the backup index to the new enriched index
   - validating the enriched index integrity before (optionally) deleting the temporary backup index

#### Preventing overload of OpenSearch or memory

The reindexing service is configured to run in batches, to avoid overwhelming the OpenSearch domain with too many concurrent requests. The batch size and maximum number of batches can be configured via the `STATS_DASHBOARD_REINDEXING_BATCH_SIZE` and `STATS_DASHBOARD_REINDEXING_MAX_BATCHES` configuration variables.

```{important}
OpenSearch has a hard limit of 10,000 documents for search results. This means `STATS_DASHBOARD_REINDEXING_BATCH_SIZE` cannot exceed 10,000, and any attempt to count documents after a search_after position will be limited to 10,000 results maximum.
```

The service will check the memory usage of the OpenSearch domain on starting each batch and exit if the memory usage exceeds the `STATS_DASHBOARD_REINDEXING_MAX_MEMORY_PERCENT` configuration variable. The service will also check the health of the OpenSearch domain on starting each batch and exit if the health is not good.

#### Handling failures

If the reindexing of a particular month fails, the service will leave the original index in place and continue with the next month. It will log a warning and report the failure in the service's output report. The service will reset that index's bookmark to the beginning and try to reindex the month again on the next run. Alternately, you may manually retry the migration of a particular month by running the `invenio community-stats usage-events migrate` CLI command with its `--months` option set to the month in question and its `--event-types` option set to the event type in question.

For more information about failed migrations and how to retry them, you can use the `invenio community-stats usage-events status` CLI command.

#### Handling progress across migration runs

If the service hits the maximum number of batches before a monthly index is completely migrated, it will log a warning and report the progress in the service's output report. The service will set a bookmark to record the last processed event id, so that the next reindexing service run can continue from that point. These bookmarks are stored in the `stats-community-events-reindexing` index and are set independently for each monthly index.

If you wish to clear the bookmarks for a particular month, you can use the `invenio community-stats usage-events clear-bookmarks` CLI command with its `--months` option set to the month in question, and its `--event-types` option set to the event type in question, and the `--fresh-start` flag.

To clear the bookmarks for all months, you can use the `invenio community-stats usage-events clear-bookmarks` CLI command.

## 4. Initial aggregation of historical data

???configure subcounts first

The extension will perform the initial aggregation of historical statistics automatically as part of the scheduled aggregation tasks. This can be a long process, especially for large instances, so a utility CLI command to perform the catch-up aggregation manually. In the ui app container, one may run

```shell
invenio community-stats aggregate
```

This gives the instance maintainer more control over the process and can still run in the background while the instance is in use. For details, see the [CLI commands](#cli-commands) section below.

```{note}
**Monitoring Progress**: You can monitor the progress of the catch-up aggregation using the `invenio community-stats status` command. This command shows the current state of all aggregation indices, including bookmark dates, document counts, and visual completeness bars. For more details, see the [CLI commands](#cli-commands) section below.
```

## 5. Configuration

## 6. Enable the tasks and dashboards

- `COMMUNITY_STATS_ENABLED` = `True`
- `COMMUNITY_STATS_SCHEDULED_AGG_TASKS_ENABLED` = `True`
- `COMMUNITY_STATS_SCHEDULED_CACHE_TASKS_ENABLED` = `True`
- `STATS_DASHBOARD_MENU_ENABLED` = `True` (if desired)

## Automated setup

After these tasks are completed, the extension will be ready to perform the remaining setup actions automatically. The catch-up aggregation of historical statistics will then be performed automatically as part of the scheduled aggregation tasks. Since this can, however, be a long process, especially for large instances, a utility CLI command to perform the catch-up aggregation manually is also provided.

## Search index template registration

If the `invenio-stats-dashboard` extension is installed on a new InvenioRDM instance, the `invenio-stats` module will automatically register the extension's search index templates with the OpenSearch domain. But `invenio-stats` does not automatically do this registration for existing InvenioRDM instances, i.e. if the main OpenSearch index setup has already been performed. So the `invenio-stats-dashboard` extension will check at application startup to ensure that the extension's search index templates are registered with the OpenSearch domain. If they are not, it registers them with the `invenio-search` module and puts them to OpenSearch. The aggregation indices will then be created automatically when the first records are indexed.

Registration of the expanded index templates for view and download events happens automatically as part of the usage event migration process.
