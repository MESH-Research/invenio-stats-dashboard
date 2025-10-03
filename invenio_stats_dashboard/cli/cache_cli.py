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

import click
from flask.cli import with_appcontext

from ..resources.cache_utils import StatsCache


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
    """
    cache = StatsCache()

    if not (force and yes_i_know):
        click.confirm(
            "Are you sure you want to clear all cached statistics data? "
            "This will force recalculation of all statistics on next request.",
            abort=True,
        )

    with click.progressbar(length=1, label="Clearing cache...") as bar:
        success, deleted_count = cache.clear_all_cache()
        bar.update(1)

    if success:
        if deleted_count > 0:
            click.echo(f"✅ Successfully cleared {deleted_count} cache entries")
        else:
            click.echo("ℹ️  No cache entries found to clear")
    else:
        click.echo("❌ Failed to clear cache entries - check Redis connection and logs")
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
    """Clear a specific cached statistics item.

    This command removes a specific cached statistics entry based on the
    provided parameters. If the exact cache entry is not found, no error
    will be reported.

    Arguments:
    - community_id: Community ID or "global"
    - stat_name: Name of the statistics query

    Examples:
    - invenio community-stats cache clear-item global record_snapshots
    - invenio community-stats cache clear-item my-community usage_delta \\
      --start-date 2024-01-01
    - invenio community-stats cache clear-item global record_created \\
      --date-basis created
    """
    cache = StatsCache()

    # Prepare parameters for cache key generation
    cache_params = {
        "community_id": community_id,
        "stat_name": stat_name,
        "start_date": start_date or "",
        "end_date": end_date or "",
        "date_basis": date_basis,
    }

    if content_type:
        cache_params["content_type"] = content_type

    # Generate the cache key to show what will be cleared
    cache_key = cache._generate_cache_key(**cache_params)

    click.echo(f"Clearing cache entry: {cache_key}")

    success = cache.invalidate_cache(community_id, stat_name)

    if success:
        click.echo("✅ Cache entry cleared successfully")
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
@with_appcontext
def list_cache_keys_command(limit, pattern):
    """List all cached statistics keys.

    This command displays all cached statistics keys, optionally filtered
    by a pattern. Keys are shown with their full names and can be used
    to identify specific cache entries for clearing.

    Examples:
    - invenio community-stats cache list
    - invenio community-stats cache list --limit 20
    - invenio community-stats cache list --pattern "*global*"
    """
    cache = StatsCache()

    keys = cache.list_cache_keys()

    if not keys:
        click.echo("No cache entries found")
        return

    # Apply pattern filter if provided
    if pattern:
        import fnmatch

        keys = [key for key in keys if fnmatch.fnmatch(key, pattern)]

    # Apply limit
    if limit > 0:
        keys = keys[:limit]

    total_keys = len(cache.list_cache_keys())
    click.echo(f"Cache Keys (showing {len(keys)} of {total_keys}):")
    click.echo("=" * 60)

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
    """
    cache = StatsCache(cache_prefix="test")

    test_request_data = {"community_id": "global", "stat_name": "test"}

    # Test data
    test_data = {
        "test": True,
        "timestamp": "2024-01-01T00:00:00Z",
        "message": "This is a test cache entry",
    }

    click.echo("Testing cache functionality...")

    # Test setting cache
    click.echo("Setting test cache entry...")
    success = cache.set_cached_response(
        "application/json",
        test_request_data,
        json.dumps(test_data),
        timeout=60,  # 1 minute timeout for test
    )

    if not success:
        click.echo("❌ Failed to set test cache entry")
        return 1

    click.echo("✅ Test cache entry set successfully")

    # Test getting cache
    click.echo("Retrieving test cache entry...")
    cached_data = cache.get_cached_response("application/json", test_request_data)

    if cached_data is None:
        click.echo("❌ Failed to retrieve test cache entry")
        return 1

    click.echo("✅ Test cache entry retrieved successfully")

    # Clean up test entry
    click.echo("Cleaning up test cache entry...")
    cache.invalidate_cache("test*")
    cached_data_after = cache.get_cached_response("application/json", test_request_data)

    if cached_data_after is None:
        click.echo("✅ Test cache entry cleaned up")
    else:
        click.echo("❌ Failed to clean up test cache entry with `invalidate_cache`")
        return 1

    click.echo("\n🎉 Cache functionality test completed successfully!")
