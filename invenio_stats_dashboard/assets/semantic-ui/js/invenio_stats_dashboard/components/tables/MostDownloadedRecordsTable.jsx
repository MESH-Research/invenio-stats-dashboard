import React from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsTable } from "../shared_components/StatsTable";
import { PropTypes } from "prop-types";

const MostDownloadedRecordsTable = ({ title = i18next.t("Most Downloaded Records"), icon: labelIcon = "file outline", headers = [i18next.t("Record"), i18next.t("Downloads")], rows = [
  ["file outline", "absc2341", "500000"],
  ["file outline", "absc2342", "5000"],
  ["file outline", "absc2343", "50"],
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

MostDownloadedRecordsTable.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  rows: PropTypes.array,
};

export { MostDownloadedRecordsTable };