# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 MESH Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Tests for custom fields functionality."""

from collections.abc import Callable
from typing import Any

import pytest
from invenio_communities.proxies import current_communities
from invenio_records_resources.services.custom_fields import BooleanCF
from invenio_records_resources.services.custom_fields.validate import (
    validate_custom_fields,
)
from invenio_search import current_search_client
from invenio_search.engine import dsl
from invenio_search.utils import build_alias_name
from marshmallow.exceptions import ValidationError

from invenio_stats_dashboard.records.communities.custom_fields.custom_fields import (
    COMMUNITIES_NAMESPACES,
    COMMUNITY_STATS_FIELDS,
    COMMUNITY_STATS_FIELDS_UI,
    DashboardLayoutCF,
    DashboardLayoutSchema,
)
from tests.conftest import RunningApp


class TestDashboardLayoutSchema:
    """Test the DashboardLayoutSchema validation."""

    def test_valid_global_config(self):
        """Test valid global configuration."""
        valid_data: dict[str, Any] = {
            "global_layout": {
                "tabs": [
                    {
                        "name": "Overview",
                        "label": "Overview Tab",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {
                                        "component": "SingleStatRecordCount",
                                        "props": {
                                            "title": "Downloads",
                                            "chart_type": "line",
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        }

        schema = DashboardLayoutSchema()
        result = schema.load(valid_data)
        assert result["global_layout"]["tabs"][0]["name"] == "Overview"
        assert (
            result["global_layout"]["tabs"][0]["rows"][0]["components"][0]["component"]
            == "SingleStatRecordCount"
        )

    def test_valid_community_config(self):
        """Test valid community configuration."""
        valid_data = {
            "community_layout": {
                "tabs": [
                    {
                        "name": "Community Stats",
                        "label": "Community Stats Tab",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {
                                        "component": "SingleStatUploaders",
                                        "props": {
                                            "title": "Total Records",
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

        schema = DashboardLayoutSchema()
        result = schema.load(valid_data)
        assert result["community_layout"]["tabs"][0]["name"] == "Community Stats"

    def test_valid_both_configs(self):
        """Test valid configuration with both global and community."""
        valid_data = {
            "global_layout": {
                "tabs": [
                    {
                        "name": "Global Overview",
                        "label": "Global Overview Tab",
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
                        "name": "Community Stats",
                        "label": "Community Stats Tab",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {
                                        "component": "SingleStatUploaders",
                                        "props": {"title": "Community Records"},
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
        }

        schema = DashboardLayoutSchema()
        result = schema.load(valid_data)
        assert "global_layout" in result
        assert "community_layout" in result

    def test_empty_config(self):
        """Test empty configuration."""
        valid_data: dict[str, Any] = {}

        schema = DashboardLayoutSchema()
        result = schema.load(valid_data)
        assert result == {}

    def test_invalid_tab_structure(self):
        """Test invalid tab structure."""
        invalid_data = {
            "global_layout": {
                "tabs": [
                    {
                        "name": "Test Tab",
                        "label": "Test Tab Label",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {
                                        # Missing required 'component' field
                                        "props": {}
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        }

        schema = DashboardLayoutSchema()
        with pytest.raises(ValidationError):
            schema.load(invalid_data)

    def test_missing_required_fields(self):
        """Test missing required fields."""
        invalid_data = {
            "global_layout": {
                "tabs": [
                    {
                        "label": "Test Tab",  # Missing 'name' field for tab
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {"component": "SingleStatRecordCount", "props": {}}
                                ],
                            }
                        ],
                    }
                ]
            }
        }

        schema = DashboardLayoutSchema()
        with pytest.raises(ValidationError):
            schema.load(invalid_data)

    def test_unknown_fields_excluded(self):
        """Test that unknown fields are excluded."""
        data_with_unknown = {
            "global_layout": {
                "tabs": [
                    {
                        "name": "Test Tab",
                        "label": "Test Tab Label",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {
                                        "component": "SingleStatRecordCount",
                                        "props": {"title": "Test Chart"},
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
            "unknown_field": "should be excluded",
        }

        schema = DashboardLayoutSchema()
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data_with_unknown)

        assert exc_info.value.messages == {"unknown_field": ["Unknown field."]}


class TestDashboardLayoutCF:
    """Test the DashboardLayoutCF custom field."""

    def test_field_property(self):
        """Test the field property returns correct Marshmallow field."""
        cf = DashboardLayoutCF(name="stats:dashboard_layout")
        field = cf.field

        assert hasattr(field, "schema")
        assert field.schema.__class__ == DashboardLayoutSchema

    def test_mapping_property(self):
        """Test the mapping property returns correct Elasticsearch mapping."""
        cf = DashboardLayoutCF(name="stats:dashboard_layout")
        mapping = cf.mapping

        assert mapping["type"] == "object"
        assert mapping["enabled"] is False

    def test_field_name(self):
        """Test the field name is correctly set."""
        cf = DashboardLayoutCF(name="stats:dashboard_layout")
        assert cf.name == "stats:dashboard_layout"


class TestCustomFieldsConfiguration:
    """Test the custom fields configuration."""

    def test_community_stats_fields_defined(self):
        """Test that community stats fields are properly defined."""
        assert len(COMMUNITY_STATS_FIELDS) == 2
        assert isinstance(COMMUNITY_STATS_FIELDS[0], BooleanCF)
        assert isinstance(COMMUNITY_STATS_FIELDS[1], DashboardLayoutCF)
        assert COMMUNITY_STATS_FIELDS[0].name == "stats:dashboard_enabled"
        assert COMMUNITY_STATS_FIELDS[1].name == "stats:dashboard_layout"

    def test_community_stats_fields_ui_defined(self):
        """Test that community stats fields UI is properly defined."""
        ui_config = COMMUNITY_STATS_FIELDS_UI()  # Call to get the config dict
        assert isinstance(ui_config, dict)
        assert ui_config["section"] == "Stats Dashboard Settings"
        assert len(ui_config["fields"]) > 0
        assert ui_config["fields"][0]["field"] == "stats:dashboard_enabled"

    def test_communities_namespaces_defined(self):
        """Test that communities namespaces are properly defined."""
        assert "stats" in COMMUNITIES_NAMESPACES
        assert COMMUNITIES_NAMESPACES["stats"] is None


class TestCustomFieldsIntegration:
    """Test custom fields integration with InvenioRDM."""

    def test_custom_fields_validation(self, app):
        """Test that custom fields configuration is valid."""
        available_fields = app.config.get("COMMUNITIES_CUSTOM_FIELDS", [])
        namespaces = set(app.config.get("COMMUNITIES_NAMESPACES", {}).keys())

        # This should not raise an exception
        validate_custom_fields(
            given_fields=None,
            available_fields=available_fields,
            namespaces=namespaces,
        )

    def test_opensearch_mapping_creation(
        self,
        running_app: RunningApp,
        search_clear: Callable,
        create_communities_custom_fields: Callable,
    ) -> None:
        """Test that OpenSearch mapping is created correctly."""
        # The create_communities_custom_fields fixture creates the custom field mapping
        # The search_clear and running_app fixtures handle the index setup
        communities_index = dsl.Index(
            build_alias_name(current_communities.service.config.record_cls.index._name),
            using=current_search_client,
        )

        mapping = communities_index.get_mapping()
        # Get the actual index name from the mapping (not the alias)
        index_name = list(mapping.keys())[0]
        properties = mapping[index_name]["mappings"]["properties"]

        assert "custom_fields" in properties
        assert "properties" in properties["custom_fields"]
        assert "stats:dashboard_layout" in properties["custom_fields"]["properties"]

        dashboard_layout_mapping = properties["custom_fields"]["properties"][
            "stats:dashboard_layout"
        ]
        assert dashboard_layout_mapping["type"] == "object"
        assert dashboard_layout_mapping["enabled"] is False

        assert "stats:dashboard_enabled" in properties["custom_fields"]["properties"]

        dashboard_enabled_mapping = properties["custom_fields"]["properties"][
            "stats:dashboard_enabled"
        ]
        assert dashboard_enabled_mapping["type"] == "boolean"

    def test_community_without_custom_field(
        self,
        running_app: RunningApp,
        minimal_community_factory: Callable,
        set_app_config_fn_scoped: Callable,
    ) -> None:
        """Test creating a community without the custom field.

        The field with a default value should still be created.
        """
        set_app_config_fn_scoped({"STATS_DASHBOARD_COMMUNITY_OPT_IN": True})
        community = minimal_community_factory(slug="test-community")

        assert (
            "stats:dashboard_layout" not in community._record.custom_fields
            or not community._record.custom_fields.get("stats:dashboard_layout")
        )
        assert "stats:dashboard_enabled" in community._record.custom_fields
        assert community._record.custom_fields["stats:dashboard_enabled"] is False

    def test_custom_field_data_persistence(
        self, running_app: RunningApp, minimal_community_factory: Callable
    ) -> None:
        """Test that custom field data persists correctly."""
        original_data = {
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
                                        "props": {
                                            "title": "Downloads",
                                            "chart_type": "line",
                                        },
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
                        "name": "Community Stats",
                        "label": "Community Stats Label",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {
                                        "component": "SingleStatUploaders",
                                        "props": {
                                            "title": "Total Records",
                                            "icon": "users",
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
        }

        custom_fields_data = {"stats:dashboard_layout": original_data}

        community = minimal_community_factory(
            slug="test-community", custom_fields=custom_fields_data
        )

        # Serialize and deserialize
        serialized = community.to_dict()

        # Verify the data structure is preserved
        deserialized_data = serialized["custom_fields"]["stats:dashboard_layout"]
        assert (
            deserialized_data["global_layout"]["tabs"][0]["name"] == "Global Overview"
        )
        assert (
            deserialized_data["community_layout"]["tabs"][0]["name"]
            == "Community Stats"
        )
        assert (
            deserialized_data["global_layout"]["tabs"][0]["rows"][0]["components"][0][
                "props"
            ]["title"]
            == "Downloads"
        )
        assert (
            deserialized_data["community_layout"]["tabs"][0]["rows"][0]["components"][
                0
            ]["props"]["icon"]
            == "users"
        )
