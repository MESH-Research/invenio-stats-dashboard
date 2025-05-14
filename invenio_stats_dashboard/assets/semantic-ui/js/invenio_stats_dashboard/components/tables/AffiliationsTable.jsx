import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsTable } from "../shared_components/StatsTable";
import { PropTypes } from "prop-types";

const AffiliationsTable = ({ headers = ["Institution", "Records"], rows = [
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
      title={i18next.t("Content by Institution")}
    />
  );
};

AffiliationsTable.propTypes = {
  affiliationItems: PropTypes.array.isRequired,
};

export { AffiliationsTable };
