## Usage

### Enabling the global dashboard template

A Jinja2 template for the global dashboard, registered as a top-level page template at the global stats dashboard route (`/stats` by default). A top-level menu item is registered for this template by default, but can be disabled by setting the `STATS_DASHBOARD_MENU_ENABLED` configuration variable to `False`. The text and position of the menu item can be configured via config variables. Alternately, a custom function can be provided to register the menu item (See [Configuration](#configuration) below for more information.)

### Enabling the community dashboard template

A Jinja2 template for the community dashboard page content, intended to be used as a sub-page of the community details page. This is registered with the community stats dashboard route (`/communities/<community_id>/stats` by default).

To implement this in your community details page, you can add a menu tab to the community details page template linking to this template route.

### Blueprints and routes

The module provides a blueprint `invenio_stats_dashboard.blueprint` that is registered with the following routes:

- `/stats` - the global dashboard.
- `/communities/<community_id>/stats` - the community dashboard.

These default routes are set via the `STATS_DASHBOARD_ROUTES` configuration variable and can be overridden.

### Customizing the layout of your dashboard

The layout and pagination of the stats dashboards is intended to be highly customizable via
the `STATS_DASHBOARD_LAYOUT` configuration variable. This is a dictionary that maps dashboard types (currently `global` and `community` are available) to layout configurations. Each layout configuration is a dictionary that maps dashboard sections to a list of components to display in that section.

- Tabs can be specified to group dashboard pages, navigated between using a menu at the side
- Rows can be specified to group components together, and component widths can be specified with a "width" key.
- Individual components of the layout are React components that are configurable via the `props` key.
    - specify, e.g., the title, number of items to display in the view, etc.

```{note}
The plan is to provide a way to register additional React components via an entry point, so that they can be used in the layout configuration.
```

```{note}
We will also be using ReactOverridable to allow overriding of the default React components. This will include the overall dashboard frame layout (with menu, sidebar, and main content areas) as well as individual metrics components.
```

#### Layout Configuration Structure

The `STATS_DASHBOARD_LAYOUT` configuration follows this structure:

```python
STATS_DASHBOARD_LAYOUT = {
    "global": {
        "tabs": [
            {
                "name": "tab_identifier",
                "label": "Tab Display Name",
                "icon": "semantic-ui-icon-name",
                "date_range_phrase": "Date range description",
                "rows": [
                    {
                        "name": "row_identifier",
                        "components": [
                            {
                                "component": "ComponentName",
                                "width": 16,  # Grid width (1-16)
                                "props": {
                                    "title": "Component Title",
                                    "height": 300,
                                    "pageSize": 10,
                                    # ... other component-specific props
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    }
}
```

#### Available Components

The dashboard supports several categories of components:

**Single Statistics Components:**

These are single numerical metrics much like the ones provided at the top of the default record stats display for view and download counts.

Several built-in single-statistic components give numerical counts for some metric during a given period of time. The time period is dictated by the dashboard global date range selector.

- `SingleStatRecordCount` - Number of records added during a period
- `SingleStatUploaders` - Number of active uploaders during a period
- `SingleStatDataVolume` - Volume of downloaded data during a period
- `SingleStatViews` - Number of unique views during a period
- `SingleStatDownloads` - Number of unique downloads during a period
- `SingleStatTraffic` - Volume of data downloaded during a period

The other category of built-in single-statistic components give cumulative totals for some metric by a given date. The date is the end point of the range selected in the dashboard global date range selector.

- `SingleStatRecordCountCumulative` - Cumulative total number of records added by a given date
- `SingleStatUploadersCumulative` - Cumulative total number of unique uploaders by a date
- `SingleStatDataVolumeCumulative` - Cumulative total volume of downloaded data by a given date
- `SingleStatViewsCumulative` - Cumulative total number of unique views by a given date
- `SingleStatDownloadsCumulative` - Cumulative total number of unique downloads by a given date
- `SingleStatTrafficCumulative` - Cumulative total volume of data downloaded by a given date

Both categories of single-statistic components all inherit from the abstract `SingleStatBox` component, which can be used to construct other single-statistic components.

**Chart Components:**

These are bar or line charts (rendered by Apache ECharts) that show time series data. The time period is dictated by the dashboard global date range selector. The granularity of the data points displayed (day, week, month, quarter, year) is dictated by the dashboard global granularity selector.

The default charts visualize the four different types of aggregation series:

- `ContentStatsChart` - Daily record deltas (additional records, files, uploaders, and data volume during each period)
- `ContentStatsChartCumulative` - Daily record snapshots (cumulative totals of records, files, uploaders, and data volume as of each date)
- `TrafficStatsChart` - Usage deltas (additional views, downloads, and data volume each period)
- `TrafficStatsChartCumulative` - Usage snapshots (cumulative totals of views, downloads, and data volume as of each date)

The "display separately" filter in each one can be configured to allow dynamic display of any breakdown configured for the extension. We could allow only breakdowns by resource type, file type, and funder, for example:

```python
{
    "component": "ContentStatsChart",
    "width": 16,
    "props": {
        "height": 300,
        "title": "Cumulative Content Totals",
        "display_subcounts": ["resource_types", "file_types", "funders"],
    },
}
```

These all inherit from the abstract `StatsChart` component, which can be used to construct other chart components.

**Multi-Display Components:**

The multi-display components show a single metric broken down by one of the configured subcount types (e.g., top resource types by cumulative record count, top subjects by views during a period, etc.). They display as a box with a title, icon, and controls to switch the visualization type on the fly. The available visualization types are:

- text table
- pie chart
- bar chart

The default visualization type, as well as which visualization types are available, can be configured separately for each multi-display component via component props. For example, I could specify in my layout that I want to display the top resource types by cumulative record count, with:

- the pie chart as the default visualization type
- only the table as an alternate available visualization type (hiding the bar chart option)
- displaying only the top 10 items

```python
{
    "component": "ResourceTypesMultiDisplay",
    "width": 8,
    "props": {
        "title": "Top Resource Types",
        "pageSize": 10,
        "available_views": ["bar", "list"],
        "default_view": "pie",
    },
}
```

If I wish to display just one visualization type, with no selection controls, I can set the `available_views` prop to an array containing only the desired visualization type.

Currently, all of the build-in multi-display components provide counts *for the period selected in the dashboard global date range selector*. We plan to add multi-display components that provide cumulative totals *as of the end of the range selected in the dashboard global date range selector*.

Several of the built-in multi-display components are offer record counts broken down by a metadata field:

- `ResourceTypesMultiDisplay` - Record counts by resource type
- `SubjectsMultiDisplay` - Record counts by subject
- `AccessStatusesMultiDisplay` - Record counts by access status
- `RightsMultiDisplay` - Record counts by rights/licenses
- `AffiliationsMultiDisplay` - Record counts by affiliation
- `FundersMultiDisplay` - Record counts by funder
- `PeriodicalsMultiDisplay` - Record counts by periodical
- `PublishersMultiDisplay` - Record counts by publisher
- `TopLanguagesMultiDisplay` - Record counts by language
- `FileTypesMultiDisplay` - Record counts by file type

Other built-in multi-display components offer top lists of values broken down by view or download event data:

- `TopCountriesMultiDisplay` - Top countries by visits
- `TopReferrersMultiDisplay` - Top referrer domains
- `MostDownloadedRecordsMultiDisplay` - Most downloaded records
- `MostViewedRecordsMultiDisplay` - Most viewed records

**Map Components:**

A map component is also available to display the geographic distribution of record viewers:

- `StatsMap` - Interactive world map showing geographic distribution

This can be added to the layout like this:

```python
{
    "component": "StatsMap",
    "width": 16,
    "props": {
        "title": "Top Countries by Visits",
        "height": 400,
        "minHeight": 400,
        "zoom": 1.3,
        "center": [0, 20],
    },
}
```

The plan is to add an additional map component to display the geographic distribution of downloaders.

#### Component Properties

Each component accepts various properties through the `props` dictionary:

**Common Properties:**
- `title` - Display title for the component
- `height` - Component height in pixels
- `pageSize` - Number of items to display per page (for tables/lists)

**Chart-Specific Properties:**
- `display_subcounts` - Array of subcount types to display (e.g., `["resource_types", "subjects"]`)

**Multi-Display Properties:**
- `available_views` - Array of available view types: `["pie", "bar", "list"]`
- `default_view` - Default view type to display

**Map-Specific Properties:**
- `minHeight` - Minimum height for the map
- `zoom` - Initial zoom level
- `center` - Map center coordinates `[latitude, longitude]`

### Global UI Configuration

The `STATS_DASHBOARD_UI_CONFIG` variable controls dashboard-wide settings:

```python
STATS_DASHBOARD_UI_CONFIG = {
    "global": {
        "title": "Statistics",
        "description": "Dashboard description",
        "maxHistoryYears": 15,
        "default_granularity": "month",
        "show_title": True,
        "show_description": False,
    },
    "community": {
        "title": "Community Statistics",
        "description": "Community dashboard description",
        "maxHistoryYears": 15,
        "default_granularity": "month",
        "show_title": True,
        "show_description": False,
    }
}
```

**UI Configuration Parameters:**
- `title` - Dashboard title
- `description` - Dashboard description text
- `maxHistoryYears` - Maximum number of years of historical data that can be selected for view
- `default_granularity` - Default time granularity (`"day"`, `"week"`, `"month"`) to display in the date range selector when the dashboard is first loaded
- `show_title` - Whether to display the dashboard title
- `show_description` - Whether to display the dashboard description

#### Customization Examples

**Example 1: Custom Global Dashboard Layout**

```python
STATS_DASHBOARD_LAYOUT = {
    "global": {
        "tabs": [
            {
                "name": "overview",
                "label": "Overview",
                "icon": "chart bar",
                "date_range_phrase": "Data as of",
                "rows": [
                    {
                        "name": "key-metrics",
                        "components": [
                            {
                                "component": "SingleStatRecordCountCumulative",
                                "width": 8,
                                "props": {"title": "Total Records", "icon": "file"}
                            },
                            {
                                "component": "SingleStatViewsCumulative",
                                "width": 8,
                                "props": {"title": "Total Views", "icon": "eye"}
                            }
                        ]
                    },
                    {
                        "name": "content-breakdown",
                        "components": [
                            {
                                "component": "ResourceTypesMultiDisplay",
                                "width": 16,
                                "props": {
                                    "title": "Content by Type",
                                    "pageSize": 15,
                                    "available_views": ["pie", "bar", "list"],
                                    "default_view": "pie"
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    }
}
```

**Example 2: Community Dashboard Layout**

```python
STATS_DASHBOARD_LAYOUT = {
    "community": {
        "tabs": [
            {
                "name": "community-stats",
                "label": "Community Statistics",
                "icon": "users",
                "date_range_phrase": "Community activity during",
                "rows": [
                    {
                        "name": "metrics",
                        "components": [
                            {
                                "component": "SingleStatRecordCount",
                                "width": 16,
                                "props": {"title": "Records Added", "icon": "plus"}
                            }
                        ]
                    }
                ]
            }
        ]
    }
}
```

**Example 3: Customizing Component Widths**

Components use a 16-column grid system. You can control layout by adjusting widths:

```python
"components": [
    {
        "component": "SingleStatRecordCount",
        "width": 4,  # Takes 1/4 of the row
        "props": {"title": "Records"}
    },
    {
        "component": "SingleStatViews",
        "width": 8,  # Takes 1/2 of the row
        "props": {"title": "Views"}
    },
    {
        "component": "SingleStatDownloads",
        "width": 4,  # Takes 1/4 of the row
        "props": {"title": "Downloads"}
    }
]
```

### Adding dashboard views to other pages

The default global and community dashboard templates are based on a Jinja2 template macro that can also be included in other templates to display an embedded dashboard view:

```html
{%- extends "invenio_theme/page.html" %}
{%- import "invenio_stats_dashboard/stats_dashboard.html" as stats_dashboard %}

{%- block page_body %}
  {{ stats_dashboard.stats_dashboard(dashboard_config, community=community) }}
{%- endblock %}
```

The macro takes the following parameters:

- `dashboard_config`: The configuration for the dashboard. This is a dictionary that maps dashboard types (currently `global` and `community`) to layout configurations.
- `community`: The community to display the dashboard for (if `dashboard_type` is `community`). [Optional. Defaults to `None`, which will display the global dashboard].

