
const statsApiClient = {
  getStats: async (communityId, dashboardType) => {
    const response = await fetch(`/api/stats/${communityId}/${dashboardType}`);
    return response.json();
  }
};

export { statsApiClient };