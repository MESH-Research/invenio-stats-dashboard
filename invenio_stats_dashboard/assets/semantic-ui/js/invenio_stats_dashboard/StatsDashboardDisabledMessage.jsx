import React from "react";

import { Container, Grid, Message } from "semantic-ui-react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";

const StatsDashboardDisabledMessage = ({ msg, dashboardType }) => {
	const containerClassNames = `${dashboardType}-stats-dashboard`;
	return (
		<Container
			className={`grid ${containerClassNames} ${dashboardType !== "global" ? "rel-m-2" : "rel-mb-2"} stats-dashboard-container`}
			id={`${dashboardType}-stats-dashboard`}
		>
			<Grid.Row>
				<Grid.Column>
					<Message
						info
						header={i18next.t("Dashboard Not Enabled")}
						content={msg}
					/>
				</Grid.Column>
			</Grid.Row>
		</Container>
	);
};

export { StatsDashboardDisabledMessage };
