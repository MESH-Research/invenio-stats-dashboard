/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 */

import React from "react";
import { Message, Icon, Loader } from "semantic-ui-react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { formatCacheTimestamp } from "../../utils/statsCache";
import PropTypes from "prop-types";

/**
 * Component to display update status messages for the stats dashboard
 * Shows either "updating" with spinner or "last updated" with timestamp
 */
const UpdateStatusMessage = ({
  isUpdating,
  lastUpdated,
  className = "",
  size = "small"
}) => {
  if (!isUpdating && !lastUpdated) {
    return null;
  }

  return (
    <div
      className={`stats-update-status ${className}`}
      data-testid="update-status-message"
    >
      {isUpdating ? (
        <div className="stats-updating-container">
          <Loader active inline size="mini" />
          <span className="stats-updating-text">
            {i18next.t("Updating data...")}
          </span>
        </div>
      ) : (
        <div className="stats-last-updated-container">
          <Icon name="clock outline" />
          <span className="stats-last-updated-text">
            {i18next.t("Last updated: {{timestamp}}", {
              timestamp: formatCacheTimestamp(lastUpdated)
            })}
          </span>
        </div>
      )}
    </div>
  );
};

UpdateStatusMessage.propTypes = {
  isUpdating: PropTypes.bool,
  lastUpdated: PropTypes.number,
  className: PropTypes.string,
  size: PropTypes.oneOf(["mini", "tiny", "small", "large", "big", "huge", "massive"])
};

export { UpdateStatusMessage };
