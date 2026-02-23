# Known Issues

as of 2026-02-19

### UI

- Ring charts with a **large "other" category** are problematic.
- The **map view** is not displaying the data properly.
- The **mobile** view needs to be improved
  - especially for the charts

### Dependencies

- The service component calls depend on code changes in InvenioRDM version 13.
  - invenio-requests (https://github.com/inveniosoftware/invenio-requests/pull/457)
  - invenio-rdm-records (https://github.com/inveniosoftware/invenio-rdm-records/pull/2002)
  - For version 12 instances without these changes, a provided bash script will patch the required files in your local site-packages directory. See the [setup](./setup.md) section for details.

### CLI Commands

- the `-background` versions of CLI commands are working but not creating the correct PID files, so the **`status` and `cancel` sub-commands are not working correctly**.
  - We need to manage the background processes manually for now. But the process logs are still being captured correctly in the /tmp folder.

### Stats Index Migration

- The index migration operation currently will **not** work to move from one subcount configuration (in COMMUNITY*STATS_SUBCOUNTS) to another. Running the `community-stats usage-events migrate` command after a migration has been completed will not change the metadata included in already-migrated documents. If the old (pre v2.0.0) indices have already been deleted, the command will be a no-op. Even with the `--fresh-start` flag set, and the pre v2.0.0 indices still in place, the changed metadata subcount configuration will only be applied to events \_in the original indices*. They will not be applied to additional events recorded _after_ the first migration. The plan is to provide a re-migration path in future.

### Country statistics

- Many view records currently lack country information. This needs to be resolved in order for country statistics to be meaningful.

### Aggregations

- The queries of the `stats-community-events` index in the delta aggregators is currently _not_ paginated and will miss community add/remove events above 10k total. **This needs immediate attention.**
- Aggregators and views that use record publication or creation as the time basis are currently deactivated and may or may not be reimplemented.
  - Publication-date-based aggregations pose a particular challenge because publication dates are often back-dated prior to the current date. This would require potentially costly re-aggregation of select previous aggregations.
- Not a problem, but need to clarify that the "affiliations" subcounts count the _number of creators/contributors_ to records with the affiliation (i.e., the number of "contributions"), not the _number of records_ with the affiliation.
- Record snapshot aggregators should use a streamed scan search and running cached totals to handle the top- subcount aggregations, like with the usage snapshot aggregator (to reduce possibility of OOM errors).

### JSON Response Caching

- Currently no regular sanity checks or cleanup of cached responses.
- Currently no automated re-caching when a community's dashboard layout changes

### Translations

- The translations haven't been added yet.

### Documentation

- The documentation is not up to date with the latest changes to API requests, CLI commands, and the server-side caching setup.
  - This will be remedied shortly.
