import React, { useState, useMemo, useEffect, useCallback, useRef } from "react";
import Header from "../../components/navigation/Header";
import Icon from "../../components/AppIcon";
import Button from "../../components/ui/Button";
import TorrentsTable from "./components/TorrentsTable";
import { getTorrents } from "../../services/torrentService";

// ─── Formatters (shared helpers) ─────────────────────────────────────────────

function formatBytes(bytes, decimals = 1) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals))} ${sizes[i]}`;
}

function formatSpeed(bytesPerSec) {
  if (bytesPerSec === 0) return "0 KB/s";
  return `${formatBytes(bytesPerSec)}/s`;
}

// ─── Filter tabs config ───────────────────────────────────────────────────────

const FILTER_TABS = [
  { key: "all", label: "All", icon: "List" },
  { key: "downloading", label: "Downloading", icon: "Download" },
  { key: "seeding", label: "Seeding", icon: "Upload" },
  { key: "paused", label: "Paused", icon: "Pause" },
  { key: "error", label: "Error", icon: "AlertCircle" },
];

// ─── Global Stats ─────────────────────────────────────────────────────────────

function GlobalStats({ torrents, transfer }) {
  const totalDl = transfer?.dl_speed ?? torrents.reduce((acc, t) => acc + t.dlSpeed, 0);
  const totalUl = transfer?.ul_speed ?? torrents.reduce((acc, t) => acc + t.ulSpeed, 0);
  const totalSize = torrents.reduce((acc, t) => acc + t.downloaded, 0);
  const totalUploaded = torrents.reduce((acc, t) => acc + t.uploaded, 0);
  const globalRatio = totalSize > 0 ? totalUploaded / totalSize : 0;
  const activeCount = torrents.filter((t) => ["downloading", "seeding"].includes(t.status)).length;

  const stats = [
    {
      label: "Download",
      value: formatSpeed(totalDl),
      icon: "Download",
      color: "text-primary",
      bgColor: "bg-primary/10",
    },
    {
      label: "Upload",
      value: formatSpeed(totalUl),
      icon: "Upload",
      color: "text-success",
      bgColor: "bg-success/10",
    },
    {
      label: "Active",
      value: `${activeCount} torrent${activeCount !== 1 ? "s" : ""}`,
      icon: "Activity",
      color: "text-secondary",
      bgColor: "bg-secondary/10",
    },
    {
      label: "Global Ratio",
      value: globalRatio.toFixed(2),
      icon: "ArrowLeftRight",
      color: globalRatio >= 1 ? "text-success" : globalRatio >= 0.5 ? "text-warning" : "text-error",
      bgColor: "bg-accent/10",
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="bg-card border border-border rounded-lg px-4 py-3 flex items-center gap-3"
        >
          <div
            className={`w-9 h-9 rounded-lg ${stat.bgColor} flex items-center justify-center flex-shrink-0`}
          >
            <Icon name={stat.icon} size={16} className={stat.color} />
          </div>
          <div className="min-w-0">
            <p className={`text-base font-bold tabular-nums ${stat.color}`}>{stat.value}</p>
            <p className="text-xs text-muted-foreground">{stat.label}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

const POLL_INTERVAL_MS = 60_000;

const Torrents = () => {
  const [activeTab, setActiveTab] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedItems, setSelectedItems] = useState([]);
  const [torrents, setTorrents] = useState([]);
  const [transfer, setTransfer] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);

  const fetchTorrents = useCallback(async () => {
    try {
      const data = await getTorrents();
      setTorrents(data.torrents ?? []);
      setTransfer(data.transfer ?? null);
      setError(null);
    } catch (err) {
      setError(err?.response?.data?.detail ?? err?.message ?? "Failed to load torrents");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTorrents();
    intervalRef.current = setInterval(fetchTorrents, POLL_INTERVAL_MS);
    return () => clearInterval(intervalRef.current);
  }, [fetchTorrents]);

  // Count per tab
  const tabCounts = useMemo(() => {
    const counts = { all: torrents.length };
    FILTER_TABS.slice(1).forEach((tab) => {
      counts[tab.key] = torrents.filter((t) => t.status === tab.key).length;
    });
    return counts;
  }, [torrents]);

  // Filtered list
  const filteredTorrents = useMemo(() => {
    let result = torrents;

    if (activeTab !== "all") {
      result = result.filter((t) => t.status === activeTab);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (t) =>
          t.name.toLowerCase().includes(q) ||
          t.tracker?.toLowerCase().includes(q) ||
          t.category?.toLowerCase().includes(q),
      );
    }

    return result;
  }, [torrents, activeTab, searchQuery]);

  // Selection handlers
  const handleSelectAll = (checked) => {
    setSelectedItems(checked ? filteredTorrents.map((t) => t.id) : []);
  };

  const handleSelectItem = (id, checked) => {
    setSelectedItems((prev) => (checked ? [...prev, id] : prev.filter((i) => i !== id)));
  };

  // Actions (mock — will call API later)
  const handlePauseResume = (torrent) => {
    setTorrents((prev) =>
      prev.map((t) => {
        if (t.id !== torrent.id) return t;
        if (t.status === "paused") {
          return { ...t, status: "downloading" };
        }
        if (["downloading", "seeding"].includes(t.status)) {
          return { ...t, status: "paused", dlSpeed: 0, ulSpeed: 0 };
        }
        return t;
      }),
    );
  };

  const handleRecheck = (torrent) => {
    setTorrents((prev) =>
      prev.map((t) => (t.id === torrent.id ? { ...t, status: "checking", progress: 0 } : t)),
    );
    // Simulate recheck completing after 2s
    setTimeout(() => {
      setTorrents((prev) =>
        prev.map((t) => (t.id === torrent.id ? { ...t, status: "paused", progress: 1.0 } : t)),
      );
    }, 2000);
  };

  const handleBulkPause = () => {
    setTorrents((prev) =>
      prev.map((t) =>
        selectedItems.includes(t.id) && ["downloading", "seeding"].includes(t.status)
          ? { ...t, status: "paused", dlSpeed: 0, ulSpeed: 0 }
          : t,
      ),
    );
  };

  const handleBulkResume = () => {
    setTorrents((prev) =>
      prev.map((t) =>
        selectedItems.includes(t.id) && t.status === "paused"
          ? { ...t, status: t.progress === 1 ? "seeding" : "downloading" }
          : t,
      ),
    );
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <div className="container mx-auto px-4 pt-20 md:pt-24 pb-8">
        {/* Page Header */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <Icon name="Download" size={20} color="var(--color-primary)" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-foreground">Torrents</h1>
              <p className="text-sm text-muted-foreground">
                Manage and monitor all active torrent transfers
              </p>
            </div>
          </div>

          {/* Client badge */}
          <div className="flex items-center gap-2 px-3 py-1.5 bg-card border border-border rounded-lg self-start lg:self-auto">
            <span
              className={`w-2 h-2 rounded-full animate-pulse ${
                error ? "bg-error" : transfer ? "bg-success" : "bg-muted-foreground"
              }`}
            />
            <span className="text-sm text-muted-foreground">qBittorrent</span>
            <Icon name="ChevronDown" size={14} className="text-muted-foreground/50" />
          </div>
        </div>

        {/* Error banner */}
        {error && (
          <div className="bg-error/10 border border-error/30 rounded-lg px-4 py-3 mb-4 flex items-center gap-2">
            <Icon name="AlertCircle" size={16} className="text-error flex-shrink-0" />
            <span className="text-sm text-foreground">{error}</span>
          </div>
        )}

        {/* Global Stats */}
        <GlobalStats torrents={torrents} transfer={transfer} />

        {/* Filter tabs + Search */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          {/* Tabs */}
          <div className="flex items-center gap-1 bg-card border border-border rounded-lg p-1 overflow-x-auto">
            {FILTER_TABS.map((tab) => {
              const count = tabCounts[tab.key] ?? 0;
              const isActive = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  onClick={() => {
                    setActiveTab(tab.key);
                    setSelectedItems([]);
                  }}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium whitespace-nowrap transition-colors
                    ${
                      isActive
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                    }`}
                >
                  <Icon name={tab.icon} size={13} />
                  {tab.label}
                  {count > 0 && (
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded-full tabular-nums
                      ${isActive ? "bg-white/20" : "bg-muted text-muted-foreground"}`}
                    >
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Search */}
          <div className="relative">
            <Icon
              name="Search"
              size={15}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
            />
            <input
              type="text"
              placeholder="Search torrents…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-3 py-1.5 bg-card border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring w-56"
            />
          </div>
        </div>

        {/* Bulk action bar */}
        {selectedItems.length > 0 && (
          <div className="bg-primary/10 border border-primary/30 rounded-lg px-4 py-3 mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Icon name="CheckSquare" size={16} className="text-primary" />
              <span className="text-sm font-medium text-foreground">
                {selectedItems.length} torrent{selectedItems.length !== 1 ? "s" : ""} selected
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="xs" iconName="Pause" onClick={handleBulkPause}>
                Pause
              </Button>
              <Button variant="outline" size="xs" iconName="Play" onClick={handleBulkResume}>
                Resume
              </Button>
              <button
                onClick={() => setSelectedItems([])}
                className="text-xs text-muted-foreground hover:text-foreground ml-2"
              >
                Clear
              </button>
            </div>
          </div>
        )}

        {/* Loading spinner (first load only) */}
        {isLoading && (
          <div className="flex items-center justify-center py-16">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {/* Table */}
        {!isLoading && (
          <TorrentsTable
            data={filteredTorrents}
            selectedItems={selectedItems}
            onSelectAll={handleSelectAll}
            onSelectItem={handleSelectItem}
            onPauseResume={handlePauseResume}
            onRecheck={handleRecheck}
          />
        )}
      </div>
    </div>
  );
};

export default Torrents;
