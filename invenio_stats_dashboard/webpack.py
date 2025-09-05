"""Webpack configuration for Invenio Stats Dashboard."""

from invenio_assets.webpack import WebpackThemeBundle

theme = WebpackThemeBundle(
    __name__,
    "assets",
    default="semantic-ui",
    themes={
        "semantic-ui": dict(
            entry={
                "invenio-stats-dashboard": "./js/invenio_stats_dashboard/index.js",
                "invenio-stats-dashboard-css": (
                    "./less/invenio_stats_dashboard/stats_dashboard.less"
                ),
            },
            dependencies={
                "echarts": "^5.4.2",
                "echarts-for-react": "^3.0.2",
                "pako": "^2.1.0",
            },
            aliases={
                "@js/invenio_stats_dashboard": "js/invenio_stats_dashboard",
                "@translations/invenio_stats_dashboard": (
                    "translations/invenio_stats_dashboard"
                ),
            },
        )
    },
)
