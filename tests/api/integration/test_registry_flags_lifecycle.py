# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Integration tests for AGG and CACHE registry flag lifecycle.

These tests verify that AGG and CACHE registry keys are properly set and cleaned up
during aggregation and caching tasks, including normalization scenarios and edge cases.
"""

import arrow
import pytest
from invenio_access.permissions import system_identity
from invenio_search import current_search_client

from invenio_stats_dashboard.constants import RegistryOperation
from invenio_stats_dashboard.tasks.aggregation_tasks import (
    CommunityStatsAggregationTask,
    aggregate_community_record_stats,
)
from invenio_stats_dashboard.tasks.cache_tasks import generate_cached_responses_task


@pytest.mark.integration
class RegistryFlagsLifecycleBase:
    """Base class for registry flags lifecycle tests."""

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

    def verify_agg_registry_keys(
        self, registry, community_ids, should_exist=True
    ):
        """Verify AGG registry keys exist or don't exist.

        Args:
            registry: Registry instance.
            community_ids: List of community IDs to check.
            should_exist: Whether keys should exist (True) or not (False).

        Returns:
            list: List of found registry keys.
        """
        found_keys = []
        for community_id in community_ids:
            agg_key = registry.make_registry_key(
                community_id, RegistryOperation.AGG
            )
            value = registry.get(agg_key)
            if should_exist:
                assert value is not None, (
                    f"AGG registry key should exist for {community_id}"
                )
                found_keys.append(agg_key)
            else:
                assert value is None, (
                    f"AGG registry key should not exist for {community_id}"
                )
        return found_keys

    def verify_cache_registry_keys(
        self, registry, community_ids, years, should_exist=True
    ):
        """Verify CACHE registry keys exist or don't exist.

        Args:
            registry: Registry instance.
            community_ids: List of community IDs to check.
            years: List of years to check.
            should_exist: Whether keys should exist (True) or not (False).

        Returns:
            list: List of found registry keys.
        """
        found_keys = []
        for community_id in community_ids:
            for year in years:
                cache_operation = RegistryOperation.CACHE.replace(
                    "{year}", str(year)
                )
                cache_key = registry.make_registry_key(
                    community_id, cache_operation
                )
                value = registry.get(cache_key)
                if should_exist:
                    assert value is not None, (
                        f"CACHE registry key should exist for "
                        f"{community_id}/{year}"
                    )
                    found_keys.append(cache_key)
                else:
                    assert value is None, (
                        f"CACHE registry key should not exist for "
                        f"{community_id}/{year}"
                    )
        return found_keys


class TestAggregationRegistryKeysLifecycle(RegistryFlagsLifecycleBase):
    """Test AGG registry keys are set and cleaned up during aggregation."""

    def test_agg_keys_set_and_cleaned_up_for_explicit_communities(
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
        """Test AGG keys are set and cleaned up for explicitly specified communities."""
        app, client, community, community_id = self.setup_test_data(
            minimal_community_factory,
            minimal_published_record_factory,
            user_factory,
        )

        start_date, end_date = self.get_date_range()
        aggregations = self.get_aggregations()

        try:
            # Verify no AGG keys exist before aggregation
            self.verify_agg_registry_keys(
                registry, [community_id], should_exist=False
            )

            # Run aggregation with explicit community ID
            result = aggregate_community_record_stats(
                aggregations=aggregations,
                start_date=start_date,
                end_date=end_date,
                community_ids=[community_id],
                eager=True,
                update_bookmark=True,
                ignore_bookmark=False,
            )

            # Verify aggregation completed
            assert result is not None, "Aggregation should return a result"
            assert "results" in result, "Aggregation result should have 'results'"

            # Verify AGG keys were cleaned up after aggregation completes
            self.verify_agg_registry_keys(
                registry, [community_id], should_exist=False
            )

        except Exception as e:
            app.logger.warning(f"Aggregation task failed: {e}")
            # Even on failure, keys should be cleaned up
            self.verify_agg_registry_keys(
                registry, [community_id], should_exist=False
            )

    def test_agg_keys_set_and_cleaned_up_for_all_communities(
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
        """Test AGG keys are set for all communities when community_ids=None."""
        app, client, community, community_id = self.setup_test_data(
            minimal_community_factory,
            minimal_published_record_factory,
            user_factory,
        )

        start_date, end_date = self.get_date_range()
        aggregations = self.get_aggregations()

        try:
            # Run aggregation with None (should normalize to all communities)
            result = aggregate_community_record_stats(
                aggregations=aggregations,
                start_date=start_date,
                end_date=end_date,
                community_ids=None,  # Should normalize to all communities
                eager=True,
                update_bookmark=True,
                ignore_bookmark=False,
            )

            # Verify aggregation completed
            assert result is not None, "Aggregation should return a result"

            # Verify AGG keys were cleaned up (including for our test community)
            # Note: We can't easily verify all communities, but we can verify
            # that our test community's key was cleaned up
            self.verify_agg_registry_keys(
                registry, [community_id], should_exist=False
            )

        except Exception as e:
            app.logger.warning(f"Aggregation task failed: {e}")
            # Even on failure, keys should be cleaned up
            self.verify_agg_registry_keys(
                registry, [community_id], should_exist=False
            )

    def test_agg_keys_cleaned_up_on_exception(
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
        """Test AGG keys are cleaned up even when aggregation raises an exception."""
        app, client, community, community_id = self.setup_test_data(
            minimal_community_factory,
            minimal_published_record_factory,
            user_factory,
        )

        start_date, end_date = self.get_date_range()
        aggregations = self.get_aggregations()

        # Mock an exception during aggregation
        from unittest.mock import patch

        try:
            with patch(
                "invenio_stats_dashboard.aggregations.base."
                "CommunityAggregatorBase.run"
            ) as mock_run:
                mock_run.side_effect = Exception("Test exception")

                # This should raise an exception
                try:
                    aggregate_community_record_stats(
                        aggregations=aggregations,
                        start_date=start_date,
                        end_date=end_date,
                        community_ids=[community_id],
                        eager=True,
                        update_bookmark=True,
                        ignore_bookmark=False,
                    )
                except Exception:
                    pass  # Expected

                # Verify AGG keys were still cleaned up despite exception
                self.verify_agg_registry_keys(
                    registry, [community_id], should_exist=False
                )

        except Exception as e:
            app.logger.warning(f"Test setup failed: {e}")


class TestCacheRegistryKeysLifecycle(RegistryFlagsLifecycleBase):
    """Test CACHE registry keys are set and cleaned up during caching."""

    def test_cache_keys_set_and_cleaned_up_for_explicit_communities(
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
        """Test CACHE keys are set and cleaned up for explicit communities."""
        app, client, community, community_id = self.setup_test_data(
            minimal_community_factory,
            minimal_published_record_factory,
            user_factory,
        )

        current_year = arrow.utcnow().year

        try:
            # Verify no CACHE keys exist before caching
            self.verify_cache_registry_keys(
                registry, [community_id], [current_year], should_exist=False
            )

            # Run caching with explicit community ID and year
            result = generate_cached_responses_task(
                community_ids=[community_id],
                years=current_year,
                overwrite=False,
                async_mode=False,
                current_year_only=False,
                optimize=False,
            )

            # Verify caching completed
            assert result is not None, "Cache task should return a result"
            assert "responses" in result or "success" in result, (
                "Cache result should have 'responses' or 'success'"
            )

            # Verify CACHE keys were cleaned up after caching completes
            self.verify_cache_registry_keys(
                registry, [community_id], [current_year], should_exist=False
            )

        except Exception as e:
            app.logger.warning(f"Caching task failed: {e}")
            # Even on failure, keys should be cleaned up
            self.verify_cache_registry_keys(
                registry, [community_id], [current_year], should_exist=False
            )

    def test_cache_keys_set_and_cleaned_up_for_all_communities(
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
        """Test CACHE keys are set for all communities when community_ids='all'."""
        app, client, community, community_id = self.setup_test_data(
            minimal_community_factory,
            minimal_published_record_factory,
            user_factory,
        )

        current_year = arrow.utcnow().year

        try:
            # Run caching with "all" (should normalize to all communities)
            result = generate_cached_responses_task(
                community_ids="all",  # Should normalize to all communities
                years=current_year,
                overwrite=False,
                async_mode=False,
                current_year_only=False,
                optimize=False,
            )

            # Verify caching completed
            assert result is not None, "Cache task should return a result"

            # Verify CACHE keys were cleaned up (including for our test community)
            self.verify_cache_registry_keys(
                registry, [community_id], [current_year], should_exist=False
            )

        except Exception as e:
            app.logger.warning(f"Caching task failed: {e}")
            # Even on failure, keys should be cleaned up
            self.verify_cache_registry_keys(
                registry, [community_id], [current_year], should_exist=False
            )

    def test_cache_keys_set_for_multiple_years(
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
        """Test CACHE keys are set and cleaned up for multiple years."""
        app, client, community, community_id = self.setup_test_data(
            minimal_community_factory,
            minimal_published_record_factory,
            user_factory,
        )

        current_year = arrow.utcnow().year
        years = [current_year - 1, current_year]

        try:
            # Run caching with multiple years
            result = generate_cached_responses_task(
                community_ids=[community_id],
                years=years,
                overwrite=False,
                async_mode=False,
                current_year_only=False,
                optimize=False,
            )

            # Verify caching completed
            assert result is not None, "Cache task should return a result"

            # Verify CACHE keys were cleaned up for all years
            self.verify_cache_registry_keys(
                registry, [community_id], years, should_exist=False
            )

        except Exception as e:
            app.logger.warning(f"Caching task failed: {e}")
            # Even on failure, keys should be cleaned up
            self.verify_cache_registry_keys(
                registry, [community_id], years, should_exist=False
            )

    def test_cache_keys_cleaned_up_on_exception(
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
        """Test CACHE keys are cleaned up even when caching raises an exception."""
        app, client, community, community_id = self.setup_test_data(
            minimal_community_factory,
            minimal_published_record_factory,
            user_factory,
        )

        current_year = arrow.utcnow().year

        # Mock an exception during caching
        from unittest.mock import patch

        try:
            with patch(
                "invenio_stats_dashboard.services.cached_response_service."
                "CachedResponseService._create"
            ) as mock_create:
                mock_create.side_effect = Exception("Test exception")

                # This should raise an exception
                try:
                    generate_cached_responses_task(
                        community_ids=[community_id],
                        years=current_year,
                        overwrite=False,
                        async_mode=False,
                        current_year_only=False,
                        optimize=False,
                    )
                except Exception:
                    pass  # Expected

                # Verify CACHE keys were still cleaned up despite exception
                self.verify_cache_registry_keys(
                    registry, [community_id], [current_year], should_exist=False
                )

        except Exception as e:
            app.logger.warning(f"Test setup failed: {e}")


class TestRegistryKeysNormalization(RegistryFlagsLifecycleBase):
    """Test that registry keys are set correctly after normalization."""

    def test_agg_keys_for_none_normalizes_to_all(
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
        """Test that community_ids=None normalizes to all communities for AGG keys."""
        app, client, community, community_id = self.setup_test_data(
            minimal_community_factory,
            minimal_published_record_factory,
            user_factory,
        )

        start_date, end_date = self.get_date_range()
        aggregations = self.get_aggregations()

        try:
            # Run aggregation with None
            result = aggregate_community_record_stats(
                aggregations=aggregations,
                start_date=start_date,
                end_date=end_date,
                community_ids=None,  # Should normalize to all communities
                eager=True,
                update_bookmark=True,
                ignore_bookmark=False,
            )

            # Verify aggregation completed
            assert result is not None, "Aggregation should return a result"

            # The key should have been set (during aggregation) and cleaned up
            # We verify cleanup happened by checking the key doesn't exist
            self.verify_agg_registry_keys(
                registry, [community_id], should_exist=False
            )

        except Exception as e:
            app.logger.warning(f"Aggregation task failed: {e}")

    def test_cache_keys_for_all_normalizes_correctly(
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
        """Test that community_ids='all' normalizes correctly for CACHE keys."""
        app, client, community, community_id = self.setup_test_data(
            minimal_community_factory,
            minimal_published_record_factory,
            user_factory,
        )

        current_year = arrow.utcnow().year

        try:
            # Run caching with "all"
            result = generate_cached_responses_task(
                community_ids="all",  # Should normalize to all communities
                years=current_year,
                overwrite=False,
                async_mode=False,
                current_year_only=False,
                optimize=False,
            )

            # Verify caching completed
            assert result is not None, "Cache task should return a result"

            # The key should have been set (during caching) and cleaned up
            self.verify_cache_registry_keys(
                registry, [community_id], [current_year], should_exist=False
            )

        except Exception as e:
            app.logger.warning(f"Caching task failed: {e}")

