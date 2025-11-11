# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 MESH Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Top-level pytest configuration for Invenio-Stats-Dashboard tests."""

import os
import shutil
import tempfile
from collections import namedtuple
from pathlib import Path

import jinja2
import pytest
from invenio_app.factory import create_app as _create_app
from invenio_files_rest.models import Location
from invenio_queues import current_queues
from invenio_search.proxies import current_search_client

from .fixtures.custom_fields import test_config_fields
from .fixtures.frontend import MockManifestLoader
from .fixtures.identifiers import test_config_identifiers
from .fixtures.stats import test_config_stats

pytest_plugins = (
    "celery.contrib.pytest",
    "tests.fixtures.files",
    "tests.fixtures.fixtures",
    "tests.fixtures.mail",
    "tests.fixtures.communities",
    "tests.fixtures.custom_fields",
    "tests.fixtures.records",
    "tests.fixtures.roles",
    "tests.fixtures.stats",
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
)


def _(x):
    """Identity function for string extraction."""
    return x


test_config = {
    **test_config_identifiers,
    **test_config_fields,
    **test_config_stats,
    "SQLALCHEMY_DATABASE_URI": (
        "postgresql+psycopg2://invenio:invenio@localhost:5432/invenio"
    ),
    "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    "SEARCH_INDEX_PREFIX": "",
    "POSTGRES_USER": "invenio",
    "POSTGRES_PASSWORD": "invenio",
    "POSTGRES_DB": "invenio",
    "WTF_CSRF_ENABLED": False,
    "WTF_CSRF_METHODS": [],
    "RATELIMIT_ENABLED": False,
    "APP_DEFAULT_SECURE_HEADERS": {
        "content_security_policy": {"default-src": []},
        "force_https": False,
    },
    "BROKER_URL": "amqp://guest:guest@localhost:5672//",
    "CELERY_TASK_ALWAYS_EAGER": False,
    "CELERY_TASK_EAGER_PROPAGATES_EXCEPTIONS": True,
    "CELERY_LOGLEVEL": "DEBUG",
    "INVENIO_INSTANCE_PATH": "/opt/invenio/var/instance",
    "MAIL_SUPPRESS_SEND": False,
    "MAIL_SERVER": "smtp.sparkpostmail.com",
    "MAIL_PORT": 587,
    "MAIL_USE_TLS": True,
    "MAIL_USE_SSL": False,
    "MAIL_USERNAME": os.getenv("SPARKPOST_USERNAME"),
    "MAIL_PASSWORD": os.getenv("SPARKPOST_API_KEY"),
    "MAIL_DEFAULT_SENDER": os.getenv("INVENIO_ADMIN_EMAIL"),
    "SECRET_KEY": "test-secret-key",
    "SECURITY_PASSWORD_SALT": "test-secret-key",
    "WEBPACKEXT_MANIFEST_LOADER": MockManifestLoader,
    "TESTING": True,
    "DEBUG": True,
    "COMMUNITY_STATS_ENABLED": True,
    "COMMUNITY_STATS_SCHEDULED_AGG_TASKS_ENABLED": True,
    "COMMUNITY_STATS_SCHEDULED_CACHE_TASKS_ENABLED": True,
    # Disable optimization by default in tests so all metrics are included
    # Individual tests can enable optimization explicitly if needed
    "STATS_DASHBOARD_OPTIMIZE_DATA_SERIES": False,
}

parent_path = Path(__file__).parent
log_folder_path = parent_path / "test_logs"
log_file_path = log_folder_path / "invenio.log"
if not log_file_path.exists():
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    log_file_path.touch()

test_config["LOGGING_FS_LEVEL"] = "DEBUG"
test_config["LOGGING_FS_LOGFILE"] = str(log_file_path)
test_config["LOGGING_CONSOLE_LEVEL"] = "DEBUG"
test_config["CELERY_LOGFILE"] = str(log_folder_path / "celery.log")

# enable DataCite DOI provider
test_config["DATACITE_ENABLED"] = True
test_config["DATACITE_USERNAME"] = "INVALID"
test_config["DATACITE_PASSWORD"] = "INVALID"
test_config["DATACITE_DATACENTER_SYMBOL"] = "TEST"
test_config["DATACITE_PREFIX"] = "10.17613"
test_config["DATACITE_TEST_MODE"] = True
# ...but fake it

test_config["SITE_API_URL"] = os.environ.get(
    "INVENIO_SITE_API_URL", "https://127.0.0.1:5000/api"
)
test_config["SITE_UI_URL"] = os.environ.get(
    "INVENIO_SITE_UI_URL", "https://127.0.0.1:5000"
)


@pytest.fixture(scope="session")
def celery_config(celery_config):
    """Celery config fixture for Invenio-Stats-Dashboard."""
    celery_config["logfile"] = str(log_folder_path / "celery.log")
    celery_config["loglevel"] = "DEBUG"
    celery_config["task_always_eager"] = True
    celery_config["cache_backend"] = "memory"
    celery_config["result_backend"] = "cache"
    celery_config["task_eager_propagates_exceptions"] = True

    return celery_config


@pytest.fixture(scope="session")
def celery_enable_logging():
    """Celery enable logging fixture."""
    return True


@pytest.yield_fixture(scope="module")
def location(database):
    """Creates a simple default location for a test.

    Use this fixture if your test requires a `files location <https://invenio-
    files-rest.readthedocs.io/en/latest/api.html#invenio_files_rest.models.
    Location>`_. The location will be a default location with the name
    ``pytest-location``.
    """
    uri = tempfile.mkdtemp()
    location_obj = Location(name="pytest-location", uri=uri, default=True)

    database.session.add(location_obj)
    database.session.commit()

    yield location_obj

    shutil.rmtree(uri)


# This is a namedtuple that holds all the fixtures we're likely to need
# in a single test.
RunningApp = namedtuple(
    "RunningApp",
    [
        "app",
        "location",
        "cache",
        "affiliations_v",
        "awards_v",
        "community_type_v",
        "contributors_role_v",
        "creators_role_v",
        "date_type_v",
        "description_type_v",
        "funders_v",
        "language_v",
        "licenses_v",
        # "relation_type_v",
        "resource_type_v",
        "subject_v",
        "title_type_v",
        "create_communities_custom_fields",
        "create_records_custom_fields",
    ],
)


@pytest.fixture(scope="function")
def running_app(
    app,
    location,
    cache,
    affiliations_v,
    awards_v,
    community_type_v,
    contributors_role_v,
    creators_role_v,
    date_type_v,
    description_type_v,
    funders_v,
    language_v,
    licenses_v,
    # relation_type_v,
    resource_type_v,
    subject_v,
    title_type_v,
    create_communities_custom_fields,
    create_records_custom_fields,
):
    """This fixture provides an app with the typically needed db data loaded.

    All of these fixtures are often needed together, so collecting them
    under a semantic umbrella makes sense.
    """
    return RunningApp(
        app,
        location,
        cache,
        affiliations_v,
        awards_v,
        community_type_v,
        contributors_role_v,
        creators_role_v,
        date_type_v,
        description_type_v,
        funders_v,
        language_v,
        licenses_v,
        # relation_type_v,
        resource_type_v,
        subject_v,
        title_type_v,
        create_communities_custom_fields,
        create_records_custom_fields,
    )


@pytest.fixture(scope="function")
def search_clear(search_clear):
    """Clear search indices after test finishes (function scope).

    the search_clear fixture should each time start by running
    ```python
    current_search.create()
    current_search.put_templates()
    ```
    and then clear the indices during the fixture teardown. But
    this doesn't catch the stats indices, so we need to add an
    additional step to delete the stats indices and template manually.
    Otherwise, the stats indices aren't cleared between tests.
    """
    # Clear identity cache before each test to prevent stale community role data
    from invenio_communities.proxies import current_identities_cache

    current_identities_cache.flush()

    yield search_clear

    # Delete stats indices and templates if they exist
    # Without this we get data pollution between tests
    current_search_client.indices.delete("*stats*", ignore=[404])
    current_search_client.indices.delete_template("*stats*", ignore=[404])


@pytest.fixture(scope="module")
def template_loader():
    """Fixture providing overloaded and custom templates to test app."""

    def load_tempates(app):
        """Load templates for the test app."""
        theme_path = (
            Path(__file__).parent.parent
            / "invenio_stats_dashboard"
            / "templates"
            / "semantic-ui"
        )
        root_path = (
            Path(__file__).parent.parent / "invenio_stats_dashboard" / "templates"
        )
        test_path = Path(__file__).parent / "helpers" / "templates" / "semantic-ui"
        for path in (
            theme_path,
            root_path,
            test_path,
        ):
            assert path.exists()
        custom_loader = jinja2.ChoiceLoader([
            app.jinja_loader,
            jinja2.FileSystemLoader([str(theme_path), str(root_path), str(test_path)]),
        ])
        app.jinja_loader = custom_loader
        app.jinja_env.loader = custom_loader

    return load_tempates


@pytest.fixture(scope="module")
def app(
    app,
    app_config,
    database,
    search,
    template_loader,
    admin_roles,
):
    """This fixture provides an app with the typically needed basic fixtures.

    This fixture should be used in conjunction with the `running_app`
    fixture to provide a complete app with all the typically needed
    fixtures. This fixture sets up the basic functions like db, search,
    and template loader once per modules. The `running_app` fixture is function
    scoped and initializes all the fixtures that should be reset between tests.
    """
    current_queues.declare()
    template_loader(app)
    yield app


@pytest.fixture(scope="module")
def app_config(app_config) -> dict:
    """App config fixture."""
    for k, v in test_config.items():
        app_config[k] = v

    return app_config


@pytest.fixture(scope="module")
def create_app(instance_path, entry_points):
    """Create the app fixture.

    This initializes the basic Flask app which will then be used
    to set up the `app` fixture with initialized services.
    """
    return _create_app
