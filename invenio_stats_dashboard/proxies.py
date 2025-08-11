from flask import current_app
from werkzeug.local import LocalProxy


def _get_community_stats_service():
    """Get the community stats service, checking if it's enabled."""
    extension = current_app.extensions.get("invenio-stats-dashboard")
    if extension is None:
        raise RuntimeError("Invenio Stats Dashboard extension not initialized")

    service = extension.service
    if service is None:
        raise RuntimeError(
            "Community stats service is disabled. "
            "Set COMMUNITY_STATS_ENABLED=True to enable this feature."
        )
    return service


def _get_event_reindexing_service():
    """Get the event reindexing service, checking if it's enabled."""
    extension = current_app.extensions.get("invenio-stats-dashboard")
    if extension is None:
        raise RuntimeError("Invenio Stats Dashboard extension not initialized")

    service = extension.event_reindexing_service
    if service is None:
        raise RuntimeError(
            "Event reindexing service is disabled. "
            "Set COMMUNITY_STATS_ENABLED=True to enable this feature."
        )
    return service


current_community_stats = LocalProxy(
    lambda: current_app.extensions["invenio-stats-dashboard"]
)
current_community_stats_service = LocalProxy(_get_community_stats_service)
current_event_reindexing_service = LocalProxy(_get_event_reindexing_service)
