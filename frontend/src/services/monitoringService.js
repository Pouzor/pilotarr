import pilotarrClient from "../lib/pilotarrClient";

export const getMonitoringItems = async () => {
  try {
    const response = await pilotarrClient.get("/monitoring/items");
    return response?.data || [];
  } catch (error) {
    console.error("Error fetching monitoring items:", error?.message);
    return [];
  }
};
