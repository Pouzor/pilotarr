import React, { useState, useEffect } from "react";
import Header from "../../components/navigation/Header";
import Icon from "../../components/AppIcon";
import Button from "../../components/ui/Button";
import Select from "../../components/ui/Select";
import { Checkbox } from "../../components/ui/Checkbox";
import AlertCard from "./components/AlertCard";
import AlertHistory from "./components/AlertHistory";
import FilterToolbar from "./components/FilterToolbar";

const Alerts = () => {
  const [activeTab, setActiveTab] = useState("all");
  const [selectedAlerts, setSelectedAlerts] = useState([]);
  const [alerts, setAlerts] = useState([
    {
      id: 1,
      type: "connection",
      service: "Radarr",
      severity: "error",
      message: "Failed to connect to Radarr API",
      details:
        "Connection timeout after 30 seconds. Please verify the API URL and network connectivity.",
      timestamp: new Date(Date.now() - 300000),
      dismissed: false,
      suggestions: [
        "Check API URL configuration",
        "Verify network connectivity",
        "Ensure Radarr service is running",
      ],
    },
    {
      id: 2,
      type: "api",
      service: "Sonarr",
      severity: "warning",
      message: "API rate limit approaching",
      details:
        "Current API usage is at 85% of the rate limit. Consider reducing request frequency.",
      timestamp: new Date(Date.now() - 600000),
      dismissed: false,
      suggestions: [
        "Increase refresh interval",
        "Review automated tasks",
        "Contact Sonarr support for rate limit increase",
      ],
    },
    {
      id: 3,
      type: "request",
      service: "Jellyseerr",
      severity: "error",
      message: "Failed to process media request",
      details:
        'Request for "The Matrix Resurrections" failed due to invalid TMDB ID.',
      timestamp: new Date(Date.now() - 900000),
      dismissed: false,
      suggestions: [
        "Verify TMDB ID is correct",
        "Check Jellyseerr logs",
        "Retry the request manually",
      ],
    },
    {
      id: 4,
      type: "system",
      service: "Jellyfin",
      severity: "warning",
      message: "High CPU usage detected",
      details:
        "Jellyfin server CPU usage has exceeded 80% for the last 10 minutes.",
      timestamp: new Date(Date.now() - 1200000),
      dismissed: false,
      suggestions: [
        "Check active transcoding sessions",
        "Review server resources",
        "Consider hardware upgrade",
      ],
    },
    {
      id: 5,
      type: "connection",
      service: "Sonarr",
      severity: "error",
      message: "Database connection lost",
      details:
        "Lost connection to Sonarr database. Service may be unavailable.",
      timestamp: new Date(Date.now() - 1800000),
      dismissed: false,
      suggestions: [
        "Restart Sonarr service",
        "Check database server status",
        "Review database logs",
      ],
    },
    {
      id: 6,
      type: "api",
      service: "Radarr",
      severity: "info",
      message: "API key rotation recommended",
      details:
        "Your Radarr API key has been in use for over 90 days. Consider rotating for security.",
      timestamp: new Date(Date.now() - 2400000),
      dismissed: false,
      suggestions: [
        "Generate new API key in Radarr settings",
        "Update API key in ServarrHub",
        "Test connection after update",
      ],
    },
  ]);

  const [dismissedAlerts, setDismissedAlerts] = useState([]);
  const [filters, setFilters] = useState({
    dateRange: "all",
    service: "all",
    severity: "all",
    status: "active",
  });
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [showHistory, setShowHistory] = useState(false);

  const tabs = [
    {
      id: "all",
      label: "All Alerts",
      count: alerts?.filter((a) => !a?.dismissed)?.length,
    },
    {
      id: "connection",
      label: "Connection Failures",
      count: alerts?.filter((a) => a?.type === "connection" && !a?.dismissed)
        ?.length,
    },
    {
      id: "api",
      label: "API Errors",
      count: alerts?.filter((a) => a?.type === "api" && !a?.dismissed)?.length,
    },
    {
      id: "request",
      label: "Failed Requests",
      count: alerts?.filter((a) => a?.type === "request" && !a?.dismissed)
        ?.length,
    },
    {
      id: "system",
      label: "System Warnings",
      count: alerts?.filter((a) => a?.type === "system" && !a?.dismissed)
        ?.length,
    },
  ];

  const handleDismiss = (alertId) => {
    const alert = alerts?.find((a) => a?.id === alertId);
    if (alert) {
      setAlerts(
        alerts?.map((a) => (a?.id === alertId ? { ...a, dismissed: true } : a)),
      );
      setDismissedAlerts([
        ...dismissedAlerts,
        { ...alert, dismissedAt: new Date() },
      ]);
      setSelectedAlerts(selectedAlerts?.filter((id) => id !== alertId));
    }
  };

  const handleDismissSelected = () => {
    const now = new Date();
    const dismissedItems = alerts?.filter((a) =>
      selectedAlerts?.includes(a?.id),
    );
    setAlerts(
      alerts?.map((a) =>
        selectedAlerts?.includes(a?.id) ? { ...a, dismissed: true } : a,
      ),
    );
    setDismissedAlerts([
      ...dismissedAlerts,
      ...(dismissedItems?.map((item) => ({ ...item, dismissedAt: now })) || []),
    ]);
    setSelectedAlerts([]);
  };

  const handleMarkAllRead = () => {
    const activeAlerts = getFilteredAlerts();
    const now = new Date();
    const idsToMark = activeAlerts?.map((a) => a?.id);
    setAlerts(
      alerts?.map((a) =>
        idsToMark?.includes(a?.id) ? { ...a, dismissed: true } : a,
      ),
    );
    setDismissedAlerts([
      ...dismissedAlerts,
      ...(activeAlerts?.map((item) => ({ ...item, dismissedAt: now })) || []),
    ]);
    setSelectedAlerts([]);
  };

  const handleSelectAll = (checked) => {
    if (checked) {
      const activeAlerts = getFilteredAlerts();
      setSelectedAlerts(activeAlerts?.map((a) => a?.id));
    } else {
      setSelectedAlerts([]);
    }
  };

  const handleSelectAlert = (alertId, checked) => {
    if (checked) {
      setSelectedAlerts([...selectedAlerts, alertId]);
    } else {
      setSelectedAlerts(selectedAlerts?.filter((id) => id !== alertId));
    }
  };

  const handleExportLogs = () => {
    const exportData = alerts?.map((alert) => ({
      timestamp: alert?.timestamp?.toISOString(),
      type: alert?.type,
      service: alert?.service,
      severity: alert?.severity,
      message: alert?.message,
      details: alert?.details,
      dismissed: alert?.dismissed,
    }));

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `servarrhub-alerts-${new Date()?.toISOString()?.split("T")?.[0]}.json`;
    document.body?.appendChild(a);
    a?.click();
    document.body?.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleRestoreAlert = (alert) => {
    setAlerts([
      ...(alerts?.filter((a) => a?.id !== alert?.id) || []),
      { ...alert, dismissed: false },
    ]);
    setDismissedAlerts(dismissedAlerts?.filter((a) => a?.id !== alert?.id));
  };

  const getFilteredAlerts = () => {
    return alerts?.filter((alert) => {
      if (alert?.dismissed) return false;
      if (activeTab !== "all" && alert?.type !== activeTab) return false;
      if (filters?.service !== "all" && alert?.service !== filters?.service)
        return false;
      if (filters?.severity !== "all" && alert?.severity !== filters?.severity)
        return false;

      if (filters?.dateRange !== "all") {
        const now = Date.now();
        const alertTime = alert?.timestamp?.getTime();
        const ranges = {
          "1h": 3600000,
          "24h": 86400000,
          "7d": 604800000,
          "30d": 2592000000,
        };
        if (now - alertTime > ranges?.[filters?.dateRange]) return false;
      }

      return true;
    });
  };

  const filteredAlerts = getFilteredAlerts();
  const allSelected =
    filteredAlerts?.length > 0 &&
    selectedAlerts?.length === filteredAlerts?.length;

  useEffect(() => {
    const interval = setInterval(() => {
      const randomTypes = ["connection", "api", "request", "system"];
      const randomServices = ["Radarr", "Sonarr", "Jellyfin", "Jellyseerr"];
      const randomSeverities = ["error", "warning", "info"];

      if (Math.random() > 0.95) {
        const newAlert = {
          id: Date.now(),
          type: randomTypes?.[Math.floor(Math.random() * randomTypes?.length)],
          service:
            randomServices?.[
              Math.floor(Math.random() * randomServices?.length)
            ],
          severity:
            randomSeverities?.[
              Math.floor(Math.random() * randomSeverities?.length)
            ],
          message: "New alert detected",
          details:
            "This is a simulated real-time alert for demonstration purposes.",
          timestamp: new Date(),
          dismissed: false,
          suggestions: [
            "Check service status",
            "Review logs",
            "Contact support if issue persists",
          ],
        };

        setAlerts((prev) => [newAlert, ...prev]);

        if (soundEnabled) {
          const audio = new Audio(
            "data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBTGH0fPTgjMGHm7A7+OZURE",
          );
          audio?.play()?.catch(() => {});
        }
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [soundEnabled]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-amber-50">
      <Header />
      <div className="container mx-auto px-4 py-8">
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                System Alerts
              </h1>
              <p className="text-gray-600">
                Monitor and manage system notifications across all Servarr
                services
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                iconName="Bell"
                onClick={() => setSoundEnabled(!soundEnabled)}
                className={
                  soundEnabled ? "border-orange-500 text-orange-600" : ""
                }
              >
                {soundEnabled ? "Sound On" : "Sound Off"}
              </Button>
              <Button
                variant="outline"
                iconName="Download"
                onClick={handleExportLogs}
              >
                Export Logs
              </Button>
              <Button
                variant="outline"
                iconName="History"
                onClick={() => setShowHistory(!showHistory)}
              >
                {showHistory ? "Hide History" : "Show History"}
              </Button>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-6">
          <div className="flex overflow-x-auto">
            {tabs?.map((tab) => (
              <button
                key={tab?.id}
                onClick={() => setActiveTab(tab?.id)}
                className={`flex items-center gap-2 px-6 py-4 font-medium whitespace-nowrap transition-colors border-b-2 ${
                  activeTab === tab?.id
                    ? "border-orange-500 text-orange-600 bg-orange-50"
                    : "border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                }`}
              >
                {tab?.label}
                {tab?.count > 0 && (
                  <span
                    className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
                      activeTab === tab?.id
                        ? "bg-orange-500 text-white"
                        : "bg-gray-200 text-gray-700"
                    }`}
                  >
                    {tab?.count}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Filter Toolbar */}
        <FilterToolbar filters={filters} onFilterChange={setFilters} />

        {/* Bulk Actions */}
        {filteredAlerts?.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Checkbox
                  checked={allSelected}
                  onChange={(e) => handleSelectAll(e?.target?.checked)}
                  label="Select All"
                />
                {selectedAlerts?.length > 0 && (
                  <span className="text-sm text-gray-600">
                    {selectedAlerts?.length} alert
                    {selectedAlerts?.length !== 1 ? "s" : ""} selected
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3">
                {selectedAlerts?.length > 0 && (
                  <Button
                    variant="destructive"
                    size="sm"
                    iconName="X"
                    onClick={handleDismissSelected}
                  >
                    Dismiss Selected
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  iconName="CheckCheck"
                  onClick={handleMarkAllRead}
                >
                  Mark All as Read
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Alert List */}
        {!showHistory ? (
          <div className="space-y-4">
            {filteredAlerts?.length === 0 ? (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
                <Icon
                  name="CheckCircle"
                  size={48}
                  className="mx-auto mb-4 text-green-500"
                />
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  No Active Alerts
                </h3>
                <p className="text-gray-600">
                  All systems are operating normally
                </p>
              </div>
            ) : (
              filteredAlerts?.map((alert) => (
                <AlertCard
                  key={alert?.id}
                  alert={alert}
                  selected={selectedAlerts?.includes(alert?.id)}
                  onSelect={(checked) => handleSelectAlert(alert?.id, checked)}
                  onDismiss={() => handleDismiss(alert?.id)}
                />
              ))
            )}
          </div>
        ) : (
          <AlertHistory
            alerts={dismissedAlerts}
            onRestore={handleRestoreAlert}
          />
        )}
      </div>
    </div>
  );
};

export default Alerts;
