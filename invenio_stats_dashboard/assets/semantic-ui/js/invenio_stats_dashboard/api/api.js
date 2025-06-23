import { axios } from "axios";
import { DASHBOARD_TYPES } from "../constants";

/**
 * API client for requesting stats to populate a stats dashboard.
 *
 * Returns a promise that resolves to an object with the following keys:
 * - record_deltas
 * - record_snapshots
 * - usage_deltas
 * - usage_snapshots
 *
 * Each property is an array of objects, each representing one day of stats.
 *
 * @param {string} communityId - The ID of the community to get stats for.
 * @param {string} dashboardType - The type of dashboard to get stats for.
 * @param {string} startDate - The start date of the stats. If not provided, the stats will begin at the earliest date in the data.
 * @param {string} endDate - The end date of the stats. If not provided, the stats will end at the current date or latest date in the data.
 *
 * @returns {Promise<Object>} - The stats data.
 */
const statsApiClient = {
  getStats: async (communityId, dashboardType, startDate = null, endDate = null) => {
    if (dashboardType === DASHBOARD_TYPES.GLOBAL) {
      communityId = "global";
    }
    let requestBody = {
      [`${dashboardType}-stats`]: {
        "stat": `${dashboardType}-stats`,
        "params": {
          "community_id": communityId,
        }
      },
    };
    if (startDate) {
      requestBody[`${dashboardType}-stats`].start_date = startDate;
    }
    if (endDate) {
      requestBody[`${dashboardType}-stats`].end_date = endDate;
    }
    const response = await axios.post(`/api/stats`, requestBody);
    return response.data;
  }
};

export { statsApiClient };