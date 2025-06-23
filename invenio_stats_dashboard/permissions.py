"""Permissions for the stats dashboard."""

AllowAllPermission = type(
    "Allow",
    (),
    {"can": lambda self: True, "allows": lambda *args: True},
)()


def CommunityStatsPermissionFactory(obj_id, action):
    """Permission factory for the stats dashboard."""
    # FIXME: restrict this permission to authorized users with the proper role
    return AllowAllPermission
