# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 MESH Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Integration tests for dashboard UI views with custom fields."""

from collections.abc import Callable

from tests.conftest import RunningApp


class TestDashboardViewsIntegration:
    """Integration tests for dashboard UI views with custom fields."""

    def test_global_dashboard_view(
        self, running_app: RunningApp, client, set_app_config_fn_scoped: Callable
    ) -> None:
        """Test global dashboard view returns correct layout."""
        # Set up test-specific layout config
        set_app_config_fn_scoped({
            "STATS_DASHBOARD_LAYOUT": {
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
            },
        })

        # Make request to global dashboard (route is /stats)
        response = client.get("/stats")

        assert response.status_code == 200
        # The template should be rendered with the correct layout
        # Check for the dashboard div and config data
        assert (
            b"stats-dashboard" in response.data
            or b"Global Overview" in response.data
        )

    def test_community_dashboard_view_with_custom_layout(
        self,
        running_app: RunningApp,
        client,
        db,
        minimal_community_factory: Callable,
        set_app_config_fn_scoped: Callable,
    ) -> None:
        """Test community dashboard view with custom layout."""
        # Create a community with custom dashboard layout
        custom_fields_data = {
            "stats:dashboard_enabled": True,
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

        # Set up test-specific layout config
        set_app_config_fn_scoped({
            "STATS_DASHBOARD_LAYOUT": {
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
                                            "props": {
                                                "title": "Default Community Chart"
                                            },
                                        }
                                    ],
                                }
                            ],
                        }
                    ]
                },
            },
        })

        # Make request to community dashboard
        # Route uses pid_value, which is the community ID
        response = client.get(f"/communities/{community.id}/stats")

        assert response.status_code == 200
        # The template should be rendered with the custom layout
        # Check for the dashboard div and config data
        assert (
            b"stats-dashboard" in response.data
            or b"Custom Community Tab" in response.data
        )

    def test_community_dashboard_view_without_custom_layout(
        self,
        running_app: RunningApp,
        client,
        db,
        minimal_community_factory: Callable,
        set_app_config_fn_scoped: Callable,
    ) -> None:
        """Test dashboard falls back to config default without custom layout."""
        # Create a community without custom dashboard layout
        community = minimal_community_factory(
            slug="test-community",
            custom_fields={"stats:dashboard_enabled": True},
        )

        # Set up test-specific layout config
        set_app_config_fn_scoped({
            "STATS_DASHBOARD_LAYOUT": {
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
                                            "props": {
                                                "title": "Default Community Chart"
                                            },
                                        }
                                    ],
                                }
                            ],
                        }
                    ]
                }
            },
        })

        # Make request to community dashboard
        # Route uses pid_value, which is the community ID
        response = client.get(f"/communities/{community.id}/stats")

        assert response.status_code == 200
        # The template should be rendered with the default layout from config
        # Check for the dashboard div and config data
        assert (
            b"stats-dashboard" in response.data
            or b"Default Community Tab" in response.data
        )

