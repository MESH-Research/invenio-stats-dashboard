# Overview

## Features

The `invenio-stats-dashboard` extension provides global and community statistics recording and reporting for an InvenioRDM instance. It provides responsive, performant, and highly configurable dashboards for viewing statistics. Separate dashboards are provided for the InvenioRDM instance as a whole as well as for each of its communities. The extension makes available time-series data for each community and the instance as a whole, including:

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

For a new InvenioRDM instance all of the initial setup of the back-end statistics infrastructure is handled automatically when the module is installed. This includes

- registration of automated celery tasks
- registration of new stats search templates
- progressive aggregation of any historical statistics
- pre-preparation of JSON response objects for any historical statistics

This initial setup is handled by the background tasks that run on a regular schedule to aggregate the statistics. If the instance has a large number of records and/or communities, this may up to a day or more to complete.

In existing InvenioRDM instances, two steps needing to be performed first via CLI commands:

- initial indexing of the community add/remove events for existing records
- migration of existing view and download indices to an expanded schema (with added community and record metadata)

The module also provides a set of utility classes and functions, along with cli commands, to facilitate setup and maintenance of the statistics infrastructure.

## FAQs

### Do I need to enable all of the different kinds of statistics?

No. ???
