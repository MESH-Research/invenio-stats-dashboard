import React, { useEffect, useState, useRef } from "react";
import PropTypes from "prop-types";
import { Dropdown, Button, Popup, Card, Form, Select, Segment } from "semantic-ui-react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import {
  getCurrentUTCDate,
  addDays,
  addMonths,
  addYears,
  setDateParts
} from "../../utils/dates";

const getDateRange = (todayDate, period, maxHistoryYears) => {
  let startDate = addDays(todayDate, -30);
  let endDate = todayDate;
  const currentMonth = todayDate.getUTCMonth() + 1; // Convert to 1-indexed
  // Get current quarter (0-3)
  const currentQuarterIndex = Math.floor((currentMonth - 1) / 3);
  // Get current quarter start date
  const quarterStartMonth = currentQuarterIndex * 3 + 1;

  switch (period) {
    case "allTime":
      startDate = setDateParts(addYears(todayDate, -maxHistoryYears), { month: 1, day: 1 });
      break;
    // Day periods
    case "7days":
      startDate = addDays(todayDate, -7);
      break;
    case "30days":
      startDate = addDays(todayDate, -30);
      break;
    case "90days":
      startDate = addDays(todayDate, -90);
      break;

    // Week periods
    case "1week":
      startDate = addDays(todayDate, -7);
      break;
    case "2weeks":
      startDate = addDays(todayDate, -14);
      break;
    case "4weeks":
      startDate = addDays(todayDate, -28);
      break;
    case "8weeks":
      startDate = addDays(todayDate, -56);
      break;
    case "12weeks":
      startDate = addDays(todayDate, -84);
      break;
    case "24weeks":
      startDate = addDays(todayDate, -168);
      break;

    // Month periods
    case "currentMonth":
      startDate = setDateParts(todayDate, { day: 1 });
      break;
    case "1month":
      startDate = addMonths(todayDate, -1);
      break;
    case "3months":
      startDate = addMonths(todayDate, -3);
      break;
    case "6months":
      startDate = addMonths(todayDate, -6);
      break;
    case "12months":
      startDate = addMonths(todayDate, -12);
      break;

    // Quarter periods
    // The periods for 2 quarters, 3 quarters and 4 quarters include the current quarter
    // up to the current day.
    case "currentQuarter":
      startDate = setDateParts(todayDate, { month: quarterStartMonth, day: 1 });
      break;
    case "previousQuarter":
      // Get previous quarter's start month (1-12)
      const prevQuarterStartMonth = (currentQuarterIndex - 1) * 3 + 1;
      // Get previous quarter's end month (1-12)
      const prevQuarterEndMonth = prevQuarterStartMonth + 2;
      startDate = setDateParts(todayDate, { month: prevQuarterStartMonth, day: 1 });
      endDate = addDays(setDateParts(todayDate, { month: prevQuarterEndMonth + 1, day: 1 }), -1);
      break;
    case "2quarters":
      startDate = addMonths(setDateParts(todayDate, { month: quarterStartMonth, day: 1 }), -6);
      break;
    case "3quarters":
      startDate = addMonths(setDateParts(todayDate, { month: quarterStartMonth, day: 1 }), -9);
      break;
    case "4quarters":
      startDate = addMonths(setDateParts(todayDate, { month: quarterStartMonth, day: 1 }), -12);
      break;

    // Year periods
    // Multi year periods treat the current year up to the current day as one year.
    case "currentYear":
      startDate = setDateParts(todayDate, { month: 1, day: 1 });
      break;
    case "previousYear":
      startDate = setDateParts(addYears(todayDate, -1), { month: 1, day: 1 });
      endDate = setDateParts(addYears(todayDate, -1), { month: 12, day: 31 });
      break;
    case "2years":
      startDate = setDateParts(addYears(todayDate, -2), { month: 1, day: 1 });
      break;
    case "3years":
      startDate = setDateParts(addYears(todayDate, -3), { month: 1, day: 1 });
      break;
    case "4years":
      startDate = setDateParts(addYears(todayDate, -4), { month: 1, day: 1 });
      break;
    case "5years":
      startDate = setDateParts(addYears(todayDate, -5), { month: 1, day: 1 });
      break;

    default:
      startDate = addDays(todayDate, -30);
  }

  if (maxHistoryYears && startDate < addYears(todayDate, -maxHistoryYears)) {
    startDate = setDateParts(addYears(todayDate, -maxHistoryYears), { month: 1, day: 1 });
  }

  return { start: startDate, end: endDate };
};

const getCurrentPeriod = (dateRange, granularity, maxHistoryYears) => {
  const todayDate = getCurrentUTCDate();

  // Calculate difference in milliseconds
  const diffMs = todayDate.getTime() - dateRange?.start?.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const diffMonths = Math.floor(diffDays / 30);
  const diffYears = Math.floor(diffDays / 365);

  const startMonth = dateRange?.start?.getUTCMonth() + 1;
  const startDay = dateRange?.start?.getUTCDate();
  const endMonth = dateRange?.end?.getUTCMonth() + 1;
  const endDay = dateRange?.end?.getUTCDate();

  // Check if the date range spans the maximum history
  if (startDay === 1 && startMonth === 1 && diffYears >= maxHistoryYears) {
    return "allTime";
  }

  switch (granularity) {
    case "day":
      if (diffDays === 7) return "7days";
      if (diffDays === 30) return "30days";
      if (diffDays === 90) return "90days";
      break;

    case "week":
      if (diffDays === 7) return "1week";
      if (diffDays === 14) return "2weeks";
      if (diffDays === 28) return "4weeks";
      if (diffDays === 56) return "8weeks";
      if (diffDays === 84) return "12weeks";
      if (diffDays === 168) return "24weeks";
      break;

    case "month":
      if (
        startDay === 1 &&
        startMonth === todayDate.getUTCMonth() + 1 &&
        endMonth === todayDate.getUTCMonth() + 1
      ) {
        return "currentMonth";
      }
      if (diffMonths === 1) return "1month";
      if (diffMonths === 3) return "3months";
      if (diffMonths === 6) return "6months";
      if (diffMonths === 12) return "1year";
      break;

    case "quarter":
      const currentQuarterIndex = Math.floor((todayDate.getUTCMonth()) / 3);
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
      if (diffMonths === 6) return "2quarters";
      if (diffMonths === 9) return "3quarters";
      if (diffMonths === 12) return "4quarters";
      break;

    case "year":
      if (startDay === 1 && startMonth === 1) {
        if (endMonth === todayDate.getUTCMonth() + 1 && endDay === todayDate.getUTCDate()) {
          return "currentYear";
        }
        if (endDay === 31 && endMonth === 12) {
          if (diffYears === 1) return "previousYear";
          if (diffYears === 2) return "2years";
          if (diffYears === 3) return "3years";
          if (diffYears === 4) return "4years";
          if (diffYears === 5) return "5years";
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
  const todayDate = getCurrentUTCDate();
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
