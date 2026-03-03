import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../../components/navigation/Header";
import FilterToolbar from "./components/FilterToolbar";
import RequestCard from "../main-dashboard/components/RequestCard";
import Icon from "../../components/AppIcon";
import Button from "../../components/ui/Button";
import {
  getJellyseerrRequests,
  approveRequest,
  declineRequest,
} from "../../services/requestService";

const JellyseerrRequests = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [requests, setRequests] = useState([]);
  const [filteredRequests, setFilteredRequests] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState({
    status: "all",
    type: "all",
    user: "all",
  });

  useEffect(() => {
    loadRequests();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [requests, searchQuery, filters]);

  const loadRequests = async () => {
    setLoading(true);
    try {
      // Fetch all requests from API (no status filter to get all)
      const data = await getJellyseerrRequests("all", 100);
      setRequests(data);
    } catch (error) {
      console.error("Error loading requests:", error);
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = [...requests];

    // Search filter
    if (searchQuery) {
      filtered = filtered?.filter((request) =>
        request?.title?.toLowerCase()?.includes(searchQuery?.toLowerCase()),
      );
    }

    // Status filter - map numeric status to string
    if (filters?.status !== "all") {
      const statusMap = {
        pending: 1,
        approved: 2,
        declined: 3,
        available: 4,
      };
      const numericStatus = statusMap?.[filters?.status];
      filtered = filtered?.filter((request) => request?.status === numericStatus);
    }

    // Type filter
    if (filters?.type !== "all") {
      filtered = filtered?.filter((request) => request?.mediaType === filters?.type);
    }

    // User filter
    if (filters?.user !== "all") {
      filtered = filtered?.filter((request) => request?.requestedBy === filters?.user);
    }

    setFilteredRequests(filtered);
  };

  const handleFilterChange = (filterName, value) => {
    setFilters((prev) => ({
      ...prev,
      [filterName]: value,
    }));
  };

  const handleApproveRequest = async (id) => {
    const success = await approveRequest(id);
    if (success) {
      setRequests((prev) => prev?.map((req) => (req?.id === id ? { ...req, status: 2 } : req)));
    }
  };

  const handleRejectRequest = async (id) => {
    const success = await declineRequest(id);
    if (success) {
      setRequests((prev) => prev?.map((req) => (req?.id === id ? { ...req, status: 3 } : req)));
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      1: "bg-blue-500/10 text-blue-400 border-blue-500/20",
      2: "bg-green-500/10 text-green-400 border-green-500/20",
      3: "bg-red-500/10 text-red-400 border-red-500/20",
      4: "bg-purple-500/10 text-purple-400 border-purple-500/20",
    };
    return colors?.[status] || colors?.[1];
  };

  const getStatusIcon = (status) => {
    const icons = {
      1: "Clock",
      2: "CheckCircle",
      3: "XCircle",
      4: "PackageCheck",
    };
    return icons?.[status] || "Clock";
  };

  const getStatusLabel = (status) => {
    const labels = {
      1: "pending",
      2: "approved",
      3: "declined",
      4: "available",
    };
    return labels?.[status] || "pending";
  };

  // Get unique users for filter
  const uniqueUsers = ["all", ...new Set(requests?.map((r) => r?.requestedBy))];

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="container mx-auto px-4 pt-20 md:pt-24 pb-6 md:pb-8">
        {/* Page Header */}
        <div className="mb-6 md:mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <Icon name="Film" size={20} color="var(--color-primary)" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-foreground">
                Jellyseerr Requests
              </h1>
              <p className="text-sm text-muted-foreground">
                Manage all media requests with comprehensive filtering and status tracking
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
          totalResults={filteredRequests?.length}
          uniqueUsers={uniqueUsers}
        />

        {/* Status Summary */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          {[1, 2, 3, 4]?.map((statusNum) => {
            const count = requests?.filter((r) => r?.status === statusNum)?.length;
            const statusLabel = getStatusLabel(statusNum);
            return (
              <div
                key={statusNum}
                className="bg-card border border-border rounded-lg p-4 hover:shadow-elevation-1 transition-smooth cursor-pointer"
                onClick={() => handleFilterChange("status", statusLabel)}
              >
                <div className="flex items-center gap-2 mb-2">
                  <Icon
                    name={getStatusIcon(statusNum)}
                    size={18}
                    className="text-muted-foreground"
                  />
                  <span className="text-sm font-medium text-muted-foreground capitalize">
                    {statusLabel}
                  </span>
                </div>
                <p className="text-2xl font-bold text-foreground">{count}</p>
              </div>
            );
          })}
        </div>

        {/* Requests Grid */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Icon name="Loader" size={32} className="animate-spin text-muted-foreground" />
          </div>
        ) : filteredRequests?.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {filteredRequests?.map((request) => (
              <RequestCard
                key={request?.id}
                request={request}
                onApprove={handleApproveRequest}
                onReject={handleRejectRequest}
              />
            ))}
          </div>
        ) : (
          <div className="bg-card border border-border rounded-lg p-12 text-center">
            <Icon name="Search" size={48} className="mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-semibold text-foreground mb-2">No requests found</h3>
            <p className="text-muted-foreground mb-4">
              {searchQuery ||
              filters?.status !== "all" ||
              filters?.type !== "all" ||
              filters?.user !== "all"
                ? "Try adjusting your filters"
                : "No requests available at the moment"}
            </p>
            {(searchQuery ||
              filters?.status !== "all" ||
              filters?.type !== "all" ||
              filters?.user !== "all") && (
              <Button
                variant="outline"
                onClick={() => {
                  setSearchQuery("");
                  setFilters({ status: "all", type: "all", user: "all" });
                }}
              >
                Clear All Filters
              </Button>
            )}
          </div>
        )}
      </main>
    </div>
  );
};

export default JellyseerrRequests;
