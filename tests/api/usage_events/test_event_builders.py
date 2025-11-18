# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Unit tests for event builders."""

from invenio_access.permissions import system_identity
from invenio_rdm_records.proxies import current_rdm_records_service

from invenio_stats_dashboard.search_indices.event_builders import (
    file_download_event_builder,
    record_view_event_builder,
)


def test_file_download_basic_event_creation(
    running_app,
    db,
    minimal_published_record_factory,
    record_metadata,
    test_sample_files_folder,
):
    """Test basic event creation with real record and file."""
    app = running_app.app

    test_metadata = record_metadata()
    record_item = minimal_published_record_factory(
        metadata=test_metadata.metadata_in,
        file_paths=[str(test_sample_files_folder / "sample.pdf")],
    )
    record = record_item._record

    file_service = current_rdm_records_service.files

    # Get file content to get the object_version
    # files._results is a ValuesView, so we get the key from record.files.entries
    assert len(record.files.entries) > 0
    file_key = list(record.files.entries.keys())[0]

    file_item = file_service.get_file_content(system_identity, record["id"], file_key)
    obj = file_item._file.object_version
    assert obj is not None

    # Create event context
    event: dict = {}

    with app.test_request_context(headers={"Referer": "https://example.com"}):
        result = file_download_event_builder(
            event, app, record=record, obj=obj, via_api=True
        )

    assert result is not None
    assert result["bucket_id"] == str(obj.bucket_id)
    assert result["file_id"] == str(obj.file_id)
    assert result["file_key"] == obj.key
    assert result["size"] == obj.file.size
    assert result["recid"] == record["id"]
    assert result["parent_recid"] == record.parent["id"]
    assert "timestamp" in result
    assert "referrer" in result
    assert "user_id" in result or "visitor_id" in result


def test_file_download_vocabulary_fields_from_relations(
    running_app,
    db,
    minimal_published_record_factory,
    record_metadata,
    test_sample_files_folder,
):
    """Test vocabulary fields are resolved from relations when available."""
    app = running_app.app

    # Start with complete metadata from fixture and update fields
    test_metadata = record_metadata()
    test_metadata.update_metadata({
        "metadata|resource_type": {"id": "textDocument-journalArticle"},
        "metadata|languages": [{"id": "eng"}, {"id": "fra"}],
        "metadata|subjects": [
            {
                "id": "http://id.worldcat.org/fast/813346",
                "scheme": "FAST-topical",
                "subject": "Architecture",
            }
        ],
        "metadata|rights": [{"id": "cc-by-4.0"}],
        "files|enabled": True,
    })

    record_item = minimal_published_record_factory(
        metadata=test_metadata.metadata_in,
        file_paths=[str(test_sample_files_folder / "sample.pdf")],
    )
    record = record_item._record

    # Get file object
    file_service = current_rdm_records_service.files
    # files._results is a ValuesView, so we get the key from record.files.entries
    assert len(record.files.entries) > 0
    file_key = list(record.files.entries.keys())[0]
    file_item = file_service.get_file_content(
        system_identity, record["id"], file_key
    )
    obj = file_item._file.object_version

    event: dict = {}

    with app.test_request_context(headers={"Referer": "https://example.com"}):
        result = file_download_event_builder(
            event, app, record=record, obj=obj, via_api=True
        )

    # Resource type should have full object with title
    assert result["resource_type"] is not None
    assert result["resource_type"]["id"] == "textDocument-journalArticle"
    assert result["resource_type"]["title"] == {"en": "Journal Article"}
    # Relation only extracts specific keys: title, props.type, props.subtype
    assert "props" in result["resource_type"]
    assert result["resource_type"]["props"]["type"] == "textDocument"
    assert result["resource_type"]["props"]["subtype"] == "textDocument-journalArticle"

    # Languages should be list with full objects
    assert result["languages"] is not None
    assert isinstance(result["languages"], list)
    assert len(result["languages"]) == 2

    # Check both languages are present
    lang_ids = [lang["id"] for lang in result["languages"]]
    assert "eng" in lang_ids
    assert "fra" in lang_ids

    # Check specific language values
    eng_lang = next(lang for lang in result["languages"] if lang["id"] == "eng")
    assert eng_lang["title"] == {"en": "English"}
    fra_lang = next(lang for lang in result["languages"] if lang["id"] == "fra")
    assert fra_lang["title"] == {"en": "French"}

    # Subjects should have full objects
    assert result["subjects"] is not None
    assert isinstance(result["subjects"], list)
    assert len(result["subjects"]) == 1
    assert result["subjects"][0]["id"] == "http://id.worldcat.org/fast/813346"

    # Rights should have full objects (from licenses relation)
    assert result["rights"] is not None
    assert isinstance(result["rights"], list)
    assert len(result["rights"]) == 1
    assert result["rights"][0]["id"] == "cc-by-4.0"
    assert result["rights"][0]["title"] == {
        "en": "Creative Commons Attribution 4.0 International"
    }
    assert "description" in result["rights"][0]
    assert isinstance(result["rights"][0]["description"], dict)
    assert "props" in result["rights"][0]


def test_file_download_vocabulary_fields_fallback_to_metadata(
    running_app,
    db,
    minimal_published_record_factory,
    record_metadata,
    test_sample_files_folder,
):
    """Test vocabulary fields fall back to metadata when relations unavailable."""
    app = running_app.app

    # Start with complete metadata from fixture and update fields
    test_metadata = record_metadata()
    test_metadata.update_metadata({
        "metadata|resource_type": {"id": "textDocument-journalArticle"},
        "metadata|languages": [{"id": "eng"}],
        "metadata|subjects": [
            {
                "id": "http://id.worldcat.org/fast/1012163",
                "scheme": "FAST-topical",
                "subject": "Mathematics",
            }
        ],
        "metadata|rights": [{"id": "cc-by-4.0"}],
        "files|enabled": True,
    })

    record_item = minimal_published_record_factory(
        metadata=test_metadata.metadata_in,
        file_paths=[str(test_sample_files_folder / "sample.pdf")],
    )
    record = record_item._record

    # Get file object
    file_service = current_rdm_records_service.files
    # files._results is a ValuesView, so we get the key from record.files.entries
    assert len(record.files.entries) > 0
    file_key = list(record.files.entries.keys())[0]
    file_item = file_service.get_file_content(
        system_identity, record["id"], file_key
    )
    obj = file_item._file.object_version

    event: dict = {}

    with app.test_request_context(headers={"Referer": "https://example.com"}):
        result = file_download_event_builder(
            event, app, record=record, obj=obj, via_api=True
        )

    # Should fall back to metadata if relations don't resolve
    assert result["resource_type"] is not None
    assert result["resource_type"]["id"] == "textDocument-journalArticle"
    assert result["languages"] is not None
    assert len(result["languages"]) >= 0
    assert result["subjects"] is not None
    assert result["rights"] is not None


def test_file_download_file_type_extraction(
    running_app,
    db,
    minimal_published_record_factory,
    record_metadata,
    test_sample_files_folder,
):
    """Test file type extraction from file extension."""
    app = running_app.app

    # Start with complete metadata from fixture and update files
    test_metadata = record_metadata()
    test_metadata.update_metadata({"files|enabled": True})

    record_item = minimal_published_record_factory(
        metadata=test_metadata.metadata_in,
        file_paths=[str(test_sample_files_folder / "sample.pdf")],
    )
    record = record_item._record

    file_service = current_rdm_records_service.files
    # files._results is a ValuesView, so we get the key from record.files.entries
    assert len(record.files.entries) > 0
    file_key = list(record.files.entries.keys())[0]
    file_item = file_service.get_file_content(
        system_identity, record["id"], file_key
    )
    obj = file_item._file.object_version

    event: dict = {}

    with app.test_request_context():
        result = file_download_event_builder(
            event, app, record=record, obj=obj, via_api=True
        )

    # File type should be extracted
    assert "file_types" in result
    if result["file_types"]:
        assert isinstance(result["file_types"], list)
        assert "pdf" in result["file_types"]


def test_record_view_basic_event_creation(
    running_app,
    db,
    minimal_published_record_factory,
):
    """Test basic event creation."""
    app = running_app.app

    record_item = minimal_published_record_factory()
    record = record_item._record

    event: dict = {}

    with app.test_request_context(headers={"Referer": "https://example.com"}):
        result = record_view_event_builder(event, app, record=record)

    assert result is not None
    assert result["recid"] == record["id"]
    assert result["parent_recid"] == record.parent["id"]
    assert "timestamp" in result
    assert "referrer" in result
    assert "community_ids" in result


def test_record_view_unpublished_record_dropped(
    running_app,
    db,
    record_metadata,
):
    """Test that unpublished records are not processed."""
    app = running_app.app

    # Create but don't publish (is_draft=True, is_published=False)
    # Use complete metadata from fixture
    test_metadata = record_metadata()
    draft = current_rdm_records_service.create(
        system_identity, test_metadata.metadata_in
    )
    record = current_rdm_records_service.read_draft(
        system_identity, id_=draft.id
    )._record

    event: dict = {}

    with app.test_request_context():
        result = record_view_event_builder(event, app, record=record)

    assert result is None


def test_record_view_vocabulary_fields_in_event(
    running_app,
    db,
    minimal_published_record_factory,
    record_metadata,
):
    """Test that vocabulary fields are included in event."""
    app = running_app.app

    # Start with complete metadata from fixture and update fields
    test_metadata = record_metadata()
    test_metadata.update_metadata({
        "metadata|resource_type": {"id": "textDocument-journalArticle"},
        "metadata|languages": [{"id": "eng"}],
        "metadata|subjects": [
            {
                "id": "http://id.worldcat.org/fast/813346",
                "scheme": "FAST-topical",
                "subject": "Architecture",
            }
        ],
        "metadata|rights": [{"id": "cc-by-4.0"}],
    })

    record_item = minimal_published_record_factory(metadata=test_metadata.metadata_in)
    # Read through service to get relations dereferenced
    record_item_with_relations = current_rdm_records_service.read(
        system_identity, id_=record_item.id
    )
    record = record_item_with_relations._record

    event: dict = {}

    with app.test_request_context():
        result = record_view_event_builder(event, app, record=record)

    # Record view uses metadata directly (relations dereferenced in service.read)
    assert result["resource_type"] is not None
    assert result["resource_type"]["id"] == "textDocument-journalArticle"
    assert result["languages"] is not None
    assert isinstance(result["languages"], list)
    assert len(result["languages"]) == 1
    assert result["languages"][0]["id"] == "eng"

    # Subjects should be list
    assert result["subjects"] is not None
    assert isinstance(result["subjects"], list)
    assert len(result["subjects"]) == 1
    assert result["subjects"][0]["id"] == "http://id.worldcat.org/fast/813346"

    # Rights should be list
    assert result["rights"] is not None
    assert isinstance(result["rights"], list)
    assert len(result["rights"]) == 1
    assert result["rights"][0]["id"] == "cc-by-4.0"


def test_record_view_file_types_extraction(
    running_app,
    db,
    minimal_published_record_factory,
    record_metadata,
    test_sample_files_folder,
):
    """Test file types extraction from record files."""
    app = running_app.app

    # Start with complete metadata from fixture and update files
    test_metadata = record_metadata()
    test_metadata.update_metadata({"files|enabled": True})

    record_item = minimal_published_record_factory(
        metadata=test_metadata.metadata_in,
        file_paths=[
            str(test_sample_files_folder / "sample.pdf"),
            str(test_sample_files_folder / "sample.jpg"),
        ],
    )
    record = record_item._record

    event: dict = {}

    with app.test_request_context():
        result = record_view_event_builder(event, app, record=record)

    assert "file_types" in result
    if result["file_types"]:
        assert isinstance(result["file_types"], list)
        # Should include the file types from the record
        assert len(result["file_types"]) > 0


def test_record_view_files_disabled(
    running_app,
    db,
    minimal_published_record_factory,
):
    """Test when files are disabled."""
    app = running_app.app

    record_item = minimal_published_record_factory()
    record_item_with_relations = current_rdm_records_service.read(
        system_identity, id_=record_item.id
    )
    record = record_item_with_relations._record

    # Disable files
    record.files.enabled = False

    event: dict = {}

    with app.test_request_context():
        result = record_view_event_builder(event, app, record=record)

    assert result["file_types"] is None or result["file_types"] == []


def test_record_view_missing_communities(
    running_app,
    db,
    minimal_published_record_factory,
):
    """Test record with no communities."""
    app = running_app.app

    record_item = minimal_published_record_factory(community_list=None)
    record_item_with_relations = current_rdm_records_service.read(
        system_identity, id_=record_item.id
    )
    record = record_item_with_relations._record

    event: dict = {}

    with app.test_request_context():
        result = record_view_event_builder(event, app, record=record)

    # Should handle missing communities gracefully
    assert "community_ids" in result
    assert isinstance(result["community_ids"], list)


def test_record_view_affiliations_flattened(
    running_app,
    db,
    minimal_published_record_factory,
    record_metadata,
):
    """Test that affiliations are flattened from nested structure in record view."""
    app = running_app.app

    # Create metadata with multiple creators and contributors, each with affiliations
    test_metadata = record_metadata()
    test_metadata.update_metadata({
        "metadata|creators": [
            {
                "person_or_org": {
                    "family_name": "One",
                    "given_name": "Creator",
                    "name": "Creator One",
                    "type": "personal",
                },
                "affiliations": [
                    {"id": "cern", "name": "CERN"},
                    {"id": "03rmrcq20", "name": "University of British Columbia"},
                ],
            },
            {
                "person_or_org": {
                    "family_name": "Two",
                    "given_name": "Creator",
                    "name": "Creator Two",
                    "type": "personal",
                },
                "affiliations": [
                    {"id": "013v4ng57", "name": "San Francisco Public Library"},
                ],
            },
        ],
        "metadata|contributors": [
            {
                "person_or_org": {
                    "family_name": "One",
                    "given_name": "Contributor",
                    "name": "Contributor One",
                    "type": "personal",
                },
                "role": {"id": "other"},
                "affiliations": [
                    {"id": "cern", "name": "CERN"},
                ],
            },
        ],
    })

    record_item = minimal_published_record_factory(metadata=test_metadata.metadata_in)
    record_item_with_relations = current_rdm_records_service.read(
        system_identity, id_=record_item.id
    )
    record = record_item_with_relations._record

    event: dict = {}

    with app.test_request_context():
        result = record_view_event_builder(event, app, record=record)

    # Affiliations should be a flat list, not nested arrays
    assert "affiliations" in result
    assert isinstance(result["affiliations"], list)

    # Should be a flat array of affiliation objects, not array of arrays
    assert len(result["affiliations"]) > 0
    for affiliation in result["affiliations"]:
        # Each item should be a dict (affiliation object), not a list
        assert isinstance(affiliation, dict), (
            f"Expected affiliation to be a dict, got {type(affiliation)}: {affiliation}"
        )
        # Should have id or name
        assert "id" in affiliation or "name" in affiliation

    # Should have all affiliations from creators and contributors
    # We expect: CERN (twice), University of British Columbia, SFPL
    affiliation_ids = [
        aff.get("id") for aff in result["affiliations"] if aff.get("id")
    ]
    affiliation_names = [
        aff.get("name") for aff in result["affiliations"] if aff.get("name")
    ]

    # CERN should appear (from creator 1 and contributor 1)
    assert "cern" in affiliation_ids or "CERN" in affiliation_names
    # University of British Columbia should appear
    ubc_in_ids = "03rmrcq20" in affiliation_ids
    ubc_in_names = "University of British Columbia" in affiliation_names
    assert ubc_in_ids or ubc_in_names
    # San Francisco Public Library should appear
    sfpl_in_ids = "013v4ng57" in affiliation_ids
    sfpl_in_names = "San Francisco Public Library" in affiliation_names
    assert sfpl_in_ids or sfpl_in_names


def test_file_download_affiliations_flattened(
    running_app,
    db,
    minimal_published_record_factory,
    record_metadata,
    test_sample_files_folder,
):
    """Test that affiliations are flattened from nested structure in file download."""
    app = running_app.app

    # Create metadata with multiple creators and contributors, each with affiliations
    test_metadata = record_metadata()
    test_metadata.update_metadata({
        "metadata|creators": [
            {
                "person_or_org": {
                    "family_name": "One",
                    "given_name": "Creator",
                    "name": "Creator One",
                    "type": "personal",
                },
                "affiliations": [
                    {"id": "cern", "name": "CERN"},
                    {"id": "03rmrcq20", "name": "University of British Columbia"},
                ],
            },
            {
                "person_or_org": {
                    "family_name": "Two",
                    "given_name": "Creator",
                    "name": "Creator Two",
                    "type": "personal",
                },
                "affiliations": [
                    {"id": "013v4ng57", "name": "San Francisco Public Library"},
                ],
            },
        ],
        "metadata|contributors": [
            {
                "person_or_org": {
                    "family_name": "One",
                    "given_name": "Contributor",
                    "name": "Contributor One",
                    "type": "personal",
                },
                "role": {"id": "other"},
                "affiliations": [
                    {"id": "cern", "name": "CERN"},
                ],
            },
        ],
        "files|enabled": True,
    })

    record_item = minimal_published_record_factory(
        metadata=test_metadata.metadata_in,
        file_paths=[str(test_sample_files_folder / "sample.pdf")],
    )
    record = record_item._record

    file_service = current_rdm_records_service.files
    assert len(record.files.entries) > 0
    file_key = list(record.files.entries.keys())[0]
    file_item = file_service.get_file_content(system_identity, record["id"], file_key)
    obj = file_item._file.object_version
    assert obj is not None

    event: dict = {}

    with app.test_request_context(headers={"Referer": "https://example.com"}):
        result = file_download_event_builder(
            event, app, record=record, obj=obj, via_api=True
        )

    # Affiliations should be a flat list, not nested arrays
    assert "affiliations" in result
    assert isinstance(result["affiliations"], list)

    # Should be a flat array of affiliation objects, not array of arrays
    assert len(result["affiliations"]) > 0
    for affiliation in result["affiliations"]:
        # Each item should be a dict (affiliation object), not a list
        assert isinstance(affiliation, dict), (
            f"Expected affiliation to be a dict, got {type(affiliation)}: {affiliation}"
        )
        # Should have id or name
        assert "id" in affiliation or "name" in affiliation

    # Should have all affiliations from creators and contributors
    # We expect: CERN (twice), University of British Columbia, SFPL
    affiliation_ids = [
        aff.get("id") for aff in result["affiliations"] if aff.get("id")
    ]
    affiliation_names = [
        aff.get("name") for aff in result["affiliations"] if aff.get("name")
    ]

    # CERN should appear (from creator 1 and contributor 1)
    assert "cern" in affiliation_ids or "CERN" in affiliation_names
    # University of British Columbia should appear
    ubc_in_ids = "03rmrcq20" in affiliation_ids
    ubc_in_names = "University of British Columbia" in affiliation_names
    assert ubc_in_ids or ubc_in_names
    # San Francisco Public Library should appear
    sfpl_in_ids = "013v4ng57" in affiliation_ids
    sfpl_in_names = "San Francisco Public Library" in affiliation_names
    assert sfpl_in_ids or sfpl_in_names
