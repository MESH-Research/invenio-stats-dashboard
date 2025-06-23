from invenio_records_resources.services.custom_fields import BaseListCF
from marshmallow import fields
from marshmallow_utils.fields import SanitizedUnicode


class CommunityEventsCF(BaseListCF):
    """Community events custom field."""

    def __init__(self, name, **kwargs):
        """Constructor."""
        super().__init__(
            name,
            field_cls=fields.Nested,
            field_args={
                "nested": {
                    "community_id": SanitizedUnicode(),
                    "added": SanitizedUnicode(),
                    "removed": SanitizedUnicode(),
                },
            },
            multiple=True,
            **kwargs,
        )

    @property
    def mapping(self):
        """Notes search mappings."""
        return {
            "type": "nested",
            "properties": {
                "community_id": {"type": "keyword"},
                "added": {"type": "date"},
                "removed": {"type": "date"},
            },
        }


STATS_NAMESPACE = {"stats": ""}

COMMUNITY_EVENTS_FIELDS = [CommunityEventsCF(name="stats:community_events")]
