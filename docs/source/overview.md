# Overview

## Features

The `invenio-stats-dashboard` extension provides global and community statistics recording and reporting for an InvenioRDM instance. It provides responsive, performant, and highly configurable dashboards for viewing statistics. Separate dashboards are provided for the InvenioRDM instance as a whole as well as for each of its communities.

### Statistic for display

The extension makes available time-series data for each community and the instance as a whole, including:

- running cumulative totals and delta changes for a given date range
  - number of records and files
  - file data volume
  - number of unique uploaders
  - number of unique views and downloads
- subcounts for each metric broken down by a configurable list of metadata fields like
  - resource type
  - access status (open, restricted, etc.)
  - language
  - creator/contributor affiliation
  - funding organization
  - subject heading
  - publisher name
  - periodical title
  - file type
- subcounts for view/download metrics broken down by visitor country

## Usable

- Downloadable reports in JSON, CSV, XML, or XLSX formats.
- CLI tooling to aid with setup and maintenance.

### Configurable

Some additional features make the dashboards adaptable to a wide variety of InvenioRDM instances:

- Opt-in community dashboards
  - Community dashboards can be enabled for all communities centrally, or they can be enabled individually via controls on each community's settings page.
- Fully customizable dashboard layouts
  - Dashboard pages, page layouts, and included widgets are configurable via a config object.
- Customizable metadata subcounts
  - Determine which metadata fields to make available for statistics subcounts via a config variable during setup.
- Enable either the global instance dashboard, or the community dashboards, or both.

### Performant

- Only pre-calculates the statistics you need
  - No calculation for communities with their dashboard turned off
- Server-side pre-caching of JSON responses for display
  - Responses are calculated once and cached in a dedicated Redis store.
- Streamlined JSON for front end display
  - Pre-transformed JSON responses include only the values needed by the UI widgets configured for your dashboards.
- Client-side caching of api responses

## Architecture

The extension provides:

```{eval-rst}
+---------------------+--------------------------------------------------------+
| **Layer**           | **Component**                                          |
+=====================+========================================================+
| data-layer          | storage of pre-aggregated statistics (daily cumulative |
|                     | snapshots and deltas) for each community and for the   |
|                     | instance as a whole                                    |
|                     |                                                        |
|                     | - search templates and indices to store pre-compiled   |
|                     |   stats                                                |
|                     | - search template and indices to store log of record   |
|                     |   additions to/removals from communities               |
|                     | - redis store to hold pre-transformed JSON responses   |
|                     |   for client requests                                  |
+---------------------+--------------------------------------------------------+
| service-layer       | aggregation of the community and global statistics on  |
|                     | a regular schedule (hourly by default)                 |
|                     |                                                        |
|                     | - configurable aggregators to pre-compile aggregated   |
|                     |   stats                                                |
|                     | - data transformers to prepare requested statistics    |
|                     |   for chart display or reports (JSON, CSV, XML, XLSX)  |
|                     | - scheduled celery tasks for pre-calculating           |
|                     |   aggregated stats                                     |
|                     | - scheduled celery tasks for pre-compiling JSON        |
|                     |   responses for front-end dashboards                   |
|                     | - service components to record record additions to/    |
|                     |   removalfrom communities                              |
+---------------------+--------------------------------------------------------+
| presentation-layer  | Configurable dashboards as well as api endpoints for   |
|                     | community and instance stats data                      |
|                     |                                                        |
|                     | - API access to the aggregated daily statistics via the|
|                     |   `/api/stats-dashboard` endpoint                      |
|                     | - API access to pre-compiled JSON responses suitable   |
|                     |   for chart display                                    |
|                     | - API access to reports in JSON, CSV, XML, or Excel    |
|                     |   formats                                              |
|                     | - Jinja2 templates to display React-based global and   |
|                     |   community statistics dashboards                      |
|                     | - menu configuration options to add the global         |
|                     |   statistics dashboard to site-wide navigation         |
+---------------------+--------------------------------------------------------+
| configuration       | full configuration control, including variables for    |
|                     |                                                        |
|                     | - API and ui routes                                    |
|                     | - Global and community dashboard layouts and widgets   |
|                     |   (configurable by community)                          |
|                     | - Metadata breakdowns for stats aggregations           |
+---------------------+--------------------------------------------------------+
```

## Setup

Much of the setup for invenio-stats-dashboard is handled automatically once the extension has been installed. But a few tasks need to be performed manually via CLI commands, and users may wish to configure various aspects of the package. See the (setup)[./setup.md] and (configuration)[./configuration.md] sections for details.

## FAQs

### Do I need to enable all of the different kinds of statistics?

No. ???
