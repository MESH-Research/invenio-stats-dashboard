# Invenio Stats Dashboard

## Current Known Issues

- the `-background` versions of CLI commands are working but not creating the correct PID files, so the `status` and `cancel` sub-commands are not working correctly. We need to manage the background processes manually for now. But the process logs are still being captured correctly in the /tmp folder.
- the record delta aggregator is not working properly when using the publication date as the basis for the aggregation. It is missing records published before the first record was created. This also throws off the record snapshot aggregator when using the publication date as the basis for the aggregation.

## Overview

Invenio module that provides global and community statistics overviews for an InvenioRDM instance. This provides a responsive, configurable dashboard for viewing and analyzing statistics for the instance and its communities. It exposes time-series data for each community and the instance as a whole, including:
- running cumulative totals and delta changes for a given date range
- covering
  - number of records and files
  - file data volume
  - number of unique uploaders
  - number of unique views and downloads
- subcounts for each metric broken down by
  - resource type
  - access status (open, restricted, etc.)
  - language
  - creator/contributor affiliation
  - funding organization
  - subject heading
  - publisher name
  - periodical title
  - file type
- subcounts for view/download metrics broken down by
  - referrer domain
  - visitor country

The extension provides:
- data-layer storage of pre-aggregated statistics (daily cumulative snapshots and deltas) for each community and for the instance as a whole
- service-layer aggregation of the community and global statistics on a regular schedule, along with service components to record community add/remove events
- API access to the aggregated daily statistics via the `/api/stats` endpoint
- Jinja2 templates and macros to display React-based global and community statistics dashboards
- menu configuration to add the global statistics dashboard to site-wide navigation

Most initial setup of the statistics infrastructure is handled automatically when the module is installed. In existing InvenioRDM instances, this includes not only setup of the necessary search indices, but also:
- migration of historical indexed usage events to the expanded mappings with added community and record metadata
- initial indexing of the community membership events for existing records (when a record is added to or removed from a community)
- progressive aggregation of historical statistics
This initial setup is handled by the background tasks that run on a regular schedule to aggregate the statistics. If the instance has a large number of records, this may up to a day or more to complete.

The module also provides a set of utility classes and functions, along with cli commands, to facilitate setup and maintenance of the statistics infrastructure.

## TODOs

- [x] add config flag to switch UI between test data and production data
- [ ] testing
  - [ ] move all tests into this package
  - [ ] fix failing tests
  - [ ] expand test coverage
- [ ] aggregation
  - [ ] refactor CommunityUsageSnapshotAggregator for the enriched event document structure
  - [ ] ensure CommunityUsageDeltaAggregator can handle large volumes of records gracefully (paginate the query, batch the aggregations)
  - [ ] get tests for queries working with refactored code
  - [ ] get tests for aggregator classes working
  - [ ] set up a check in aggregator classes to ensure that view/download event migration has been completed before running the aggregator tasks
  - [ ] add opensearch health and memory usage checks to the aggregator classes (as in the reindexing service) and quit out gracefully if necessary
- [ ] UI components
  - [ ] add proper loading states to the dashboard components
  - [ ] add an updated timestamp to the dashboard views
  - [ ] add custom date range picker to the dashboard views
  - [ ] fix state problems with chart views
  - [ ] add ReactOverridable support for each of the React components
  - [ ] add mechanism for adding custom React components to the dashboard views (entry point providing file paths and component labels, to be imported in components_map.js?)
  - [ ] evaluate whether additional default components are needed
- [ ] client-side data handling
  - [ ] add client-side caching of the stats data to display while new data is loading
- [ ] UI theming
  - [ ] move default CSS into this package and harmonize it with InvenioRDM defaults
  - [ ] finish theming of the global dashboard view
  - [ ] improve mobile responsiveness of the dashboard views
- [ ] API requests
  - [ ] implement security policy for API queries
- [ ] reporting
  - [ ] implement report generation (via API request? via email? generated client-side?)
  - [ ] enable report download from dashboard widget
- [ ] improve documentation

## Architecture

### Building on the `invenio-stats` module

Wherever possible, this module uses the infrastructure provided by the `invenio-stats` module to store and aggregate the statistics data. The `invenio-stats` module handles:
- registration of new and expanded search index templates (for a new instance only)
- registration of statistics aggregators via the `STATS_AGGREGATIONS` configuration variable
  - with completely new aggregator classes that work independently of any event type
- registration of usage (view and download) events via the `STATS_EVENTS` configuration variable
  - with new event search index templates to include community and record metadata fields in the usage events
  - with new event builder classes to include community and record metadata fields in the usage events
- registration of community and global statistics API responses via the `STATS_QUERIES` configuration variable
  - using new query classes to build the community and global statistics API responses
- management of the stats API endpoint where the configured queries are exposed

### Data layer

This package provides the following data layer components:
- search indices to store pre-aggregated statistics for communities and the instance as a whole
- search index to store events for community membership changes
- expanded usage event (view and download) search index mappings to include community and record metadata fields
- utility service to migrate existing usage events to the expanded mappings

#### Community membership events

Several aggregations provided by `invenio-stats-dashboard` depend on knowing exactly which records are in a community at a given time. These events are stored in the `stats-community-events` index. Each addition or removal of a record to/from a community is recorded as an event, along with the record's creation and publication dates, and deletion status/date. This allows for a more efficient aggregation of the record-based statistics. The inclusion of the creation and publication dates allows for easy aggregation of stats based on when a community's records were created or published, as well as when they were added to the community.

Events with a `community_id` of "global" are also used to mark the addition and removal of records to/from the global repository instance. This may seem redundant, but it allows aggregator classes to use the same logic in aggregating community stats and stats for the global instance. These global events are are also especially useful when aggregating statistics based on the record's publication date (which presents problems for a simple range query from the record index) as well as preserving the correct historical record counts after a record is deleted.

The `stats-community-events` index is configured by the index template at `search_indices/stats_community_events/os-v2/stats-community-events-v1.0.0.json`. Each event is shaped like this:

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

#### Enriched record usage events

In order to efficiently aggregate usage statistics by community, and in order to provide subcounts based on record metadata fields, the `invenio-stats-dashboard` module enriches the standard `invenio-stats` usage events with community and record metadata fields. This is done by overriding the default `invenio-stats` index templates for the `stats-events-record-view` and `stats-events-file-download` indices. The new index templates are identical to the default templates, but add the following fields to the index mappings:
- ????

The extension also overrides the default `invenio-stats` event builder classes for view and download events, adding logic to record community and select metadata information to each event document.

These two changes are sufficient to provide the enriched data for all future usage events. If the InvenioRDM instance has existing legacy view and download events, the extension provides a utility service to migrate the existing indices to the new index template and add the missing community and record metadata fields to the existing events. For more details, see [Setup and Migration](#setup-and-migration).

#### Aggregated statistics

The `invenio-stats-dashboard` module provides pre-aggregated daily statistics for each community and the instance as a whole. There are four kinds of pre-aggregations:

1. **Record deltas**: Daily changes in the number of records and files in the community/instance. These record the changes (additions/and removals) to the contents of a community/instance during a given day, based on the indexed record metadata and community membership events.
2. **Record snapshots**: Daily cumulative total counts of records and files in the community/instance as of a given date. These are based on the indexed record metadata and community membership events. They are calculated fresh for each day, rather than being aggregated from the record deltas. This is because some subcounts in the aggregated record deltas (such as by subject heading) include only the day's top values (e.g., the top 20 subject headings for the day). An accurate snapshot count requires that we include all records, not just the top values.
3. **Usage deltas**: Daily counts for the number of views and downloads for records and files in the community/instance. These are based on the indexed usage events.
4. **Usage snapshots**: Daily cumulative total counts of views and downloads for records and files in the community/instance as of a given date.

Each aggregation document includes a breakdown of subcounts based on a variety of metadata fields.

Each aggregation is stored in a separate set of indices, one index per year, with a common alias to facilitate easy searching across all years. Each index includes both over-arching numbers for the community/instance and broken-down subcounts based on record metadata fields such as resource type, access right, language, affiliation, funder, subject, publisher, and periodical.

With record deltas and record snapshots, there is an additional question about what to consider the "start" of a record's
lifetime for the sake of the aggregation. In some cases it may be most useful to consider when records are actually added to a community/instance. But we
may also want to display a time series of a community's contents based on when its records were published (the record's `metadata.publication_date`) or when they were created in the InvenioRDM instance (the record's `created` date).

So we aggregate and store three different versions of the record deltas and record snapshots aggregations for each day, based these three different "start" dates. Together with the usage delta and snapshot aggregations, this gives us a total of 8 different stored aggregation documents for each day for each community. These are stored in 8 different sets of search indices, with one index of each type per year. The indices are named like this:
- `stats-community-records-delta-created-YYYY`
- `stats-community-records-delta-published-YYYY`
- `stats-community-records-delta-added-YYYY`
- `stats-community-records-snapshot-created-YYYY`
- `stats-community-records-snapshot-published-YYYY`
- `stats-community-records-snapshot-added-YYYY`
- `stats-community-usage-delta-YYYY`
- `stats-community-usage-snapshot-YYYY`

```{note}
The labels included for each item in a subcount are the English values available in the record metadata. It
is most efficient to include these readable labels in the aggregated documents, rather than looking up the
labels from the record metadata after the aggregation is complete. It was deemed impractical, though, to
include these labels for every available language. Instead, the labels can be translated on the client side
as needed.
```

#### Daily record deltas

The record delta aggregations track daily changes in the number of records and files in the community/instance. These aggregations are based on the metadata records in the `rdm-records-records` index and the community membership events in the `stats-community-events` index.

Each daily record delta document includes:
- `timestamp` (date): When the aggregation was created
- `community_id` (string): The community identifier (or "global" for the instance as a whole)
- `files` (object): the number of files and data volume added/removed for the day
- `parents` (object): the number of parent records added/removed for the day, with subcounts for metadata-only parent records and parent records with files
- `records` (object): the number of records added/removed for the day, with subcounts for metadata-only records and records with files
- `period_start` and `period_end` (date): The date range for this delta
- `uploaders` (integer): Number of unique users who uploaded records
- `subcounts` (object): Detailed breakdowns by various metadata fields including:
  - `by_resource_types` (array[object]): Breakdown by resource type (journal articles, datasets, etc.)
  - `by_access_statuses` (array[object]): Breakdown by access status (open, restricted, etc.)
  - `by_languages` (array[object]): Breakdown by deposit language (English, French, etc.)
  - `by_affiliations` (array[object]): Breakdown by creator/contributor affiliations
  - `by_funders` (array[object]): Breakdown by funding organizations
  - `by_subjects` (array[object]): Breakdown by subject classifications
  - `by_publishers` (array[object]): Breakdown by publisher
  - `by_periodicals` (array[object]): Breakdown by journal/periodical
  - `by_file_types` (array[object]): Breakdown by file types (PDF, CSV, etc.)

Each of the subcounts is an array of objects. With the exception of the `by_file_types` subcount, each sujcount object in an array has the following fields:
- `id` (string): The identifier for the subcount (e.g., "open", "eng", etc.)
- `label` (string): The readable label for the subcount if one is available (e.g., "open", "English", etc.)
- `files` (object): The number of added/removed files and data volume for records with the subcount item, structured as in the top-level `files` object
- `parents` (object): The number of added/removed parent records with the subcount item, structured as in the top-level `parents` object
- `records` (object): The number of added/removed records with the subcount item, structured as in the top-level `records` object

Since it does not make sense to count metadata-only records in the subcount by file type, the `by_file_types` subcount array objects have a slightly different shape. They have the following fields:
- `id` (string): The identifier for the subcount (e.g., "pdf", "csv", etc.)
- `label` (string): The readable label for the subcount if one is available (e.g., "PDF", "CSV", etc.)
- `added` (object): The number of added files and data volume for records with the subcount item, structured as in the top-level `files.added` object
- `removed` (object): The number of removed files and data volume for records with the subcount item, structured as in the top-level `files.removed` object

```{note}
Each subcount array will include objects for only those subcount values that appear in that day's added or removed records. For example, if there are no records with the "open" access status on a given day, the `by_access_statuses` subcount array will not include an object for "open".
```

These aggregation documents are stored in the indices:
- `stats-community-records-delta-created-YYYY`
  - alias: `stats-community-records-delta-created`
  - index template: `search_indices/stats_community_records_delta_created/os-v2/stats-community-records-delta-created-v1.0.0.json`
- `stats-community-records-delta-published-YYYY`
  - alias: `stats-community-records-delta-published`
  - index template: `search_indices/stats_community_records_delta_published/os-v2/stats-community-records-delta-published-v1.0.0.json`
- `stats-community-records-delta-added-YYYY`
  - alias: `stats-community-records-delta-added`
  - index template: `search_indices/stats_community_records_delta_added/os-v2/stats-community-records-delta-added-v1.0.0.json`

Each document is shaped like this (the documents for the three different record delta indices have an identical shape, but the counts will differ):
```json
{
    "timestamp": "2021-01-01T00:00:00Z",
    "community_id": "global",
    "files": {
        "added": {
            "data_volume": 1000000,
            "file_count": 100
        }
    },
    "parents": {
        "added": {
            "metadata_only": 100,
            "with_files": 100
        }
    },
    "records": {
        "added": {
            "metadata_only": 100,
            "with_files": 100
        }
    },
    "period_start": "2021-01-01",
    "period_end": "2021-01-01",
    "uploaders": 100,
    "subcounts": {
        "by_resource_types": [
            {
                "id": "dataset",
                "label": "Dataset",
                "files": {
                    "added": {
                        "data_volume": 1000000,
                        "file_count": 100
                    }
                }
            },
            {
                "id": "research_paper",
                "label": "Research Paper",
                "files": {
                    "added": {
                        "data_volume": 1000000,
                        "file_count": 100
                    }
                }
            }
        ],
        "by_access_statuses": [],
        "by_languages": [],
        "by_affiliations": [],
        "by_funders": [],
        "by_subjects": [],
        "by_publishers": [],
        "by_periodicals": [],
        "by_file_types": [
          {
            "id": "pdf",
            "label": "",
              "added": {
                  "data_volume": 1000000,
                  "file_count": 100,
                  "parents": 100,
                  "records": 100
              },
              "removed": {
                  "data_volume": 0,
                  "file_count": 0,
                  "parents": 0,
                  "records": 0
              }
            }
          ]
    },
    "updated_timestamp": "2021-01-01T00:00:00Z"
}
```

#### Daily record snapshots

The snapshot aggregations provide cumulative totals at specific points in time, showing the total state of the community/instance as of a given date. These aggregations are based on the metadata records in the `rdm-records-records` index and the community membership events in the `stats-community-events` index. Each snapshot document includes:

- `community_id` (string): The community identifier
- `snapshot_date` (date): The date of this snapshot
- `timestamp` (date): When the aggregation was created
- `total_records` (object): Total record counts (metadata-only vs with files)
- `total_parents` (object): Total parent record counts
- `total_files` (object): Total file counts and data volume
- `total_uploaders` (integer): Total number of unique uploaders
- `subcounts` (object): Cumulative breakdowns by metadata fields, similar to deltas but showing totals rather than daily changes.
  - `all_access_statuses` (array[object]): Total number of records by access status
  - `all_file_types` (array[object]): Total number of records by file type
  - `all_rights` (array[object]): Total number of records by rights
  - `all_resource_types` (array[object]): Total number of records by resource type
  - `top_languages` (array[object]): Top N languages by number of records (configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT)
  - `top_affiliations_contributor` (array[object]): Top N contributor affiliations by number of records (configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT)
  - `top_affiliations_creator` (array[object]): Top N creator affiliations by number of records (configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT)
  - `top_funders` (array[object]): Top N funders by number of records (configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT)
  - `top_periodicals` (array[object]): Top N journals/periodicals by number of records (configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT)
  - `top_publishers` (array[object]): Top N publishers by number of records (configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT)
  - `top_subjects` (array[object]): Top N subjects by number of records (configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT)

The subcount properties are named slightly differently from the delta aggregations, with the `by_` prefix removed from the property names. Instead, some the subcount properties will be prefixed with either `all_` or `top_`. The `all_` prefix indicates that the subcount includes all values for the metadata field that have been used in the community/instance to-date. For example, the `all_access_statuses` subcount will provide a number for all access status values that appear in any record. The `top_` prefix indicates that the subcount includes only the top values for the metadata field that have been used in the community/instance to-date. For example, the `top_affiliations_contributor` subcount will provide a number for the top N contributor affiliations that have been used in the community/instance to-date (where N is configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT).

Each subcount array object has the same shape as the subcount objects in the corresponding delta aggregations.

```{note}
The `top_` subcounts provide the top values over the whole history of the community/instance, even if it does not appear in records added on the snapshot date.
```

These aggregation documents are stored in the indices:
- `stats-community-records-snapshot-created-YYYY`
  - alias: `stats-community-records-snapshot-created`
  - index template: `search_indices/stats_community_records_snapshot_created/os-v2/stats-community-records-snapshot-created-v1.0.0.json`
- `stats-community-records-snapshot-published-YYYY`
  - alias: `stats-community-records-snapshot-published`
  - index template: `search_indices/stats_community_records_snapshot_published/os-v2/stats-community-records-snapshot-published-v1.0.0.json`
- `stats-community-records-snapshot-added-YYYY`
  - alias: `stats-community-records-snapshot-added`
  - index template: `search_indices/stats_community_records_snapshot_added/os-v2/stats-community-records-snapshot-added-v1.0.0.json`

Each document is shaped like this (the documents for the three different record snapshot indices have an identical shape, but the counts will differ):
```json
{
    "community_id": "global",
    "snapshot_date": "2021-01-01",
    "timestamp": "2021-01-01T00:00:00Z",
    "total_records": {
        "metadata_only": 100,
        "with_files": 100
    },
    "total_parents": {
        "metadata_only": 100,
        "with_files": 100
    },
    "total_files": {
        "data_volume": 1000000,
        "file_count": 100
    },
    "total_uploaders": 100,
    "subcounts": {
        "all_access_statuses": [
          {
            "id": "open",
            "label": "Open",
            "records": {
              "metadata_only": 100,
              "with_files": 100
            },
            "parents": {
              "metadata_only": 100,
              "with_files": 100
            },
            "files": {
              "added": {
                "data_volume": 1000000,
                "file_count": 100
              }
            }
          }
        ],
        "all_file_types": [
          {
            "id": "pdf",
            "label": "PDF",
            "added": {
              "data_volume": 1000000,
              "file_count": 100
            },
            "removed": {
              "data_volume": 0,
              "file_count": 0
            }
          }
        ],
        "top_languages": [],
        "all_resource_types": [],
        "top_affiliations_contributor": [],
        "top_affiliations_creator": [],
        "top_funders": [],
        "top_periodicals": [],
        "top_publishers": [],
        "top_subjects": []
    },
    "updated_timestamp": "2021-01-01T00:00:00Z"
}
```

```{note}
The `top_` subcounts will in practice never be empty after the first few snapshots, since the top N values to-date will always be included (where N is configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT).
```

#### Usage deltas

The usage delta aggregations track daily view and download counts for the community/instance as a whole. These aggregations are based on the `record-view` and `file-download` events indexed by the `invenio-stats` module, which are enriched beforehand with community membership information and selected record metadata. Each usage delta document includes:

- `community_id` (string): The community identifier
- `period_start` and `period_end` (date): The date range for this delta
- `timestamp` (date): When the aggregation was created
- `totals` (object): Overall usage metrics for the day:
  - `view` (object): View event statistics
    - `total_events` (integer): Total number of views
    - `unique_parents` (integer): Total number of unique parent records viewed
    - `unique_records` (integer): Total number of unique records viewed
    - `unique_visitors` (integer): Total number of unique visitors who viewed the records
  - `download` (object): Download event statistics with data volume
    - `total_events` (integer): Total number of downloads
    - `total_volume` (float): Total data volume of downloads
    - `unique_files` (integer): Total number of unique files downloaded
    - `unique_parents` (integer): Total number of unique parent records downloaded
    - `unique_records` (integer): Total number of unique records downloaded
    - `unique_visitors` (integer): Total number of unique visitors
- `subcounts` (object): Detailed breakdowns by:
  - `by_access_statuses` (array[object]): Usage by access status
  - `by_resource_types` (array[object]): Usage by resource type
  - `by_rights` (array[object]): Usage by rights type
  - `by_funders` (array[object]): Usage by funding organization
  - `by_periodicals` (array[object]): Usage by journal/periodical
  - `by_languages` (array[object]): Usage by language
  - `by_subjects` (array[object]): Usage by subject classification
  - `by_publishers` (array[object]): Usage by publisher
  - `by_affiliations` (array[object]): Usage by creator/contributor affiliations
  - `by_file_types` (array[object]): Usage by file type
  - `by_countries` (array[object]): Usage by visitor country
  - `by_referrers` (array[object]): Usage by referrer

Each of the subcount arrays will include objects for only those subcount values that appear in that day's view or download events. For example, if no records with the "open" access status are viewed or downloaded on a given day, the `by_access_statuses` subcount array will not include an object for "open".

Each object in the subcount arrays will have the following fields:
- `id` (string): The identifier for the subcount (e.g., "open", "eng", etc.)
- `label` (string): The label for the subcount (e.g., "Open", "English", etc.)
- `view` (object): The number of views for records with the subcount item, structured as in the top-level `view` object
- `download` (object): The number of downloads for records with the subcount item, structured as in the top-level `download` object

```{note}
In addition to the same subcounts included in the record delta aggregations, the usage delta aggregations also include the following subcounts for visitor country and referrer domain.
```

```{note}
The counts for unique visitors, unique views, and unique downloads depend on the deduplication logic in the `invenio-stats` module, implemented when the `record-view` and `file-download` events are indexed.
```

These aggregation documents are stored in the indices:
- `stats-community-usage-delta-YYYY`
  - alias: `stats-community-usage-delta`
  - index template: `search_indices/stats_community_usage_delta/os-v2/stats-community-usage-delta-v1.0.0.json`

Each document is shaped like this:
```json
{
    "community_id": "global",
    "period_start": "2021-01-01",
    "period_end": "2021-01-01",
    "timestamp": "2021-01-01T00:00:00Z",
    "totals": {
        "view": {
            "total_events": 100,
            "unique_parents": 100,
            "unique_records": 100,
            "unique_visitors": 100
        },
        "download": {
            "total_events": 100,
            "total_volume": 1000000,
            "unique_files": 100,
            "unique_parents": 100,
            "unique_records": 100,
            "unique_visitors": 100
        }
    },
    "subcounts": {
      "by_access_statuses": [
        {
          "id": "open",
          "label": "Open",
          "view": {
            "total_events": 100,
            "unique_parents": 100,
            "unique_records": 100,
            "unique_visitors": 100
          },
          "download": {
            "total_events": 100,
            "total_volume": 1000000,
            "unique_files": 100,
            "unique_parents": 100,
            "unique_records": 100,
            "unique_visitors": 100
          }
        }
      ],
      "by_resource_types": [],
      "by_rights": [],
      "by_funders": [],
      "by_periodicals": [],
      "by_languages": [],
      "by_subjects": [],
      "by_publishers": [],
      "by_file_types": [],
      "by_affiliations": [],
      "by_countries": [],
      "by_referrers": []
    }
}
```


#### Usage snapshots

The usage snapshot aggregations provide cumulative view and download totals for each community/instance at the end of each day. These aggregations are based
on the `record-view` and `file-download` events indexed by the `invenio-stats` module, which are enriched beforehand with community membership information and selected record metadata. Each usage snapshot
document includes:

- `community_id` (string): The community identifier
- `snapshot_date` (date): The date of this snapshot
- `timestamp` (date): When the aggregation was created
- `totals` (object): Cumulative usage metrics (similar structure to deltas but cumulative)
  - `view` (object): View event statistics
    - `total_events` (integer): Total number of views
    - `unique_parents` (integer): Total number of unique parent records viewed
    - `unique_records` (integer): Total number of unique records viewed
    - `unique_visitors` (integer): Total number of unique visitors who viewed the records
  - `download` (object): Download event statistics with data volume
    - `total_events` (integer): Total number of downloads
    - `total_volume` (float): Total data volume of downloads
    - `unique_files` (integer): Total number of unique files downloaded
    - `unique_parents` (integer): Total number of unique parent records downloaded
    - `unique_records` (integer): Total number of unique records downloaded
    - `unique_visitors` (integer): Total number of unique visitors
- `subcounts` (object): Cumulative breakdowns by metadata fields, showing total usage across all time rather than daily changes
  - `all_access_statuses` (array[object]): Total number of records by access status
  - `all_file_types` (array[object]): Total number of records by file type
  - `all_rights` (array[object]): Total number of records by rights type
  - `all_resource_types` (array[object]): Total number of records by resource type
  - `top_languages` (array[object]): Top N languages by number of records (configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT)
  - `top_affiliations` (array[object]): Top N contributor affiliations by number of records (configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT)
  - `top_funders` (array[object]): Top N funders by number of records (configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT)
  - `top_periodicals` (array[object]): Top N journals/periodicals by number of records (configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT)
  - `top_publishers` (array[object]): Top N publishers by number of records (configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT)
  - `top_subjects` (array[object]): Top N subjects by number of records (configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT)
  - `top_countries` (array[object]): Top N countries by number of records (configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT)
  - `top_referrers` (array[object]): Top N referrers by number of records (configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT)

```{note}
Each of the `top_` subcount arrays will include objects for the top N values to-date (where N is configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT), even if they do not appear in the records added on the snapshot date.
```

Each object in the `all_` subcount arrays will have the following fields:
- `id` (string): The identifier for the subcount (e.g., "open", "eng", etc.)
- `label` (string): The label for the subcount (e.g., "Open", "English", etc.)
- `view` (object): The number of views for records with the subcount item, structured as in the top-level `view` object
- `download` (object): The number of downloads for records with the subcount item, structured as in the top-level `download` object

Each object in the `top_` subcount arrays will have the following fields is further broken down into a `by_view` and `by_download` object. Separate arrays are provided for the most-viewed and most-downloaded metadata values. Each object in these `by_view` and `by_download` objects will have the same fields as the `all_` subcount objects.

```{note}
The counts for unique visitors, unique views, and unique downloads depend on the deduplication logic in the `invenio-stats` module, implemented when the `record-view` and `file-download` events are indexed.
```

These aggregation documents are stored in the indices:
- `stats-community-usage-snapshot-YYYY`
  - alias: `stats-community-usage-snapshot`
  - index template: `search_indices/stats_community_usage_snapshot/os-v2/stats-community-usage-snapshot-v1.0.0.json`

Each document is shaped like this:
```json
{
    "community_id": "global",
    "snapshot_date": "2021-01-01",
    "timestamp": "2021-01-01T00:00:00Z",
    "totals": {
        "view": {
            "total_events": 100,
            "unique_parents": 100,
            "unique_records": 100,
            "unique_visitors": 100
        },
        "download": {
            "total_events": 100,
            "total_volume": 1000000,
            "unique_files": 100,
            "unique_parents": 100,
            "unique_records": 100,
            "unique_visitors": 100
        }
    },
    "subcounts": {
        "all_access_statuses": [
          {
            "id": "open",
            "label": "Open",
            "view": {
              "total_events": 100,
              "unique_parents": 100,
              "unique_records": 100,
              "unique_visitors": 100
            },
            "download": {
              "total_events": 100,
              "total_volume": 1000000,
              "unique_files": 100,
              "unique_parents": 100,
              "unique_records": 100,
              "unique_visitors": 100
            }
          }
        ],
        "top_languages": [],
        "all_rights": [],
        "all_resource_types": [],
        "top_affiliations": {
          "by_view": [
            {
              "id": "013v4ng57",
              "label": "University of California, Berkeley",
              "view": {
                "total_events": 100,
                "unique_parents": 100,
                "unique_records": 100,
                "unique_visitors": 100
              },
              "download": {
                "total_events": 100,
                "total_volume": 1000000,
                "unique_files": 100,
                "unique_parents": 100,
                "unique_records": 100,
                "unique_visitors": 100
              }
            }
          ],
          "by_download": [
            {
              "id": "013v4ng58",
              "label": "National Science Foundation",
              "view": {
                "total_events": 100,
                "unique_parents": 100,
                "unique_records": 100,
                "unique_visitors": 100
              },
              "download": {
                "total_events": 100,
                "total_volume": 1000000,
                "unique_files": 100,
                "unique_parents": 100,
                "unique_records": 100,
                "unique_visitors": 100
              }
            }
          ]
        },
        "top_funders": [],
        "top_periodicals": [],
        "top_publishers": [],
        "top_subjects": [],
        "top_countries": [],
        "top_referrers": []
    }
}
```

#### Search index configuration

The indices used for the statistics are managed by index templates that are registered with `invenio-stats` via the
aggregation configurations in the `STATS_AGGREGATIONS` configuration variable. In a new InvenioRDM instance, the `invenio-stats` module
ensures that the templates are registered with the OpenSearch domain. and the indices are created automatically when records are first indexed.

For more information about the index configuration and creation process, see [Setup and Migration](#setup-and-migration) below.

### Service layer

At the service layer, this module provides:
- celery tasks to aggregate community and global instance statistics on an hourly schedule
- service components to record community and global add/remove events
- a service class to facilitate programmatic access to the statistics data (accessed via the `current_community_stats_service` proxy)
- a second service class to facilitate migration of the usage event indices (accessed via the `current_event_reindexing_service` proxy)
- a helper class to generate synthetic usage events for testing

The celery tasks are also responsible for ensuring that historical data is progressively aggregated and indexed when the extension is first installed. For more information, see [Setup and Migration](#setup-and-migration) below.

#### Aggregator classes

The actual aggregations are performed by a set of aggregator classes registered with the `invenio-stats` module via the `STATS_AGGREGATIONS` configuration variable. These classes are:

- **CommunityRecordsSnapshotCreatedAggregator**: Creates snapshot aggregations based on record creation dates
- **CommunityRecordsSnapshotAddedAggregator**: Creates snapshot aggregations based on when records were added to communities
- **CommunityRecordsSnapshotPublishedAggregator**: Creates snapshot aggregations based on record publication dates
- **CommunityRecordsDeltaCreatedAggregator**: Creates delta aggregations based on record creation dates
- **CommunityRecordsDeltaAddedAggregator**: Creates delta aggregations based on when records were added to communities
- **CommunityRecordsDeltaPublishedAggregator**: Creates delta aggregations based on record publication dates
- **CommunityUsageSnapshotAggregator**: Creates usage snapshot aggregations for view and download events
- **CommunityUsageDeltaAggregator**: Creates usage delta aggregations for view and download events

One additional aggregator class (**CommunityEventsIndexAggregator**) is registered with the `invenio-stats` module to facilitate registration of the index template for the `stats-community-events` index. This class does not usually actually perform any aggregation, since those events are created by the service components described below. It is
only called by the utility service method that sets up the initial indexed events for an existing InvenioRDM
instance.

```{note}
The aggregator classes are idempotent, meaning that they can be run multiple times without causing duplicate aggregations. This is achieved first by using the `invenio-stats` bookmarking mechanism to track the progress of the aggregation and begin each aggregation from the last processed date. The aggregator classes also check each time for an existing aggregation document and deleting any that are found for the same date before indexing a new one.
```

```{note}
The `invenio-stats` module expects each configured aggregation to correspond to a configured event type. The default aggregator class, along with several available properties of the `STATS_AGGREGATIONS` config objects, are designed with this kind of event-aggregation structure in mind. The `invenio-stats-dashboard` aggregations, however, are compiling counts based on record metadata or usage events in ways that do not fit this pattern. Hence this package provides aggregator classes that are designed quite differently, although they follow some of the patterns of the default aggregator class (e.g., the use of an `agg_iter` method and the `invenio-stats` bookmarking mechanism). As a result, the `STATS_AGGREGATIONS` config objects for the `invenio-stats-dashboard` aggregations include less information than what must be provided to the default aggregator class.
```

#### Scheduled aggregation of statistics

The aggregator classes are run via a celery task, tasks.aggregate_community_record_stats. This task calls the `run` method of the eight aggregator classes in turn. These methods are run sequentially by design, to avoid race conditions, and to avoid overloading the OpenSearch domain with too many concurrent requests. The task is scheduled to run hourly by default, but can be configured via the `COMMUNITY_STATS_CELERYBEAT_SCHEDULE` configuration variable. The scheduled tasks can be disabled by setting the `COMMUNITY_STATS_SCHEDULED_TASKS_ENABLED` configuration variable to `False`. (See [Configuration](#configuration) below for more information.)

#### Aggregation task locking and catch-up limits

The background aggregation tasks are designed to be as efficient as possible. With large instances, though, it is theoretically possible that an aggregation task may not complete before the next aggregation task is scheduled to run. To prevent this, a lock prevents a new aggregation tasks from starting until the previous task has completed. In case a scheduled task is not able to acquire the lock, it will log a warning and skip the aggregation. Aggregation will continue normally on the next scheduled run, provided that the lock is not still held by the previous task. This locking mechanism can be disabled or configured via the `STATS_DASHBOARD_LOCK_CONFIG` configuration variable.

The risk of long-running tasks is mitigated by the use of a catch-up limit. Most long-running tasks would result from the presence of historical data that must be aggregated before the current date's aggregation can begin. The catch-up limit is set to 365 days by default, but can be configured via the `STATS_DASHBOARD_CATCHUP_INTERVAL` configuration variable. If the catch-up limit is reached before the current date's aggregation is complete, the task will exit and continue to catch up on the next scheduled run. See [Setup and Migration](#setup-and-migration) below for more information about the catch-up process.

#### Service components for community event tracking

The module provides specialized service components that automatically record community membership changes. These
components hook into the following service classes and methods:

- **CommunityAcceptedEventComponent**: Integrates with the `RequestEventsService` from `invenio-requests` and triggers on the `create` method when community inclusion, submission, or transfer requests are accepted. It automatically creates events in the `stats-community-events` index when records are added to communities through the request workflow.

- **RecordCommunityEventComponent**: Integrates with the `RDMRecordService` from `invenio-rdm-records` and provides three key methods:
  - `publish`: Called when a record is published, compares the new community membership with the previous published version to determine additions and removals
  - `delete_record`: Called when a record is deleted, marks all existing community events for that record as deleted
  - `restore_record`: Called when a record is restored, clears the deletion flags from all community events for that record

- **RecordCommunityEventTrackingComponent**: Integrates with the `RecordCommunitiesService` from `invenio-rdm-records` and provides methods for direct community membership management:
  - `add`: Called when records are added to communities, creates addition events
  - `bulk_add`: Called for bulk community additions, processes multiple records at once
  - `remove`: Called when records are removed from communities, creates removal events

```{note}
There is some redundant overlap between the components for these service components, meaning that in some cases
the same user action will trigger more than one component. This will *not* result in duplicate events being created,
and it is necessary to ensure that all events are caught when community inclusion is changed using any of the
multiple possible methods.
```

#### Programmatic statistics access service

The module includes a CommunityStatsService class that provides a programmatic interface to the statistics data, accessed via the `current_community_stats_service` proxy. The class exposes the following public methods:

- `generate_record_community_events`: Creates community add/remove events for all records in the instance that do not already have events. Can be run via the `invenio community-stats generate-community-events` CLI command.
- `aggregate_stats`: Manually triggers the aggregation of statistics for a community or instance. Can be run via the `invenio community-stats aggregate-stats` CLI command.
- `read_stats`: Reads the statistics data for a community or instance. Can be run via the `invenio community-stats read-stats` CLI command.

#### Helper class for usage event index migration

The module includes an EventReindexingService class that can be used to migrate existing usage events to the new index templates, accessed via the `current_event_reindexing_service` proxy. This class can also be used via the `invenio community-stats migrate-events` CLI command and its associated helper commands.

#### Utilities for generating testing data

The module includes a helper class (utils.usage_events.UsageEventFactory) that can be used to generate synthetic view and download events for testing.
This class creates usage events *without* the enriched metadata fields that are added to the events by the `invenio-stats-dashboard` module, to facilitate testing of the index migration process for those usage events.

### Presentation layer

At the presentation layer, this module provides:
- Jinja2 templates and macros to display dynamic and configurable React-based statistics dashboards
- a Flask blueprint `invenio_stats_dashboard.blueprint` that registers view functions and routes for the global and community dashboards
- API queries to retrieve the aggregated statistics data at the `/api/stats` endpoint managed by the `invenio-stats` module

#### Dashboard templates

Two templates are provided, one for the global dashboard and one for the community dashboard:
- `templates/semantic-ui/invenio_stats_dashboard/stats_dashboard.html` - the global dashboard template
- `templates/semantic-ui/invenio_stats_dashboard/community_stats_dashboard.html` - the community dashboard template

Both of these templates are essentially wrappers around the `invenio_stats_dashboard/macros/stats_dashboard_macro.html` macro, which is used to display the dashboard content.

The templates themselves may be overridden by providing a custom template in the `STATS_DASHBOARD_TEMPLATES` configuration variable.

#### Views and routes

The `invenio_stats_dashboard` (in views/views.py) registers two view functions for the global and community dashboards:
- the global dashboard view, using the `invenio_stats_dashboard/stats_dashboard.html` template
- the community dashboard view, using the `invenio_stats_dashboard/community_stats_dashboard.html` template

By default, the global dashboard is registered with the `/stats` route, and the community dashboard is registered with the `/communities/<community_id>/stats` route. These routes can be overridden via the `STATS_DASHBOARD_ROUTES` configuration variable.

#### API queries

The module exposes the aggregated stats at the `/api/stats` endpoint managed by the `invenio-stats` module by adding configured queries to the `STATS_QUERIES` configuration variable.

Ten different queries are configured for this endpoint. Eight of these retrieve aggregated statistics from one of the `invenio-stats-dashboard` aggregation indices:

- `community-record-delta-created`
- `community-record-delta-published`
- `community-record-delta-added`
- `community-record-snapshot-created`
- `community-record-snapshot-added`
- `community-record-snapshot-published`
- `community-usage-delta`
- `community-usage-snapshot`

The ninth and tenth queries, `global-stats` and `community-stats`, are composite queries that retrieve the results of the other eight queries and combines them into a single response. Both of these queries use the `CommunityStatsResultsQuery` class. The `global-stats` query calls the `CommunityStatsResultsQuery` class with the `global` community ID and passes along optional `start_date` and `end_date` parameters. The `community-stats` query calls the `CommunityStatsResultsQuery` class with a required `community_id` parameter (the UUID of the community for which the stats are being retrieved) as well as the optional `start_date` and `end_date` parameters.

These queries can be customized by configuring the `COMMUNITY_STATS_QUERIES` configuration variable.

The usage of these endpoints is described in the [Usage](#usage) section below.

## Setup and Migration

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
- `STATS_DASHBOARD_MENU_ENABLED` = `True`
8. Set up other configuration and community page templates as desired
9. Restart the InvenioRDM instance

### Search index template registration

If the `invenio-stats-dashboard` extension is installed on a new InvenioRDM instance, the `invenio-stats` module will automatically register the extension's search index templates with the OpenSearch domain. But `invenio-stats` does not automatically do this registration for existing InvenioRDM instances, i.e. if the main OpenSearch index setup has already been performed. So the `invenio-stats-dashboard` extension will check at application startup to ensure that the extension's search index templates are registered with the OpenSearch domain. If they are not, it registers them with the `invenio-search` module and puts them to OpenSearch. The aggregation indices will then be created automatically when the first records are indexed.

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

If the reindexing of a particular month fails, the service will leave the original index in place and continue with the next month. It will log a warning and report the failure in the service's output report. The service will try to reindex the month again on the next run.

#### Handling progress across migration runs

If the service hits the maximum number of batches before a monthly index is completely migrated, it will log a warning and report the progress in the service's output report. The service will set a bookmark to record the last processed event id, so that the next reindexing service run can continue from that point. These bookmarks are stored in the `stats-community-events-reindexing` index and are set independently for each monthly index.

### Initial aggregation of historical data

The extension will perform the initial aggregation of historical statistics automatically as part of the scheduled aggregation tasks. This can be a long process, especially for large instances, so a utility CLI command to perform the catch-up aggregation manually is also provided. This gives the instance maintainer more control over the process and can still run in the background while the instance is in use. For details, see the [CLI commands](#cli-commands) section below.

## Usage

The module provides:

### Blueprints and routes

The module provides a blueprint `invenio_stats_dashboard.blueprint` that is registered with the following routes:

- `/stats` - the global dashboard.
- `/communities/<community_id>/stats` - the community dashboard.

These default routes are set via the `STATS_DASHBOARD_ROUTES` configuration variable and can be overridden.

### Jinja2 templates

#### Template macro

a Jinja2 template macro that can be included in other templates to display an embedded dashboard view:

```html
{%- extends "invenio_theme/page.html" %}
{%- import "invenio_stats_dashboard/stats_dashboard.html" as stats_dashboard %}

{%- block page_body %}
  {{ stats_dashboard.stats_dashboard() }}
{%- endblock %}
```

The macro takes the following parameters:

- `dashboard_config`: The configuration for the dashboard.
- `community`: The community to display the dashboard for (if `dashboard_type` is `community`). [Optional. Defaults to `None`].

#### Global dashboard template

A Jinja2 template for the global dashboard, registered as a top-level page template at the global stats dashboard route (`/stats` by default). A top-level menu item is registered for this template by default, but can be disabled by setting the `STATS_DASHBOARD_MENU_ENABLED` configuration variable to `False`. The text and position of the menu item can be configured via config variables. Alternately, a custom function can be provided to register the menu item (See [Configuration](#configuration) below for more information.)

#### Community dashboard template

A Jinja2 template for the community dashboard page content, intended to be used as a sub-page of the community details page. This is registered with the community stats dashboard route (`/communities/<community_id>/stats` by default).

To implement this in your community details page, you can add a menu tab to the community details page template linking to this template route.

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
- **CLI aggregation commands will fail**: `aggregate-stats` command will show an error
- **Manual aggregation still works**: You can still run aggregation manually via Celery tasks
- **All other functionality remains**: Event tracking, migration, and other features work normally

This allows you to enable the module for manual operations while preventing automatic background tasks.

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

### Aggregation task locking

The following configuration variables control the locking mechanism for the aggregation task:

```python
STATS_DASHBOARD_LOCK_CONFIG = {
    "enabled": True,  # Enable/disable distributed locking
    "lock_timeout": 86400,  # Lock timeout in seconds (24 hours)
    "lock_name": "community_stats_aggregation",  # Lock name
}
```

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

### Configuration Reference

The following table provides a complete reference of all available configuration variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `COMMUNITY_STATS_ENABLED` | `True` | Enable/disable the entire module |
| `COMMUNITY_STATS_SCHEDULED_TASKS_ENABLED` | `True` | Enable/disable scheduled aggregation tasks |
| `COMMUNITY_STATS_CELERYBEAT_SCHEDULE` | `{...}` | Celery beat schedule for aggregation tasks |
| `COMMUNITY_STATS_CATCHUP_INTERVAL` | `365` | Maximum days to catch up when aggregating historical data |
| `COMMUNITY_STATS_AGGREGATIONS` | `{...}` | Aggregation configurations (auto-generated) |
| `COMMUNITY_STATS_QUERIES` | `{...}` | Query configurations (auto-generated) |
| `STATS_DASHBOARD_LOCK_CONFIG` | `{...}` | Distributed locking configuration |
| `STATS_DASHBOARD_TEMPLATES` | `{...}` | Template paths for dashboard views |
| `STATS_DASHBOARD_ROUTES` | `{...}` | URL routes for dashboard pages |
| `STATS_DASHBOARD_UI_CONFIG` | `{...}` | UI configuration for dashboard appearance |
| `STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS` | `{...}` | Default date range options |
| `STATS_DASHBOARD_LAYOUT` | `{...}` | Dashboard layout and component configuration |
| `STATS_DASHBOARD_MENU_ENABLED` | `True` | Enable/disable menu integration |
| `STATS_DASHBOARD_MENU_TEXT` | `_("Statistics")` | Menu item text |
| `STATS_DASHBOARD_MENU_ORDER` | `1` | Menu item order |
| `STATS_DASHBOARD_MENU_ENDPOINT` | `"invenio_stats_dashboard.global_stats_dashboard"` | Menu item endpoint |
| `STATS_DASHBOARD_MENU_REGISTRATION_FUNCTION` | `None` | Custom menu registration function |
| `STATS_DASHBOARD_REINDEXING_MAX_BATCHES` | `1000` | Maximum batches per month for migration |
| `STATS_DASHBOARD_REINDEXING_BATCH_SIZE` | `1000` | Events per batch for migration. **Note: OpenSearch has a hard limit of 10,000 documents for search results, so this value cannot exceed 10,000.** |
| `STATS_DASHBOARD_REINDEXING_MAX_MEMORY_PERCENT` | `75` | Maximum memory usage for migration |

**Note**: Variables marked with `{...}` contain complex configuration objects that are documented in detail in the sections above.

## Statistics

We want to show the following statistics:

- Number of records in collection
  - Cumulative total at a given point of time (time series for histogram)
- Number of new records added
  - Total during a given period (time series for histogram)
- Number of record views
  - Total at a given point of time (time series for histogram)
  - Total during a given period (time series for histogram)
- Number of file downloads
  - Total at a given point of time (time series for histogram)
  - Total during a given period (times series for histogram)
- Data traffic (i.e., download volume)
  - Total at a given point of time (time series for histogram)
  - Total during a given period (time series for histogram)
- Data volume in collection
  - Total at a given point of time (time series for histogram)
  - Total during a given period (time series for histogram)
- Number of uploaders
  - Total at a given point of time (time series for histogram)
  - Total during a given period (time series for histogram)
- Top records by views
  - During a given period
- Top records by downloads
  - During a given period
- Top records by data traffic
  - During a given period
- Top users by created records
- Top languages
  - During a given period
- Top visitor countries
  - During a given period
- Top referrers
  - During a given period
- Top access rights
  - During a given period
- Top record types
  - During a given period
- Top record rights
  - During a given period
- Top funders for created records
- Top affiliations
- Top subject headings?
- Top communities?
- Top sub-communities?


## Search indices for statistics

**Assume that STATS_REGISTER_INDEX_TEMPLATES is set to True.**

## CLI Commands

The `invenio-stats-dashboard` module provides the following CLI commands for managing statistics infrastructure, migrating events, and monitoring progress. All commands are available as subcommands under the `invenio community-stats` command.

### Usage Event Migration Commands

#### `migrate-events`

Migrate existing usage (view and download) events to enriched indices with community and record metadata.

```bash
invenio community-stats migrate-events [OPTIONS]
```

**Options:**
- `--event-types, -e`: Event types to migrate (view, download). Can be specified multiple times. Defaults to both.
- `--max-batches, -b`: Maximum batches to process per month (default from `STATS_DASHBOARD_REINDEXING_MAX_BATCHES`)
- `--batch-size`: Number of events to process per batch (default from `STATS_DASHBOARD_REINDEXING_BATCH_SIZE`; max 10,000)
- `--max-memory-percent`: Maximum memory usage percentage before stopping (default from `STATS_DASHBOARD_REINDEXING_MAX_MEMORY_PERCENT`)
- `--dry-run`: Show what would be migrated without doing it
- `--async`: Run reindexing asynchronously using Celery
- `--delete-old-indices`: Delete old indices after migration (default is to keep them)

**Examples:**
```bash
# Basic migration for all event types
invenio community-stats migrate-events

# Dry run to see what would be migrated
invenio community-stats migrate-events --dry-run

# Limit batches for testing
invenio community-stats migrate-events --max-batches 10

# Migrate only view events
invenio community-stats migrate-events --event-types view

# Run asynchronously with custom settings
invenio community-stats migrate-events --async --batch-size 500 --max-memory-percent 70
```

#### `migrate-events-background`

Start event migration in the background with full process management capabilities. This command provides the same functionality as `migrate-events` but runs in the background with monitoring and control features.

```bash
invenio community-stats migrate-events-background [OPTIONS]
```

**Options:**
- `--event-types, -e`: Event types to migrate (view, download). Can be specified multiple times. Defaults to both.
- `--max-batches, -b`: Maximum batches to process per month
- `--batch-size`: Number of events to process per batch (default: 1000)
- `--max-memory-percent`: Maximum memory usage percentage before stopping (default: 85)
- `--delete-old-indices`: Delete old indices after migration
- `--pid-dir`: Directory to store PID and status files (default: `/tmp`)

**Examples:**
```bash
# Start background migration for all event types
invenio community-stats migrate-events-background

# Start background migration with custom settings
invenio community-stats migrate-events-background \
  --event-types view download \
  --batch-size 500 \
  --max-memory-percent 70 \
  --max-batches 100

# Use custom PID directory
invenio community-stats migrate-events-background \
  --pid-dir /var/run/invenio-community-stats
```

**Process Management:**
- Process name: `event-migration`
- Monitor progress: `invenio community-stats process-status event-migration`
- Cancel process: `invenio community-stats cancel-process event-migration`
- View logs: `invenio community-stats process-status event-migration --show-log`

#### `migrate-month`

Migrate a specific monthly download or view event index.

```bash
invenio community-stats migrate-month [OPTIONS]
```

**Options:**
- `--event-type, -e`: Event type (view or download) [required]
- `--month, -m`: Month to migrate (YYYY-MM) [required]
- `--max-batches, -b`: Maximum batches to process (default from `STATS_DASHBOARD_REINDEXING_MAX_BATCHES`)
- `--batch-size`: Number of events to process per batch (default from `STATS_DASHBOARD_REINDEXING_BATCH_SIZE`; max 10,000)
- `--max-memory-percent`: Maximum memory usage percentage (default from `STATS_DASHBOARD_REINDEXING_MAX_MEMORY_PERCENT`)
- `--delete-old-indices`: Delete old indices after migration

**Examples:**
```bash
# Migrate specific month
invenio community-stats migrate-month --event-type view --month 2024-01

# Resume interrupted migration with batch limit
invenio community-stats migrate-month --event-type download --month 2024-02 --max-batches 50

# Migrate with custom settings
invenio community-stats migrate-month --event-type view --month 2024-03 --batch-size 500 --max-memory-percent 70
```

### Status and Progress Commands

#### `migration-status`

Show the current migration status and progress across all monthly indices.

```bash
invenio community-stats migration-status
```

**Output includes:**
- System health status and memory usage
- Event estimates for each type (view, download)
- Monthly indices found with current month indicators
- Migration bookmarks showing progress for each month

**Example output:**
```
Migration Status
===============
System Health: ✅ OK
Memory Usage: 45.2%

Event Estimates:
  view: 1,234,567 events
  download: 567,890 events
  Total: 1,802,457 events

Monthly Indices:
  view: 24 indices
    - kcworks-events-stats-record-view-2023-01
    - kcworks-events-stats-record-view-2023-02
    - kcworks-events-stats-record-view-2024-01 (current)
  download: 24 indices
    - kcworks-events-stats-file-download-2023-01
    - kcworks-events-stats-file-download-2023-02
    - kcworks-events-stats-file-download-2024-01 (current)

Migration Bookmarks:
  view:
    2023-01: not started
    2023-02: abc123def456
    2024-01: xyz789uvw012
  download:
    2023-01: not started
    2023-02: def456ghi789
    2024-01: uvw012xyz345
```

#### `show-interrupted`

Show details about interrupted migrations and provide resume commands.

```bash
invenio community-stats show-interrupted
```

**Output includes:**
- List of interrupted migrations by event type and month
- Source and target indices for each interrupted migration
- Last processed event ID
- Resume commands for each interrupted migration

**Example output:**
```
Interrupted Migrations
=====================

⏸️  VIEW 2024-01:
  Source index: kcworks-events-stats-record-view-2024-01
  Last processed ID: abc123def456
  More records available: Yes
  Resume command:
    invenio community-stats migrate-month --event-type view --month 2024-01

⏸️  DOWNLOAD 2024-02:
  Source index: kcworks-events-stats-file-download-2024-02
  Last processed ID: xyz789uvw012
  More records available: Yes
  Resume command:
    invenio community-stats migrate-month --event-type download --month 2024-02
```

#### `estimate-migration`

Estimate the total number of events to migrate and provide time estimates.

```bash
invenio community-stats estimate-migration
```

**Output includes:**
- Event counts by type (view, download)
- Total events to migrate
- Rough time estimates for completion

**Example output:**
```
Event Migration Estimates:
========================================
     view:  1,234,567 events
 download:    567,890 events
----------------------------------------
    TOTAL:  1,802,457 events

Rough time estimate: 3.2 hours
(This is a very conservative estimate - actual time may vary significantly)
```

### Process Management Commands

These commands provide monitoring and control capabilities for background processes started with the `*-background` commands.

#### `process-status`

Monitor the status of a running background process.

```bash
invenio community-stats process-status <process-name> [OPTIONS]
```

**Arguments:**
- `process-name`: Name of the process to monitor (e.g., `event-migration`, `community-event-generation`)

**Options:**
- `--show-log`: Show recent log output from the process
- `--log-lines`: Number of log lines to show (default: 20)
- `--pid-dir`: Directory containing PID and status files (default: `/tmp`)

**Examples:**
```bash
# Check basic status
invenio community-stats process-status event-migration

# Show recent logs
invenio community-stats process-status event-migration --show-log

# Show more log lines
invenio community-stats process-status event-migration --show-log --log-lines 50
```

#### `cancel-process`

Gracefully cancel a running background process.

```bash
invenio community-stats cancel-process <process-name> [OPTIONS]
```

**Arguments:**
- `process-name`: Name of the process to cancel (e.g., `event-migration`, `community-event-generation`)

**Options:**
- `--timeout`: Seconds to wait for graceful shutdown before force kill (default: 30)
- `--pid-dir`: Directory containing PID files (default: `/tmp`)

**Examples:**
```bash
# Cancel with default timeout
invenio community-stats cancel-process event-migration

# Cancel with custom timeout
invenio community-stats cancel-process event-migration --timeout 60
```

#### `list-processes`

List all currently running background processes.

```bash
invenio community-stats list-processes [OPTIONS]
```

**Options:**
- `--pid-dir`: Directory containing PID files (default: `/tmp`)
- `--package-only`: Only show processes managed by invenio-stats-dashboard

**Examples:**
```bash
# List all processes
invenio community-stats list-processes

# List only package processes
invenio community-stats list-processes --package-only
```

### Community Add/Remove Events Commands

#### `generate-community-events`

Generate community add/remove events for all records in the instance or specific records/communities. This generates randomized synthetic data for testing purposes.

```bash
invenio community-stats generate-community-events [OPTIONS]
```

**Options:**
- `--community-id`: The UUID or slug of the community to generate events for. Can be specified multiple times.
- `--record-ids`: The IDs of the records to generate events for. Can be specified multiple times.

**Examples:**
```bash
# Generate events for all records
invenio community-stats generate-community-events

# Generate events for specific community
invenio community-stats generate-community-events --community-id my-community-slug

# Generate events for specific records
invenio community-stats generate-community-events --record-ids abc123 def456 ghi789

# Generate events for multiple communities
invenio community-stats generate-community-events --community-id comm1 --community-id comm2
```

#### `generate-community-events-background`

Start community event generation in the background with full process management capabilities. This command provides the same functionality as `generate-community-events` but runs in the background with monitoring and control features.

```bash
invenio community-stats generate-community-events-background [OPTIONS]
```

**Options:**
- `--community-id`: The UUID or slug of the community to generate events for. Can be specified multiple times.
- `--record-ids`: The IDs of the records to generate events for. Can be specified multiple times.
- `--pid-dir`: Directory to store PID and status files (default: `/tmp`).

**Examples:**
```bash
# Start background event generation for all records
invenio community-stats generate-community-events-background

# Start background event generation for specific community
invenio community-stats generate-community-events-background --community-id my-community-slug

# Start background event generation for specific records
invenio community-stats generate-community-events-background --record-ids abc123 def456 ghi789

# Use custom PID directory
invenio community-stats generate-community-events-background --pid-dir /var/run/invenio-community-stats
```

**Process Management:**
- Process name: `community-event-generation`
- Monitor progress: `invenio community-stats process-status community-event-generation`
- Cancel process: `invenio community-stats cancel-process community-event-generation`
- View logs: `invenio community-stats process-status community-event-generation --show-log`

### Usage Event Generation Commands

#### `generate-usage-events`

Generate synthetic usage events (view/download) for testing purposes using the UsageEventFactory.

```bash
invenio community-stats generate-usage-events [OPTIONS]
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

**Examples:**
```bash
# Generate 5 events per record for all records
invenio community-stats generate-usage-events

# Generate events for specific date range
invenio community-stats generate-usage-events \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --events-per-record 10

# Dry run to see what would be generated
invenio community-stats generate-usage-events --dry-run

# Generate enriched events for limited records
invenio community-stats generate-usage-events \
  --max-records 100 \
  --enrich-events \
  --events-per-record 3
```

#### `generate-usage-events-background`

Start usage event generation in the background with full process management capabilities. This command provides the same functionality as `generate-usage-events` but runs in the background with monitoring and control features.

```bash
invenio community-stats generate-usage-events-background [OPTIONS]
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
invenio community-stats generate-usage-events-background

# Start with custom parameters
invenio community-stats generate-usage-events-background \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --events-per-record 10 \
  --enrich-events

# Use custom PID directory
invenio community-stats generate-usage-events-background \
  --pid-dir /var/run/invenio-community-stats
```

**Process Management:**
- Process name: `usage-event-generation`
- Monitor progress: `invenio community-stats process-status usage-event-generation`
- Cancel process: `invenio community-stats cancel-process usage-event-generation`
- View logs: `invenio community-stats process-status usage-event-generation --show-log`

### Statistics Commands

#### `aggregate-stats`

Manually trigger the asynchronous aggregation of statistics for a community or instance.

```bash
invenio community-stats aggregate-stats [OPTIONS]
```

**Options:**
- `--community-id`: The UUID or slug of the community to aggregate stats for. Can also be `global` to aggregate stats for the global instance. If not specified, the aggregation will be done for all communities and the global instance.
- `--start-date`: The start date to aggregate stats for (default: the creation/publication/adding of the first record in the community/instance)
- `--end-date`: The end date to aggregate stats for (default: today)
- `--eager`: Whether to aggregate stats eagerly rather than asynchronously (default: False)
- `--update-bookmark`: Whether to update the progress bookmark (default: True)
- `--ignore-bookmark`: Whether to ignore the progress bookmark and force a full re-aggregation (default: False)

**Examples:**
```bash
# Aggregate stats for all communities and the global instance
invenio community-stats aggregate-stats

# Aggregate stats for specific community
invenio community-stats aggregate-stats --community-id my-community-id

# Aggregate stats for specific date range
invenio community-stats aggregate-stats --start-date 2024-01-01 --end-date 2024-01-31

# Force eager aggregation
invenio community-stats aggregate-stats --eager --ignore-bookmark
```

```{warning}
Currently this task does not automatically migrate historical view/download events. This needs to be done manually by running the `migrate-events` command before this task is run.
```

```{note}
This aggregation task will try to catch up missing community add/remove events, as with the regular scheduled aggregation tasks. It will also observe the aggregators' limits on the number of records to process in a single task run.
```

```{note}
Since the Celery task involved employs a lock to prevent concurrent execution, this manual trigger will prevent the scheduled task from running until it is completed.
```

#### `read-stats`

Read and display statistics data for a community or instance.

```bash
invenio community-stats read-stats [OPTIONS]
```

**Options:**
- `--community-id`: The ID of the community to read stats for (default: "global")
- `--start-date`: The start date to read stats for (default: yesterday)
- `--end-date`: The end date to read stats for (default: today)

**Examples:**
```bash
# Read global stats for yesterday
invenio community-stats read-stats

# Read community stats for specific date range
invenio community-stats read-stats --community-id my-community-id --start-date 2024-01-01 --end-date 2024-01-31

# Read global stats for specific date range
invenio community-stats read-stats --start-date 2024-01-01 --end-date 2024-01-31
```

**Note:** This command calls the `read_stats` method on the CommunityStatsService and displays the results using `pprint`.
