import React from "react";
import Icon from "../../../components/AppIcon";

const CalendarGrid = ({
  selectedDate,
  setSelectedDate,
  events,
  eventFilters,
  viewMode,
  isLoading,
}) => {
  const getDaysInMonth = (date) => {
    const year = date?.getFullYear();
    const month = date?.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay?.getDate();
    const startingDayOfWeek = firstDay?.getDay();

    return { daysInMonth, startingDayOfWeek, year, month };
  };

  const isToday = (date) => {
    const today = new Date();
    return (
      date?.getDate() === today?.getDate() &&
      date?.getMonth() === today?.getMonth() &&
      date?.getFullYear() === today?.getFullYear()
    );
  };

  const isSelectedDate = (date) => {
    return (
      date?.getDate() === selectedDate?.getDate() &&
      date?.getMonth() === selectedDate?.getMonth() &&
      date?.getFullYear() === selectedDate?.getFullYear()
    );
  };

  const getEventsForDate = (date) => {
    return events?.filter((event) => {
      const eventDate = new Date(event?.releaseDate);
      const matchesDate =
        eventDate?.getDate() === date?.getDate() &&
        eventDate?.getMonth() === date?.getMonth() &&
        eventDate?.getFullYear() === date?.getFullYear();

      if (!matchesDate) return false;

      // Apply event type filters
      if (
        event?.eventType === "release" &&
        event?.type === "tv" &&
        !eventFilters?.tvReleases
      )
        return false;
      if (
        event?.eventType === "release" &&
        event?.type === "movie" &&
        !eventFilters?.movieReleases
      )
        return false;
      if (event?.eventType === "view" && !eventFilters?.views) return false;

      return true;
    });
  };

  const getEventTypeColor = (eventType, mediaType) => {
    if (eventType === "release" && mediaType === "tv") return "bg-blue-500";
    if (eventType === "release" && mediaType === "movie") return "bg-green-500";
    if (eventType === "download") return "bg-orange-500";
    if (eventType === "view") return "bg-purple-500";
    return "bg-gray-500";
  };

  const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const { daysInMonth, startingDayOfWeek, year, month } =
    getDaysInMonth(selectedDate);

  const renderMonthView = () => {
    const days = [];

    // Empty cells for days before month starts
    for (let i = 0; i < startingDayOfWeek; i++) {
      days?.push(
        <div
          key={`empty-${i}`}
          className="aspect-square p-2 bg-muted/30 border border-border/50"
        ></div>,
      );
    }

    // Days of the month
    for (let day = 1; day <= daysInMonth; day++) {
      const date = new Date(year, month, day);
      const dayEvents = getEventsForDate(date);
      const hasEvents = dayEvents?.length > 0;
      const isTodayDate = isToday(date);
      const isSelected = isSelectedDate(date);

      days?.push(
        <div
          key={day}
          onClick={() => setSelectedDate(date)}
          className={`aspect-square p-2 border border-border cursor-pointer transition-all hover:bg-accent/50 ${
            isTodayDate ? "bg-primary/10 border-primary" : "bg-card"
          } ${isSelected ? "ring-2 ring-primary shadow-lg" : ""}`}
        >
          <div className="h-full flex flex-col">
            <div
              className={`text-sm font-semibold mb-1 ${
                isTodayDate ? "text-primary" : "text-foreground"
              }`}
            >
              {day}
            </div>
            {hasEvents && (
              <div className="flex-1 space-y-1 overflow-hidden">
                {dayEvents?.slice(0, 3)?.map((event, idx) => (
                  <div
                    key={idx}
                    className={`h-1.5 rounded-full ${getEventTypeColor(event?.eventType, event?.type)}`}
                    title={event?.title}
                  ></div>
                ))}
                {dayEvents?.length > 3 && (
                  <div className="text-xs text-muted-foreground font-medium">
                    +{dayEvents?.length - 3} more
                  </div>
                )}
              </div>
            )}
          </div>
        </div>,
      );
    }

    return days;
  };

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-lg p-8">
        <div className="flex items-center justify-center">
          <Icon
            name="Loader2"
            size={32}
            className="animate-spin text-muted-foreground"
          />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden">
      {/* Day Names Header */}
      <div className="grid grid-cols-7 bg-muted/50 border-b border-border">
        {dayNames?.map((day) => (
          <div
            key={day}
            className="p-3 text-center text-sm font-semibold text-foreground"
          >
            {day}
          </div>
        ))}
      </div>

      {/* Calendar Grid */}
      <div className="grid grid-cols-7">{renderMonthView()}</div>

      {/* Legend */}
      <div className="p-4 border-t border-border bg-muted/30">
        <div className="flex flex-wrap gap-4 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-blue-500"></div>
            <span className="text-muted-foreground">TV Episode Release</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <span className="text-muted-foreground">Movie Release</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-purple-500"></div>
            <span className="text-muted-foreground">Viewing Activity</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CalendarGrid;
