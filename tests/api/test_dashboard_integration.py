# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 MESH Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Integration tests for dashboard views with custom fields."""

from collections.abc import Callable

import pytest

from tests.conftest import RunningApp


class TestDashboardViewsIntegration:
    """Integration tests for dashboard views with custom fields."""

    @pytest.mark.skip(
        reason="Integration tests with actual view calls not yet implemented"
    )
    def test_global_dashboard_view(
        self, running_app: RunningApp, client: Callable
    ) -> None:
        """Test global dashboard view returns correct layout."""
        # Mock the global dashboard layout config
        running_app.app.config["STATS_DASHBOARD_LAYOUT"] = {
            "global_layout": {
                "tabs": [
                    {
                        "name": "Global Overview",
                        "label": "Global Overview Label",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {
                                        "component": "SingleStatRecordCount",
                                        "props": {"title": "Global Downloads"},
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        }

        # Make request to global dashboard
        response = client.get("/stats/dashboard/global")

        assert response.status_code == 200
        # The template should be rendered with the correct layout
        assert b"Global Overview" in response.data

    @pytest.mark.skip(
        reason="Integration tests with actual view calls not yet implemented"
    )
    def test_community_dashboard_view_with_custom_layout(
        self,
        running_app: RunningApp,
        client: Callable,
        minimal_community_factory: Callable,
    ) -> None:
        """Test community dashboard view with custom layout."""
        # Create a community with custom dashboard layout
        custom_fields_data = {
            "stats:dashboard_layout": {
                "community_layout": {
                    "tabs": [
                        {
                            "name": "Custom Community Tab",
                            "label": "Custom Community Tab Label",
                            "rows": [
                                {
                                    "name": "row1",
                                    "components": [
                                        {
                                            "component": "SingleStatRecordCount",
                                            "props": {
                                                "title": "Custom Community Chart"
                                            },
                                        }
                                    ],
                                }
                            ],
                        }
                    ]
                }
            }
        }

        community = minimal_community_factory(
            slug="test-community", custom_fields=custom_fields_data
        )

        # Mock the default dashboard layout config
        running_app.app.config["STATS_DASHBOARD_LAYOUT"] = {
            "global_layout": {
                "tabs": [
                    {
                        "name": "Global Overview",
                        "label": "Global Overview Label",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {
                                        "component": "SingleStatRecordCount",
                                        "props": {"title": "Global Downloads"},
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
            "community_layout": {
                "tabs": [
                    {
                        "name": "Default Community Tab",
                        "label": "Default Community Tab Label",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {
                                        "component": "SingleStatRecordCount",
                                        "props": {"title": "Default Community Chart"},
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
        }

        # Make request to community dashboard
        response = client.get(f"/communities/{community.slug}/stats/dashboard")

        assert response.status_code == 200
        # The template should be rendered with the custom layout
        assert b"Custom Community Tab" in response.data

    @pytest.mark.skip(
        reason="Integration tests with actual view calls not yet implemented"
    )
    def test_community_dashboard_view_without_custom_layout(
        self,
        running_app: RunningApp,
        client: Callable,
        minimal_community_factory: Callable,
    ) -> None:
        """Test community dashboard view without custom layout falls back to default."""
        # Create a community without custom dashboard layout
        community = minimal_community_factory(slug="test-community")

        # Mock the default dashboard layout config
        running_app.app.config["STATS_DASHBOARD_LAYOUT"] = {
            "global_layout": {
                "tabs": [
                    {
                        "name": "Global Overview",
                        "label": "Global Overview Label",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {
                                        "component": "SingleStatRecordCount",
                                        "props": {"title": "Global Downloads"},
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
            "community_layout": {
                "tabs": [
                    {
                        "name": "Default Community Tab",
                        "label": "Default Community Tab Label",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {
                                        "component": "SingleStatRecordCount",
                                        "props": {"title": "Default Community Chart"},
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
        }

        # Make request to community dashboard
        response = client.get(f"/communities/{community.slug}/stats/dashboard")

        assert response.status_code == 200
        # The template should be rendered with the default layout
        assert b"Default Community Tab" in response.data

    @pytest.mark.skip(
        reason="Integration tests with actual view calls not yet implemented"
    )
    def test_community_dashboard_view_fallback_to_global(
        self, running_app, client, minimal_community_factory
    ):
        """Test community dashboard view falls back to global config."""
        # Create a community with only global custom layout
        custom_fields_data = {
            "stats:dashboard_layout": {
                "global_layout": {
                    "tabs": [
                        {
                            "name": "Custom Global Tab",
                            "label": "Custom Global Tab Label",
                            "rows": [
                                {
                                    "name": "row1",
                                    "components": [
                                        {
                                            "component": "SingleStatRecordCount",
                                            "props": {"title": "Custom Global Chart"},
                                        }
                                    ],
                                }
                            ],
                        }
                    ]
                }
            }
        }

        community = minimal_community_factory(
            slug="test-community", custom_fields=custom_fields_data
        )

        # Mock the default dashboard layout config
        running_app.app.config["STATS_DASHBOARD_LAYOUT"] = {
            "global_layout": {
                "tabs": [
                    {
                        "name": "Default Global Tab",
                        "label": "Default Global Tab Label",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {
                                        "component": "SingleStatRecordCount",
                                        "props": {"title": "Default Global Chart"},
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
            "community_layout": {
                "tabs": [
                    {
                        "name": "Default Community Tab",
                        "label": "Default Community Tab Label",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {
                                        "component": "SingleStatRecordCount",
                                        "props": {"title": "Default Community Chart"},
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
        }

        # Make request to community dashboard
        response = client.get(f"/communities/{community.slug}/stats/dashboard")

        assert response.status_code == 200
        # Should fallback to global config since no community-specific config
        assert b"Default Global Tab" in response.data

    @pytest.mark.skip(
        reason="Integration tests with actual view calls not yet implemented"
    )
    def test_dashboard_config_passed_to_template(
        self, running_app, client, minimal_community_factory
    ):
        """Test that dashboard config is properly passed to template."""
        # Create a community with custom layout
        custom_fields_data = {
            "stats:dashboard_layout": {
                "community_layout": {
                    "tabs": [
                        {
                            "name": "Test Tab",
                            "label": "Test Tab Label",
                            "rows": [
                                {
                                    "name": "row1",
                                    "components": [
                                        {
                                            "component": "SingleStatUploaders",
                                            "props": {
                                                "title": "Test Metric",
                                                "icon": "users",
                                            },
                                        }
                                    ],
                                }
                            ],
                        }
                    ]
                }
            }
        }

        community = minimal_community_factory(
            slug="test-community", custom_fields=custom_fields_data
        )

        # Mock the dashboard layout config
        running_app.app.config["STATS_DASHBOARD_LAYOUT"] = {
            "community_layout": {
                "tabs": [
                    {
                        "name": "Default Tab",
                        "label": "Default Tab Label",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {
                                        "component": "SingleStatRecordCount",
                                        "props": {"title": "Default Chart"},
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        }

        # Mock other required config
        running_app.app.config["STATS_DASHBOARD_TEMPLATES"] = {
            "community": "invenio_stats_dashboard/community_dashboard.html"
        }
        running_app.app.config["STATS_DASHBOARD_UI_CONFIG"] = {"community_layout": {}}
        running_app.app.config["STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS"] = []

        # Make request to community dashboard
        response = client.get(f"/communities/{community.slug}/stats/dashboard")

        assert response.status_code == 200

        # Verify the custom layout data is in the response
        # The template should receive the custom layout in dashboard_config
        assert b"Test Tab" in response.data
        assert b"Test Metric" in response.data
        assert b"42" in response.data

    @pytest.mark.skip(
        reason="Integration tests with actual view calls not yet implemented"
    )
    def test_permission_check_in_community_dashboard(
        self, running_app, client, minimal_community_factory, user_factory
    ):
        """Test that permission check works correctly in community dashboard."""
        # Create a community
        community = minimal_community_factory(slug="test-community")

        # Create a user who is not a member of the community
        user = user_factory(email="test@example.com")

        # Mock the dashboard layout config
        running_app.app.config["STATS_DASHBOARD_LAYOUT"] = {
            "community_layout": {
                "tabs": [
                    {
                        "name": "Default Tab",
                        "label": "Default Tab Label",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {
                                        "component": "SingleStatRecordCount",
                                        "props": {"title": "Default Chart"},
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        }

        # Login as the user
        client.login_user(user.user)

        # Make request to community dashboard
        response = client.get(f"/communities/{community.slug}/stats/dashboard")

        # Should be denied access if user doesn't have read permission
        # The exact status code depends on how permissions are configured
        # but it should not be 200 if user lacks permission
        assert (
            response.status_code != 200
            or b"Permission denied" in response.data
            or b"403" in response.data
        )
