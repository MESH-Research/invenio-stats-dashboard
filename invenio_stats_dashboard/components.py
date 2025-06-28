from pprint import pformat
from typing import Any

import arrow
from flask import current_app
from flask_principal import Identity
from invenio_access.permissions import system_identity
from invenio_drafts_resources.services.records.uow import RecordCommitOp
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_rdm_records.records.api import RDMDraft, RDMRecord
from invenio_rdm_records.requests.community_inclusion import (
    CommunityInclusion,
    AcceptAction as CommunityInclusionAcceptAction,
)
from invenio_rdm_records.requests.community_submission import (
    CommunitySubmission,
    AcceptAction as CommunitySubmissionAcceptAction,
)
from invenio_rdm_records.requests.community_transfer import (
    CommunityTransferRequest,
    AcceptCommunityTransfer as CommunityTransferAcceptAction,
)
from invenio_records_resources.services.records.components.base import ServiceComponent
from invenio_records_resources.services.uow import UnitOfWork, unit_of_work
from invenio_requests.records.api import RequestEvent
from invenio_search import current_search_client
from invenio_search.utils import prefix_index


def update_event_deletion_fields(
    event_id: str, is_deleted: bool, deleted_date: str | None
):
    """Update deletion-related fields and updated_timestamp for an existing event."""
    client = current_search_client
    search_index = prefix_index("stats-community-events")

    update_doc = {
        "doc": {
            "is_deleted": is_deleted,
            "updated_timestamp": arrow.utcnow().isoformat(),
        }
    }
    if deleted_date:
        update_doc["doc"]["deleted_date"] = deleted_date

    try:
        client.update(index=search_index, id=event_id, body=update_doc)
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

    # Find all events for this record and update their deletion fields
    query = {
        "query": {"term": {"record_id": record_id}},
        "size": 1000,  # Adjust if needed for large numbers of events
    }

    try:
        result = client.search(index=search_index, body=query)
        if result["hits"]["total"]["value"] > 0:
            for hit in result["hits"]["hits"]:
                event_id = hit["_id"]
                event_source = hit["_source"]
                current_is_deleted = event_source.get("is_deleted", False)
                current_deleted_date = event_source.get("deleted_date")

                # Only update if the deletion status has changed
                if (
                    current_is_deleted != is_deleted
                    or current_deleted_date != deleted_date
                ):
                    update_event_deletion_fields(event_id, is_deleted, deleted_date)

            current_app.logger.info(
                f"Updated deletion fields for {result['hits']['total']['value']} community events for record {record_id}"
            )
        else:
            current_app.logger.info(
                f"No community events found for record {record_id} to update deletion fields"
            )
    except Exception as e:
        current_app.logger.error(
            f"Error updating deletion fields for all events of record {record_id}: {e}"
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
) -> None:
    """Update the community events index with new events.

    This function manages record community events in a separate search index.

    Args:
        record_id: The record ID
        community_ids_to_add: List of community IDs to mark as added
        community_ids_to_remove: List of community IDs to mark as removed
        timestamp: ISO format timestamp to use (defaults to current UTC time)
        record_created_date: When the record was created
        record_published_date: When the record was published
        is_deleted: Whether the record is deleted
        deleted_date: When the record was deleted
    """
    if timestamp is None:
        timestamp = arrow.utcnow().isoformat()

    client = current_search_client
    # Use alias for searching across all annual indices
    search_index = prefix_index("stats-community-events")

    # Determine the specific annual index for writing based on event timestamp
    event_year = arrow.get(timestamp).year
    write_index = prefix_index(f"stats-community-events-{event_year}")

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
                    f"No prior events found for record {record_id}, community {community_id} when attempting removal"
                )
        except Exception as e:
            current_app.logger.error(
                f"Error querying community events index for record {record_id}, community {community_id}: {e}"
            )
        return None

    def create_new_event(
        record_id: str, community_id: str, event_type: str, event_date: str
    ):
        """Create a new community event in the appropriate annual index."""
        event_doc = {
            "record_id": record_id,
            "community_id": community_id,
            "event_type": event_type,
            "event_date": event_date,
            "record_created_date": record_created_date,
            "record_published_date": record_published_date,
            "is_deleted": is_deleted,
            "timestamp": arrow.utcnow().isoformat(),
            "updated_timestamp": arrow.utcnow().isoformat(),
        }
        if deleted_date:
            event_doc["deleted_date"] = deleted_date

        try:
            client.index(index=write_index, body=event_doc)
        except Exception as e:
            current_app.logger.error(
                f"Error creating new community event for record {record_id}, community {community_id}: {e}"
            )

    def process_community_events(
        record_id: str, community_ids: list[str], event_type: str, timestamp: str
    ):
        """Process community events (additions or removals) with common logic."""
        for community_id in community_ids:
            # For removals, always check if there's an addition event first
            if event_type == "removed":
                addition_query = {
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"record_id": record_id}},
                                {"term": {"community_id": community_id}},
                                {"term": {"event_type": "added"}},
                            ]
                        }
                    },
                    "size": 1,
                }

                try:
                    addition_result = client.search(
                        index=search_index, body=addition_query
                    )
                    if addition_result["hits"]["total"]["value"] == 0:
                        # No addition event found - create dummy addition event one second before removal
                        addition_timestamp = (
                            arrow.get(timestamp).shift(seconds=-1).isoformat()
                        )
                        current_app.logger.error(
                            f"No addition event found for record {record_id}, community {community_id}. "
                            f"Creating addition event at {addition_timestamp} before removal at {timestamp}"
                        )
                        create_new_event(
                            record_id, community_id, "added", addition_timestamp
                        )
                        create_new_event(record_id, community_id, "removed", timestamp)
                        continue  # Skip the rest of the logic since we've handled this case
                except Exception as e:
                    current_app.logger.error(
                        f"Error checking for addition events for record {record_id}, community {community_id}: {e}"
                    )

            # Normal event processing logic
            newest_event = get_newest_event(
                record_id, community_id, is_removal=(event_type == "removed")
            )

            if newest_event:
                newest_event_source = newest_event["_source"]
                newest_event_type = newest_event_source["event_type"]

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
                    create_new_event(record_id, community_id, event_type, timestamp)
            else:
                create_new_event(record_id, community_id, event_type, timestamp)

    if community_ids_to_add:
        process_community_events(record_id, community_ids_to_add, "added", timestamp)
    if community_ids_to_remove:
        process_community_events(
            record_id, community_ids_to_remove, "removed", timestamp
        )

    try:
        client.indices.refresh(index=write_index)
        client.indices.refresh(index=search_index)
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
        current_app.logger.error("ACCEPTED EVENT COMPONENT ******************")
        current_app.logger.error(f"data: {pformat(data)}")
        current_app.logger.error(f"event: {pformat(event)}")
        current_app.logger.error(f"type: {event.type}")
        current_app.logger.error(f"payload: {dir(event)}")
        current_app.logger.error(f"payload: {pformat(event.metadata)}")
        current_app.logger.error(f"payload: {pformat(event.get('payload'))}")
        request_data = event.request.data
        current_app.logger.error(f"request: {pformat(request_data)}")
        current_app.logger.error(CommunityInclusion.type_id)
        current_app.logger.error(CommunityInclusionAcceptAction.status_to)
        current_app.logger.error(CommunitySubmission.type_id)
        current_app.logger.error(CommunitySubmissionAcceptAction.status_to)
        current_app.logger.error(CommunityTransferRequest.type_id)
        current_app.logger.error(CommunityTransferAcceptAction.status_to)

        # TODO: Direct community inclusion seems not to produce an "L" log event
        # but only a "C" comment event?
        if (
            (
                request_data["type"] == CommunityInclusion.type_id
                and event.get("payload").get("event")
                == CommunityInclusionAcceptAction.status_to
            )
            or (
                request_data["type"] == CommunitySubmission.type_id
                and event.get("payload").get("event")
                == CommunitySubmissionAcceptAction.status_to
            )
            or (
                request_data["type"] == CommunityTransferRequest.type_id
                and event.get("payload").get("event")
                == CommunityTransferAcceptAction.status_to
            )
        ):
            current_app.logger.error(
                f"in accepted component, record: "
                f"{pformat(request_data['topic']['record'])}"
            )
            record = RDMRecord.pid.resolve(request_data["topic"]["record"])
            current_app.logger.error(f"record: {pformat(record)}")
            metadata = record.metadata
            current_app.logger.error(f"metadata: {pformat(metadata)}")

            # Use centralized function to update community events index
            community_id = request_data["receiver"]["community"]
            update_community_events_index(
                record_id=str(record.id),
                community_ids_to_add=[community_id],
            )

            current_app.logger.error(
                f"Updated community events index for record {record.id} and community {community_id}"
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
        current_app.logger.error("PUBLISH COMPONENT ******************")
        current_app.logger.error(f"in publish component, draft: {pformat(draft.id)}")
        current_app.logger.error(
            f"in publish component, draft parent: {pformat(draft.parent)}"
        )
        current_app.logger.error(f"published?: {pformat(record.is_published)}")

        new_community_ids = {
            c
            for c in (
                record.parent.communities.ids
                if record.parent.communities
                else []  # type: ignore
            )
        }
        current_community_ids = set()

        current_app.logger.error(
            f"in publish component, record parent: {pformat(record.parent)}"
        )

        previous_published_version_rec = RDMRecord.get_latest_published_by_parent(
            record.parent
        )
        current_app.logger.error(
            f"previous_published_version_rec: {pformat(previous_published_version_rec.parent)}"
        )
        current_app.logger.error(
            f"previous_published_version_rec: {pformat(previous_published_version_rec.metadata)}"
        )
        if previous_published_version_rec and previous_published_version_rec.pid:
            previous_published_version = current_rdm_records_service.read(
                system_identity,
                id_=previous_published_version_rec.pid.pid_value,  # type: ignore
            )
            current_app.logger.error(
                f"previous_published_version: {pformat(previous_published_version.to_dict())}"
            )

            current_community_ids = {
                c["id"]
                for c in (
                    draft.parent.communities.get("entries", []) if draft.parent else []
                )
            }
            current_app.logger.error(
                f"current_community_ids: {pformat(current_community_ids)}"
            )

        current_app.logger.error(
            f"in publish component, new_community_ids: " f"{pformat(new_community_ids)}"
        )

        # Determine communities to add and remove
        communities_to_add = list(new_community_ids - current_community_ids)
        communities_to_remove = list(current_community_ids - new_community_ids)

        # Use centralized function to update community events index
        update_community_events_index(
            record_id=str(record.id),
            community_ids_to_add=communities_to_add,
            community_ids_to_remove=communities_to_remove,
        )

        current_app.logger.error(
            f"Updated community events index for record {record.id}: added {communities_to_add}, removed {communities_to_remove}"
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
        current_app.logger.error("DELETE COMPONENT ******************")

        # Update deletion fields for all community events for this record
        update_community_events_deletion_fields(
            record_id=str(record.id),
            is_deleted=True,
            deleted_date=arrow.utcnow().isoformat(),
        )

        current_app.logger.error(
            f"Updated deletion fields for all community events for record {record.id}"
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
        current_app.logger.error("RESTORE COMPONENT ******************")

        # Update deletion fields for all community events for this record
        update_community_events_deletion_fields(
            record_id=str(record.id),
            is_deleted=False,
            deleted_date=None,
        )

        current_app.logger.error(
            f"Cleared deletion fields for all community events for record {record.id}"
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
        current_app.logger.error("ADD COMPONENT ******************")
        current_app.logger.error(f"in add component, record: {pformat(record)}")
        current_app.logger.error(
            f"in add component, communities: {pformat(communities)}"
        )

        # Extract community IDs from the communities list
        community_ids = [community["id"] for community in communities]

        # Use centralized function to update community events index
        update_community_events_index(
            record_id=str(record.id),
            community_ids_to_add=community_ids,
        )

        current_app.logger.error(
            f"Updated community events index for record {record.id}: added communities {community_ids}"
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

            # Use centralized function to update community events index
            update_community_events_index(
                record_id=str(record.id),
                community_ids_to_add=[community_id],
            )

            # Note: No need to register RecordCommitOp since we're not modifying the record
            # The community events are now stored in a separate index

    def remove(
        self,
        identity: Identity,
        record: RDMRecord,
        communities: list[dict[str, Any]],
        valid_data: dict[str, Any],
        errors: list[dict[str, Any]],
        uow: UnitOfWork | None = None,
        **kwargs: Any,
    ) -> None:
        """Record removal of a record in the record metadata.

        Parameters:
            identity (Any): The identity performing the action
            record (RDMRecord): The record being removed
            communities (list[dict[str, Any]]): The communities to remove
            errors (list[dict[str, Any]]): The errors to add to
            uow (UnitOfWork | None, optional): The unit of work manager. Defaults
                to None.
            **kwargs (Any): Additional keyword arguments
        """
        current_app.logger.error("REMOVE COMPONENT ******************")
        communities_to_remove = [c["id"] for c in communities]

        # Use centralized function to update community events index
        update_community_events_index(
            record_id=str(record.id),
            community_ids_to_remove=communities_to_remove,
        )

        current_app.logger.error(
            f"Updated community events index for record {record.id}: removed communities {communities_to_remove}"
        )
        # Note: No need to register RecordCommitOp since we're not modifying the record
        # The community events are now stored in a separate index
