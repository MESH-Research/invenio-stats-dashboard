import React from "react";
import PropTypes from "prop-types";
import { Button, Dropdown, Icon } from "semantic-ui-react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import {
  Button as AriaButton,
  CalendarCell,
  CalendarGrid,
  DateInput,
  DateRangePicker,
  DateSegment,
  Dialog,
  Group,
  Heading,
  Label,
  Popover,
  RangeCalendar
} from 'react-aria-components';
import { today, getLocalTimeZone } from "@internationalized/date";
import { useStatsDashboard } from '../../context/StatsDashboardContext';

const DateRangeSelector = ({ maxHistoryYears, defaultRange }) => {
  const { dateRange, setDateRange, granularity, setGranularity } = useStatsDashboard();

  const handleGranularityChange = (e, { value }) => {
    setGranularity(value);
  };

  const granularityOptions = [
    { key: 'day', text: 'Day', value: 'day' },
    { key: 'week', text: 'Week', value: 'week' },
    { key: 'month', text: 'Month', value: 'month' },
    { key: 'year', text: 'Year', value: 'year' },
  ];

  return (
    <div className="date-range-selector">
      <ButtonGroup>
        <Button
          onClick={() => setDateRange({
            start: today(getLocalTimeZone()).subtract({ days: 7 }),
            end: today(getLocalTimeZone())
          })}
          active={dateRange.start?.equals(today(getLocalTimeZone()).subtract({ days: 7 }))}
        >
          Last 7 days
        </Button>
        <Button
          onClick={() => setDateRange({
            start: today(getLocalTimeZone()).subtract({ days: 30 }),
            end: today(getLocalTimeZone())
          })}
          active={dateRange.start?.equals(today(getLocalTimeZone()).subtract({ days: 30 }))}
        >
          Last 30 days
        </Button>
        <Button
          onClick={() => setDateRange({
            start: today(getLocalTimeZone()).subtract({ months: 6 }),
            end: today(getLocalTimeZone())
          })}
          active={dateRange.start?.equals(today(getLocalTimeZone()).subtract({ months: 6 }))}
        >
          Last 6 months
        </Button>
        <Button
          onClick={() => setDateRange({
            start: today(getLocalTimeZone()).subtract({ years: 1 }),
            end: today(getLocalTimeZone())
          })}
          active={dateRange.start?.equals(today(getLocalTimeZone()).subtract({ years: 1 }))}
        >
          Last year
        </Button>
      </ButtonGroup>
      <Dropdown
        selection
        options={granularityOptions}
        value={granularity}
        onChange={handleGranularityChange}
        className="granularity-selector"
      />
    </div>
  );
};

DateRangeSelector.propTypes = {
  maxHistoryYears: PropTypes.number,
  defaultRange: PropTypes.string,
};

export { DateRangeSelector };