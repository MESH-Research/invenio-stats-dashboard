# Invenio Stats Dashboard

{bdg-warning}`Pre-alpha`

**Pre-alpha version. Not ready for production use. Some things currently don't work!**

Copyright 2025, MESH Research

Licensed under the MIT License. See LICENSE file for details.

{bdg-dark}`Code style: black`

## Current Known Issues

- the `-background` versions of CLI commands are working but not creating the correct PID files, so the `status` and `cancel` sub-commands are not working correctly. We need to manage the background processes manually for now. But the process logs are still being captured correctly in the /tmp folder.
- the record delta aggregator is not working properly when using the publication date as the basis for the aggregation. It is missing records published before the first record was created. This also throws off the record snapshot aggregator when using the publication date as the basis for the aggregation.
- Not a problem, but need to clarify that the "affiliations" subcounts count the *number of creators/contributors* to records with the affiliation (i.e., the number of "contributions"), not the *number of records* with the affiliation.

## TODOs

- [ ] decide whether to rename the package `invenio-community-stats`
- [x] add config flag to switch UI between test data and production data
- [ ] testing
  - [ ] move all tests from centralized KCWorks test suite into this package
  - [ ] fix failing tests
  - [ ] expand test coverage
- [ ] search indexing
  - [ ] add dynamic creation of index templates based on subcount configurations
  - [ ] make view and download event factories use the subcounts configuration
- [ ] aggregation
  - [x] refactor CommunityUsageSnapshotAggregator for the enriched event document structure
  - [x] ensure CommunityUsageDeltaAggregator can handle large volumes of records gracefully (paginate the query, batch the aggregations)
  - [x] get tests for aggregator classes working
  - [ ] get tests for queries working with refactored code
  - [ ] set up a check in aggregator classes to ensure that view/download event migration has been completed before running the aggregator tasks
  - [ ] set up automatic triggering of the startup tasks (index community events, migrate usage events) when the aggregators first run
  - [ ] add opensearch health and memory usage checks to the aggregator classes (as in the reindexing service) and quit out gracefully if necessary
  - [ ] evaluate the viability of the "published" record aggregators (currently not working because of inherent issue of published dates being retroactive)
- [ ] UI components
  - [x] add proper loading states to the dashboard components
  - [x] add an updated timestamp to the dashboard views
  - [x] fix state problems with chart views
  - [ ] add custom date range picker to the dashboard views
  - [ ] add ReactOverridable support for each of the React components
  - [ ] add mechanism for adding custom React components to the dashboard views (entry point providing file paths and component labels, to be imported in components_map.js?)
  - [ ] evaluate whether additional default components are needed
  - [ ] add `invenio-communities` custom field to provide per-community configuration of the dashboard layout
- [ ] client-side data handling
  - [ ] add client-side caching of the stats data to display while new data is loading (current implementation with IndexedDB is not working)
  - [ ] update client-side data transformer to use the configurable subcounts
- [ ] UI theming
  - [x] move default CSS into this package
  - [x] finish basic theming of the global dashboard view
  - [ ] harmonize default CSS with InvenioRDM defaults
  - [ ] improve mobile responsiveness of the dashboard views
- [ ] API requests
  - [ ] implement security policy for API queries
- [ ] reporting
  - [ ] implement report generation (via API request? via email? generated client-side?)
  - [ ] enable report download from dashboard widget
- [ ] improve documentation
