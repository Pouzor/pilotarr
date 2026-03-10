import React, { useState } from "react";
import Icon from "../../../components/AppIcon";
import StatusIndicator from "./StatusIndicator";
import ExpandableRow from "./ExpandableRow";
import { Checkbox } from "../../../components/ui/Checkbox";
import Button from "../../../components/ui/Button";

const MonitoringTable = ({ data, selectedItems, onSelectAll, onSelectItem, onRefresh }) => {
  const [expandedRows, setExpandedRows] = useState([]);
  const [refreshingIds, setRefreshingIds] = useState([]);
  const [sortConfig, setSortConfig] = useState({
    key: "title",
    direction: "asc",
  });

  const handleRefresh = async (id) => {
    if (refreshingIds.includes(id)) return;
    setRefreshingIds((prev) => [...prev, id]);
    try {
      await onRefresh(id);
    } finally {
      setRefreshingIds((prev) => prev.filter((r) => r !== id));
    }
  };

  const toggleRow = (id) => {
    setExpandedRows((prev) =>
      prev?.includes(id) ? prev?.filter((rowId) => rowId !== id) : [...prev, id],
    );
  };

  const handleSort = (key) => {
    setSortConfig((prev) => ({
      key,
      direction: prev?.key === key && prev?.direction === "asc" ? "desc" : "asc",
    }));
  };

  const sortedData = React.useMemo(() => {
    const sorted = [...data];
    sorted?.sort((a, b) => {
      const aValue = a?.[sortConfig?.key];
      const bValue = b?.[sortConfig?.key];

      if (aValue < bValue) return sortConfig?.direction === "asc" ? -1 : 1;
      if (aValue > bValue) return sortConfig?.direction === "asc" ? 1 : -1;
      return 0;
    });
    return sorted;
  }, [data, sortConfig]);

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date?.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const allSelected = data?.length > 0 && selectedItems?.length === data?.length;
  const someSelected = selectedItems?.length > 0 && selectedItems?.length < data?.length;

  if (data?.length === 0) {
    return (
      <div className="bg-card border border-border rounded-lg p-12 text-center">
        <Icon name="Inbox" size={48} className="mx-auto mb-4 text-muted-foreground" />
        <h3 className="text-lg font-semibold text-foreground mb-2">No monitored media found</h3>
        <p className="text-sm text-muted-foreground">
          Try adjusting your filters or add new media to monitor
        </p>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden">
      {/* Desktop Table View */}
      <div className="hidden lg:block overflow-x-auto">
        <table className="w-full">
          <thead className="bg-muted/30 border-b border-border">
            <tr>
              <th className="px-4 py-3 text-left w-12">
                <Checkbox
                  checked={allSelected}
                  indeterminate={someSelected}
                  onChange={(e) => onSelectAll(e?.target?.checked)}
                />
              </th>
              <th className="px-4 py-3 text-left w-12"></th>
              <th
                className="px-4 py-3 text-left cursor-pointer hover:bg-muted/50 transition-colors"
                onClick={() => handleSort("title")}
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-foreground">Title</span>
                  {sortConfig?.key === "title" && (
                    <Icon
                      name={sortConfig?.direction === "asc" ? "ChevronUp" : "ChevronDown"}
                      size={14}
                      className="text-primary"
                    />
                  )}
                </div>
              </th>
              <th className="px-4 py-3 text-left">
                <span className="text-sm font-semibold text-foreground">Service</span>
              </th>
              <th className="px-4 py-3 text-left">
                <span className="text-sm font-semibold text-foreground">Monitoring</span>
              </th>
              <th className="px-4 py-3 text-left">
                <span className="text-sm font-semibold text-foreground">Availability</span>
              </th>
              <th className="px-4 py-3 text-left">
                <span className="text-sm font-semibold text-foreground">Quality</span>
              </th>
              <th
                className="px-4 py-3 text-left cursor-pointer hover:bg-muted/50 transition-colors"
                onClick={() => handleSort("lastUpdated")}
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-foreground">Last Updated</span>
                  {sortConfig?.key === "lastUpdated" && (
                    <Icon
                      name={sortConfig?.direction === "asc" ? "ChevronUp" : "ChevronDown"}
                      size={14}
                      className="text-primary"
                    />
                  )}
                </div>
              </th>
              <th className="px-4 py-3 text-right">
                <span className="text-sm font-semibold text-foreground">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedData?.map((item) => (
              <React.Fragment key={item?.id}>
                <tr className="border-b border-border hover:bg-muted/20 transition-colors">
                  <td className="px-4 py-3">
                    <Checkbox
                      checked={selectedItems?.includes(item?.id)}
                      onChange={(e) => onSelectItem(item?.id, e?.target?.checked)}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => toggleRow(item?.id)}
                      className="text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <Icon
                        name={expandedRows?.includes(item?.id) ? "ChevronDown" : "ChevronRight"}
                        size={18}
                      />
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Icon
                        name={item?.service === "sonarr" ? "Tv" : "Film"}
                        size={16}
                        className={item?.service === "sonarr" ? "text-purple-400" : "text-blue-400"}
                      />
                      <span className="text-sm font-medium text-foreground">{item?.title}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-primary/10 text-primary capitalize">
                      {item?.service}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <StatusIndicator status={item?.monitoringStatus} type="monitoring" />
                  </td>
                  <td className="px-4 py-3">
                    <StatusIndicator status={item?.availabilityStatus} type="availability" />
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm text-foreground">{item?.qualityProfile}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm text-muted-foreground">
                      {formatDate(item?.lastUpdated)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        iconName="RefreshCw"
                        className={`h-8 w-8 ${refreshingIds.includes(item?.id) ? "animate-spin opacity-50" : ""}`}
                        disabled={refreshingIds.includes(item?.id)}
                        onClick={() => handleRefresh(item?.id)}
                        title="Refresh & rescan"
                      />
                    </div>
                  </td>
                </tr>
                {expandedRows?.includes(item?.id) && (
                  <tr>
                    <td colSpan="9" className="px-4 py-0">
                      <ExpandableRow item={item} />
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
      {/* Mobile Card View */}
      <div className="lg:hidden divide-y divide-border">
        {sortedData?.map((item) => (
          <div key={item?.id} className="p-4">
            <div className="flex items-start gap-3 mb-3">
              <Checkbox
                checked={selectedItems?.includes(item?.id)}
                onChange={(e) => onSelectItem(item?.id, e?.target?.checked)}
                className="mt-1"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <Icon
                    name={item?.service === "sonarr" ? "Tv" : "Film"}
                    size={16}
                    className={item?.service === "sonarr" ? "text-purple-400" : "text-blue-400"}
                  />
                  <h3 className="text-sm font-semibold text-foreground">{item?.title}</h3>
                </div>
                <div className="grid grid-cols-2 gap-2 mb-3">
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Service</p>
                    <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-primary/10 text-primary capitalize">
                      {item?.service}
                    </span>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Quality</p>
                    <span className="text-xs text-foreground">{item?.qualityProfile}</span>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Monitoring</p>
                    <StatusIndicator status={item?.monitoringStatus} type="monitoring" />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Availability</p>
                    <StatusIndicator status={item?.availabilityStatus} type="availability" />
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mb-3">
                  Updated: {formatDate(item?.lastUpdated)}
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    iconName={expandedRows?.includes(item?.id) ? "ChevronUp" : "ChevronDown"}
                    onClick={() => toggleRow(item?.id)}
                    className="flex-1"
                  >
                    {expandedRows?.includes(item?.id) ? "Hide" : "Show"} Details
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    iconName="RefreshCw"
                    disabled={refreshingIds.includes(item?.id)}
                    className={refreshingIds.includes(item?.id) ? "animate-spin opacity-50" : ""}
                    onClick={() => handleRefresh(item?.id)}
                    title="Refresh & rescan"
                  />
                </div>
              </div>
            </div>
            {expandedRows?.includes(item?.id) && (
              <div className="mt-3 pt-3 border-t border-border">
                <ExpandableRow item={item} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default MonitoringTable;
