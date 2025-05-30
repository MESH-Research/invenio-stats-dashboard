import React from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsTable } from "../shared_components/StatsTable";
import { PropTypes } from "prop-types";

const FundersTable = ({ title = i18next.t("Content by Funder"), icon: labelIcon = "money bill alternate", headers = [i18next.t("Funder"), i18next.t("Records")], rows = [
  ["money bill alternate", "National Science Foundation", "5,432", "nsf"],
  ["money bill alternate", "European Research Council", "4,321", "erc"],
  ["money bill alternate", "National Institutes of Health", "3,210", "nih"],
  ["money bill alternate", "Wellcome Trust", "2,109", "wellcome"],
  ["money bill alternate", "Bill & Melinda Gates Foundation", "1,098", "gates"]
] }) => {
  const rowsWithLinks = rows.map(([icon, label, count, id]) => [
    icon,
    <a href={`/search?q=metadata.funders.id:${id}`} target="_blank" rel="noopener noreferrer">{label}</a>,
    count
  ]);

  return (
    <StatsTable
      label="funders"
      headers={headers}
      rows={rowsWithLinks}
      title={title}
      labelIcon={labelIcon}
    />
  );
};

FundersTable.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  rows: PropTypes.array,
};

export { FundersTable };
