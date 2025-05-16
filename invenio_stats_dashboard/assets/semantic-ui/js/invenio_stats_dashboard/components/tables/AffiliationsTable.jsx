import React from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsTable } from "../shared_components/StatsTable";
import { PropTypes } from "prop-types";

const AffiliationsTable = ({ title = i18next.t("Content by Institution"), icon: labelIcon = "university", headers = [i18next.t("Institution"), i18next.t("Records")], rows = [
  ["university", "Harvard University", "3,456", "harvard"],
  ["university", "MIT", "3,210", "mit"],
  ["university", "Stanford University", "2,987", "stanford"],
  ["university", "University of Oxford", "2,765", "oxford"],
  ["university", "ETH Zurich", "2,543", "eth"]
] }) => {
  const rowsWithLinks = rows.map(([icon, label, count, id]) => [
    icon,
    <a href={`/search?q=metadata.affiliations.id:${id}`} target="_blank" rel="noopener noreferrer">{label}</a>,
    count
  ]);

  return (
    <StatsTable
      label="affiliations"
      headers={headers}
      rows={rowsWithLinks}
      title={title}
      labelIcon={labelIcon}
    />
  );
};

AffiliationsTable.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  rows: PropTypes.array,
};

export { AffiliationsTable };
