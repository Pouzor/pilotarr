import pilotarrClient from "../lib/pilotarrClient";

/**
 * Analytics Service
 * Handles fetching analytics data from Pilotarr API
 */

/**
 * Fetch usage analytics data
 * @param {string} startDate - Start date in YYYY-MM-DD format
 * @param {string} endDate - End date in YYYY-MM-DD format
 * @returns {Promise<Array>} Usage analytics data
 */
export const getUsageAnalytics = async (startDate, endDate) => {
  try {
    const response = await pilotarrClient?.get("/analytics/usage", {
      params: {
        start_date: startDate,
        end_date: endDate,
      },
    });
    return response?.data || [];
  } catch (error) {
    console.error("Failed to fetch usage analytics:", error);
    return [];
  }
};

/**
 * Fetch device breakdown analytics data
 * @param {number} periodDays - Number of days to analyze (default: 365)
 * @returns {Promise<Array>} Device breakdown data
 */
export const getDeviceBreakdown = async (periodDays = 365) => {
  try {
    const response = await pilotarrClient?.get("/analytics/devices", {
      params: {
        period_days: periodDays,
      },
    });
    return response?.data || [];
  } catch (error) {
    console.error("Failed to fetch device breakdown:", error);
    return [];
  }
};

/**
 * Fetch media playback analytics data
 * @param {number} limit - Number of media items to fetch (default: 10)
 * @param {string} sortBy - Field to sort by (default: 'plays')
 * @param {string} order - Sort order 'asc' or 'desc' (default: 'desc')
 * @returns {Promise<Array>} Media analytics data
 */
export const getMediaAnalytics = async (
  limit = 10,
  sortBy = "plays",
  order = "desc",
) => {
  try {
    const response = await pilotarrClient?.get("/analytics/media", {
      params: {
        limit,
        sort_by: sortBy,
        order,
      },
    });
    return response?.data || [];
  } catch (error) {
    console.error("Failed to fetch media analytics:", error);
    return [];
  }
};

/**
 * Fetch server performance metrics
 * @returns {Promise<Object>} Server metrics data including CPU, memory, storage, bandwidth, and active sessions
 */
export const getServerMetrics = async () => {
  try {
    const response = await pilotarrClient?.get("/analytics/server-metrics");
    return response?.data || null;
  } catch (error) {
    console.error("Failed to fetch server metrics:", error);
    return null;
  }
};

/**
 * Fetch playback sessions for a date range
 * @param {string} start - Start date YYYY-MM-DD
 * @param {string} end - End date YYYY-MM-DD
 * @returns {Promise<Array>} Playback sessions
 */
export const getPlaybackSessions = async (start, end) => {
  try {
    const params = new URLSearchParams();
    if (start) params.append("start", start);
    if (end) params.append("end", end);
    const response = await pilotarrClient?.get(`/analytics/sessions?${params}`);
    return response?.data || [];
  } catch (error) {
    return [];
  }
};

export default {
  getUsageAnalytics,
  getDeviceBreakdown,
  getMediaAnalytics,
  getServerMetrics,
  getPlaybackSessions,
};
