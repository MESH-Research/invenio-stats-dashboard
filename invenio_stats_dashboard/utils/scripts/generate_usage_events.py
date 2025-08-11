#!/usr/bin/env python3
"""Generate and index configurable usage events for all records in the repository.

This script uses the UsageEventFactory to create usage events for all records
in the repository, with configurable parameters for events per day and date ranges.

The events include realistic country codes from a curated list of ISO 3166-1 alpha-2
country codes to provide more realistic test data for analytics and visualization.
"""

import argparse
import sys
from datetime import datetime, timedelta
from typing import List

from invenio_search.proxies import current_search_client
from invenio_search.utils import prefix_index
from opensearchpy.helpers.search import Search

# Import the UsageEventFactory from the utils module
from ..usage_events import UsageEventFactory


def get_all_record_ids() -> List[str]:
    """Get all record IDs from the repository."""
    client = current_search_client
    search = Search(using=client, index=prefix_index("rdmrecords-records"))
    search = search.source(["id"])

    record_ids = []
    for result in search.scan():
        record_ids.append(result["id"])

    return record_ids


def parse_date(date_str: str) -> datetime:
    """Parse a date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid date format: {date_str}. Use YYYY-MM-DD"
        )


def main():
    """Main function to generate usage events."""
    parser = argparse.ArgumentParser(
        description="Generate and index usage events for all records"
    )
    parser.add_argument(
        "--events-per-day",
        type=int,
        default=5,
        help="Number of events to create per day per record (default: 5)",
    )
    parser.add_argument(
        "--start-date",
        type=parse_date,
        help="Start date for event generation (YYYY-MM-DD). "
        "If not provided, uses 30 days ago",
    )
    parser.add_argument(
        "--end-date",
        type=parse_date,
        help="End date for event generation (YYYY-MM-DD). "
        "If not provided, uses current date",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate events but don't index them",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    # Set default dates if not provided
    if args.start_date is None:
        args.start_date = datetime.utcnow() - timedelta(days=30)
    if args.end_date is None:
        args.end_date = datetime.utcnow()

    if args.verbose:
        print("Configuration:")
        print(f"  Events per day: {args.events_per_day}")
        print(f"  Start date: {args.start_date.strftime('%Y-%m-%d')}")
        print(f"  End date: {args.end_date.strftime('%Y-%m-%d')}")
        print(f"  Dry run: {args.dry_run}")

    # Get all record IDs
    if args.verbose:
        print("Fetching all record IDs...")

    record_ids = get_all_record_ids()

    if args.verbose:
        print(f"Found {len(record_ids)} records")

    # Create factory and generate events
    factory = UsageEventFactory()

    if args.verbose:
        print("Generating events...")

    all_events = factory.create_events_for_records(
        record_ids=record_ids,
        events_per_day=args.events_per_day,
        start_date=args.start_date,
        end_date=args.end_date,
    )

    # Count total events
    total_events = sum(len(events) for events in all_events.values())

    if args.verbose:
        print(f"Generated {total_events} total events")
        print(f"Events per record: {len(all_events)} records")

    if not args.dry_run:
        if args.verbose:
            print("Indexing events...")

        # Index all events
        success = factory.index_events(
            [event for events in all_events.values() for event in events]
        )

        if success:
            print(f"Successfully indexed {total_events} events")
        else:
            print("Error indexing events")
            sys.exit(1)
    else:
        print(f"Dry run completed. Would have indexed {total_events} events")


if __name__ == "__main__":
    main()
