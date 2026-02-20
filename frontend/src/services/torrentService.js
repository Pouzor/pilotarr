import pilotarrClient from "../lib/pilotarrClient";

/**
 * Torrent Operations
 */

// Get all torrents + global transfer stats from the active torrent client
export const getTorrents = async () => {
  const response = await pilotarrClient.get("/torrents/all");
  return response.data;
};

export default { getTorrents };
