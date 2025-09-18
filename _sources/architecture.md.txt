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

This package provides infrastructure to pre-calculate and store daily aggregated delta and snapshot statistics for each community and the instance as a whole, with subcounts broken down by a configurable list of metadata fields. The data layer includes:

- search indices to store pre-aggregated statistics for communities and the instance as a whole
- search index to store events for community membership changes
- expanded usage event (view and download) search index mappings to include community and record metadata fields
- utility service to migrate existing usage events to the expanded mappings
- configuration to control which additional metadata fields are added to usage events to allow subcount aggregation by those fields
- configuration to control which metadata fields are used to provide pre-calculated subcounts in all aggregated statistics
- scheduled background tasks for hourly aggregation of the statistics

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

There is one index for each year, suffixed like this: `stats-community-events-2021`. The indices are collectively aliased to `stats-community-events`.

#### Enriched record usage events

In order to efficiently aggregate usage statistics by community, and in order to provide subcounts based on record metadata fields, the `invenio-stats-dashboard` module enriches the standard `invenio-stats` usage events with community and record metadata fields. This is done by overriding the default `invenio-stats` index templates for the `stats-events-record-view` and `stats-events-file-download` indices.

The new index templates are identical to the default templates, but add:

- a "community_ids" field with a list of the record's communities at the time of the event.
- a set of additional configurable fields containing record metadata to be used for subcount aggregations

By default, the following metadata fields are added to the enriched events:
- "resource_type"
- "access_status"
- "languages"
- "subjects"
- "publisher"
- "journal_title"
- "rights"
- "funders"
- "affiliations"
- "file_types"
- "periodical"

```{note}
The addition of these metadata fields does increase the size of the view and download search indices. Addition of the full set of metadata fields for each record will increase the size of the indices by approximately 100-150%.
```

The extension also overrides the default `invenio-stats` event builder classes for view and download events, adding logic to record community and select metadata information to each event document.

These two changes are sufficient to provide the enriched data for all future usage events. If the InvenioRDM instance has existing legacy view and download events, the extension provides a utility service to migrate the existing indices to the new index template and add the missing community and record metadata fields to the existing events. For more details, see [Setup and Migration](#setup-and-migration).

```{note}
The default search index templates provided by the `invenio-rdm-records` package do not specify the number of shards to be used per index. On platforms like AWS, this can result in creation of 5 shard indices per month, which can be problematic for performance and cost. The `invenio-stats-dashboard` module overrides the default templates to specify a single shard per index by default.
```

#### Aggregated statistics

The `invenio-stats-dashboard` module provides pre-aggregated daily statistics for each community and the instance as a whole. There are four kinds of pre-aggregations:

1. **Record deltas**: Daily changes in the number of records and files in the community/instance. These record the changes (additions/and removals) to the contents of a community/instance during a given day, based on the indexed record metadata and community membership events.
2. **Record snapshots**: Daily cumulative total counts of records and files in the community/instance as of a given date. These are based on the indexed record metadata and community membership events. They are calculated fresh for each day, rather than being aggregated from the record deltas. This is because some subcounts in the aggregated record deltas (such as by subject heading) include only the day's top values (e.g., the top 20 subject headings for the day). An accurate snapshot count requires that we include all records, not just the top values.
3. **Usage deltas**: Daily counts for the number of views and downloads for records and files in the community/instance. These are based on the indexed usage events.
4. **Usage snapshots**: Daily cumulative total counts of views and downloads for records and files in the community/instance as of a given date.

Each aggregation document includes a breakdown of subcounts based on a configurable list of metadata fields. By default, the following metadata fields are used:

- "metadata.resource_type"
- "access.status"
- "metadata.languages"
- "metadata.subjects"
- "metadata.publisher"
- "custom_fields.journal:journal.title"
- "metadata.rights"
- "metadata.funding.funder"
- "metadata.creators.affiliations"
- "metadata.contributors.affiliations"
- "files.entries.ext"

This allows on-the-fly display and reporting of any aggregated metrics broken down by any of these metadata fields.

Each aggregation is stored in a separate set of indices, one index per year, with a common alias to facilitate easy searching across all years. Each index includes daily documents with over-arching numbers for the InvenioRDM instance, as well as daily documents for each community. Each daily document includes broken-down subcounts based on record metadata fields such as resource type, access right, language, affiliation, funder, subject, publisher, and periodical.

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

```{warning}
The "published" record delta aggregators are not currently working. These require significant extra logic to handle (a) the aggregation of past delta documents prior to the InvenioRDM instance's first published record and (b) the updating of past snapshot documents when new records are added with a prior publication date.
```

#### Daily record deltas

The record delta aggregations track daily changes in the number of records and files in the community/instance. These aggregations are based on the metadata records in the `rdm-records-records` index and the community membership events in the `stats-community-events` index.

Each daily record delta document includes these fields:

- `timestamp` (date): When the aggregation was created
- `community_id` (string): The community identifier (or "global" for the instance as a whole)
- `files` (object): the number of files and data volume added/removed for the day
- `parents` (object): the number of parent records added/removed for the day, with subcounts for metadata-only parent records and parent records with files
- `records` (object): the number of records added/removed for the day, with subcounts for metadata-only records and records with files
- `period_start` and `period_end` (date): The date range for this delta
- `uploaders` (integer): Number of unique users who uploaded records
- `subcounts` (object): breakdowns by configurable metadata fields, by default including:
  - `resource_types` (array[object]): breakdown by resource type (journal articles, datasets, etc.)
  - `access_statuses` (array[object]): breakdown by access status (open, restricted, etc.)
  - `languages` (array[object]): breakdown by deposit language (English, French, etc.)
  - `affiliations_contributor` (array[object]): breakdown by contributor affiliations
  - `affiliations_creator` (array[object]): breakdown by creator affiliations
  - `funders` (array[object]): breakdown by funding organizations
  - `subjects` (array[object]): breakdown by subject classifications
  - `publishers` (array[object]): breakdown by publisher
  - `periodicals` (array[object]): breakdown by journal/periodical
  - `file_types` (array[object]): breakdown by file types (PDF, CSV, etc.)

Each of the subcounts is an array of objects with the following fields:

- `id` (string): The identifier for the subcount (e.g., "open", "eng", etc.)
- `label` (string or object): The readable label for the subcount if one is available (e.g., "open", {"en": "English", "fr": "French"}, etc.). The type of this field value depends on the type of the readable field provided in the record metadata schema.
- `files` (object): The number of added/removed files and data volume for records with the subcount item, structured as in the top-level `files` object
- `parents` (object): The number of added/removed parent records with the subcount item, structured as in the top-level `parents` object
- `records` (object): The number of added/removed records with the subcount item, structured as in the top-level `records` object

```{note}
Each subcount array will include objects for only those subcount values that appear in that day's added or removed records. For example, if there are no records with the "open" access status on a given day, the `access_statuses` subcount array will not include an object for "open".
```

These aggregation documents are stored in a set of annual indices:

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
        "resource_types": [
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
        "access_statuses": [],
        "languages": [],
        "affiliations": [],
        "funders": [],
        "subjects": [],
        "publishers": [],
        "periodicals": [],
        "file_types": [
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
- `total_parents` (object): Total parent record counts (metadata-only vs with files)
- `total_files` (object): Total file counts and data volume
- `total_uploaders` (integer): Total number of unique uploaders
- `subcounts` (object): Cumulative breakdowns by metadata fields, similar to deltas but showing totals rather than daily changes. By default these include:
    - `access_statuses` (array[object]): Total number of records by access status
    - `file_types` (array[object]): Total number of records by file type
    - `rights` (array[object]): Total number of records by rights
    - `resource_types` (array[object]): Total number of records by resource type
    - `languages` (array[object]): Top N languages by number of records (configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT)
    - `affiliations_contributor` (array[object]): Top N contributor affiliations by number of records (configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT)
    - `affiliations_creator` (array[object]): Top N creator affiliations by number of records (configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT)
    - `funders` (array[object]): Top N funders by number of records (configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT)
    - `periodicals` (array[object]): Top N journals/periodicals by number of records (configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT)
    - `publishers` (array[object]): Top N publishers by number of records (configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT)
    - `subjects` (array[object]): Top N subjects by number of records (configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT)

The subcount properties are named slightly differently from the delta aggregations. With unified field names, the subcount properties use the same names across delta and snapshot documents. The subcount for each day includes all values for the metadata field that have been used in the community/instance to-date. For example, the `access_statuses` subcount will provide a number for all access status values that appear in any record. The `affiliations_contributor` subcount will provide a number for the top N contributor affiliations that have been used in the community/instance to-date (where N is configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT).

Each subcount array object has the same shape as the subcount objects in the corresponding delta aggregations.

```{note}
The subcounts provide the top values over the whole history of the community/instance, even if it does not appear in records added on the snapshot date.
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
        "access_statuses": [
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
        "file_types": [
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
        "languages": [],
        "resource_types": [],
        "affiliations_contributor": [],
        "affiliations_creator": [],
        "funders": [],
        "periodicals": [],
        "publishers": [],
        "subjects": []
    },
    "updated_timestamp": "2021-01-01T00:00:00Z"
}
```

```{note}
The subcounts will in practice never be empty after the first few snapshots, since even the subcounts will include the top N values to-date (where N is configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT).
```

#### Usage deltas

The usage delta aggregations track daily view and download counts for the community/instance as a whole. These aggregations are based on the `record-view` and `file-download` events indexed by the `invenio-stats` module, which are enriched beforehand with community membership information and selected record metadata. Each usage delta document includes these fields:

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
  - `subcounts` (object): Detailed breakdowns by configurable metadata fields, by default including:
      - `access_statuses` (array[object]): Usage by access status
      - `resource_types` (array[object]): Usage by resource type
      - `rights` (array[object]): Usage by rights type
      - `funders` (array[object]): Usage by funding organization
      - `periodicals` (array[object]): Usage by journal/periodical
      - `languages` (array[object]): Usage by language
      - `subjects` (array[object]): Usage by subject classification
      - `publishers` (array[object]): Usage by publisher
      - `affiliations` (array[object]): Usage by creator/contributor affiliations
      - `file_types` (array[object]): Usage by file type
      - `countries` (array[object]): Usage by visitor country
      - `referrers` (array[object]): Usage by referrer

Each of the subcount arrays will include objects for only those subcount values that appear in that day's view or download events. For example, if no records with the "open" access status are viewed or downloaded on a given day, the `access_statuses` subcount array will not include an object for "open".

Each object in the subcount arrays will have the following fields:

- `id` (string): The identifier for the subcount (e.g., "open", "eng", etc.)
- `label` (string): The label for the subcount (e.g., "Open", "English", etc.)
- `view` (object): The number of views for records with the subcount item, structured as in the top-level `view` object
- `download` (object): The number of downloads for records with the subcount item, structured as in the top-level `download` object

```{note}
In addition to the same subcounts included in the record delta aggregations, the usage delta aggregations by default also include subcounts for visitor country and referrer domain. These too are configurable via the COMMUNITY_STATS_SUBCOUNT_CONFIGS configuration.
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
      "access_statuses": [
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
      "resource_types": [],
      "rights": [],
      "funders": [],
      "periodicals": [],
      "languages": [],
      "subjects": [],
      "publishers": [],
      "file_types": [],
      "affiliations": [],
      "countries": [],
      "referrers": []
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
  - `subcounts` (object): Cumulative breakdowns by metadata fields, showing total usage across all time rather than daily changes, by default including:
      - `access_statuses` (array[object]): Total number of records by access status
      - `file_types` (array[object]): Total number of records by file type
      - `rights` (array[object]): Total number of records by rights type
      - `resource_types` (array[object]): Total number of records by resource type
      - `languages` (array[object]): Top N languages, calculated both by number of views and number of downloads
      - `affiliations` (array[object]): Top N contributor affiliations, calculated both by number of views and number of downloads
      - `funders` (array[object]): Top N funders, calculated both by number of views and number of downloads
      - `periodicals` (array[object]): Top N journals/periodicals, calculated both by number of views and number of downloads
      - `publishers` (array[object]): Top N publishers, calculated both by number of views and number of downloads
      - `subjects` (array[object]): Top N subjects, calculated both by number of views and number of downloads
      - `countries` (array[object]): Top N countries, calculated both by number of views and number of downloads
      - `referrers` (array[object]): Top N referrers, calculated both by number of views and number of downloads

```{note}
Each of the subcount arrays will include objects for the top N values to-date (where N is configurable via COMMUNITY_STATS_TOP_SUBCOUNT_LIMIT), even if they do not appear in the records added on the snapshot date.
```

Each object in the subcount arrays will have the following fields:

- `id` (string): The identifier for the subcount (e.g., "open", "eng", etc.)
- `label` (string): The label for the subcount (e.g., "Open", "English", etc.)
- `view` (object): The number of views for records with the subcount item, structured as in the top-level `view` object
- `download` (object): The number of downloads for records with the subcount item, structured as in the top-level `download` object

Each object in the subcount arrays will have the following fields:
- `by_view` (array[object]): The top N views for the subcount item, each with the fields:
  - `id` (string): The identifier for the subcount (e.g., "open", "eng", etc.)
  - `label` (string): The label for the subcount (e.g., "Open", "English", etc.)
  - `view` (object): The number of views for records with the subcount item, structured as in the top-level `view` object
  - `download` (object): The number of downloads for records with the subcount item, structured as in the top-level `download` object
- `by_download` (array[object]): The top N downloads for the subcount item, each with the fields:
  - `id` (string): The identifier for the subcount (e.g., "open", "eng", etc.)
  - `label` (string): The label for the subcount (e.g., "Open", "English", etc.)
  - `view` (object): The number of views for records with the subcount item, structured as in the top-level `view` object
  - `download` (object): The number of downloads for records with the subcount item, structured as in the top-level `download` object

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
        "access_statuses": [
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
        "languages": [],
        "rights": [],
        "resource_types": [],
        "affiliations": {
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
        "funders": [],
        "periodicals": [],
        "publishers": [],
        "subjects": [],
        "countries": [],
        "referrers": []
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
- a `CommunityStatsService` class to facilitate programmatic access to the statistics data (accessed via the `current_community_stats_service` proxy) and handle community event record operations
- a second `EventReindexingService` class to facilitate migration of the usage event indices (accessed via the `current_event_reindexing_service` proxy)
- a helper `UsageEventFactory` class to generate synthetic usage events for testing

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

- `generate_record_community_events`: Creates community add/remove events for all records in the instance that do not already have events. Can be run via the `invenio community-stats community-events generate` CLI command.
- `aggregate_stats`: Manually triggers the aggregation of statistics for a community or instance. Can be run via the `invenio community-stats aggregate` CLI command.
- `read_stats`: Reads the statistics data for a community or instance. Can be run via the `invenio community-stats read` CLI command.

#### Helper class for usage event index migration

The module includes an `EventReindexingService` class that can be used to migrate existing usage events to the new index templates, accessed via the `current_event_reindexing_service` proxy. This class can also be used via the `invenio community-stats usage-events migrate` CLI command and its associated helper commands.

#### Utilities for generating testing data

The module includes a helper class (`UsageEventFactory`) that can be used to generate synthetic view and download events for testing.
This class can create usage events with or without the enriched metadata fields that are added to the events by the `invenio-stats-dashboard` module, to facilitate testing of the index migration process for those usage events. This class can also be used via the `invenio community-stats usage-events generate` CLI command and its associated helper commands.

```{warning}
Generated usage events cannot easily be removed without deleting the indices and losing any genuine usage events. It is therefore important not to generate these synthetic events in a production environment.
```

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

The `invenio_stats_dashboard` (in `views/views.py`) registers two view functions for the global and community dashboards:
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

The ninth and tenth queries, `global-stats` and `community-stats`, are composite queries that retrieve the results of the other eight queries and combines them into a single response. Both of these queries use the `CommunityStatsResultsQuery` class:

- `global-stats`: calls the `CommunityStatsResultsQuery` class with the `global` community ID and passes along optional `start_date` and `end_date` parameters.
- `community-stats`: calls the `CommunityStatsResultsQuery` class with a required `community_id` parameter (the UUID of the community for which the stats are being retrieved) as well as the optional `start_date` and `end_date` parameters.
