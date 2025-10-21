import React, { useEffect, useState, useRef } from "react";
import PropTypes from "prop-types";
import {
  Dropdown,
  Button,
  Popup,
  Card,
  Form,
  Select,
  Segment,
  Input,
  Grid,
} from "semantic-ui-react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import {
  getCurrentUTCDate,
  addDays,
  addMonths,
  addYears,
  setDateParts,
  createUTCDateFromParts,
} from "../../utils/dates";

const getDateRange = (todayDate, period, maxHistoryYears) => {
  let startDate = addDays(todayDate, -30);
  let endDate = todayDate;
  const currentMonth = todayDate.getUTCMonth() + 1; // Convert to 1-indexed
  // Get current quarter (0-3)
  const currentQuarterIndex = Math.floor((currentMonth - 1) / 3);
  // Get current quarter start date
  const quarterStartMonth = currentQuarterIndex * 3 + 1;

  // Debug logging for quarter calculation
  if (period === "currentQuarter") {
    console.log("Current quarter calculation debug:");
    console.log("todayDate:", todayDate.toISOString());
    console.log("currentMonth (1-indexed):", currentMonth);
    console.log("currentQuarterIndex (0-3):", currentQuarterIndex);
    console.log("Expected quarter:", currentQuarterIndex + 1);
    console.log("quarterStartMonth:", quarterStartMonth);
  }

  switch (period) {
    case "allTime":
      startDate = setDateParts(addYears(todayDate, -maxHistoryYears), {
        month: 1,
        day: 1,
      });
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
      // Set end date to the last day of the current quarter
      const quarterEndMonth = quarterStartMonth + 2; // Q1: Jan-Mar, Q2: Apr-Jun, etc.
      endDate = addDays(
        setDateParts(todayDate, { month: quarterEndMonth + 1, day: 1 }),
        -1,
      );

      // Debug logging for current quarter date range
      console.log("Current quarter date range:");
      console.log("startDate:", startDate.toISOString());
      console.log("endDate:", endDate.toISOString());
      console.log("quarterStartMonth:", quarterStartMonth);
      console.log("quarterEndMonth:", quarterEndMonth);
      break;
    case "previousQuarter":
      // Get previous quarter's start month (1-12)
      const prevQuarterStartMonth = (currentQuarterIndex - 1) * 3 + 1;
      // Get previous quarter's end month (1-12)
      const prevQuarterEndMonth = prevQuarterStartMonth + 2;
      startDate = setDateParts(todayDate, {
        month: prevQuarterStartMonth,
        day: 1,
      });
      endDate = addDays(
        setDateParts(todayDate, { month: prevQuarterEndMonth + 1, day: 1 }),
        -1,
      );
      break;
    case "2quarters":
      startDate = addMonths(
        setDateParts(todayDate, { month: quarterStartMonth, day: 1 }),
        -6,
      );
      break;
    case "3quarters":
      startDate = addMonths(
        setDateParts(todayDate, { month: quarterStartMonth, day: 1 }),
        -9,
      );
      break;
    case "4quarters":
      startDate = addMonths(
        setDateParts(todayDate, { month: quarterStartMonth, day: 1 }),
        -12,
      );
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
    startDate = setDateParts(addYears(todayDate, -maxHistoryYears), {
      month: 1,
      day: 1,
    });
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
      const currentQuarterIndex = Math.floor(todayDate.getUTCMonth() / 3);
      const quarterStartMonth = currentQuarterIndex * 3 + 1;
      const prevQuarterStartMonth = (currentQuarterIndex - 1) * 3 + 1;

      if (
        startMonth === quarterStartMonth &&
        endMonth === quarterStartMonth + 3
      ) {
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
        if (
          endMonth === todayDate.getUTCMonth() + 1 &&
          endDay === todayDate.getUTCDate()
        ) {
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
  { key: "custom", text: i18next.t("Custom range"), value: "custom" },
];

const weekPeriodOptions = [
  { key: "1week", text: i18next.t("Past 1 week"), value: "1week" },
  { key: "2weeks", text: i18next.t("Past 2 weeks"), value: "2weeks" },
  { key: "4weeks", text: i18next.t("Past 4 weeks"), value: "4weeks" },
  { key: "8weeks", text: i18next.t("Past 8 weeks"), value: "8weeks" },
  { key: "12weeks", text: i18next.t("Past 12 weeks"), value: "12weeks" },
  { key: "24weeks", text: i18next.t("Past 24 weeks"), value: "24weeks" },
  { key: "allTime", text: i18next.t("All time"), value: "allTime" },
  { key: "custom", text: i18next.t("Custom range"), value: "custom" },
];

const monthPeriodOptions = [
  { key: "1month", text: i18next.t("Past 1 month"), value: "1month" },
  { key: "3months", text: i18next.t("Past 3 months"), value: "3months" },
  { key: "6months", text: i18next.t("Past 6 months"), value: "6months" },
  { key: "12months", text: i18next.t("Past year"), value: "12months" },
  { key: "allTime", text: i18next.t("All time"), value: "allTime" },
  { key: "custom", text: i18next.t("Custom range"), value: "custom" },
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
  { key: "custom", text: i18next.t("Custom range"), value: "custom" },
];

const yearPeriodOptions = [
  { key: "currentYear", text: i18next.t("Current year"), value: "currentYear" },
  {
    key: "previousYear",
    text: i18next.t("Previous year"),
    value: "previousYear",
  },
  { key: "2years", text: i18next.t("Past 2 years"), value: "2years" },
  { key: "3years", text: i18next.t("Past 3 years"), value: "3years" },
  { key: "4years", text: i18next.t("Past 4 years"), value: "4years" },
  { key: "5years", text: i18next.t("Past 5 years"), value: "5years" },
  { key: "allTime", text: i18next.t("All time"), value: "allTime" },
  { key: "custom", text: i18next.t("Custom range"), value: "custom" },
];

const periodOptions = {
  day: dayPeriodOptions,
  week: weekPeriodOptions,
  month: monthPeriodOptions,
  quarter: quarterPeriodOptions,
  year: yearPeriodOptions,
};

/** Validate the date
 *
 * @param {string} year - The year
 * @param {string} month - The month
 * @param {string} day - The day
 * @param {string} fieldPrefix - The field prefix
 * @returns {object} The errors
 */
const validateDate = (year, month, day, fieldPrefix) => {
  const errors = {};

  if (!year || !/^\d{4}$/.test(year)) {
    errors[`${fieldPrefix}Year`] = i18next.t("Year must be 4 digits");
  } else {
    const yearNum = parseInt(year, 10);
    if (yearNum < 1900 || yearNum > 2100) {
      errors[`${fieldPrefix}Year`] = i18next.t("Year must be between 1900 and 2100");
    }
  }

  if (!month || !/^\d{2}$/.test(month)) {
    errors[`${fieldPrefix}Month`] = i18next.t("Month must be 2 digits");
  } else {
    const monthNum = parseInt(month, 10);
    if (monthNum < 1 || monthNum > 12) {
      errors[`${fieldPrefix}Month`] = i18next.t("Month must be between 01 and 12");
    }
  }

  if (!day || !/^\d{2}$/.test(day)) {
    errors[`${fieldPrefix}Day`] = i18next.t("Day must be 2 digits");
  } else {
    const dayNum = parseInt(day, 10);
    if (dayNum < 1 || dayNum > 31) {
      errors[`${fieldPrefix}Day`] = i18next.t("Day must be between 01 and 31");
    }
  }

  if (!errors[`${fieldPrefix}Year`] && !errors[`${fieldPrefix}Month`] && !errors[`${fieldPrefix}Day`]) {
    try {
      const yearNum = parseInt(year, 10);
      const monthNum = parseInt(month, 10);
      const dayNum = parseInt(day, 10);
      const testDate = createUTCDateFromParts(yearNum, monthNum, dayNum);

      // Check if the date is valid (handles leap years, etc.)
      if (testDate.getUTCFullYear() !== yearNum ||
          testDate.getUTCMonth() !== monthNum - 1 ||
          testDate.getUTCDate() !== dayNum) {
        errors[`${fieldPrefix}Day`] = i18next.t("Invalid date");
      }
    } catch (e) {
      errors[`${fieldPrefix}Day`] = i18next.t("Invalid date");
    }
  }

  return errors;
};

/**
 * Auto-format year input (1-digit or 2-digit to 4-digit)
 * @param {string} year - The year input value
 * @returns {string} Formatted year
 */
const formatYear = (year) => {
  if (!year) return "";

  const yearNum = parseInt(year, 10);
  if (isNaN(yearNum)) return year;

  // If it's already 4 digits, return as is
  if (year.length === 4) return year;

  // If it's 1 or 2 digits, assume closest year
  if (year.length === 1 || year.length === 2) {
    const currentYear = new Date().getFullYear();
    const currentCentury = Math.floor(currentYear / 100) * 100;
    const nextCentury = currentCentury + 100;

    const fullYear = currentCentury + yearNum;
    const nextFullYear = nextCentury + yearNum;

    // Choose the closest year
    const currentDiff = Math.abs(fullYear - currentYear);
    const nextDiff = Math.abs(nextFullYear - currentYear);

    return currentDiff <= nextDiff ? fullYear.toString() : nextFullYear.toString();
  }

  return year;
};

/**
 * Auto-format month input (1-digit to 2-digit with leading zero)
 * @param {string} month - The month input value
 * @returns {string} Formatted month
 */
const formatMonth = (month) => {
  if (!month) return "";

  const monthNum = parseInt(month, 10);
  if (isNaN(monthNum)) return month;

  // If it's already 2 digits, return as is
  if (month.length === 2) return month;

  // If it's 1 digit, add leading zero
  if (month.length === 1) {
    return monthNum.toString().padStart(2, "0");
  }

  return month;
};

/**
 * Auto-format day input (1-digit to 2-digit with leading zero)
 * @param {string} day - The day input value
 * @returns {string} Formatted day
 */
const formatDay = (day) => {
  if (!day) return "";

  const dayNum = parseInt(day, 10);
  if (isNaN(dayNum)) return day;

  // If it's already 2 digits, return as is
  if (day.length === 2) return day;

  // If it's 1 digit, add leading zero
  if (day.length === 1) {
    return dayNum.toString().padStart(2, "0");
  }

  return day;
};

/** Custom Date Range Popup Component
 *
 * @param {object} props - The component props
 * @param {boolean} props.isOpen - Whether the popup is open
 * @param {function} props.onClose - The function to close the popup
 * @param {function} props.onSubmit - The function to submit the form
 * @param {function} props.onClear - The function to clear and reset to default range
 * @param {Date} props.initialStartDate - The initial start date
 * @param {Date} props.initialEndDate - The initial end date
 * @param {React.RefObject} props.triggerRef - The ref object to trigger the popup
 *
 * @returns {React.ReactElement} The CustomDateRangePopup component
 */
const CustomDateRangePopup = ({
  isOpen,
  onClose,
  onSubmit,
  onClear,
  initialStartDate,
  initialEndDate,
  triggerRef,
}) => {
  const [startYear, setStartYear] = useState("");
  const [startMonth, setStartMonth] = useState("");
  const [startDay, setStartDay] = useState("");
  const [endYear, setEndYear] = useState("");
  const [endMonth, setEndMonth] = useState("");
  const [endDay, setEndDay] = useState("");
  const [errors, setErrors] = useState({});
  const popupRef = useRef(null);
  const firstInputRef = useRef(null);

  useEffect(() => {
    if (initialStartDate && initialEndDate) {
      setStartYear(initialStartDate.getUTCFullYear().toString());
      setStartMonth((initialStartDate.getUTCMonth() + 1).toString().padStart(2, "0"));
      setStartDay(initialStartDate.getUTCDate().toString().padStart(2, "0"));
      setEndYear(initialEndDate.getUTCFullYear().toString());
      setEndMonth((initialEndDate.getUTCMonth() + 1).toString().padStart(2, "0"));
      setEndDay(initialEndDate.getUTCDate().toString().padStart(2, "0"));
    } else {
      const today = getCurrentUTCDate();
      setStartYear(today.getUTCFullYear().toString());
      setStartMonth((today.getUTCMonth() + 1).toString().padStart(2, "0"));
      setStartDay(today.getUTCDate().toString().padStart(2, "0"));
      setEndYear(today.getUTCFullYear().toString());
      setEndMonth((today.getUTCMonth() + 1).toString().padStart(2, "0"));
      setEndDay(today.getUTCDate().toString().padStart(2, "0"));
    }
  }, [initialStartDate, initialEndDate]);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === "Escape" && isOpen) {
        onClose();
        if (triggerRef?.current) {
          triggerRef.current.focus();
        }
      }
    };

    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
      return () => document.removeEventListener("keydown", handleKeyDown);
    }
  }, [isOpen, onClose, triggerRef]);

  // Focus the first input field when popup opens
  useEffect(() => {
    if (isOpen && firstInputRef?.current) {
      setTimeout(() => {
        firstInputRef.current.focus();
      }, 100);
    }
  }, [isOpen]);


  const handleSubmit = (e) => {
    e.preventDefault();

    const startErrors = validateDate(startYear, startMonth, startDay, "start");
    const endErrors = validateDate(endYear, endMonth, endDay, "end");

    const allErrors = { ...startErrors, ...endErrors };

    if (Object.keys(allErrors).length === 0) {
      try {
        const startDate = createUTCDateFromParts(
          parseInt(startYear, 10),
          parseInt(startMonth, 10),
          parseInt(startDay, 10)
        );
        const endDate = createUTCDateFromParts(
          parseInt(endYear, 10),
          parseInt(endMonth, 10),
          parseInt(endDay, 10)
        );

        if (startDate > endDate) {
          allErrors.endDay = i18next.t("End date must be after start date");
        }
      } catch (e) {
        allErrors.endDay = i18next.t("Invalid date range");
      }
    }

    setErrors(allErrors);

    if (Object.keys(allErrors).length === 0) {
      const startDate = createUTCDateFromParts(
        parseInt(startYear, 10),
        parseInt(startMonth, 10),
        parseInt(startDay, 10)
      );
      const endDate = createUTCDateFromParts(
        parseInt(endYear, 10),
        parseInt(endMonth, 10),
        parseInt(endDay, 10)
      );

      onSubmit({ start: startDate, end: endDate });
      onClose();
      if (triggerRef?.current) {
        triggerRef.current.focus();
      }
    }
  };

  const handleCancel = () => {
    onClose();
    if (triggerRef?.current) {
      triggerRef.current.focus();
    }
  };

  const handleClose = () => {
    onClose();
    if (triggerRef?.current) {
      triggerRef.current.focus();
    }
  };

  const handleClear = () => {
    onClear();
    onClose();
    if (triggerRef?.current) {
      triggerRef.current.focus();
    }
  };

  return (
    <Popup
      ref={popupRef}
      open={isOpen}
      onClose={handleClose}
      on="click"
      position="bottom right"
      wide
      trigger={<div />}
      className="custom-date-range-popup"
    >
      <Card>
        <Card.Content>
          <Card.Header>{i18next.t("Custom Date Range")}</Card.Header>
          <Form onSubmit={handleSubmit} className="pt-10">
            <Form.Group widths="equal">
              <Form.Field>
                <Grid>
                  <Grid.Column width={3}>
                    <Form.Field>
                      <b>{i18next.t("From")}</b>
                    </Form.Field>
                  </Grid.Column>
                  <Grid.Column width={5} className="pr-5">
                    <Form.Field error={!!errors.startYear}>
                      <label>{i18next.t("Year")}</label>
                      <Input
                        ref={firstInputRef}
                        placeholder="YYYY"
                        value={startYear}
                        onChange={(e) => setStartYear(e.target.value)}
                        onBlur={(e) => setStartYear(formatYear(e.target.value))}
                        maxLength={4}
                      />
                      {errors.startYear && (
                        <div className="ui pointing red basic label">
                          {errors.startYear}
                        </div>
                      )}
                    </Form.Field>
                  </Grid.Column>
                  <Grid.Column width={4} className="pr-5 pl-5">
                    <Form.Field error={!!errors.startMonth}>
                      <label>{i18next.t("Month")}</label>
                      <Input
                        placeholder="MM"
                        value={startMonth}
                        onChange={(e) => setStartMonth(e.target.value)}
                        onBlur={(e) => setStartMonth(formatMonth(e.target.value))}
                        maxLength={2}
                      />
                      {errors.startMonth && (
                        <div className="ui pointing red basic label">
                          {errors.startMonth}
                        </div>
                      )}
                    </Form.Field>
                  </Grid.Column>
                  <Grid.Column width={4} className="pl-5">
                    <Form.Field error={!!errors.startDay}>
                      <label>{i18next.t("Day")}</label>
                      <Input
                        placeholder="DD"
                        value={startDay}
                        onChange={(e) => setStartDay(e.target.value)}
                        onBlur={(e) => setStartDay(formatDay(e.target.value))}
                        maxLength={2}
                      />
                      {errors.startDay && (
                        <div className="ui pointing red basic label">
                          {errors.startDay}
                        </div>
                      )}
                    </Form.Field>
                  </Grid.Column>
                </Grid>
              </Form.Field>
            </Form.Group>

            <Form.Group widths="equal">
              <Form.Field>
                <Grid>
                  <Grid.Column width={3}>
                    <Form.Field>
                      <b>{i18next.t("To")}</b>
                    </Form.Field>
                  </Grid.Column>
                  <Grid.Column width={5} className="pr-5">
                    <Form.Field error={!!errors.endYear}>
                      <Input
                        placeholder="YYYY"
                        value={endYear}
                        onChange={(e) => setEndYear(e.target.value)}
                        onBlur={(e) => setEndYear(formatYear(e.target.value))}
                        maxLength={4}
                      />
                      {errors.endYear && (
                        <div className="ui pointing red basic label">
                          {errors.endYear}
                        </div>
                      )}
                    </Form.Field>
                  </Grid.Column>
                  <Grid.Column width={4} className="pr-5 pl-5">
                    <Form.Field error={!!errors.endMonth}>
                      <Input
                        placeholder="MM"
                        value={endMonth}
                        onChange={(e) => setEndMonth(e.target.value)}
                        onBlur={(e) => setEndMonth(formatMonth(e.target.value))}
                        maxLength={2}
                      />
                      {errors.endMonth && (
                        <div className="ui pointing red basic label">
                          {errors.endMonth}
                        </div>
                      )}
                    </Form.Field>
                  </Grid.Column>
                  <Grid.Column width={4} className="pl-5">
                    <Form.Field error={!!errors.endDay}>
                      <Input
                        placeholder="DD"
                        value={endDay}
                        onChange={(e) => setEndDay(e.target.value)}
                        onBlur={(e) => setEndDay(formatDay(e.target.value))}
                        maxLength={2}
                      />
                      {errors.endDay && (
                        <div className="ui pointing red basic label">
                          {errors.endDay}
                        </div>
                      )}
                    </Form.Field>
                  </Grid.Column>
                </Grid>
              </Form.Field>
            </Form.Group>

            <Form.Group className="pt-5 pb-0">
              <Button type="submit" primary>
                {i18next.t("Apply")}
              </Button>
              <Button type="button" onClick={handleClear}>
                {i18next.t("Clear")}
              </Button>
              <Button type="button" onClick={handleCancel}>
                {i18next.t("Cancel")}
              </Button>
            </Form.Group>
          </Form>
        </Card.Content>
      </Card>
    </Popup>
  );
};

CustomDateRangePopup.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onSubmit: PropTypes.func.isRequired,
  onClear: PropTypes.func.isRequired,
  initialStartDate: PropTypes.instanceOf(Date),
  initialEndDate: PropTypes.instanceOf(Date),
  triggerRef: PropTypes.object,
};

const DateRangeSelector = ({
  dateRange,
  dataFetchRange,
  defaultRangeOptions,
  granularity,
  maxHistoryYears = 15,
  setDateRange,
  setDataFetchRange,
}) => {
  const [isPopupOpen, setIsPopupOpen] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [isCustomRange, setIsCustomRange] = useState(false);
  const menuRef = useRef(null);
  const customButtonRef = useRef(null);
  const todayDate = getCurrentUTCDate();
  const currentPeriodOptions = periodOptions[granularity];
  const [currentSelectedOption, setCurrentSelectedOption] = useState(
    dateRange
      ? getCurrentPeriod(dateRange, granularity, maxHistoryYears)
      : currentPeriodOptions[0].value,
  );

  useEffect(() => {
    if (!dateRange) {
      const defaultPeriod = defaultRangeOptions?.[granularity] || "30days";
      console.log("defaultPeriod", defaultPeriod);
      const initialDateRange = getDateRange(
        todayDate,
        defaultPeriod,
        maxHistoryYears,
      );
      setDateRange(initialDateRange);
      setDataFetchRange(initialDateRange); // Also set initial data fetch range
      setCurrentSelectedOption(defaultPeriod);
    }
  }, []);

  useEffect(() => {
    const newDefaultPeriod = defaultRangeOptions?.[granularity];
    setCurrentSelectedOption(newDefaultPeriod);
    const newDateRange = getDateRange(
      todayDate,
      newDefaultPeriod,
      maxHistoryYears,
    );
    setDateRange(newDateRange);

    // Update dataFetchRange if the new range extends beyond current dataFetchRange
    if (
      !dataFetchRange ||
      newDateRange.start < dataFetchRange.start ||
      newDateRange.end > dataFetchRange.end
    ) {
      setDataFetchRange(newDateRange);
    }
  }, [granularity]);

  const handlePeriodChange = (e, { value }) => {
    if (value === "custom") {
      setIsCustomRange(true);
      setIsPopupOpen(true);
      setIsOpen(false);
    } else {
      setCurrentSelectedOption(value);
      setIsCustomRange(false);
      const newDateRange = getDateRange(todayDate, value, maxHistoryYears);
      setDateRange(newDateRange);

      // Only update dataFetchRange if the new range extends beyond current dataFetchRange
      if (
        !dataFetchRange ||
        newDateRange.start < dataFetchRange.start ||
        newDateRange.end > dataFetchRange.end
      ) {
        setDataFetchRange(newDateRange);
      }

      setIsOpen(false);
    }
  };

  const handleCustomRangeSubmit = (customDateRange) => {
    setDateRange(customDateRange);
    setCurrentSelectedOption("custom");
    setIsCustomRange(true);

    // Only update dataFetchRange if the new range extends beyond current dataFetchRange
    if (
      !dataFetchRange ||
      customDateRange.start < dataFetchRange.start ||
      customDateRange.end > dataFetchRange.end
    ) {
      setDataFetchRange(customDateRange);
    }
  };

  const handleClearCustomRange = () => {
    const defaultPeriod = defaultRangeOptions?.[granularity] || "30days";
    const newDateRange = getDateRange(todayDate, defaultPeriod, maxHistoryYears);
    setDateRange(newDateRange);
    setCurrentSelectedOption(defaultPeriod);
    setIsCustomRange(false);

    // Only update dataFetchRange if the new range extends beyond current dataFetchRange
    if (
      !dataFetchRange ||
      newDateRange.start < dataFetchRange.start ||
      newDateRange.end > dataFetchRange.end
    ) {
      setDataFetchRange(newDateRange);
    }
  };

  const handleMenuOpen = () => {
    setIsOpen(true);
    const selectorElement = document.querySelector(".period-selector");
    if (selectorElement) {
      selectorElement.style.position = "relative";
      selectorElement.style.zIndex = "1000";
    }
  };

  const handleMenuClose = () => {
    setIsOpen(false);
    setTimeout(() => {
      const selectorElement = document.querySelector(".period-selector");
      const menuElement = document.querySelector(".period-selector .menu");
      if (selectorElement) {
        selectorElement.style = "";
      }
      if (menuElement) {
        menuElement.style = "";
      }
    }, 100);
  };

  // Get display text for dropdown
  const getDisplayText = () => {
    if (isCustomRange) {
      return i18next.t("Custom");
    }
    const selectedOption = currentPeriodOptions.find(option => option.value === currentSelectedOption);
    return selectedOption ? selectedOption.text : currentPeriodOptions[0].text;
  };

  return (
    <Segment className="date-range-selector">
      <label
        id="date-range-selector-label"
        className="stats-dashboard-field-label"
        htmlFor="date-range-selector"
      >
        {i18next.t("for the")}
      </label>
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
        text={getDisplayText()}
      />

      <Button
        ref={customButtonRef}
        fluid
        icon="calendar"
        labelPosition="right"
        content={i18next.t("Custom")}
        onClick={() => setIsPopupOpen(true)}
        className="custom-range-button mt-10"
      />

      {isCustomRange && (
        <Button
          fluid
          icon="refresh"
          labelPosition="right"
          content={i18next.t("Clear")}
          onClick={handleClearCustomRange}
          className="clear-custom-button mt-5"
        />
      )}

      <CustomDateRangePopup
        isOpen={isPopupOpen}
        onClose={() => {
          setIsPopupOpen(false);
          if (customButtonRef?.current) {
            customButtonRef.current.focus();
          }
        }}
        onSubmit={handleCustomRangeSubmit}
        onClear={handleClearCustomRange}
        initialStartDate={dateRange?.start}
        initialEndDate={dateRange?.end}
        triggerRef={customButtonRef}
      />
    </Segment>
  );
};

DateRangeSelector.propTypes = {
  dateRange: PropTypes.object,
  dataFetchRange: PropTypes.object,
  defaultRangeOptions: PropTypes.object,
  granularity: PropTypes.string,
  maxHistoryYears: PropTypes.number,
  setDateRange: PropTypes.func,
  setDataFetchRange: PropTypes.func,
};

export { DateRangeSelector };
