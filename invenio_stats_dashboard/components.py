from typing import Any

import arrow
from flask_principal import Identity
from invenio_drafts_resources.services.records.uow import RecordCommitOp
from invenio_rdm_records.records.api import RDMDraft, RDMRecord
from invenio_rdm_records.services import RDMRecordService
from invenio_rdm_records.services.communities.service import RecordCommunitiesService
from invenio_records_resources.services.records.components.base import ServiceComponent
from invenio_records_resources.services.uow import UnitOfWork


class CommunityEventComponent(ServiceComponent):
    """Component to update the community record events on a record.

    Intended for use with the RDMRecordService from invenio-rdm-records.
    This component's update_record method is called when a record is published
    or deleted and looks for changes to the communities.
    """

    def __init__(self, service: RDMRecordService):
        """Initialize the component."""
        self.service = service

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
        new_community_ids = {
            c["id"]
            for c in (draft.parent.get("communities", []) if draft.parent else [])
        }

        custom_fields = record.custom_fields or {}
        old_events = custom_fields.get("stats:community_events", [])  # type: ignore

        # Create a mapping of community_id to event dict for easier lookup
        event_map = {}
        for event in old_events:
            community_id = event.get("community_id")
            if community_id:
                event_map[community_id] = event

        new_events = []
        updated_events = []

        for community_id in new_community_ids:
            if community_id in event_map:
                existing_event = event_map[community_id]
                if "removed" in existing_event:
                    existing_event["added"] = arrow.utcnow().isoformat()
                    existing_event.pop("removed", None)
                    updated_events.append(community_id)
            else:
                new_event = {
                    "community_id": community_id,
                    "added": arrow.utcnow().isoformat(),
                }
                new_events.append(new_event)

        for community_id, event in event_map.items():
            if community_id not in new_community_ids:
                if "removed" not in event:
                    event["removed"] = arrow.utcnow().isoformat()
                    updated_events.append(community_id)
                if "added" in event:
                    assert arrow.get(event["added"]) < arrow.get(event["removed"])

        all_events = old_events + new_events
        custom_fields["stats:community_events"] = all_events  # type: ignore  # noqa: E501
        record.custom_fields = custom_fields

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
        old_communities = {
            c
            for c in (
                record.parent.communities.ids if record.parent.communities else []
            )
        }
        custom_fields = record.custom_fields or {}
        old_events = custom_fields.get("stats:community_events", [])  # type: ignore

        new_events = []
        for community_id in old_communities:
            matching_event = next(
                (e for e in old_events if e["community_id"] == community_id),
                None,
            )
            if matching_event:
                matching_event["removed"] = arrow.utcnow().isoformat()
            else:
                new_events.append(
                    {
                        "community_id": community_id,
                        "removed": arrow.utcnow().isoformat(),
                    }
                )

        custom_fields["stats:community_events"] = old_events + new_events  # type: ignore  # noqa: E501
        record.custom_fields = custom_fields


class DraftCommunityEventComponent(ServiceComponent):
    """Component to update the community record events on a draft record.

    Intended for use with the RDMRecordService from invenio-rdm-records.
    This component's update_draft method is called when a draft record is updated
    and looks for changes to the communities.
    """

    def __init__(self, service: RDMRecordService):
        """Initialize the component."""
        self.service = service

    def update_draft(
        self,
        identity: Identity,
        data: dict,
        record: RDMDraft,
        errors: list,
        **kwargs,
    ) -> None:
        """Update the community record events.

        Find any changes to the communities field and update the community events
        accordingly on the draft record.

        Args:
            identity (Identity): The identity performing the update.
            data (dict): The data to update the record with (complete record data, not
                just new values).
            record (RDMDraft): The draft being updated.
            errors (list): The list of errors to add to.
            **kwargs: Additional keyword arguments.
        """
        old_communities = record.parent.get("communities", []) if record.parent else []
        new_communities = (
            data.get("parent", {}).get("communities", []) if data.get("parent") else []
        )
        custom_fields = record.custom_fields or {}
        old_events = custom_fields.get("stats:community_events", [])  # type: ignore

        old_community_ids = {c["id"] for c in old_communities}
        new_community_ids = {c["id"] for c in new_communities}

        removed_community_ids = old_community_ids - new_community_ids
        added_community_ids = new_community_ids - old_community_ids

        new_events = []

        for community_id in removed_community_ids:
            existing_event = next(
                (e for e in old_events if e["community_id"] == community_id),
                None,
            )
            if existing_event:
                # Update existing event with removal timestamp
                existing_event["removed"] = arrow.utcnow().isoformat()
            else:
                # Create new removal event
                new_events.append(
                    {
                        "community_id": community_id,
                        "removed": arrow.utcnow().isoformat(),
                    }
                )

        for community_id in added_community_ids:
            existing_event = next(
                (e for e in old_events if e["community_id"] == community_id),
                None,
            )
            if existing_event:
                # Update existing event with addition timestamp
                existing_event["added"] = arrow.utcnow().isoformat()
            else:
                # Create new addition event
                new_events.append(
                    {
                        "community_id": community_id,
                        "added": arrow.utcnow().isoformat(),
                    }
                )

        # Update the custom fields with modified events and new events
        custom_fields["stats:community_events"] = old_events + new_events  # type: ignore  # noqa: E501
        record.custom_fields = custom_fields


class RecordCommunityEventComponent(ServiceComponent):
    """Service component that records record add/remove events.

    Intended for use with the RecordCommunitiesService from invenio-rdm-records.
    """

    def __init__(self, service: RecordCommunitiesService):
        """Initialize the component."""
        self.service = service

    def add(self, identity: Identity, id_: str, data: dict[str, Any], uow: UnitOfWork):
        """Record addition of a record in the record metadata."""
        custom_fields = data.get("custom_fields", {})
        custom_fields.setdefault("stats:community_events", []).append(
            {
                "community_id": data["communities"][0]["id"],
                "added": arrow.utcnow().isoformat(),
            }
        )
        data["custom_fields"] = custom_fields

    def bulk_add(
        self,
        identity: Identity,
        record_ids: list[str],
        community_id: str,
        set_default: bool,
        uow: UnitOfWork,
    ) -> None:
        """Record addition of each record in the record metadata."""

        for record_id in record_ids:
            record = self.service.record_cls.pid.resolve(record_id)

            custom_fields = record.custom_fields
            custom_fields.setdefault("stats:community_events", []).append(
                {
                    "community_id": community_id,
                    "added": arrow.utcnow().isoformat(),
                }
            )

            uow.register(
                RecordCommitOp(
                    record,
                    indexer=self.service.indexer,
                )
            )

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
        communities_to_remove = [c["id"] for c in communities]
        custom_fields = record.custom_fields or {}
        new_events = []
        for community in communities_to_remove:
            new_events.append(
                {
                    "community_id": community,
                    "removed": arrow.utcnow().isoformat(),
                }
            )
        old_events = custom_fields.get("stats:community_events", [])  # type: ignore
        custom_fields["stats:community_events"] = old_events + new_events  # type: ignore  # noqa: E501
        record.custom_fields = custom_fields
