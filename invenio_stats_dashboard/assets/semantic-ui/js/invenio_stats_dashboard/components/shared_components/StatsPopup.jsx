import React from 'react';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { formatNumber } from "../../utils/numbers";

const StatsPopup = ({ number, compactThreshold }) => {
  const localizedNumber = formatNumber(number, 'default');
  const compactNumber = formatNumber(number, 'compact', { compactThreshold });
  return localizedNumber !== compactNumber ? (
    <div>
      <span
        tabindex="0"
        role="button"
        className="popup-trigger compact-number"
        aria-expanded="false"
        aria-label={ i18next.t("See the full number") }
        data-variation="mini"
      >
        { compactNumber }
      </span>
      <p role="tooltip" className="popup-content ui flowing popup transition hidden">
        { localizedNumber }
      </p>
    </div>
  ) : (
    localizedNumber
  );
};

export { StatsPopup };
