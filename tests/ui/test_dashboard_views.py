# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 MESH Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Tests for dashboard UI view functions to verify template context variables."""

from collections.abc import Callable
from unittest.mock import patch

import pytest
from flask import Flask, g
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities
from invenio_records_resources.services.errors import PermissionDeniedError

from invenio_stats_dashboard.constants import FirstRunStatus, RegistryOperation
from invenio_stats_dashboard.resources.cache_utils import StatsAggregationRegistry
from invenio_stats_dashboard.views.views import (
    community_stats_dashboard,
    global_stats_dashboard,
)
from tests.conftest import RunningApp


class TestGlobalStatsDashboardView:
    """Test the global_stats_dashboard view function."""

    def test_global_dashboard_passes_correct_config_to_template(
        self, app: Flask
    ) -> None:
        """Test that global dashboard view passes correct config to template."""
        # Set up app config
        app.config["STATS_DASHBOARD_ENABLED_GLOBAL"] = True
        app.config["STATS_DASHBOARD_DISABLED_MESSAGE_GLOBAL"] = (
            "The global statistics dashboard must be enabled by the "
            "{title} administrators."
        )
        app.config["THEME_SHORT_TITLE"] = "Test Site"
        app.config["STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS"] = [
            {"value": "30days", "label": "Last 30 days"}
        ]
        app.config["STATS_DASHBOARD_LAYOUT"] = {
            "global_layout": {
                "tabs": [
                    {
                        "name": "overview",
                        "label": "Overview",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {"component": "SingleStatRecordCount"}
                                ],
                            }
                        ],
                    }
                ]
            }
        }
        app.config["STATS_DASHBOARD_UI_SUBCOUNTS"] = {}
        app.config["STATS_DASHBOARD_UI_CONFIG"] = {"global": {"show_title": True}}
        app.config["STATS_DASHBOARD_CLIENT_CACHE_COMPRESSION_ENABLED"] = False
        app.config["STATS_DASHBOARD_COMPRESS_JSON"] = True
        app.config["APP_RDM_DISPLAY_DECIMAL_FILE_SIZES"] = True
        app.config["STATS_DASHBOARD_USE_TEST_DATA"] = False

        with app.test_request_context():
            with patch(
                "invenio_stats_dashboard.views.views.render_template"
            ) as mock_render:
                mock_render.return_value = "rendered template"

                global_stats_dashboard()

                # Verify render_template was called
                assert mock_render.called
                call_args = mock_render.call_args

                # Verify template name
                assert call_args[0][0] == "invenio_stats_dashboard/stats_dashboard.html"

                # Verify dashboard_config is passed
                assert "dashboard_config" in call_args[1]
                dashboard_config = call_args[1]["dashboard_config"]

                # Verify all expected config values
                assert dashboard_config["dashboard_type"] == "global"
                assert dashboard_config["dashboard_enabled"] is True
                assert dashboard_config["client_cache_compression_enabled"] is False
                assert dashboard_config["compress_json"] is True
                assert dashboard_config["display_binary_sizes"] is False  # Inverted
                assert dashboard_config["use_test_data"] is False
                assert dashboard_config["layout"] == {
                    "tabs": [
                        {
                            "name": "overview",
                            "label": "Overview",
                            "rows": [
                                {
                                    "name": "row1",
                                    "components": [
                                        {"component": "SingleStatRecordCount"}
                                    ],
                                }
                            ],
                        }
                    ]
                }
                assert dashboard_config["ui_subcounts"] == {}
                assert dashboard_config["default_range_options"] == [
                    {"value": "30days", "label": "Last 30 days"}
                ]

                # Verify disabled message is formatted correctly
                assert "Test Site" in dashboard_config["disabled_message"]

    def test_global_dashboard_when_disabled(self, app: Flask) -> None:
        """Test that global dashboard passes disabled config when disabled."""
        app.config["STATS_DASHBOARD_ENABLED_GLOBAL"] = False
        app.config["STATS_DASHBOARD_DISABLED_MESSAGE_GLOBAL"] = (
            "The global statistics dashboard must be enabled by the "
            "{title} administrators."
        )
        app.config["THEME_SHORT_TITLE"] = "Test Site"
        app.config["STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS"] = []
        app.config["STATS_DASHBOARD_LAYOUT"] = {"global_layout": {}}
        app.config["STATS_DASHBOARD_UI_SUBCOUNTS"] = {}
        app.config["STATS_DASHBOARD_UI_CONFIG"] = {"global": {}}
        app.config["STATS_DASHBOARD_CLIENT_CACHE_COMPRESSION_ENABLED"] = False
        app.config["STATS_DASHBOARD_COMPRESS_JSON"] = True
        app.config["APP_RDM_DISPLAY_DECIMAL_FILE_SIZES"] = True
        app.config["STATS_DASHBOARD_USE_TEST_DATA"] = False

        with app.test_request_context():
            with patch(
                "invenio_stats_dashboard.views.views.render_template"
            ) as mock_render:
                mock_render.return_value = "rendered template"

                global_stats_dashboard()

                dashboard_config = mock_render.call_args[1]["dashboard_config"]
                assert dashboard_config["dashboard_enabled"] is False

    def test_global_dashboard_csrf_cookie_reset(self, app: Flask) -> None:
        """Test that CSRF cookie is reset for global dashboard."""
        app.config["STATS_DASHBOARD_ENABLED_GLOBAL"] = True
        app.config["STATS_DASHBOARD_DISABLED_MESSAGE_GLOBAL"] = "Disabled"
        app.config["THEME_SHORT_TITLE"] = "Test"
        app.config["STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS"] = []
        app.config["STATS_DASHBOARD_LAYOUT"] = {"global_layout": {}}
        app.config["STATS_DASHBOARD_UI_SUBCOUNTS"] = {}
        app.config["STATS_DASHBOARD_UI_CONFIG"] = {"global": {}}
        app.config["STATS_DASHBOARD_CLIENT_CACHE_COMPRESSION_ENABLED"] = False
        app.config["STATS_DASHBOARD_COMPRESS_JSON"] = True
        app.config["APP_RDM_DISPLAY_DECIMAL_FILE_SIZES"] = True
        app.config["STATS_DASHBOARD_USE_TEST_DATA"] = False

        with app.test_request_context() as req_ctx:
            with patch(
                "invenio_stats_dashboard.views.views.render_template"
            ) as mock_render:
                mock_render.return_value = "rendered template"

                global_stats_dashboard()

                # Verify CSRF cookie reset is set
                assert hasattr(req_ctx.request, "csrf_cookie_needs_reset")
                assert req_ctx.request.csrf_cookie_needs_reset is True


class TestCommunityStatsDashboardView:
    """Test the community_stats_dashboard view function."""

    def test_community_dashboard_passes_correct_config_to_template(
        self,
        running_app: RunningApp,
        db,
        minimal_community_factory: Callable,
        set_app_config_fn_scoped: Callable,
        anon_identity,
    ) -> None:
        """Test that community dashboard view passes correct config to template."""
        app = running_app.app

        # Create a community with dashboard enabled
        community = minimal_community_factory(
            slug="test-community",
            custom_fields={"stats:dashboard_enabled": True},
        )

        # Set up temporary config
        set_app_config_fn_scoped({
            "STATS_DASHBOARD_ENABLED_COMMUNITY": True,
            "STATS_DASHBOARD_ENABLED_GLOBAL": True,
            "STATS_DASHBOARD_COMMUNITY_OPT_IN": True,
            "STATS_DASHBOARD_DISABLED_MESSAGE_COMMUNITY": (
                "Community managers can enable the dashboard from settings"
            ),
            "STATS_DASHBOARD_DISABLED_MESSAGE_GLOBAL": (
                "The global statistics dashboard must be enabled by the "
                "{title} administrators."
            ),
            "THEME_SHORT_TITLE": "Test Site",
            "STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS": [
                {"value": "30days", "label": "Last 30 days"}
            ],
            "STATS_DASHBOARD_LAYOUT": {
                "global_layout": {
                    "tabs": [
                        {
                            "name": "global",
                            "label": "Global",
                            "rows": [
                                {
                                    "name": "row1",
                                    "components": [
                                        {"component": "SingleStatRecordCount"}
                                    ],
                                }
                            ],
                        }
                    ]
                },
                "community_layout": {
                    "tabs": [
                        {
                            "name": "community",
                            "label": "Community",
                            "rows": [
                                {
                                    "name": "row1",
                                    "components": [
                                        {"component": "SingleStatRecordCount"}
                                    ],
                                }
                            ],
                        }
                    ]
                },
            },
            "STATS_DASHBOARD_UI_SUBCOUNTS": {},
            "STATS_DASHBOARD_UI_CONFIG": {"community": {"show_title": True}},
            "STATS_DASHBOARD_CLIENT_CACHE_COMPRESSION_ENABLED": False,
            "STATS_DASHBOARD_COMPRESS_JSON": True,
            "APP_RDM_DISPLAY_DECIMAL_FILE_SIZES": True,
            "STATS_DASHBOARD_USE_TEST_DATA": False,
        })

        community_route_template = app.config["STATS_DASHBOARD_ROUTES"]["community"]
        community_route = community_route_template.replace(
            "<pid_value>", str(community.id)
        )
        with app.test_request_context(
            path=community_route
        ):
            # Set up g.identity for the @pass_community decorator
            g.identity = anon_identity

            with patch(
                "invenio_stats_dashboard.views.views.render_template"
            ) as mock_render:
                mock_render.return_value = "rendered template"

                # Call view directly with pid_value - decorator fetches community
                community_stats_dashboard(pid_value=community.id)

                # Verify render_template was called
                assert mock_render.called
                call_args = mock_render.call_args

                # Verify template name
                assert call_args[0][0] == "invenio_communities/details/stats/index.html"

                # Verify dashboard_config is passed
                assert "dashboard_config" in call_args[1]
                dashboard_config = call_args[1]["dashboard_config"]

                # Verify all expected config values
                assert dashboard_config["dashboard_type"] == "community"
                assert dashboard_config["dashboard_enabled"] is True
                assert dashboard_config["dashboard_enabled_communities"] is True
                assert dashboard_config["dashboard_enabled_global"] is True
                assert dashboard_config["client_cache_compression_enabled"] is False
                assert dashboard_config["compress_json"] is True
                assert dashboard_config["display_binary_sizes"] is False  # Inverted
                assert dashboard_config["use_test_data"] is False
                assert dashboard_config["ui_subcounts"] == {}
                assert dashboard_config["default_range_options"] == [
                    {"value": "30days", "label": "Last 30 days"}
                ]

                # Verify disabled messages
                assert dashboard_config["disabled_message"] == (
                    "Community managers can enable the dashboard from settings"
                )
                assert "Test Site" in dashboard_config["disabled_message_global"]

                # Verify community and permissions are passed
                assert "community" in call_args[1]
                assert "permissions" in call_args[1]
                assert call_args[1]["permissions"]["can_read"] is True

    def test_community_dashboard_when_global_community_disabled(
        self,
        running_app: RunningApp,
        db,
        minimal_community_factory: Callable,
        set_app_config_fn_scoped: Callable,
    ) -> None:
        """Test community dashboard when global community dashboard is disabled."""
        app = running_app.app

        # Create a community with dashboard enabled
        community = minimal_community_factory(
            slug="test-community",
            custom_fields={"stats:dashboard_enabled": True},
        )

        # Set up temporary config with global community dashboard disabled
        set_app_config_fn_scoped({
            "STATS_DASHBOARD_ENABLED_COMMUNITY": False,
            "STATS_DASHBOARD_ENABLED_GLOBAL": True,
            "STATS_DASHBOARD_COMMUNITY_OPT_IN": True,
            "STATS_DASHBOARD_DISABLED_MESSAGE_COMMUNITY": "Community disabled",
            "STATS_DASHBOARD_DISABLED_MESSAGE_GLOBAL": "Global disabled",
            "THEME_SHORT_TITLE": "Test",
            "STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS": [],
            "STATS_DASHBOARD_LAYOUT": {
                "global_layout": {},
                "community_layout": {},
            },
            "STATS_DASHBOARD_UI_SUBCOUNTS": {},
            "STATS_DASHBOARD_UI_CONFIG": {"community": {}},
            "STATS_DASHBOARD_CLIENT_CACHE_COMPRESSION_ENABLED": False,
            "STATS_DASHBOARD_COMPRESS_JSON": True,
            "APP_RDM_DISPLAY_DECIMAL_FILE_SIZES": True,
            "STATS_DASHBOARD_USE_TEST_DATA": False,
        })

        community_route_template = app.config["STATS_DASHBOARD_ROUTES"]["community"]
        community_route = community_route_template.replace(
            "<pid_value>", str(community.id)
        )
        with app.test_request_context(
            path=community_route
        ) as req_ctx:
            g.identity = system_identity

            # Set request.view_args - Flask unpacks this as **kwargs when calling views
            req_ctx.request.view_args = {"pid_value": community.id}

            with patch(
                "invenio_stats_dashboard.views.views.render_template"
            ) as mock_render:
                mock_render.return_value = "rendered template"

                # Flask would call the view with **request.view_args unpacked
                community_stats_dashboard(**req_ctx.request.view_args)

                dashboard_config = mock_render.call_args[1]["dashboard_config"]
                # When dashboard_enabled_communities is False,
                # dashboard_enabled should be False
                assert dashboard_config["dashboard_enabled_communities"] is False
                assert dashboard_config["dashboard_enabled"] is False

    def test_community_dashboard_when_community_disabled_opt_in(
        self,
        running_app: RunningApp,
        db,
        minimal_community_factory: Callable,
        set_app_config_fn_scoped: Callable,
    ) -> None:
        """Test community dashboard when specific community is disabled (opt-in)."""
        app = running_app.app

        # Create a community with dashboard disabled (opt-in scenario)
        community = minimal_community_factory(
            slug="test-community",
            custom_fields={"stats:dashboard_enabled": False},
        )

        # Set up temporary config with opt-in enabled
        set_app_config_fn_scoped({
            "STATS_DASHBOARD_ENABLED_COMMUNITY": True,
            "STATS_DASHBOARD_ENABLED_GLOBAL": True,
            "STATS_DASHBOARD_COMMUNITY_OPT_IN": True,
            "STATS_DASHBOARD_DISABLED_MESSAGE_COMMUNITY": "Community disabled",
            "STATS_DASHBOARD_DISABLED_MESSAGE_GLOBAL": "Global disabled",
            "THEME_SHORT_TITLE": "Test",
            "STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS": [],
            "STATS_DASHBOARD_LAYOUT": {
                "global_layout": {},
                "community_layout": {},
            },
            "STATS_DASHBOARD_UI_SUBCOUNTS": {},
            "STATS_DASHBOARD_UI_CONFIG": {"community": {}},
            "STATS_DASHBOARD_CLIENT_CACHE_COMPRESSION_ENABLED": False,
            "STATS_DASHBOARD_COMPRESS_JSON": True,
            "APP_RDM_DISPLAY_DECIMAL_FILE_SIZES": True,
            "STATS_DASHBOARD_USE_TEST_DATA": False,
        })

        community_route_template = app.config["STATS_DASHBOARD_ROUTES"]["community"]
        community_route = community_route_template.replace(
            "<pid_value>", str(community.id)
        )
        with app.test_request_context(
            path=community_route
        ) as req_ctx:
            g.identity = system_identity

            # Set request.view_args - Flask unpacks this as **kwargs when calling views
            req_ctx.request.view_args = {"pid_value": community.id}

            with patch(
                "invenio_stats_dashboard.views.views.render_template"
            ) as mock_render:
                mock_render.return_value = "rendered template"

                # Flask would call the view with **request.view_args unpacked
                community_stats_dashboard(**req_ctx.request.view_args)

                dashboard_config = mock_render.call_args[1]["dashboard_config"]
                # When opt-in is True and community has dashboard_enabled=False,
                # dashboard_enabled should be False
                assert dashboard_config["dashboard_enabled_communities"] is True
                assert dashboard_config["dashboard_enabled"] is False

    def test_community_dashboard_when_opt_in_false(
        self,
        running_app: RunningApp,
        db,
        minimal_community_factory: Callable,
        set_app_config_fn_scoped: Callable,
    ) -> None:
        """Test community dashboard when opt-in is False (opt-out mode)."""
        app = running_app.app

        # Create a community without dashboard custom field (opt-out mode)
        community = minimal_community_factory(
            slug="test-community",
            custom_fields={},  # No dashboard_enabled field
        )

        # Set up temporary config with opt-in disabled (opt-out mode)
        set_app_config_fn_scoped({
            "STATS_DASHBOARD_ENABLED_COMMUNITY": True,
            "STATS_DASHBOARD_ENABLED_GLOBAL": True,
            "STATS_DASHBOARD_COMMUNITY_OPT_IN": False,  # Opt-out mode
            "STATS_DASHBOARD_DISABLED_MESSAGE_COMMUNITY": "Community disabled",
            "STATS_DASHBOARD_DISABLED_MESSAGE_GLOBAL": "Global disabled",
            "THEME_SHORT_TITLE": "Test",
            "STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS": [],
            "STATS_DASHBOARD_LAYOUT": {
                "global_layout": {},
                "community_layout": {},
            },
            "STATS_DASHBOARD_UI_SUBCOUNTS": {},
            "STATS_DASHBOARD_UI_CONFIG": {"community": {}},
            "STATS_DASHBOARD_CLIENT_CACHE_COMPRESSION_ENABLED": False,
            "STATS_DASHBOARD_COMPRESS_JSON": True,
            "APP_RDM_DISPLAY_DECIMAL_FILE_SIZES": True,
            "STATS_DASHBOARD_USE_TEST_DATA": False,
        })

        community_route_template = app.config["STATS_DASHBOARD_ROUTES"]["community"]
        community_route = community_route_template.replace(
            "<pid_value>", str(community.id)
        )
        with app.test_request_context(
            path=community_route
        ) as req_ctx:
            g.identity = system_identity

            # Set request.view_args - Flask unpacks this as **kwargs when calling views
            req_ctx.request.view_args = {"pid_value": community.id}

            with patch(
                "invenio_stats_dashboard.views.views.render_template"
            ) as mock_render:
                mock_render.return_value = "rendered template"

                # Flask would call the view with **request.view_args unpacked
                community_stats_dashboard(**req_ctx.request.view_args)

                dashboard_config = mock_render.call_args[1]["dashboard_config"]
                # In opt-out mode (opt_in=False),
                # missing custom field means enabled
                assert dashboard_config["dashboard_enabled_communities"] is True
                assert dashboard_config["dashboard_enabled"] is True

    def test_community_dashboard_permission_denied(
        self,
        running_app: RunningApp,
        db,
        minimal_community_factory: Callable,
        set_app_config_fn_scoped: Callable,
    ) -> None:
        """Test PermissionDeniedError when no read permission."""
        app = running_app.app

        # Create a community
        community = minimal_community_factory(
            slug="test-community",
            custom_fields={},
        )

        # Set up temporary config
        set_app_config_fn_scoped({
            "STATS_DASHBOARD_UI_CONFIG": {"community": {}},
        })

        community_route_template = app.config["STATS_DASHBOARD_ROUTES"]["community"]
        community_route = community_route_template.replace(
            "<pid_value>", str(community.id)
        )
        with app.test_request_context(
            path=community_route
        ) as req_ctx:
            g.identity = system_identity

            # Set request.view_args - Flask unpacks this as **kwargs when calling views
            req_ctx.request.view_args = {"pid_value": community.id}

            community_item = current_communities.service.read(
                system_identity, id_=community.id
            )

            # Mock has_permissions_to to deny read access
            community_item.has_permissions_to = lambda perms: {"can_read": False}

            # Mock service.read() to return the community with mocked permissions
            # This is needed because @pass_community decorator calls service.read()
            # which would create a new object without our mock
            with patch.object(
                current_communities.service,
                "read",
                return_value=community_item,
            ):
                with patch(
                    "invenio_stats_dashboard.views.views.render_template"
                ) as mock_render:
                    mock_render.return_value = "Template rendered"

                    with pytest.raises(PermissionDeniedError):
                        # Flask would call the view with **request.view_args unpacked
                        community_stats_dashboard(**req_ctx.request.view_args)

    def test_community_dashboard_csrf_cookie_reset(
        self,
        running_app: RunningApp,
        db,
        minimal_community_factory: Callable,
        set_app_config_fn_scoped: Callable,
    ) -> None:
        """Test that CSRF cookie is reset for community dashboard."""
        app = running_app.app

        # Create a community
        community = minimal_community_factory(
            slug="test-community",
            custom_fields={"stats:dashboard_enabled": True},
        )

        # Set up temporary config
        set_app_config_fn_scoped({
            "STATS_DASHBOARD_ENABLED_COMMUNITY": True,
            "STATS_DASHBOARD_ENABLED_GLOBAL": True,
            "STATS_DASHBOARD_COMMUNITY_OPT_IN": True,
            "STATS_DASHBOARD_DISABLED_MESSAGE_COMMUNITY": "Disabled",
            "STATS_DASHBOARD_DISABLED_MESSAGE_GLOBAL": "Global disabled",
            "THEME_SHORT_TITLE": "Test",
            "STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS": [],
            "STATS_DASHBOARD_LAYOUT": {
                "global_layout": {},
                "community_layout": {},
            },
            "STATS_DASHBOARD_UI_SUBCOUNTS": {},
            "STATS_DASHBOARD_UI_CONFIG": {"community": {}},
            "STATS_DASHBOARD_CLIENT_CACHE_COMPRESSION_ENABLED": False,
            "STATS_DASHBOARD_COMPRESS_JSON": True,
            "APP_RDM_DISPLAY_DECIMAL_FILE_SIZES": True,
            "STATS_DASHBOARD_USE_TEST_DATA": False,
        })

        community_route_template = app.config["STATS_DASHBOARD_ROUTES"]["community"]
        community_route = community_route_template.replace(
            "<pid_value>", str(community.id)
        )
        with app.test_request_context(
            path=community_route
        ) as req_ctx:
            g.identity = system_identity

            # Set request.view_args - Flask unpacks this as **kwargs when calling views
            req_ctx.request.view_args = {"pid_value": community.id}

            with patch(
                "invenio_stats_dashboard.views.views.render_template"
            ) as mock_render:
                mock_render.return_value = "rendered template"

                # Flask would call the view with **request.view_args unpacked
                community_stats_dashboard(**req_ctx.request.view_args)

                # Verify CSRF cookie reset is set
                assert hasattr(req_ctx.request, "csrf_cookie_needs_reset")
                assert req_ctx.request.csrf_cookie_needs_reset is True

    def test_community_dashboard_layout_from_custom_fields(
        self,
        running_app: RunningApp,
        db,
        minimal_community_factory: Callable,
        set_app_config_fn_scoped: Callable,
    ) -> None:
        """Test that community dashboard uses layout from custom fields."""
        app = running_app.app

        # Community with custom layout
        custom_layout = {
            "tabs": [
                {
                    "name": "custom-community-tab",
                    "label": "Custom Tab",
                    "rows": [
                        {
                            "name": "row1",
                            "components": [
                                {"component": "SingleStatRecordCount"}
                            ],
                        }
                    ],
                }
            ]
        }
        community = minimal_community_factory(
            slug="test-community",
            custom_fields={
                "stats:dashboard_enabled": True,
                "stats:dashboard_layout": {"community_layout": custom_layout},
            },
        )

        # Set up temporary config
        set_app_config_fn_scoped({
            "STATS_DASHBOARD_ENABLED_COMMUNITY": True,
            "STATS_DASHBOARD_ENABLED_GLOBAL": True,
            "STATS_DASHBOARD_COMMUNITY_OPT_IN": True,
            "STATS_DASHBOARD_DISABLED_MESSAGE_COMMUNITY": "Disabled",
            "STATS_DASHBOARD_DISABLED_MESSAGE_GLOBAL": "Global disabled",
            "THEME_SHORT_TITLE": "Test",
            "STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS": [],
            "STATS_DASHBOARD_LAYOUT": {
                "global_layout": {
                    "tabs": [
                        {
                            "name": "global",
                            "label": "Global",
                            "rows": [
                                {
                                    "name": "row1",
                                    "components": [
                                        {"component": "SingleStatRecordCount"}
                                    ],
                                }
                            ],
                        }
                    ]
                },
                "community_layout": {
                    "tabs": [
                        {
                            "name": "default-community",
                            "label": "Default Community",
                            "rows": [
                                {
                                    "name": "row1",
                                    "components": [
                                        {"component": "SingleStatRecordCount"}
                                    ],
                                }
                            ],
                        }
                    ]
                },
            },
            "STATS_DASHBOARD_UI_SUBCOUNTS": {},
            "STATS_DASHBOARD_UI_CONFIG": {"community": {}},
            "STATS_DASHBOARD_CLIENT_CACHE_COMPRESSION_ENABLED": False,
            "STATS_DASHBOARD_COMPRESS_JSON": True,
            "APP_RDM_DISPLAY_DECIMAL_FILE_SIZES": True,
            "STATS_DASHBOARD_USE_TEST_DATA": False,
        })

        community_route_template = app.config["STATS_DASHBOARD_ROUTES"]["community"]
        community_route = community_route_template.replace(
            "<pid_value>", str(community.id)
        )
        with app.test_request_context(
            path=community_route
        ) as req_ctx:
            g.identity = system_identity

            # Set request.view_args - Flask unpacks this as **kwargs when calling views
            req_ctx.request.view_args = {"pid_value": community.id}

            with patch(
                "invenio_stats_dashboard.views.views.render_template"
            ) as mock_render:
                mock_render.return_value = "rendered template"

                # Flask would call the view with **request.view_args unpacked
                community_stats_dashboard(**req_ctx.request.view_args)

                dashboard_config = mock_render.call_args[1]["dashboard_config"]
                # Should use custom layout from community custom fields
                assert dashboard_config["layout"] == custom_layout
                assert (
                    dashboard_config["layout"]["tabs"][0]["name"]
                    == "custom-community-tab"
                )

    def test_community_dashboard_agg_in_progress_flag(
        self,
        running_app: RunningApp,
        db,
        minimal_community_factory: Callable,
        set_app_config_fn_scoped: Callable,
        anon_identity,
    ) -> None:
        """Test that agg_in_progress flag is True when aggregation operations exist."""
        app = running_app.app

        # Create a community
        community = minimal_community_factory(
            slug="test-community",
            custom_fields={"stats:dashboard_enabled": True},
        )

        # Set up temporary config
        set_app_config_fn_scoped({
            "STATS_DASHBOARD_ENABLED_COMMUNITY": True,
            "STATS_DASHBOARD_ENABLED_GLOBAL": True,
            "STATS_DASHBOARD_COMMUNITY_OPT_IN": True,
            "STATS_DASHBOARD_DISABLED_MESSAGE_COMMUNITY": "Disabled",
            "STATS_DASHBOARD_DISABLED_MESSAGE_GLOBAL": "Global disabled",
            "THEME_SHORT_TITLE": "Test",
            "STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS": [],
            "STATS_DASHBOARD_LAYOUT": {
                "global_layout": {},
                "community_layout": {},
            },
            "STATS_DASHBOARD_UI_SUBCOUNTS": {},
            "STATS_DASHBOARD_UI_CONFIG": {"community": {}},
            "STATS_DASHBOARD_CLIENT_CACHE_COMPRESSION_ENABLED": False,
            "STATS_DASHBOARD_COMPRESS_JSON": True,
            "APP_RDM_DISPLAY_DECIMAL_FILE_SIZES": True,
            "STATS_DASHBOARD_USE_TEST_DATA": False,
        })

        # Set up registry with an active aggregation operation
        registry = StatsAggregationRegistry()
        agg_key = registry.make_registry_key(
            str(community.id), RegistryOperation.AGG
        )
        registry.set(agg_key, "2024-01-01T12:00:00.000", ttl=7200)

        community_route_template = app.config["STATS_DASHBOARD_ROUTES"]["community"]
        community_route = community_route_template.replace(
            "<pid_value>", str(community.id)
        )
        with app.test_request_context(
            path=community_route
        ):
            g.identity = anon_identity

            with patch(
                "invenio_stats_dashboard.views.views.render_template"
            ) as mock_render:
                mock_render.return_value = "rendered template"

                # Call view directly with pid_value - decorator fetches community
                community_stats_dashboard(pid_value=community.id)

                dashboard_config = mock_render.call_args[1]["dashboard_config"]
                # Should be True when aggregation operation exists
                assert dashboard_config["agg_in_progress"] is True

        # Clean up
        registry.delete(agg_key)

    def test_community_dashboard_agg_in_progress_flag_when_no_operations(
        self,
        running_app: RunningApp,
        db,
        minimal_community_factory: Callable,
        set_app_config_fn_scoped: Callable,
        anon_identity,
    ) -> None:
        """Test agg_in_progress flag is False when no aggregation operations exist."""
        app = running_app.app

        # Create a community
        community = minimal_community_factory(
            slug="test-community",
            custom_fields={"stats:dashboard_enabled": True},
        )

        # Set up temporary config
        set_app_config_fn_scoped({
            "STATS_DASHBOARD_ENABLED_COMMUNITY": True,
            "STATS_DASHBOARD_ENABLED_GLOBAL": True,
            "STATS_DASHBOARD_COMMUNITY_OPT_IN": True,
            "STATS_DASHBOARD_DISABLED_MESSAGE_COMMUNITY": "Disabled",
            "STATS_DASHBOARD_DISABLED_MESSAGE_GLOBAL": "Global disabled",
            "THEME_SHORT_TITLE": "Test",
            "STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS": [],
            "STATS_DASHBOARD_LAYOUT": {
                "global_layout": {},
                "community_layout": {},
            },
            "STATS_DASHBOARD_UI_SUBCOUNTS": {},
            "STATS_DASHBOARD_UI_CONFIG": {"community": {}},
            "STATS_DASHBOARD_CLIENT_CACHE_COMPRESSION_ENABLED": False,
            "STATS_DASHBOARD_COMPRESS_JSON": True,
            "APP_RDM_DISPLAY_DECIMAL_FILE_SIZES": True,
            "STATS_DASHBOARD_USE_TEST_DATA": False,
        })

        community_route_template = app.config["STATS_DASHBOARD_ROUTES"]["community"]
        community_route = community_route_template.replace(
            "<pid_value>", str(community.id)
        )
        with app.test_request_context(
            path=community_route
        ):
            g.identity = anon_identity

            with patch(
                "invenio_stats_dashboard.views.views.render_template"
            ) as mock_render:
                mock_render.return_value = "rendered template"

                # Call view directly - decorator will handle fetching community
                community_stats_dashboard(pid_value=community.id)

                dashboard_config = mock_render.call_args[1]["dashboard_config"]
                # Should be False when no aggregation operations exist
                assert dashboard_config["agg_in_progress"] is False

    def test_community_dashboard_caching_in_progress_flag(
        self,
        running_app: RunningApp,
        db,
        minimal_community_factory: Callable,
        set_app_config_fn_scoped: Callable,
        anon_identity,
    ) -> None:
        """Test that caching_in_progress flag is True when cache operations exist."""
        app = running_app.app

        # Create a community
        community = minimal_community_factory(
            slug="test-community",
            custom_fields={"stats:dashboard_enabled": True},
        )

        # Set up temporary config
        set_app_config_fn_scoped({
            "STATS_DASHBOARD_ENABLED_COMMUNITY": True,
            "STATS_DASHBOARD_ENABLED_GLOBAL": True,
            "STATS_DASHBOARD_COMMUNITY_OPT_IN": True,
            "STATS_DASHBOARD_DISABLED_MESSAGE_COMMUNITY": "Disabled",
            "STATS_DASHBOARD_DISABLED_MESSAGE_GLOBAL": "Global disabled",
            "THEME_SHORT_TITLE": "Test",
            "STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS": [],
            "STATS_DASHBOARD_LAYOUT": {
                "global_layout": {},
                "community_layout": {},
            },
            "STATS_DASHBOARD_UI_SUBCOUNTS": {},
            "STATS_DASHBOARD_UI_CONFIG": {"community": {}},
            "STATS_DASHBOARD_CLIENT_CACHE_COMPRESSION_ENABLED": False,
            "STATS_DASHBOARD_COMPRESS_JSON": True,
            "APP_RDM_DISPLAY_DECIMAL_FILE_SIZES": True,
            "STATS_DASHBOARD_USE_TEST_DATA": False,
        })

        # Set up registry with an active cache operation (with year suffix)
        registry = StatsAggregationRegistry()
        current_year = 2024
        cache_operation = RegistryOperation.CACHE.replace("{year}", str(current_year))
        cache_key = registry.make_registry_key(
            str(community.id), cache_operation
        )
        registry.set(cache_key, "2024-01-01T12:00:00.000", ttl=7200)

        community_route_template = app.config["STATS_DASHBOARD_ROUTES"]["community"]
        community_route = community_route_template.replace(
            "<pid_value>", str(community.id)
        )
        with app.test_request_context(
            path=community_route
        ):
            g.identity = anon_identity

            with patch(
                "invenio_stats_dashboard.views.views.render_template"
            ) as mock_render:
                mock_render.return_value = "rendered template"

                # Call view directly - decorator fetches community
                community_stats_dashboard(pid_value=community.id)

                dashboard_config = mock_render.call_args[1]["dashboard_config"]
                # Should be True when cache operation exists
                assert dashboard_config["caching_in_progress"] is True

        # Clean up
        registry.delete(cache_key)

    def test_community_dashboard_caching_in_progress_flag_when_no_operations(
        self,
        running_app: RunningApp,
        db,
        minimal_community_factory: Callable,
        set_app_config_fn_scoped: Callable,
        anon_identity,
    ) -> None:
        """Test caching_in_progress flag is False when no cache operations exist."""
        app = running_app.app

        # Create a community
        community = minimal_community_factory(
            slug="test-community",
            custom_fields={"stats:dashboard_enabled": True},
        )

        # Set up temporary config
        set_app_config_fn_scoped({
            "STATS_DASHBOARD_ENABLED_COMMUNITY": True,
            "STATS_DASHBOARD_ENABLED_GLOBAL": True,
            "STATS_DASHBOARD_COMMUNITY_OPT_IN": True,
            "STATS_DASHBOARD_DISABLED_MESSAGE_COMMUNITY": "Disabled",
            "STATS_DASHBOARD_DISABLED_MESSAGE_GLOBAL": "Global disabled",
            "THEME_SHORT_TITLE": "Test",
            "STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS": [],
            "STATS_DASHBOARD_LAYOUT": {
                "global_layout": {},
                "community_layout": {},
            },
            "STATS_DASHBOARD_UI_SUBCOUNTS": {},
            "STATS_DASHBOARD_UI_CONFIG": {"community": {}},
            "STATS_DASHBOARD_CLIENT_CACHE_COMPRESSION_ENABLED": False,
            "STATS_DASHBOARD_COMPRESS_JSON": True,
            "APP_RDM_DISPLAY_DECIMAL_FILE_SIZES": True,
            "STATS_DASHBOARD_USE_TEST_DATA": False,
        })

        community_route_template = app.config["STATS_DASHBOARD_ROUTES"]["community"]
        community_route = community_route_template.replace(
            "<pid_value>", str(community.id)
        )
        with app.test_request_context(
            path=community_route
        ):
            g.identity = anon_identity

            with patch(
                "invenio_stats_dashboard.views.views.render_template"
            ) as mock_render:
                mock_render.return_value = "rendered template"

                # Call view directly - decorator fetches community
                community_stats_dashboard(pid_value=community.id)

                dashboard_config = mock_render.call_args[1]["dashboard_config"]
                # Should be False when no cache operations exist
                assert dashboard_config["caching_in_progress"] is False

    def test_community_dashboard_first_run_incomplete_when_no_records(
        self,
        running_app: RunningApp,
        db,
        minimal_community_factory: Callable,
        set_app_config_fn_scoped: Callable,
        anon_identity,
    ) -> None:
        """Test first_run_incomplete flag is True when no first_run records exist."""
        app = running_app.app

        # Create a community
        community = minimal_community_factory(
            slug="test-community",
            custom_fields={"stats:dashboard_enabled": True},
        )

        # Set up temporary config
        set_app_config_fn_scoped({
            "STATS_DASHBOARD_ENABLED_COMMUNITY": True,
            "STATS_DASHBOARD_ENABLED_GLOBAL": True,
            "STATS_DASHBOARD_COMMUNITY_OPT_IN": True,
            "STATS_DASHBOARD_DISABLED_MESSAGE_COMMUNITY": "Disabled",
            "STATS_DASHBOARD_DISABLED_MESSAGE_GLOBAL": "Global disabled",
            "THEME_SHORT_TITLE": "Test",
            "STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS": [],
            "STATS_DASHBOARD_LAYOUT": {
                "global_layout": {},
                "community_layout": {},
            },
            "STATS_DASHBOARD_UI_SUBCOUNTS": {},
            "STATS_DASHBOARD_UI_CONFIG": {"community": {}},
            "STATS_DASHBOARD_CLIENT_CACHE_COMPRESSION_ENABLED": False,
            "STATS_DASHBOARD_COMPRESS_JSON": True,
            "APP_RDM_DISPLAY_DECIMAL_FILE_SIZES": True,
            "STATS_DASHBOARD_USE_TEST_DATA": False,
        })

        # No first_run records set up - registry should be empty

        community_route_template = app.config["STATS_DASHBOARD_ROUTES"]["community"]
        community_route = community_route_template.replace(
            "<pid_value>", str(community.id)
        )
        with app.test_request_context(
            path=community_route
        ):
            g.identity = anon_identity

            with patch(
                "invenio_stats_dashboard.views.views.render_template"
            ) as mock_render:
                mock_render.return_value = "rendered template"

                # Call view directly - decorator fetches community
                community_stats_dashboard(pid_value=community.id)

                dashboard_config = mock_render.call_args[1]["dashboard_config"]
                # Should be True when no first_run records exist
                assert dashboard_config["first_run_incomplete"] is True

    def test_community_dashboard_first_run_incomplete_when_in_progress(
        self,
        running_app: RunningApp,
        db,
        minimal_community_factory: Callable,
        set_app_config_fn_scoped: Callable,
        anon_identity,
    ) -> None:
        """Test first_run_incomplete flag is True when first_run is IN_PROGRESS."""
        app = running_app.app

        # Create a community
        community = minimal_community_factory(
            slug="test-community",
            custom_fields={"stats:dashboard_enabled": True},
        )

        # Set up temporary config
        set_app_config_fn_scoped({
            "STATS_DASHBOARD_ENABLED_COMMUNITY": True,
            "STATS_DASHBOARD_ENABLED_GLOBAL": True,
            "STATS_DASHBOARD_COMMUNITY_OPT_IN": True,
            "STATS_DASHBOARD_DISABLED_MESSAGE_COMMUNITY": "Disabled",
            "STATS_DASHBOARD_DISABLED_MESSAGE_GLOBAL": "Global disabled",
            "THEME_SHORT_TITLE": "Test",
            "STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS": [],
            "STATS_DASHBOARD_LAYOUT": {
                "global_layout": {},
                "community_layout": {},
            },
            "STATS_DASHBOARD_UI_SUBCOUNTS": {},
            "STATS_DASHBOARD_UI_CONFIG": {"community": {}},
            "STATS_DASHBOARD_CLIENT_CACHE_COMPRESSION_ENABLED": False,
            "STATS_DASHBOARD_COMPRESS_JSON": True,
            "APP_RDM_DISPLAY_DECIMAL_FILE_SIZES": True,
            "STATS_DASHBOARD_USE_TEST_DATA": False,
        })

        # Set up registry with first_run in IN_PROGRESS status
        registry = StatsAggregationRegistry()
        first_run_key = registry.make_registry_key(
            str(community.id), RegistryOperation.FIRST_RUN
        )
        # Store as string - Redis will encode it automatically
        registry.set(
            first_run_key,
            FirstRunStatus.IN_PROGRESS,
            ttl=None,
        )

        community_route_template = app.config["STATS_DASHBOARD_ROUTES"]["community"]
        community_route = community_route_template.replace(
            "<pid_value>", str(community.id)
        )
        with app.test_request_context(
            path=community_route
        ):
            g.identity = anon_identity

            with patch(
                "invenio_stats_dashboard.views.views.render_template"
            ) as mock_render:
                mock_render.return_value = "rendered template"

                # Call view directly - decorator fetches community
                community_stats_dashboard(pid_value=community.id)

                dashboard_config = mock_render.call_args[1]["dashboard_config"]
                # Should be True when first_run is IN_PROGRESS
                assert dashboard_config["first_run_incomplete"] is True

        # Clean up
        registry.delete(first_run_key)

    def test_community_dashboard_first_run_complete_when_completed(
        self,
        running_app: RunningApp,
        db,
        minimal_community_factory: Callable,
        set_app_config_fn_scoped: Callable,
        anon_identity,
    ) -> None:
        """Test first_run_incomplete flag is False when first_run is COMPLETED."""
        app = running_app.app

        # Create a community
        community = minimal_community_factory(
            slug="test-community",
            custom_fields={"stats:dashboard_enabled": True},
        )

        # Set up temporary config
        set_app_config_fn_scoped({
            "STATS_DASHBOARD_ENABLED_COMMUNITY": True,
            "STATS_DASHBOARD_ENABLED_GLOBAL": True,
            "STATS_DASHBOARD_COMMUNITY_OPT_IN": True,
            "STATS_DASHBOARD_DISABLED_MESSAGE_COMMUNITY": "Disabled",
            "STATS_DASHBOARD_DISABLED_MESSAGE_GLOBAL": "Global disabled",
            "THEME_SHORT_TITLE": "Test",
            "STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS": [],
            "STATS_DASHBOARD_LAYOUT": {
                "global_layout": {},
                "community_layout": {},
            },
            "STATS_DASHBOARD_UI_SUBCOUNTS": {},
            "STATS_DASHBOARD_UI_CONFIG": {"community": {}},
            "STATS_DASHBOARD_CLIENT_CACHE_COMPRESSION_ENABLED": False,
            "STATS_DASHBOARD_COMPRESS_JSON": True,
            "APP_RDM_DISPLAY_DECIMAL_FILE_SIZES": True,
            "STATS_DASHBOARD_USE_TEST_DATA": False,
        })

        # Set up registry with first_run in COMPLETED status
        registry = StatsAggregationRegistry()
        first_run_key = registry.make_registry_key(
            str(community.id), RegistryOperation.FIRST_RUN
        )
        # Store as string - Redis will encode it automatically
        registry.set(
            first_run_key,
            FirstRunStatus.COMPLETED,
            ttl=None,
        )

        community_route_template = app.config["STATS_DASHBOARD_ROUTES"]["community"]
        community_route = community_route_template.replace(
            "<pid_value>", str(community.id)
        )
        with app.test_request_context(
            path=community_route
        ):
            g.identity = anon_identity

            with patch(
                "invenio_stats_dashboard.views.views.render_template"
            ) as mock_render:
                mock_render.return_value = "rendered template"

                # Call view directly - decorator fetches community
                community_stats_dashboard(pid_value=community.id)

                dashboard_config = mock_render.call_args[1]["dashboard_config"]
                # Should be False when first_run is COMPLETED
                assert dashboard_config["first_run_incomplete"] is False

        # Clean up
        registry.delete(first_run_key)
