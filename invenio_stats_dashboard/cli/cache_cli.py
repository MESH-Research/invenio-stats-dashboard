# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
#
# Copyright (C) 2025 Mesh Research
#
# invenio-stats-dashboard is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Cache management CLI commands."""

import json
from pprint import pformat
from typing import Any

import click
from flask import current_app
from flask.cli import with_appcontext
from invenio_access.permissions import system_identity
from invenio_communities.communities.services.results import CommunityListResult
from invenio_communities.proxies import current_communities
from tqdm import tqdm

from ..models.cached_response import CachedResponse
from ..resources.cache_utils import StatsCache
from ..services.cached_response_service import CachedResponseService
from ..tasks.cache_tasks import generate_cached_responses_task
from ..utils.utils import format_age, format_bytes


def check_scheduled_tasks_enabled(command="cache"):
    """Check if scheduled tasks are enabled.

    Raises:
        click.ClickException: If scheduled tasks are disabled.
    """
    if not current_app.config.get(
        "COMMUNITY_STATS_SCHEDULED_CACHE_TASKS_ENABLED", True
    ):
        message = (
            "Community stats scheduled caching tasks are disabled. "
            "Set COMMUNITY_STATS_SCHEDULED_CACHE_TASKS_ENABLED=True to enable "
            "response cache preparation tasks."
        )
        if command == "cache":
            message += (
                " Use --force to bypass this check and run cache preparation directly."
            )
        raise click.ClickException(message)


@click.group(name="cache")
def cache_cli():
    """Cache management commands for statistics data."""
    pass


@cache_cli.command(name="clear-all")
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompt and clear all cache immediately",
)
@click.option(
    "--yes-i-know",
    is_flag=True,
    help="Bypass confirmation prompt",
)
@with_appcontext
def clear_all_cache_command(force, yes_i_know):
    """Clear all cached statistics data.

    This command removes all cached statistics data from Redis. This will
    force all statistics queries to be recalculated on the next request.

    Examples:
    - invenio community-stats cache clear-all
    - invenio community-stats cache clear-all --force
    - invenio community-stats cache clear-all --force --yes-i-know

    Returns:
        None: This is a CLI command function.
    """
    cache = StatsCache()

    if not (force and yes_i_know):
        click.confirm(
            "Are you sure you want to clear all cached statistics data? "
            "This will force recalculation of all statistics on next request.",
            abort=True,
        )

    with click.progressbar(length=1, label="Clearing cache...") as bar:
        success, deleted_count = cache.clear_all()
        bar.update(1)

    if success:
        if deleted_count > 0:
            click.echo(f"✅ Successfully cleared {deleted_count} cache entries")
        else:
            click.echo("ℹ️  No cache entries found to clear")
    else:
        click.echo("❌ Failed to clear cache entries - check Redis connection and logs")
        return 1


@cache_cli.command(name="clear-pattern")
@click.argument("pattern", required=True)
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompt and clear immediately",
)
@with_appcontext
def clear_pattern_cache_command(pattern, force):
    r"""Clear cache entries matching a pattern.

    This command removes all cached statistics entries that match the given
    Redis key pattern. Use with caution as this can delete multiple entries.

    Args:
        pattern: Redis key pattern to match (e.g., "*global*", "*2023*")
        force: Skip confirmation prompt and clear immediately

    Examples:  # noqa:D412

    \b
    - invenio community-stats cache clear-pattern "*global*"
    - invenio community-stats cache clear-pattern "*2023*" --force
    - invenio community-stats cache clear-pattern "*record_delta*"

    Returns:
        None: This is a CLI command function.
    """
    cache = StatsCache()

    # Show what will be cleared
    matching_keys = cache.keys(pattern)

    if not matching_keys:
        click.echo(f"No cache entries found matching pattern: {pattern}")
        return 0

    click.echo(f"Found {len(matching_keys)} cache entries matching pattern: {pattern}")
    for key in matching_keys[:10]:  # Show first 10 keys
        click.echo(f"  {key}")
    if len(matching_keys) > 10:
        click.echo(f"  ... and {len(matching_keys) - 10} more")

    # Confirm before clearing
    if not force:
        if not click.confirm("Do you want to clear these cache entries?"):
            click.echo("Cache clearing cancelled")
            return 0

    # Clear the cache entries
    success, deleted_count = cache.clear_all(pattern)

    if success:
        click.echo(f"Successfully cleared {deleted_count} cache entries")
    else:
        click.echo("❌ Failed to clear cache entries")
        return 1


@cache_cli.command(name="clear-item")
@click.argument("community_id")
@click.argument("stat_name")
@click.option(
    "--start-date",
    type=str,
    help="Start date for the cache entry (YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    type=str,
    help="End date for the cache entry (YYYY-MM-DD)",
)
@click.option(
    "--date-basis",
    type=click.Choice(["added", "created", "published"]),
    default="added",
    help="Date basis for the cache entry",
)
@click.option(
    "--content-type",
    type=str,
    help="Content type for the cache entry",
)
@with_appcontext
def clear_item_cache_command(
    community_id, stat_name, start_date, end_date, date_basis, content_type
):
    r"""Clear a specific cached statistics item.

    This command removes a specific cached statistics entry based on the
    provided parameters. If the exact cache entry is not found, no error
    will be reported.

    Arguments:  #  noqa:D412

    \b
    - community_id: Community ID or "global"
    - stat_name: Name of the statistics query

    Examples:  # noqua:D412

    \b
    - invenio community-stats cache clear-item global record_snapshots
    - invenio community-stats cache clear-item my-community usage_delta \\
      --start-date 2024-01-01
    - invenio community-stats cache clear-item global record_created \\
      --date-basis created

    Returns:
        None: This is a CLI command function.
    """
    cache = StatsCache()

    # Build request_data structure for key generation (matching __init__ structure)
    request_data = {
        "stat": stat_name,
        "params": {
            "community_id": community_id,
            "start_date": start_date or "",
            "end_date": end_date or "",
            "date_basis": date_basis,
        }
    }

    # Generate the cache key to show what will be cleared
    cache_key = CachedResponse.generate_cache_key(
        content_type or "application/json", request_data
    )

    click.echo(f"Clearing cache entry: {cache_key}")

    # Clear the specific cache entry
    success = cache.delete(cache_key)

    if success:
        click.echo("Cache entry cleared successfully")
    else:
        click.echo("❌ Failed to clear cache entry")
        return 1


@cache_cli.command(name="info")
@click.option(
    "--detailed",
    is_flag=True,
    help="Show detailed cache information including Redis stats",
)
@with_appcontext
def cache_info_command(detailed):
    """Show cache information including size and item count.

    This command displays information about the current cache state,
    including the number of cached items, memory usage, and Redis
    configuration details.

    Examples:
    - invenio community-stats cache info
    - invenio community-stats cache info --detailed

    Returns:
        None: This is a CLI command function.
    """
    cache = StatsCache()

    if detailed:
        info = cache.get_cache_info()
        size_info = cache.get_cache_size_info()

        click.echo("Cache Information:")
        click.echo("=" * 50)
        click.echo(pformat(info))
        click.echo("\nCache Size Information:")
        click.echo("=" * 50)
        click.echo(pformat(size_info))
    else:
        size_info = cache.get_cache_size_info()

        if "error" in size_info:
            click.echo(f"❌ Error retrieving cache info: {size_info['error']}")
            return 1

        click.echo("Cache Summary:")
        click.echo("=" * 30)
        click.echo(f"Total items: {size_info['key_count']}")
        click.echo(f"Memory used: {size_info['total_memory_human']}")
        click.echo(f"Cache prefix: {size_info['cache_prefix']}")
        click.echo(f"Last updated: {size_info['timestamp']}")


@cache_cli.command(name="list")
@click.option(
    "--limit",
    type=int,
    default=50,
    help="Maximum number of keys to display (default: 50)",
)
@click.option(
    "--pattern",
    type=str,
    help="Filter keys by pattern (e.g., '*global*')",
)
@click.option(
    "--human-readable",
    "human_readable",
    is_flag=True,
    help=(
        "Show human-readable identifiers (community, year, category) "
        "instead of hashed keys"
    ),
)
@click.option(
    "--community-id",
    type=str,
    help=(
        "Filter by community ID or slug (only works with --human-readable). "
        "Slugs will be automatically resolved to UUIDs."
    ),
)
@click.option(
    "--include-sizes",
    "include_sizes",
    is_flag=True,
    help="Include size in bytes for each cached item (uses batched Redis calls)",
)
@click.option(
    "--include-ages",
    "include_ages",
    is_flag=True,
    help=(
        "Include age in human-readable format for each cached item "
        "(uses batched Redis calls)"
    ),
)
@with_appcontext
def list_cache_keys_command(
    limit, pattern, human_readable, community_id, include_sizes, include_ages
):
    """List all cached statistics keys.

    This command displays all cached statistics keys, optionally filtered
    by a pattern. Keys are shown with their full names and can be used
    to identify specific cache entries for clearing.

    With --human-readable, shows community_id, year, and category
    instead of hashed keys, making it easier to identify cache entries.

    Returns:
        None: This is a CLI command function.

    Examples:
    - invenio community-stats cache list
    - invenio community-stats cache list --limit 20
    - invenio community-stats cache list --pattern "*global*"
    - invenio community-stats cache list --human-readable
    - invenio community-stats cache list --human-readable --community-id global
    """
    if human_readable:

        try:
            service = CachedResponseService()
        except Exception as e:
            click.echo(f"Failed to initialize cache service: {e}")
            return 1

        responses = service.list_cached_responses(
            community_id=community_id,
            include_sizes=include_sizes,
            include_ages=include_ages,
        )

        if not responses:
            click.echo("No cached responses found")
            if community_id:
                click.echo(f"(filtered by community_id: {community_id})")
            return

        # Apply limit
        total_responses = len(responses)
        if limit > 0:
            responses = responses[:limit]

        click.echo(
            f"Cached Responses (showing {len(responses)} of {total_responses}):"
        )

        # Determine table width and columns based on what's included
        has_extra_info = include_sizes or include_ages
        if has_extra_info:
            # Calculate column widths
            width = 120 if (include_sizes and include_ages) else 100
            click.echo("=" * width)

            # Build header
            header_parts = ["#", "Community ID", "Year", "Category"]
            if include_sizes:
                header_parts.append("Size")
            if include_ages:
                header_parts.append("Age")

            # Build format string
            if include_sizes and include_ages:
                header = (
                    f"{'#':<4} {'Community ID':<32} {'Year':<6} "
                    f"{'Category':<24} {'Size':<12} {'Age':<20}"
                )
            elif include_sizes:
                header = (
                    f"{'#':<4} {'Community ID':<36} {'Year':<6} "
                    f"{'Category':<28} {'Size':<12}"
                )
            else:  # include_ages only
                header = (
                    f"{'#':<4} {'Community ID':<36} {'Year':<6} "
                    f"{'Category':<28} {'Age':<20}"
                )

            click.echo(header)
            click.echo("-" * width)

            for i, response in enumerate(responses, 1):
                comm_id = response["community_id"]
                year = response["year"]
                category = response["category"]

                if include_sizes and include_ages:
                    size_bytes = response.get("size_bytes")
                    age_seconds = response.get("age_seconds")
                    size_str = format_bytes(size_bytes)
                    age_str = format_age(age_seconds)
                    click.echo(
                        f"{i:<4} {comm_id:<32} {year:<6} {category:<24} "
                        f"{size_str:<12} {age_str:<20}"
                    )
                elif include_sizes:
                    size_bytes = response.get("size_bytes")
                    size_str = format_bytes(size_bytes)
                    click.echo(
                        f"{i:<4} {comm_id:<36} {year:<6} {category:<28} "
                        f"{size_str:<12}"
                    )
                else:  # include_ages only
                    age_seconds = response.get("age_seconds")
                    age_str = format_age(age_seconds)
                    click.echo(
                        f"{i:<4} {comm_id:<36} {year:<6} {category:<28} "
                        f"{age_str:<20}"
                    )
        else:
            click.echo("=" * 80)
            # Display in a table-like format without extra info
            click.echo(
                f"{'#':<4} {'Community ID':<40} {'Year':<6} {'Category':<30}"
            )
            click.echo("-" * 80)

            for i, response in enumerate(responses, 1):
                comm_id = response["community_id"]
                year = response["year"]
                category = response["category"]
                click.echo(f"{i:<4} {comm_id:<40} {year:<6} {category:<30}")

        if limit > 0 and len(responses) >= limit:
            remaining = total_responses - len(responses)
            click.echo(f"\n... and {remaining} more entries")
            click.echo("Use --limit to show more entries")

        if community_id:
            click.echo(f"\nFiltered by community_id: {community_id}")

    else:
        # show hashed keys
        try:
            service = CachedResponseService()
        except Exception as e:
            click.echo(f"Failed to initialize cache service: {e}")
            return 1

        # Get all keys (with optional pattern filter)
        all_keys = service.list_cache_keys(pattern=pattern)

        if not all_keys:
            click.echo("No cache entries found")
            return

        # Apply limit
        keys = all_keys
        if limit > 0:
            keys = keys[:limit]

        total_keys = len(all_keys)
        click.echo(f"Cache Keys (showing {len(keys)} of {total_keys}):")
        click.echo("=" * 60)

        cache = StatsCache()
        for i, key in enumerate(keys, 1):
            # Remove the prefix for cleaner display
            display_key = key.replace(f"{cache.cache_prefix}:", "")
            click.echo(f"{i:3d}. {display_key}")

        if limit > 0 and len(keys) >= limit:
            remaining = total_keys - len(keys)
            click.echo(f"\n... and {remaining} more entries")
            click.echo("Use --limit to show more entries")


@cache_cli.command(name="test")
@click.option(
    "--community-id",
    type=str,
    default="global",
    help="Community ID to test with",
)
@click.option(
    "--stat-name",
    type=str,
    default="test_stat",
    help="Stat name to test with",
)
@with_appcontext
def test_cache_command(community_id, stat_name):
    r"""Test cache functionality by setting and retrieving a test entry.

    This command tests the cache functionality by storing a test entry
    and then retrieving it to verify the cache is working correctly.

    Examples:
    - invenio community-stats cache test
    - invenio community-stats cache test --community-id my-community \\
      --stat-name test_query

    Returns:
        None: This is a CLI command function.
    """
    cache = StatsCache(cache_prefix="stats_test")

    test_request_data = {
        "stat": "test_stat",
        "params": {"community_id": "global", "stat_name": "test"}
    }

    # Test data
    test_data = {
        "test": True,
        "timestamp": "2024-01-01T00:00:00Z",
        "message": "This is a test cache entry",
    }

    click.echo("Testing cache functionality...")

    # Test setting cache
    click.echo("Setting test cache entry...")
    cache_key = CachedResponse.generate_cache_key(
        "application/json", test_request_data, cache_prefix="stats_test"
    )
    success = cache.set(
        cache_key,
        json.dumps(test_data).encode("utf-8"),
        ttl=60,  # 1 minute ttl for test
    )

    if not success:
        click.echo("❌ Failed to set test cache entry")
        return 1

    click.echo("✅ Test cache entry set successfully")

    # Test getting cache
    click.echo("Retrieving test cache entry...")
    cached_data = cache.get(cache_key)

    if cached_data is None:
        click.echo("❌ Failed to retrieve test cache entry")
        return 1

    click.echo("✅ Test cache entry retrieved successfully")

    # Clean up test entry
    click.echo("Cleaning up test cache entry...")
    success = cache.delete(cache_key)

    if success:
        click.echo("✅ Test cache entry cleaned up")
    else:
        click.echo("❌ Failed to clean up test cache entry")
        return 1

    click.echo("\n🎉 Cache functionality test completed successfully!")


@cache_cli.command(name="generate")
@click.option(
    "--community-id",
    multiple=True,
    help=(
        "Community ID(s) to generate cache for (can be specified multiple times). "
        "If not specified, generates for all communities plus global."
    ),
)
@click.option(
    "--community-slug", multiple=True, help="Community slug(s) to generate cache for"
)
@click.option(
    "--year",
    type=str,
    multiple=True,
    help=(
        "Single year or year range to generate cache for (can be specified "
        "multiple times)"
    ),
)
@click.option(
    "--async",
    "async_mode",
    is_flag=True,
    help="Run cache generation asynchronously using Celery",
)
@click.option(
    "--force", is_flag=True, help="Override config setting for enabling tasks."
)
@click.option("--overwrite", is_flag=True, help="Overwrite existing cache entries")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without actually generating cache",
)
@with_appcontext
def generate_cache_command(
    community_id, community_slug, year, async_mode, force, overwrite, dry_run
):
    r"""Generate cached stats responses for all data series categories.

    This command generates cached responses for the specified communities and years,
    covering all data series categories (record_delta, usage_delta, etc.).

    If no communities are specified, it will generate cache for all communities
    and the global instance. Multiple community IDs can be specified using
    --community-id multiple times.

    Multiple years can be specified using --year multiple times or by
    providing a year range (e.g., 2020-2023). If no years are specified, a
    cached response will be generated for all years since community creation.

    Arguments:  # noqa:D412

    \b
    - community_id: Community ID(s) to generate cache for
      (can be specified multiple times)
    - community_slug: Community slug(s) to generate cache for
      (can be specified multiple times)
    - year: Single year or year range to generate cache for
      (can be specified multiple times if single years are given)
    - async_mode: Run cache generation asynchronously using Celery
    - force: Override config setting for enabling cache settings.
    - overwrite: Overwrite existing cache entries
    - dry_run: Show what would be done without actually generating cache

    Examples:  # noqa:D412

    \b
    - invenio community-stats cache generate --year 2023
    - invenio community-stats cache generate --community-id 123 --year 2023
    - invenio community-stats cache generate --community-id 123 --community-id 456 \\
            --year 2023
    - invenio community-stats cache generate --community-slug my-community \\
            --years 2020-2023
    - invenio community-stats cache generate --all-years --async
    - invenio community-stats cache generate --community-id global --year 2023 --dry-run

    Returns:
        None: This is a CLI command function.

    Raises:
        BadParameter: If invalid year values are provided.
    """
    if not force:
        check_scheduled_tasks_enabled(command="cache")
    else:
        current_app.logger.info(
            "Bypassing scheduled caching tasks check due to --force flag. "
            "Running cache generation directly."
        )

    try:
        service = CachedResponseService()
    except Exception as e:
        click.echo(f"Failed to initialize cache service: {e}")
        return 1

    community_ids = list(community_id)
    for slug in community_slug:
        try:
            community_id_resolved = resolve_slug_to_id(slug)
            community_ids.append(community_id_resolved)
        except Exception as e:
            click.echo(f"Failed to resolve community slug '{slug}': {e}")
            return 1

    if not community_ids:
        community_ids = ["global"] + service._get_all_community_ids()

    years_param: list[int] | str = "auto"
    if year:
        parsed_years: list[int] = []
        for year_value in year:
            value = year_value.strip()
            if not value:
                continue
            try:
                if "-" in value:
                    parsed_years.extend(parse_year_range(value))
                else:
                    parsed_years.append(int(value))
            except ValueError as exc:
                raise click.BadParameter(
                    f"Invalid year value '{value}'",
                    param_hint="--year",
                ) from exc

        if parsed_years:
            years_param = sorted(set(parsed_years))

    if dry_run:
        try:
            show_dry_run_results(community_ids, years_param, service.categories)
        except Exception as e:
            click.echo(f"Failed to generate dry run results: {e}")
            return 1
    else:
        try:
            if async_mode:
                click.echo("Starting async cache generation...")
                task = generate_cached_responses_task.delay(  # type: ignore
                    community_ids=community_ids,
                    years=years_param,
                    overwrite=overwrite,
                    async_mode=True,
                    current_year_only=False,
                )

                click.echo(f"Task started with ID: {task.id}")
                click.echo("Use Celery monitoring tools to track progress.")
                return 0
            else:
                # First, determine the total number of responses to process
                all_responses = service._generate_all_response_objects(
                    community_ids, service._normalize_years(years_param, community_ids)
                )
                if not overwrite:
                    responses_to_process = [
                        r
                        for r in all_responses
                        if not service.exists(r.community_id, r.year, r.category)
                    ]
                else:
                    responses_to_process = all_responses

                total_responses = len(responses_to_process)

                if total_responses == 0:
                    click.echo("No cache entries to generate.")
                    return 0

                bar = tqdm(
                    total=total_responses,
                    desc="Generating cache",
                    unit="item",
                    dynamic_ncols=True,
                )

                # Create progress callback function
                def progress_callback(current, total, message):
                    bar.set_description_str(f"Generating cache: {message}")
                    bar.update(1)

                try:
                    results = service.create(
                        community_ids=community_ids,
                        years=years_param,
                        overwrite=overwrite,
                        progress_callback=progress_callback,
                    )
                finally:
                    bar.close()

                report_results(results)

        except Exception as e:
            click.echo(f"Cache generation failed: {e}")
            return 1


def resolve_slug_to_id(slug: str) -> str:
    """Resolve community slug to ID using communities service.

    Returns:
        str: The community ID corresponding to the slug.

    Raises:
        ValueError: If the community slug is not found or if there's an error
            searching for the community.
    """
    try:
        communities_result: CommunityListResult = current_communities.service.search(
            system_identity, params={"q": f"slug:{slug}"}, size=1
        )
        result_dict: dict[str, Any] = communities_result.to_dict()
        hits: list[dict[str, Any]] = result_dict.get("hits", {}).get("hits", [])
        if hits:
            return str(hits[0]["id"])
    except Exception as e:
        raise ValueError(
            f"Error searching for community with slug '{slug}': {e}"
        ) from e

    raise ValueError(f"Community with slug '{slug}' not found")


def parse_year_range(year_range: str) -> list[int]:
    """Parse year range string (e.g., '2020-2023') into list.

    Returns:
        list[int]: List of years in the range.

    Raises:
        ValueError: If the year range format is invalid.
    """
    try:
        start, end = map(int, year_range.split("-"))
        return list(range(start, end + 1))
    except ValueError as e:
        msg = f"Invalid year range format: {year_range}"
        raise ValueError(msg) from e


def show_dry_run_results(
    community_ids: list[str], years: list[int] | str, categories: list[str]
) -> None:
    """Show what would be done in dry-run mode."""
    service = CachedResponseService()

    years_per_community = service._normalize_years(years, community_ids)

    # Calculate display info
    all_years = set()
    for community_years in years_per_community.values():
        all_years.update(community_years)

    if len(all_years) > 0:
        years_display = f"years {min(all_years)}-{max(all_years)}"
        total_combinations = sum(
            len(years) * len(categories) for years in years_per_community.values()
        )
    else:
        years_display = "no valid years"
        total_combinations = 0

    click.echo("Would generate cache for:")
    click.echo(f"  Communities: {', '.join(community_ids)}")
    click.echo(f"  Years: {years_display}")
    click.echo(f"  Categories: {', '.join(categories)}")

    # Show per-community year breakdown
    click.echo("  Year range per community:")
    existing_count = 0
    for community_id in community_ids:
        community_years = years_per_community.get(community_id, [])
        if len(community_years) > 0:
            years_range = f"{min(community_years)}-{max(community_years)}"
            combinations = len(community_years) * len(categories)
            click.echo(f"    {community_id}: {years_range} ({combinations} entries)")

            # Check existing entries for this community
            for year in community_years:
                for category in categories:
                    if service.exists(community_id, year, category):
                        existing_count += 1
        else:
            # Provide more specific messaging about why there are no valid years
            if community_id == "global":
                click.echo(
                    f"    {community_id}: no valid years to cache (no records found)"
                )
            else:
                # Check if this is because the requested time frame is before
                # community existence
                requested_years = []
                if isinstance(years, list):
                    requested_years = years
                elif isinstance(years, int):
                    requested_years = [years]

                if requested_years:
                    earliest_requested = min(requested_years)
                    community_creation_year = service._get_community_creation_year(
                        community_id
                    )
                    if (
                        community_creation_year
                        and earliest_requested < community_creation_year
                    ):
                        click.echo(
                            f"    {community_id}: no valid years to cache "
                            f"(requested {min(requested_years)}-"
                            f"{max(requested_years)}, "
                            f"but community started in {community_creation_year})"
                        )
                    else:
                        click.echo(
                            f"    {community_id}: no valid years to cache "
                            f"(no events found for this community)"
                        )
                else:
                    click.echo(
                        f"    {community_id}: no valid years to cache "
                        f"(no events found for this community)"
                    )

    click.echo(f"  Total combinations: {total_combinations}")
    if existing_count > 0:
        click.echo(f"  Existing entries: {existing_count}")
        click.echo(f"  New entries to create: {total_combinations - existing_count}")
        click.echo("")
        click.echo(f"⚠️  {existing_count} entries already exist in cache.")
        click.echo("   Use --force to overwrite existing entries.")
    else:
        click.echo(f"  All {total_combinations} entries are new.")


def report_results(results: dict[str, Any]) -> None:
    """Report execution results."""
    if results.get("async"):
        click.echo("Cache generation started in background")
        click.echo(f"Task IDs: {results['task_ids']}")
        click.echo(f"Total tasks: {results['task_count']}")
    else:
        click.echo("Cache generation completed")

        # Calculate skipped entries if we have the data
        skipped = results.get("skipped", 0)
        total_found = results["success"] + results["failed"] + skipped
        if skipped > 0:
            click.echo("Results:")
            click.echo(f"  Success: {results['success']}")
            click.echo(f"  Failed: {results['failed']}")
            click.echo(f"  Skipped (already exist): {skipped}")
            click.echo(f"  Total found: {total_found}")
            click.echo("")
            click.echo(
                f"{skipped} entries were skipped because they already exist in cache."
            )
            click.echo("   Use --force to overwrite existing entries.")
        else:
            click.echo(f"Success: {results['success']}, Failed: {results['failed']}")
        if results.get("errors"):
            click.echo("Errors:")
            for error in results["errors"]:
                click.echo(
                    f"  {error['community_id']}/{error['year']}/"
                    f"{error['category']}: {error['error']}"
                )
