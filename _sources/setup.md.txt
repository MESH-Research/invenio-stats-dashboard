# Setup and Migration

Much of the setup of invenio-stats-dashboard is automated. There are, however, a few manual steps required, and some optional configuration to be done. This guide will walk you through these steps.

```{warning}
This package depends on pull requests that were merged into invenio-requests and invenio-rdm-records for InvenioRDM version 13 (see (known issues)[./known_issues.html#dependencies]). For version 12 instances, a bash script is provided to patch the required files in your local site-packages directory. Simply run `bash apply_patches.sh [environment_path]` from the root of the `invenio-stats-dashboard` package directory, where `[environment_path]` is the path to your python environment folder (the parent folder of `site-packages`). You can view the contents of the patched files in the `invenio_stats_dashboard/patches` directory.
```

## Setup overview

1. Install the python package.
2. Set initial config variables for the setup period (and restart the InvenioRDM instance).
3. Execute manual CLI commands
   a. Initialize the community custom field (via CLI command).
   b. Index community addition events for all existing records (via CLI command)
   c. Migrate and enrich the existing view and download events (via CLI command)
4. OPTIONAL: Manually run the catch-up aggregations (via CLI command)
5. OPTIONAL: Manually run the initial response pre-caching (via CLI command)
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

After installing the package, the next step is to customize your configuration by overriding default values (from invenio_stats_dashboard.config.config) in your invenio.cfg file. Full configuration documentation are available in the (configuration)[./configuration.md] section. Some of these settings do not affect extension setup, but a few values must be set at the beginning.

First, you must ensure that the following control variables are set to their default values. These settings allow the initial setup to proceed without yet displaying the dashboards or their menu links:

- `COMMUNITY_STATS_ENABLED = True`
- `COMMUNITY_STATS_SCHEDULED_AGG_TASKS_ENABLED = False`
- `COMMUNITY_STATS_SCHEDULED_CACHE_TASKS_ENABLED = False`
- `STATS_DASHBOARD_MENU_ENABLED = False`
- `STATS_DASHBOARD_ENABLED_GLOBAL = False`
- `STATS_DASHBOARD_ENABLED_COMMUNITY = False`

Any changes to the default configuration for metadata subcount breakdowns. In particular, ensure that you have made your desired changes to the following variables:

| Variable                     | Purpose                                                                                         |
| ---------------------------- | ----------------------------------------------------------------------------------------------- |
| COMMUNITY_STATS_SUBCOUNTS    | Main configuration for which metadata fields to use in aggregated subcount statistics.          |
| STATS_DASHBOARD_UI_SUBCOUNTS | Which metadata subcounts should be available to the dashboard UI.                               |
| STATS_DASHBOARD_LAYOUT       | Pages and page layout for the dashboard UI, including config settings for each React component. |

The UI layout configuration may seem less important to configure at this point, and it can be changed later on. Note, though, that the contents of the pre-compiled JSON responses cached for each community depend in part on which subcounts and widgets are included in your layout.

```{danger}
Changes to COMMUNITY_STATS_SUBCOUNTS currently **cannot** be made after the initial migration of stats indices and catchup aggregation operations. The index migration *may* be performed again from scratch if (a) you have not deleted the original stats indices, and (b) you have not recorded additional view and download events. After this, you will still need to re-aggregate all existing statistics from scratch. A post-setup re-migration and re-aggregation path is planned for the future.
```

Some other variables control the behaviour of setup migration and aggregation behaviour. These have sane defaults, but you may want to customize them for your system resources:

| Variable                                      | Purpose                                                                                                                                                                                                                                                                       |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| COMMUNITY_STATS_CATCHUP_INTERVAL              | How many days of historical data to aggregate in a single aggregator run. If un-aggregated past data exists for more days than this, the aggregator will place a bookmark at the last aggregated date and wait to complete the catch-up operation on the next aggregator run. |
| STATS_DASHBOARD_REINDEXING_MAX_BATCHES        | Maximum number of ???                                                                                                                                                                                                                                                         |
| STATS_DASHBOARD_REINDEXING_BATCH_SIZE         | Batch size to be used in paged search index requests while migrating existing view and download stats to the enriched indices.                                                                                                                                                |
| STATS_DASHBOARD_REINDEXING_MAX_MEMORY_PERCENT | Memory use threshold to be used to throttle stats index migration operations                                                                                                                                                                                                  |

```{warning}
Since the included search index tamplates all use the new-style index templates, you **must** also ensure that STATS_REGISTER_INDEX_TEMPLATES is set to True. This is currently *not* the default for InvenioRDM instances, but it should not interfere with any other packages. The only other index templates currently registered are those from the `invenio-stats` module, which are overridden by the `invenio-stats-dashboard` extension.
```

## 3. Manual CLI steps

Once the basic config variables are set to their setup values, three tasks must be performed manually via CLI commands, detailed below:

a. initialize the stats-dashboard custom fields
b. index community addition events for all existing records
c. migrate the existing view and download events to the new index templates and enrich them with community and record metadata

The first of these tasks must be performed for any installation. The second and third are necessary **only for existing InvenioRDM instances** that already have records and view/download statistics.

These tasks require zero downtime and can be performed in the background on a running InvenioRDM instance.

### Initialize community custom fields

First, two custom fields must be initialized. The extension adds new fields to the community metadata schema:

- `stats:dashboard_layout` allows communities to store dashboard layout configurations to override instance-wide defaults.
- `stats:dashboard_enabled` allows communities to enable or disable their dashboards on an individual basis (if the package is configured to allow it).

To initialize these fields, execute the following command inside your instance's ui container:

```bash
# Initialize the custom field
invenio custom-fields communities init stats:dashboard_layout

# Verify the field exists
invenio custom-fields communities exists stats:dashboard_layout
```

The toggle for enabling and disabling a community's dashboard is automatically integrated into community creation and editing forms _if_ you have configured community dashboards to be opt-in (`STATS_DASHBOARD_COMMUNITY_OPT_IN = True`).

### Initial indexing of community addition events

The next step is to run a CLI command that indexes "add" events retroactively for existing records. When the `invenio-stats-dashboard` extension is loaded, it registers a template for a dedicated search index to store data about when each record was added to or removed from a community. From that point on, new add/remove events are indexed automatically by service components. But if an InvenioRDM instance already includes records, past add/remove events must be created retroactively for existing records. Inside the ui app container, run this CLI command:

```shell
invenio community-stats community-events generate
```

For details on this command's use, see the section on [CLI community-event commands](./cli.html#community-events-generate).

This back-filling of add/remove events is usually relatively fast, but can still take several minutes on a large instance. So the `community-evenst status` CLI command is available ([detailed here](./cli.html#community-events-status)) to check the progress of the operation and ensure that it has completed successfully.

```{warning}
Note that this command must be run even if the existing records are not yet placed in communities. The statistics aggregations for the instance as a whole also rely on "add" events to the "global" corpus recorded in this index.
```

```{note}
This command by default runs as a live process in the container (usually the ui container) in which it is executed. The `generate-background` command runs the migration as a background process, detached from the user's shell session, with output recorded in a log file. It does *not*, however, run the operation as a celery task in the `worker` app. It is still run by the ui app.
```

### Initial migration of existing view/download events

```{note}
This migration step must be run **after** the previous step (indexing of initial community events) has finished.
```

Before any statistics can be aggregated, the `invenio-stats-dashboard` package must also migrate all existing view and download events in the search index to new indices, using expanded field mappings. These schemas provided by the `invenio-stats` package (and customized by the `invenio-rdm-records` package) are expanded with additional fields for:

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

## 4. Initial aggregation of historical data (optional)

```{note}
This migration step must be run **after** the previous steps (indexing of initial community events) have finished.
```

The extension will perform the initial aggregation of historical statistics automatically as part of the scheduled aggregation tasks. This can be a long process, especially for large instances, so a utility CLI command to perform the catch-up aggregation manually. In the ui app container, one may run

```shell
invenio community-stats aggregate
```

This gives the instance maintainer more control over the process and can still run in the background while the instance is in use. Optional command-line parameters allow specifying a time-frame, a specific aggregator, or specific communities. For details, see the [CLI commands](./cli.html) section below.

```{note}
**Monitoring Progress**: You can monitor the progress of the catch-up aggregation using the `invenio community-stats status` command. This command shows the current state of all aggregation indices, including bookmark dates, document counts, and visual completeness bars. For more details, see the [CLI commands](#cli-commands) section below.
```

## 5. Initial response caching (optional)

```{note}
This step must be run **after** aggregation (section 4) has produced data. Response caching pre-generates the JSON responses used by the dashboard to allow short load times.
```

The extension will perform initial response caching automatically as part of the scheduled cache tasks. This can be a long process, especially for large instances or many communities, so a CLI command is provided to run the initial cache generation manually. In the ui app container, you may run:

```shell
invenio community-stats cache generate --all-years
```

This pre-generates cached responses for all data series categories (record_delta, usage_delta, etc.) for all communities and the global instance, for every year since community creation. Optional command-line parameters allow limiting by community (`--community-id`, `--community-slug`), by year (`--year`, `--years`), or running asynchronously via Celery (`--async`). For details, see the [CLI cache commands](./cli.html#cache-generate) section.

```{note}
You can use `invenio community-stats cache generate --dry-run` to see which communities and years would be processed without writing cache entries. The `cache info` and `cache list` commands can also provide progress information while the caching operation is running.
```

## 6. Enable the tasks and dashboards

Once you are ready to begin the scheduled background tasks for normal operation and expose the dashboard menu items (if desired), you can update these config variables.

- `COMMUNITY_STATS_ENABLED` = `True`
- `COMMUNITY_STATS_SCHEDULED_AGG_TASKS_ENABLED` = `True`
- `COMMUNITY_STATS_SCHEDULED_CACHE_TASKS_ENABLED` = `True`
- `STATS_DASHBOARD_MENU_ENABLED` = `True` (if desired)
- `STATS_DASHBOARD_COMMUNITY_MENU_ENABLED` = `True` (if desired)

```{note}
Until the instance/community's initial aggregations and response caching are finished, an "in progress" message will be shown on the dashboard. In large instances this state can continue for several hours.
```

## 7. Restart the InvenioRDM instance

The final config changes will not take effect, and the scheduled tasks will not begin to run, until the InvenioRDM instance has been restarted.

## Automated setup completion

After these tasks are completed, the extension will be ready to perform the remaining setup actions automatically. The catch-up aggregation of historical statistics will then be performed automatically as part of the scheduled aggregation tasks; since this can be a long process, especially for large instances, a CLI command is also provided to run the catch-up aggregation manually (see section 4). Likewise, initial response caching will be performed by the scheduled cache tasks, but you may run `invenio community-stats cache generate --all-years` manually for faster initial dashboard readiness (see section 5).
