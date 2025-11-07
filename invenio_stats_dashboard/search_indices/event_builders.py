# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
#
# Copyright (C) 2025 Mesh Research
#
# Based on the original event builders from invenio-rdm-records:
#
# Copyright (C) 2023 TU Wien.
#
# Invenio Stats Dashboard and invenio-rdm-records are free software; you
# can redistribute and/or modify them under the terms of the MIT License;
# see LICENSE file for more details.

"""Custom event builders to support advanced statistics aggregations.

Note that the arguments to these functions will be the same as passed to the
``EventEmitter`` objects when they are called.
Currently in InvenioRDM this is done in resources (for API) and view functions (for UI).
As such, it is assumed that a request context is available (and thus, Flask's global
``request`` is accessible).
"""

from datetime import datetime
from typing import Any

from flask import request
from invenio_records_resources.records.systemfields.relations import (
    PIDListRelation,
)
from invenio_stats.utils import get_user


def _flatten_affiliations(creators_and_contributors: list) -> list:
    """Flatten affiliations from creators and contributors into a single list.

    Each creator/contributor has a list of affiliations, so we get a list of lists.
    This function flattens: [[aff1, aff2], [aff3]] -> [aff1, aff2, aff3]

    Args:
        creators_and_contributors: List of creator/contributor dicts

    Returns:
        Flat list of affiliation dicts
    """
    affiliations = []
    for person in creators_and_contributors:
        person_affiliations = person.get("affiliations", [])
        if person_affiliations:
            affiliations.extend(person_affiliations)
    return affiliations


def file_download_event_builder(
    event: dict[str, Any], sender_app: str, **kwargs: Any
) -> dict[str, Any] | None:
    """Build a file-download event.

    *Note* that this function assumes a request context by accessing properties of
    Flask's global ``request`` object.

    Returns:
        dict: A dictionary ready to be indexed as a file download event.
    """
    assert "record" in kwargs
    assert "obj" in kwargs

    record = kwargs["record"]
    obj = kwargs["obj"]
    file_type = (
        obj.file.ext
        if hasattr(obj.file, "ext")
        else obj.key.split(".")[-1].lower()
        if "." in obj.key
        else None
    )

    # Access vocabulary fields through relations to ensure they're resolved.
    # For file downloads, the record comes from get_file_content() which doesn't
    # go through the same expansion as read(), so relations may not be resolved
    # when accessing metadata directly. Accessing via relations ensures resolution.
    def _get_vocabulary_field(
        relation_name: str, metadata_key: str | None = None
    ):
        """Get a vocabulary field with resolved relations.

        Args:
            relation_name: Name of the relation field
                (e.g., "resource_type", "languages")
            metadata_key: Metadata key to use as fallback
                (defaults to relation_name)

        Returns:
            Resolved vocabulary object(s) or metadata fallback
        """
        if metadata_key is None:
            metadata_key = relation_name

        if hasattr(record, "relations") and hasattr(
            record.relations, relation_name
        ):
            try:
                relation = getattr(record.relations, relation_name)
                resolved = relation()

                if resolved:
                    # Check if this is a list relation or single relation
                    # by checking the relation type, not the resolved value
                    if isinstance(relation, PIDListRelation):
                        # List relation (e.g., languages, subjects, rights)
                        try:
                            resolved_list = list(resolved)
                            if resolved_list:
                                return [
                                    item.to_dict()
                                    for item in resolved_list
                                    if hasattr(item, "to_dict")
                                ]
                        except TypeError:
                            # Not iterable, return None
                            pass
                    else:
                        # Single relation (e.g., resource_type)
                        if hasattr(resolved, "to_dict"):
                            return resolved.to_dict()
            except Exception:
                pass

        # Fallback to metadata if relations unavailable
        return record.metadata.get(metadata_key)

    event.update({
        # When:
        "timestamp": datetime.utcnow().isoformat(),
        # What:
        "bucket_id": str(obj.bucket_id),
        "file_id": str(obj.file_id),
        "file_key": obj.key,
        "size": obj.file.size,
        "recid": record["id"],
        "parent_recid": record.parent["id"],
        # Who:
        "referrer": request.referrer,
        **get_user(),
        "resource_type": _get_vocabulary_field("resource_type"),
        "access_status": record.access.status.value,
        "publisher": record.metadata.get("publisher", None),
        "languages": _get_vocabulary_field("languages"),
        "subjects": _get_vocabulary_field("subjects"),
        "journal_title": (
            record.custom_fields.get("journal:journal", {}).get("title", None)
        ),
        # Note: relation name is "licenses" but it manages metadata["rights"]
        "rights": _get_vocabulary_field("licenses", "rights"),
        "funders": [f.get("funder") for f in record.metadata.get("funding", [])],
        "affiliations": _flatten_affiliations(
            record.metadata.get("contributors", [])
            + record.metadata.get("creators", [])
        ),
        "file_types": [file_type] if file_type else None,
    })
    return event


def record_view_event_builder(
    event: dict[str, Any], sender_app: str, **kwargs: Any
) -> dict[str, Any] | None:
    """Build a record-view event.

    *Note* that this function assumes a request context by accessing properties of
    Flask's global ``request`` object.

    Returns:
        dict: A dictionary ready to be indexed as a record view event.
    """
    assert "record" in kwargs
    record = kwargs["record"]

    is_published = getattr(record, "is_published", False)
    is_draft = getattr(record, "is_draft", True)

    # drop not published records
    if is_published and not is_draft:
        file_types = (
            [file.ext for file in record.files.values() if hasattr(file, "ext")]
            if record.files.enabled
            else None
        )
        event.update({
            # When:
            "timestamp": datetime.utcnow().isoformat(),
            # What:
            "recid": record["id"],
            "parent_recid": record.parent["id"],
            # Who:
            "referrer": request.referrer,
            **get_user(),
            # TODO probably we can add more request context information here for
            #      extra filtering (e.g. URL or query params for discarding the
            #      event when it's a citation text export)
            "community_ids": (
                record.parent.communities.ids if record.parent.communities else []
            ),
            "resource_type": record.metadata["resource_type"],
            "access_status": record.access.status.value,
            "languages": record.metadata.get("languages", None),
            "subjects": record.metadata.get("subjects", None),
            "publisher": record.metadata.get("publisher", None),
            "journal_title": (
                record.custom_fields.get("journal:journal", {}).get("title", None)
            ),
            "rights": record.metadata.get("rights", None),
            "funders": [f.get("funder") for f in record.metadata.get("funding", [])],
            "affiliations": _flatten_affiliations(
                record.metadata.get("contributors", [])
                + record.metadata.get("creators", [])
            ),
            "file_types": file_types,
        })
        return event
    return None
