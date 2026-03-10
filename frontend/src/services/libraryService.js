import pilotarrClient from "../lib/pilotarrClient";

/**
 * Get recent items (media and request) from dashboard API
 * @param {number} limit - Number of items to fetch
 * @param {string} sortBy - Sort field (added_date, ratio, size, title)
 * @param {string} sortOrder - Sort order (asc, desc)
 * @returns {Promise<Array>} Array of recent items
 */
export const getRecentItems = async (limit = 10, sortBy = "added_date", sortOrder = "desc") => {
  try {
    const response = await pilotarrClient?.get(
      `/dashboard/recent-items?limit=${limit}&sort_by=${sortBy}&sort_order=${sortOrder}`,
    );
    return response?.data || [];
  } catch (error) {
    console.error("Error fetching recent items:", error?.message);
    return [];
  }
};

/**
 * Get all library items
 * @param {number} limit - Number of items to fetch
 * @param {string} sortBy - Sort field (added_date, ratio, size, title)
 * @param {string} sortOrder - Sort order (asc, desc)
 * @returns {Promise<Array>} Array item
 */
export const getLibraryItems = async (
  limit = 18,
  sortBy = "added_date",
  sortOrder = "desc",
  { search, mediaType, quality } = {},
) => {
  try {
    const params = new URLSearchParams({ sort_by: sortBy, sort_order: sortOrder });
    if (limit !== null) params.append("limit", limit);
    if (search) params.append("search", search);
    if (mediaType && mediaType !== "all") params.append("media_type", mediaType);
    if (quality && quality !== "all") params.append("quality", quality);
    const response = await pilotarrClient?.get(`/library?${params}`);
    return response?.data || { items: [], total: 0 };
  } catch (error) {
    console.error("Error fetching library items:", error?.message);
    return { items: [], total: 0 };
  }
};

/**
 * Get library item by id
 * @param {string} id - Media item ID
 * @returns {Promise<Object|null>} Media detail object or null
 */
export const getLibraryItemById = async (id) => {
  try {
    const response = await pilotarrClient?.get(`/library/${id}`);
    return response?.data || [];
  } catch (error) {
    console.error("Error fetching library items:", error?.message);
    return null;
  }
};

/**
 * Get all seasons with embedded episodes for a TV show (single request)
 * @param {string} id - Library item ID
 * @returns {Promise<Array>} Array of seasons with episodes
 */
export const getSeasonsWithEpisodes = async (id) => {
  try {
    const response = await pilotarrClient?.get(`/library/${id}/seasons-with-episodes`);
    return response?.data || [];
  } catch (error) {
    console.error("Error fetching seasons with episodes:", error?.message);
    return [];
  }
};

export const setEpisodeWatched = async (mediaId, seasonNumber, episodeNumber, watched) => {
  try {
    await pilotarrClient?.patch(
      `/library/${mediaId}/seasons/${seasonNumber}/episodes/${episodeNumber}/watched`,
      { watched },
    );
    return true;
  } catch (error) {
    console.error("Error updating episode watched:", error?.message);
    return false;
  }
};

export const setSeasonWatched = async (mediaId, seasonNumber, watched) => {
  try {
    await pilotarrClient?.patch(`/library/${mediaId}/seasons/${seasonNumber}/watched`, { watched });
    return true;
  } catch (error) {
    console.error("Error updating season watched:", error?.message);
    return false;
  }
};

export const monitorEpisode = async (mediaId, seasonNumber, episodeNumber) => {
  try {
    await pilotarrClient?.post(
      `/library/${mediaId}/seasons/${seasonNumber}/episodes/${episodeNumber}/monitor`,
    );
    return true;
  } catch (error) {
    console.error("Error monitoring episode:", error?.message);
    return false;
  }
};

export const searchEpisode = async (mediaId, seasonNumber, episodeNumber) => {
  try {
    await pilotarrClient?.post(
      `/library/${mediaId}/seasons/${seasonNumber}/episodes/${episodeNumber}/search`,
    );
    return true;
  } catch (error) {
    console.error("Error searching episode:", error?.message);
    return false;
  }
};

export const refreshMediaItem = async (id) => {
  const response = await pilotarrClient?.post(`/library/${id}/refresh`);
  return response?.data;
};
