# Known Issues

as of 2025-09-30

### Setup

- the initial catch-up aggregation is **not yet automatically triggered**.
    - It can be performed manually via a series of CLI commands. See the [CLI Commands](./cli.md) section for details.
- catch-up aggregation will be **very slow for large instances**.
    - We need to speed this up by reducing the number of queries made per aggregation document.
- **initial server-side data series caching** needs to be more graceful.
    - Currently each request for a community's data series will be extremely slow (> 2 minutes). After that the dashboard will load quickly from the server-side cache.
    - We need a scheduled task to update the cache.
    - We need automated creation of the cache documents after setup, immediately after the initial catch-up aggregation.

### UI

- Selecting of **date ranges beyond the current year** is not working.
    - We need to make incremental API calls in fixed 1-year chunks to take advantage of the server-side data series caching.
- **Quarter granularity** is not working properly.
- Some subcount views are **displaying too many items** to be readable.
- Ring charts with a **large "other" category** are problematic.
- The **stacked bar charts** are not very readable for some data sets.
- The **map view** is not displaying the data properly.
- Some bar charts are displaying with **overlapping regions** in multi-series views.
- The **y-axis labels** are sometimes shifted left out of view.
- The **date range picker** doesn't have a custom range option yet.
- The **report download UI** needs to be finished.
- The **mobile** view needs to be improved
    - especially for the charts

### Reporting

- **Download of data series via the UI** is not yet working.
    - The non-JSON serializers aren't finished yet.
    - But the JSON download via the API is working. See the [API Requests](./api_requests.md) section for details.

### Dependencies

- the service component calls **require PRs to be merged**
    - invenio-requests (https://github.com/inveniosoftware/invenio-requests/pull/457)
    - invenio-rdm-records (https://github.com/inveniosoftware/invenio-rdm-records/pull/2002)
    - These PRs are both approved and will be merged soon. In the meantime, a provided bash script is provided to patch the required files in your local site-packages directory. See the [setup](./setup.md) section for details.

### CLI Commands

- the `-background` versions of CLI commands are working but not creating the correct PID files, so the **`status` and `cancel` sub-commands are not working correctly**.
    - We need to manage the background processes manually for now. But the process logs are still being captured correctly in the /tmp folder.

### Aggregations

- the record delta aggregator is not working properly when using the **publication date as the basis** for the aggregation.
    - It is missing records published before the first record was created. This also throws off the record snapshot aggregator when using the publication date as the basis for the aggregation.
- Not a problem, but need to clarify that the "affiliations" subcounts count the *number of creators/contributors* to records with the affiliation (i.e., the number of "contributions"), not the *number of records* with the affiliation.

### Translations

- The translations haven't been added yet.

### Documentation

- The documentation is not up to date with the latest changes to API requests, CLI commands, and the server-side caching setup.
    - This will be remedied shortly.