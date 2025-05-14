import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsTable } from "../shared_components/StatsTable";
import { PropTypes } from "prop-types";

const AccessRightsTable = ({ headers = ["Access Rights", "Records"], rows = [
  ["lock open", "Open Access", "45,432", "open"],
  ["lock", "Restricted Access", "15,321", "restricted"],
  ["lock", "Embargoed Access", "12,210", "embargoed"],
  ["lock", "Metadata Only", "8,109", "metadata-only"],
  ["lock", "Closed Access", "5,098", "closed"]
] }) => {
  const rowsWithLinks = rows.map(([icon, label, count, id]) => [
    icon,
    <a href={`/search?q=metadata.access_rights.id:${id}`} target="_blank" rel="noopener noreferrer">{label}</a>,
    count
  ]);

  return (
    <StatsTable
      label="access-rights"
      headers={headers}
      rows={rowsWithLinks}
      title={i18next.t("Content by Access Rights")}
    />
  );
};

AccessRightsTable.propTypes = {
  accessRightsItems: PropTypes.array.isRequired,
};

export { AccessRightsTable };
