from flask import current_app
from werkzeug.local import LocalProxy

current_community_stats = LocalProxy(
    lambda: current_app.extensions["invenio-stats-dashboard"]
)
current_community_stats_service = LocalProxy(
    lambda: current_app.extensions["invenio-stats-dashboard"].service
)
