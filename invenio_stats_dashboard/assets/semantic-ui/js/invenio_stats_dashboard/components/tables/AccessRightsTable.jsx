import React from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsTable } from "../shared_components/StatsTable";
import { PropTypes } from "prop-types";

const AccessRightsTable = ({
  title = i18next.t("Content by Access Rights"),
  icon: labelIcon = "lock",
  headers = [i18next.t("Access Rights"), i18next.t("Records")],
  rows = [
    [null, "Open Access", "45,432", "open"],
    [null, "Restricted Access", "15,321", "restricted"],
    [null, "Embargoed Access", "12,210", "embargoed"],
    [null, "Metadata Only", "8,109", "metadata-only"],
    [null, "Closed Access", "5,098", "closed"],
  ],
}) => {
  const rowsWithLinks = rows.map(([icon, label, count, id]) => [
    icon,
    <a
      href={`/search?q=metadata.access_rights.id:${id}`}
      target="_blank"
      rel="noopener noreferrer"
    >
      {label}
    </a>,
    count,
  ]);

  return (
    <StatsTable
      label="access-rights"
      headers={headers}
      rows={rowsWithLinks}
      title={title}
      labelIcon={labelIcon}
    />
  );
};

AccessRightsTable.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  rows: PropTypes.array,
};

export { AccessRightsTable };
