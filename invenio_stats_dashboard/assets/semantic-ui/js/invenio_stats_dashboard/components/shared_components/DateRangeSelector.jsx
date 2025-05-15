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

const DateRangeSelector = ({
  dateRange,
  onDateRangeChange,
  granularity,
  onGranularityChange,
  maxHistoryYears = 15
}) => {
  const granularityOptions = [
    { key: 'day', text: i18next.t('Day'), value: 'day' },
    { key: 'week', text: i18next.t('Week'), value: 'week' },
    { key: 'month', text: i18next.t('Month'), value: 'month' },
    { key: 'year', text: i18next.t('Year'), value: 'year' }
  ];

  return (
    <div className="stats-dashboard-controls">
      <div className="stats-date-range-picker">
        <DateRangePicker
          value={dateRange}
          onChange={onDateRangeChange}
          granularity={granularity}
          maxValue={today(getLocalTimeZone())}
          minValue={today(getLocalTimeZone()).subtract({ years: maxHistoryYears })}
          locale={i18next.language}
        >
          <Label>{i18next.t("Select date range")}</Label>
          <Group>
            <DateInput slot="start">
              {(segment) => <DateSegment segment={segment} />}
            </DateInput>
            <span aria-hidden="true">–</span>
            <DateInput slot="end">
              {(segment) => <DateSegment segment={segment} />}
            </DateInput>
            <AriaButton className="ui button">
              <Icon name="calendar" />
            </AriaButton>
          </Group>
          <Popover>
            <Dialog>
              <RangeCalendar />
            </Dialog>
          </Popover>
        </DateRangePicker>
      </div>
      <Dropdown
        selection
        value={granularity}
        options={granularityOptions}
        onChange={(e, { value }) => onGranularityChange(value)}
        aria-label={i18next.t("Select time granularity")}
      />
    </div>
  );
};

DateRangeSelector.propTypes = {
  dateRange: PropTypes.shape({
    start: PropTypes.object.isRequired,
    end: PropTypes.object.isRequired,
  }).isRequired,
  onDateRangeChange: PropTypes.func.isRequired,
  granularity: PropTypes.oneOf(['day', 'week', 'month', 'year']).isRequired,
  onGranularityChange: PropTypes.func.isRequired,
  maxHistoryYears: PropTypes.number,
};

export { DateRangeSelector };