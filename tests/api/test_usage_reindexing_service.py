# Part of the Invenio-Stats-Dashboard extension for InvenioRDM

# Copyright (C) 2025 MESH Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Tests for the EventReindexingService functionality."""

import copy
from pathlib import Path

import arrow
import pytest
from flask import current_app
from invenio_access.utils import get_identity
from invenio_accounts.proxies import current_datastore
from invenio_search import current_search_client
from invenio_search.utils import prefix_index
from opensearchpy.helpers.search import Search

from invenio_stats_dashboard.proxies import current_event_reindexing_service
from invenio_stats_dashboard.services.usage_reindexing import (
    EventReindexingService,
)
from tests.fixtures.records import enhance_metadata_with_funding_and_affiliations
from tests.helpers.sample_records import (
    sample_metadata_journal_article4_pdf,
    sample_metadata_journal_article5_pdf,
    sample_metadata_journal_article6_pdf,
)


@pytest.mark.skip(reason="Deprecated method")
class TestEventReindexingServiceFallback:
    """Test the fallback behavior of EventReindexingService without reindexing."""

    def test_get_community_membership_fallback_basic(
        self,
        running_app,
        minimal_community_factory,
        minimal_published_record_factory,
        user_factory,
    ):
        """Test basic fallback behavior for community membership."""
        app = running_app.app
        service = EventReindexingService(app)

        # Create test data
        u = user_factory(email="test@example.com")
        user_email = u.user.email
        user_id = u.user.id

        community = minimal_community_factory(user_id)
        community_id = community["id"]

        record = minimal_published_record_factory(
            identity=get_identity(current_datastore.get_user_by_email(user_email)),
            community_list=[community_id],
        )
        record_id = record["id"]

        # Get metadata for the record
        metadata = service.get_metadata_for_records([record_id])

        # Test the fallback method directly
        fallback_membership = service._get_community_membership_fallback(metadata)

        # Verify the fallback found the record and community
        assert record_id in fallback_membership, "Fallback should find record"
        community_ids = [comm[0] for comm in fallback_membership[record_id]]
        assert community_id in community_ids, "Fallback should find community"

        # Verify the format is correct (community_id, effective_date)
        assert len(fallback_membership[record_id]) == 1, "Should have one community"
        community_tuple = fallback_membership[record_id][0]
        expected_format = "Should be (community_id, effective_date) tuple"
        assert len(community_tuple) == 2, expected_format
        first_element_msg = "First element should be community_id"
        second_element_msg = "Second element should be effective_date string"
        assert community_tuple[0] == community_id, first_element_msg
        assert isinstance(community_tuple[1], str), second_element_msg

    def test_get_community_membership_fallback_multiple_records(
        self,
        running_app,
        minimal_community_factory,
        minimal_published_record_factory,
        user_factory,
    ):
        """Test fallback behavior with multiple records in the same community."""
        app = running_app.app
        service = EventReindexingService(app)

        # Create test data
        u = user_factory(email="test@example.com")
        user_email = u.user.email
        user_id = u.user.id

        # Create community
        community = minimal_community_factory(user_id)
        community_id = community["id"]

        # Create multiple records in the same community
        record1 = minimal_published_record_factory(
            identity=get_identity(current_datastore.get_user_by_email(user_email)),
            community_list=[community_id],
        )
        record2 = minimal_published_record_factory(
            identity=get_identity(current_datastore.get_user_by_email(user_email)),
            community_list=[community_id],
        )

        record_ids = [record1["id"], record2["id"]]

        # Get metadata for all records
        metadata = service.get_metadata_for_records(record_ids)

        # Test the fallback method
        fallback_membership = service._get_community_membership_fallback(metadata)

        # Verify both records are found
        assert record_ids[0] in fallback_membership, "First record should be found"
        assert record_ids[1] in fallback_membership, "Second record should be found"

        # Verify both records belong to the community
        for record_id in record_ids:
            community_ids = [comm[0] for comm in fallback_membership[record_id]]
            msg = f"Record {record_id} should belong to community"
            assert community_id in community_ids, msg

    def test_get_community_membership_fallback_no_communities(
        self, running_app, minimal_published_record_factory, user_factory
    ):
        """Test fallback behavior when records have no communities."""
        app = running_app.app
        service = EventReindexingService(app)

        # Create test data - record without community
        u = user_factory(email="test@example.com")
        user_email = u.user.email

        # Create a record without specifying a community
        record = minimal_published_record_factory(
            identity=get_identity(current_datastore.get_user_by_email(user_email)),
        )
        record_id = record["id"]
        current_search_client.indices.refresh(index="*rdmrecords-records*")

        # Get metadata for the record
        metadata = service.get_metadata_for_records([record_id])

        # Test the fallback method
        fallback_membership = service._get_community_membership_fallback(metadata)

        # Verify the record is found but has no communities
        assert record_id in fallback_membership, "Record should be found"
        assert (
            len(fallback_membership[record_id]) == 0
        ), "Record should have no communities"

    def test_get_community_membership_fallback_multiple_communities(
        self,
        running_app,
        minimal_community_factory,
        minimal_published_record_factory,
        user_factory,
    ):
        """Test fallback behavior when records belong to multiple communities."""
        app = running_app.app
        service = EventReindexingService(app)

        # Create test data
        u = user_factory(email="test@example.com")
        user_email = u.user.email
        user_id = u.user.id

        # Create a community
        community1 = minimal_community_factory(user_id)
        community1_id = community1["id"]

        # Create a record that belongs to both communities
        record = minimal_published_record_factory(
            identity=get_identity(current_datastore.get_user_by_email(user_email)),
            community_list=[community1_id],
        )
        record_id = record["id"]

        # Get metadata for the record
        metadata = service.get_metadata_for_records([record_id])

        # Test the fallback method
        fallback_membership = service._get_community_membership_fallback(metadata)

        # Verify the record is found
        assert record_id in fallback_membership, "Record should be found"

    def test_get_community_membership_fallback_invalid_metadata(self, running_app):
        """Test fallback behavior with invalid or empty metadata."""
        app = running_app.app
        service = EventReindexingService(app)

        # Test with empty metadata
        empty_metadata = {}
        fallback_membership = service._get_community_membership_fallback(empty_metadata)
        assert (
            fallback_membership == {}
        ), "Empty metadata should return empty membership"

        # Test with None metadata
        fallback_membership = service._get_community_membership_fallback({})
        assert fallback_membership == {}, "None metadata should return empty membership"

    def test_get_community_membership_fallback_metadata_structure(
        self,
        running_app,
        minimal_community_factory,
        minimal_published_record_factory,
        user_factory,
    ):
        """Test fallback behavior with different metadata structures."""
        app = running_app.app
        service = EventReindexingService(app)

        # Create test data
        u = user_factory(email="test@example.com")
        user_email = u.user.email
        user_id = u.user.id

        # Create community
        community = minimal_community_factory(user_id)
        community_id = community["id"]

        # Create a record
        record = minimal_published_record_factory(
            identity=get_identity(current_datastore.get_user_by_email(user_email)),
            community_list=[community_id],
        )
        record_id = record["id"]

        # Get metadata for the record
        metadata = service.get_metadata_for_records([record_id])

        # Test the fallback method
        fallback_membership = service._get_community_membership_fallback(metadata)

        # Verify the metadata structure is handled correctly
        assert record_id in fallback_membership, "Record should be found"

        # Check that the effective_date is properly calculated
        record_data = metadata[record_id]
        record_created = record_data.get("created")

        if record_created:
            # The effective_date should be at least as recent as the record creation
            community_tuple = fallback_membership[record_id][0]
            effective_date = community_tuple[1]
            assert (
                effective_date >= record_created
            ), "Effective date should be >= record creation date"


class TestEventReindexingService:
    """Test class for EventReindexingService with monthly indices.

    This class orchestrates a single comprehensive test run with all setup
    and verification steps delegated to private helper methods.
    """

    core_fields = [
        "recid",
        "timestamp",
        "session_id",
        "visitor_id",
        "country",
        "unique_session_id",
        "referrer",
        "path",
        "query_string",
        "via_api",
        "is_robot",
    ]

    # Test Configuration Properties
    @property
    def event_types(self):
        """Event types to test. Override to test different combinations."""
        return ["view", "download"]

    @property
    def max_batches(self):
        """Maximum batches for reindexing. Override for different batch sizes."""
        return 100

    @property
    def delete_old_indices(self):
        """Whether to delete old indices after reindexing."""
        return True

    @property
    def memory_limit_percent(self):
        """Memory limit percentage for the service."""
        return 90

    @property
    def test_months(self):
        """Months to create test data for. Override for different date ranges."""
        current_month = arrow.utcnow().format("YYYY-MM")
        previous_month = arrow.get(current_month).shift(months=-1).format("YYYY-MM")
        previous_month_2 = arrow.get(current_month).shift(months=-2).format("YYYY-MM")
        return [previous_month_2, previous_month, current_month]

    @property
    def record_creation_date(self):
        """Date to use for record creation. Override for different scenarios."""
        return "2024-01-01T10:00:00.000000+00:00"

    @property
    def sample_metadata_list(self):
        """Sample metadata to use for creating records."""
        return [
            sample_metadata_journal_article4_pdf,
            sample_metadata_journal_article5_pdf,
            sample_metadata_journal_article6_pdf,
        ]

    @property
    def events_per_record(self):
        """Number of events to create per record."""
        return 100

    @property
    def expected_total_events(self):
        """Total number of events expected."""
        return 600  # 3 records * 100 events * 2 event types

    @property
    def expected_events_per_type(self):
        """Expected events per type."""
        return 300  # 3 records * 100 events

    @property
    def user_email(self):
        """Email for test user."""
        return "test@example.com"

    def get_event_date_range(self):
        """Get the date range for creating usage events."""
        months = self.test_months
        return {
            "start_date": f"{months[0]}-01",
            "end_date": arrow.utcnow().format("YYYY-MM-DD"),
        }

    def get_reindexing_parameters(self):
        """Parameters for the reindexing service call."""
        return {
            "event_types": self.event_types,
            "max_batches": self.max_batches,
            "delete_old_indices": self.delete_old_indices,
        }

    def get_expected_month_counts(self, month):
        """Expected event counts for a specific month."""
        return {"view": 100, "download": 100}  # 1 record * 100 events

    @property
    def enriched_fields(self):
        """Dynamically extract enriched fields from the v2.0.0 index templates."""
        enriched_fields = {"record-view": set(), "file-download": set()}

        for event_type in ["record-view", "file-download"]:
            template_name = f"events-stats-{event_type}-v2.0.0"
            try:
                template_info = current_search_client.indices.get_index_template(
                    name=prefix_index(template_name)
                )

                template_body = template_info["index_templates"][0]["index_template"]
                mappings = template_body.get("template", {}).get("mappings", {})
                properties = mappings.get("properties", {})

                core_fields = set(self.core_fields)
                for field_name in properties.keys():
                    if field_name not in core_fields:
                        enriched_fields[event_type].add(field_name)

            except Exception as e:
                # If template doesn't exist, fall back to known fields
                current_app.logger.warning(
                    f"Could not extract enriched fields from template "
                    f"{template_name}: {e}"
                )

        result = {
            event_type: list(fields) for event_type, fields in enriched_fields.items()
        }
        return result

    def _verify_original_templates_lack_enriched_fields(self):
        """Verify that the original index templates do NOT contain enriched fields.

        This check ensures that the old templates from invenio-rdm-records
        don't have the new enriched fields, which is important for testing
        the migration scenario.
        """
        from invenio_search.utils import prefix_index

        for event_type in ["record-view", "file-download"]:
            template_name = f"events-stats-{event_type}-v1.0.0"
            try:
                template_info = current_search_client.indices.get_index_template(
                    name=prefix_index(template_name)
                )

                template_body = template_info["index_templates"][0]["index_template"]
                mappings = template_body.get("template", {}).get("mappings", {})

                # Check that enriched fields are NOT present in the original mappings
                for field in self.enriched_fields:
                    properties = mappings.get("properties", {})
                    assert field not in properties, (
                        f"Original template {template_name} should NOT contain "
                        f"enriched field '{field}'"
                    )

                print(
                    f"✓ Original template {template_name} correctly lacks "
                    f"enriched fields"
                )

            except Exception as e:
                # If template doesn't exist or can't be retrieved, that's fine
                # as long as we're testing the migration scenario
                print(f"Note: Could not verify template {template_name}: {e}")

    def _test_current_month_fetching(self):
        """Test fetching the current month."""
        current_month = current_event_reindexing_service.get_current_month()
        assert current_month == arrow.utcnow().format("YYYY-MM")

    def test_reindexing_monthly_indices(
        self,
        running_app,
        db,
        minimal_community_factory,
        minimal_published_record_factory,
        user_factory,
        put_old_stats_templates,
        celery_worker,
        requests_mock,
        search_clear,
        usage_event_factory,
    ):
        """Comprehensive test for EventReindexingService with monthly indices.

        This test orchestrates the entire test flow from setup through verification,
        delegating each step to private helper methods for clarity and maintainability.
        """
        self.app = running_app.app
        self.user_factory = user_factory
        self.minimal_community_factory = minimal_community_factory
        self.minimal_published_record_factory = minimal_published_record_factory
        self.usage_event_factory = usage_event_factory

        # update service's memory limit since test setup has
        # limited resources and tests pass 85% memory usage
        extension = self.app.extensions.get("invenio-stats-dashboard")
        if hasattr(extension, "event_reindexing_service"):
            service = extension.event_reindexing_service
            if service:
                service.max_memory_percent = self.memory_limit_percent

        self._verify_original_templates_lack_enriched_fields()
        self._setup_test_data()
        self._pre_migration_setup()
        self._create_usage_events()
        self._capture_original_event_data()
        self._verify_events_created_in_monthly_indices()

        self._test_current_month_fetching()
        reindexing_params = self.get_reindexing_parameters()
        results = current_event_reindexing_service.reindex_events(**reindexing_params)
        self._verify_initial_results(results)
        self._verify_enriched_events_created()
        self._verify_old_indices_deleted()
        self._verify_aliases_updated()
        self._verify_current_month_write_alias()
        self._verify_new_fields_in_v2_indices()
        self._verify_event_content_preserved()

    def _setup_test_data(self):
        """Setup test data including users, communities, records, and usage events."""
        # Clear any existing records to ensure clean test state
        # FIXME: Why is the search index not being cleared by search_clear?
        current_search_client.delete_by_query(
            index=prefix_index("rdmrecords-records"),
            body={"query": {"match_all": {}}},
            conflicts="proceed",
        )
        current_search_client.indices.refresh(index=prefix_index("rdmrecords-records"))

        u = self.user_factory(email=self.user_email)
        self.user_id = u.user.id

        self.community = self.minimal_community_factory(
            self.user_id,
            created="2023-12-01T10:00:00.000000+00:00",  # Before record creation
        )
        self.community_id = self.community["id"]

        self.records = []
        user_identity = get_identity(u.user)

        # Use sample metadata fixtures that contain full metadata and file information
        sample_metadata_list = self.sample_metadata_list

        for i, sample_data in enumerate(sample_metadata_list):
            metadata = copy.deepcopy(sample_data["input"])
            metadata["created"] = self.record_creation_date
            enhance_metadata_with_funding_and_affiliations(metadata, i)

            if metadata.get("files", {}).get("enabled", False):
                filename = list(metadata["files"]["entries"].keys())[0]
                file_paths = [
                    Path(__file__).parent.parent / "helpers" / "sample_files" / filename
                ]
            else:
                # Fallback to sample.pdf if no files in metadata
                metadata["files"] = {
                    "enabled": True,
                    "entries": {"sample.pdf": {"key": "sample.pdf", "ext": "pdf"}},
                }
                file_paths = [
                    Path(__file__).parent.parent
                    / "helpers"
                    / "sample_files"
                    / "sample.pdf"
                ]

            record = self.minimal_published_record_factory(
                identity=user_identity,
                community_list=self._get_community_list_for_record(i),
                metadata=metadata,
                file_paths=file_paths,
                update_community_event_dates=True,
            )
            self.records.append(record)

        current_search_client.indices.refresh(index=prefix_index("rdmrecords-records"))
        current_search_client.indices.refresh(
            index=prefix_index("stats-community-events")
        )
        assert [
            arrow.get(r.to_dict()["created"]).format("YYYY-MM-DD") for r in self.records
        ] == ["2024-01-01"] * len(
            self.records
        ), f"Should have {len(self.records)} records"

    def _get_community_list_for_record(self, record_index):
        """Get community list for a specific record by index.

        Subclasses can override this method to customize community assignment
        per record. Default implementation assigns all records to the community.
        """
        return [self.community_id]

    def _pre_migration_setup(self):
        """Placeholder method for custom setup logic before migration.

        This method is called after records have been created but before
        the migration starts. Subclasses can override this method to add
        custom setup logic.
        """
        pass

    def _create_usage_events(self):
        """Create usage events in different months."""
        self.months = self.test_months

        try:
            date_range = self.get_event_date_range()

            self.usage_event_factory.generate_and_index_repository_events(
                events_per_record=self.events_per_record,
                event_start_date=date_range["start_date"],
                event_end_date=date_range["end_date"],
            )
        except Exception as e:
            self.app.logger.error(f"Exception during method call: {e}")
            raise

    def _capture_original_event_data(self):
        """Capture original event data before migration for later comparison."""
        self.original_event_data = {}

        for event_type in ["view", "download"]:
            index_pattern = current_event_reindexing_service.index_patterns[event_type]
            self.original_event_data[event_type] = {}

            for month in self.months:
                index_name = f"{index_pattern}-{month}"

                search = Search(using=current_search_client, index=index_name)
                search = search.extra(size=1000)
                results = search.execute()

                if results.hits.hits:
                    self.original_event_data[event_type][month] = {
                        hit["_id"]: hit["_source"] for hit in results.hits.hits
                    }
                else:
                    self.original_event_data[event_type][month] = {}

    def _verify_events_created_in_monthly_indices(self):
        """Verify that events are created in correct monthly indices."""
        event_count = 0
        for month in self.months:
            view_index = f"{prefix_index('events-stats-record-view')}-{month}"
            download_index = f"{prefix_index('events-stats-file-download')}-{month}"

            view_exists = current_search_client.indices.exists(index=view_index)
            assert view_exists, f"Index {view_index} should exist"
            download_exists = current_search_client.indices.exists(index=download_index)
            assert download_exists, f"Index {view_index} should exist"

            count_response = current_search_client.count(index=view_index)
            try:
                if hasattr(count_response, "body"):
                    view_count = count_response.body["count"]
                elif isinstance(count_response, dict):
                    view_count = count_response["count"]
                else:
                    view_count = count_response
            except Exception as e:
                self.app.logger.error(f"Error getting view count: {e}")
                view_count = 0

            count_response = current_search_client.count(index=download_index)
            try:
                if hasattr(count_response, "body"):
                    download_count = count_response.body["count"]
                elif isinstance(count_response, dict):
                    download_count = count_response["count"]
                else:
                    download_count = count_response
            except Exception as e:
                self.app.logger.error(f"Error getting download count: {e}")
                download_count = 0

            assert view_count > 0, f"No view events found in {month} index"
            assert download_count > 0, f"No download events found in {month} index"
            event_count += view_count + download_count
        assert (
            event_count == self.expected_total_events
        ), f"Should have {self.expected_total_events} events"

    def _verify_initial_results(self, results):
        """Verify initial results of reindexing."""
        for event_type in self.event_types:
            assert (
                event_type in results["event_types"]
            ), f"Should have {event_type} results"
            assert (
                results["event_types"][event_type]["processed"]
                == self.expected_events_per_type
            ), f"Should have processed {self.expected_events_per_type} {event_type} events"  # noqa: E501
            assert (
                results["event_types"][event_type]["errors"] == 0
            ), f"Should have no {event_type} errors"
            assert set(
                list(results["event_types"][event_type]["months"].keys())
            ) == set(
                self.months
            ), f"Should have {len(self.months)} months of migrated {event_type} events"

    def _verify_enriched_events_created(self):
        """Verify that enriched events were created in new indices."""
        # Look for indices that end with -v2.0.0 for each month
        enriched_view_indices = {}
        enriched_download_indices = {}

        for month in self.months:
            view_index = f"{prefix_index('events-stats-record-view')}-{month}-v2.0.0"
            download_index = (
                f"{prefix_index('events-stats-file-download')}-{month}-v2.0.0"
            )

            if current_search_client.indices.exists(index=view_index):
                enriched_view_indices[month] = view_index
            if current_search_client.indices.exists(index=download_index):
                enriched_download_indices[month] = download_index

        assert len(enriched_view_indices) == len(self.months), (
            f"Should have created {len(self.months)} enriched view indices, "
            f"found: {list(enriched_view_indices.keys())}"
        )
        assert len(enriched_download_indices) == len(self.months), (
            f"Should have created {len(self.months)} enriched download indices, "
            f"found: {list(enriched_download_indices.keys())}"
        )

        # Check that all enriched events have the new fields
        # and are accessible via the default aliases
        for index in ["record-view", "file-download"]:
            enriched_search = Search(
                using=current_search_client,
                index=f"{prefix_index(f'events-stats-{index}')}",
            )
            enriched_search = enriched_search.extra(size=400)
            enriched_results = enriched_search.execute()

            event_type = index
            expected_fields = self.enriched_fields[event_type]

            for enriched_event in enriched_results.hits.hits:
                for field in expected_fields:
                    assert (
                        field in enriched_event["_source"]
                    ), f"Enriched {event_type} events should have {field}"

    def _verify_old_indices_deleted(self):
        """Verify that old indices are deleted."""
        for index in ["record-view", "file-download"]:
            index_pattern = f"{prefix_index(f'events-stats-{index}')}-*"
            existing_indices = current_search_client.indices.get(index=index_pattern)
            assert len(existing_indices) == len(
                self.months
            ), f"Should have {len(self.months)} new enriched indices only"
            for month in self.months:
                old_index = f"{prefix_index(f'events-stats-{index}')}-{month}"
                assert old_index not in existing_indices, "Old index should be deleted"
                new_index = f"{prefix_index(f'events-stats-{index}')}-{month}-v2.0.0"
                assert new_index in existing_indices, "New index should be present"

    def _verify_aliases_updated(self):
        """Verify that aliases now to point to v2.0.0 indices."""
        for event_type in self.event_types:
            index_pattern = current_event_reindexing_service.index_patterns[event_type]

            try:
                aliases_info = current_search_client.indices.get_alias(
                    index=f"{index_pattern}*"
                )
            except Exception as e:
                pytest.fail(f"Failed to get aliases for {event_type}: {e}")

            indices_with_main_alias = [
                name
                for name, info in aliases_info.items()
                if index_pattern in info.get("aliases", {}) and name.endswith("-v2.0.0")
            ]

            assert (
                len(indices_with_main_alias) > 0
            ), f"No indices found with alias {index_pattern}"

    def _verify_current_month_write_alias(self):
        """Verify that the current month has proper write alias setup.

        Check that the current month has aliases for both event types that
        point from the old indices for the current month to the v2.0.0 index
        """
        for event_type in self.event_types:
            index_pattern = current_event_reindexing_service.index_patterns[event_type]
            old_index_name = f"{index_pattern}-{self.months[-1]}"
            v2_index_name = f"{index_pattern}-{self.months[-1]}-v2.0.0"

            alias_info = current_search_client.indices.get_alias(index=v2_index_name)

            alias_targets = list(alias_info[v2_index_name]["aliases"].keys())
            assert (
                len(alias_targets) == 2
            ), f"Write alias {v2_index_name} should have exactly one target"

            assert (
                old_index_name in alias_targets
            ), f"Write alias {v2_index_name} should point to {old_index_name}"
            assert (
                index_pattern in alias_targets
            ), f"Write alias {v2_index_name} should point to {index_pattern}"

    def _verify_new_fields_in_v2_indices(self):
        """Verify that new events are created and accessible via aliases."""
        for event_type in self.event_types:
            index_pattern = current_event_reindexing_service.index_patterns[event_type]
            event_type_pattern = (
                "record-view" if event_type == "view" else "file-download"
            )
            v2_index_name = f"{index_pattern}-{self.months[-1]}-v2.0.0"

            initial_count = current_search_client.count(index=v2_index_name)["count"]

            # Create a test event manually using the service's enrichment methods
            test_event = {
                "recid": self.records[0]["id"],  # Use the first record we created
                "timestamp": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss"),
                "session_id": "test-session-123",
                "unique_id": "test-unique-id-456",
                "visitor_id": "test-visitor-456",
                "country": "US",
                "unique_session_id": "test-unique-session-789",
                "is_robot": False,
                "is_machine": False,
                "referrer": "https://example.com",
                "via_api": False,
            }

            record_id = test_event["recid"]
            metadata = current_event_reindexing_service.get_metadata_for_records(
                [record_id]
            )

            enrichment_data = (
                current_event_reindexing_service.metadata_extractor.extract_fields(
                    metadata, record_id
                )
            )
            community_list = self._get_community_list_for_record(0)
            enriched_event = {
                **test_event,
                **enrichment_data,
                "community_ids": community_list,
            }

            doc_id = f"test-event-{event_type}-{arrow.utcnow().timestamp()}"
            current_search_client.index(
                index=v2_index_name, id=doc_id, body=enriched_event, refresh=True
            )

            final_count = current_search_client.count(index=v2_index_name)["count"]
            assert (
                final_count == initial_count + 1
            ), f"New events should be written to {v2_index_name}"

            # Verify the new event is accessible via the main alias
            main_alias = index_pattern
            main_alias_count = current_search_client.count(index=main_alias)["count"]
            assert (
                main_alias_count > 0
            ), f"Events should be accessible via main alias {main_alias}"

            # Verify the new event is accessible via the current month's write alias
            current_month_alias = f"{index_pattern}-{self.months[-1]}"
            current_month_count = current_search_client.count(
                index=current_month_alias
            )["count"]
            assert current_month_count == final_count, (
                f"Events should be accessible via current month alias "
                f"{current_month_alias}"
            )

            # Verify that the new events in the v2.0.0 index have enriched fields
            search = (
                Search(using=current_search_client, index=v2_index_name)
                .filter("term", recid=record_id)
                .filter(
                    "range",
                    timestamp={"gte": arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss")},
                )
                .extra(size=10)
            )
            results = search.execute()

            assert len(results.hits.hits) == 1, "Should have 1 hit"
            source = results.hits.hits[0]["_source"]
            for field in self.enriched_fields[event_type_pattern]:
                assert (
                    field in source
                ), f"New events in {v2_index_name} should have {field}"

    def _verify_event_content_preserved(self):
        """Verify that event content remains identical in new indices."""
        for event_type in self.event_types:
            index_pattern = current_event_reindexing_service.index_patterns[event_type]
            event_type_pattern = (
                "record-view" if event_type == "view" else "file-download"
            )

            for month in self.months:
                new_index = f"{index_pattern}-{month}-v2.0.0"

                original_events = self.original_event_data.get(event_type, {}).get(
                    month, {}
                )

                new_search = Search(using=current_search_client, index=new_index)
                new_search = new_search.extra(
                    size=len(list(original_events.keys())) + 10
                )
                new_results = new_search.execute()

                if month == self.months[-1]:
                    assert (
                        len(new_results.hits.hits)
                        == len(list(original_events.keys())) + 1
                    )
                else:
                    assert len(new_results.hits.hits) == len(
                        list(original_events.keys())
                    )

                new_hit_dict = {
                    hit["_id"]: hit["_source"] for hit in new_results.hits.hits
                }
                for original_id, original_source in original_events.items():
                    new_event = new_hit_dict[original_id]

                    for field in self.core_fields:
                        if field in original_source:
                            assert (
                                field in new_event
                            ), f"Core field {field} missing in new index"
                            assert original_source[field] == new_event[field], (
                                f"Core field {field} value differs between old and "
                                f"new indices"
                            )

                    for field in self.enriched_fields[event_type_pattern]:
                        assert (
                            field in new_event
                        ), f"Enriched field {field} missing in new index"
                        assert (
                            new_event[field] is not None
                        ), f"Enriched field {field} is None in new index"


class TestEventReindexingServiceNoCommunityEventsIndex(TestEventReindexingService):
    """Test EventReindexingService with no community events index scenario.

    This subclass tests the error scenario in
    EventReindexingService.get_community_membership by clearing the community events
    index to force the error.
    """

    def _pre_migration_setup(self):
        """Clear community events index to force fallback mechanism."""
        # Delete community events index to trigger error
        current_search_client.indices.delete(
            index="*stats-community-events*",
        )

    def _verify_initial_results(self, results):
        """Verify initial results of reindexing."""
        assert (
            "Community events index does not exist" in results["health_issues"]
        ), "Community events index should not exist"
        assert results["completed"] is False, "Reindexing should not be completed"
        assert (
            results["error"]
            == "Community events index does not exist - cannot proceed with reindexing"
        ), "Error message should be set"
        assert results["total_errors"] == 1, "Total errors should be 1"

    def _verify_enriched_events_created(self):
        """Verify that enriched events were created in new indices."""
        enriched_view_indices = {}
        enriched_download_indices = {}

        for month in self.months:
            view_index = f"{prefix_index('events-stats-record-view')}-{month}-v2.0.0"
            download_index = (
                f"{prefix_index('events-stats-file-download')}-{month}-v2.0.0"
            )

            if current_search_client.indices.exists(index=view_index):
                enriched_view_indices[month] = view_index
            if current_search_client.indices.exists(index=download_index):
                enriched_download_indices[month] = download_index

        assert len(enriched_view_indices) == 0, (
            f"Should have created no enriched view indices, "
            f"found: {list(enriched_view_indices.keys())}"
        )
        assert len(enriched_download_indices) == 0, (
            f"Should have created no enriched download indices, "
            f"found: {list(enriched_download_indices.keys())}"
        )

    def _verify_old_indices_deleted(self):
        """Verify that old indices are deleted."""
        pass

    def _verify_aliases_updated(self):
        """Verify that aliases are updated."""
        pass

    def _verify_current_month_write_alias(self):
        """Verify that the current month has proper write alias setup."""
        pass

    def _verify_new_fields_in_v2_indices(self):
        """Verify that new fields are in v2 indices."""
        pass

    def _verify_event_content_preserved(self):
        """Verify that event content remains identical in new indices."""
        pass


class TestEventReindexingServiceCustomDateRange(TestEventReindexingService):
    """Test with custom date range spanning 6 months."""

    @property
    def test_months(self):
        """Override to test 6 months instead of 3."""
        current_month = arrow.utcnow().format("YYYY-MM")
        return [
            arrow.get(current_month).shift(months=-5).format("YYYY-MM"),
            arrow.get(current_month).shift(months=-4).format("YYYY-MM"),
            arrow.get(current_month).shift(months=-3).format("YYYY-MM"),
            arrow.get(current_month).shift(months=-2).format("YYYY-MM"),
            arrow.get(current_month).shift(months=-1).format("YYYY-MM"),
            current_month,
        ]

    @property
    def events_per_record(self):
        """Override to create 200 events per record to distribute across 6 months."""
        return 200  # 100 events per month * 6 months

    @property
    def expected_total_events(self):
        """Override expected total for 6 months."""
        return 1200  # 3 records * 200 events per record * 2 types

    @property
    def expected_events_per_type(self):
        """Override expected events per type for 6 months."""
        return 600  # 3 records * 200 events per record

    def get_event_date_range(self):
        """Override to span all 6 months for event generation."""
        months = self.test_months
        last_month_arrow = arrow.get(months[-1])
        last_day = min(
            last_month_arrow.ceil("month").shift(days=-1).day, arrow.utcnow().day - 1
        )  # so the check for one new event added after now doesn't fail
        return {
            "start_date": f"{months[0]}-01",
            "end_date": f"{months[-1]}-{last_day:02d}",
        }

    def get_expected_month_counts(self, month):
        """Override expected counts per month."""
        return {"view": 100, "download": 100}


class TestEventReindexingServiceHighVolume(TestEventReindexingService):
    """Test with higher event volume."""

    @property
    def events_per_record(self):
        """Override to create more events per record."""
        return 500

    @property
    def expected_total_events(self):
        """Override expected total for higher volume."""
        return 3000  # 3 records * 500 events * 2 types

    @property
    def expected_events_per_type(self):
        """Override expected events per type for higher volume."""
        return 1500  # 3 records * 500 events


class TestEventReindexingServiceMixedCommunityMembership(TestEventReindexingService):
    """Test EventReindexingService with mixed community membership.

    This subclass creates two records - one assigned to a community and one without
    any community - and verifies that migrated events have correct community_ids values.
    """

    @property
    def sample_metadata_list(self):
        """Override to use only two sample metadata records."""
        return [
            sample_metadata_journal_article4_pdf,
            sample_metadata_journal_article5_pdf,
        ]

    @property
    def events_per_record(self):
        """Override to create 10 events per record."""
        return 10

    @property
    def expected_total_events(self):
        """Override expected total for 2 records with 10 events each."""
        return 40  # 2 records * 10 events * 2 event types

    @property
    def expected_events_per_type(self):
        """Override expected events per type for 2 records."""
        return 20  # 2 records * 10 events

    def _get_community_list_for_record(self, record_index):
        """Override to assign only the first record to a community."""
        if record_index == 0:
            return [self.community_id]
        return []

    def _setup_test_data(self):
        """Override to call parent setup and store record IDs for verification."""
        super()._setup_test_data()
        # Store which record has community membership for verification
        self.record_with_community = self.records[0]["id"]
        self.record_without_community = self.records[1]["id"]

    def _pre_migration_setup(self):
        """Override to perform custom setup before migration."""
        super()._pre_migration_setup()

        current_search_client.indices.refresh(
            index=prefix_index("stats-community-events")
        )

    def _verify_event_content_preserved(self):
        """Override to add community_ids verification on top of base verification."""
        # Call parent verification first
        super()._verify_event_content_preserved()

        # Add our specific community_ids verification
        self._verify_community_ids()

    def _verify_community_ids(self):
        """Verify that community_ids are correctly set based on record membership."""
        for event_type in self.event_types:
            index_pattern = current_event_reindexing_service.index_patterns[event_type]

            for month in self.months:
                new_index = f"{index_pattern}-{month}-v2.0.0"

                new_search = Search(using=current_search_client, index=new_index)
                new_search = new_search.extra(size=100)  # Get all events
                new_results = new_search.execute()

                new_hit_dict = {
                    hit["_id"]: hit["_source"] for hit in new_results.hits.hits
                }

                # Verify community_ids for events belonging to record with community
                events_with_community = [
                    event
                    for event in new_hit_dict.values()
                    if event.get("recid") == self.record_with_community
                ]
                for event in events_with_community:
                    assert "community_ids" in event, (
                        "Events for record with community should have "
                        "community_ids field"
                    )
                    assert event["community_ids"] == [self.community_id], (
                        f"Events for record {self.record_with_community} should have "
                        f"community_ids=[{self.community_id}], "
                        f"got {event['community_ids']}"
                    )

                # Verify community_ids for events belonging to record without community
                events_without_community = [
                    event
                    for event in new_hit_dict.values()
                    if event.get("recid") == self.record_without_community
                ]
                for event in events_without_community:
                    assert "community_ids" in event, (
                        "Events for record without community should have "
                        "community_ids field"
                    )
                    assert event["community_ids"] == [], (
                        f"Events for record {self.record_without_community} "
                        f"should have empty community_ids list, "
                        f"got {event['community_ids']}"
                    )
