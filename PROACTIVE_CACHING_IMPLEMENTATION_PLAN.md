# Proactive Stats Caching Implementation Plan

## Overview

This document outlines the implementation of a proactive stats caching system that generates cached responses for all data series categories without waiting for client requests. The system leverages existing cache infrastructure while introducing new domain objects and service layers.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Command   │───▶│  Service Class  │───▶│ Celery Task     │
│                 │    │                  │    │                 │
│ • Parse args    │    │ • CRUD methods   │    │ • Background    │
│ • Validate      │    │ • Orchestration  │    │   processing    │
│ • Report        │    │ • Uses existing  │    │ • Delegates to  │
└─────────────────┘    │   cache methods  │    │   CachedResponse│
                       └──────────────────┘    └─────────────────┘
```

## File Structure

```
invenio_stats_dashboard/
├── models/
│   └── cached_response.py              # CachedResponse domain model
├── services/
│   └── cached_response_service.py       # CRUD service for cached responses
├── tasks/
│   └── cache_tasks.py                   # Celery background tasks
└── cli/
    └── cache_commands.py                # CLI command definitions
```

## Detailed Implementation

### 1. CachedResponse Model (`models/cached_response.py`)

**Purpose**: Domain object representing a cached stats response with methods for content generation and cache key management.

#### Class Definition
```python
class CachedResponse:
    """Represents a cached stats response for a specific community/year/category combination."""

    def __init__(self, community_id, year, category, cache_type='community'):
        self.community_id = community_id  # 'global' for global stats
        self.year = year
        self.category = category  # Data series category (e.g., 'record_delta', 'usage_delta')
        self.cache_type = cache_type  # 'community' or 'global'
        self._cache_key = None
        self._data = None
        self._created_at = None
        self._expires_at = None
```

#### Methods

##### Core Properties
```python
@property
def is_global(self):
    """Check if this is a global stats response."""
    return self.community_id == 'global'

@property
def cache_key(self):
    """Get the cache key for this response."""
    if self._cache_key is None:
        self._cache_key = self._generate_cache_key()
    return self._cache_key

@property
def data(self):
    """Get the cached data."""
    return self._data

@property
def is_expired(self):
    """Check if the cached response is expired."""
    return self._expires_at and datetime.now() > self._expires_at
```

##### Cache Key Generation
```python
def _generate_cache_key(self):
    """Generate cache key using existing cache_utils logic."""
    from invenio_stats_dashboard.resources.cache_utils import _generate_response_cache_key

    request_data = {
        'start_date': f'{self.year}-01-01',
        'end_date': f'{self.year}-12-31',
        'community_id': self.community_id if not self.is_global else None,
        'cache_type': self.cache_type,
        'category': self.category
    }

    return _generate_response_cache_key(request_data)
```

##### Content Generation
```python
def generate_content(self):
    """Generate the JSON content for this cached response."""
    from invenio_stats_dashboard.views import StatsDashboardAPIResource

    # Create request context
    request_data = {
        'start_date': f'{self.year}-01-01',
        'end_date': f'{self.year}-12-31',
        'community_id': self.community_id if not self.is_global else None,
        'cache_type': self.cache_type,
        'category': self.category
    }

    # Use existing API resource logic
    resource = StatsDashboardAPIResource()
    response_data = resource._generate_stats_response(request_data)

    # Store the generated data
    self._data = response_data
    self._created_at = datetime.now()
    self._expires_at = self._created_at + timedelta(days=30)  # 30-day TTL

    return response_data

def to_json(self):
    """Convert the cached response to JSON format."""
    return {
        'community_id': self.community_id,
        'year': self.year,
        'category': self.category,
        'cache_type': self.cache_type,
        'cache_key': self.cache_key,
        'data': self._data,
        'created_at': self._created_at.isoformat() if self._created_at else None,
        'expires_at': self._expires_at.isoformat() if self._expires_at else None
    }
```

##### Cache Operations
```python
def save_to_cache(self):
    """Save this response to the cache using existing cache_utils."""
    from invenio_stats_dashboard.resources.cache_utils import _set_cached_response

    if self._data is None:
        self.generate_content()

    _set_cached_response(self.cache_key, self._data)
    return True

def load_from_cache(self):
    """Load this response from the cache using existing cache_utils."""
    from invenio_stats_dashboard.resources.cache_utils import _get_cached_response

    cached_data = _get_cached_response(self.cache_key)
    if cached_data:
        self._data = cached_data
        return True
    return False

def delete_from_cache(self):
    """Delete this response from the cache using existing cache_utils."""
    from invenio_stats_dashboard.resources.cache_utils import _clear_cached_response

    _clear_cached_response(self.cache_key)
    return True
```

### 2. CachedResponseService (`services/cached_response_service.py`)

**Purpose**: CRUD service for managing cached responses, orchestrating generation for all data series categories.

#### Class Definition
```python
class CachedResponseService:
    """Service for managing cached stats responses."""

    def __init__(self):
        self.categories = [
            'record_delta', 'record_snapshot', 'usage_delta', 'usage_snapshot',
            'record_delta_data_added', 'record_delta_data_removed',
            'usage_delta_data_views', 'usage_delta_data_downloads'
        ]
```

#### CRUD Methods

##### Create
```python
def create(self, community_ids, years, force=False, async_mode=False):
    """
    Create cached responses for given communities, years, and all categories.

    Args:
        community_ids: str, list, or 'all' - Community IDs to process
        years: int, list, or 'auto' - Years to process
        force: bool - Overwrite existing cache
        async_mode: bool - Use Celery tasks

    Returns:
        dict - Results summary
    """
    # Normalize inputs
    community_ids = self._normalize_community_ids(community_ids)
    years = self._normalize_years(years, community_ids)

    # Generate CachedResponse objects for all combinations
    responses = self._generate_all_response_objects(community_ids, years)

    # Filter existing (unless force=True)
    if not force:
        responses = [r for r in responses if not self.exists(r.community_id, r.year, r.category)]

    # Execute (sync or async)
    if async_mode:
        return self._create_async(responses)
    else:
        return self._create_sync(responses)
```

##### Read
```python
def read(self, community_id, year, category):
    """Read a specific cached response."""
    response = CachedResponse(community_id, year, category)
    if response.load_from_cache():
        return response
    return None

def read_all(self, community_id, year):
    """Read all cached responses for a community/year combination."""
    responses = []
    for category in self.categories:
        response = self.read(community_id, year, category)
        if response:
            responses.append(response)
    return responses
```

##### Update
```python
def update(self, community_id, year, category, data):
    """Update a cached response with new data."""
    response = CachedResponse(community_id, year, category)
    response._data = data
    response._created_at = datetime.now()
    response._expires_at = response._created_at + timedelta(days=30)
    return response.save_to_cache()
```

##### Delete
```python
def delete(self, community_id, year, category=None):
    """Delete cached response(s)."""
    if category:
        # Delete specific category
        response = CachedResponse(community_id, year, category)
        return response.delete_from_cache()
    else:
        # Delete all categories for community/year
        results = []
        for cat in self.categories:
            response = CachedResponse(community_id, year, cat)
            results.append(response.delete_from_cache())
        return all(results)
```

##### Exists
```python
def exists(self, community_id, year, category):
    """Check if a cached response exists."""
    response = CachedResponse(community_id, year, category)
    return response.load_from_cache()
```

##### List
```python
def list(self, community_id=None, year=None, category=None):
    """List cached responses with optional filters."""
    # This would need to be implemented based on how we track cached responses
    # Could use Redis keys pattern matching or a separate tracking mechanism
    pass
```

#### Helper Methods

##### Input Normalization
```python
def _normalize_community_ids(self, community_ids):
    """Convert various inputs to list of community IDs."""
    if community_ids == 'all':
        return self._get_all_community_ids()
    elif isinstance(community_ids, str):
        return [community_ids]
    else:
        return community_ids

def _normalize_years(self, years, community_ids):
    """Convert various inputs to list of years."""
    if years == 'auto':
        return self._get_years_since_creation(community_ids)
    elif isinstance(years, int):
        return [years]
    else:
        return years

def _get_all_community_ids(self):
    """Get all community IDs from existing community model."""
    # Use existing community model methods
    from invenio_communities.models import Community
    return [str(c.id) for c in Community.query.all()]

def _get_years_since_creation(self, community_ids):
    """Get years since creation for given communities."""
    years = set()
    current_year = datetime.now().year

    for community_id in community_ids:
        if community_id == 'global':
            # For global, use a reasonable range
            years.update(range(2020, current_year + 1))
        else:
            # Get community creation year
            creation_year = self._get_community_creation_year(community_id)
            years.update(range(creation_year, current_year + 1))

    return sorted(list(years))

def _get_community_creation_year(self, community_id):
    """Get the creation year for a community."""
    from invenio_communities.models import Community
    community = Community.query.get(community_id)
    if community:
        return community.created.year
    return 2020  # Default fallback
```

##### Response Generation
```python
def _generate_all_response_objects(self, community_ids, years):
    """Generate CachedResponse objects for all combinations."""
    responses = []

    for community_id in community_ids:
        for year in years:
            for category in self.categories:
                response = CachedResponse(community_id, year, category)
                responses.append(response)

    return responses
```

##### Execution Methods
```python
def _create_sync(self, responses):
    """Create responses synchronously."""
    results = {
        'success': 0,
        'failed': 0,
        'errors': [],
        'responses': []
    }

    for response in responses:
        try:
            response.generate_content()
            response.save_to_cache()
            results['success'] += 1
            results['responses'].append(response)
        except Exception as e:
            results['failed'] += 1
            results['errors'].append({
                'community_id': response.community_id,
                'year': response.year,
                'category': response.category,
                'error': str(e)
            })

    return results

def _create_async(self, responses):
    """Create responses asynchronously using Celery tasks."""
    from invenio_stats_dashboard.tasks.cache_tasks import generate_cached_response_task

    task_ids = []
    for response in responses:
        task = generate_cached_response_task.delay(
            response.community_id,
            response.year,
            response.category
        )
        task_ids.append(task.id)

    return {
        'async': True,
        'task_count': len(task_ids),
        'task_ids': task_ids
    }
```

### 3. Celery Tasks (`tasks/cache_tasks.py`)

**Purpose**: Background processing for cache generation, delegating to CachedResponse.

#### Task Definition
```python
from celery import shared_task
from invenio_stats_dashboard.models.cached_response import CachedResponse

@shared_task
def generate_cached_response_task(community_id, year, category):
    """Generate a single cached response using CachedResponse."""
    try:
        response = CachedResponse(community_id, year, category)
        response.generate_content()
        response.save_to_cache()

        return {
            'success': True,
            'community_id': community_id,
            'year': year,
            'category': category,
            'cache_key': response.cache_key
        }
    except Exception as e:
        return {
            'success': False,
            'community_id': community_id,
            'year': year,
            'category': category,
            'error': str(e)
        }

@shared_task
def generate_batch_cache_task(community_year_category_triples):
    """Generate multiple cached responses in batch."""
    results = []
    for community_id, year, category in community_year_category_triples:
        result = generate_cached_response_task(community_id, year, category)
        results.append(result)
    return results
```

### 4. CLI Commands (`cli/cache_commands.py`)

**Purpose**: Thin interface to service layer with comprehensive argument handling.

#### Command Definition
```python
import click
from invenio_stats_dashboard.services.cached_response_service import CachedResponseService

@click.command()
@click.option('--community-id', multiple=True, help='Community ID(s)')
@click.option('--community-slug', multiple=True, help='Community slug(s)')
@click.option('--year', type=int, help='Single year')
@click.option('--years', help='Year range (e.g., 2020-2023)')
@click.option('--all-years', is_flag=True, help='All years since community creation')
@click.option('--async', 'async_mode', is_flag=True, help='Run asynchronously')
@click.option('--force', is_flag=True, help='Overwrite existing cache')
@click.option('--dry-run', is_flag=True, help='Show what would be done')
def generate(community_id, community_slug, year, years, all_years, async_mode, force, dry_run):
    """Generate cached stats responses for all data series categories."""

    # Resolve slugs to IDs
    community_ids = list(community_id)
    for slug in community_slug:
        community_ids.append(resolve_slug_to_id(slug))

    # Determine years
    if all_years:
        years_param = 'auto'
    elif years:
        years_param = parse_year_range(years)
    elif year:
        years_param = [year]
    else:
        years_param = 'auto'  # Default to all years

    # Create service and execute
    service = CachedResponseService()

    if dry_run:
        # Show what would be done
        show_dry_run_results(community_ids, years_param, service.categories)
    else:
        # Execute
        results = service.create(
            community_ids=community_ids,
            years=years_param,
            force=force,
            async_mode=async_mode
        )

        # Report results
        report_results(results)
```

#### Helper Functions
```python
def resolve_slug_to_id(slug):
    """Resolve community slug to ID using existing community model."""
    from invenio_communities.models import Community
    community = Community.query.filter_by(slug=slug).first()
    if community:
        return str(community.id)
    raise click.ClickException(f"Community with slug '{slug}' not found")

def parse_year_range(year_range):
    """Parse year range string (e.g., '2020-2023') into list."""
    try:
        start, end = map(int, year_range.split('-'))
        return list(range(start, end + 1))
    except ValueError:
        raise click.ClickException(f"Invalid year range format: {year_range}")

def show_dry_run_results(community_ids, years, categories):
    """Show what would be done in dry-run mode."""
    total_combinations = len(community_ids) * len(years) * len(categories)
    click.echo(f"Would generate {total_combinations} cached responses:")
    click.echo(f"  Communities: {len(community_ids)}")
    click.echo(f"  Years: {len(years)}")
    click.echo(f"  Categories: {len(categories)}")

def report_results(results):
    """Report execution results."""
    if results.get('async'):
        click.echo(f"✅ Cache generation started in background")
        click.echo(f"📋 Task IDs: {results['task_ids']}")
    else:
        click.echo(f"✅ Cache generation completed")
        click.echo(f"📊 Success: {results['success']}, Failed: {results['failed']}")
        if results['errors']:
            click.echo("❌ Errors:")
            for error in results['errors']:
                click.echo(f"  {error['community_id']}/{error['year']}/{error['category']}: {error['error']}")
```

## Existing Logic Integration

### Leveraging Existing Cache Utils
- **`_generate_response_cache_key()`**: Used in `CachedResponse._generate_cache_key()`
- **`_get_cached_response()`**: Used in `CachedResponse.load_from_cache()`
- **`_set_cached_response()`**: Used in `CachedResponse.save_to_cache()`
- **`_clear_cached_response()`**: Used in `CachedResponse.delete_from_cache()`

### Leveraging Existing API Logic
- **`StatsDashboardAPIResource._generate_stats_response()`**: Used in `CachedResponse.generate_content()`

### Leveraging Existing Community Model
- **`Community.query.all()`**: Used in `CachedResponseService._get_all_community_ids()`
- **`Community.query.get()`**: Used in `CachedResponseService._get_community_creation_year()`
- **`Community.query.filter_by(slug=slug)`**: Used in CLI `resolve_slug_to_id()`

## Data Series Categories

The system will generate cached responses for all of these categories:
- `record_delta`
- `record_snapshot`
- `usage_delta`
- `usage_snapshot`
- `record_delta_data_added`
- `record_delta_data_removed`
- `usage_delta_data_views`
- `usage_delta_data_downloads`

## Example Usage

```bash
# Single community, single year
community-stats cache generate --community-id 123 --year 2023

# Multiple communities, year range
community-stats cache generate --community-id 123 --community-id 456 --years 2020-2023

# All communities, all years since creation
community-stats cache generate --all-years

# Global stats for specific years
community-stats cache generate --community-id global --years 2020-2023

# Async execution
community-stats cache generate --community-id 123 --year 2023 --async

# Dry run
community-stats cache generate --community-id 123 --year 2023 --dry-run
```

## Implementation Phases

### Phase 1: Core Domain Model
1. Create `CachedResponse` class with cache key generation
2. Implement content generation using existing API logic
3. Add cache operations using existing cache_utils
4. Create unit tests

### Phase 2: Service Layer
1. Create `CachedResponseService` with CRUD methods
2. Implement input normalization and validation
3. Add batch processing capabilities
4. Create integration tests

### Phase 3: Celery Integration
1. Create cache generation tasks
2. Implement async processing
3. Add task monitoring and error handling
4. Create task tests

### Phase 4: CLI Interface
1. Create command structure with comprehensive options
2. Implement argument parsing and validation
3. Add reporting and dry-run functionality
4. Create CLI tests

### Phase 5: Integration and Testing
1. End-to-end testing
2. Performance optimization
3. Documentation
4. Deployment preparation

## Notes

- All cache operations use existing `cache_utils.py` methods
- Content generation uses existing `StatsDashboardAPIResource` logic
- Community operations use existing `Community` model methods
- The system generates responses for all data series categories automatically
- Cache keys are generated using existing logic to ensure consistency
- Binary JSON blobs are stored as with current caching implementation
