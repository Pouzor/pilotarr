import React, { useState, useMemo } from "react";
import Icon from "../../../components/AppIcon";
import Image from "../../../components/AppImage";

const MediaAnalyticsTable = ({ data, isLoading }) => {
  const [sortConfig, setSortConfig] = useState({
    key: "lastPlayedAt",
    direction: "desc",
  });

  const sortedData = useMemo(() => {
    const sorted = [...data]?.sort((a, b) => {
      if (sortConfig?.direction === "asc") {
        return a?.[sortConfig?.key] > b?.[sortConfig?.key] ? 1 : -1;
      }
      return a?.[sortConfig?.key] < b?.[sortConfig?.key] ? 1 : -1;
    });
    return sorted;
  }, [data, sortConfig]);

  const handleSort = (key) => {
    setSortConfig({
      key,
      direction:
        sortConfig?.key === key && sortConfig?.direction === "desc"
          ? "asc"
          : "desc",
    });
  };

  const SortIcon = ({ columnKey }) => {
    if (sortConfig?.key !== columnKey) {
      return <Icon name="ChevronsUpDown" size={14} className="opacity-30" />;
    }
    return (
      <Icon
        name={sortConfig?.direction === "asc" ? "ChevronUp" : "ChevronDown"}
        size={14}
        color="var(--color-primary)"
      />
    );
  };

  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden">
      <div className="p-4 md:p-6 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center">
            <Icon name="PlayCircle" size={20} color="var(--color-success)" />
          </div>
          <div>
            <h3 className="text-base md:text-lg font-semibold text-foreground">
              Media Playback Analytics
            </h3>
            <p className="text-xs md:text-sm text-muted-foreground">
              Detailed content performance metrics
            </p>
          </div>
        </div>
      </div>
      <div className="overflow-x-auto">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
              <p className="text-sm text-muted-foreground">
                Loading media analytics...
              </p>
            </div>
          </div>
        ) : data?.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <p className="text-sm text-muted-foreground">
              No media analytics data available
            </p>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-muted/30">
              <tr>
                <th className="px-4 py-3 text-left">
                  <button
                    onClick={() => handleSort("title")}
                    className="flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Media Title
                    <SortIcon columnKey="title" />
                  </button>
                </th>
                <th className="px-4 py-3 text-left hidden md:table-cell">
                  <button
                    onClick={() => handleSort("type")}
                    className="flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Type
                    <SortIcon columnKey="type" />
                  </button>
                </th>
                <th className="px-4 py-3 text-left">
                  <button
                    onClick={() => handleSort("plays")}
                    className="flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Plays
                    <SortIcon columnKey="plays" />
                  </button>
                </th>
                <th className="px-4 py-3 text-left hidden lg:table-cell">
                  <button
                    onClick={() => handleSort("duration")}
                    className="flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Duration
                    <SortIcon columnKey="duration" />
                  </button>
                </th>
                <th className="px-4 py-3 text-left hidden lg:table-cell">
                  <button
                    onClick={() => handleSort("quality")}
                    className="flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Quality
                    <SortIcon columnKey="quality" />
                  </button>
                </th>
                <th className="px-4 py-3 text-left">
                  <span className="text-xs font-semibold text-muted-foreground">
                    Status
                  </span>
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedData?.map((item, index) => (
                <tr
                  key={index}
                  className="border-t border-border hover:bg-muted/20 transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 md:w-16 md:h-16 rounded-lg overflow-hidden flex-shrink-0">
                        <Image
                          src={item?.thumbnail}
                          alt={item?.thumbnailAlt}
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-foreground truncate">
                          {item?.title}
                        </p>
                        {item?.type === "TV Show" && item?.episodeInfo && (
                          <p className="text-xs text-primary font-medium truncate">
                            {item?.episodeInfo}
                          </p>
                        )}
                        <p className="text-xs text-muted-foreground truncate md:hidden">
                          {item?.type}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell">
                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-muted text-xs font-medium text-foreground">
                      <Icon
                        name={item?.type === "Movie" ? "Film" : "Tv"}
                        size={12}
                      />
                      {item?.type}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm font-semibold text-foreground">
                      {item?.plays}
                    </span>
                  </td>
                  <td className="px-4 py-3 hidden lg:table-cell">
                    <span className="text-sm text-muted-foreground">
                      {item?.duration}
                    </span>
                  </td>
                  <td className="px-4 py-3 hidden lg:table-cell">
                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-primary/10 text-xs font-medium text-primary">
                      <Icon name="Sparkles" size={12} />
                      {item?.quality}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div
                        className={`w-2 h-2 rounded-full ${item?.transcoded ? "bg-warning" : "bg-success"}`}
                      ></div>
                      <span className="text-xs text-muted-foreground hidden sm:inline">
                        {item?.transcoded ? "Transcoded" : "Direct"}
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default MediaAnalyticsTable;
