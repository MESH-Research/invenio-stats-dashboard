# OpenSearch Index Template Migration Strategy

This document outlines a safe approach to updating OpenSearch index templates and migrating data with minimal downtime for production applications with large datasets.

## Overview

When you need to update index templates that control mappings for existing indices with millions of records, you need a strategy that:

1. **Minimizes downtime** - Application remains available throughout the process
2. **Preserves data** - No data loss during migration
3. **Enables enrichment** - Add new field values during migration
4. **Provides rollback** - Ability to revert if issues arise
5. **Scales efficiently** - Handle large datasets over multiple days

## Migration Strategy

### Phase 1: Template Update (Zero Downtime)

**Goal**: Update the index template without affecting existing indices.

```bash
# Update template - this doesn't affect existing indices
curl -X PUT "localhost:9200/_index_template/your-template-name" \
  -H "Content-Type: application/json" \
  -d @updated-template.json
```

**Key Points**:
- Existing indices continue to use their current mappings
- New indices created after this point will use the updated template
- No downtime or data loss

### Phase 2: Create New Indices

**Goal**: Create new indices with updated mappings for each monthly index.

```bash
# Example: Create new index for January 2024
curl -X PUT "localhost:9200/your-index-2024-01-v2" \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 1
    },
    "mappings": {
      "properties": {
        "existing_field": {"type": "keyword"},
        "new_field_1": {"type": "keyword"},
        "new_field_2": {"type": "text"}
      }
    }
  }'
```

### Phase 3: Reindex with Enrichment

**Goal**: Copy data from old indices to new indices while adding new field values.

Based on the existing `EventReindexingService` pattern in the codebase:

```python
def reindex_with_enrichment(source_index, target_index, enrichment_data):
    """Reindex data with enrichment."""
    client = current_search_client

    # Use scroll API for large datasets
    search = Search(using=client, index=source_index)
    search = search.extra(size=1000)

    for batch in search.scan():
        enriched_docs = []
        for hit in batch:
            doc = hit["_source"]
            doc_id = hit["_id"]

            # Add new field values
            if doc_id in enrichment_data:
                doc.update(enrichment_data[doc_id])

            enriched_docs.append({
                "_index": target_index,
                "_id": doc_id,
                "_source": doc
            })

        # Bulk index enriched documents
        if enriched_docs:
            bulk(client, enriched_docs)
```

### Phase 4: Update Aliases

**Goal**: Switch aliases to point to new indices.

```bash
# Update alias to point to new index
curl -X POST "localhost:9200/_aliases" \
  -H "Content-Type: application/json" \
  -d '{
    "actions": [
      {
        "remove": {
          "index": "your-index-2024-01",
          "alias": "your-index-alias"
        }
      },
      {
        "add": {
          "index": "your-index-2024-01-v2",
          "alias": "your-index-alias"
        }
      }
    ]
  }'
```

### Phase 5: Verification

**Goal**: Ensure migration was successful.

```python
def verify_migration(old_index, new_index):
    """Verify migration success."""
    # Check document counts
    old_count = client.count(index=old_index)["count"]
    new_count = client.count(index=new_index)["count"]

    assert old_count == new_count

    # Verify sample documents
    sample_docs = client.search(
        index=old_index,
        body={"size": 100}
    )["hits"]["hits"]

    for hit in sample_docs:
        doc_id = hit["_id"]
        new_doc = client.get(index=new_index, id=doc_id)
        assert new_doc["_source"] == hit["_source"]
```

## Implementation Steps

### 1. Prepare Updated Template

Create your updated index template with new fields:

```json
{
  "index_patterns": ["your-index-*"],
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 1
    },
    "mappings": {
      "properties": {
        "existing_field": {"type": "keyword"},
        "new_field_1": {"type": "keyword"},
        "new_field_2": {"type": "text"}
      }
    }
  },
  "priority": 100,
  "version": 2,
  "_meta": {
    "description": "Updated template with new fields"
  }
}
```

### 2. Deploy Template

Update the template without affecting existing indices:

```bash
curl -X PUT "localhost:9200/_index_template/your-template" \
  -H "Content-Type: application/json" \
  -d @updated-template.json
```

### 3. Create Migration Script

Use the provided migration script or create your own based on the patterns in the codebase:

```bash
python scripts/migrate_index_template.py \
  --template your-template \
  --template-file updated-template.json \
  --index-pattern your-index \
  --alias your-index-alias \
  --batch-size 1000 \
  --enrichment-file enrichment-data.json
```

### 4. Execute Gradual Migration

Migrate indices one at a time, starting with the oldest:

```python
monthly_indices = [
    "your-index-2023-01",
    "your-index-2023-02",
    # ... all your monthly indices
]

for old_index in monthly_indices:
    new_index = f"{old_index}-v2"

    # Create new index
    create_new_index(new_index, new_mapping)

    # Reindex with enrichment
    reindex_with_enrichment(old_index, new_index, enrichment_data)

    # Update alias
    update_alias(old_index, new_index)

    # Verify migration
    verify_migration(old_index, new_index)
```

### 5. Monitor and Cleanup

After successful migration:

```bash
# Optional: Delete old indices after verification
curl -X DELETE "localhost:9200/your-index-2023-01"
```

## Best Practices

### 1. Gradual Migration

- Migrate one index at a time
- Start with oldest data first
- Monitor system resources during migration

### 2. Enrichment Strategy

- Prepare enrichment data in advance
- Use batch processing for large datasets
- Implement error handling and retry logic

### 3. Verification

- Verify document counts match
- Check sample documents for accuracy
- Monitor application functionality during migration

### 4. Rollback Plan

- Keep old indices until verification is complete
- Document rollback procedures
- Test rollback scenarios

### 5. Monitoring

- Monitor OpenSearch cluster health
- Track migration progress
- Alert on errors or failures

## Example Usage

### Basic Migration

```bash
# Update template
curl -X PUT "localhost:9200/_index_template/my-template" \
  -H "Content-Type: application/json" \
  -d @updated-template.json

# Run migration script
python scripts/migrate_index_template.py \
  --template my-template \
  --template-file updated-template.json \
  --index-pattern my-index \
  --alias my-index-alias
```

### Migration with Enrichment

```bash
# Create enrichment data file
cat > enrichment-data.json << EOF
{
  "doc1": {"new_field_1": "value1"},
  "doc2": {"new_field_1": "value2"}
}
EOF

# Run migration with enrichment
python scripts/migrate_index_template.py \
  --template my-template \
  --template-file updated-template.json \
  --index-pattern my-index \
  --alias my-index-alias \
  --enrichment-file enrichment-data.json
```

## Troubleshooting

### Common Issues

1. **Template Update Fails**
   - Check template syntax
   - Verify template name and version
   - Ensure proper permissions

2. **Reindexing Errors**
   - Reduce batch size
   - Check cluster resources
   - Verify enrichment data format

3. **Alias Update Fails**
   - Ensure alias exists
   - Check index names
   - Verify permissions

4. **Verification Failures**
   - Check document counts
   - Review sample documents
   - Verify enrichment data

### Monitoring Commands

```bash
# Check cluster health
curl "localhost:9200/_cluster/health"

# Monitor indices
curl "localhost:9200/_cat/indices?v"

# Check aliases
curl "localhost:9200/_cat/aliases?v"

# Monitor reindexing progress
curl "localhost:9200/_tasks?detailed=true&actions=*reindex"
```

## Conclusion

This migration strategy provides a safe, gradual approach to updating OpenSearch index templates and migrating data with minimal downtime. By following the patterns established in the KCWorks codebase and implementing proper verification and rollback procedures, you can successfully migrate large datasets while maintaining application availability.