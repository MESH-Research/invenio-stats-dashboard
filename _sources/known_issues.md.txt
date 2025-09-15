# Known Issues

## as of 2025-09-12:

- the service component calls require PRs to be merged in invenio-requests (https://github.com/inveniosoftware/invenio-requests/pull/457) and invenio-rdm-records (https://github.com/inveniosoftware/invenio-rdm-records/pull/2002). These PRs are both currently in review. In development I'm using forked versions of these packages with the changes merged in.
    - in the meantime, a provided bash script is provided to patch the required files in your local site-packages directory. See the [setup](./setup.md) section for details.
- client-side transformation of the queried API data is broken while we refactor it to use the configurable subcounts
- the `-background` versions of CLI commands are working but not creating the correct PID files, so the `status` and `cancel` sub-commands are not working correctly. We need to manage the background processes manually for now. But the process logs are still being captured correctly in the /tmp folder.
- the record delta aggregator is not working properly when using the publication date as the basis for the aggregation. It is missing records published before the first record was created. This also throws off the record snapshot aggregator when using the publication date as the basis for the aggregation.
- Not a problem, but need to clarify that the "affiliations" subcounts count the *number of creators/contributors* to records with the affiliation (i.e., the number of "contributions"), not the *number of records* with the affiliation.
