import React from "react";
import Icon from "../../../components/AppIcon";

const BAR_COLORS = {
  movies: "var(--color-primary)",
  tv: "var(--color-secondary)",
};

const GenreColumn = ({ title, icon, iconColor, items, barColor }) => {
  const max = items?.[0]?.count || 1;

  return (
    <div className="flex-1 min-w-0">
      <div className="flex items-center gap-2 mb-4">
        <Icon name={icon} size={16} color={iconColor} />
        <span className="text-sm font-semibold text-foreground">{title}</span>
        <span className="ml-auto text-xs text-muted-foreground">{items?.length ?? 0} genres</span>
      </div>

      {items?.length > 0 ? (
        <div className="space-y-2.5">
          {items.map((item, index) => (
            <div key={item.genre} className="group">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-xs text-muted-foreground w-4 shrink-0 text-right">
                    {index + 1}
                  </span>
                  <span className="text-sm text-foreground truncate">{item.genre}</span>
                </div>
                <span className="text-xs font-semibold text-foreground ml-2 shrink-0">
                  {item.count}
                </span>
              </div>
              <div className="h-1.5 bg-muted rounded-full overflow-hidden ml-6">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.round((item.count / max) * 100)}%`,
                    backgroundColor: barColor,
                    opacity: 1 - index * 0.07,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex items-center justify-center h-32 text-muted-foreground">
          <p className="text-sm">No genre data yet — sync required</p>
        </div>
      )}
    </div>
  );
};

const GenreStatsCard = ({ genreData, isLoading }) => {
  return (
    <div className="bg-card border border-border rounded-lg p-4 md:p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
          <Icon name="Tags" size={20} color="var(--color-accent)" />
        </div>
        <div>
          <h3 className="text-base md:text-lg font-semibold text-foreground">Genre Statistics</h3>
          <p className="text-xs md:text-sm text-muted-foreground">Top 10 genres by media count</p>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-48 text-muted-foreground">
          <p className="text-sm">Loading genre data...</p>
        </div>
      ) : (
        <div className="flex flex-col md:flex-row gap-6 md:gap-8">
          <GenreColumn
            title="Movies"
            icon="Film"
            iconColor="var(--color-primary)"
            items={genreData?.movies ?? []}
            barColor={BAR_COLORS.movies}
          />
          <div className="hidden md:block w-px bg-border shrink-0" />
          <GenreColumn
            title="TV Shows"
            icon="Tv"
            iconColor="var(--color-secondary)"
            items={genreData?.tv ?? []}
            barColor={BAR_COLORS.tv}
          />
        </div>
      )}
    </div>
  );
};

export default GenreStatsCard;
