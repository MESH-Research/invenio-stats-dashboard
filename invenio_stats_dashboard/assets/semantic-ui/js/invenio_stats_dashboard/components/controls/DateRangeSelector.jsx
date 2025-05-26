import React, { useEffect, useState, useRef } from "react";
import PropTypes from "prop-types";
import { Dropdown, Button, Popup, Card, Form, Select, Segment } from "semantic-ui-react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { today, getLocalTimeZone } from "@internationalized/date";

const getDateRange = (todayDate, period, maxHistoryYears) => {
  let startDate = todayDate.subtract({ days: 30 });
  let endDate = todayDate;
  const currentMonth = todayDate.month;
  // Get current quarter (0-3)
  const currentQuarterIndex = Math.floor((currentMonth - 1) / 3);
  // Get current quarter start date
  const quarterStartMonth = currentQuarterIndex * 3 + 1;

  switch (period) {
    case "allTime":
      startDate = todayDate.subtract({ years: maxHistoryYears }).set({ month: 1, day: 1 });
      break;
    // Day periods
    case "7days":
      startDate = todayDate.subtract({ days: 7 });
      break;
    case "30days":
      startDate = todayDate.subtract({ days: 30 });
      break;
    case "90days":
      startDate = todayDate.subtract({ days: 90 });
      break;

    // Week periods
    case "1week":
      startDate = todayDate.subtract({ weeks: 1 });
      break;
    case "2weeks":
      startDate = todayDate.subtract({ weeks: 2 });
      break;
    case "4weeks":
      startDate = todayDate.subtract({ weeks: 4 });
      break;
    case "8weeks":
      startDate = todayDate.subtract({ weeks: 8 });
      break;
    case "12weeks":
      startDate = todayDate.subtract({ weeks: 12 });
      break;
    case "24weeks":
      startDate = todayDate.subtract({ weeks: 24 });
      break;

    // Month periods
    case "currentMonth":
      startDate = todayDate.set({ day: 1 });
      break;
    case "1month":
      startDate = todayDate.subtract({ months: 1 });
      break;
    case "3months":
      startDate = todayDate.subtract({ months: 3 });
      break;
    case "6months":
      startDate = todayDate.subtract({ months: 6 });
      break;
    case "12months":
      startDate = todayDate.subtract({ months: 12 });
      break;

    // Quarter periods
    // The periods for 2 quarters, 3 quarters and 4 quarters include the current quarter
    // up to the current day.
    case "currentQuarter":
      startDate = todayDate.set({ month: quarterStartMonth, day: 1 });
      break;
    case "previousQuarter":
      // Get previous quarter's start month (1-12)
      const prevQuarterStartMonth = (currentQuarterIndex - 1) * 3 + 1;
      // Get previous quarter's end month (1-12)
      const prevQuarterEndMonth = prevQuarterStartMonth + 2;
      startDate = todayDate.set({ month: prevQuarterStartMonth, day: 1 });
      endDate = todayDate
        .set({ month: prevQuarterEndMonth + 1, day: 1 })
        .subtract({ days: 1 });
      break;
    case "2quarters":
      startDate = todayDate
        .set({ month: quarterStartMonth, day: 1 })
        .subtract({ months: 6 });
      break;
    case "3quarters":
      startDate = todayDate
        .set({ month: quarterStartMonth, day: 1 })
        .subtract({ months: 9 });
      break;
    case "4quarters":
      startDate = todayDate
        .set({ month: quarterStartMonth, day: 1 })
        .subtract({ months: 12 });
      break;

    // Year periods
    // Multi year periods treat the current year up to the current day as one year.
    case "currentYear":
      startDate = todayDate.set({ month: 1, day: 1 });
      break;
    case "previousYear":
      startDate = todayDate.subtract({ years: 1 }).set({ month: 1, day: 1 });
      endDate = todayDate.subtract({ years: 1 }).set({ month: 12, day: 31 });
      break;
    case "2years":
      startDate = todayDate.subtract({ years: 2 }).set({ month: 1, day: 1 });
      break;
    case "3years":
      startDate = todayDate.subtract({ years: 3 }).set({ month: 1, day: 1 });
      break;
    case "4years":
      startDate = todayDate.subtract({ years: 4 }).set({ month: 1, day: 1 });
      break;
    case "5years":
      startDate = todayDate.subtract({ years: 5 }).set({ month: 1, day: 1 });
      break;

    default:
      startDate = todayDate.subtract({ days: 30 });
  }
  if (maxHistoryYears && startDate < todayDate.subtract({ years: maxHistoryYears }) ) {
    startDate = todayDate.subtract({ years: maxHistoryYears }).set({ month: 1, day: 1 });
  }

  return { start: startDate, end: endDate };
};

const getCurrentPeriod = (dateRange, granularity, maxHistoryYears) => {
  const todayDate = today(getLocalTimeZone());
  const diff = todayDate.subtract(dateRange?.start);
  const startMonth = dateRange?.start?.month;
  const startDay = dateRange?.start?.day;
  const endMonth = dateRange?.end?.month;
  const endDay = dateRange?.end?.day;

  // Check if the date range spans the maximum history
  if (startDay === 1 && startMonth === 1 && diff.years >= maxHistoryYears) {
    return "allTime";
  }

  switch (granularity) {
    case "day":
      if (diff.days === 7) return "7days";
      if (diff.days === 30) return "30days";
      if (diff.days === 90) return "90days";
      break;

    case "week":
      if (diff.weeks === 1) return "1week";
      if (diff.weeks === 2) return "2weeks";
      if (diff.weeks === 4) return "4weeks";
      if (diff.weeks === 8) return "8weeks";
      if (diff.weeks === 12) return "12weeks";
      if (diff.weeks === 24) return "24weeks";
      break;

    case "month":
      if (
        startDay === 1 &&
        startMonth === todayDate.month &&
        endMonth === todayDate.month
      ) {
        return "currentMonth";
      }
      if (diff.months === 1) return "1month";
      if (diff.months === 3) return "3months";
      if (diff.months === 6) return "6months";
      if (diff.months === 12) return "1year";
      break;

    case "quarter":
      const currentQuarterIndex = Math.floor((todayDate.month - 1) / 3);
      const quarterStartMonth = currentQuarterIndex * 3 + 1;
      const prevQuarterStartMonth = (currentQuarterIndex - 1) * 3 + 1;

      if (startMonth === quarterStartMonth && endMonth === quarterStartMonth + 3) {
        return "currentQuarter";
      }
      if (
        startMonth === prevQuarterStartMonth &&
        endMonth === prevQuarterStartMonth + 3
      ) {
        return "previousQuarter";
      }
      if (diff.months === 6) return "2quarters";
      if (diff.months === 9) return "3quarters";
      if (diff.months === 12) return "4quarters";
      break;

    case "year":
      if (startDay === 1 && startMonth === 1) {
        if (endMonth === todayDate.month && endDay === todayDate.day) {
          return "currentYear";
        }
        if (endDay === 31 && endMonth === 12) {
          if (diff.years === 1) return "previousYear";
          if (diff.years === 2) return "2years";
          if (diff.years === 3) return "3years";
          if (diff.years === 4) return "4years";
          if (diff.years === 5) return "5years";
        }
      }
      break;
  }

  // If no match is found, return the default for the current granularity
  switch (granularity) {
    case "day":
      return "30days";
    case "week":
      return "12weeks";
    case "month":
      return "12months";
    case "quarter":
      return "4quarters";
    case "year":
      return "5years";
    default:
      return "allTime";
  }
};

const dayPeriodOptions = [
  { key: "7days", text: i18next.t("Past 7 days"), value: "7days" },
  { key: "30days", text: i18next.t("Past 30 days"), value: "30days" },
  { key: "90days", text: i18next.t("Past 90 days"), value: "90days" },
  { key: "6months", text: i18next.t("Past 6 months"), value: "6months" },
  { key: "1year", text: i18next.t("Past year"), value: "1year" },
  { key: "allTime", text: i18next.t("All time"), value: "allTime" },
];

const weekPeriodOptions = [
  { key: "1week", text: i18next.t("Past 1 week"), value: "1week" },
  { key: "2weeks", text: i18next.t("Past 2 weeks"), value: "2weeks" },
  { key: "4weeks", text: i18next.t("Past 4 weeks"), value: "4weeks" },
  { key: "8weeks", text: i18next.t("Past 8 weeks"), value: "8weeks" },
  { key: "12weeks", text: i18next.t("Past 12 weeks"), value: "12weeks" },
  { key: "24weeks", text: i18next.t("Past 24 weeks"), value: "24weeks" },
  { key: "allTime", text: i18next.t("All time"), value: "allTime" },
];

const monthPeriodOptions = [
  { key: "1month", text: i18next.t("Past 1 month"), value: "1month" },
  { key: "3months", text: i18next.t("Past 3 months"), value: "3months" },
  { key: "6months", text: i18next.t("Past 6 months"), value: "6months" },
  { key: "12months", text: i18next.t("Past year"), value: "12months" },
  { key: "allTime", text: i18next.t("All time"), value: "allTime" },
];

const quarterPeriodOptions = [
  {
    key: "currentQuarter",
    text: i18next.t("Current quarter"),
    value: "currentQuarter",
  },
  {
    key: "previousQuarter",
    text: i18next.t("Previous quarter"),
    value: "previousQuarter",
  },
  { key: "2quarters", text: i18next.t("Past 2 quarters"), value: "2quarters" },
  { key: "3quarters", text: i18next.t("Past 3 quarters"), value: "3quarters" },
  { key: "4quarters", text: i18next.t("Past 4 quarters"), value: "4quarters" },
  { key: "allTime", text: i18next.t("All time"), value: "allTime" },
];

const yearPeriodOptions = [
  { key: "currentYear", text: i18next.t("Current year"), value: "currentYear" },
  { key: "previousYear", text: i18next.t("Previous year"), value: "previousYear" },
  { key: "2years", text: i18next.t("Past 2 years"), value: "2years" },
  { key: "3years", text: i18next.t("Past 3 years"), value: "3years" },
  { key: "4years", text: i18next.t("Past 4 years"), value: "4years" },
  { key: "5years", text: i18next.t("Past 5 years"), value: "5years" },
  { key: "allTime", text: i18next.t("All time"), value: "allTime" },
];

const periodOptions = {
  day: dayPeriodOptions,
  week: weekPeriodOptions,
  month: monthPeriodOptions,
  quarter: quarterPeriodOptions,
  year: yearPeriodOptions,
};

const DateRangeSelector = ({
  dateRange,
  defaultRangeOptions,
  granularity,
  maxHistoryYears = 15,
  setDateRange,
}) => {
  const [isPopupOpen, setIsPopupOpen] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);
  const todayDate = today(getLocalTimeZone());
  const currentPeriodOptions = periodOptions[granularity];
  const [currentSelectedOption, setCurrentSelectedOption] = useState(dateRange ? getCurrentPeriod(dateRange, granularity, maxHistoryYears) : currentPeriodOptions[0].value);
  console.log("dateRange", dateRange);
  console.log("defaultRangeOptions", defaultRangeOptions);
  console.log("granularity", granularity);
  console.log("todayDate", todayDate);
  console.log("currentPeriodOptions", currentPeriodOptions);
  console.log("currentSelectedOption", currentSelectedOption);

  useEffect(() => {
    console.log("first render");
    if (!dateRange) {
      const defaultPeriod = defaultRangeOptions?.[granularity] || "30days";
      const initialDateRange = getDateRange(todayDate, defaultPeriod, maxHistoryYears);
      setDateRange(initialDateRange);
      setCurrentSelectedOption(defaultPeriod);
      console.log(dateRange);
    }
  }, []);

  useEffect(() => {
    console.log("granularity changed");
    console.log(granularity);
    const newDefaultPeriod = defaultRangeOptions?.[granularity];
    console.log("newDefaultPeriod", newDefaultPeriod);
    setCurrentSelectedOption(newDefaultPeriod);
    const newDateRange = getDateRange(todayDate, newDefaultPeriod, maxHistoryYears);
    console.log("newDateRange", newDateRange);
    setDateRange(newDateRange);
  }, [granularity]);

  const handlePeriodChange = (e, { value }) => {
    console.log("setting date range");
    console.log(value);
    setCurrentSelectedOption(value);
    const newDateRange = getDateRange(todayDate, value, maxHistoryYears);
    console.log(newDateRange);
    setDateRange(newDateRange);
    setIsOpen(false);
  };

  // const handleCustomRangeChange = (startDate, endDate) => {
  //   setDateRange({ start: startDate, end: endDate });
  //   setIsPopupOpen(false);
  // };

  const handleMenuOpen = () => {
    setIsOpen(true);
    const selectorElement = document.querySelector('.period-selector');
    if (selectorElement) {
      selectorElement.style.position = 'relative';
      selectorElement.style.zIndex = '1000';
    }
  };

  const handleMenuClose = () => {
    setIsOpen(false);
    setTimeout(() => {
      const selectorElement = document.querySelector('.period-selector');
      const menuElement = document.querySelector('.period-selector .menu');
      if (selectorElement) {
        selectorElement.style = '';
      }
      if (menuElement) {
        menuElement.style = '';
      }
    }, 100);
  };

  return (
    <Segment className="date-range-selector">
      <label id="date-range-selector-label" className="stats-dashboard-field-label" htmlFor="date-range-selector">{i18next.t("for the")}</label>
      <Dropdown
        id="date-range-selector"
        selection
        fluid
        options={currentPeriodOptions}
        value={currentSelectedOption}
        onChange={handlePeriodChange}
        className="period-selector"
        closeOnBlur={true}
        closeOnChange={false}
        selectOnBlur={true}
        open={isOpen}
        onOpen={handleMenuOpen}
        onClose={handleMenuClose}
        onBlur={handleMenuClose}
        ref={menuRef}
      />
      {/* <Popup
        content={
          <Card>
            <Card.Content>
              <Form>
                <Form.Field>
                  <label>{i18next.t("Start Date")}</label>
                  <input
                    type="date"
                    onChange={(e) => {
                      const startDate = new Date(e.target.value);
                      if (dateRange?.end) {
                        handleCustomRangeChange(startDate, dateRange.end);
                      }
                    }}
                  />
                </Form.Field>
                <Form.Field>
                  <label>{i18next.t("End Date")}</label>
                  <input
                    type="date"
                    onChange={(e) => {
                      const endDate = new Date(e.target.value);
                      if (dateRange?.start) {
                        handleCustomRangeChange(dateRange.start, endDate);
                      }
                    }}
                  />
                </Form.Field>
              </Form>
            </Card.Content>
          </Card>
        }
        on="click"
        position="bottom right"
        open={isPopupOpen}
        onOpen={() => setIsPopupOpen(true)}
        onClose={() => setIsPopupOpen(false)}
        trigger={
          <Button
            fluid
            icon="calendar"
            labelPosition="right"
            content="custom range"
            onClick={() => setIsPopupOpen(!isPopupOpen)}
            className="custom-range-button mt-10"
          />
        }
      /> */}
    </Segment>
  );
};

DateRangeSelector.propTypes = {
  dateRange: PropTypes.object,
  granularity: PropTypes.string,
  maxHistoryYears: PropTypes.number,
  setDateRange: PropTypes.func,
};

export { DateRangeSelector };
