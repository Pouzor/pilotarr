import React, { useState, useEffect } from "react";
import Icon from "../../components/AppIcon";

import UsageChart from "./components/UsageChart";
import UserStatsCard from "./components/UserStatsCard";
import ServerPerformancePanel from "./components/ServerPerformancePanel";
import DeviceBreakdownCard from "./components/DeviceBreakdownCard";
import MediaAnalyticsTable from "./components/MediaAnalyticsTable";
import {
  getUsageAnalytics,
  getDeviceBreakdown,
  getMediaAnalytics,
  getServerMetrics,
} from "../../services/analyticsService";
import Header from "../../components/navigation/Header";

const JellyfinStatistics = () => {
  const [filters, setFilters] = useState({
    contentType: "all",
    dateRange: "last7days",
    user: "all",
    deviceType: "all",
    customStartDate: "",
    customEndDate: "",
  });

  const [chartType, setChartType] = useState("line");
  const [usageData, setUsageData] = useState([]);
  const [isLoadingUsage, setIsLoadingUsage] = useState(false);
  const [deviceData, setDeviceData] = useState([]);
  const [isLoadingDevices, setIsLoadingDevices] = useState(true);
  const [mediaData, setMediaData] = useState([]);
  const [isLoadingMedia, setIsLoadingMedia] = useState(true);
  const [performanceData, setPerformanceData] = useState(null);
  const [isLoadingPerformance, setIsLoadingPerformance] = useState(true);

  // Calculate date range based on filter
  const getDateRange = () => {
    const endDate = new Date();
    const startDate = new Date();

    if (
      filters?.dateRange === "custom" &&
      filters?.customStartDate &&
      filters?.customEndDate
    ) {
      return {
        start: filters?.customStartDate,
        end: filters?.customEndDate,
      };
    }

    // Default date ranges
    switch (filters?.dateRange) {
      case "last7days":
        startDate?.setDate(endDate?.getDate() - 6);
        break;
      case "last30days":
        startDate?.setDate(endDate?.getDate() - 29);
        break;
      case "last90days":
        startDate?.setDate(endDate?.getDate() - 89);
        break;
      default:
        startDate?.setDate(endDate?.getDate() - 6);
    }

    return {
      start: startDate?.toISOString()?.split("T")?.[0],
      end: endDate?.toISOString()?.split("T")?.[0],
    };
  };

  // Fetch usage analytics data
  const fetchUsageAnalytics = async () => {
    setIsLoadingUsage(true);
    try {
      const { start, end } = getDateRange();
      const data = await getUsageAnalytics(start, end);

      // Transform API response to chart format
      const transformedData =
        data?.map((item) => ({
          date: new Date(item?.date)?.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
          }),
          hoursWatched: item?.hours_watched || 0,
          totalPlays: item?.total_plays || 0,
        })) || [];

      setUsageData(transformedData);
    } catch (error) {
      console.error("Error fetching usage analytics:", error);
      setUsageData([]);
    } finally {
      setIsLoadingUsage(false);
    }
  };

  // Fetch device breakdown data
  const fetchDeviceBreakdown = async () => {
    setIsLoadingDevices(true);
    try {
      const data = await getDeviceBreakdown(365);
      setDeviceData(data);
    } catch (error) {
      console.error("Error fetching device breakdown:", error);
      setDeviceData([]);
    } finally {
      setIsLoadingDevices(false);
    }
  };

  // Fetch media analytics data
  const fetchMediaAnalytics = async () => {
    setIsLoadingMedia(true);
    try {
      const data = await getMediaAnalytics(20, "last_played", "desc");

      // Transform API response to component format
      const transformedData =
        data?.map((item) => ({
          title: item?.series_name || item?.media_title || "Unknown",
          episodeInfo: item?.episode_info || null,
          lastPlayedAt: item?.last_played_at || null,
          thumbnail:
            item?.poster_url ||
            "https://images.unsplash.com/photo-1574267432644-f610f5b7e4d1",
          thumbnailAlt: `${item?.media_title || "Media"} poster`,
          type: item?.media_type === "tv" ? "TV Show" : "Movie",
          plays: item?.plays || 0,
          duration: item?.duration || "N/A",
          quality: item?.quality || "Unknown",
          transcoded: item?.status === "Transcoded",
        })) || [];

      setMediaData(transformedData);
    } catch (error) {
      console.error("Error fetching media analytics:", error);
      setMediaData([]);
    } finally {
      setIsLoadingMedia(false);
    }
  };

  // Fetch server performance metrics
  useEffect(() => {
    const fetchServerMetrics = async () => {
      setIsLoadingPerformance(true);
      try {
        const data = await getServerMetrics();

        // Format memory and storage
        const memoryFormatted = formatMemory(data?.memory_usage_gb || 0);
        const totalMemoryFormatted = formatMemory(data?.memory_total_gb || 0);
        const storageFormatted = formatStorage(data?.storage_used_tb || 0);
        const totalStorageFormatted = formatStorage(
          data?.storage_total_tb || 0,
        );

        // Transform API response to component format
        const transformedData = {
          cpuUsage: data?.cpu_usage_percent || 0,
          cpuStatus: data?.cpu_status || "success",
          memoryUsage: memoryFormatted?.value,
          memoryUnit: memoryFormatted?.unit,
          totalMemory: totalMemoryFormatted?.value,
          totalMemoryUnit: totalMemoryFormatted?.unit,
          memoryStatus: data?.memory_status || "success",
          bandwidth: data?.bandwidth_mbps || 0,
          bandwidthStatus: data?.bandwidth_status || "success",
          maxBandwidth: 1000, // Default max bandwidth
          storageUsed: storageFormatted?.value,
          storageUnit: storageFormatted?.unit,
          totalStorage: totalStorageFormatted?.value,
          storageStatus: data?.storage_status || "success",
          activeTranscodes: data?.active_transcoding_count || 0,
          transcodingSessions:
            data?.active_sessions?.map((session) => ({
              title: session?.media_title || "Unknown",
              user: session?.user_name || "Unknown",
              quality: session?.quality_from || "Unknown",
              targetQuality: session?.quality_to || "Unknown",
              progress: session?.progress || 0,
              speed: session?.speed || 1,
            })) || [],
        };
        setPerformanceData(transformedData);
      } catch (error) {
        console.error("Error fetching server metrics:", error);
        setPerformanceData(null);
      } finally {
        setIsLoadingPerformance(false);
      }
    };

    fetchServerMetrics();
  }, []);

  // Fetch data on mount and when date range changes
  useEffect(() => {
    fetchUsageAnalytics();
    fetchDeviceBreakdown();
    fetchMediaAnalytics();
  }, [filters?.dateRange, filters?.customStartDate, filters?.customEndDate]);

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleApplyFilters = () => {
    console.log("Applying filters:", filters);
    fetchUsageAnalytics();
  };

  const handleResetFilters = () => {
    setFilters({
      contentType: "all",
      dateRange: "last7days",
      user: "all",
      deviceType: "all",
      customStartDate: "",
      customEndDate: "",
    });
  };

  const handleExport = () => {
    console.log("Exporting data with filters:", filters);
  };

  // Utility functions for formatting memory and storage
  const formatMemory = (valueInGb) => {
    if (valueInGb < 1) {
      // Convert to MB and round
      return {
        value: Math.round(valueInGb * 1024),
        unit: "MB",
      };
    }
    return {
      value: parseFloat(valueInGb?.toFixed(2)),
      unit: "GB",
    };
  };

  const formatStorage = (valueInTb) => {
    if (valueInTb < 1) {
      // Convert to GB and round to 2 decimal places
      return {
        value: parseFloat((valueInTb * 1024)?.toFixed(2)),
        unit: "GB",
      };
    }
    return {
      value: parseFloat(valueInTb?.toFixed(2)),
      unit: "TB",
    };
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="pt-20 md:pt-24 px-4 md:px-6 lg:px-8 pb-8">
        <div className="max-w-7xl mx-auto">
          <div className="mb-6 md:mb-8">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Icon name="BarChart2" size={20} color="var(--color-primary)" />
              </div>
              <div>
                <h1 className="text-2xl md:text-3xl font-bold text-foreground">
                  Jellyfin Statistics
                </h1>
                <p className="text-sm text-muted-foreground">
                  Comprehensive media server analytics and performance
                  monitoring
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 md:gap-8 mb-6 md:mb-8">
            <div className="lg:col-span-2">
              <UsageChart
                data={usageData}
                chartType={chartType}
                onChartTypeChange={setChartType}
                isLoading={isLoadingUsage}
              />
            </div>
            <UserStatsCard
              totalUsers={156}
              activeUsers={42}
              newUsers={12}
              growthRate={8.5}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
            <ServerPerformancePanel
              performanceData={performanceData}
              isLoading={isLoadingPerformance}
            />
            <DeviceBreakdownCard
              deviceData={deviceData}
              isLoading={isLoadingDevices}
            />
          </div>

          <MediaAnalyticsTable data={mediaData} isLoading={isLoadingMedia} />
        </div>
      </main>
    </div>
  );
};

export default JellyfinStatistics;
