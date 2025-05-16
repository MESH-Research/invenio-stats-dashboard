import React from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsTable } from "../shared_components/StatsTable";
import { PropTypes } from "prop-types";

const MostViewedRecordsTable = ({ title = i18next.t("Most Viewed Records"), icon: labelIcon = "file outline", headers = [i18next.t("Record"), i18next.t("Views")], rows = [
  ["file outline", "absc2341", "1000000"],
  ["file outline", "absc2342", "10000"],
  ["file outline", "absc2343", "100"],
] }) => {
  return (
    <StatsTable
      label="record"
      headers={headers}
      rows={rows}
      title={title}
      labelIcon={labelIcon}
    />
  );
};

MostViewedRecordsTable.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  rows: PropTypes.array,
};

export { MostViewedRecordsTable };