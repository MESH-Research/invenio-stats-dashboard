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

from flask import request
from invenio_stats.utils import get_user


def file_download_event_builder(event, sender_app, **kwargs):
    """Build a file-download event.

    *Note* that this function assumes a request context by accessing properties of
    Flask's global ``request`` object.
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
        "resource_type": record.metadata["resource_type"],
        "access_status": record.access.status.value,
        "publisher": record.metadata.get("publisher", None),
        "languages": record.metadata.get("languages", None),
        "subjects": record.metadata.get("subjects", None),
        "journal_title": (
            record.custom_fields.get("journal:journal", {}).get("title", None)
        ),
        "rights": record.metadata.get("rights", None),
        "funders": [f.get("funder") for f in record.metadata.get("funding", [])],
        "affiliations": [
            c.get("affiliations")
            for c in record.metadata.get("contributors", [])
            + record.metadata.get("creators", [])
        ],
        "file_type": file_type,
    })
    return event


def record_view_event_builder(event, sender_app, **kwargs):
    """Build a record-view event.

    *Note* that this function assumes a request context by accessing properties of
    Flask's global ``request`` object.
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
            "affiliations": [
                c.get("affiliations")
                for c in record.metadata.get("contributors", [])
                + record.metadata.get("creators", [])
            ],
            "file_types": file_types,
        })
        return event
    return None
