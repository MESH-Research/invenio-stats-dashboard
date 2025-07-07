# Invenio Stats Dashboard

Invenio module that provides global and community statistics overviews for an InvenioRDM instance. It provides:
- data-layer storage of pre-aggregated statistics (daily cumulative snapshots and deltas) for communities and the instance as a whole
- service-layer aggregation of the community and global statistics on a regular schedule, along with service components to record community add/remove events
- API access to the aggregated daily statistics via the `/api/stats` endpoint
- Jinja2 templates and macros to display React-based global and community statistics dashboards

## Architecture

### Data layer

The data layer is responsible for storing the statistics in the search indices, using the infrastructure provided by the `invenio-stats` module. This module stores daily pre-aggregated statistics for the instance as a whole, and for each community in a series of dedicated search indices. There are four kinds of aggregations: record deltas, record snapshots, usage deltas, and usage snapshots. Each aggregation is stored in a separate set of indices, one index per year, with a common alias to facilitate easy searching across all years. Each index includes both over-arching numbers for the community/instance and broken-down subcounts based on record metadata fields such as resource type, access right, language, affiliation, funder, subject, publisher, and periodical.

With record deltas and record snapshots, there is an additional question about what to consider the "start" of a record's
lifetime. In some cases it may be most useful to consider when records are actually added to a community. But we
may also want to consider records based on when they are first published (`metadata.publication_date`), or when their
published records are first created. So we aggregate and store three different record deltas and three snapshots for each day,
one for each of these three different "start" dates.

#### Record deltas

Each daily record delta document includes:
- `community_id`: The community identifier
- `period_start` and `period_end`: The date range for this delta
- `timestamp`: When the aggregation was created
- `records_added` and `records_removed`: Count of records added/removed
- `parents_added` and `parents_removed`: Count of parent records added/removed
- `uploaders`: Number of unique users who uploaded records
- `subcounts`: Detailed breakdowns by various metadata fields including:
  - `by_resource_type`: Breakdown by resource type (journal articles, datasets, etc.)
  - `by_access_right`: Breakdown by access rights (open, restricted, etc.)
  - `by_language`: Breakdown by language
  - `by_affiliation`: Breakdown by creator/contributor affiliations
  - `by_funder`: Breakdown by funding organizations
  - `by_subject`: Breakdown by subject classifications
  - `by_publisher`: Breakdown by publisher
  - `by_periodical`: Breakdown by journal/periodical
  - `by_file_type`: Breakdown by file types (PDF, CSV, etc.)

These are stored in the indices:
- `stats-community-records-delta-created`
- `stats-community-records-delta-published`
- `stats-community-records-delta-added`

#### Record snapshots

The snapshot aggregations provide cumulative totals at specific points in time, showing the total state of the community/instance as of a given date. Each snapshot document includes:

- `community_id`: The community identifier
- `snapshot_date`: The date of this snapshot
- `timestamp`: When the aggregation was created
- `total_records`: Total record counts (metadata-only vs with files)
- `total_parents`: Total parent record counts
- `total_files`: Total file counts and data volume
- `total_uploaders`: Total number of unique uploaders
- `subcounts`: Cumulative breakdowns by metadata fields, similar to deltas but showing totals rather than daily changes

These are stored in the indices:
- `stats-community-records-snapshot-created`
- `stats-community-records-snapshot-published`
- `stats-community-records-snapshot-added`

#### Usage deltas

The usage delta aggregations track daily changes in usage statistics for each day. These aggregations are based
on the `record-view` and `file-download` events indexed by the `invenio-stats` module. Each usage delta
document includes:
- `community_id`: The community identifier
- `period_start` and `period_end`: The date range for this delta
- `timestamp`: When the aggregation was created
- `totals`: Overall usage metrics for the day:
  - `view`: View event statistics
  - `download`: Download event statistics with data volume
- `subcounts`: Detailed breakdowns by:
  - `by_access_rights`: Usage by access rights
  - `by_resource_types`: Usage by resource type
  - `by_licenses`: Usage by license type
  - `by_funders`: Usage by funding organization
  - `by_periodicals`: Usage by journal/periodical
  - `by_languages`: Usage by language
  - `by_subjects`: Usage by subject classification
  - `by_publishers`: Usage by publisher
  - `by_affiliations`: Usage by creator/contributor affiliations
  - `by_countries`: Usage by visitor country
  - `by_referrers`: Usage by referrer
  - `by_file_types`: Usage by file type

These are stored in the index `stats-community-usage-delta`.

#### Usage snapshots

The usage snapshot aggregations provide cumulative usage totals at specific points in time, showing the total usage statistics for the community/instance as of a given date. These aggregations are again based
on the `record-view` and `file-download` events indexed by the `invenio-stats` module. Each usage snapshot
document includes:

- `community_id`: The community identifier
- `snapshot_date`: The date of this snapshot
- `timestamp`: When the aggregation was created
- `totals`: Cumulative usage metrics (similar structure to deltas but cumulative)
- `subcounts`: Cumulative breakdowns by metadata fields, showing total usage across all time rather than daily changes

These are stored in the index `stats-community-usage-snapshot`.

```{note}
An additional temporary index is used during the aggregation process to store working composite documents that
combine usage data with record metadata. This index is not used for any other purpose and is deleted after each
aggregation is complete. The use of a temporary index allows us to avoid keeping large amounts of data in memory
during the aggregation process, when we need to correlate several different dimensions of data taken as a whole.
```

#### Search indices

These indices are managed by index templates that are registered with `invenio-stats` via the
aggregation configurations in the `STATS_AGGREGATIONS` configuration variable. The `invenio-stats` module
ensures that the templates are registered and the indices are created automatically when records are
first indexed.

An additional permanent index `stats-community-events` is used to store the addition and removal of each
record to/from a community. This index also includes information about the record's creation and publication
dates, and deletion status/date. This allows for a more efficient aggregation of the record-based statistics.
Events with a `community_id` of "global" are also used to mark the addition and removal of records to/from the
global repository instance and are particularly useful in accurate aggregation of statistics based on the
record's publication date (which presents problems for a simple range query from the record index) as well as
preserving the correct record counts after a record is deleted.

```{note}
The labels included for each item in a subcount are the English values available in the record metadata. It
is most efficient to include these readable labels in the aggregated documents, rather than looking up the
labels from the record metadata after the aggregation is complete. It was deemed impractical, though, to
include these labels for every available language. Instead, the labels can be translated on the client side
as needed.
```

### Service layer

At the service layer, this module provides:
- aggregation of the statistics on a regular schedule
- service components to record community add/remove events
- a service class to facilitate programmatic access to the statistics data
- helper functions to facilitate setup and maintenance of the statistics indices

#### Scheduled aggregation of statistics

The module implements a comprehensive aggregation system that runs on a regular schedule. Aggregation is performed
by a celery background task that by default runs hourly. The aggregation process is designed to be incremental,
using bookmarks (and the `invenio-stats` bookmarking utilities) to track the most recent successful aggregation for each community and aggregation type.

The actual aggregations are performed by a set of classes registered with the `invenio-stats` module via the `STATS_AGGREGATIONS` configuration variable. These classes are:

- **CommunityRecordsSnapshotCreatedAggregator**: Creates snapshot aggregations based on record creation dates
- **CommunityRecordsSnapshotAddedAggregator**: Creates snapshot aggregations based on when records were added to communities
- **CommunityRecordsSnapshotPublishedAggregator**: Creates snapshot aggregations based on record publication dates
- **CommunityRecordsDeltaCreatedAggregator**: Creates delta aggregations based on record creation dates
- **CommunityRecordsDeltaAddedAggregator**: Creates delta aggregations based on when records were added to communities
- **CommunityRecordsDeltaPublishedAggregator**: Creates delta aggregations based on record publication dates
- **CommunityUsageSnapshotAggregator**: Creates usage snapshot aggregations for view and download events
- **CommunityUsageDeltaAggregator**: Creates usage delta aggregations for view and download events

One additional aggregator class (CommunityEventsIndexAggregator) is registered with the `invenio-stats` module to facilitate registration of the index template for the `stats-community-events` index. This class does not usually actually perform any aggregation, since those events are created by the service components described below. It is
only called by the utility service method that sets up the initial indexed events for an existing InvenioRDM
instance.

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

- **Index template registration**: Functions to ensure proper registration of Elasticsearch index templates with the `invenio-stats` module
- **Event index maintenance**: Utilities for updating community events when records are modified, deleted, or restored
- **Deletion field management**: Functions to properly mark events as deleted when records are removed from the system
- **Index cleanup**: Tools for managing temporary indices used during aggregation processes
- **Configuration validation**: Helper functions to verify that the statistics infrastructure is properly configured

These utilities ensure that the statistics system remains consistent and accurate as the underlying data changes, and provide administrators with tools to maintain the system over time.

### Presentation layer

At the presentation layer, this module provides:
- Jinja2 templates and macros to display dynamic and configurable React-based statistics dashboards
- API queries to retrieve the aggregated statistics data

#### Dashboard templates

#### API queries

The module exposes the aggregated stats at the `/api/stats` endpoint managed by the `invenio-stats` module.




## Installation

```bash
pip install invenio-stats-dashboard
```

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

### Layout and components

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
                            {"component": "AccessRightsTable", "width": 8},
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


All record statistics should be presentable either for individual versions or for parents (all versions at once).

Time series data is very expensive to compute for large collections or for an entire instance. This cost is magnified if we want to cross-reference multiple time-series. So we pre-generate aggregated daily totals in search indices. One document is generated for each community for each day. If an instance has 10000 communities, this means 10000 documents per day. If we want to store 10 years of data, this means 10000 * 365 * 10 = 36_500_000 documents. To ensure the indices remain a manageable size (even for very large instances), we use separate annual indices. These are then linked by a common alias to facilitate easy searching across all years.

** visit counts for community landing page **

## Search indices for statistics

**Assume that STATS_REGISTER_INDEX_TEMPLATES is set to True.**

### stats-community-contents-snapshot

```json
{
  "timestamp": "2024-01-01T00:00:00",
  "community_id": "abcd",
  "snapshot_date": "2024-01-01",
  "total_records": {
    "metadata_only": 100,
    "with_files": 200,
  },
  "total_parents": {
    "metadata_only": 100,
    "with_files": 200,
  },
  "total_files": {
    "file_count": 100,
    "data_volume": 200.0,
  },
  "total_uploaders": 100,
  "subcounts": {
    "all_resource_types": [
      {
        "id": "123",
        "label": {"lang": "en", "value": "Resource Type 1"},
        "records": {
          "metadata_only": 100,
          "with_files": 200,
        },
        "parents": {
          "metadata_only": 100,
          "with_files": 200,
        },
        "files": {
          "file_count": 100,
          "data_volume": 200.0,
        },
      },
    ],
    "all_access_rights": [
      {
        "id": "123",
        "label": {"lang": "en", "value": "Access Right 1"},
        "records": {
          "metadata_only": 100,
          "with_files": 200,
        },
        "parents": {
          "metadata_only": 100,
          "with_files": 200,
        },
        "files": {
          "file_count": 100,
          "data_volume": 200.0,
        },
      },
    ],
    "all_languages": [],
    "all_licenses": [],
    "top_affiliations_creator": [],
    "top_affiliations_contributor": [],
    "top_funders": [],
    "top_subjects": [],
    "top_publishers": [],
    "top_periodicals": [],
    "top_keywords": [],
  },
}
```

### stats-community-contents-delta

```json
{
  "timestamp": "2025-01-01T00:00:00",
  "community_id": "123",
  "period_start": "2025-01-01T00:00:00",
  "period_end": "2025-01-01T23:59:59",
  "records_added": 100,
  "records_removed": 10,
  "parents_added": 10,
  "parents_removed": 10,
  "uploaders": 10,
  "subcounts": {
    "by_resource_type": [
      {
        "id": "textDocument-journalArticle",
        "label": {"en": "Journal Article"},
        "records": {
          "added": {
            "metadata_only": 50,
            "with_files": 50,
          },
          "removed": {
            "metadata_only": 5,
            "with_files": 5,
          },
        },
        "parents": {
          "added": {
            "metadata_only": 5,
            "with_files": 5,
          },
          "removed": {
            "metadata_only": 1,
            "with_files": 1,
          },
        },
        "files": {
          "added": {
            "file_count": 50,
            "data_volume": 100.0,
          },
          "removed": {
            "file_count": 5,
            "data_volume": 10.0,
          },
        },
      },
    ],
    "by_access_right": [
      {
        "id": "open",
        "label": {"en": "Open Access"},
        "records": {
          "added": {
            "metadata_only": 50,
            "with_files": 50,
          },
          "removed": {
            "metadata_only": 5,
            "with_files": 5,
          },
        },
        "parents": {
          "added": {
            "metadata_only": 5,
            "with_files": 5,
          },
          "removed": {
            "metadata_only": 1,
            "with_files": 1,
          },
        },
        "files": {
          "added": {
            "file_count": 50,
            "data_volume": 100.0,
          },
          "removed": {
            "file_count": 5,
            "data_volume": 10.0,
          },
        },
      },
    ],
    "by_language": [
      {
        "id": "en",
        "label": {"en": "English"},
        "records": {
          "added": {
            "metadata_only": 50,
            "with_files": 50,
          },
          "removed": {
            "metadata_only": 5,
            "with_files": 5,
          },
        },
        "parents": {
          "added": {
            "metadata_only": 5,
            "with_files": 5,
          },
          "removed": {
            "metadata_only": 1,
            "with_files": 1,
          },
        },
        "files": {
          "added": {
            "file_count": 50,
            "data_volume": 100.0,
          },
          "removed": {
            "file_count": 5,
            "data_volume": 10.0,
          },
        },
      },
    ],
    "by_affiliation_creator": [
      {
        "id": "University of California, Berkeley",
        "label": "University of California, Berkeley",
        "records": {
          "added": {
            "metadata_only": 50,
            "with_files": 50,
          },
          "removed": {
            "metadata_only": 5,
            "with_files": 5,
          },
        },
        "parents": {
          "added": {
            "metadata_only": 5,
            "with_files": 5,
          },
          "removed": {
            "metadata_only": 1,
            "with_files": 1,
          },
        },
        "files": {
          "added": {
            "file_count": 50,
            "data_volume": 100.0,
          },
          "removed": {
            "file_count": 5,
            "data_volume": 10.0,
          },
        },
      },
    ],
    "by_funder": [
      {
        "id": "National Science Foundation",
        "label": "National Science Foundation",
        "records": {
          "added": {
            "metadata_only": 50,
            "with_files": 50,
          },
          "removed": {
            "metadata_only": 5,
            "with_files": 5,
          },
        },
        "parents": {
          "added": {
            "metadata_only": 5,
            "with_files": 5,
          },
          "removed": {
            "metadata_only": 1,
            "with_files": 1,
          },
        },
        "files": {
          "added": {
            "file_count": 50,
            "data_volume": 100.0,
          },
          "removed": {
            "file_count": 5,
            "data_volume": 10.0,
          },
        },
      },
    ],
    "by_subject": [
      {
        "id": "123",
        "label": "Subject 1",
        "records": {
          "added": {
            "metadata_only": 50,
            "with_files": 50,
          },
          "removed": {
            "metadata_only": 5,
            "with_files": 5,
          },
        },
        "parents": {
          "added": {
            "metadata_only": 5,
            "with_files": 5,
          },
          "removed": {
            "metadata_only": 1,
            "with_files": 1,
          },
        },
        "files": {
          "added": {
            "file_count": 50,
            "data_volume": 100.0,
          },
          "removed": {
            "file_count": 5,
            "data_volume": 10.0,
          },
        },
      },
    ],
    "by_publisher": [
      {
        "id": "University of California Press",
        "label": "University of California Press",
        "records": {
          "added": {
            "metadata_only": 50,
            "with_files": 50,
          },
          "removed": {
            "metadata_only": 5,
            "with_files": 5,
          },
        },
        "parents": {
          "added": {
            "metadata_only": 5,
            "with_files": 5,
          },
          "removed": {
            "metadata_only": 1,
            "with_files": 1,
          },
        },
        "files": {
          "added": {
            "file_count": 50,
            "data_volume": 100.0,
          },
          "removed": {
            "file_count": 5,
            "data_volume": 10.0,
          },
        },
      },
    ],
    "by_periodical": [
      {
        "id": "Journal of Research",
        "label": "Journal of Research",
        "records": {
          "added": {
            "metadata_only": 50,
            "with_files": 50,
          },
          "removed": {
            "metadata_only": 5,
            "with_files": 5,
          },
        },
        "parents": {
          "added": {
            "metadata_only": 5,
            "with_files": 5,
          },
          "removed": {
            "metadata_only": 1,
            "with_files": 1,
          },
        },
        "files": {
          "added": {
            "file_count": 50,
            "data_volume": 100.0,
          },
          "removed": {
            "file_count": 5,
            "data_volume": 10.0,
          },
        },
      },
    ],
    "by_file_type": [
      {
        "id": "pdf",
        "label": "PDF",
        "records": {
          "added": {
            "metadata_only": 0,
            "with_files": 50,
          },
          "removed": {
            "metadata_only": 0,
            "with_files": 5,
          },
        },
        "parents": {
          "added": {
            "metadata_only": 0,
            "with_files": 5,
          },
          "removed": {
            "metadata_only": 0,
            "with_files": 1,
          },
        },
        "files": {
          "added": {
            "file_count": 50,
            "data_volume": 100.0,
          },
          "removed": {
            "file_count": 5,
            "data_volume": 10.0,
          },
        },
      },
    ],
  },
}
```
```

### stats-community-usage-delta

```json
{
  "timestamp": "2025-01-01T00:00:00",
  "community_id": "123",
  "period_start": "2025-01-01T00:00:00",
  "period_end": "2025-01-01T23:59:59",
  "totals": {
    "view": {
      "total_events": 150,
      "unique_visitors": 45,
      "unique_records": 25,
      "unique_parents": 20,
    },
    "download": {
      "total_events": 75,
      "unique_visitors": 30,
      "unique_records": 15,
      "unique_parents": 12,
      "unique_files": 20,
      "total_volume": 5000000.0,
    },
  },
  "subcounts": {
    "by_access_rights": [
      {
        "id": "open",
        "label": "Open Access",
        "view": {
          "total_events": 100,
          "unique_visitors": 30,
          "unique_records": 20,
          "unique_parents": 15,
        },
        "download": {
          "total_events": 50,
          "unique_visitors": 20,
          "unique_records": 10,
          "unique_parents": 8,
          "unique_files": 15,
          "total_volume": 3000000.0,
        },
      },
    ],
    "by_resource_types": [
      {
        "id": "textDocument-journalArticle",
        "label": "Journal Article",
        "view": {
          "total_events": 80,
          "unique_visitors": 25,
          "unique_records": 15,
          "unique_parents": 12,
        },
        "download": {
          "total_events": 40,
          "unique_visitors": 15,
          "unique_records": 8,
          "unique_parents": 6,
          "unique_files": 12,
          "total_volume": 2000000.0,
        },
      },
    ],
    "by_languages": [
      {
        "id": "en",
        "label": "English",
        "view": {
          "total_events": 120,
          "unique_visitors": 35,
          "unique_records": 20,
          "unique_parents": 16,
        },
        "download": {
          "total_events": 60,
          "unique_visitors": 25,
          "unique_records": 12,
          "unique_parents": 10,
          "unique_files": 18,
          "total_volume": 4000000.0,
        },
      },
    ],
    "by_subjects": [
      {
        "id": "http://id.worldcat.org/fast/1234567",
        "label": "Computer Science",
        "view": {
          "total_events": 50,
          "unique_visitors": 15,
          "unique_records": 10,
          "unique_parents": 8,
        },
        "download": {
          "total_events": 25,
          "unique_visitors": 10,
          "unique_records": 5,
          "unique_parents": 4,
          "unique_files": 8,
          "total_volume": 1500000.0,
        },
      },
    ],
    "by_countries": [
      {
        "id": "US",
        "label": "United States",
        "view": {
          "total_events": 80,
          "unique_visitors": 25,
          "unique_records": 15,
          "unique_parents": 12,
        },
        "download": {
          "total_events": 40,
          "unique_visitors": 15,
          "unique_records": 8,
          "unique_parents": 6,
          "unique_files": 12,
          "total_volume": 2000000.0,
        },
      },
    ],
    "by_file_types": [
      {
        "id": "pdf",
        "label": "PDF",
        "view": {
          "total_events": 60,
          "unique_visitors": 20,
          "unique_records": 12,
          "unique_parents": 10,
        },
        "download": {
          "total_events": 30,
          "unique_visitors": 12,
          "unique_records": 6,
          "unique_parents": 5,
          "unique_files": 10,
          "total_volume": 1500000.0,
        },
      },
    ],
  },
}
```

### stats-community-usage-snapshot

```json
{
  "timestamp": "2025-01-01T00:00:00",
  "community_id": "123",
  "snapshot_date": "2025-01-01",
  "totals": {
    "view": {
      "total_events": 1500,
      "unique_visitors": 450,
      "unique_records": 250,
      "unique_parents": 200,
    },
    "download": {
      "total_events": 750,
      "unique_visitors": 300,
      "unique_records": 150,
      "unique_parents": 120,
      "unique_files": 200,
      "total_volume": 50000000.0,
    },
  },
  "subcounts": {
    "all_resource_types": [
      {
        "id": "textDocument-journalArticle",
        "label": "Journal Article",
        "view": {
          "total_events": 800,
          "unique_visitors": 250,
          "unique_records": 150,
          "unique_parents": 120,
        },
        "download": {
          "total_events": 400,
          "unique_visitors": 150,
          "unique_records": 80,
          "unique_parents": 60,
          "unique_files": 120,
          "total_volume": 20000000.0,
        },
      },
    ],
    "all_access_rights": [
      {
        "id": "open",
        "label": "Open Access",
        "view": {
          "total_events": 1000,
          "unique_visitors": 300,
          "unique_records": 200,
          "unique_parents": 150,
        },
        "download": {
          "total_events": 500,
          "unique_visitors": 200,
          "unique_records": 100,
          "unique_parents": 80,
          "unique_files": 150,
          "total_volume": 30000000.0,
        },
      },
    ],
    "all_languages": [
      {
        "id": "en",
        "label": "English",
        "view": {
          "total_events": 1200,
          "unique_visitors": 350,
          "unique_records": 200,
          "unique_parents": 160,
        },
        "download": {
          "total_events": 600,
          "unique_visitors": 250,
          "unique_records": 120,
          "unique_parents": 100,
          "unique_files": 180,
          "total_volume": 40000000.0,
        },
      },
    ],
    "all_file_types": [
      {
        "id": "pdf",
        "label": "PDF",
        "view": {
          "total_events": 600,
          "unique_visitors": 200,
          "unique_records": 120,
          "unique_parents": 100,
        },
        "download": {
          "total_events": 300,
          "unique_visitors": 120,
          "unique_records": 60,
          "unique_parents": 50,
          "unique_files": 100,
          "total_volume": 15000000.0,
        },
      },
    ],
    "top_subjects": [
      {
        "id": "http://id.worldcat.org/fast/1234567",
        "label": "Computer Science",
        "view": {
          "total_events": 500,
          "unique_visitors": 150,
          "unique_records": 100,
          "unique_parents": 80,
        },
        "download": {
          "total_events": 250,
          "unique_visitors": 100,
          "unique_records": 50,
          "unique_parents": 40,
          "unique_files": 80,
          "total_volume": 15000000.0,
        },
      },
    ],
    "top_publishers": [
      {
        "id": "University of California Press",
        "label": "University of California Press",
        "view": {
          "total_events": 300,
          "unique_visitors": 100,
          "unique_records": 60,
          "unique_parents": 50,
        },
        "download": {
          "total_events": 150,
          "unique_visitors": 60,
          "unique_records": 30,
          "unique_parents": 25,
          "unique_files": 45,
          "total_volume": 9000000.0,
        },
      },
    ],
    "top_countries": [
      {
        "id": "US",
        "label": "United States",
        "view": {
          "total_events": 800,
          "unique_visitors": 250,
          "unique_records": 150,
          "unique_parents": 120,
        },
        "download": {
          "total_events": 400,
          "unique_visitors": 150,
          "unique_records": 80,
          "unique_parents": 60,
          "unique_files": 120,
          "total_volume": 20000000.0,
        },
      },
    ],
  },
}


## Development

```bash
# Install development dependencies
pip install -e ".[all]"

# Run tests
pytest
```