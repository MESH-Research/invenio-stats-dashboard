# Invenio Stats Dashboard

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

## Architecture

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
  - `by_resource_type` (array[object]): Breakdown by resource type (journal articles, datasets, etc.)
  - `by_access_status` (array[object]): Breakdown by access status (open, restricted, etc.)
  - `by_language` (array[object]): Breakdown by deposit language (English, French, etc.)
  - `by_affiliation` (array[object]): Breakdown by creator/contributor affiliations
  - `by_funder` (array[object]): Breakdown by funding organizations
  - `by_subject` (array[object]): Breakdown by subject classifications
  - `by_publisher` (array[object]): Breakdown by publisher
  - `by_periodical` (array[object]): Breakdown by journal/periodical
  - `by_file_type` (array[object]): Breakdown by file types (PDF, CSV, etc.)

Each of the subcounts is an array of objects. With the exception of the `by_file_type` subcount, each sujcount object in an array has the following fields:
- `id` (string): The identifier for the subcount (e.g., "open", "eng", etc.)
- `label` (string): The readable label for the subcount if one is available (e.g., "open", "English", etc.)
- `files` (object): The number of added/removed files and data volume for records with the subcount item, structured as in the top-level `files` object
- `parents` (object): The number of added/removed parent records with the subcount item, structured as in the top-level `parents` object
- `records` (object): The number of added/removed records with the subcount item, structured as in the top-level `records` object

Since it does not make sense to count metadata-only records in the subcount by file type, the `by_file_type` subcount array objects have a slightly different shape. They have the following fields:
- `id` (string): The identifier for the subcount (e.g., "pdf", "csv", etc.)
- `label` (string): The readable label for the subcount if one is available (e.g., "PDF", "CSV", etc.)
- `added` (object): The number of added files and data volume for records with the subcount item, structured as in the top-level `files.added` object
- `removed` (object): The number of removed files and data volume for records with the subcount item, structured as in the top-level `files.removed` object

```{note}
Each subcount array will include objects for only those subcount values that appear in that day's added or removed records. For example, if there are no records with the "open" access status on a given day, the `by_access_status` subcount array will not include an object for "open".
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
        "by_resource_type": [
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
        "by_access_status": [],
        "by_language": [],
        "by_affiliation": [],
        "by_funder": [],
        "by_subject": [],
        "by_publisher": [],
        "by_periodical": [],
        "by_file_type": [
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
  - `all_access_status` (array[object]): Total number of records by access status
  - `all_file_types` (array[object]): Total number of records by file type
  - `all_languages` (array[object]): Total number of records by language
  - `all_licenses` (array[object]): Total number of records by license
  - `all_resource_types` (array[object]): Total number of records by resource type
  - `top_affiliations_contributor` (array[object]): Top 20 contributor affiliations by number of records
  - `top_affiliations_creator` (array[object]): Top 20 creator affiliations by number of records
  - `top_funders` (array[object]): Top 20 funders by number of records
  - `top_periodicals` (array[object]): Top 20 journals/periodicals by number of records
  - `top_publishers` (array[object]): Top 20 publishers by number of records
  - `top_subjects` (array[object]): Top 20 subjects by number of records

The subcount properties are named slightly differently from the delta aggregations, with the `by_` prefix removed from the property names. Instead, some the subcount properties will be prefixed with either `all_` or `top_`. The `all_` prefix indicates that the subcount includes all values for the metadata field that have been used in the community/instance to-date. For example, the `all_access_status` subcount will provide a number for all access status values that appear in any record. The `top_` prefix indicates that the subcount includes only the top values for the metadata field that have been used in the community/instance to-date. For example, the `top_affiliations_contributor` subcount will provide a number for the top 20 contributor affiliations that have been used in the community/instance to-date.

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
        "all_access_status": [
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
        "all_languages": [],
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
The `top_` subcounts will in practice never be empty after the first few snapshots, since the top 20 values to-date will always be included.
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
  - `by_access_status` (array[object]): Usage by access status
  - `by_resource_types` (array[object]): Usage by resource type
  - `by_licenses` (array[object]): Usage by license type
  - `by_funders` (array[object]): Usage by funding organization
  - `by_periodicals` (array[object]): Usage by journal/periodical
  - `by_languages` (array[object]): Usage by language
  - `by_subjects` (array[object]): Usage by subject classification
  - `by_publishers` (array[object]): Usage by publisher
  - `by_affiliations` (array[object]): Usage by creator/contributor affiliations
  - `by_file_types` (array[object]): Usage by file type
  - `by_countries` (array[object]): Usage by visitor country
  - `by_referrers` (array[object]): Usage by referrer

Each of the subcount arrays will include objects for only those subcount values that appear in that day's view or download events. For example, if no records with the "open" access status are viewed or downloaded on a given day, the `by_access_status` subcount array will not include an object for "open".

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
      "by_access_status": [
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
      "by_licenses": [],
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
  - `all_access_status` (array[object]): Total number of records by access status
  - `all_file_types` (array[object]): Total number of records by file type
  - `all_languages` (array[object]): Total number of records by language
  - `all_licenses` (array[object]): Total number of records by license type
  - `all_resource_types` (array[object]): Total number of records by resource type
  - `top_affiliations` (array[object]): Top 20 contributor affiliations by number of records
  - `top_funders` (array[object]): Top 20 funders by number of records
  - `top_periodicals` (array[object]): Top 20 journals/periodicals by number of records
  - `top_publishers` (array[object]): Top 20 publishers by number of records
  - `top_subjects` (array[object]): Top 20 subjects by number of records
  - `top_countries` (array[object]): Top 20 countries by number of records
  - `top_referrers` (array[object]): Top 20 referrers by number of records

```{note}
Each of the `top_` subcount arrays will include objects for the top 20 values to-date, even if they do not appear in the records added on the snapshot date.
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
        "all_access_status": [
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
        "all_languages": [],
        "all_licenses": [],
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
- a service class to facilitate programmatic access to the statistics data
- helper functions to facilitate setup and maintenance of the statistics indices

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
The `invenio-stats` module expects each configured aggregation to correspond to a configure event type. The default aggregator class, along with several available properties of the `STATS_AGGREGATIONS` config objects, are designed with this kind of event-aggregation structure in mind. The `invenio-stats-dashboard` aggregations, however, are compiling counts based on record metadata or usage events in ways that do not fit this pattern. Hence this package provides aggregator classes that are designed quite differently, although they follow some of the patterns of the default aggregator class (e.g., the use of an `agg_iter` method and the `invenio-stats` bookmarking mechanism). As a result, the `STATS_AGGREGATIONS` config objects for the `invenio-stats-dashboard` aggregations include less information than what must be provided to the default aggregator class.
```

#### Scheduled aggregation of statistics

The aggregator classes are run via a celery task, tasks.aggregate_community_record_stats. This task calls the `run` method of the eight aggregator classes in turn. These methods are run sequentially by design, to avoid race conditions, and to avoid overloading the OpenSearch domain with too many concurrent requests. The task is scheduled to run hourly by default, but can be configured via the `COMMUNITY_STATS_CELERYBEAT_SCHEDULE` configuration variable.

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

#### Helper functions for index management

The module includes utility functions for setting up and maintaining the statistics infrastructure:

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

Setup of the `invenio-stats-dashboard` involves simply installing the python package and restarting the InvenioRDM instance. After installation, the extension may still be disabled by manually setting the `COMMUNITY_STATS_ENABLED` configuration variable to `False`. Otherwise, a number of setup tasks will be performed automatically.

### Search index template registration

If the `invenio-stats-dashboard` extension is installed on a new InvenioRDM instance, the `invenio-stats` module will automatically register the extension's search index templates with the OpenSearch domain. But `invenio-stats` does not automatically do this registration for existing InvenioRDM instances, i.e. if the main OpenSearch index setup has already been performed. So the `invenio-stats-dashboard` extension will check at application startup to ensure that the extension's search index templates are registered with the OpenSearch domain. If they are not, it registers them with the `invenio-search` module and puts them to OpenSearch. The aggregation indices will then be created automatically when the first records are indexed.

### Initial migration of existing record usage events

The `invenio-stats` search index templates for view and download events must then be updated to provide mappings for the additional fields used by `invenio-stats-dashboard`. If the InvenioRDM instance has existing legacy view and download events, these will also need to be migrated to the new index templates. The `EventReindexingService` class in the `service.py` performs both of these tasks and must be run before the first scheduled aggregation task can be performed.

Where no legacy view or download events exist, the `EventReindexingService.reindex_events` method will simply register the new index templates and usage events can be indexed normally. If usage events have already been indexed, however, the `reindex_events` method will perform the following steps:

1. Verify that the new index templates are registered with the OpenSearch domain
2. Create new monthly view and download indices for each legacy monthly index, adding the suffix `.v2.0.0` to the index names.
3. Copy the events from the legacy monthly indices to the new monthly indices, adding the community and record metadata fields to the events.
4. Confirm that the events have all been copied over.
5. Update the read aliases to point to the new monthly indices.
6. Delete the legacy monthly indices for months prior to the current month.
7. Create a write alias so that new usage events for the current month are indexed to the current month's new index.
8. After the month is complete, delete the current month's legacy index.

#### Manual reindexing of existing events

The `EventReindexingService.reindex_events` method can be run manually to reindex the events, or it can be run automatically as part of the first scheduled aggregation task.

#### Automatic reindexing of existing events


### Initial aggregation of historical data

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

A Jinja2 template for the global dashboard, registered as a top-level page template at the global stats dashboard route (`/stats` by default).

#### Community dashboard template

A Jinja2 template for the community dashboard page content, intended to be used as a sub-page of the community details page. This is registered with the community stats dashboard route (`/communities/<community_id>/stats` by default).

To implement this in your community details page, you can add a menu tab to the community details page template linking to this template route.

## Configuration

### Menu configuration

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
                            {"component": "LicensesTable", "width": 8},
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
STATS_DASHBOARD_CONFIG = {
    "global": {
        "title": "Statistics Dashboard",
        "description": "This is the global stats dashboard.",
        "maxHistoryYears": 15,
        "show_title": True,
        "show_description": False,
    },
    "community": {
        "title": "Community Statistics Dashboard",
        "description": "This is the community stats dashboard.",
        "maxHistoryYears": 15,
        "show_title": True,
        "show_description": False,
    },
}
```

#### Title and description display

The title and description display in different places for the global and community dashboards. For the global dashboard, the title and description are displayed in the page subheader, while for the community dashboard they display at the top of the dashboard sidebar.

The `show_title` and `show_description` options can be used to control whether the title and description are displayed for the global and community dashboards.

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
- Top record licenses
  - During a given period
- Top funders for created records
- Top affiliations
- Top subject headings?
- Top communities?
- Top sub-communities?


## Search indices for statistics

**Assume that STATS_REGISTER_INDEX_TEMPLATES is set to True.**
