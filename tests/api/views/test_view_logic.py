# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 MESH Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Tests for view logic that accesses custom field data."""

from unittest.mock import Mock

from flask import Flask
from invenio_communities.communities.services.results import CommunityItem

from invenio_stats_dashboard.views.views import get_community_dashboard_layout


class TestGetCommunityDashboardLayout:
    """Test the get_community_dashboard_layout function."""

    def test_with_community_specific_config(self, app: Flask) -> None:
        """Test getting layout with community-specific configuration."""
        # Mock community with custom field data
        community_mock = Mock(spec=CommunityItem)
        community_mock.id = "test-community-id"
        community_mock.data = {
            "custom_fields": {
                "stats:dashboard_layout": {
                    "community_layout": {
                        "tabs": [
                            {
                                "name": "Community Custom Tab",
                                "label": "Community Custom Tab Label",
                                "rows": [
                                    {
                                        "name": "row1",
                                        "components": [
                                            {
                                                "component": "SingleStatRecordCount",
                                                "props": {"title": "Community Chart"},
                                            }
                                        ],
                                    }
                                ],
                            }
                        ]
                    }
                }
            }
        }
        # Add _record attribute for fallback access
        community_mock._record = Mock()
        community_mock._record.custom_fields = {}

        # Mock app config
        app.config["STATS_DASHBOARD_LAYOUT"] = {
            "global_layout": {
                "tabs": [
                    {
                        "name": "Global Tab",
                        "label": "Global Tab Label",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {
                                        "component": "SingleStatRecordCount",
                                        "props": {"title": "Global Chart"},
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

        with app.app_context():
            result = get_community_dashboard_layout(community_mock, "community")

            # Should return community-specific config
            assert result["tabs"][0]["name"] == "Community Custom Tab"
            test_component = result["tabs"][0]["rows"][0]["components"][0]
            assert test_component["props"]["title"] == "Community Chart"

    def test_without_community_specific_config(self, app: Flask) -> None:
        """Test getting layout without community-specific configuration."""
        # Mock community without custom field data
        community_mock = Mock(spec=CommunityItem)
        community_mock.id = "test-community-id"
        community_mock.data = {"custom_fields": {}}
        # Add _record attribute for fallback access
        community_mock._record = Mock()
        community_mock._record.custom_fields = {}

        # Mock app config
        app.config["STATS_DASHBOARD_LAYOUT"] = {
            "global_layout": {
                "tabs": [
                    {
                        "name": "Global Tab",
                        "label": "Global Tab Label",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {
                                        "component": "SingleStatRecordCount",
                                        "props": {"title": "Global Chart"},
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

        with app.app_context():
            result = get_community_dashboard_layout(community_mock, "community")

            # Should return default community config
            assert result["tabs"][0]["name"] == "Default Community Tab"
            assert (
                result["tabs"][0]["rows"][0]["components"][0]["props"]["title"]
                == "Default Community Chart"
            )

    def test_fallback_to_global_config(self, app: Flask) -> None:
        """Test fallback to global config when community config is missing."""
        # Mock community with custom field data but no community-specific config
        community_mock = Mock(spec=CommunityItem)
        community_mock.id = "test-community-id"
        community_mock.data = {
            "custom_fields": {
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
                                                "props": {
                                                    "title": "Custom Global Chart"
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
        }
        # Add _record attribute for fallback access
        community_mock._record = Mock()
        community_mock._record.custom_fields = {}

        # Mock app config
        app.config["STATS_DASHBOARD_LAYOUT"] = {
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

        with app.app_context():
            result = get_community_dashboard_layout(community_mock, "community")

            # Should return default community config since no bespoke community config
            assert result["tabs"][0]["name"] == "Default Community Tab"
            assert (
                result["tabs"][0]["rows"][0]["components"][0]["props"]["title"]
                == "Default Community Chart"
            )

    def test_fallback_to_global_when_no_community_config(self, app: Flask) -> None:
        """Test fallback to global config when community_layout missing."""
        # Mock community without custom field data
        community_mock = Mock(spec=CommunityItem)
        community_mock.id = "test-community-id"
        community_mock.data = {"custom_fields": {}}
        # Add _record attribute for fallback access
        community_mock._record = Mock()
        community_mock._record.custom_fields = {}

        # Mock app config WITHOUT community_layout (only global_layout)
        app.config["STATS_DASHBOARD_LAYOUT"] = {
            "global_layout": {
                "tabs": [
                    {
                        "name": "Global Tab",
                        "label": "Global Tab Label",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {
                                        "component": "SingleStatRecordCount",
                                        "props": {"title": "Global Chart"},
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
            # Note: No "community_layout" key - this should trigger fallback to global
        }

        with app.app_context():
            result = get_community_dashboard_layout(community_mock, "community")

            # Should fallback to global config since no community_layout in app config
            assert result["tabs"][0]["name"] == "Global Tab"
            assert (
                result["tabs"][0]["rows"][0]["components"][0]["props"]["title"]
                == "Global Chart"
            )

    def test_empty_custom_fields_fallback(self, app: Flask) -> None:
        """Test fallback when custom_fields is empty."""
        # Mock community with empty custom fields
        community_mock = Mock(spec=CommunityItem)
        community_mock.id = "test-community-id"
        community_mock.data = {"custom_fields": {}}
        # Add _record attribute for fallback access
        community_mock._record = Mock()
        community_mock._record.custom_fields = {}

        # Mock app config
        app.config["STATS_DASHBOARD_LAYOUT"] = {
            "global_layout": {
                "tabs": [
                    {
                        "name": "Global Tab",
                        "label": "Global Tab Label",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {
                                        "component": "SingleStatRecordCount",
                                        "props": {"title": "Global Chart"},
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

        with app.app_context():
            result = get_community_dashboard_layout(community_mock, "community")

            # Should return default community config
            assert result["tabs"][0]["name"] == "Default Community Tab"

    def test_missing_custom_fields_key_fallback(self, app: Flask) -> None:
        """Test fallback when custom_fields key is missing."""
        # Mock community without custom_fields key
        community_mock = Mock(spec=CommunityItem)
        community_mock.id = "test-community-id"
        community_mock.data = {}
        # Add _record attribute for fallback access
        community_mock._record = Mock()
        community_mock._record.custom_fields = {}

        # Mock app config
        app.config["STATS_DASHBOARD_LAYOUT"] = {
            "global_layout": {
                "tabs": [
                    {
                        "name": "Global Tab",
                        "label": "Global Tab Label",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {
                                        "component": "SingleStatRecordCount",
                                        "props": {"title": "Global Chart"},
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

        with app.app_context():
            result = get_community_dashboard_layout(community_mock, "community")

            # Should return default community config
            assert result["tabs"][0]["name"] == "Default Community Tab"

    def test_record_fallback_when_data_missing(self, app: Flask) -> None:
        """Test fallback to underlying record when data is missing."""
        # Mock community with missing data but underlying record has custom fields
        community_mock = Mock(spec=CommunityItem)
        community_mock.id = "test-community-id"
        community_mock.data = {}  # No custom_fields in data

        # Mock underlying record with custom fields
        record_mock = Mock()
        record_mock.custom_fields = {
            "stats:dashboard_layout": {
                "community_layout": {
                    "tabs": [
                        {
                            "name": "Record Tab",
                            "label": "Record Tab Label",
                            "rows": [
                                {
                                    "name": "row1",
                                    "components": [
                                        {
                                            "component": "SingleStatRecordCount",
                                            "props": {"title": "Record Chart"},
                                        }
                                    ],
                                }
                            ],
                        }
                    ]
                }
            }
        }
        community_mock._record = record_mock

        # Mock app config
        app.config["STATS_DASHBOARD_LAYOUT"] = {
            "global_layout": {
                "tabs": [
                    {
                        "name": "Global Tab",
                        "label": "Global Tab Label",
                        "rows": [
                            {
                                "name": "row1",
                                "components": [
                                    {
                                        "component": "SingleStatRecordCount",
                                        "props": {"title": "Global Chart"},
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

        with app.app_context():
            result = get_community_dashboard_layout(community_mock, "community")

            # Should return record-based config
            assert result["tabs"][0]["name"] == "Record Tab"
            assert (
                result["tabs"][0]["rows"][0]["components"][0]["props"]["title"]
                == "Record Chart"
            )

    def test_global_dashboard_type(self, app: Flask) -> None:
        """Test getting layout for global dashboard type."""
        # Mock community with custom field data
        community_mock = Mock(spec=CommunityItem)
        community_mock.id = "test-community-id"
        community_mock.data = {
            "custom_fields": {
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
                                                "props": {
                                                    "title": "Custom Global Chart"
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
        }
        # Add _record attribute for fallback access
        community_mock._record = Mock()
        community_mock._record.custom_fields = {}

        # Mock app config
        app.config["STATS_DASHBOARD_LAYOUT"] = {
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
            }
        }

        with app.app_context():
            result = get_community_dashboard_layout(community_mock, "global")

            # Should return custom global config
            assert result["tabs"][0]["name"] == "Custom Global Tab"
            assert (
                result["tabs"][0]["rows"][0]["components"][0]["props"]["title"]
                == "Custom Global Chart"
            )
