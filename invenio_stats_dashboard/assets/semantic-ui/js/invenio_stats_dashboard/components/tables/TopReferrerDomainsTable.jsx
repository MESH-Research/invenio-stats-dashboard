import React from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsTable } from "../shared_components/StatsTable";
import { PropTypes } from "prop-types";

const TopReferrerDomainsTable = ({ title = i18next.t("Top Referrer Domains"), icon: labelIcon = "globe", headers = [i18next.t("Domain"), i18next.t("Views")], rows = [
  ["globe", "google.com", "25,432", "google.com"],
  ["globe", "scholar.google.com", "15,321", "scholar.google.com"],
  ["globe", "linkedin.com", "12,210", "linkedin.com"],
  ["globe", "twitter.com", "8,109", "twitter.com"],
  ["globe", "facebook.com", "5,098", "facebook.com"]
] }) => {
  const rowsWithLinks = rows.map(([icon, label, count, domain]) => [
    icon,
    <a href={`/search?q=metadata.referrer_domains:${domain}`} target="_blank" rel="noopener noreferrer">{label}</a>,
    count
  ]);

  return (
    <StatsTable
      label="top-referrer-domains"
      headers={headers}
      rows={rowsWithLinks}
      title={title}
      labelIcon={labelIcon}
    />
  );
};

TopReferrerDomainsTable.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  rows: PropTypes.array,
};

export { TopReferrerDomainsTable };
