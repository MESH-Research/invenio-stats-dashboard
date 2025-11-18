# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Tests for the enable-dashboards CLI command."""

from unittest.mock import patch

import arrow
from invenio_search.proxies import current_search_client
from invenio_search.utils import prefix_index

from invenio_stats_dashboard.cli import cli


def test_enable_dashboards_with_community_ids(
    running_app,
    db,
    search_clear,
    cli_runner,
    minimal_community_factory,
    user_factory,
):
    """Test enable-dashboards command with community IDs."""
    user = user_factory(email="test@example.com")
    community1 = minimal_community_factory(slug="comm-1", owner=user.user.id)
    community2 = minimal_community_factory(slug="comm-2", owner=user.user.id)

    result = cli_runner(
        cli,
        None,
        "enable-dashboards",
        community1.id,
        community2.id,
    )

    assert result.exit_code == 0
    assert "Enabling stats dashboards" in result.output
    assert "Enabled dashboards for" in result.output


def test_enable_dashboards_with_first_active(
    running_app,
    db,
    search_clear,
    cli_runner,
    minimal_community_factory,
    user_factory,
    create_stats_indices,
):
    """Test enable-dashboards command with --first-active option."""
    user = user_factory(email="test@example.com")
    community1 = minimal_community_factory(slug="comm-1", owner=user.user.id)

    # Create a community event
    client = current_search_client
    event_year = arrow.utcnow().year
    write_index = prefix_index(f"stats-community-events-{event_year}")
    event = {
        "record_id": "test-record",
        "community_id": community1.id,
        "event_type": "added",
        "event_date": "2024-01-15T10:00:00Z",
        "is_deleted": False,
        "timestamp": arrow.utcnow().isoformat(),
        "updated_timestamp": arrow.utcnow().isoformat(),
    }
    client.index(index=write_index, body=event)
    client.indices.refresh(index=write_index)

    result = cli_runner(
        cli,
        None,
        "enable-dashboards",
        "--first-active",
        "2024-01-18",
    )

    assert result.exit_code == 0
    assert "Enabling stats dashboards" in result.output


def test_enable_dashboards_with_active_since(
    running_app,
    db,
    search_clear,
    cli_runner,
    minimal_community_factory,
    user_factory,
    create_stats_indices,
):
    """Test enable-dashboards command with --active-since option."""
    user = user_factory(email="test@example.com")
    community1 = minimal_community_factory(slug="comm-1", owner=user.user.id)

    # Create a community event
    client = current_search_client
    event_year = arrow.utcnow().year
    write_index = prefix_index(f"stats-community-events-{event_year}")
    event = {
        "record_id": "test-record",
        "community_id": community1.id,
        "event_type": "added",
        "event_date": "2024-01-20T10:00:00Z",
        "is_deleted": False,
        "timestamp": arrow.utcnow().isoformat(),
        "updated_timestamp": arrow.utcnow().isoformat(),
    }
    client.index(index=write_index, body=event)
    client.indices.refresh(index=write_index)

    result = cli_runner(
        cli,
        None,
        "enable-dashboards",
        "--active-since",
        "2024-01-18",
    )

    assert result.exit_code == 0
    assert "Enabling stats dashboards" in result.output


def test_enable_dashboards_with_record_threshold(
    running_app,
    db,
    search_clear,
    cli_runner,
    minimal_community_factory,
    user_factory,
    create_stats_indices,
):
    """Test enable-dashboards command with --record-threshold option."""
    user = user_factory(email="test@example.com")
    community1 = minimal_community_factory(slug="comm-1", owner=user.user.id)

    # Create multiple community events
    client = current_search_client
    event_year = arrow.utcnow().year
    write_index = prefix_index(f"stats-community-events-{event_year}")
    for i in range(3):
        event = {
            "record_id": f"test-record-{i}",
            "community_id": community1.id,
            "event_type": "added",
            "event_date": f"2024-01-{15 + i}T10:00:00Z",
            "is_deleted": False,
            "timestamp": arrow.utcnow().isoformat(),
            "updated_timestamp": arrow.utcnow().isoformat(),
        }
        client.index(index=write_index, body=event)
    client.indices.refresh(index=write_index)

    result = cli_runner(
        cli,
        None,
        "enable-dashboards",
        "--record-threshold",
        "2",
    )

    assert result.exit_code == 0
    assert "Enabling stats dashboards" in result.output


def test_enable_dashboards_with_verbose(
    running_app,
    db,
    search_clear,
    cli_runner,
    minimal_community_factory,
    user_factory,
):
    """Test enable-dashboards command with --verbose flag."""
    user = user_factory(email="test@example.com")
    community1 = minimal_community_factory(slug="comm-1", owner=user.user.id)

    result = cli_runner(
        cli,
        None,
        "enable-dashboards",
        "--verbose",
        community1.id,
    )

    assert result.exit_code == 0
    assert "Enabling stats dashboards" in result.output


def test_enable_dashboards_no_parameters(
    running_app,
    db,
    search_clear,
    cli_runner,
):
    """Test enable-dashboards command with no parameters."""
    result = cli_runner(cli, None, "enable-dashboards")

    assert result.exit_code == 0
    assert "No community ids or selection criteria provided" in result.output


def test_enable_dashboards_service_error(
    running_app,
    db,
    search_clear,
    cli_runner,
):
    """Test enable-dashboards command when service raises an error."""
    with patch(
        "invenio_stats_dashboard.cli.core_cli.CommunityDashboardsService"
    ) as mock_service_class:
        mock_service = mock_service_class.return_value
        mock_service.enable_community_dashboards.side_effect = Exception(
            "Service error"
        )

        result = cli_runner(
            cli,
            None,
            "enable-dashboards",
            "test-community-id",
        )

        assert result.exit_code == 0  # Command catches exceptions
        assert "Something went wrong" in result.output

