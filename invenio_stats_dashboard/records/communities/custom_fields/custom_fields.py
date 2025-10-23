"""Custom fields for community records."""

from invenio_i18n import lazy_gettext as _
from invenio_records_resources.services.custom_fields import BaseCF
from marshmallow import INCLUDE, RAISE, Schema, fields, validate

COMMUNITIES_NAMESPACES = {"stats": None}


class ComponentPropsSchema(Schema):
    """Schema for component props - flexible dict for component-specific properties."""

    class Meta:  # noqa: D106
        unknown = INCLUDE  # Allow any additional props

    # Basic display props
    title = fields.Str(allow_none=True)
    icon = fields.Str(allow_none=True)

    # Layout and sizing props (used in dashboard config)
    width = fields.Int(allow_none=True, validate=validate.Range(min=1, max=16))
    height = fields.Int(allow_none=True, validate=validate.Range(min=100, max=2000))
    minHeight = fields.Int(allow_none=True, validate=validate.Range(min=100, max=2000))
    maxHeight = fields.Str(allow_none=True)  # Can be string like "300px" or number

    # Chart props (passed through to StatsChart)
    chartType = fields.Str(allow_none=True, validate=validate.OneOf(["bar", "line"]))
    maxSeries = fields.Int(allow_none=True, validate=validate.Range(min=1, max=50))
    display_subcounts = fields.Dict(allow_none=True)

    # Multi-display props (passed through to StatsMultiDisplay)
    pageSize = fields.Int(allow_none=True, validate=validate.Range(min=1, max=100))
    default_view = fields.Str(
        allow_none=True, validate=validate.OneOf(["pie", "bar", "list", "table"])
    )
    available_views = fields.List(
        fields.Str(validate=validate.OneOf(["pie", "bar", "list", "table"])),
        allow_none=True,
    )
    hideOtherInCharts = fields.Bool(allow_none=True)

    # Map props (StatsMap specific)
    zoom = fields.Int(allow_none=True, validate=validate.Range(min=1, max=20))
    center = fields.List(fields.Float(), allow_none=True)
    metric = fields.Str(
        allow_none=True,
        validate=validate.OneOf(["views", "downloads", "visitors", "dataVolume"]),
    )
    useSnapshot = fields.Bool(allow_none=True)

    # Single stat props (passed through to SingleStatBox)
    compactThreshold = fields.Int(allow_none=True, validate=validate.Range(min=1))


class ComponentSchema(Schema):
    """Schema for individual dashboard components."""

    component = fields.Str(required=True, validate=validate.Length(min=1))
    width = fields.Int(allow_none=True, validate=validate.Range(min=1, max=16))
    props = fields.Nested(ComponentPropsSchema, allow_none=True)


class RowSchema(Schema):
    """Schema for dashboard rows."""

    name = fields.Str(required=True, validate=validate.Length(min=1))
    components = fields.List(
        fields.Nested(ComponentSchema),
        required=True,
        validate=validate.Length(min=1),
        error_messages={"required": "Row must have at least one component"},
    )


class TabSchema(Schema):
    """Schema for dashboard tabs."""

    name = fields.Str(required=True, validate=validate.Length(min=1))
    label = fields.Str(required=True, validate=validate.Length(min=1))
    icon = fields.Str(allow_none=True)
    date_range_phrase = fields.Str(allow_none=True)
    rows = fields.List(
        fields.Nested(RowSchema),
        required=True,
        validate=validate.Length(min=1),
        error_messages={"required": "Tab must have at least one row"},
    )


class DashboardTypeSchema(Schema):
    """Schema for dashboard type configuration (global/community)."""

    tabs = fields.List(
        fields.Nested(TabSchema),
        required=True,
        validate=validate.Length(min=1),
        error_messages={"required": "Dashboard must have at least one tab"},
    )


class DashboardLayoutSchema(Schema):
    """Schema for the complete dashboard layout configuration."""

    global_layout = fields.Nested(DashboardTypeSchema, allow_none=True)
    community_layout = fields.Nested(DashboardTypeSchema, allow_none=True)

    class Meta:  # noqa: D106
        unknown = RAISE  # Only allow defined fields


class DashboardLayoutCF(BaseCF):
    """Dashboard layout custom field for community records."""

    @property
    def field(self):
        """Dashboard layout field definition."""
        return fields.Nested(DashboardLayoutSchema)

    @property
    def mapping(self):
        """Dashboard layout search mappings."""
        return {
            "type": "object",
            "enabled": False,  # Content not indexed, but field existence is trackable
        }


COMMUNITY_STATS_FIELDS = [
    DashboardLayoutCF(name="stats:dashboard_layout"),
]

COMMUNITY_STATS_FIELDS_UI = {
    "section": _("Stats Dashboard Settings"),
    "fields": [
        {
            "field": "stats:dashboard_layout",
            "ui_widget": "DashboardLayoutField",
            "template": "dashboard_layout_field.html",
            "props": {
                "label": _("Dashboard Layout Configuration"),
                "placeholder": _("Enter dashboard layout configuration as JSON"),
                "description": _(
                    "JSON configuration for community-specific dashboard layout"
                ),
                "icon": "chart pie",
            },
        }
    ],
}
