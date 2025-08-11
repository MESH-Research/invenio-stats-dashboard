"""Usage event factory for generating test usage events."""

import hashlib
import random
from typing import Optional

import arrow
from flask import current_app
from invenio_search.proxies import current_search_client
from invenio_search.utils import prefix_index
from invenio_stats.processors import anonymize_user
from opensearchpy.helpers import bulk
from opensearchpy.helpers.search import Search

# Realistic public IP addresses from various countries for test data
# These are dummy IPs that represent different countries
PUBLIC_IP_ADDRESSES = [
    # United States
    "8.8.8.8",  # Google DNS
    "1.1.1.1",  # Cloudflare DNS
    "208.67.222.222",  # OpenDNS
    # United Kingdom
    "151.101.1.69",  # BBC
    "151.101.193.69",  # BBC
    # Germany
    "91.198.174.192",  # Wikimedia
    "91.198.174.208",  # Wikimedia
    # France
    "185.31.16.185",  # Wikimedia
    "185.31.16.184",  # Wikimedia
    # Canada
    "142.250.72.14",  # Google
    "142.250.72.78",  # Google
    # Australia
    "203.208.60.1",  # Google
    "203.208.60.2",  # Google
    # Japan
    "202.216.163.11",  # Google
    "202.216.163.12",  # Google
    # China
    "203.208.50.1",  # Google
    "203.208.50.2",  # Google
    # India
    "203.208.60.1",  # Google
    "203.208.60.2",  # Google
    # Brazil
    "142.250.72.14",  # Google
    "142.250.72.78",  # Google
    # Italy
    "91.198.174.192",  # Wikimedia
    "91.198.174.208",  # Wikimedia
    # Spain
    "91.198.174.192",  # Wikimedia
    "91.198.174.208",  # Wikimedia
    # Netherlands
    "91.198.174.192",  # Wikimedia
    "91.198.174.208",  # Wikimedia
    # South Korea
    "203.208.60.1",  # Google
    "203.208.60.2",  # Google
    # Sweden
    "91.198.174.192",  # Wikimedia
    "91.198.174.208",  # Wikimedia
    # Switzerland
    "91.198.174.192",  # Wikimedia
    "91.198.174.208",  # Wikimedia
    # Belgium
    "91.198.174.192",  # Wikimedia
    "91.198.174.208",  # Wikimedia
    # Austria
    "91.198.174.192",  # Wikimedia
    "91.198.174.208",  # Wikimedia
    # Denmark
    "91.198.174.192",  # Wikimedia
    "91.198.174.208",  # Wikimedia
    # Norway
    "91.198.174.192",  # Wikimedia
    "91.198.174.208",  # Wikimedia
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
        ip_address = random.choice(PUBLIC_IP_ADDRESSES)

        user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        return {
            "timestamp": event_time.format("YYYY-MM-DDTHH:mm:ss"),
            "recid": str(record["id"]),
            "parent_recid": str(record.get("parent", {}).get("id", record["id"])),
            "unique_id": f"{record['id']}-{ident}",
            "user_id": user_id,
            "session_id": session_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
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
        start_date: str, end_date: str, max_records: Optional[int] = None
    ) -> list:
        """Get records within a date range."""
        index_name = prefix_index("rdmrecords-records")

        record_search = Search(using=current_search_client, index=index_name)
        record_search = record_search.filter(
            "range", created={"gte": start_date, "lte": end_date}
        )
        record_search = record_search.filter("term", is_published=True)

        if max_records:
            record_search = record_search.extra(size=max_records)

        # Execute the search and get results
        results = list(record_search.scan())
        return results

    @staticmethod
    def _validate_date_range(
        start_date: arrow.Arrow, end_date: arrow.Arrow, record_created: arrow.Arrow
    ) -> tuple[arrow.Arrow, arrow.Arrow]:
        """Validate and adjust date range to ensure it doesn't start before record creation."""
        # Ensure start date is not before record creation
        if start_date < record_created:
            start_date = record_created

        # Ensure end date is not before start date
        if end_date < start_date:
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

        for i, record in enumerate(records):
            record_data = record.to_dict()
            record_created = arrow.get(record_data["created"])

            record_start, record_end = UsageEventFactory._validate_date_range(
                start_date, end_date, record_created
            )

            if record_start >= record_end:
                continue

            for j in range(events_per_record):
                days_range = (record_end - record_start).days
                if days_range > 0:
                    random_days = random.randint(0, days_range)
                    event_date = record_start.shift(days=random_days)
                else:
                    event_date = record_start

                view_event, view_id = UsageEventFactory.make_view_event(
                    record_data, event_date, len(events)
                )
                events.append((view_event, view_id))

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

        monthly_events = {}
        for event, event_id in events:
            timestamp = arrow.get(event["timestamp"])
            month = timestamp.format("YYYY-MM")

            event_type = "download" if "bucket_id" in event else "view"

            if month not in monthly_events:
                monthly_events[month] = {"view": [], "download": []}

            monthly_events[month][event_type].append((event, event_id))

        for month, type_events in monthly_events.items():
            for event_type, type_event_list in type_events.items():
                if not type_event_list:
                    continue

                if event_type == "view":
                    index_pattern = prefix_index("events-stats-record-view")
                else:
                    index_pattern = prefix_index("events-stats-file-download")

                monthly_index = f"{index_pattern}-{month}"

                docs = []
                for event, event_id in type_event_list:
                    docs.append(
                        {
                            "_index": monthly_index,
                            "_id": event_id,
                            "_source": event,
                        }
                    )

                try:
                    success, errors_batch = bulk(
                        current_search_client, docs, stats_only=False
                    )
                    if errors_batch:
                        errors += len(errors_batch)
                    else:
                        indexed += len(docs)
                except Exception:
                    errors += len(docs)

        return {"indexed": indexed, "errors": errors}

    @staticmethod
    def generate_repository_events(
        start_date: str = "",
        end_date: str = "",
        events_per_record: int = 5,
        max_records: int = 0,
    ) -> list:
        """Generate events for published records within a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format. If an empty string,
                uses earliest record creation date.
            end_date: End date in YYYY-MM-DD format. If an empty string,
                uses current date.
            events_per_record: Number of events to generate per record.
            max_records: Maximum number of records to process.

        Returns:
            List of (event, event_id) tuples.
        """
        if end_date == "":
            end_date = arrow.utcnow().format("YYYY-MM-DD")
        if start_date == "":
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
                start_date = arrow.utcnow().format("YYYY-MM-DD")

        start_arrow = arrow.get(start_date)
        end_arrow = arrow.get(end_date)

        records = UsageEventFactory._get_records_for_date_range(
            start_date, end_date, max_records
        )

        events = UsageEventFactory._generate_events_for_records(
            records, start_arrow, end_arrow, events_per_record
        )

        return events

    @staticmethod
    def generate_and_index_repository_events(
        start_date: str = "",
        end_date: str = "",
        events_per_record: int = 5,
        max_records: int = 0,
    ) -> dict:
        """Generate and index events for records within a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format. If an empty string,
                uses earliest record creation date.
            end_date: End date in YYYY-MM-DD format. If an empty string,
                uses current date.
            events_per_record: Number of events to generate per record.
            max_records: Maximum number of records to process.

        Returns:
            Dictionary with indexing results.
        """
        events = UsageEventFactory.generate_repository_events(
            start_date, end_date, events_per_record, max_records
        )

        result = UsageEventFactory.index_usage_events(events)

        return result
