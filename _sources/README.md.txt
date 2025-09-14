# Invenio Stats Dashboard

**Pre-alpha version. Not ready for production use. Some things currently don't work!**

Copyright 2025, MESH Research

Licensed under the MIT License. See LICENSE file for details.

## Current Status

See the [Known Issues](known_issues.html) and [TODOs](todos.html) pages for current known issues and planned work.

## Overview

The `invenio-stats-dashboard` extension provides global and community statistics recording and reporting for an InvenioRDM instance. It provides a highly configurable dashboard for viewing and analyzing statistics for the instance and each of its communities. The extension makes available time-series data for each community and the instance as a whole, including:

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
- subcounts for view/download metrics broken down by
    - referrer domain
    - visitor country

The extension provides:

| Layer | Component |
|-------|-----------|
| data-layer | storage of pre-aggregated statistics (daily cumulative snapshots and deltas) for each community and for the instance as a whole |
| service-layer | aggregation of the community and global statistics on a regular schedule, along with service components to record community add/remove events |
| presentation-layer | API access to the aggregated daily statistics via the `/api/stats` endpoint |
| | Jinja2 templates to display React-based global and community statistics dashboards |
| | menu configuration options to add the global statistics dashboard to site-wide navigation |

Most initial setup of the statistics infrastructure is handled automatically when the module is installed. In existing InvenioRDM instances, this includes not only setup of the necessary search indices, but also:
- migration of historical indexed usage events to the expanded mappings with added community and record metadata
- initial indexing of the community membership events for existing records (when a record is added to or removed from a community)
- progressive aggregation of historical statistics
This initial setup is handled by the background tasks that run on a regular schedule to aggregate the statistics. If the instance has a large number of records, this may up to a day or more to complete.

The module also provides a set of utility classes and functions, along with cli commands, to facilitate setup and maintenance of the statistics infrastructure.
