import React, { useState, useMemo, useEffect } from "react";
import Header from "../../components/navigation/Header";

import Icon from "../../components/AppIcon";

import MediaGrid from "./components/MediaGrid";
import FilterToolbar from "./components/FilterToolbar";
import { getRecentItems } from "../../services/libraryService";

/**
 * Format file size from API response
 * Handles both string formats ("8.5 GB") and numeric bytes
 * @param {string|number} size - Size from API (string with units or number in bytes)
 * @returns {string} Formatted size string
 */
const formatFileSize = (size) => {
  // If size is null or undefined
  if (!size && size !== 0) return "0.0 GB";

  // If size is already a string with units (e.g., "8.5 GB", "142.8 GB")
  if (typeof size === "string") {
    // Check if it already contains GB, MB, KB, etc.
    if (/\d+(\.\d+)?\s*(GB|MB|KB|TB)/i?.test(size)) {
      return size;
    }
    // Try to parse as number if it's a numeric string
    const parsed = parseFloat(size);
    if (isNaN(parsed)) return "0.0 GB";
    size = parsed;
  }

  // If size is 0
  if (size === 0) return "0.0 GB";

  // If size is a number, assume it's in bytes and convert to GB
  // Only convert if the number is large enough to be bytes (> 1024)
  if (typeof size === "number") {
    if (size > 1024) {
      // Likely in bytes, convert to GB
      return `${(size / 1024 ** 3)?.toFixed(1)} GB`;
    } else {
      // Small number, likely already in GB
      return `${size?.toFixed(1)} GB`;
    }
  }

  return "0.0 GB";
};

/**
 * Aggregate an array of torrent info objects into summary values
 * @param {Array} torrentInfoArray - Array of {seeding_time, ratio, size, download_date, status}
 * @returns {Object} Aggregated values
 */
const aggregateTorrentInfo = (torrentInfoArray) => {
  if (!Array.isArray(torrentInfoArray) || torrentInfoArray.length === 0) {
    return null;
  }

  const count = torrentInfoArray.length;

  const ratios = torrentInfoArray.map((t) => t?.ratio).filter((r) => r != null);
  const seedingTimes = torrentInfoArray
    .map((t) => t?.seeding_time)
    .filter((s) => s != null);
  const sizes = torrentInfoArray.map((t) => t?.size).filter((s) => s != null);
  const dates = torrentInfoArray
    .map((t) => t?.download_date)
    .filter((d) => d != null);
  const statuses = torrentInfoArray
    .map((t) => t?.status)
    .filter((s) => s != null);

  const avgRatio =
    ratios.length > 0 ? ratios.reduce((a, b) => a + b, 0) / ratios.length : 0;
  const avgSeedingTime =
    seedingTimes.length > 0
      ? seedingTimes.reduce((a, b) => a + b, 0) / seedingTimes.length
      : 0;
  const totalSize = sizes.reduce((a, b) => a + b, 0);
  const latestDate =
    dates.length > 0 ? dates.reduce((a, b) => (a > b ? a : b)) : null;
  const uniqueStatuses = [...new Set(statuses)];
  const status =
    uniqueStatuses.length === 1 ? uniqueStatuses[0] : "downloading";

  return {
    ratio: avgRatio,
    seedingTime: avgSeedingTime,
    size: totalSize,
    downloadedDate: latestDate,
    status,
    torrentCount: count,
  };
};

const Library = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState({
    contentType: "all",
    quality: "all",
    sortBy: "added_date",
    order: "desc",
  });
  const [limit, setLimit] = useState(20);
  const [mediaData, setMediaData] = useState([]);
  const [loading, setLoading] = useState(true);

  // Fetch data from API
  useEffect(() => {
    const fetchMediaData = async () => {
      setLoading(true);
      try {
        const data = await getRecentItems(
          limit,
          filters?.sortBy,
          filters?.order,
        );
        // Transform API response to match component structure
        const transformedData =
          data?.map((item) => {
            const agg = aggregateTorrentInfo(item?.torrent_info);
            return {
              id: item?.id,
              title: item?.title,
              type: item?.media_type,
              quality: item?.quality || "N/A",
              size: item?.size || "0.0 GB",
              addedDate: item?.created_at?.split("T")?.[0] || item?.added_date,
              viewCount: 99, // Hard-coded as requested
              torrent_info: item?.torrent_info,
              torrentCount: agg?.torrentCount || item?.torrent_count || 0,
              hasSubtitles: true,
              seedRatio: agg?.ratio || 0,
              nbMedia: item?.nb_media || 0,
              image: item?.image_url || "https://via.placeholder.com/300x450",
              imageAlt: item?.image_alt || `${item?.title} poster`,
            };
          }) || [];
        setMediaData(transformedData);
      } catch (error) {
        console.error("Error loading media data:", error);
        setMediaData([]);
      } finally {
        setLoading(false);
      }
    };

    fetchMediaData();
  }, [limit, filters?.sortBy, filters?.order]);

  // Filter and search logic (removed sorting - now handled by API)
  const filteredMedia = useMemo(() => {
    let result = [...mediaData];

    // Apply search filter
    if (searchQuery) {
      result = result?.filter((item) =>
        item?.title?.toLowerCase()?.includes(searchQuery?.toLowerCase()),
      );
    }

    // Apply content type filter
    if (filters?.contentType !== "all") {
      result = result?.filter((item) => item?.type === filters?.contentType);
    }

    // Apply quality filter
    if (filters?.quality !== "all") {
      result = result?.filter((item) =>
        item?.quality?.includes(filters?.quality),
      );
    }

    return result;
  }, [searchQuery, filters?.contentType, filters?.quality, mediaData]);

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="container mx-auto px-4 py-6 md:py-8">
        {/* Page Header */}
        <div className="mb-6 md:mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <Icon name="Library" size={20} color="var(--color-primary)" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-foreground">
                Media Library
              </h1>
              <p className="text-sm text-muted-foreground">
                Browse and manage your complete Jellyfin collection
              </p>
            </div>
          </div>
        </div>

        {/* Filter Toolbar */}
        <FilterToolbar
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          filters={filters}
          onFilterChange={handleFilterChange}
          totalResults={filteredMedia?.length}
        />

        {/* Media Grid */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
              <p className="text-muted-foreground">Loading media library...</p>
            </div>
          </div>
        ) : (
          <MediaGrid media={filteredMedia} />
        )}

        {/* Limit Selector */}
        <div className="mt-8 flex items-center justify-center gap-4">
          <span className="text-sm text-muted-foreground">Items per page:</span>
          <div className="flex gap-2">
            {[20, 50, 100]?.map((value) => (
              <button
                key={value}
                onClick={() => setLimit(value)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  limit === value
                    ? "bg-primary text-white"
                    : "bg-card text-foreground hover:bg-primary/10"
                }`}
              >
                {value}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Library;
