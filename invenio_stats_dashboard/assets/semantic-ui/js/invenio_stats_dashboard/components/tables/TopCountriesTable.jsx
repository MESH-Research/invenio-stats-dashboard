import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsTable } from "../shared_components/StatsTable";
import { PropTypes } from "prop-types";

const TopCountriesTable = ({ headers = ["Country", "Views"], rows = [
  ["globe", "United States", "35,432", "US"],
  ["globe", "United Kingdom", "25,321", "GB"],
  ["globe", "Germany", "22,210", "DE"],
  ["globe", "France", "18,109", "FR"],
  ["globe", "Canada", "15,098", "CA"]
] }) => {
  const rowsWithLinks = rows.map(([icon, label, count, code]) => [
    icon,
    <a href={`/search?q=metadata.countries.id:${code}`} target="_blank" rel="noopener noreferrer">{label}</a>,
    count
  ]);

  return (
    <StatsTable
      label="top-countries"
      headers={headers}
      rows={rowsWithLinks}
      title={i18next.t("Top Countries")}
    />
  );
};

TopCountriesTable.propTypes = {
  countryItems: PropTypes.array.isRequired,
};

export { TopCountriesTable };
