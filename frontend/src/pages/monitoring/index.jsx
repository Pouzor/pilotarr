import React, { useState, useMemo, useEffect } from "react";
import Header from "../../components/navigation/Header";
import Icon from "../../components/AppIcon";
import FilterToolbar from "./components/FilterToolbar";
import MonitoringTable from "./components/MonitoringTable";
import Button from "../../components/ui/Button";
import { getMonitoringItems } from "../../services/monitoringService";

const Monitoring = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState({
    service: "all",
    status: "all",
    quality: "all",
  });
  const [selectedItems, setSelectedItems] = useState([]);
  const [monitoringData, setMonitoringData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const raw = await getMonitoringItems();
        const mapped = raw.map((item) => ({
          id: item.id,
          title: item.title,
          year: item.year,
          service: item.service,
          monitoringStatus: item.monitoring_status,
          availabilityStatus: item.availability_status,
          qualityProfile: item.quality_profile,
          lastUpdated: item.last_updated,
          fileSize: item.file_size,
          imageUrl: item.image_url,
          seasons: item.seasons,
          downloadHistory: item.download_history,
        }));
        setMonitoringData(mapped);
      } catch (err) {
        setError("Failed to load monitoring data.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  // Filter logic
  const filteredData = useMemo(() => {
    let result = [...monitoringData];

    // Search filter
    if (searchQuery) {
      result = result?.filter((item) =>
        item?.title?.toLowerCase()?.includes(searchQuery?.toLowerCase()),
      );
    }

    // Service filter
    if (filters?.service !== "all") {
      result = result?.filter((item) => item?.service === filters?.service);
    }

    // Status filter
    if (filters?.status !== "all") {
      result = result?.filter(
        (item) => item?.availabilityStatus === filters?.status,
      );
    }

    // Quality filter
    if (filters?.quality !== "all") {
      result = result?.filter((item) =>
        item?.qualityProfile?.includes(filters?.quality),
      );
    }

    return result;
  }, [searchQuery, filters, monitoringData]);

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleSelectAll = (checked) => {
    if (checked) {
      setSelectedItems(filteredData?.map((item) => item?.id));
    } else {
      setSelectedItems([]);
    }
  };

  const handleSelectItem = (id, checked) => {
    if (checked) {
      setSelectedItems((prev) => [...prev, id]);
    } else {
      setSelectedItems((prev) => prev?.filter((itemId) => itemId !== id));
    }
  };

  const handleBulkAction = (action) => {
    console.log(`Bulk action: ${action} on items:`, selectedItems);
    // Implement bulk action logic here
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="container mx-auto px-4 py-6 md:py-8">
        {/* Page Header */}
        <div className="mb-6 md:mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <Icon name="Monitor" size={20} color="var(--color-primary)" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-foreground">
                Media Monitoring
              </h1>
              <p className="text-sm text-muted-foreground">
                Comprehensive oversight of all Sonarr and Radarr monitored
                content
              </p>
            </div>
          </div>
        </div>

        {/* Loading / Error states */}
        {isLoading && (
          <div className="flex items-center justify-center py-16">
            <Icon
              name="Loader"
              size={24}
              className="animate-spin text-primary mr-2"
            />
            <span className="text-muted-foreground">
              Loading monitoring data...
            </span>
          </div>
        )}

        {!isLoading && error && (
          <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-4 mb-6 flex items-center gap-2">
            <Icon name="AlertCircle" size={18} className="text-destructive" />
            <span className="text-sm text-destructive">{error}</span>
          </div>
        )}

        {!isLoading && !error && (
          <>
            {/* Filter Toolbar */}
            <FilterToolbar
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              filters={filters}
              onFilterChange={handleFilterChange}
              totalResults={filteredData?.length}
            />

            {/* Bulk Actions */}
            {selectedItems?.length > 0 && (
              <div className="bg-primary/10 border border-primary/30 rounded-lg p-4 mb-6 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Icon name="CheckSquare" size={18} className="text-primary" />
                  <span className="text-sm font-medium text-foreground">
                    {selectedItems?.length}{" "}
                    {selectedItems?.length === 1 ? "item" : "items"} selected
                  </span>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    iconName="Play"
                    onClick={() => handleBulkAction("monitor")}
                  >
                    Monitor
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    iconName="Pause"
                    onClick={() => handleBulkAction("unmonitor")}
                  >
                    Unmonitor
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    iconName="RefreshCw"
                    onClick={() => handleBulkAction("refresh")}
                  >
                    Refresh
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    iconName="Search"
                    onClick={() => handleBulkAction("search")}
                  >
                    Search
                  </Button>
                </div>
              </div>
            )}

            {/* Monitoring Table */}
            <MonitoringTable
              data={filteredData}
              selectedItems={selectedItems}
              onSelectAll={handleSelectAll}
              onSelectItem={handleSelectItem}
            />
          </>
        )}
      </div>
    </div>
  );
};

export default Monitoring;
