import React from "react";
import PropTypes from "prop-types";
import { Button, ButtonGroup, Icon } from "semantic-ui-react";
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
            <Button>
              <Icon name="calendar" />
            </Button>
          </Group>
          <Popover>
            <Dialog>
              <RangeCalendar />
            </Dialog>
          </Popover>
        </DateRangePicker>
      </div>
      <ButtonGroup>
        <Button
          toggle
          active={granularity === 'day'}
          onClick={() => onGranularityChange('day')}
          aria-pressed={granularity === 'day'}
        >
          {i18next.t('Day')}
        </Button>
        <Button
          toggle
          active={granularity === 'week'}
          onClick={() => onGranularityChange('week')}
          aria-pressed={granularity === 'week'}
        >
          {i18next.t('Week')}
        </Button>
        <Button
          toggle
          active={granularity === 'month'}
          onClick={() => onGranularityChange('month')}
          aria-pressed={granularity === 'month'}
        >
          {i18next.t('Month')}
        </Button>
        <Button
          toggle
          active={granularity === 'year'}
          onClick={() => onGranularityChange('year')}
          aria-pressed={granularity === 'year'}
        >
          {i18next.t('Year')}
        </Button>
      </ButtonGroup>
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