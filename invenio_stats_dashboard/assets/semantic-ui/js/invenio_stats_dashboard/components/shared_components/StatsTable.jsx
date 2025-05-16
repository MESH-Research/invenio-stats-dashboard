import React from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { Table, Header, Segment, Icon } from "semantic-ui-react";
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
const StatsTable = ({ headers = [], rows = [], title, label, labelIcon }) => {
  const tableLabel = label || (title ? title.toLowerCase().replace(/\s+/g, '-') : 'stats');

  return (
    <div className={`stats-table-container ${tableLabel}-stats-table-container`} role="region" aria-label={title}>
      {title && (
        <Header as="h3" className="stats-table-header" id={`${tableLabel}-stats-table-header`} attached="top">
          {title}
        </Header>
      )}
      <Segment attached>
        <Table
          id={`${tableLabel}-stats-table`}
          aria-labelledby={`${tableLabel}-stats-table-header`}
          basic="very"
          compact
          unstackable
        >
          <Table.Header>
            <Table.Row>
              <Table.HeaderCell scope="col" />  {/* Icon column */}
              {headers.map((header, index) => (
                <Table.HeaderCell key={index} scope="col">
                  {labelIcon && (
                    <Icon
                      name={labelIcon}
                      className="stats-table-icon"
                      aria-hidden="true"
                    />
                  )}
                  {header}
                </Table.HeaderCell>
              ))}
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {rows.map(([iconName, ...values], rowIndex) => (
              <Table.Row key={rowIndex}>
                <Table.Cell>
                  {iconName && (
                    <Icon
                      name={iconName}
                      className="stats-table-icon"
                      aria-hidden="true"
                    />
                  )}
                </Table.Cell>
                {values.map((value, cellIndex) => (
                  <Table.Cell key={cellIndex}>
                    {value}
                  </Table.Cell>
                ))}
              </Table.Row>
            ))}
          </Table.Body>
        </Table>
      </Segment>
    </div>
  );
};

StatsTable.propTypes = {
  headers: PropTypes.array.isRequired,
  rows: PropTypes.array.isRequired,
  title: PropTypes.string,
  label: PropTypes.string,
};

export { StatsTable };
