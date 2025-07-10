# Improve search query efficiency
_Exported on 7/7/2025 at 14:44:10 EDT from Cursor (1.2.1)_

---

**User**

Are there places you see in aggregations.py where I could make the search queries more efficient without changing functionality? Don't make any changes. Just explain them to me.

---

**Cursor**

Looking at the `aggregations.py` file, I can identify several areas where search query efficiency could be improved without changing functionality:


Based on my analysis of the `aggregations.py` file and related code, here are the key areas where search query efficiency could be improved without changing functionality:

## 3. **Inefficient Metadata Retrieval**

In `_get_metadata_for_records()` (lines 1900-1950), the method retrieves metadata for records one by one:

```python
meta_search = Search(using=self.client, index=prefix_index("rdmrecords-records"))
meta_search = meta_search.filter("terms", id=record_ids)
meta_search = meta_search.source([...])  # Large source list
```

**Optimization**:
- Use `search_after` for better pagination performance
- Consider using `collapse` aggregation to reduce duplicate metadata
- Implement caching for frequently accessed metadata

## 4. **Multiple Index Refreshes**

Throughout the code, there are frequent calls to `self.client.indices.refresh(index=index_name)`. For example:

```python
self.client.indices.refresh(index=temp_index)
```

**Optimization**: Batch refresh operations or use `wait_for` parameter to reduce the number of refresh calls.

## 5. **Inefficient Date Range Queries**

In several places, date range queries use string formatting:

```python
search = search.filter(
    "range",
    timestamp={
        "gte": date.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
        "lt": date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
    },
)
```

**Optimization**: Use timestamp objects directly instead of string formatting, which is more efficient for OpenSearch.

## 6. **Large Source Lists in Queries**

In `_get_metadata_for_records()`, the source list is quite extensive:

```python
meta_search = meta_search.source([
    "access.status",
    "custom_fields.journal:journal.title.keyword",
    "files.types",
    # ... many more fields
])
```

**Optimization**: Only retrieve the fields that are actually used in the aggregation logic.

## 7. **Inefficient Bucket Processing**

In `_create_aggregation_doc()`, the code processes buckets multiple times:

```python
for bucket in buckets:
    # Process each bucket
    # Then process again for different metrics
```

**Optimization**: Process all metrics for each bucket in a single pass rather than multiple iterations.

## 8. **Missing Query Optimization Hints**

The queries don't use OpenSearch's query optimization features like:
- `_source` filtering
- `docvalue_fields` for better performance on keyword fields
- `runtime_mappings` for computed fields

## 9. **Inefficient Bulk Operations**

In the bulk indexing operations, the chunk size is fixed:

```python
bulk(
    self.client,
    self.agg_iter(community_id, lower_limit, upper_limit),
    stats_only=False if return_results else True,
    chunk_size=50,  # Fixed chunk size
)
```

**Optimization**: Use adaptive chunk sizing based on document size and cluster performance.

## 10. **Redundant Community Event Queries**

In `_filter_for_community()`, the method queries community events for each record:

```python
community_search = (
    Search(using=self.client, index=prefix_index("stats-community-events"))
    .filter("term", community_id=community_id)
    .filter("terms", record_id=list(record_ids))
)
```

**Optimization**: Cache community membership data or use more efficient aggregation queries.

## 11. **Inefficient Top Hits Aggregations**

The code uses `top_hits` aggregations with size=1 in multiple places:

```python
field_bucket.bucket(
    "title",
    "top_hits",
    size=1,
    _source={"includes": title_field},
    sort=[{"_score": "desc"}],
)
```

**Optimization**: Use `max` or `min` aggregations where possible instead of `top_hits` with size=1.

## 12. **Missing Index Optimization**

The code doesn't take advantage of:
- Index routing for better shard distribution
- Index aliases for zero-downtime operations
- Index lifecycle management for automatic optimization

These optimizations would significantly improve query performance while maintaining the same functionality. The most impactful would be the composite aggregation optimization, reducing redundant searches, and implementing proper caching strategies.

```python
composite_params = {
    "sources": [
        {
            "recid": {
                "terms": {
                    "field": "recid",
                }
            }
        }
    ],
    "size": 1000,  # Fixed size
}
```

```python
# First search for composite aggregation
search = Search(using=self.client, index=event_index)
# ... composite aggregation logic

# Second search for actual hits
hits_search = Search(using=self.client, index=event_index)
hits_search = hits_search.filter("terms", recid=list(record_ids))
```

```python
meta_search = Search(using=self.client, index=prefix_index("rdmrecords-records"))
meta_search = meta_search.filter("terms", id=record_ids)
meta_search = meta_search.source([...])  # Large source list
```

```python
self.client.indices.refresh(index=temp_index)
```

```python
search = search.filter(
    "range",
    timestamp={
        "gte": date.floor("day").format("YYYY-MM-DDTHH:mm:ss"),
        "lt": date.ceil("day").format("YYYY-MM-DDTHH:mm:ss"),
    },
)
```

```python
meta_search = meta_search.source([
    "access.status",
    "custom_fields.journal:journal.title.keyword",
    "files.types",
    # ... many more fields
])
```

```python
for bucket in buckets:
    # Process each bucket
    # Then process again for different metrics
```

```python
bulk(
    self.client,
    self.agg_iter(community_id, lower_limit, upper_limit),
    stats_only=False if return_results else True,
    chunk_size=50,  # Fixed chunk size
)
```

```python
community_search = (
    Search(using=self.client, index=prefix_index("stats-community-events"))
    .filter("term", community_id=community_id)
    .filter("terms", record_id=list(record_ids))
)
```

```python
field_bucket.bucket(
    "title",
    "top_hits",
    size=1,
    _source={"includes": title_field},
    sort=[{"_score": "desc"}],
)
```

---

**User**

Regarding #1, isn't that just the request size limit? It doesn't use more memory or time if the actual number of hits is smaller?

---

**Cursor**

You're absolutely correct! I made an error in my analysis. The `size` parameter in composite aggregations is indeed just a **request size limit**, not a memory allocation. Here's the clarification:

## How Composite Aggregation Size Actually Works

According to the [Elasticsearch documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/search-aggregations-bucket-composite-aggregation.html), the `size` parameter:

- **Limits the number of composite buckets returned** in a single response
- **Does NOT pre-allocate memory** for that size
- **Only processes the actual number of documents** that match the query
- **Returns up to `size` buckets** (or fewer if there aren't enough matches)

So in the code:
```python
composite_params = {
    "sources": [
        {
            "recid": {
                "terms": {
                    "field": "recid",
                }
            }
        }
    ],
    "size": 1000,  # This is just a limit, not memory allocation
}
```

If there are only 50 unique `recid` values in the date range, the aggregation will:
- Process only 50 documents
- Return 50 buckets
- Use memory proportional to 50 buckets, not 1000

## The Real Optimization Opportunity

The actual optimization for composite aggregations would be:

1. **Adaptive sizing based on expected results**: If you know the dataset typically has 100-200 unique records per day, using `size=200` instead of `size=1000` would reduce network transfer and response parsing time.

2. **Using `track_total_hits: false`** for better performance:
```python
search = Search(using=self.client, index=event_index)
search = search.extra(track_total_hits=False)  # Add this
```

3. **Index sorting optimization**: If the index is sorted by `recid` and `timestamp`, the composite aggregation can use early termination, making it much faster.

4. **Pagination efficiency**: Using smaller sizes (like 100-500) with proper `after_key` pagination is often more efficient than larger sizes, especially for memory-constrained environments.

So you're right - the `size` parameter itself doesn't cause memory inefficiency. The real optimizations would be around the pagination strategy, index sorting, and using `track_total_hits: false` for better performance.

```python
composite_params = {
    "sources": [
        {
            "recid": {
                "terms": {
                    "field": "recid",
                }
            }
        }
    ],
    "size": 1000,  # This is just a limit, not memory allocation
}
```

```python
search = Search(using=self.client, index=event_index)
search = search.extra(track_total_hits=False)  # Add this
```

---

**User**

I don't understand what track_total_hits would do?

---

**Cursor**

Great question! Let me explain what `track_total_hits` does and why it matters for performance.

## What `track_total_hits` Does

According to the [Elasticsearch documentation](https://www.elastic.co/guide/en/elasticsearch/reference/7.1/search-request-track-total-hits.html), `track_total_hits` controls whether Elasticsearch counts the total number of documents that match your query.

### The Problem It Solves

When you run a search query, Elasticsearch needs to know how many total documents match your criteria. However, counting **every single matching document** can be very expensive, especially for queries that match millions of documents.

### How It Works

1. **`track_total_hits: true`** - Counts ALL matching documents accurately
2. **`track_total_hits: false`** - Doesn't count at all (fastest)
3. **`track_total_hits: 10000`** - Counts accurately up to 10,000, then stops (default since Elasticsearch 7.0)

### Example Response Differences

**With `track_total_hits: true`:**
```json
{
  "hits": {
    "total": {
      "value": 2048,
      "relation": "eq"  // Accurate count
    }
  }
}
```

**With `track_total_hits: false`:**
```json
{
  "hits": {
    // No total count at all
  }
}
```

**With `track_total_hits: 10000` (default):**
```json
{
  "hits": {
    "total": {
      "value": 10000,
      "relation": "gte"  // "Greater than or equal to 10,000"
    }
  }
}
```

## Why This Matters for Your Aggregations

In your `aggregations.py` code, you're doing searches like:

```python
search = Search(using=self.client, index=event_index)
search = search.filter("range", timestamp={...})
```

By default, Elasticsearch will count up to 10,000 matching documents. If your date range has 50,000 events, it will:
- Process all 50,000 documents for the aggregation
- But only count the first 10,000 for the total
- Return `"gte": 10000` instead of the actual count

## Performance Impact

According to the [GitHub PR discussion](https://github.com/elastic/elasticsearch/pull/37466), this change was made because:

> "Generally the total hit count can't be computed accurately without visiting all matches, which is costly for queries that match lots of documents."

For your aggregation queries, you probably don't need the total count at all since you're doing aggregations, not pagination. Setting `track_total_hits: false` would:

1. **Skip the counting phase entirely**
2. **Process documents faster**
3. **Reduce memory usage**
4. **Improve response times**

## When to Use Each Setting

- **`track_total_hits: false`** - When you only need aggregations (your use case)
- **`track_total_hits: true`** - When you need exact pagination counts
- **`track_total_hits: 10000`** - Default, good for most pagination use cases

For your aggregation code, using `track_total_hits: false` would be the most efficient since you're not using the total count for anything.

```json
{
  "hits": {
    "total": {
      "value": 2048,
      "relation": "eq"  // Accurate count
    }
  }
}
```

```json
{
  "hits": {
    // No total count at all
  }
}
```

```json
{
  "hits": {
    "total": {
      "value": 10000,
      "relation": "gte"  // "Greater than or equal to 10,000"
    }
  }
}
```

```python
search = Search(using=self.client, index=event_index)
search = search.filter("range", timestamp={...})
```

