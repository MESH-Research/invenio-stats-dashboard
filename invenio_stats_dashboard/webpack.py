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
            },
            dependencies={},
            aliases={},
        )
    },
)
