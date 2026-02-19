import React from "react";
import Icon from "../../../components/AppIcon";
import Button from "../../../components/ui/Button";
import { Checkbox } from "../../../components/ui/Checkbox";

const ViewToolbar = ({
  viewMode,
  setViewMode,
  eventFilters,
  setEventFilters,
  selectedDate,
  monthNames,
  navigateMonth,
  goToToday,
}) => {
  const handleFilterChange = (filterKey) => {
    setEventFilters((prev) => ({
      ...prev,
      [filterKey]: !prev?.[filterKey],
    }));
  };

  return (
    <div className="bg-card border border-border rounded-lg p-4 mb-6">
      {/* Top Row: View Mode and Date Navigation */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-4">
        {/* View Mode Switcher */}
        <div className="flex items-center gap-2">
          <Button
            variant={viewMode === "month" ? "default" : "outline"}
            size="sm"
            onClick={() => setViewMode("month")}
          >
            <Icon name="Calendar" size={16} className="mr-2" />
            Month
          </Button>
        </div>

        {/* Date Navigation */}
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigateMonth(-1)}
            iconName="ChevronLeft"
            iconSize={20}
          />
          <div className="min-w-[200px] text-center">
            <h3 className="text-lg font-semibold text-foreground">
              {monthNames?.[selectedDate?.getMonth()]}{" "}
              {selectedDate?.getFullYear()}
            </h3>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigateMonth(1)}
            iconName="ChevronRight"
            iconSize={20}
          />
          <Button variant="outline" size="sm" onClick={goToToday}>
            Today
          </Button>
        </div>
      </div>

      {/* Bottom Row: Event Filters */}
      <div className="border-t border-border pt-4">
        <div className="flex items-center gap-2 mb-3">
          <Icon name="Filter" size={16} className="text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">
            Filter Events:
          </span>
        </div>
        <div className="flex flex-wrap gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <Checkbox
              checked={eventFilters?.tvReleases}
              onChange={() => handleFilterChange("tvReleases")}
            />
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-blue-500"></div>
              <span className="text-sm text-foreground">
                TV Episode Releases
              </span>
            </div>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <Checkbox
              checked={eventFilters?.movieReleases}
              onChange={() => handleFilterChange("movieReleases")}
            />
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
              <span className="text-sm text-foreground">Movie Releases</span>
            </div>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <Checkbox
              checked={eventFilters?.views}
              onChange={() => handleFilterChange("views")}
            />
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-purple-500"></div>
              <span className="text-sm text-foreground">Viewing Activity</span>
            </div>
          </label>
        </div>
      </div>
    </div>
  );
};

export default ViewToolbar;
