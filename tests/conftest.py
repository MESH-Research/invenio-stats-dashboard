# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025-2026 MESH Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Top-level pytest configuration for Invenio-Stats-Dashboard tests.

Shared `app_config` from `kcworks-test-fixtures` supplies the common baseline;
this conftest only wraps it for package-specific keys and template paths.
"""

from pathlib import Path

import pytest
from invenio_app.factory import create_app as _create_app

from tests.fixtures.app import RunningApp  # noqa: F401 — re-export for tests

pytest_plugins = (
    "celery.contrib.pytest",
    "tests.fixtures.app",
    "tests.fixtures.app_config",
    "tests.fixtures.bootstrap",
    "tests.fixtures.caching",
    "tests.fixtures.celery",
    "tests.fixtures.cli",
    "tests.fixtures.communities",
    "tests.fixtures.community_events",
    "tests.fixtures.custom_fields",
    "tests.fixtures.files",
    "tests.fixtures.fixtures",
    "tests.fixtures.frontend",
    "tests.fixtures.identifiers",
    "tests.fixtures.indexer_queues",
    "tests.fixtures.logging",
    "tests.fixtures.mail",
    "tests.fixtures.records",
    "tests.fixtures.roles",
    "tests.fixtures.search",
    "tests.fixtures.search_provisioning",
    "tests.fixtures.stats",
    "tests.fixtures.uow",
    "tests.fixtures.users",
    "tests.fixtures.vocabularies.affiliations",
    "tests.fixtures.vocabularies.community_types",
    "tests.fixtures.vocabularies.date_types",
    "tests.fixtures.vocabularies.descriptions",
    "tests.fixtures.vocabularies.funding_and_awards",
    "tests.fixtures.vocabularies.languages",
    "tests.fixtures.vocabularies.licenses",
    "tests.fixtures.vocabularies.resource_types",
    "tests.fixtures.vocabularies.roles",
    "tests.fixtures.vocabularies.subjects",
    "tests.fixtures.vocabularies.title_types",
    "tests.pytest_plugins.pytest_live_status",
)


@pytest.fixture(scope="session")
def template_loader_paths() -> list[Path]:
    """Stats-dashboard template directories for the shared `template_loader`.

    Returns:
        list[Path]: Ordered template directories for Jinja.
    """
    test_root = Path(__file__).parent
    package_root = test_root.parent
    return [
        test_root / "helpers" / "templates" / "semantic-ui",
        package_root / "invenio_stats_dashboard" / "templates" / "semantic-ui",
    ]


@pytest.fixture(scope="module")
def app_config(app_config) -> dict:
    """Add stats-dashboard package keys onto the shared test defaults.

    Returns:
        dict: The layered Flask/Invenio application config.
    """
    app_config["COMMUNITY_STATS_ENABLED"] = True
    app_config["COMMUNITY_STATS_SCHEDULED_AGG_TASKS_ENABLED"] = True
    app_config["COMMUNITY_STATS_SCHEDULED_CACHE_TASKS_ENABLED"] = True
    # Disable optimization by default so all metrics are included; individual
    # tests can enable it explicitly when needed.
    app_config["STATS_DASHBOARD_OPTIMIZE_DATA_SERIES"] = False
    app_config["STATS_DASHBOARD_COMMUNITY_OPT_IN"] = False
    return app_config


@pytest.fixture(scope="module")
def create_app(instance_path, entry_points):
    """Provide the application factory used to build the Flask app.

    Returns:
        Callable: The application factory function.
    """
    return _create_app
