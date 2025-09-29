# API Requests

This document describes all available API endpoints and query parameters for the Invenio Stats Dashboard.

## Base URL

```
/api/stats
```

## Available Queries

The following queries are available through the `/api/stats` endpoint:

### Individual Community Statistics Queries

These queries return daily aggregation documents for specific types of statistics for a community or for the entire instance:

#### Record Delta Queries
- **`community-record-delta-created`**: Record changes based on creation date
- **`community-record-delta-published`**: Record changes based on publication date
- **`community-record-delta-added`**: Record changes based on addition date

#### Record Snapshot Queries
- **`community-record-snapshot-created`**: Record totals based on creation date
- **`community-record-snapshot-published`**: Record totals based on publication date
- **`community-record-snapshot-added`**: Record totals based on addition date

#### Usage Queries
- **`community-usage-delta`**: Usage changes over time
- **`community-usage-snapshot`**: Usage totals at specific points in time

### Data Series Queries

These queries individual data point series derived from the daily aggregation documents for visualization or analysis:

#### Usage Data Series
- **`usage-snapshot-series`**: One time series derived from usage snapshot aggregations
- **`usage-delta-series`**: One time series derived from usage delta aggregations

#### Record Data Series
- **`record-snapshot-series`**: One time series derived from record snapshot aggregations
- **`record-delta-series`**: One time series derived from record delta aggregations

### Category-Wide Queries

These queries return sets of multiple data point series derived from the daily aggregation documents, broken down by categories:

#### Usage Category Queries
- **`usage-snapshot-category`**: All data point series derived from usage snapshot aggregations
- **`usage-delta-category`**: All data point series derived from usage delta aggregations

#### Record Category Queries
- **`record-snapshot-category`**: All data point series derived from record snapshot aggregations
- **`record-delta-category`**: All data point series derived from record delta aggregations

### Composite Queries

These queries combine multiple aggregation document requests into a single response:

- **`community-stats`**: Combined aggregation documents for a specific community
- **`global-stats`**: Combined aggregation documents for the global repository

## Query Parameters

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `community_id` | string | UUID of the community (for community-specific queries) |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_date` | string | None | Start date for the query range (ISO 8601 format: YYYY-MM-DD) |
| `end_date` | string | None | End date for the query range (ISO 8601 format: YYYY-MM-DD) |
| `date_basis` | string | "added" | Date field to use for determining the start of a record's "lifetime" for statistics |

### Date Basis Parameter

The `date_basis` parameter determines which date field to use for determining the start of a record's "lifetime" for statistics. This parameter is supported by all data series and category queries.

#### Available Values

- **`"added"`** (default): Date when the record was added to the community/instance (==`created` date for the global repository stats)
- **`"created"`**: Record creation (publication) in the InvenioRDM instance (`created`)
- **`"published"`**: Publication date of the record's material (`metadata.publication_date`)

#### How It Works

When a `date_basis` parameter is specified, the query system:

1. Dynamically selects the appropriate OpenSearch index based on the date basis
2. Appends the date basis as a suffix to the base index name
3. Filters documents using the specified date field

For example:
- `date_basis="created"` → searches in `stats-community-records-snapshot-created`
- `date_basis="published"` → searches in `stats-community-records-snapshot-published`
- `date_basis="added"` → searches in `stats-community-records-snapshot-added`

## Example Requests

All API requests are made using POST requests with JSON bodies to the `/api/stats` endpoint.

### Individual Community Statistics

```bash
# Get record delta aggregation documents based on creation date
POST /api/stats
Content-Type: application/json

{
  "community-record-delta-created": {
    "stat": "community-record-delta-created",
    "params": {
      "community_id": "12345678-1234-1234-1234-123456789012",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31",
      "date_basis": "created"
    }
  }
}

# Get record snapshot aggregation documents based on publication date
POST /api/stats
Content-Type: application/json

{
  "community-record-snapshot-published": {
    "stat": "community-record-snapshot-published",
    "params": {
      "community_id": "12345678-1234-1234-1234-123456789012",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
      "date_basis": "published"
    }
  }
}

# Get usage delta aggregation documents based on added date
POST /api/stats
Content-Type: application/json

{
  "community-usage-delta": {
    "stat": "community-usage-delta",
    "params": {
      "community_id": "12345678-1234-1234-1234-123456789012",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
    }
  }
}

# Get usage snapshot aggregation documents based on added date
POST /api/stats
Content-Type: application/json

{
  "community-usage-snapshot": {
    "stat": "community-usage-snapshot",
    "params": {
      "community_id": "12345678-1234-1234-1234-123456789012",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
    }
  }
}
```

### Data Series Queries

```bash
# Get record snapshot data point series based on record creation date
POST /api/stats
Content-Type: application/json

{
  "record-snapshot-series": {
    "stat": "record-snapshot-series",
    "params": {
      "community_id": "12345678-1234-1234-1234-123456789012",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
      "date_basis": "created",
    }
  }
}

# Get record delta data point series based on added date
POST /api/stats
Content-Type: application/json

{
  "record-delta-series": {
    "stat": "record-delta-series",
    "params": {
      "community_id": "12345678-1234-1234-1234-123456789012",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
    }
  }
}

# Get usage snapshot data point series based on added date
POST /api/stats
Content-Type: application/json

{
  "usage-snapshot-series": {
    "stat": "usage-snapshot-series",
    "params": {
      "community_id": "12345678-1234-1234-1234-123456789012",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
    }
  }
}

# Get usage delta data point series based on added date
POST /api/stats
Content-Type: application/json

{
  "usage-delta-series": {
    "stat": "usage-delta-series",
    "params": {
      "community_id": "12345678-1234-1234-1234-123456789012",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
    }
  }
}
```

### Category-Wide Queries

```bash
# Get all record snapshot data point series based on record creation date
POST /api/stats
Content-Type: application/json

{
  "record-snapshot-category": {
    "stat": "record-snapshot-category",
    "params": {
      "community_id": "12345678-1234-1234-1234-123456789012",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31",
      "date_basis": "created"
    }
  }
}

# Get all record delta data point series based on added date
POST /api/stats
Content-Type: application/json

{
  "record-delta-category": {
    "stat": "record-delta-category",
    "params": {
      "community_id": "12345678-1234-1234-1234-123456789012",
      "date_basis": "published",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
    }
  }
}

# Get all usage snapshot data point series based on added date
POST /api/stats
Content-Type: application/json

{
  "usage-snapshot-category": {
    "stat": "usage-snapshot-category",
    "params": {
      "community_id": "12345678-1234-1234-1234-123456789012",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
    }
  }
}

# Get all usage delta data point series based on added date
POST /api/stats
Content-Type: application/json

{
  "usage-delta-category": {
    "stat": "usage-delta-category",
    "params": {
      "community_id": "12345678-1234-1234-1234-123456789012",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
    }
  }
}
```

### Composite Queries

```bash
# Get all aggregation documents for a specific community
POST /api/stats
Content-Type: application/json

{
  "community-stats": {
    "stat": "community-stats",
    "params": {
      "community_id": "12345678-1234-1234-1234-123456789012",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
    }
  }
}

# Get all aggregation documents for a specific community based on record creation date
POST /api/stats
Content-Type: application/json

{
  "community-stats": {
    "stat": "community-stats",
    "params": {
      "community_id": "12345678-1234-1234-1234-123456789012",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31",
      "date_basis": "created"
    }
  }
}

# Get all global aggregation documents based on added date
POST /api/stats
Content-Type: application/json

{
  "global-stats": {
    "stat": "global-stats",
    "params": {
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
    }
  }
}

# Get all global aggregation documents based on publication date
POST /api/stats
Content-Type: application/json

{
  "global-stats": {
    "stat": "global-stats",
    "params": {
      "date_basis": "published",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
    }
  }
}
```

### Multiple Queries in Single Request

```bash
# Get multiple statistics in a single request
POST /api/stats
Content-Type: application/json

{
  "usage-snapshot-category": {
    "stat": "usage-snapshot-category",
    "params": {
      "community_id": "12345678-1234-1234-1234-123456789012",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
    }
  },
  "record-snapshot-category": {
    "stat": "record-snapshot-category",
    "params": {
      "community_id": "12345678-1234-1234-1234-123456789012",
      "date_basis": "created",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
    }
  }
}
```

## Response Formats

The API supports multiple response formats through content negotiation:

### JSON (Default)
```
Accept: application/json
```

### Compressed JSON

The API supports two compression formats for JSON responses to reduce bandwidth usage, especially beneficial for large data series:

#### Gzip Compression
```
Accept: application/json
Accept-Encoding: gzip
```

#### Brotli Compression (Recommended)
```
Accept: application/json
Accept-Encoding: br
```

#### Both Compression Methods
```
Accept: application/json
Accept-Encoding: br, gzip
```

**Note:** When both compression methods are supported by the client, Brotli is preferred as it typically provides better compression ratios (15-25% smaller files) while maintaining fast decompression speeds.

### CSV
```
Accept: text/csv
```

### XML
```
Accept: application/xml
```

### Excel
```
Accept: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
```

## Response Structure



### Composite Queries

```json
{
  "record_deltas_created": {
    "hits": {
      "total": {"value": 100, "relation": "eq"},
      "hits": [...]
    }
  },
  "record_deltas_published": {
    "hits": {
      "total": {"value": 95, "relation": "eq"},
      "hits": [...]
    }
  },
  "record_deltas_added": {
    "hits": {
      "total": {"value": 100, "relation": "eq"},
      "hits": [...]
    }
  },
  "record_snapshots_created": {
    "hits": {
      "total": {"value": 1000, "relation": "eq"},
      "hits": [...]
    }
  },
  "record_snapshots_published": {
    "hits": {
      "total": {"value": 950, "relation": "eq"},
      "hits": [...]
    }
  },
  "record_snapshots_added": {
    "hits": {
      "total": {"value": 1000, "relation": "eq"},
      "hits": [...]
    }
  },
  "usage_deltas": {
    "hits": {
      "total": {"value": 500, "relation": "eq"},
      "hits": [...]
    }
  },
  "usage_snapshots": {
    "hits": {
      "total": {"value": 5000, "relation": "eq"},
      "hits": [...]
    }
  }
}
```

## Performance Optimization

### Compression Benefits

For large data series queries (especially those returning 10MB+ of JSON data), compression can significantly improve performance:

- **Brotli**: Typically 15-25% better compression than gzip, with fast decompression
- **Gzip**: Widely supported, good compression ratio, fast compression and decompression
- **Uncompressed**: Fastest for small datasets, but inefficient for large data series

### Recommended Usage

- **Large datasets**: Use Brotli compression (`Accept-Encoding: br`) for best performance
- **Maximum compatibility**: Use Gzip compression (`Accept-Encoding: gzip`) for older clients
- **Small datasets**: Uncompressed JSON is often sufficient for queries returning <1MB

### Example Performance Comparison

For a typical data series query returning 10MB of JSON data:
- **Uncompressed**: ~10MB transfer
- **Gzip**: ~4MB transfer (60% reduction)
- **Brotli**: ~3MB transfer (70% reduction)

## Error Responses

### 400 Bad Request

```json
{
  "error": "Invalid date format",
  "message": "The provided date format is invalid. Please use ISO 8601 format (YYYY-MM-DD)."
}
```

### 404 Not Found

```json
{
  "error": "Community not found",
  "message": "The specified community ID does not exist."
}
```

### 500 Internal Server Error

```json
{
  "error": "Query execution failed",
  "message": "An error occurred while executing the statistics query."
}
```

## Authentication

Some queries may require authentication depending on the community's privacy settings. Include authentication headers when required:

```
Authorization: Bearer <your-token>
```

## Rate Limiting

API requests are subject to rate limiting to ensure system stability. The current limits are:

- 100 requests per minute per IP address
- 1000 requests per hour per authenticated user

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Download API

The Invenio Stats Dashboard provides JavaScript API functions for downloading statistics data in various serialization formats. These functions automatically use the current UI display settings (start/end date, community, dateBasis) and handle file downloads with appropriate naming.

### JavaScript API Functions

#### Import the API functions

```javascript
import {
  downloadStatsSeries,
  downloadStatsSeriesWithFilename,
  SERIALIZATION_FORMATS
} from '../api/api';
import { DASHBOARD_TYPES } from '../constants';
```

#### `downloadStatsSeriesWithFilename()`

Downloads statistics data and automatically triggers a browser download with an appropriate filename.

**Parameters:**
- `communityId` (string): Community ID or 'global' for global stats
- `dashboardType` (string): Either `DASHBOARD_TYPES.GLOBAL` or `DASHBOARD_TYPES.COMMUNITY`
- `format` (string): One of the `SERIALIZATION_FORMATS` constants
- `startDate` (string, optional): Start date in YYYY-MM-DD format
- `endDate` (string, optional): End date in YYYY-MM-DD format
- `dateBasis` (string, optional): "added", "created", or "published" (default: "added")
- `filename` (string, optional): Custom filename (auto-generated if not provided)

**Example:**
```javascript
// Download CSV format for a specific community
await downloadStatsSeriesWithFilename({
  communityId: 'research-community',
  dashboardType: DASHBOARD_TYPES.COMMUNITY,
  format: SERIALIZATION_FORMATS.CSV,
  startDate: '2024-01-01',
  endDate: '2024-12-31',
  dateBasis: 'added'
});
// Downloads: stats_series_research-community_2024-01-01_to_2024-12-31.tar.gz
```

#### `downloadStatsSeries()`

Downloads statistics data as a Blob for custom handling (e.g., upload to cloud storage, custom processing).

**Parameters:**
- `communityId` (string): Community ID or 'global' for global stats
- `dashboardType` (string): Either `DASHBOARD_TYPES.GLOBAL` or `DASHBOARD_TYPES.COMMUNITY`
- `format` (string): One of the `SERIALIZATION_FORMATS` constants
- `startDate` (string, optional): Start date in YYYY-MM-DD format
- `endDate` (string, optional): End date in YYYY-MM-DD format
- `dateBasis` (string, optional): "added", "created", or "published" (default: "added")

**Returns:** Promise<Blob> - The downloaded file as a Blob

**Example:**
```javascript
// Get the file as a blob for custom processing
const blob = await downloadStatsSeries(
  'research-community',
  DASHBOARD_TYPES.COMMUNITY,
  SERIALIZATION_FORMATS.XML,
  '2024-01-01',
  '2024-12-31',
  'published'
);

// Custom handling - e.g., upload to cloud storage
const formData = new FormData();
formData.append('file', blob, 'stats.xml');
await fetch('/api/upload', { method: 'POST', body: formData });
```

### Available Serialization Formats

| Format | Constant | Description | File Extension |
|--------|----------|-------------|----------------|
| JSON (Compressed) | `SERIALIZATION_FORMATS.JSON_BROTLI` | Brotli-compressed JSON | `.json.gz` |
| JSON (Gzip) | `SERIALIZATION_FORMATS.JSON_GZIP` | Gzip-compressed JSON | `.json.gz` |
| JSON (Raw) | `SERIALIZATION_FORMATS.JSON` | Uncompressed JSON | `.json.gz` |
| CSV | `SERIALIZATION_FORMATS.CSV` | Compressed CSV archive | `.tar.gz` |
| Excel | `SERIALIZATION_FORMATS.EXCEL` | Compressed Excel archive | `.tar.gz` |
| XML | `SERIALIZATION_FORMATS.XML` | XML with Dublin Core metadata | `.xml` |

### File Naming Convention

Files are automatically named using this pattern:
```
stats_series_{community}_{startDate}_to_{endDate}.{extension}
```

**Examples:**
- `stats_series_global_2024-01-01_to_2024-12-31.tar.gz`
- `stats_series_research-community_2024-06-01_to_2024-06-30.xml`
- `stats_series_digital-humanities.tar.gz` (no date range)

### React Component Integration

The `ReportSelector` component has been updated to use this API:

```jsx
import { ReportSelector } from '../components/controls/ReportSelector';

// In your dashboard component
<ReportSelector defaultFormat="csv" />
```

The component automatically:
- Uses current dashboard context (community, date range, date basis)
- Shows loading state during download
- Handles errors gracefully
- Generates appropriate filenames

### Advanced Usage Examples

#### Batch Downloads

```javascript
// Download multiple formats for the same data
const formats = [
  SERIALIZATION_FORMATS.CSV,
  SERIALIZATION_FORMATS.EXCEL,
  SERIALIZATION_FORMATS.XML
];

for (const format of formats) {
  await downloadStatsSeriesWithFilename({
    communityId: 'research-community',
    dashboardType: DASHBOARD_TYPES.COMMUNITY,
    format,
    startDate: '2024-01-01',
    endDate: '2024-12-31'
  });
}
```

#### Custom Filename

```javascript
// Download Excel format with custom filename
await downloadStatsSeriesWithFilename({
  communityId: 'global',
  dashboardType: DASHBOARD_TYPES.GLOBAL,
  format: SERIALIZATION_FORMATS.EXCEL,
  filename: 'my_custom_stats.xlsx'
});
// Downloads: my_custom_stats.xlsx
```

#### Error Handling

```javascript
try {
  await downloadStatsSeriesWithFilename({
    communityId: 'invalid-community',
    dashboardType: DASHBOARD_TYPES.COMMUNITY,
    format: SERIALIZATION_FORMATS.CSV
  });
} catch (error) {
  console.error('Download failed:', error.message);
  // Handle error - show user notification, retry, etc.
}
```

### Community-Specific Features

When downloading community-specific stats, the API automatically:
- Includes community metadata in XML format
- Uses community slug in filenames when available
- Falls back to community ID if slug is not available
- Handles missing communities gracefully

### Underlying API Requests

The download functions make POST requests to `/api/stats` with category-wide queries that return data series sets:

```javascript
// Example request body for downloadStatsSeries
{
  "usage-snapshot-category": {
    "stat": "usage-snapshot-category",
    "params": {
      "community_id": "research-community",
      "date_basis": "added",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
    }
  },
  "usage-delta-category": {
    "stat": "usage-delta-category",
    "params": {
      "community_id": "research-community",
      "date_basis": "added",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
    }
  },
  "record-snapshot-category": {
    "stat": "record-snapshot-category",
    "params": {
      "community_id": "research-community",
      "date_basis": "added",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
    }
  },
  "record-delta-category": {
    "stat": "record-delta-category",
    "params": {
      "community_id": "research-community",
      "date_basis": "added",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
    }
  }
}
```

The response format depends on the `Accept` header specified in the request, supporting all the serialization formats listed above.