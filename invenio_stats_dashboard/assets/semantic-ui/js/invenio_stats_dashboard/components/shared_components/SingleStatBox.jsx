import React from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { Statistic, Icon } from "semantic-ui-react";
import { PropTypes } from "prop-types";

const SingleStatBox = ({ title, value, icon = undefined, description }) => {
  const descriptionId = description ? `${title.toLowerCase().replace(/\s+/g, '-')}-description` : null;

  return (
    <Statistic
      className="stats-single-stat-container centered"
      role="region"
      aria-label={title}
      aria-describedby={descriptionId}
    >
      <Statistic.Value aria-label={`${value} ${title}`}>
        {value}
      </Statistic.Value>
      <Statistic.Label className="stats-single-stat-header">
        {icon && <Icon name={icon} aria-hidden="true" />}
        {title}
      </Statistic.Label>
      {description && (
        <Statistic.Label
          id={descriptionId}
          className="stats-single-stat-description"
          aria-label={description}
        >
          {description}
        </Statistic.Label>
      )}
    </Statistic>
  );
};

SingleStatBox.propTypes = {
  title: PropTypes.string.isRequired,
  value: PropTypes.string.isRequired,
  icon: PropTypes.string,
  description: PropTypes.string,
};

export { SingleStatBox };
