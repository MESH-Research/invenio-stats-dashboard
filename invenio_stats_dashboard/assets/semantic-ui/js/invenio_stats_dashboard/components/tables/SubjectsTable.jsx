import React from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsTable } from "../shared_components/StatsTable";
import { PropTypes } from "prop-types";

const SubjectsTable = ({ title = i18next.t("Content by Subject"), icon: labelIcon = "book", headers = [i18next.t("Subject"), i18next.t("Records")], rows = [
  ["book", "Computer Science", "15,432", "computer-science"],
  ["book", "Physics", "12,345", "physics"],
  ["book", "Biology", "10,987", "biology"],
  ["book", "Chemistry", "9,876", "chemistry"],
  ["book", "Mathematics", "8,765", "mathematics"]
] }) => {
  const rowsWithLinks = rows.map(([icon, label, count, id]) => [
    icon,
    <a href={`/search?q=metadata.subjects.id:${id}`} target="_blank" rel="noopener noreferrer">{label}</a>,
    count
  ]);

  return (
    <StatsTable
      label="subjects"
      headers={headers}
      rows={rowsWithLinks}
      title={title}
      labelIcon={labelIcon}
    />
  );
};

SubjectsTable.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  rows: PropTypes.array,
};

export { SubjectsTable };
