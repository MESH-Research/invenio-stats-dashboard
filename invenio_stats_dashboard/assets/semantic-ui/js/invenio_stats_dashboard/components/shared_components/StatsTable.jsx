// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React from "react";
import { Table, Icon } from "semantic-ui-react";
import { PropTypes } from "prop-types";

/**
 * A table component that displays a list of headers and rows.
 * The headers and rows are passed as props to the component.
 * The component will also display an optional icon for each row.
 *
 * @param {string[]} headers - The headers for the table columns. The headers may be strings or React elements.
 * @param {string[][]} rows - The rows of the table. An array of arrays, where each inner array contains the data for a row. The first element of each inner array is the icon name (or null if no icon is needed), and the rest are the values. The values may be strings or React elements.
 * @param {string} title - Optional title text for the table header
 * @param {string} label - Optional label for class names. If not provided, will be derived from title
 * @returns {React.ReactElement} - The StatsTable component.
 */
const StatsTable = ({ headers = [], rows = [], title, label, maxHeight = null }) => {
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
          {headers.map((header, index) => (
            <Table.HeaderCell
              key={index}
              scope="col"
              className="stats-table-header-cell"
            >
              {header}
            </Table.HeaderCell>
          ))}
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
};

export { StatsTable };
