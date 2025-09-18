# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
#
# Copyright (C) 2023-2024 Mesh Research
#
# invenio-stats-dashboard is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""CLI commands for destroying search indices created by invenio-stats-dashboard."""

import sys

import click
from flask.cli import with_appcontext
from invenio_search.cli import abort_if_false
from invenio_search.proxies import current_search_client

from .core_cli import check_stats_enabled


def find_matching_indices(index_patterns: list[str]) -> list[str]:
    """Find all indices that match the specified patterns.

    Args:
        index_patterns (list[str]): The list of index patterns to match.

    Returns:
        list[str]: A list of matching index names.
    """
    all_matching_indices = []

    for pattern in index_patterns:
        try:
            indices_response = current_search_client.indices.get(index=pattern)
            matching_indices = list(indices_response.keys())
            all_matching_indices.extend(matching_indices)

        except Exception as e:
            click.echo(
                f"Error finding indices matching pattern {pattern}: {e}",
                err=True,
            )

    return sorted(all_matching_indices)


def delete_indices_with_progress(
    indices: list[str], ignore: list[int] | None = None
) -> tuple[list[str], list[str]]:
    """Delete the specified indices with a progress bar.

    Args:
        indices (list[str]): The list of index names to delete.
        ignore (list[int] | None, optional): The list of error codes to ignore.
            Defaults to None.

    Returns:
        tuple[list[str], list[str]]: A tuple of (succeeded_indices, failed_indices).
    """
    succeeded_indices = []
    failed_indices = []

    if not indices:
        return succeeded_indices, failed_indices

    with click.progressbar(
        indices,
        label="Deleting indices...",
        show_percent=True,
        show_pos=True,
    ) as bar:
        for index_name in bar:
            bar.label = f"Deleting {index_name}"
            try:
                response = current_search_client.indices.delete(
                    index=index_name,
                    ignore=ignore,
                )

                if (
                    response
                    and "error" not in response
                    and response.get("acknowledged")
                ):
                    succeeded_indices.append(index_name)
                else:
                    failed_indices.append(index_name)

            except Exception as e:
                failed_indices.append(index_name)
                click.echo(f"\nError deleting index {index_name}: {e}", err=True)

    return succeeded_indices, failed_indices


STATS_DASHBOARD_INDICES = [
    "*stats-community-events*",
    "*stats-community-records-delta-created*",
    "*stats-community-records-delta-published*",
    "*stats-community-records-delta-added*",
    "*stats-community-records-snapshot-created*",
    "*stats-community-records-snapshot-published*",
    "*stats-community-records-snapshot-added*",
    "*stats-community-usage-delta*",
    "*stats-community-usage-snapshot*",
    "*events-stats-record-view-*-v2.0.0",
    "*events-stats-file-download-*-v2.0.0",
]


@click.command(name="destroy-indices")
@click.option(
    "--yes-i-know",
    is_flag=True,
    callback=abort_if_false,
    expose_value=False,
    prompt=(
        "Do you know that you are going to destroy all "
        "invenio-stats-dashboard indices?"
    ),
    help="Skip the confirmation prompt (required for non-interactive use).",
)
@with_appcontext
def destroy_indices_command():
    """Destroy all search indices created by the invenio-stats-dashboard package.

    This command permanently deletes all search indices created by the
    invenio-stats-dashboard package from OpenSearch.

    WARNING:
    THIS COMMAND WILL WIPE ALL STATISTICS DATA STORED IN OPENSEARCH/ELASTICSEARCH.
    ONLY RUN THIS WHEN YOU KNOW WHAT YOU ARE DOING. Statistics data is stored in
    the search engine and is not persisted in the database.

    Indices to be destroyed:

    \b
    - Community events index: stats-community-events-*
    - Aggregation indices for community statistics:
      - stats-community-records-delta-* (created, published, added)
      - stats-community-records-snapshot-* (created, published, added)
      - stats-community-usage-delta-*
      - stats-community-usage-snapshot-*
    - Enriched/migrated view and download indices (v2.0.0 versions only):
      - events-stats-record-view-*-v2.0.0
      - events-stats-file-download-*-v2.0.0

    Note:

    \b
    This command will NOT destroy:
    - View and download events in non-migrated indices (original usage events)
    - Per-record view and download aggregations used for individual record stats

    However, if the original view/download indices have been deleted after
    migration, the raw event data will be lost.
    """
    check_stats_enabled()

    click.secho(
        "Destroying invenio-stats-dashboard indices...",
        fg="red",
        bold=True,
        file=sys.stderr,
    )

    click.echo("Searching for matching indices...")
    matching_indices = find_matching_indices(STATS_DASHBOARD_INDICES)

    if not matching_indices:
        click.echo("No matching indices found to delete.")
        return

    click.echo(f"Found {len(matching_indices)} indices to delete:")
    for index_name in matching_indices:
        click.echo(f"  - {index_name}")

    succeeded_indices, failed_indices = delete_indices_with_progress(
        matching_indices, ignore=[400, 404]
    )

    if succeeded_indices:
        click.echo(f"\n✅ Successfully deleted {len(succeeded_indices)} indices:")
        for index_name in succeeded_indices:
            click.echo(f"  - {index_name}")

    if failed_indices:
        click.echo(f"\n⚠️  Failed to delete {len(failed_indices)} indices:")
        for index_name in failed_indices:
            click.echo(f"  - {index_name}")
        click.echo("  This may be because they don't exist or are already deleted.")

    if not succeeded_indices and not failed_indices:
        click.echo("\n  No matching indices found to delete.")

    click.echo("\n  You may need to re-run aggregation commands to rebuild statistics.")
