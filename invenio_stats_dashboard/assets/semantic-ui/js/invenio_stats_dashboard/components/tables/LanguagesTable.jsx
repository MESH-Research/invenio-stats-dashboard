import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsTable } from "../shared_components/StatsTable";
import { PropTypes } from "prop-types";

const LanguagesTable = ({ headers = ["Language", "Records"], rows = [
  ["globe", "English", "12,345", "en"],
  ["globe", "Spanish", "8,765", "es"],
  ["globe", "French", "6,543", "fr"],
  ["globe", "German", "4,321", "de"],
  ["globe", "Chinese", "3,210", "zh"]
] }) => {
  const rowsWithLinks = rows.map(([icon, label, count, code]) => [
    icon,
    <a href={`/search?q=metadata.languages.id:${code}`} target="_blank" rel="noopener noreferrer">{label}</a>,
    count
  ]);

  return (
    <StatsTable
      label="languages"
      headers={headers}
      rows={rowsWithLinks}
      title={i18next.t("Content by Language")}
    />
  );
};

LanguagesTable.propTypes = {
  languageItems: PropTypes.array.isRequired,
};

export { LanguagesTable };
