# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.
#
# This file is adapted from the invenio-rdm-records package:
# Copyright (C) 2019-2025 CERN.
# Copyright (C) 2019-2022 Northwestern University.
# Copyright (C) 2021 TU Wien.
# Copyright (C) 2022-2023 Graz University of Technology.
# Invenio-RDM-Records is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Roles related pytest fixtures for testing."""

import pytest
from invenio_accounts.proxies import current_accounts


@pytest.fixture(scope="module")
def admin_roles():
    """Fixture to create admin roles."""
    current_accounts.datastore.create_role(name="admin-moderator")
    current_accounts.datastore.create_role(name="administration")
    current_accounts.datastore.create_role(name="administration-moderation")
