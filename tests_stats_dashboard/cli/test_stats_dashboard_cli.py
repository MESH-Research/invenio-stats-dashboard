# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Tests for the invenio_stats_dashboard CLI commands."""

from unittest.mock import patch

import arrow
import pytest

from invenio_stats_dashboard.cli import cli

pytest.skip("Skipping CLI tests for now", allow_module_level=True)

@pytest.fixture(scope="module")
def cli_runner(base_app):
    """Create a CLI runner for testing CLI commands."""

    def cli_invoke(command, *args, input=None):
        return base_app.test_cli_runner().invoke(command, args, input=input)

    return cli_invoke


class TestCommunityEventsGenerateCommand:
    """Test the community-events generate CLI command."""

    def test_community_events_generate_no_parameters(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
    ):
        """Test community-events generate command with no parameters."""
        with patch(
            "invenio_stats_dashboard.proxies.current_community_stats_service"
        ) as mock_service:
            # Mock count_records_needing_events to return records that need events
            mock_service.count_records_needing_events.return_value = {
                "total_records": 10,
                "records_needing_events": 5,
                "total_events_needed": 5,
                "community_breakdown": {"global": 5},
                "communities_checked": ["global"],
            }
            mock_service.generate_record_community_events.return_value = (5, 5, 0)

            result = cli_runner(cli, "community-events", "generate")

            assert result.exit_code == 0
            mock_service.count_records_needing_events.assert_called_once_with(
                community_ids=None,
                recids=None,
                start_date=None,
                end_date=None,
            )
            mock_service.generate_record_community_events.assert_called_once_with(
                community_ids=None,
                recids=None,
                start_date=None,
                end_date=None,
            )

    def test_community_events_generate_with_community_ids(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
    ):
        """Test community-events generate command with community IDs."""
        with patch(
            "invenio_stats_dashboard.proxies.current_community_stats_service"
        ) as mock_service:
            # Mock count_records_needing_events to return records that need events
            mock_service.count_records_needing_events.return_value = {
                "total_records": 10,
                "records_needing_events": 3,
                "total_events_needed": 3,
                "community_breakdown": {"comm-1": 2, "comm-2": 1},
                "communities_checked": ["comm-1", "comm-2"],
            }
            mock_service.generate_record_community_events.return_value = (3, 3, 0)

            result = cli_runner(
                cli,
                "community-events",
                "generate",
                "--community-id",
                "comm-1",
                "--community-id",
                "comm-2",
            )

            assert result.exit_code == 0
            mock_service.count_records_needing_events.assert_called_once_with(
                community_ids=["comm-1", "comm-2"],
                recids=None,
                start_date=None,
                end_date=None,
            )
            mock_service.generate_record_community_events.assert_called_once_with(
                community_ids=["comm-1", "comm-2"],
                recids=None,
                start_date=None,
                end_date=None,
            )

    def test_community_events_generate_with_record_ids(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
    ):
        """Test community-events generate command with record IDs."""
        with patch(
            "invenio_stats_dashboard.proxies.current_community_stats_service"
        ) as mock_service:
            # Mock count_records_needing_events to return records that need events
            mock_service.count_records_needing_events.return_value = {
                "total_records": 2,
                "records_needing_events": 2,
                "total_events_needed": 2,
                "community_breakdown": {"global": 2},
                "communities_checked": ["global"],
            }
            mock_service.generate_record_community_events.return_value = (2, 2, 0)

            result = cli_runner(
                cli,
                "community-events",
                "generate",
                "--record-ids",
                "rec-1",
                "--record-ids",
                "rec-2",
            )

            assert result.exit_code == 0
            mock_service.count_records_needing_events.assert_called_once_with(
                community_ids=None,
                recids=["rec-1", "rec-2"],
                start_date=None,
                end_date=None,
            )
            mock_service.generate_record_community_events.assert_called_once_with(
                community_ids=None,
                recids=["rec-1", "rec-2"],
                start_date=None,
                end_date=None,
            )

    def test_community_events_generate_with_both_parameters(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
    ):
        """Test community-events generate command with both community and record IDs."""
        with patch(
            "invenio_stats_dashboard.proxies.current_community_stats_service"
        ) as mock_service:
            # Mock count_records_needing_events to return records that need events
            mock_service.count_records_needing_events.return_value = {
                "total_records": 1,
                "records_needing_events": 1,
                "total_events_needed": 1,
                "community_breakdown": {"comm-1": 1},
                "communities_checked": ["comm-1"],
            }
            mock_service.generate_record_community_events.return_value = (1, 1, 0)

            result = cli_runner(
                cli,
                "community-events",
                "generate",
                "--community-id",
                "comm-1",
                "--record-ids",
                "rec-1",
            )

            assert result.exit_code == 0
            mock_service.count_records_needing_events.assert_called_once_with(
                community_ids=["comm-1"],
                recids=["rec-1"],
                start_date=None,
                end_date=None,
            )
            mock_service.generate_record_community_events.assert_called_once_with(
                community_ids=["comm-1"],
                recids=["rec-1"],
                start_date=None,
                end_date=None,
            )

    def test_community_events_generate_service_error(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
    ):
        """Test community-events generate command when service raises an error."""
        with patch(
            "invenio_stats_dashboard.proxies.current_community_stats_service"
        ) as mock_service:
            # Mock count_records_needing_events to return records that need events
            mock_service.count_records_needing_events.return_value = {
                "total_records": 5,
                "records_needing_events": 5,
                "total_events_needed": 5,
                "community_breakdown": {"global": 5},
                "communities_checked": ["global"],
            }
            mock_service.generate_record_community_events.side_effect = Exception(
                "Service error"
            )

            result = cli_runner(cli, "community-events", "generate")

            assert result.exit_code != 0


class TestAggregateCommand:
    """Test the aggregate CLI command."""

    def test_aggregate_no_parameters(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
        celery_worker,
    ):
        """Test aggregate command with no parameters."""
        with patch(
            "invenio_stats_dashboard.proxies.current_community_stats_service"
        ) as mock_service:
            mock_service.aggregate_stats.return_value = {"status": "success"}

            result = cli_runner(cli, "aggregate")

            assert result.exit_code == 0
            mock_service.aggregate_stats.assert_called_once_with(
                community_ids=None,
                start_date=None,
                end_date=None,
                eager=False,
                update_bookmark=True,
                ignore_bookmark=False,
                verbose=False,
                force=False,
            )

    def test_aggregate_stats_with_community_id(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
        celery_worker,
    ):
        """Test aggregate command with community ID."""
        with patch(
            "invenio_stats_dashboard.proxies.current_community_stats_service"
        ) as mock_service:
            mock_service.aggregate_stats.return_value = {"status": "success"}

            result = cli_runner(cli, "aggregate", "--community-id", "comm-1")

            assert result.exit_code == 0
            mock_service.aggregate_stats.assert_called_once_with(
                community_ids=["comm-1"],
                start_date=None,
                end_date=None,
                eager=False,
                update_bookmark=False,
                ignore_bookmark=False,
            )

    def test_aggregate_stats_with_dates(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
        celery_worker,
    ):
        """Test aggregate command with start and end dates."""
        with patch(
            "invenio_stats_dashboard.proxies.current_community_stats_service"
        ) as mock_service:
            mock_service.aggregate_stats.return_value = {"status": "success"}

            result = cli_runner(
                cli,
                "aggregate",
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-01-31",
            )

            assert result.exit_code == 0
            mock_service.aggregate_stats.assert_called_once_with(
                community_ids=None,
                start_date="2024-01-01",
                end_date="2024-01-31",
                eager=False,
                update_bookmark=False,
                ignore_bookmark=False,
            )

    def test_aggregate_stats_with_eager_flag(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
    ):
        """Test aggregate command with eager flag."""
        with patch(
            "invenio_stats_dashboard.proxies.current_community_stats_service"
        ) as mock_service:
            mock_service.aggregate_stats.return_value = {"status": "success"}

            result = cli_runner(cli, "aggregate", "--eager")

            assert result.exit_code == 0
            mock_service.aggregate_stats.assert_called_once_with(
                community_ids=None,
                start_date=None,
                end_date=None,
                eager=True,
                update_bookmark=False,
                ignore_bookmark=False,
            )

    def test_aggregate_stats_with_update_bookmark_flag(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
        celery_worker,
    ):
        """Test aggregate command with update-bookmark flag."""
        with patch(
            "invenio_stats_dashboard.proxies.current_community_stats_service"
        ) as mock_service:
            mock_service.aggregate_stats.return_value = {"status": "success"}

            result = cli_runner(cli, "aggregate", "--update-bookmark")

            assert result.exit_code == 0
            mock_service.aggregate_stats.assert_called_once_with(
                community_ids=None,
                start_date=None,
                end_date=None,
                eager=False,
                update_bookmark=True,
                ignore_bookmark=False,
            )

    def test_aggregate_stats_with_ignore_bookmark_flag(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
        celery_worker,
    ):
        """Test aggregate command with ignore-bookmark flag."""
        with patch(
            "invenio_stats_dashboard.proxies.current_community_stats_service"
        ) as mock_service:
            mock_service.aggregate_stats.return_value = {"status": "success"}

            result = cli_runner(cli, "aggregate", "--ignore-bookmark")

            assert result.exit_code == 0
            mock_service.aggregate_stats.assert_called_once_with(
                community_ids=None,
                start_date=None,
                end_date=None,
                eager=False,
                update_bookmark=False,
                ignore_bookmark=True,
            )

    def test_aggregate_stats_with_all_parameters(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
        celery_worker,
    ):
        """Test aggregate command with all parameters."""
        with patch(
            "invenio_stats_dashboard.proxies.current_community_stats_service"
        ) as mock_service:
            mock_service.aggregate_stats.return_value = {"status": "success"}

            result = cli_runner(
                cli,
                "aggregate",
                "--community-id",
                "comm-1",
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-01-31",
                "--eager",
                "--update-bookmark",
                "--ignore-bookmark",
            )

            assert result.exit_code == 0
            mock_service.aggregate_stats.assert_called_once_with(
                community_ids=["comm-1"],
                start_date="2024-01-01",
                end_date="2024-01-31",
                eager=True,
                update_bookmark=True,
                ignore_bookmark=True,
            )

    def test_aggregate_stats_service_error(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
    ):
        """Test aggregate command when service raises an error."""
        with patch(
            "invenio_stats_dashboard.proxies.current_community_stats_service"
        ) as mock_service:
            mock_service.aggregate_stats.side_effect = Exception("Service error")

            result = cli_runner(cli, "aggregate")

            assert result.exit_code != 0


class TestReadStatsCommand:
    """Test the read CLI command."""

    def test_read_stats_default_parameters(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
    ):
        """Test read command with default parameters."""
        with patch(
            "invenio_stats_dashboard.proxies.current_community_stats_service"
        ) as mock_service:
            mock_stats = {
                "community_id": "global",
                "total_records": 100,
                "daily_stats": [],
            }
            mock_service.get_community_stats.return_value = mock_stats

            result = cli_runner(cli, "read")

            assert result.exit_code == 0
            # Check that the command printed the stats
            assert "Reading stats for community global" in result.output
            # Verify the service was called with default dates
            mock_service.get_community_stats.assert_called_once()
            call_args = mock_service.get_community_stats.call_args
            assert call_args[0][0] == "global"  # community_id
            # The dates should be yesterday and today
            start_date = arrow.get(call_args[0][1])
            end_date = arrow.get(call_args[0][2])
            assert start_date.date() == arrow.get().shift(days=-1).date()
            assert end_date.date() == arrow.get().date()

    def test_read_stats_with_custom_community(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
    ):
        """Test read command with custom community ID."""
        with patch(
            "invenio_stats_dashboard.proxies.current_community_stats_service"
        ) as mock_service:
            mock_stats = {
                "community_id": "comm-1",
                "total_records": 50,
                "daily_stats": [],
            }
            mock_service.get_community_stats.return_value = mock_stats

            result = cli_runner(cli, "read", "--community-id", "comm-1")

            assert result.exit_code == 0
            assert "Reading stats for community comm-1" in result.output
            mock_service.get_community_stats.assert_called_once_with(
                "comm-1",
                start_date=mock_service.get_community_stats.call_args[0][1],
                end_date=mock_service.get_community_stats.call_args[0][2],
            )

    def test_read_stats_with_custom_dates(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
    ):
        """Test read command with custom dates."""
        with patch(
            "invenio_stats_dashboard.proxies.current_community_stats_service"
        ) as mock_service:
            mock_stats = {
                "community_id": "global",
                "total_records": 75,
                "daily_stats": [],
            }
            mock_service.get_community_stats.return_value = mock_stats

            result = cli_runner(
                cli,
                "read",
                "--start-date",
                "2024-01-01T00:00:00Z",
                "--end-date",
                "2024-01-31T23:59:59Z",
            )

            assert result.exit_code == 0
            assert "Reading stats for community global" in result.output
            assert "from 2024-01-01T00:00:00Z to 2024-01-31T23:59:59Z" in result.output
            mock_service.get_community_stats.assert_called_once_with(
                "global",
                start_date="2024-01-01T00:00:00Z",
                end_date="2024-01-31T23:59:59Z",
            )

    def test_read_stats_with_all_parameters(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
    ):
        """Test read command with all parameters."""
        with patch(
            "invenio_stats_dashboard.proxies.current_community_stats_service"
        ) as mock_service:
            mock_stats = {
                "community_id": "comm-1",
                "total_records": 25,
                "daily_stats": [
                    {"date": "2024-01-15", "count": 5},
                    {"date": "2024-01-16", "count": 3},
                ],
            }
            mock_service.get_community_stats.return_value = mock_stats

            result = cli_runner(
                cli,
                "read",
                "--community-id",
                "comm-1",
                "--start-date",
                "2024-01-15T00:00:00Z",
                "--end-date",
                "2024-01-16T23:59:59Z",
            )

            assert result.exit_code == 0
            assert "Reading stats for community comm-1" in result.output
            assert "from 2024-01-15T00:00:00Z to 2024-01-16T23:59:59Z" in result.output
            # Check that the stats were printed (pprint output)
            assert "comm-1" in result.output
            assert "25" in result.output
            mock_service.get_community_stats.assert_called_once_with(
                "comm-1",
                start_date="2024-01-15T00:00:00Z",
                end_date="2024-01-16T23:59:59Z",
            )

    def test_read_stats_service_error(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
    ):
        """Test read command when service raises an error."""
        with patch(
            "invenio_stats_dashboard.proxies.current_community_stats_service"
        ) as mock_service:
            mock_service.get_community_stats.side_effect = Exception("Service error")

            result = cli_runner(cli, "read")

            assert result.exit_code != 0


class TestCLIHelp:
    """Test CLI help functionality."""

    def test_cli_help(self, running_app, cli_runner):
        """Test that the CLI shows help information."""
        result = cli_runner(cli, "--help")

        assert result.exit_code == 0
        assert "generate-events" in result.output
        assert "aggregate" in result.output
        assert "read" in result.output

    def test_generate_events_help(self, running_app, cli_runner):
        """Test generate-events command help."""
        result = cli_runner(cli, "generate-events", "--help")

        assert result.exit_code == 0
        assert "--community-id" in result.output
        assert "--record-ids" in result.output

    def test_aggregate_stats_help(self, running_app, cli_runner):
        """Test aggregate command help."""
        result = cli_runner(cli, "aggregate", "--help")

        assert result.exit_code == 0
        assert "--community-id" in result.output
        assert "--start-date" in result.output
        assert "--end-date" in result.output
        assert "--eager" in result.output
        assert "--update-bookmark" in result.output
        assert "--ignore-bookmark" in result.output

    def test_read_stats_help(self, running_app, cli_runner):
        """Test read command help."""
        result = cli_runner(cli, "read", "--help")

        assert result.exit_code == 0
        assert "--community-id" in result.output
        assert "--start-date" in result.output
        assert "--end-date" in result.output


class TestUsageEventsCommand:
    """Test the usage-events CLI commands."""

    def test_usage_events_generate_no_parameters(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
    ):
        """Test usage-events generate command with no parameters."""
        with patch(
            "invenio_stats_dashboard.utils.usage_events.UsageEventFactory"
        ) as mock_factory:
            mock_instance = mock_factory.return_value
            mock_instance.generate_and_index_repository_events.return_value = {
                "indexed": 10,
                "errors": 0,
            }

            result = cli_runner(cli, "usage-events", "generate")

            assert result.exit_code == 0
            mock_instance.generate_and_index_repository_events.assert_called_once()

    def test_usage_events_generate_with_parameters(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
    ):
        """Test usage-events generate command with parameters."""
        with patch(
            "invenio_stats_dashboard.utils.usage_events.UsageEventFactory"
        ) as mock_factory:
            mock_instance = mock_factory.return_value
            mock_instance.generate_and_index_repository_events.return_value = {
                "indexed": 5,
                "errors": 0,
            }

            result = cli_runner(
                cli,
                "usage-events",
                "generate",
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-01-31",
                "--events-per-record",
                "10",
            )

            assert result.exit_code == 0
            mock_instance.generate_and_index_repository_events.assert_called_once()


class TestProcessesCommand:
    """Test the processes CLI commands."""

    def test_processes_status_no_parameters(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
    ):
        """Test processes status command with no parameters."""
        result = cli_runner(cli, "processes", "status")

        # This command might fail if no process is running, but should not crash
        assert result.exit_code in [0, 1]

    def test_processes_status_with_parameters(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
    ):
        """Test processes status command with parameters."""
        result = cli_runner(
            cli,
            "processes",
            "status",
            "test-process",
            "--show-log",
            "--log-lines",
            "10",
        )

        # This command might fail if no process is running, but should not crash
        assert result.exit_code in [0, 1]


class TestCLIIntegration:
    """Integration tests for CLI commands with real service calls."""

    def test_generate_events_integration(
        self,
        running_app,
        db,
        minimal_community_factory,
        minimal_published_record_factory,
        search_clear,
        cli_runner,
    ):
        """Test generate-events command with real service integration."""
        # Create a test community
        community = minimal_community_factory(
            metadata={"title": "Test Community"},
            slug="test-community",
        )
        community_id = community.id

        # Create a test record
        record = minimal_published_record_factory(
            metadata={
                "metadata": {
                    "resource_type": {"id": "textDocument-journalArticle"},
                    "title": "Test Record",
                    "publisher": "Test Publisher",
                    "publication_date": "2025-01-01",
                    "creators": [
                        {
                            "person_or_org": {
                                "name": "Test Creator",
                                "family_name": "Creator",
                                "given_name": "Test",
                                "type": "personal",
                            }
                        }
                    ],
                },
                "files": {"enabled": False},
            },
            community_list=[community_id],
        )

        # Test the command
        result = cli_runner(
            cli,
            "community-events",
            "generate",
            "--community-id",
            community_id,
            "--record-ids",
            record.id,
        )

        assert result.exit_code == 0

    def test_read_stats_integration(
        self,
        running_app,
        db,
        search_clear,
        cli_runner,
    ):
        """Test read command with real service integration."""
        # Test with default parameters
        result = cli_runner(cli, "read")

        # The command should succeed even if no stats exist yet
        assert result.exit_code == 0
        assert "Reading stats for community global" in result.output
