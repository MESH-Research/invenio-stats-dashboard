import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsTable } from "../shared_components/StatsTable";
import { PropTypes } from "prop-types";

const ResourceTypesTable = ({ headers = ["Resource Type", "Records"], rows = [
  ["file", "Journal Article", "25,432", "publication-article"],
  ["file", "Dataset", "15,321", "dataset"],
  ["file", "Conference Paper", "12,210", "publication-conferencepaper"],
  ["file", "Book Chapter", "8,109", "publication-chapter"],
  ["file", "Software", "5,098", "software"]
] }) => {
  const rowsWithLinks = rows.map(([icon, label, count, id]) => [
    icon,
    <a href={`/search?q=metadata.resource_type.id:${id}`} target="_blank" rel="noopener noreferrer">{label}</a>,
    count
  ]);

  return (
    <StatsTable
      label="resource-types"
      headers={headers}
      rows={rowsWithLinks}
      title={i18next.t("Content by Resource Type")}
    />
  );
};

ResourceTypesTable.propTypes = {
  resourceTypeItems: PropTypes.array.isRequired,
};

export { ResourceTypesTable };
