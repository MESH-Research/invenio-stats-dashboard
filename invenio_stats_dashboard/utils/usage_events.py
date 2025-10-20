# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Usage event factory for generating test usage events."""

import hashlib
import random

import arrow
from invenio_access.permissions import system_identity
from invenio_rdm_records.proxies import current_rdm_records_service as records_service
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
        """Create base event data common to all event types.
        
        Returns:
            dict: Base event data dictionary.
        """
        # Ensure event time is not in the future
        current_time = arrow.utcnow()
        event_date_arrow = arrow.get(event_date)

        # If event_date is today, limit random time to current time
        if event_date_arrow.date() == current_time.date():
            max_hour = current_time.hour
            max_minute = current_time.minute
            max_second = current_time.second
        else:
            max_hour = 23
            max_minute = 59
            max_second = 59

        event_time = event_date_arrow.shift(
            hours=random.randint(0, max_hour),
            minutes=random.randint(0, max_minute),
            seconds=random.randint(0, max_second),
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
    def _enrich_event(event: dict, event_type: str) -> dict:
        """Enrich the event with additional data.
        
        Returns:
            dict: Enriched event data dictionary.
        """
        record_metadata = records_service.read(
            system_identity, id_=event["recid"]
        ).to_dict()

        file_types = [
            file["ext"]
            for file in record_metadata["files"]["entries"].values()
            if record_metadata["files"]["enabled"]
            and len(record_metadata["files"]["entries"]) > 0
        ]

        event.update(
            {
                "community_ids": (
                    record_metadata["parent"]["communities"].get("ids", None)
                ),
                "access_status": record_metadata["access"].get("status", None),
                "resource_type": record_metadata["metadata"].get("resource_type", None),
                "publisher": record_metadata["metadata"].get("publisher", None),
                "languages": record_metadata["metadata"].get("languages", None),
                "subjects": record_metadata["metadata"].get("subjects", None),
                "journal_title": (
                    record_metadata["custom_fields"]
                    .get("journal:journal", {})
                    .get("title", None)
                ),
                "rights": record_metadata["metadata"].get("rights", None),
                "funders": [
                    f.get("funder")
                    for f in record_metadata["metadata"].get("funding", [])
                ],
                "affiliations": [
                    a.get("affiliations")
                    for a in record_metadata["metadata"].get("contributors", [])
                    + record_metadata["metadata"].get("creators", [])
                ],
                "file_types": file_types or None,
            }
        )

        return event

    @staticmethod
    def make_view_event(
        record: dict, event_date: arrow.Arrow, ident: int, enrich_events: bool = False
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

        if enrich_events:
            anonymized_event = UsageEventFactory._enrich_event(anonymized_event, "view")

        return (anonymized_event, event_id)

    @staticmethod
    def make_download_event(
        record: dict, event_date: arrow.Arrow, ident: int, enrich_events: bool = False
    ) -> tuple[dict, str]:
        """Return a download event ready for indexing."""
        event_data = UsageEventFactory._create_base_event_data(
            record, event_date, ident
        )

        # Generate a consistent file_id for each file in the record
        # Use the first file's ID from the record's files entries, or generate a
        # consistent one
        if record.get("files", {}).get("entries"):
            file_id = record["files"]["entries"][0]["file_id"]
            # Use the actual file size from the record
            file_size = record["files"]["entries"][0].get(
                "size", 1000000
            )  # Default to 1MB if size not available
        else:
            # Fallback: generate a consistent file_id based on record ID
            file_id = f"test-file-{record['id']}"
            file_size = 1000000  # Default to 1MB for fallback

        event_data.update(
            {
                "bucket_id": f"test-bucket-{record['id']}",
                "file_id": file_id,
                "file_key": f"test-file-{record['id']}-{ident}.pdf",
                "size": file_size,
            }
        )

        # Anonymize the event using invenio-stats
        anonymized_event = anonymize_user(event_data)

        # Generate event ID
        hash_val = hashlib.sha1(
            (f"{event_data['unique_id']}{anonymized_event['visitor_id']}").encode()
        ).hexdigest()
        event_id = f"{event_data['timestamp']}-{hash_val}"

        if enrich_events:
            anonymized_event = UsageEventFactory._enrich_event(
                anonymized_event, "download"
            )

        return (anonymized_event, event_id)

    @staticmethod
    def _get_records_for_date_range(
        start_date: str, end_date: str, max_records: int | None = None
    ) -> list:
        """Get records within a date range.
        
        Returns:
            list: List of record dictionaries.
        """
        index_name = prefix_index("rdmrecords-records")

        record_search = Search(using=current_search_client, index=index_name)

        if start_date and end_date and start_date != end_date:
            record_search = record_search.filter(
                "range", created={"gte": start_date, "lte": end_date}
            )

        record_search = record_search.filter("term", is_published=True)

        if max_records:
            record_search = record_search.extra(size=max_records)

        results = list(record_search.scan())
        return results

    @staticmethod
    def _validate_date_range(
        start_date: arrow.Arrow | None,
        end_date: arrow.Arrow,
        record_created: arrow.Arrow,
    ) -> tuple[arrow.Arrow, arrow.Arrow]:
        """Ensure date range doesn't start before record creation.

        If start_date is None or invalid, defaults to record creation date.
        
        Returns:
            tuple[arrow.Arrow, arrow.Arrow]: Adjusted start and end dates.
        """
        # If start_date is None or invalid, use record creation date
        if start_date is None:
            start_date = record_created
        elif start_date < record_created:
            start_date = record_created

        if end_date < start_date:
            end_date = start_date

        return start_date, end_date

    @staticmethod
    def _generate_events_for_records(
        records: list,
        start_date: arrow.Arrow | None,
        end_date: arrow.Arrow,
        events_per_record: int,
        enrich_events: bool = False,
    ) -> list:
        """Generate events for a list of records.
        
        Returns:
            list: List of (event, event_id) tuples.
        """
        events: list[tuple[dict, str]] = []

        for record in records:
            record_data = record.to_dict()
            record_created = arrow.get(record_data["created"])

            event_start, event_end = UsageEventFactory._validate_date_range(
                start_date, end_date, record_created
            )

            if event_start > event_end:
                continue

            start_month = event_start.replace(day=1)
            end_month = event_end.replace(day=1)
            month_count = (
                (end_month.year - start_month.year) * 12
                + (end_month.month - start_month.month)
                + 1
            )
            events_per_month = events_per_record // month_count
            remaining_events = events_per_record % month_count

            for j in range(events_per_record):
                month_index = min(
                    j // (events_per_month + (1 if j < remaining_events else 0)),
                    month_count - 1,
                )

                if month_index == 0:
                    month_start = event_start
                else:
                    month_start = start_month.shift(months=month_index)
                if month_index == month_count - 1:
                    month_end = event_end
                else:
                    month_end = (
                        month_start.shift(months=1).replace(day=1).shift(days=-1)
                    )

                days_range = (month_end - month_start).days
                if days_range > 0:
                    random_days = random.randint(0, days_range)
                    event_date = month_start.shift(days=random_days)
                else:
                    event_date = month_start

                view_event, view_id = UsageEventFactory.make_view_event(
                    record_data, event_date, len(events), enrich_events
                )
                events.append((view_event, view_id))

                if record_data["files"]["enabled"]:
                    download_event, download_id = UsageEventFactory.make_download_event(
                        record_data, event_date, len(events), enrich_events
                    )
                    events.append((download_event, download_id))

        return events

    @staticmethod
    def _check_migrated_index_exists(index_pattern: str, month: str) -> bool:
        """Check if a migrated index with -v2.0.0 suffix exists.
        
        Returns:
            bool: True if migrated index exists, False otherwise.
        """
        migrated_index = f"{index_pattern}-{month}-v2.0.0"
        try:
            result = current_search_client.indices.exists(index=migrated_index)
            return bool(result)
        except Exception:
            return False

    @staticmethod
    def index_usage_events(events: list, use_migrated_indices: bool = False) -> dict:
        """Index usage events into the appropriate monthly indices.

        Args:
            events: List of (event, event_id) tuples to index
            use_migrated_indices: If True, use migrated indices with -v2.0.0 suffix
                when they exist
                
        Returns:
            dict: Dictionary with 'indexed' and 'errors' counts.
        """
        if not events:
            return {"indexed": 0, "errors": 0}

        indexed = 0
        errors = 0

        monthly_events: dict[str, dict[str, list[tuple[dict, str]]]] = {}
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

                # Check if we should use migrated index
                if (
                    use_migrated_indices
                    and UsageEventFactory._check_migrated_index_exists(
                        index_pattern, month
                    )
                ):
                    monthly_index = f"{index_pattern}-{month}-v2.0.0"
                else:
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

                current_search_client.indices.refresh(index=monthly_index)

        return {"indexed": indexed, "errors": errors}

    @staticmethod
    def generate_repository_events(
        start_date: str = "",
        end_date: str = "",
        events_per_record: int = 5,
        max_records: int = 0,
        enrich_events: bool = False,
        event_start_date: str = "",
        event_end_date: str = "",
    ) -> list:
        """Generate events for published records within a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format for filtering records by
                creation date. If an empty string, uses earliest record creation date.
            end_date: End date in YYYY-MM-DD format for filtering records by
                creation date. If an empty string, uses current date.
            events_per_record: Number of events to generate per record.
            max_records: Maximum number of records to process.
            enrich_events: Whether to enrich events with additional data
                matching the invenio-stats-dashboard extended fields.
            event_start_date: Start date in YYYY-MM-DD format for event timestamps.
                If an empty string, uses record creation date for each record.
            event_end_date: End date in YYYY-MM-DD format for event timestamps.
                If an empty string, uses current date.

        Returns:
            List of (event, event_id) tuples.
            
        Raises:
            IndexError: If no records are found in the specified date range.
        """
        if end_date == "":
            end_date = arrow.utcnow().format("YYYY-MM-DD")
        if start_date == "":
            # Get earliest record creation date
            record_search = Search(
                using=current_search_client, index=prefix_index("rdmrecords-records")
            )
            record_search = record_search.filter("term", is_published=True)
            record_search = record_search.extra(size=1)
            record_search = record_search.sort("created")

            try:
                search_result = record_search.execute()
                if search_result.hits.hits:
                    earliest_record = search_result.hits.hits[0]
                    start_date = arrow.get(
                        earliest_record["_source"]["created"]
                    ).format("YYYY-MM-DD")
                else:
                    raise IndexError("No hits found")
            except (IndexError, KeyError):
                start_date = arrow.utcnow().format("YYYY-MM-DD")

        # Use event dates if provided, otherwise use record creation to present
        if event_start_date == "":
            # Don't set a default here - let _validate_date_range handle it per record
            event_start_arrow = None
        else:
            event_start_arrow = arrow.get(event_start_date)

        if event_end_date == "":
            event_end_arrow = arrow.utcnow()
        else:
            event_end_arrow = arrow.get(event_end_date)

        records = UsageEventFactory._get_records_for_date_range(
            start_date, end_date, max_records
        )

        events = UsageEventFactory._generate_events_for_records(
            records,
            event_start_arrow,
            event_end_arrow,
            events_per_record,
            enrich_events,
        )

        return events

    @staticmethod
    def generate_and_index_repository_events(
        start_date: str = "",
        end_date: str = "",
        events_per_record: int = 5,
        max_records: int = 0,
        enrich_events: bool = False,
        event_start_date: str = "",
        event_end_date: str = "",
        use_migrated_indices: bool = False,
    ) -> dict:
        """Generate and index events for records within a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format for filtering records by
                creation date. If an empty string, uses earliest record creation date.
            end_date: End date in YYYY-MM-DD format for filtering records by
                creation date. If an empty string, uses current date.
            events_per_record: Number of events to generate per record.
            max_records: Maximum number of records to process.
            enrich_events: Whether to enrich events with additional data.
            event_start_date: Start date in YYYY-MM-DD format for event timestamps.
                If an empty string, uses record creation date for each record.
            event_end_date: End date in YYYY-MM-DD format for event timestamps.
                If an empty string, uses current date.
            use_migrated_indices: If True, use migrated indices with -v2.0.0 suffix
                when they exist.

        Returns:
            Dictionary with indexing results.
        """
        events = UsageEventFactory.generate_repository_events(
            start_date,
            end_date,
            events_per_record,
            max_records,
            enrich_events,
            event_start_date,
            event_end_date,
        )

        result = UsageEventFactory.index_usage_events(events, use_migrated_indices)

        return result
