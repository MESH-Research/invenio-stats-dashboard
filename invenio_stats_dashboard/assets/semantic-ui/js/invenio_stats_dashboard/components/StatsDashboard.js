import React from "react";
import PropTypes from "prop-types";
import { Container } from "semantic-ui-react";

export const StatsDashboard = ({ config }) => {
  return (
    <Container fluid>
      <h1>Stats Dashboard</h1>
      {/* Add your dashboard content here */}
    </Container>
  );
};

StatsDashboard.propTypes = {
  config: PropTypes.object.isRequired,
};