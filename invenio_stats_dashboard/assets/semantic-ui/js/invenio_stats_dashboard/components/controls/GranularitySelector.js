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

/**
 * GranularitySelector component to select the aggregation granularity
 *
 * Options are "day", "week", "month", "quarter", "year"
 *
 * The granularity state is managed by the parent component and made available
 * via the context.
 *
 * FIXME: There is a bug in the semantic-ui-react library that causes the
 * dropdown to not close once the menu is opened. Currently we are using
 * a javascript workaround to close the menu when the dropdown is blurred.
 *
 * @param {Object} props - The component props
 * @param {string} props.defaultGranularity - The default granularity
 * @param {string} props.granularity - The current granularity
 * @param {Function} props.setGranularity - The function to set the granularity
 */
const GranularitySelector = ({ defaultGranularity, granularity, setGranularity }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedOption, setSelectedOption] = useState(granularity || defaultGranularity);

  const handleGranularityChange = (e, { value }) => {
    setSelectedOption(value);
    setGranularity(value);
  };

  useEffect(() => {
    setSelectedOption(granularity || defaultGranularity);
  }, [granularity, defaultGranularity]);

  const handleMenuOpen = () => {
    setIsOpen(true);
    const menuElement = document.querySelector('.stats-dashboard-granularity-selector');
    if (menuElement) {
      menuElement.style.position = 'relative';
      menuElement.style.zIndex = '1000';
    }
  };

  const handleMenuClose = () => {
    setIsOpen(false);
    setTimeout(() => {
      const selectorElement = document.querySelector('.stats-dashboard-granularity-selector');
      const menuElement = document.querySelector('.stats-dashboard-granularity-selector .menu');
      if (menuElement) {
        menuElement.style = '';
      }
      if (selectorElement) {
        selectorElement.style = '';
      }
    }, 100);
  };

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
        openOnFocus={false}
        onOpen={handleMenuOpen}
        onClose={handleMenuClose}
        onBlur={handleMenuClose}
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
