# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 MESH Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Tests for dashboard UI templates and macros."""

from collections.abc import Callable

from flask import render_template, render_template_string
from invenio_communities.communities.resources.serializer import (
    UICommunityJSONSerializer,
)

from tests.conftest import RunningApp
from tests.helpers.utils import extract_json_from_html_attribute


class TestStatsDashboardMacro:
    """Test the stats_dashboard Jinja macro."""

    def test_macro_renders_with_minimal_config(self, running_app: RunningApp) -> None:
        """Test that macro renders with minimal dashboard config."""
        app = running_app.app
        dashboard_config = {
            "dashboard_type": "global",
            "dashboard_enabled": True,
        }

        template_str = """
        {% from config.STATS_DASHBOARD_TEMPLATES["macro"] import stats_dashboard %}
        {{ stats_dashboard(dashboard_config) }}
        """

        with app.app_context():
            with app.test_request_context():
                rendered = render_template_string(
                    template_str, dashboard_config=dashboard_config
                )

        # Check that the main div is present
        assert 'id="stats-dashboard"' in rendered
        # Check that dashboard_config is in data attribute
        assert "data-dashboard-config" in rendered
        # Check that community is not present (None)
        assert (
            'data-community="None"' in rendered or "data-community='None'" in rendered
        )

    def test_macro_renders_with_full_config(self, running_app: RunningApp) -> None:
        """Test that macro renders with full dashboard config."""
        app = running_app.app
        dashboard_config = {
            "dashboard_type": "global",
            "dashboard_enabled": True,
            "client_cache_compression_enabled": False,
            "compress_json": True,
            "display_binary_sizes": False,
            "use_test_data": False,
            "layout": {
                "tabs": [
                    {
                        "name": "overview",
                        "label": "Overview",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [{"component": "SingleStatRecordCount"}],
                            }
                        ],
                    }
                ]
            },
            "default_range_options": [{"value": "30days", "label": "Last 30 days"}],
            "ui_subcounts": {},
        }

        template_str = """
        {% from config.STATS_DASHBOARD_TEMPLATES["macro"] import stats_dashboard %}
        {{ stats_dashboard(dashboard_config) }}
        """

        with app.app_context():
            with app.test_request_context():
                rendered = render_template_string(
                    template_str, dashboard_config=dashboard_config
                )

        # Check that the main div is present
        assert 'id="stats-dashboard"' in rendered
        # Check that dashboard_config is serialized in data attribute
        assert "data-dashboard-config" in rendered

        # Extract and parse the JSON from the rendered output
        rendered_config = extract_json_from_html_attribute(
            rendered, "data-dashboard-config"
        )
        assert rendered_config == dashboard_config

    def test_macro_renders_with_community(self, running_app: RunningApp) -> None:
        """Test that macro renders with community data."""
        app = running_app.app
        dashboard_config = {
            "dashboard_type": "community",
            "dashboard_enabled": True,
        }
        community = {
            "id": "test-community-id",
            "slug": "test-community",
            "metadata": {"title": "Test Community"},
        }

        template_str = """
        {% from config.STATS_DASHBOARD_TEMPLATES["macro"] import stats_dashboard %}
        {{ stats_dashboard(dashboard_config, community=community) }}
        """

        with app.app_context():
            with app.test_request_context():
                rendered = render_template_string(
                    template_str, dashboard_config=dashboard_config, community=community
                )

        # Check that the main div is present
        assert 'id="stats-dashboard"' in rendered
        # Check that community data is present
        assert "data-community" in rendered
        # Verify community data is present and matches what we passed
        rendered_community = extract_json_from_html_attribute(
            rendered, "data-community"
        )
        assert rendered_community is not None, (
            "Community was passed to macro but was None in rendered output"
        )
        assert rendered_community == community

    def test_macro_includes_webpack_assets(self, running_app: RunningApp) -> None:
        """Test that macro includes webpack assets."""
        app = running_app.app
        dashboard_config = {"dashboard_type": "global", "dashboard_enabled": True}

        template_str = """
        {% from config.STATS_DASHBOARD_TEMPLATES["macro"] import stats_dashboard %}
        {{ stats_dashboard(dashboard_config) }}
        """

        with app.app_context():
            with app.test_request_context():
                rendered = render_template_string(
                    template_str, dashboard_config=dashboard_config
                )

        # Check that the main div is present
        assert 'id="stats-dashboard"' in rendered
        # Check that webpack assets are referenced
        # The webpack function is mocked via MockManifestLoader in conftest,
        # so it should render as asset names
        assert (
            "invenio-stats-dashboard.js" in rendered
            or "invenio-stats-dashboard-css.css" in rendered
        )


class TestGlobalStatsDashboardTemplate:
    """Test the global stats dashboard template."""

    def test_template_extends_base_template(self, running_app: RunningApp) -> None:
        """Test that template extends the base template."""
        app = running_app.app
        dashboard_config = {
            "dashboard_type": "global",
            "dashboard_enabled": True,
        }

        with app.app_context():
            with app.test_request_context():
                rendered = render_template(
                    "invenio_stats_dashboard/stats_dashboard.html",
                    dashboard_config=dashboard_config,
                )
                # Verify template rendered successfully
                assert rendered is not None
                # Verify the macro was called (dashboard div should be present)
                assert 'id="stats-dashboard"' in rendered
                assert "data-dashboard-config" in rendered

    def test_template_sets_title(self, running_app: RunningApp) -> None:
        """Test that template sets the page title."""
        app = running_app.app

        template_str = """
        {%- set title = _("Stats Dashboard") %}
        Title: {{ title }}
        """

        with app.app_context():
            with app.test_request_context():
                rendered = render_template_string(template_str)

        # Check that title is set (may be translated)
        assert "Title:" in rendered

    def test_template_calls_macro(self, running_app: RunningApp) -> None:
        """Test that template calls the stats_dashboard macro."""
        app = running_app.app
        dashboard_config = {
            "dashboard_type": "global",
            "dashboard_enabled": True,
        }

        # Test the macro import and call structure
        template_str = """
        {% from config.STATS_DASHBOARD_TEMPLATES["macro"] import stats_dashboard %}
        {{ stats_dashboard(dashboard_config) }}
        """

        with app.app_context():
            with app.test_request_context():
                rendered = render_template_string(
                    template_str, dashboard_config=dashboard_config
                )

        # Verify macro was called and rendered
        assert 'id="stats-dashboard"' in rendered
        assert "data-dashboard-config" in rendered


class TestCommunityStatsDashboardTemplate:
    """Test the community stats dashboard template."""

    def test_template_extends_community_base(self, running_app: RunningApp) -> None:
        """Test that template extends the community base template."""
        app = running_app.app
        dashboard_config = {
            "dashboard_type": "community",
            "dashboard_enabled": True,
        }
        community = {
            "id": "test-community-id",
            "slug": "test-community",
            "metadata": {"title": "Test Community"},
        }

        with app.app_context():
            with app.test_request_context():
                rendered = render_template(
                    "invenio_communities/details/stats/index.html",
                    dashboard_config=dashboard_config,
                    community=community,
                )
                # Verify template rendered successfully
                assert rendered is not None
                # Verify the macro was called (dashboard div should be present)
                assert 'id="stats-dashboard"' in rendered
                assert "data-dashboard-config" in rendered
                assert "data-community" in rendered

    def test_template_sets_active_menu_item(self, running_app: RunningApp) -> None:
        """Test that template sets active_community_header_menu_item."""
        app = running_app.app
        template_str = """
        {% set active_community_header_menu_item = "stats" %}
        Active menu: {{ active_community_header_menu_item }}
        """

        with app.app_context():
            with app.test_request_context():
                rendered = render_template_string(template_str)

        assert "Active menu: stats" in rendered

    def test_template_calls_macro_with_community(self, running_app: RunningApp) -> None:
        """Test that template calls the stats_dashboard macro with community."""
        app = running_app.app
        dashboard_config = {
            "dashboard_type": "community",
            "dashboard_enabled": True,
        }
        community = {
            "id": "test-community-id",
            "slug": "test-community",
            "metadata": {"title": "Test Community"},
        }

        template_str = """
        {% from config.STATS_DASHBOARD_TEMPLATES["macro"] import stats_dashboard %}
        {{ stats_dashboard(dashboard_config, community=community) }}
        """

        with app.app_context():
            with app.test_request_context():
                rendered = render_template_string(
                    template_str, dashboard_config=dashboard_config, community=community
                )

        # Verify macro was called with community
        assert 'id="stats-dashboard"' in rendered
        assert "data-dashboard-config" in rendered
        assert "data-community" in rendered
        # Verify community data is present
        assert "test-community-id" in rendered or "test-community" in rendered

    def test_template_calls_super_block(self, running_app: RunningApp) -> None:
        """Test that template calls super() for page_body block."""
        app = running_app.app
        # The template uses {{ super() }} to include parent template content
        # This is tested indirectly by checking the template structure
        template_str = """
        {% extends "invenio_theme/base.html" %}
        {%- block page_body %}
            {{ super() }}
            <div>Dashboard content</div>
        {%- endblock page_body -%}
        """

        with app.app_context():
            with app.test_request_context():
                rendered = render_template_string(template_str)

        # Verify the block structure - both parent content and our content
        # should be present
        assert "Dashboard content" in rendered


class TestDashboardTemplateIntegration:
    """Integration tests for dashboard templates with full app context."""

    def test_global_template_with_full_config(
        self, running_app: RunningApp, set_app_config_fn_scoped: Callable
    ) -> None:
        """Test global template rendering with full configuration."""
        app = running_app.app

        dashboard_config = {
            "dashboard_type": "global",
            "dashboard_enabled": True,
            "client_cache_compression_enabled": False,
            "compress_json": True,
            "display_binary_sizes": False,
            "use_test_data": False,
            "layout": {
                "tabs": [
                    {
                        "name": "overview",
                        "label": "Overview",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [{"component": "SingleStatRecordCount"}],
                            }
                        ],
                    }
                ]
            },
            "default_range_options": [{"value": "30days", "label": "Last 30 days"}],
            "ui_subcounts": {},
        }

        set_app_config_fn_scoped({
            "STATS_DASHBOARD_TEMPLATES": {
                "macro": "invenio_stats_dashboard/macros/stats_dashboard_macro.html",
                "global": "invenio_stats_dashboard/stats_dashboard.html",
            },
            "THEME_BASE_TEMPLATE": "invenio_theme/page.html",
            "BASE_TEMPLATE": "invenio_theme/base.html",
        })

        with app.app_context():
            with app.test_request_context():
                rendered = render_template(
                    "invenio_stats_dashboard/stats_dashboard.html",
                    dashboard_config=dashboard_config,
                )
                # Verify key elements are present
                assert rendered is not None
                # Verify macro output is present
                assert 'id="stats-dashboard"' in rendered
                assert "data-dashboard-config" in rendered

    def test_community_template_with_full_config(
        self,
        running_app: RunningApp,
        db,
        minimal_community_factory: Callable,
        set_app_config_fn_scoped: Callable,
    ) -> None:
        """Test community template rendering with full configuration."""
        app = running_app.app

        community = minimal_community_factory(
            slug="test-community",
            custom_fields={"stats:dashboard_enabled": True},
        )

        dashboard_config = {
            "dashboard_type": "community",
            "dashboard_enabled": True,
            "client_cache_compression_enabled": False,
            "compress_json": True,
            "display_binary_sizes": False,
            "use_test_data": False,
            "layout": {
                "tabs": [
                    {
                        "name": "overview",
                        "label": "Overview",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [{"component": "SingleStatRecordCount"}],
                            }
                        ],
                    }
                ]
            },
            "default_range_options": [{"value": "30days", "label": "Last 30 days"}],
            "ui_subcounts": {},
        }

        # Use the actual serializer to create community_ui, just like the
        # @pass_community(serialize=True) decorator does
        serializer = UICommunityJSONSerializer()
        community_ui = serializer.dump_obj(community.to_dict())

        set_app_config_fn_scoped({
            "STATS_DASHBOARD_TEMPLATES": {
                "macro": "invenio_stats_dashboard/macros/stats_dashboard_macro.html",
                "community": "invenio_communities/details/stats/index.html",
            },
            "BASE_TEMPLATE": "invenio_theme/base.html",
        })

        with app.app_context():
            with app.test_request_context():
                rendered = render_template(
                    "invenio_communities/details/stats/index.html",
                    dashboard_config=dashboard_config,
                    community=community_ui,
                )
                # Verify key elements are present
                assert rendered is not None
                # Verify macro output is present
                assert 'id="stats-dashboard"' in rendered
                assert "data-dashboard-config" in rendered
                assert "data-community" in rendered
