# Configurable Event Enrichment

The EventReindexingService now supports configurable event enrichment based on the existing `COMMUNITY_STATS_SUBCOUNT_CONFIGS` in `config.py`. This allows administrators to control which fields are enriched during event reindexing by simply modifying the subcount configuration.

## How It Works

The enrichment process automatically uses the `COMMUNITY_STATS_SUBCOUNT_CONFIGS` to determine:

1. **Which fields to extract** from the metadata using `extraction_path_for_event`
2. **How to extract** metadata fields (dot-separated paths or lambda functions)
3. **Field mapping** from metadata to enriched event fields

## Architecture

### MetadataExtractor Class

The system uses a high-performance `MetadataExtractor` class that:

- **Pre-compiles extraction specs** using the `glom` library for maximum performance
- **Caches extracted values** by record ID to avoid redundant lookups
- **Supports both** dot-separated string paths and lambda functions
- **Handles errors gracefully** by setting failed extractions to `None`

### Performance Features

- **Pre-compiled glom specs** for string-based extraction paths
- **Record ID caching** to avoid repeated metadata extraction for the same record
- **Lazy instantiation** of the extractor to defer compilation costs
- **Bulk processing** optimized for large numbers of events

## Configuration

### Subcount Configuration Integration

The enrichment process automatically reads the `COMMUNITY_STATS_SUBCOUNT_CONFIGS` and only enriches fields that have `usage_events` configuration with `extraction_path_for_event`. Fields with `event_field: None` are skipped for enrichment but can still be used for statistics aggregation.

```python
COMMUNITY_STATS_SUBCOUNT_CONFIGS = {
    "by_subjects": {
        "usage_events": {
            "event_field": "subjects",
            "extraction_path_for_event": "metadata.subjects",
            "field_type": Optional[list[str]],
        }
    },
    "by_resource_types": {
        "usage_events": {
            "event_field": "resource_type",
            "extraction_path_for_event": "metadata.resource_type",
            "field_type": Optional[dict[str, Any]],
        }
    },
    "by_languages": {
        "usage_events": {
            "event_field": "languages",
            "extraction_path_for_event": "metadata.languages",
            "field_type": Optional[list[str]],
        }
    }
}
```

### Field Control

To control which fields are enriched, simply modify the subcount configuration:

**Enable a field**: Add `usage_events` configuration with `extraction_path_for_event`
**Disable a field**: Remove the `usage_events` configuration or set it to empty dict `{}`
**Skip enrichment**: Set `event_field: None` for fields that already exist in events

## Supported Enrichment Fields

The following fields are supported for enrichment based on the subcount configuration:

| Field Name | Source Path | Subcount Key | Extraction Method | Description |
|------------|-------------|--------------|-------------------|-------------|
| `resource_type` | `metadata.resource_type` | `by_resource_types` | `"metadata.resource_type"` | Resource type information |
| `subjects` | `metadata.subjects` | `by_subjects` | `"metadata.subjects"` | Subject classifications |
| `languages` | `metadata.languages` | `by_languages` | `"metadata.languages"` | Languages of the record |
| `rights` | `metadata.rights` | `by_rights` | `"metadata.rights"` | Rights/license information |
| `funders` | `metadata.funding.funder` | `by_funders` | `lambda metadata: [...]` | Funding information (complex) |
| `journal_title` | `custom_fields.journal:journal.title` | `by_periodicals` | `"custom_fields.journal:journal.title.keyword"` | Journal title for articles |
| `affiliations` | `metadata.creators/contributors.affiliations` | `by_affiliations` | `lambda metadata: [...]` | Author affiliations (complex) |
| `file_types` | `files.entries.ext` | `by_file_types` | `lambda metadata: [...]` | File type extensions (complex) |
| `publisher` | `metadata.publisher` | `by_publishers` | `"metadata.publisher"` | Publisher information |
| `access_status` | `access.status` | `by_access_statuses` | `"access.status"` | Access status of the record |
| `country` | `N/A` | `by_countries` | `event_field: None` | Country information (already in events) |
| `referrer` | `N/A` | `by_referrers` | `event_field: None` | Referrer information (already in events) |

## Extraction Methods

### 1. Dot-Separated String Paths (Recommended)

For simple field access, use dot-separated paths that glom can pre-compile:

```python
"extraction_path_for_event": "metadata.resource_type"
"extraction_path_for_event": "metadata.subjects"
"extraction_path_for_event": "access.status"
```

**Benefits:**
- **Pre-compiled specs** for maximum performance
- **Automatic error handling** for missing paths
- **Clean and readable** configuration

### 2. Lambda Functions

For complex transformations that glom can't handle:

```python
"extraction_path_for_event": lambda metadata: [
    item["funder"]
    for item in metadata.get("funding", [])
    if isinstance(item, dict) and "funder" in item
]
```

**Use cases:**
- **List comprehensions** with filtering
- **Conditional logic** and fallbacks
- **Type checking** and validation
- **Data transformation** and aggregation

## Field Enrichment Control

### event_field: None (Skip Enrichment)

Some fields like `country` and `referrer` already exist in the original usage events and don't need enrichment. To skip enrichment for these fields, set `event_field: None`:

```python
"by_countries": {
    "usage_events": {
        "event_field": None,  # Skip enrichment - field already exists in events
        "field_type": Optional[str],
        # No extraction_path_for_event needed
    }
},
"by_referrers": {
    "usage_events": {
        "event_field": None,  # Skip enrichment - field already exists in events
        "field_type": Optional[str],
        # No extraction_path_for_event needed
    }
}
```

**When to use `event_field: None`:**
- **Field already exists** in the original usage event (e.g., `country`, `referrer`)
- **No metadata extraction needed** - the field value is already present
- **Performance optimization** - avoids unnecessary metadata lookups
- **Statistics only** - the subcount is used for aggregation but not enrichment

## Usage Examples

### Enable All Fields

```python
COMMUNITY_STATS_SUBCOUNT_CONFIGS = {
    "by_subjects": {
        "usage_events": {
            "event_field": "subjects",
            "extraction_path_for_event": "metadata.subjects",
            "field_type": Optional[list[str]],
        }
    },
    "by_resource_types": {
        "usage_events": {
            "event_field": "resource_type",
            "extraction_path_for_event": "metadata.resource_type",
            "field_type": Optional[dict[str, Any]],
        }
    },
    "by_languages": {
        "usage_events": {
            "event_field": "languages",
            "extraction_path_for_event": "metadata.languages",
            "field_type": Optional[list[str]],
        }
    },
    "by_rights": {
        "usage_events": {
            "event_field": "rights",
            "extraction_path_for_event": "metadata.rights",
            "field_type": Optional[list[str]],
        }
    },
    "by_funders": {
        "usage_events": {
            "event_field": "funders",
            "extraction_path_for_event": lambda metadata: [
                item["funder"]
                for item in metadata.get("funding", [])
                if isinstance(item, dict) and "funder" in item
            ],
            "field_type": Optional[list[str]],
        }
    },
    "by_periodicals": {
        "usage_events": {
            "event_field": "journal_title",
            "extraction_path_for_event": "custom_fields.journal:journal.title.keyword",
            "field_type": Optional[str],
        }
    },
    "by_affiliations": {
        "usage_events": {
            "event_field": "affiliations",
            "extraction_path_for_event": lambda metadata: [
                item["affiliations"]
                for item in metadata.get("creators", [])
                + metadata.get("contributors", [])
                if "affiliations" in item
            ],
            "field_type": Optional[list[str]],
        }
    },
    "by_file_types": {
        "usage_events": {
            "event_field": "file_types",
            "extraction_path_for_event": lambda metadata: (
                metadata.get("files", {}).get("types", [])
                if metadata.get("files", {}).get("types", [])
                else [
                    item["ext"]
                    for item in metadata.get("files", {}).get("entries", [])
                    if "ext" in item
                ]
            ),
            "field_type": Optional[list[str]],
        }
    },
    "by_publishers": {
        "usage_events": {
            "event_field": "publisher",
            "extraction_path_for_event": "metadata.publisher",
            "field_type": Optional[str],
        }
    },
    "by_access_statuses": {
        "usage_events": {
            "event_field": "access_status",
            "extraction_path_for_event": "access.status",
            "field_type": Optional[str],
        }
    },
}
```

### Selective Field Enrichment

```python
# Enable only essential fields
COMMUNITY_STATS_SUBCOUNT_CONFIGS = {
    "by_subjects": {
        "usage_events": {
            "event_field": "subjects",
            "extraction_path_for_event": "metadata.subjects",
            "field_type": Optional[list[str]],
        }
    },
    "by_resource_types": {
        "usage_events": {
            "event_field": "resource_type",
            "extraction_path_for_event": "metadata.resource_type",
            "field_type": Optional[dict[str, Any]],
        }
    },
    "by_file_types": {
        "usage_events": {
            "event_field": "file_types",
            "extraction_path_for_event": lambda metadata: [
                item["ext"]
                for item in metadata.get("files", {}).get("entries", [])
                if "ext" in item
            ],
            "field_type": Optional[list[str]],
        }
    },

    # These fields will NOT be enriched (no usage_events config)
    "by_languages": {"records": {...}},  # No usage_events
    "by_rights": {"records": {...}},     # No usage_events
}
```

### Disable Specific Fields

```python
# Disable subjects enrichment by removing usage_events
COMMUNITY_STATS_SUBCOUNT_CONFIGS = {
    "by_subjects": {
        "records": {"field": "metadata.subjects.id", ...},
        # No usage_events section = no enrichment
    },
    "by_resource_types": {
        "usage_events": {
            "event_field": "resource_type",
            "extraction_path_for_event": "metadata.resource_type",
            "field_type": Optional[dict[str, Any]],
        }
    },
}
```

### Skip Enrichment for Existing Fields

```python
# Fields that already exist in events - no enrichment needed
COMMUNITY_STATS_SUBCOUNT_CONFIGS = {
    "by_countries": {
        "usage_events": {
            "event_field": None,  # Field already exists in events
            "field_type": Optional[str],
            # No extraction_path_for_event needed
        }
    },
    "by_referrers": {
        "usage_events": {
            "event_field": None,  # Field already exists in events
            "field_type": Optional[str],
            # No extraction_path_for_event needed
        }
    },
    "by_resource_types": {
        "usage_events": {
            "event_field": "resource_type",  # This field WILL be enriched
            "extraction_path_for_event": "metadata.resource_type",
            "field_type": Optional[dict[str, Any]],
        }
    },
}
```

## Performance Considerations

- **Field Selection**: Only fields with `usage_events` configuration are enriched
- **Extraction Method**: Dot-separated paths are pre-compiled for maximum performance
- **Caching**: Record ID-based caching prevents redundant metadata extraction
- **Metadata Access**: Enrichment requires access to record metadata
- **Storage**: More enriched fields mean larger event documents
- **Indexing**: Enriched events may take longer to index

## Caching and Performance

### Record ID Caching

The `MetadataExtractor` automatically caches extracted values by record ID:

```python
# First event for record "123" → cache miss, extract metadata
enrichment = extractor.extract_fields(metadata, record_id="123")

# Second event for record "123" → cache hit, use cached metadata
enrichment = extractor.extract_fields(metadata, record_id="123")
```

### Cache Statistics

Monitor cache performance:

```python
# Get cache statistics
stats = service.metadata_extractor.get_cache_stats()
print(f"Hit rate: {stats['hit_rate_percent']}%")
print(f"Total requests: {stats['total_requests']}")

# Clear cache if needed
service.metadata_extractor.clear_cache()
```

### Performance Tuning

- **High hit rates** (90%+) indicate effective caching
- **Low hit rates** (<50%) suggest cache isn't helping much
- **Memory usage** can be monitored via `cached_records` count

## Migration Notes

When upgrading from the previous hardcoded enrichment system:

1. **Backward Compatibility**: The system automatically enriches all fields that have `usage_events` configuration
2. **Gradual Migration**: You can gradually add/remove `usage_events` configuration to test performance impact
3. **No New Configuration**: Uses existing `COMMUNITY_STATS_SUBCOUNT_CONFIGS` - no additional config needed
4. **Performance Boost**: New glom-based extraction with caching provides significant performance improvements

## Troubleshooting

### Common Issues

1. **No fields being enriched**: Check that subcounts have `usage_events` configuration with `extraction_path_for_event`
2. **Missing field data**: Verify that the source metadata paths in `extraction_path_for_event` are correct
3. **Performance issues**: Consider removing `usage_events` from subcounts you don't need
4. **Import errors**: Ensure `glom>=23.0.0` is installed (added to pyproject.toml)

### Field Path Examples

The `extraction_path_for_event` configuration determines where data is extracted from:

```python
# Simple paths (pre-compiled for performance)
"extraction_path_for_event": "metadata.subjects"
"extraction_path_for_event": "metadata.resource_type"
"extraction_path_for_event": "access.status"

# Complex transformations (lambda functions)
"extraction_path_for_event": lambda metadata: [...]
```

### Testing

To test your configuration:

1. Modify the `COMMUNITY_STATS_SUBCOUNT_CONFIGS` in your config
2. Run event reindexing
3. Check that only configured fields are enriched in the new indices
4. Monitor cache performance with `get_cache_stats()`

## Dependencies

The enrichment system requires:

- **glom>=23.0.0**: For high-performance metadata extraction with pre-compiled specs
- **Python 3.12+**: For optimal performance and type hints support

The `glom` dependency is automatically installed when installing the package.
