// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React from "react";
import { Table, Icon, Popup } from "semantic-ui-react";
import { PropTypes } from "prop-types";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";

/**
 * Create a header with an info popup explaining percentage calculations
 * @param {string} headerText - The main header text
 * @param {boolean} isDelta - Whether the data is delta (sum across period) or snapshot (as of date)
 * @param {string} dateRangeEnd - The end date for snapshot data
 * @returns {React.ReactElement} - Header element with info popup
 */
const createPercentageHeader = (headerText, isDelta = false, dateRangeEnd = null, metricType = 'records') => {
  // If isDelta is undefined, don't show popup (for API-based components)
  if (isDelta === undefined) {
    return headerText;
  }

  const explanationText = isDelta 
    ? i18next.t("Percentage of {{metric}} added during this period", { metric: metricType })
    : i18next.t("Percentage of total {{metric}} as of {{date}}", { metric: metricType, date: dateRangeEnd || i18next.t("the end date") });

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
      <span>{headerText}</span>
      <Popup
        trigger={<Icon name="info circle" size="small" color="grey" />}
        content={explanationText}
        position="top center"
        size="small"
        inverted
      />
    </div>
  );
};

/**
 * A table component that displays a list of headers and rows.
 * The headers and rows are passed as props to the component.
 * The component will also display an optional icon for each row.
 *
 * @param {string[]} headers - The headers for the table columns. The headers may be strings or React elements.
 * @param {string[][]} rows - The rows of the table. An array of arrays, where each inner array contains the data for a row. The first element of each inner array is the icon name (or null if no icon is needed), and the rest are the values. The values may be strings or React elements.
 * @param {string} title - Optional title text for the table header
 * @param {string} label - Optional label for class names. If not provided, will be derived from title
 * @param {boolean} isDelta - Whether the data is delta (sum across period) or snapshot (as of date)
 * @param {string} dateRangeEnd - The end date for snapshot data explanations
 * @param {string} metricType - The type of metric being displayed ('records', 'views', 'downloads', etc.)
 * @returns {React.ReactElement} - The StatsTable component.
 */
const StatsTable = ({ headers = [], rows = [], title, label, maxHeight = null, isDelta = false, dateRangeEnd = null, metricType = 'records' }) => {
  const tableStyle = maxHeight ? {
    maxHeight: typeof maxHeight === 'number' ? `${maxHeight}px` : maxHeight,
    overflowY: 'auto',
    display: 'block'
  } : {};

  return (
    <div style={tableStyle}>
      <Table
        id={`${label}-stats-table`}
        aria-labelledby={`${label}-stats-table-header`}
        basic="very"
        compact
        unstackable
      >
      <Table.Header>
        <Table.Row>
          {/* Icon column */}
          <Table.HeaderCell
            scope="col"
            className="stats-table-header-cell collapsing pr-0"
          />
          {headers.map((header, index) => {
            // Check if this is a percentage column (contains "Works", "Records", "Files", etc.)
            const isPercentageColumn = typeof header === 'string' && 
              (header.includes('Works') || header.includes('Records') || header.includes('Files') || 
               header.includes('Views') || header.includes('Downloads') || header.includes('Volume'));
            
            const headerContent = isPercentageColumn 
              ? createPercentageHeader(header, isDelta, dateRangeEnd, metricType)
              : header;

            return (
              <Table.HeaderCell
                key={index}
                scope="col"
                className="stats-table-header-cell"
              >
                {headerContent}
              </Table.HeaderCell>
            );
          })}
        </Table.Row>
      </Table.Header>
      <Table.Body>
        {rows.map(([iconName, ...values], rowIndex) => (
          <Table.Row key={rowIndex} data-testid={`row-${rowIndex}`}>
            <Table.Cell collapsing className="stats-table-icon-cell pr-0">
              {iconName && (
                <Icon
                  name={iconName}
                  className="stats-table-icon"
                  aria-hidden="true"
                  size="small"
                />
              )}
            </Table.Cell>
            {values.map((value, cellIndex) => (
              <Table.Cell key={cellIndex} data-testid={`cell-${rowIndex}-${cellIndex + 1}`}>{value}</Table.Cell>
            ))}
          </Table.Row>
        ))}
      </Table.Body>
    </Table>
    </div>
  );
};

StatsTable.propTypes = {
  headers: PropTypes.array.isRequired,
  rows: PropTypes.array.isRequired,
  title: PropTypes.string,
  label: PropTypes.string,
  maxHeight: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  isDelta: PropTypes.bool,
  dateRangeEnd: PropTypes.string,
  metricType: PropTypes.string,
};

export { StatsTable };
