# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Service components for community statistics and event management."""

from typing import Any

import arrow
from flask import current_app
from flask_principal import Identity
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_rdm_records.records.api import RDMDraft, RDMRecord
from invenio_rdm_records.requests.community_inclusion import (
    AcceptAction as CommunityInclusionAcceptAction,
)
from invenio_rdm_records.requests.community_inclusion import (
    CommunityInclusion,
)
from invenio_rdm_records.requests.community_submission import (
    AcceptAction as CommunitySubmissionAcceptAction,
)
from invenio_rdm_records.requests.community_submission import (
    CommunitySubmission,
)

try:  # invenio-rdm-records changed this for InvenioRDM 13.0.0
    from invenio_rdm_records.requests.community_transfer import (
        AcceptCommunityTransfer as CommunityTransferAcceptAction,
    )
    from invenio_rdm_records.requests.community_transfer import (
        CommunityTransferRequest,
    )
except ImportError:
    pass
from invenio_records_resources.services.records.components.base import ServiceComponent
from invenio_records_resources.services.uow import UnitOfWork, unit_of_work
from invenio_requests.records.api import RequestEvent
from invenio_search import current_search_client
from invenio_search.utils import prefix_index


def parse_publication_date_for_events(pub_date: str | None) -> str | None:
    """Parse publication date and return a standardized date for events index.

    This function handles various publication date formats and converts them
    to a standardized date that can be used for date range queries in the
    events index.

    Args:
        pub_date: The publication date string from record metadata

    Returns:
        A standardized date string in YYYY-MM-DD format, or None if invalid

    Examples:
        "2010" -> "2010-01-01"
        "2020-10" -> "2020-10-01"
        "2020-10-13" -> "2020-10-13"
        "2020-2021" -> "2020-01-01" (uses start of range)
    """
    if not pub_date:
        return None

    try:
        # Handle year-only format: "2010"
        if pub_date.isdigit() and len(pub_date) == 4:
            return f"{pub_date}-01-01"

        # Handle year-month format: "2020-10"
        if len(pub_date) == 7 and pub_date[4] == "-":
            year, month = pub_date.split("-")
            if year.isdigit() and month.isdigit() and 1 <= int(month) <= 12:
                return f"{year}-{month.zfill(2)}-01"

        # Handle full date format: "2020-10-13"
        if len(pub_date) == 10 and pub_date[4] == "-" and pub_date[7] == "-":
            year, month, day = pub_date.split("-")
            if year.isdigit() and month.isdigit() and day.isdigit():
                if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        # Handle date range format: "2020-2021"
        if len(pub_date) == 9 and pub_date[4] == "-":
            start_year, end_year = pub_date.split("-")
            if start_year.isdigit() and end_year.isdigit():
                # Use the start year for the event date
                return f"{start_year}-01-01"

        # If none of the above patterns match, try to parse with arrow
        parsed_date = arrow.get(pub_date)
        return str(parsed_date.floor("day").format("YYYY-MM-DDTHH:mm:ss"))

    except Exception as e:
        current_app.logger.warning(
            f"Could not parse publication date '{pub_date}': {e}"
        )
        return None


def update_event_deletion_fields(
    event_id: str, is_deleted: bool, deleted_date: str | None = None
) -> None:
    """Update deletion-related fields and updated_timestamp for an existing event."""
    client = current_search_client
    search_index = prefix_index("stats-community-events")

    # First, refresh the index to ensure we get the most up-to-date state
    try:
        client.indices.refresh(index=search_index)
    except Exception as e:
        current_app.logger.error(f"Error refreshing index {search_index}: {e}")

    # Then, find the document to get its actual index
    try:
        # Search for the document using the alias to get its actual index
        search_result = client.search(
            index=search_index, body={"query": {"term": {"_id": event_id}}}, size=1
        )

        if search_result["hits"]["total"]["value"] == 0:
            current_app.logger.error(
                f"Event {event_id} not found in community events index"
            )
            return

        # Get the actual index where the document is stored
        actual_index = search_result["hits"]["hits"][0]["_index"]

        update_doc = {
            "doc": {
                "is_deleted": is_deleted,
                "updated_timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss.SSS"),
            }
        }

        # Handle deleted_date field
        if deleted_date is not None:
            # Set the deleted_date field
            update_doc["doc"]["deleted_date"] = deleted_date
        else:
            # Set deleted_date to null when restoring
            update_doc["doc"]["deleted_date"] = None

        client.update(index=actual_index, id=event_id, body=update_doc)

    except Exception as e:
        current_app.logger.error(
            f"Error updating deletion fields for event {event_id}: {e}"
        )


def update_community_events_deletion_fields(
    record_id: str,
    is_deleted: bool,
    deleted_date: str | None = None,
) -> None:
    """Update deletion fields for all community events of a record.

    This function is used when a record is deleted to mark all its community events
    as deleted in the community events index.

    Args:
        record_id: The record ID
        is_deleted: Whether the record is deleted
        deleted_date: When the record was deleted
    """
    client = current_search_client
    search_index = prefix_index("stats-community-events")

    query = {
        "query": {"term": {"record_id": record_id}},
        "size": 1000,
    }

    try:
        result = client.search(index=search_index, body=query)

        if result["hits"]["total"]["value"] > 0:
            updated_count = 0
            for hit in result["hits"]["hits"]:
                event_id = hit["_id"]
                event_source = hit["_source"]
                current_is_deleted = event_source.get("is_deleted", None)
                current_deleted_date = event_source.get("deleted_date")

                # Only update if the deletion status has changed
                if (
                    current_is_deleted != is_deleted
                    or current_deleted_date != deleted_date
                ):
                    update_event_deletion_fields(event_id, is_deleted, deleted_date)
                    updated_count += 1

    except Exception as e:
        current_app.logger.error(
            f"Error updating deletion fields for all events of record {record_id}: {e}"
        )


def update_community_events_created_date(
    record_id: str,
    new_created_date: str,
    update_event_date: bool = True,
) -> None:
    """Update event_date and record_created_date for all community events of a record.

    This function is used when a record's created date is updated to ensure that
    all community events in the stats-community-events index reflect the new date.

    By default, this function updates both event_date and record_created_date to
    the new created date. If update_event_date is False, only the record_created_date
    is updated.

    Args:
        record_id: The record ID
        new_created_date: The new created date in ISO format
        update_event_date: If True, update both event_date and record_created_date.
                          If False, update only record_created_date.
    """
    client = current_search_client
    search_index = prefix_index("stats-community-events")
    client.indices.refresh(index=f"*{search_index}*")

    query = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"record_id": record_id}},
                    {"term": {"event_type": "added"}},
                ]
            }
        },
        "size": 1000,
    }

    try:
        result = client.search(index=search_index, body=query)

        if result["hits"]["total"]["value"] > 0:
            updated_count = 0
            for hit in result["hits"]["hits"]:
                event_id = hit["_id"]
                event_source = hit["_source"]
                current_event_date = event_source.get("event_date")
                current_record_created_date = event_source.get("record_created_date")
                # community_id = event_source.get("community_id")  # Unused variable

                # Check if we need to update record_created_date
                should_update_record_created = (
                    current_record_created_date != new_created_date
                )

                # Update if record_created_date needs updating
                if should_update_record_created:
                    actual_index = hit["_index"]

                    update_doc = {
                        "doc": {
                            "record_created_date": new_created_date,
                            "updated_timestamp": (
                                arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss.SSS")
                            ),
                        }
                    }

                    # Optionally update event_date if the flag is True
                    if update_event_date and current_event_date != new_created_date:
                        update_doc["doc"]["event_date"] = new_created_date

                    try:
                        client.update(index=actual_index, id=event_id, body=update_doc)
                        updated_count += 1
                    except Exception as e:
                        current_app.logger.error(
                            f"Error updating event {event_id}: {e}"
                        )

    except Exception as e:
        current_app.logger.error(
            f"Error updating created date for all events of record {record_id}: {e}"
        )


def update_community_events_index(
    record_id: str,
    community_ids_to_add: list[str] | None = None,
    community_ids_to_remove: list[str] | None = None,
    timestamp: str | None = None,
    record_created_date: str | None = None,
    record_published_date: str | None = None,
    is_deleted: bool = False,
    deleted_date: str | None = None,
    client=None,
) -> None:
    """Update the community events index with new events.

    This function manages record community events in a separate search index.
    It also creates a "global" event for every record to enable global statistics.

    Args:
        record_id: The record ID
        community_ids_to_add: List of community IDs to mark as added
        community_ids_to_remove: List of community IDs to mark as removed
        timestamp: ISO format timestamp to use (defaults to current UTC time)
        record_created_date: When the record was created
        record_published_date: When the record was published
        is_deleted: Whether the record is deleted
        deleted_date: When the record was deleted
        client: The search client to use for updating the index
    """
    if timestamp is None:
        timestamp = arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss.SSS")

    if client is None:
        client = current_search_client
    search_index = prefix_index("stats-community-events")

    event_year = arrow.get(timestamp).year
    write_index = prefix_index(f"stats-community-events-{event_year}")

    parsed_published_date = parse_publication_date_for_events(record_published_date)

    def get_newest_event(record_id: str, community_id: str, is_removal: bool = False):
        """Get the newest event for a record/community combination using the alias."""
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"record_id": record_id}},
                        {"term": {"community_id": community_id}},
                    ]
                }
            },
            "sort": [{"event_date": {"order": "desc"}}],
            "size": 1,
        }

        try:
            result = client.search(index=search_index, body=query)
            if result["hits"]["total"]["value"] > 0:
                return result["hits"]["hits"][0]
            elif is_removal:
                # Only log error for removals with no prior events
                current_app.logger.error(
                    f"No prior events found for record {record_id}, "
                    f"community {community_id} when attempting removal"
                )
        except Exception as e:
            if "index_not_found_exception" in str(e) or "no such index" in str(e):
                # This is normal for new records - the index will be created when
                # first document is indexed
                pass
            else:
                current_app.logger.error(
                    f"Error querying community events index for record {record_id}, "
                    f"community {community_id}: {e}"
                )
        return None

    def create_new_event(
        record_id: str,
        community_id: str,
        event_type: str,
        event_date: str,
        is_deleted: bool,
    ):
        """Create a new community event in the appropriate annual index."""
        event_doc = {
            "record_id": record_id,
            "community_id": community_id,
            "event_type": event_type,
            "event_date": event_date,
            "record_created_date": record_created_date,
            "record_published_date": parsed_published_date,
            "is_deleted": is_deleted,
            "timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss.SSS"),
            "updated_timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss.SSS"),
        }
        if deleted_date:
            event_doc["deleted_date"] = deleted_date

        current_app.logger.error(
            f"Creating new community event for record {record_id}, "
            f"community {community_id}: {event_doc}"
        )
        try:
            result = client.index(index=write_index, body=event_doc)
            current_app.logger.error(f"Created new community event: {result}")
        except Exception as e:
            current_app.logger.error(
                f"Error creating new community event for record {record_id}, "
                f"community {community_id}: {e}"
            )

    def process_community_events(
        record_id: str, community_ids: list[str], event_type: str, timestamp: str
    ):
        """Process community events (additions or removals) with common logic."""
        for community_id in community_ids:
            newest_event = get_newest_event(
                record_id, community_id, event_type == "removed"
            )

            if newest_event:
                newest_event_source = newest_event["_source"]
                newest_event_type = newest_event_source["event_type"]

                if newest_event_type != "added" and event_type == "removed":
                    # No addition event found, create one with timestamp
                    # 1 second before removal
                    removal_timestamp = arrow.get(timestamp)
                    addition_timestamp = removal_timestamp.shift(seconds=-1)
                    create_new_event(
                        record_id,
                        community_id,
                        "added",
                        addition_timestamp.format("YYYY-MM-DDTHH:mm:ss.SSS"),
                        is_deleted,
                    )
                if newest_event_type == event_type:
                    current_is_deleted = newest_event_source.get("is_deleted", False)
                    current_deleted_date = newest_event_source.get("deleted_date")

                    if (
                        current_is_deleted != is_deleted
                        or current_deleted_date != deleted_date
                    ):
                        update_event_deletion_fields(
                            newest_event["_id"], is_deleted, deleted_date
                        )
                else:
                    create_new_event(
                        record_id, community_id, event_type, timestamp, is_deleted
                    )
            else:
                if event_type == "removed":
                    # No prior events found, create an addition event first
                    # 1 second before the removal
                    removal_timestamp = arrow.get(timestamp)
                    addition_timestamp = removal_timestamp.shift(seconds=-1)
                    create_new_event(
                        record_id,
                        community_id,
                        "added",
                        addition_timestamp.format("YYYY-MM-DDTHH:mm:ss.SSS"),
                        is_deleted,
                    )
                create_new_event(
                    record_id, community_id, event_type, timestamp, is_deleted
                )

    if community_ids_to_add:
        process_community_events(record_id, community_ids_to_add, "added", timestamp)
    if community_ids_to_remove:
        process_community_events(
            record_id, community_ids_to_remove, "removed", timestamp
        )

    try:
        # Refresh both the alias and the specific write index to ensure
        # all indices are searchable
        client.indices.refresh(index=search_index)
        client.indices.refresh(index=write_index)
    except Exception as e:
        current_app.logger.error(f"Error refreshing community events indices: {e}")


class CommunityAcceptedEventComponent(ServiceComponent):
    """Component to update the community record events on a record.

    Intended for use with the RequestEventsService from invenio-requests.
    This component's create method is called when a request
    for community inclusion or submission is accepted
    and looks for changes to the communities.
    """

    @unit_of_work()
    def create(
        self,
        identity: Identity,
        data: dict,
        event: RequestEvent,
        uow: UnitOfWork,
        **kwargs,
    ) -> None:
        """Update the community record events."""
        current_app.logger.error(f"CommunityAcceptedEventComponent create: {data}")
        request_data = event.request.data  # type: ignore
        valid_request_types = [CommunityInclusion.type_id, CommunitySubmission.type_id]
        valid_request_statuses = [
            CommunityInclusionAcceptAction.status_to,
            CommunitySubmissionAcceptAction.status_to,
        ]

        # invenio-rdm-records removed transfer requests for InvenioRDM 13.0.0
        try:
            valid_request_types.append(CommunityTransferRequest.type_id)
            valid_request_statuses.append(CommunityTransferAcceptAction.status_to)
        except NameError:
            pass

        valid_request = any(
            request_data["type"] == request_type
            and event.get("payload", {}).get("event") == request_status
            for request_type, request_status in zip(
                valid_request_types, valid_request_statuses, strict=True
            )
        )

        if valid_request:
            record = RDMRecord.pid.resolve(request_data["topic"]["record"])  # type: ignore  # noqa: E501

            community_id = request_data["receiver"]["community"]
            record_published_date = record.metadata.get("publication_date")
            update_community_events_index(
                record_id=str(record.pid.pid_value),
                community_ids_to_add=[community_id, "global"],
                record_created_date=record.created,
                record_published_date=record_published_date,
            )


class RecordCommunityEventComponent(ServiceComponent):
    """Component to update the community record events on a record.

    Intended for use with the RDMRecordService from invenio-rdm-records.
    This component's update_record method is called when a record is published
    or deleted and looks for changes to the communities.
    """

    def publish(
        self,
        identity: Identity,
        draft: RDMDraft,
        record: RDMRecord,
        **kwargs,
    ) -> None:
        """Update the community record events.

        Find any changes to the communities field and update the community events
        accordingly on the record.
        """
        current_app.logger.error(f"RecordCommunityEventComponent publish: {record}")
        new_community_ids = {
            c
            for c in (
                record.parent.communities.ids  # type: ignore
                if record.parent.communities  # type: ignore
                else []  # type: ignore
            )
        }
        current_community_ids = set()

        previous_published_version_rec = RDMRecord.get_latest_published_by_parent(
            record.parent
        )

        if previous_published_version_rec and previous_published_version_rec.pid:
            current_community_ids = {
                c.pid.pid_value
                for c in (
                    draft.parent.communities.entries  # type: ignore
                    if draft.parent.communities  # type: ignore
                    else []
                )
            }

        communities_to_add = list(new_community_ids - current_community_ids)
        communities_to_remove = list(current_community_ids - new_community_ids)

        record_published_date = record.metadata.get("publication_date")  # type: ignore
        update_community_events_index(
            record_id=str(record.pid.pid_value),  # type: ignore
            community_ids_to_add=communities_to_add + ["global"],
            community_ids_to_remove=communities_to_remove,
            record_created_date=record.created,
            record_published_date=record_published_date,
        )

    def delete_record(
        self,
        identity: Identity,
        data: dict,
        record: RDMRecord,
        **kwargs,
    ) -> None:
        """Update the community record events.

        Find any changes to the communities field and update the community events
        accordingly on the record.
        """
        current_app.logger.error(f"RecordCommunityEventComponent delete_record: {data}")
        update_community_events_deletion_fields(
            record_id=str(record.pid.pid_value),  # type: ignore
            is_deleted=True,
            deleted_date=arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss.SSS"),
        )

    def restore_record(
        self,
        identity: Identity,
        record: RDMRecord,
        **kwargs,
    ) -> None:
        """Update the community record events when a record is restored.

        Clear the deletion fields for all community events for this record
        when it is restored from a deleted state.
        """
        current_app.logger.error(
            f"RecordCommunityEventComponent restore_record: {record}"
        )
        update_community_events_deletion_fields(
            record_id=str(record.pid.pid_value),  # type: ignore
            is_deleted=False,
            deleted_date=None,
        )


class RecordCommunityEventTrackingComponent(ServiceComponent):
    """Service component that records record add/remove events.

    Intended for use with the RecordCommunitiesService from invenio-rdm-records.
    """

    def add(
        self,
        identity: Identity,
        record: RDMRecord,
        communities: list[dict[str, Any]],
        uow: UnitOfWork,
    ):
        """Record addition of a record in the record metadata."""
        current_app.logger.error(
            f"RecordCommunityEventTrackingComponent add: {communities}"
        )
        community_ids = [community["id"] for community in communities]

        record_published_date = record.metadata.get("publication_date")  # type: ignore
        update_community_events_index(
            record_id=str(record.pid.pid_value),  # type: ignore
            community_ids_to_add=community_ids + ["global"],
            record_created_date=record.created,
            record_published_date=record_published_date,
        )

    def bulk_add(
        self,
        identity: Identity,
        community_id: str,
        record_ids: list[str],
        set_default: dict,
        uow: UnitOfWork,
    ) -> None:
        """Record addition of each record in the community events index."""
        for record_id in record_ids:
            record = current_rdm_records_service.record_cls.pid.resolve(record_id)

            record_published_date = record.metadata.get("publication_date")
            update_community_events_index(
                record_id=str(record.pid.pid_value),
                community_ids_to_add=[community_id, "global"],
                record_created_date=record.created,
                record_published_date=record_published_date,
            )

    def remove_community(
        self,
        identity: Identity,
        record: RDMRecord,
        community: dict[str, Any],
        valid_data: dict[str, Any],
        errors: list[dict[str, Any]],
        uow: UnitOfWork | None = None,
        **kwargs: Any,
    ) -> None:
        """Record removal of a record from a community in the record metadata.

        Parameters:
            identity (Any): The identity performing the action
            record (RDMRecord): The record being removed
            community (dict[str, Any]): The community to remove
            valid_data (dict[str, Any]): The valid data
            errors (list[dict[str, Any]]): The errors to add to
            uow (UnitOfWork | None, optional): The unit of work manager. Defaults
                to None.
            **kwargs (Any): Additional keyword arguments
        """
        current_app.logger.error(
            f"RecordCommunityEventTrackingComponent remove_community: {community}"
        )
        community_id = community["id"]

        record_published_date = record.metadata.get("publication_date")  # type: ignore

        update_community_events_index(
            record_id=str(record.pid.pid_value),  # type: ignore
            community_ids_to_remove=[community_id],
            record_created_date=record.created,
            record_published_date=record_published_date,
        )
        # Note: No need to register RecordCommitOp since we're not modifying the record
