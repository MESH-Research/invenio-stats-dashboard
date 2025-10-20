# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Permissions for the stats dashboard."""

AllowAllPermission = type(
    "Allow",
    (),
    {"can": lambda self: True, "allows": lambda *args: True},
)()


def CommunityStatsPermissionFactory(obj_id, action):
    """Permission factory for the stats dashboard.
    
    Returns:
        AllowAllPermission: Permission object allowing all access.
    """
    # FIXME: restrict this permission to authorized users with the proper role
    return AllowAllPermission
