import React, { useState } from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { Header, Segment, Icon, Button } from "semantic-ui-react";
import { PropTypes } from "prop-types";
import ReactECharts from "echarts-for-react";
import { StatsTable } from "./StatsTable";

const VIEW_MODE_ICON_MAP = {
  list: "list",
  line: "chart line",
  bar: "chart bar",
  pie: "pie chart",
  map: "map",
};

/** A component that displays a data series in a variety of views.
 *
 * Allows for a data series to be displayed in a table or a variety of chart views
 * with the ability to switch between views.
 *
 * The display modes are defined by the `chartOptions` object. If a simple table
 * view is desired as one view mode, a "list" key should be included in the object
 * and the value can be an empty object.
 *
 * Other views (various chart types) are defined by the remaining keys in
 * the `chartOptions` object. Each key is a view mode and the corresponding value
 * is the chart `option` object for the view mode.
 *
 * The view modes are defined by the `VIEW_MODE_ICON_MAP` object. The keys are
 * the view modes and the values are the icon names for the view modes. These are
 * also the valid values for the `type` property of the chart `option` object.
 *
 * Data for each chart view is provided in the `option` value for the view mode.
 * Data for the table view is provided in the `rows` array. This is an array of
 * arrays, where each item is an array representing a row in the table. The first
 * column in each row is used for the icon if an icon is desired. Other values in
 * each row can contain either a string, a number, or a React component to be
 * rendered in the corresponding table cell.
 *
 * @param {string} title - The display title for the widget.
 * @param {string} icon - The icon to display next to the title in the widget
 *      header. (Optional)
 * @param {string} label - The label of the data series.
 * @param {string[][]} headers - The headers for the table view of the data series.
 *      If the rows include an icon that column is not included in the headers array.
 *      Otherwise, the headers should match the number of columns in the rows array.
 * @param {string[][]} rows - The rows of the data series formatted for the table view.
 *      If the rows should include an icon for each item in the table display,
 *      the first column should be the icon name. Otherwise, the rows should
 *      match the number of columns in the headers array.
 * @param {object} chartOptions - An object containing the chart options for
 *      configuring the chart view of the data series. The keys are the view modes
 *      and the values are the chart options for the view mode.
 * @param {string} defaultViewMode - The default view mode of the data series.
 *      Defaults to "list".
 * @param {object} onEvents - The events to be passed to ReactECharts.
*/
const StatsMultiDisplay = ({ title, icon: labelIcon, label, headers, rows, chartOptions, defaultViewMode = "list", onEvents }) => {
  const [viewMode, setViewMode] = useState(defaultViewMode);
  const availableViewModes = Object.keys(chartOptions);
  const tableLabel = label ? label : title ? title.toLowerCase().replace(/\s+/g, "-") : "stats";

  const handleViewChange = (mode) => {
    setViewMode(mode);
  };

  // Add aria.enabled to all chart options
  const enhancedChartOptions = Object.fromEntries(
    Object.entries(chartOptions).map(([key, value]) => [
      key,
      {
        ...value,
        aria: {
          enabled: true
        }
      }
    ])
  );

  return (
    <div
      className={`stats-multi-display-container ${tableLabel}-stats-multi-display-container rel-mb-1 rel-mt-1`}
      role="region"
      aria-label={title}
    >
      {title && (
        <Header as="h3" id={`${tableLabel}-stats-multi-display-header`} className="stats-multi-display-header" attached="top">
          {labelIcon && <Icon name={labelIcon} className="stats-multi-display-icon" aria-hidden="true" size="small" />}
          {availableViewModes.length > 1 && availableViewModes.map((mode) => (
            <Button
              key={mode}
              active={viewMode === mode}
              onClick={() => handleViewChange(mode)}
              aria-label={i18next.t(mode)}
              size="small"
              toggle
            >
              <Icon fitted name={VIEW_MODE_ICON_MAP[mode]} />
            </Button>
          ))}
          {title}
        </Header>
      )}
      <Segment attached>
        {viewMode === "list" ? (
          <StatsTable
            label={`${tableLabel}-table`}
            headers={headers}
            rows={rows}
            labelIcon={labelIcon}
          />
        ) : (
          <ReactECharts
            option={enhancedChartOptions[viewMode]}
            notMerge={true}
            style={{ height: '300px' }}
            className={`${tableLabel}-${viewMode}-chart`}
            onEvents={onEvents}
          />
        )}
      </Segment>
    </div>
  );
};

StatsMultiDisplay.propTypes = {
  title: PropTypes.string.required,
  icon: PropTypes.string,
  label: PropTypes.string,
  headers: PropTypes.array.required,
  rows: PropTypes.array.required,
  chartOption: PropTypes.object,
  onEvents: PropTypes.object,
};

export { StatsMultiDisplay };