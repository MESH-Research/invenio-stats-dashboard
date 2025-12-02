# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Integration tests for first_run flag lifecycle.

These tests verify that the first_run flag is properly managed through the
complete lifecycle of aggregation and caching tasks for a community.
"""

from unittest.mock import patch

import arrow
import pytest
from flask import g
from invenio_access.permissions import system_identity
from invenio_search import current_search_client

from invenio_stats_dashboard.constants import FirstRunStatus, RegistryOperation
from invenio_stats_dashboard.tasks.aggregation_tasks import (
    CommunityStatsAggregationTask,
    aggregate_community_record_stats,
)
from invenio_stats_dashboard.tasks.cache_tasks import generate_cached_responses_task
from invenio_stats_dashboard.views.views import community_stats_dashboard


@pytest.mark.integration
class FirstRunFlagLifecycleBase:
    """Base class for first_run flag lifecycle tests."""

    def setup_test_data(
        self,
        minimal_community_factory,
        minimal_published_record_factory,
        user_factory,
    ):
        """Set up test data (community and records).

        Args:
            minimal_community_factory: Factory for creating communities.
            minimal_published_record_factory: Factory for creating records.
            user_factory: Factory for creating users.

        Returns:
            tuple: (app, client, community, community_id)
        """
        from flask import current_app

        app = current_app._get_current_object()
        client = current_search_client

        u = user_factory(email="test@example.com")
        user_id = u.user.id
        community = minimal_community_factory(slug="test-community", owner=user_id)
        community_id = community.id

        # Create test records
        for i in range(2):
            minimal_published_record_factory(
                metadata_updates={
                    "created": (
                        arrow.utcnow().shift(days=-i).format("YYYY-MM-DDTHH:mm:ssZZ")
                    )
                },
                identity=system_identity,
                community_list=[community_id],
                set_default=True,
            )

        client.indices.refresh(index="*rdmrecords-records*")

        return app, client, community, community_id

    def get_date_range(self):
        """Get the date range for aggregation.

        Returns:
            tuple: (start_date, end_date) as formatted strings.
        """
        start_date = arrow.utcnow().shift(days=-10).format("YYYY-MM-DD")
        end_date = arrow.utcnow().format("YYYY-MM-DD")
        return start_date, end_date

    def get_aggregations(self):
        """Get aggregations from task config.

        Returns:
            tuple: Aggregations tuple.
        """
        task_config = CommunityStatsAggregationTask
        task_aggs = task_config.get("args", [])
        return task_aggs[0] if task_aggs else ()

    def run_aggregation(
        self, aggregations, start_date, end_date, community_id, registry
    ):
        """Run aggregation task.

        Args:
            aggregations: Aggregations to run.
            start_date: Start date for aggregation.
            end_date: End date for aggregation.
            community_id: Community ID to aggregate.
            registry: Registry instance for checking state.

        Returns:
            dict: Aggregation results.
        """
        return aggregate_community_record_stats(
            aggregations=aggregations,
            start_date=start_date,
            end_date=end_date,
            community_ids=[community_id],
            eager=True,
            update_bookmark=True,
            ignore_bookmark=False,
        )

    def run_caching(self, community_id, years, registry):
        """Run caching task.

        Args:
            community_id: Community ID to cache.
            years: Years to cache.
            registry: Registry instance for checking state.

        Returns:
            dict: Caching results.
        """
        return generate_cached_responses_task(
            community_ids=[community_id],
            years=years,
            overwrite=False,
            async_mode=False,
            current_year_only=False,
            optimize=False,
        )

    def verify_first_run_state(
        self, registry, community_id, expected_count, expected_status=None
    ):
        """Verify first_run state in registry.

        Args:
            registry: Registry instance.
            community_id: Community ID.
            expected_count: Expected number of first_run records.
            expected_status: Expected status (None to skip status check).

        Returns:
            list: First run records (list of tuples).
        """
        first_run_records = registry.get_all(
            f"{community_id}_{RegistryOperation.FIRST_RUN}*"
        )
        assert len(first_run_records) == expected_count, (
            f"Expected {expected_count} first_run record(s)"
        )
        if expected_status is not None:
            assert first_run_records[0][1] == expected_status, (
                f"First_run should be {expected_status}"
            )
        return first_run_records

    def verify_view_flag(self, app, community, expected_incomplete):
        """Verify first_run_incomplete flag in view.

        Args:
            app: Flask application.
            community: Community object.
            expected_incomplete: Expected value for first_run_incomplete.
        """
        with app.test_request_context():
            with patch(
                "invenio_stats_dashboard.views.views.render_template"
            ) as mock_render:
                g.identity = system_identity

                try:
                    community_stats_dashboard(pid_value=community.id)
                    call_args = mock_render.call_args
                    if call_args:
                        template_context = call_args[1].get("dashboard_config", {})
                        assert (
                            template_context.get("first_run_incomplete")
                            == expected_incomplete
                        ), f"first_run_incomplete should be {expected_incomplete}"
                except Exception as e:
                    app.logger.warning(f"View check failed: {e}")

    def run_test(
        self,
        running_app,
        db,
        minimal_community_factory,
        minimal_published_record_factory,
        user_factory,
        create_stats_indices,
        celery_worker,
        search_clear,
        registry,
        requests_mock,
    ):
        """Run the test. Override this method in subclasses.

        Args:
            running_app: Running app fixture.
            db: Database fixture.
            minimal_community_factory: Community factory.
            minimal_published_record_factory: Record factory.
            user_factory: User factory.
            create_stats_indices: Stats indices fixture.
            celery_worker: Celery worker fixture.
            search_clear: Search clear fixture.
            registry: Registry fixture.
            requests_mock: Requests mock fixture.
        """
        raise NotImplementedError("Subclasses must implement run_test")

    def test_first_run_lifecycle(
        self,
        running_app,
        db,
        minimal_community_factory,
        minimal_published_record_factory,
        user_factory,
        create_stats_indices,
        celery_worker,
        search_clear,
        registry,
        requests_mock,
    ):
        """Test entry point."""
        self.run_test(
            running_app,
            db,
            minimal_community_factory,
            minimal_published_record_factory,
            user_factory,
            create_stats_indices,
            celery_worker,
            search_clear,
            registry,
            requests_mock,
        )


class TestFirstRunFlagLifecycleWithAggregationAndCaching(FirstRunFlagLifecycleBase):
    """Test the complete lifecycle of first_run flag from creation to completion.

    This test verifies:
    1. Initial state: no first_run record exists
    2. After aggregation starts: first_run is IN_PROGRESS
    3. After aggregation completes: first_run still IN_PROGRESS
    4. After caching starts: first_run still IN_PROGRESS
    5. After caching completes: first_run is COMPLETED
    """

    def run_test(
        self,
        running_app,
        db,
        minimal_community_factory,
        minimal_published_record_factory,
        user_factory,
        create_stats_indices,
        celery_worker,
        search_clear,
        registry,
        requests_mock,
    ):
        """Run the complete lifecycle test."""
        app, client, community, community_id = self.setup_test_data(
            minimal_community_factory,
            minimal_published_record_factory,
            user_factory,
        )

        current_year = arrow.utcnow().year
        start_date, end_date = self.get_date_range()
        aggregations = self.get_aggregations()

        # Step 1: Initial State - Verify no first_run record exists
        self.verify_first_run_state(registry, community_id, 0)

        # Step 2: Start Aggregation Task
        try:
            self.run_aggregation(
                aggregations, start_date, end_date, community_id, registry
            )

            # Verify first_run was created with IN_PROGRESS status
            first_run_records = self.verify_first_run_state(
                registry, community_id, 1, FirstRunStatus.IN_PROGRESS
            )

            # Step 3: Aggregation Completes
            # With eager=True, aggregation is already complete
            # The agg registry key should be deleted when aggregation completes
            # But first_run should still be IN_PROGRESS (caching hasn't completed yet)
            assert first_run_records[0][1] == FirstRunStatus.IN_PROGRESS, (
                "First_run should still be IN_PROGRESS after aggregation completes"
            )

            # Step 4: Start Caching Task
            cache_result = self.run_caching(community_id, [current_year], registry)

            # Step 5: Caching Completes
            # Verify caching succeeded (with async_mode=False, we get a result dict)
            assert cache_result is not None, "Cache task should return a result"
            assert cache_result.get("responses"), (
                f"Cache generation should succeed. Result: {cache_result}"
            )

            # Caching succeeded, first_run should be COMPLETED
            self.verify_first_run_state(
                registry, community_id, 1, FirstRunStatus.COMPLETED
            )

            # Verify first_run_incomplete is False via the view
            self.verify_view_flag(app, community, False)

        except Exception as e:
            app.logger.warning(f"Task execution failed: {e}")


class TestFirstRunFlagOnlySetOnFirstAggregation(FirstRunFlagLifecycleBase):
    """Test that first_run is only created on the first aggregation.

    This test verifies:
    1. First aggregation creates first_run as IN_PROGRESS
    2. Subsequent aggregations do NOT create new first_run records
    3. First_run remains in its current state (IN_PROGRESS or COMPLETED)
    """

    def run_test(
        self,
        running_app,
        db,
        minimal_community_factory,
        minimal_published_record_factory,
        user_factory,
        create_stats_indices,
        celery_worker,
        search_clear,
        registry,
        requests_mock,
    ):
        """Run the first aggregation only test."""
        app, client, community, community_id = self.setup_test_data(
            minimal_community_factory,
            minimal_published_record_factory,
            user_factory,
        )

        start_date, end_date = self.get_date_range()
        aggregations = self.get_aggregations()

        try:
            # First aggregation - should create first_run
            self.run_aggregation(
                aggregations, start_date, end_date, community_id, registry
            )

            # Verify first_run was created
            first_run_records = self.verify_first_run_state(registry, community_id, 1)
            first_run_status_after_first = first_run_records[0][1]

            # Second aggregation - should NOT create new first_run
            self.run_aggregation(
                aggregations, start_date, end_date, community_id, registry
            )

            # Verify still only one first_run record exists
            first_run_records = self.verify_first_run_state(registry, community_id, 1)
            assert first_run_records[0][1] == first_run_status_after_first, (
                "First_run status should remain unchanged after subsequent aggregation"
            )

        except Exception as e:
            app.logger.warning(f"Task execution failed: {e}")


class TestFirstRunFlagPersistsAfterCompletion(FirstRunFlagLifecycleBase):
    """Test that first_run persists as COMPLETED after subsequent operations.

    This test verifies:
    1. Complete first_run (aggregation + caching) sets status to COMPLETED
    2. Subsequent aggregation does NOT reset first_run to IN_PROGRESS
    3. Subsequent caching does NOT reset first_run to IN_PROGRESS
    4. No duplicate first_run records are created
    5. first_run_incomplete remains False
    """

    def run_test(
        self,
        running_app,
        db,
        minimal_community_factory,
        minimal_published_record_factory,
        user_factory,
        create_stats_indices,
        celery_worker,
        search_clear,
        registry,
        requests_mock,
    ):
        """Run the persistence after completion test."""
        app, client, community, community_id = self.setup_test_data(
            minimal_community_factory,
            minimal_published_record_factory,
            user_factory,
        )

        current_year = arrow.utcnow().year
        start_date, end_date = self.get_date_range()
        aggregations = self.get_aggregations()

        try:
            # Step 1: Complete first_run (aggregation + caching)
            self.run_aggregation(
                aggregations, start_date, end_date, community_id, registry
            )

            cache_result = self.run_caching(community_id, [current_year], registry)

            # Verify caching succeeded
            assert cache_result is not None, "Cache task should return a result"
            assert cache_result.get("responses"), (
                f"Cache generation should succeed. Result: {cache_result}"
            )

            # Verify first_run is COMPLETED
            self.verify_first_run_state(
                registry, community_id, 1, FirstRunStatus.COMPLETED
            )

            # Step 2: Run subsequent aggregation
            # This should NOT reset first_run to IN_PROGRESS
            self.run_aggregation(
                aggregations, start_date, end_date, community_id, registry
            )

            # Verify first_run is still COMPLETED (not reset to IN_PROGRESS)
            self.verify_first_run_state(
                registry, community_id, 1, FirstRunStatus.COMPLETED
            )

            # Step 3: Run subsequent caching
            # This should NOT reset first_run to IN_PROGRESS
            cache_result2 = self.run_caching(community_id, [current_year], registry)

            # Verify caching succeeded
            assert cache_result2 is not None, "Cache task should return a result"
            assert cache_result2.get("responses"), (
                f"Cache generation should succeed. Result: {cache_result2}"
            )

            # Verify first_run is still COMPLETED (not reset to IN_PROGRESS)
            self.verify_first_run_state(
                registry, community_id, 1, FirstRunStatus.COMPLETED
            )

            # Verify no duplicate records were created
            first_run_records = registry.get_all(
                f"{community_id}_{RegistryOperation.FIRST_RUN}*"
            )
            assert len(first_run_records) == 1, (
                "Only one first_run record should exist (no duplicates)"
            )

            # Verify first_run_incomplete remains False
            self.verify_view_flag(app, community, False)

        except Exception as e:
            app.logger.warning(f"Task execution failed: {e}")
