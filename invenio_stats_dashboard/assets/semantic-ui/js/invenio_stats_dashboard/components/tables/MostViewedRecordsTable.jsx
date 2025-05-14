import React from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsTable } from "../shared_components/StatsTable";
import { PropTypes } from "prop-types";

const MostViewedRecordsTable = ({ headers = ["Record", "Views"], rows = [
  ["file outline", "absc2341", "1000000"],
  ["file outline", "absc2342", "10000"],
  ["file outline", "absc2343", "100"],
] }) => {
  return (
    <StatsTable
      label="record"
      headers={headers}
      rows={rows}
      title={i18next.t("Most Viewed Records")}
    />
  );
};

MostViewedRecordsTable.propTypes = {
  recordViewsItems: PropTypes.array.isRequired,
};

export { MostViewedRecordsTable };