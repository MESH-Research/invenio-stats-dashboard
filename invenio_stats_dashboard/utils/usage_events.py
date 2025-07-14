"""Usage event factory for generating test usage events."""

import hashlib
import random
import arrow
from flask import current_app
from invenio_search.proxies import current_search_client
from invenio_search.utils import prefix_index
from invenio_stats.processors import anonymize_user
from opensearchpy.helpers.search import Search
from opensearchpy.helpers import bulk

# Realistic country codes for test data (most common countries)
COUNTRY_CODES = [
    "US",
    "GB",
    "DE",
    "FR",
    "CA",
    "AU",
    "JP",
    "CN",
    "IN",
    "BR",
    "IT",
    "ES",
    "NL",
    "KR",
    "SE",
    "CH",
    "BE",
    "AT",
    "DK",
    "NO",
]


class UsageEventFactory:
    """Factory for generating synthetic usage events."""

    @staticmethod
    def _create_base_event_data(
        record: dict, event_date: arrow.Arrow, ident: int
    ) -> dict:
        """Create base event data common to all event types."""
        event_time = arrow.get(event_date).shift(
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )

        # Generate diverse user/session data for realistic anonymization
        user_id = f"test-user-{random.randint(1000, 9999)}"
        session_id = f"test-session-{random.randint(10000, 99999)}"
        ip_address = f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}"

        # Realistic browser user agent
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        return {
            "timestamp": event_time.format("YYYY-MM-DDTHH:mm:ss"),
            "recid": str(record["id"]),
            "parent_recid": str(record.get("parent", {}).get("id", record["id"])),
            "unique_id": f"{record['id']}-{ident}",
            "user_id": user_id,
            "session_id": session_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "country": random.choice(COUNTRY_CODES),
            "referrer": f"https://example.com/records/{record['id']}",
            "via_api": False,
            "is_robot": False,
        }

    @staticmethod
    def make_view_event(
        record: dict, event_date: arrow.Arrow, ident: int
    ) -> tuple[dict, str]:
        """Return a view event ready for indexing."""
        event_data = UsageEventFactory._create_base_event_data(
            record, event_date, ident
        )

        # Anonymize the event using invenio-stats
        anonymized_event = anonymize_user(event_data)

        # Generate event ID
        hash_val = hashlib.sha1(
            (f"{event_data['unique_id']}{anonymized_event['visitor_id']}").encode()
        ).hexdigest()
        event_id = f"{event_data['timestamp']}-{hash_val}"

        return (anonymized_event, event_id)

    @staticmethod
    def make_download_event(
        record: dict, event_date: arrow.Arrow, ident: int
    ) -> tuple[dict, str]:
        """Return a download event ready for indexing."""
        event_data = UsageEventFactory._create_base_event_data(
            record, event_date, ident
        )

        # Add download-specific fields
        event_data.update(
            {
                "bucket_id": f"test-bucket-{record['id']}",
                "file_id": f"test-file-{record['id']}-{ident}",
                "file_key": f"test-file-{record['id']}-{ident}.pdf",
                "size": random.randint(100000, 5000000),  # 100KB to 5MB
            }
        )

        # Anonymize the event using invenio-stats
        anonymized_event = anonymize_user(event_data)

        # Generate event ID
        hash_val = hashlib.sha1(
            (f"{event_data['unique_id']}{anonymized_event['visitor_id']}").encode()
        ).hexdigest()
        event_id = f"{event_data['timestamp']}-{hash_val}"

        return (anonymized_event, event_id)

    @staticmethod
    def _get_records_for_date_range(
        start_date: str, end_date: str, max_records: int = None
    ) -> list:
        """Get records within a date range."""
        record_search = Search(
            using=current_search_client, index=prefix_index("rdmrecords-records")
        )
        record_search = record_search.filter(
            "range", created={"gte": start_date, "lte": end_date}
        )
        record_search = record_search.filter("term", access_status="published")

        if max_records:
            record_search = record_search.extra(size=max_records)

        return list(record_search.scan())

    @staticmethod
    def _validate_date_range(
        start_date: arrow.Arrow, end_date: arrow.Arrow, record_created: arrow.Arrow
    ) -> tuple[arrow.Arrow, arrow.Arrow]:
        """Validate and adjust date range to ensure it doesn't start before record creation."""
        # Ensure start date is not before record creation
        if start_date < record_created:
            current_app.logger.info(
                f"Adjusting start date from {start_date} to record creation date {record_created}"
            )
            start_date = record_created

        # Ensure end date is not before start date
        if end_date < start_date:
            current_app.logger.warning(
                f"End date {end_date} is before start date {start_date}, using start date as end date"
            )
            end_date = start_date

        return start_date, end_date

    @staticmethod
    def _generate_events_for_records(
        records: list,
        start_date: arrow.Arrow,
        end_date: arrow.Arrow,
        events_per_record: int,
    ) -> list:
        """Generate events for a list of records."""
        events = []

        for record in records:
            record_data = record.to_dict()
            record_created = arrow.get(record_data["created"])

            # Validate and adjust date range for this record
            record_start, record_end = UsageEventFactory._validate_date_range(
                start_date, end_date, record_created
            )

            # Skip if no valid date range
            if record_start >= record_end:
                current_app.logger.info(
                    f"Skipping record {record_data['id']} - no valid date range"
                )
                continue

            # Generate multiple events per record across the date range
            for _ in range(events_per_record):
                # Random date within the validated range
                days_range = (record_end - record_start).days
                if days_range > 0:
                    random_days = random.randint(0, days_range)
                    event_date = record_start.shift(days=random_days)
                else:
                    event_date = record_start

                # Create both view and download events
                view_event, view_id = UsageEventFactory.make_view_event(
                    record_data, event_date, len(events)
                )
                events.append((view_event, view_id))

                # 30% chance of download event
                if random.random() < 0.3:
                    download_event, download_id = UsageEventFactory.make_download_event(
                        record_data, event_date, len(events)
                    )
                    events.append((download_event, download_id))

        return events

    @staticmethod
    def index_usage_events(events: list) -> dict:
        """Index usage events into the appropriate monthly indices."""
        if not events:
            return {"indexed": 0, "errors": 0}

        indexed = 0
        errors = 0

        # Group events by month and type
        monthly_events = {}
        for event, event_id in events:
            # Parse timestamp to get month
            timestamp = arrow.get(event["timestamp"])
            month = timestamp.format("YYYY-MM")

            # Determine event type based on presence of file fields
            event_type = "download" if "bucket_id" in event else "view"

            if month not in monthly_events:
                monthly_events[month] = {"view": [], "download": []}

            monthly_events[month][event_type].append((event, event_id))

        # Index events by month and type
        for month, type_events in monthly_events.items():
            for event_type, type_event_list in type_events.items():
                if not type_event_list:
                    continue

                # Get the appropriate index pattern
                if event_type == "view":
                    index_pattern = prefix_index("events-stats-record-view")
                else:
                    index_pattern = prefix_index("events-stats-file-download")

                monthly_index = f"{index_pattern}-{month}"

                # Prepare documents for bulk indexing
                docs = []
                for event, event_id in type_event_list:
                    docs.append(
                        {
                            "_index": monthly_index,
                            "_id": event_id,
                            "_source": event,
                        }
                    )

                # Bulk index
                try:
                    success, errors_batch = bulk(
                        current_search_client, docs, stats_only=False
                    )
                    if errors_batch:
                        current_app.logger.error(
                            f"Bulk indexing errors: {errors_batch}"
                        )
                        errors += len(errors_batch)
                    else:
                        indexed += len(docs)
                except Exception as e:
                    current_app.logger.error(f"Failed to index events: {e}")
                    errors += len(docs)

        return {"indexed": indexed, "errors": errors}

    @staticmethod
    def generate_repository_events(
        start_date: str = None,
        end_date: str = None,
        events_per_record: int = 5,
        max_records: int = None,
    ) -> list:
        """Generate events for published records within a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format. If None, uses earliest record creation date.
            end_date: End date in YYYY-MM-DD format. If None, uses current date.
            events_per_record: Number of events to generate per record.
            max_records: Maximum number of records to process.

        Returns:
            List of (event, event_id) tuples.
        """
        # Set default dates if not provided
        if end_date is None:
            end_date = arrow.utcnow().format("YYYY-MM-DD")
        if start_date is None:
            # Get earliest record creation date
            record_search = Search(
                using=current_search_client, index=prefix_index("rdmrecords-records")
            )
            record_search = record_search.filter("term", access_status="published")
            record_search = record_search.extra(size=1)
            record_search = record_search.sort("created")

            try:
                earliest_record = record_search.execute().hits.hits[0]
                start_date = arrow.get(earliest_record["_source"]["created"]).format(
                    "YYYY-MM-DD"
                )
            except (IndexError, KeyError):
                current_app.logger.warning(
                    "No published records found, using current date as start"
                )
                start_date = arrow.utcnow().format("YYYY-MM-DD")

        # Parse dates
        start_arrow = arrow.get(start_date)
        end_arrow = arrow.get(end_date)

        # Get records for the date range
        records = UsageEventFactory._get_records_for_date_range(
            start_date, end_date, max_records
        )

        # Generate events
        return UsageEventFactory._generate_events_for_records(
            records, start_arrow, end_arrow, events_per_record
        )

    @staticmethod
    def generate_and_index_repository_events_old(per_day_count: int) -> dict:
        """Legacy method: Generate and index events for all published records."""
        events = UsageEventFactory.generate_repository_events(
            events_per_record=per_day_count
        )
        return UsageEventFactory.index_usage_events(events)

    @staticmethod
    def generate_and_index_repository_events(
        start_date: str = None,
        end_date: str = None,
        events_per_record: int = 5,
        max_records: int = None,
    ) -> dict:
        """Generate and index events for records within a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format. If None, uses earliest record creation date.
            end_date: End date in YYYY-MM-DD format. If None, uses current date.
            events_per_record: Number of events to generate per record.
            max_records: Maximum number of records to process.

        Returns:
            Dictionary with indexing results.
        """
        # Generate events
        events = UsageEventFactory.generate_repository_events(
            start_date, end_date, events_per_record, max_records
        )

        # Index events
        return UsageEventFactory.index_usage_events(events)
