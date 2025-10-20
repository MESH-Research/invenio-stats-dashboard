# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Test synthetic usage event creation and indexing."""

import copy

import arrow
from invenio_access.utils import get_identity
from invenio_search import current_search_client
from invenio_search.utils import prefix_index
from opensearchpy.helpers.search import Search

from invenio_stats_dashboard.utils.usage_events import UsageEventFactory


def test_synthetic_usage_event_creation(
    running_app,
    db,
    minimal_community_factory,
    minimal_published_record_factory,
    user_factory,
    record_metadata,
    create_stats_indices,
    search_clear,
    test_sample_files_folder,
):
    """Test synthetic usage event creation and indexing."""
    client = current_search_client

    u = user_factory(email="test@example.com")
    user = u.user
    user_identity = get_identity(user)

    community = minimal_community_factory(user.id)
    community_id = community["id"]

    records = []
    test_dates = [
        "2024-06-01T10:00:00.000000+00:00",
        "2024-06-15T10:00:00.000000+00:00",
    ]
    # Record creation date range for filtering
    record_start_date = "2024-06-01"
    record_end_date = "2024-08-07"

    for test_date in test_dates:
        test_metadata = copy.deepcopy(record_metadata().metadata_in)
        test_metadata["created"] = test_date
        test_metadata["files"] = {
            "enabled": True,
            "entries": {"sample.pdf": {"key": "sample.pdf", "ext": "pdf"}},
        }

        file_path = test_sample_files_folder / "sample.pdf"

        record = minimal_published_record_factory(
            identity=user_identity,
            community_list=[community_id],
            metadata=test_metadata,
            file_paths=[file_path],
            update_community_event_dates=True,
        )
        records.append(record)

    client.indices.refresh(index=prefix_index("rdmrecords-records"))

    usage_events = UsageEventFactory().generate_and_index_repository_events(
        start_date=record_start_date,
        end_date=record_end_date,
        events_per_record=50,
        event_start_date="2024-06-01",
        event_end_date="2024-12-31",
    )
    assert usage_events["indexed"] == 200, "Should have indexed 200 events"
    assert usage_events["errors"] == 0, "Should have no indexing errors"

    client.indices.refresh(index="events-stats-*")

    expected_months = [
        "2024-06",
        "2024-07",
        "2024-08",
        "2024-09",
        "2024-10",
        "2024-11",
        "2024-12",
    ]
    total_events = 0

    for month in expected_months:
        view_index = f"{prefix_index('events-stats-record-view')}-{month}"
        download_index = f"{prefix_index('events-stats-file-download')}-{month}"

        view_exists = client.indices.exists(index=view_index)
        download_exists = client.indices.exists(index=download_index)

        if view_exists:
            view_count = client.count(index=view_index)["count"]
            total_events += view_count

            view_search = Search(using=client, index=view_index)
            view_search = view_search.query("match_all")
            view_results = view_search.execute()

            for hit in view_results[:5]:
                event_data = hit.to_dict()

                assert isinstance(
                    event_data["timestamp"], str
                ), "timestamp should be string"
                assert isinstance(event_data["recid"], str), "recid should be string"
                assert isinstance(
                    event_data["unique_id"], str
                ), "unique_id should be string"
                assert isinstance(
                    event_data["visitor_id"], str
                ), "visitor_id should be string"
                assert isinstance(
                    event_data["unique_session_id"], str
                ), "unique_session_id should be string"
                assert isinstance(
                    event_data["referrer"], str
                ), "referrer should be string"

                if "country" in event_data:
                    assert isinstance(
                        event_data["country"], str
                    ), "country should be string"
                    assert (
                        len(event_data["country"]) == 2
                    ), "country should be 2 characters"
                assert isinstance(
                    event_data["via_api"], bool
                ), "via_api should be boolean"
                assert isinstance(
                    event_data["is_robot"], bool
                ), "is_robot should be boolean"

                event_timestamp = arrow.get(event_data["timestamp"])

                start_datetime = arrow.get("2024-06-01")
                end_datetime = arrow.get("2024-12-31").ceil("day")

                assert start_datetime <= event_timestamp <= end_datetime, (
                    f"View event timestamp {event_timestamp} should be between "
                    f"{start_datetime} and {end_datetime}"
                )

                # Verify it's a view event (no download-specific fields)
                assert (
                    "bucket_id" not in event_data
                ), "View event should not have bucket_id"
                assert "file_id" not in event_data, "View event should not have file_id"
                assert (
                    "file_key" not in event_data
                ), "View event should not have file_key"
                assert "size" not in event_data, "View event should not have size"

        if download_exists:
            download_count = client.count(index=download_index)["count"]
            total_events += download_count

            download_search = Search(using=client, index=download_index)
            download_search = download_search.query("match_all")
            download_results = download_search.execute()

            for hit in download_results[:5]:
                event_data = hit.to_dict()

                assert isinstance(
                    event_data["timestamp"], str
                ), "timestamp should be string"
                assert isinstance(event_data["recid"], str), "recid should be string"
                assert isinstance(
                    event_data["unique_id"], str
                ), "unique_id should be string"
                assert isinstance(
                    event_data["visitor_id"], str
                ), "visitor_id should be string"
                assert isinstance(
                    event_data["unique_session_id"], str
                ), "unique_session_id should be string"
                assert isinstance(
                    event_data["referrer"], str
                ), "referrer should be string"

                if "country" in event_data:
                    assert isinstance(
                        event_data["country"], str
                    ), "country should be string"
                    assert (
                        len(event_data["country"]) == 2
                    ), "country should be 2 characters"

                assert isinstance(
                    event_data["via_api"], bool
                ), "via_api should be boolean"
                assert isinstance(
                    event_data["is_robot"], bool
                ), "is_robot should be boolean"

                # Verify download-specific fields have correct types
                assert isinstance(
                    event_data["bucket_id"], str
                ), "bucket_id should be string"
                assert isinstance(
                    event_data["file_id"], str
                ), "file_id should be string"
                assert isinstance(
                    event_data["file_key"], str
                ), "file_key should be string"
                assert isinstance(
                    event_data["size"], int | float
                ), "size should be numeric"

                event_timestamp = arrow.get(event_data["timestamp"])

                start_datetime = arrow.get("2024-06-01")
                end_datetime = arrow.get("2024-12-31").ceil("day")

                assert start_datetime <= event_timestamp <= end_datetime, (
                    f"Download event timestamp {event_timestamp} should be between "
                    f"{start_datetime} and {end_datetime}"
                )

    assert total_events == 200, "Should have found 200 events in monthly indices"
