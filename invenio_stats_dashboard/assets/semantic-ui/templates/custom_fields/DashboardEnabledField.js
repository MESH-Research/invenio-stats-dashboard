import React from "react";
import { Form } from "semantic-ui-react";
import { BooleanCheckbox, FieldLabel } from "react-invenio-forms";
import PropTypes from "prop-types";

/**
 * Part of Invenio-Stats-Dashboard
 * Copyright (C) 2025 Mesh Research
 *
 * Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
 * it under the terms of the MIT License; see LICENSE file for more details.
 *
 * UI form field template for the stats:dashboard_enabled field
 */

const DashboardEnabledField = ({
  fieldPath,
  fieldValue,
  icon,
  label,
  description,
  trueLabel,
  falseLabel,
  helpText,
  ...restProps
}) => {
  return (
    <Form.Field id={fieldPath} name={fieldPath}>
      <BooleanCheckbox
        fieldPath={fieldPath}
        label={label}
        trueLabel={trueLabel}
        falseLabel={falseLabel}
        icon={icon}
        required={false}
        description={description}
        aria-describedby={`${fieldPath}-help-text`}
      />
      {!!helpText && (
        <label id={`${fieldPath}-help-text`} className="helptext label">
          {helpText}
        </label>
      )}
    </Form.Field>
  );
};

DashboardEnabledField.propTypes = {
  fieldPath: PropTypes.string.isRequired,
  fieldValue: PropTypes.bool,
  icon: PropTypes.string,
  label: PropTypes.string,
  description: PropTypes.string,
  trueLabel: PropTypes.string,
  falseLabel: PropTypes.string,
  helpText: PropTypes.string,
};

DashboardEnabledField.defaultProps = {
  fieldValue: false,
  icon: undefined,
  label: undefined,
  description: undefined,
  trueLabel: undefined,
  falseLabel: undefined,
  helpText: undefined,
};

export default DashboardEnabledField;
