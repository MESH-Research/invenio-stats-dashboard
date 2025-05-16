import React from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsTable } from "../shared_components/StatsTable";
import { PropTypes } from "prop-types";

const LicensesTable = ({ title = i18next.t("Content by License"), icon: labelIcon = "copyright", headers = [i18next.t("License"), i18next.t("Records")], rows = [
  ["copyright", "Creative Commons Attribution 4.0", "35,432", "cc-by-4.0"],
  ["copyright", "Creative Commons Attribution-NonCommercial 4.0", "15,321", "cc-by-nc-4.0"],
  ["copyright", "Creative Commons Attribution-ShareAlike 4.0", "12,210", "cc-by-sa-4.0"],
  ["copyright", "Creative Commons Zero 1.0", "8,109", "cc0-1.0"],
  ["copyright", "All Rights Reserved", "5,098", "arr"]
] }) => {
  const rowsWithLinks = rows.map(([icon, label, count, id]) => [
    icon,
    <a href={`/search?q=metadata.rights.id:${id}`} target="_blank" rel="noopener noreferrer">{label}</a>,
    count
  ]);

  return (
    <StatsTable
      label="licenses"
      headers={headers}
      rows={rowsWithLinks}
      title={title}
      labelIcon={labelIcon}
    />
  );
};

LicensesTable.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  rows: PropTypes.array,
};

export { LicensesTable };
