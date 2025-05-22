import React, { useEffect, useState } from "react";
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
  const [isOpen, setIsOpen] = useState(false);
  const [selectedOption, setSelectedOption] = useState(granularity || defaultGranularity);

  const handleGranularityChange = (e, { value }) => {
    setSelectedOption(value);
    setGranularity(value);
    setIsOpen(false);
  };

  useEffect(() => {
    setSelectedOption(granularity || defaultGranularity);
  }, [granularity, defaultGranularity]);

  return (
    <Segment className="stats-dashboard-granularity-selector rel-mt-1 rel-mb-1 communities-detail-stats-sidebar-segment">
      <label
        id="granularity-selector-label"
        htmlFor="granularity-selector"
        className="stats-dashboard-field-label"
      >
        {i18next.t("aggregated by")}
      </label>
      <Dropdown
        id="granularity-selector"
        className="stats-dashboard-granularity-selector"
        fluid
        selection
        value={selectedOption}
        onChange={handleGranularityChange}
        options={GRANULARITY_OPTIONS}
        open={isOpen}
        closeOnBlur={true}
        closeOnChange={false}
        selectOnBlur={true}
        onOpen={() => setIsOpen(true)}
        onClose={() => {
          console.log("closing");
          setIsOpen(false);

          // Clear menu styles after a delay
          setTimeout(() => {
            const menuElement = document.querySelector('.stats-dashboard-granularity-selector .menu');
            if (menuElement) {
              menuElement.style = '';
            }
          }, 100);
        }}
        onBlur={() => {
          console.log("blur");

          // Clear menu styles after a delay
          setTimeout(() => {
            const menuElement = document.querySelector('.stats-dashboard-granularity-selector .menu');
            if (menuElement) {
              menuElement.style = '';
            }
          }, 100);
        }}
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
