import React from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { Segment, Dropdown } from "semantic-ui-react";
import PropTypes from "prop-types";

const GRANULARITY_OPTIONS = [
  { key: "day", text: i18next.t("Day"), value: "day" },
  { key: "week", text: i18next.t("Week"), value: "week" },
  { key: "month", text: i18next.t("Month"), value: "month" },
  { key: "quarter", text: i18next.t("Quarter"), value: "quarter" },
  { key: "year", text: i18next.t("Year"), value: "year" },
];

const GranularitySelector = ({ defaultGranularity, granularity, setGranularity }) => {
  const handleGranularityChange = (e, { value }) => {
    setGranularity(value);
  };

  return (
    <Segment className="stats-dashboard-granularity-selector rel-mt-1 rel-mb-1 communities-detail-stats-sidebar-segment">
      <label
        id="stats-dashboard-granularity-label"
        htmlFor="stats-dashboard-granularity-dropdown"
        className="stats-dashboard-field-label"
      >
        {i18next.t("aggregated by")}
      </label>
      <Dropdown
        id="stats-dashboard-granularity-dropdown"
        className="stats-dashboard-granularity-dropdown"
        fluid
        selection
        value={granularity || defaultGranularity}
        onChange={handleGranularityChange}
        options={GRANULARITY_OPTIONS}
      />
    </Segment>
  );
};

GranularitySelector.propTypes = {
  defaultGranularity: PropTypes.string,
  granularity: PropTypes.string.isRequired,
  setGranularity: PropTypes.func.isRequired,
};

export { GranularitySelector, GRANULARITY_OPTIONS };
