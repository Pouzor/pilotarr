import React from "react";
import { useNavigate } from "react-router-dom";
import Icon from "../../../components/AppIcon";

const DEVICE_ICON = {
  desktop: "Monitor",
  mobile: "Smartphone",
  tablet: "Tablet",
  tv: "Tv",
  console: "Gamepad2",
  unknown: "HelpCircle",
};

const RANK_STYLES = [
  { bg: "bg-yellow-500/20", text: "text-yellow-400", icon: "Crown" },
  { bg: "bg-slate-400/20", text: "text-slate-300", icon: "Medal" },
  { bg: "bg-amber-700/20", text: "text-amber-600", icon: "Award" },
];

const UserLeaderboard = ({ users, isLoading }) => {
  const navigate = useNavigate();
  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-lg p-4 md:p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 md:w-12 md:h-12 rounded-lg bg-primary/10 flex items-center justify-center">
            <Icon name="Trophy" size={20} color="var(--color-primary)" />
          </div>
          <div>
            <h3 className="text-base md:text-lg font-semibold text-foreground">Top Viewers</h3>
            <p className="text-xs md:text-sm text-muted-foreground">Ranked by hours watched</p>
          </div>
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-14 bg-muted/40 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!users?.length) {
    return (
      <div className="bg-card border border-border rounded-lg p-4 md:p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 md:w-12 md:h-12 rounded-lg bg-primary/10 flex items-center justify-center">
            <Icon name="Trophy" size={20} color="var(--color-primary)" />
          </div>
          <div>
            <h3 className="text-base md:text-lg font-semibold text-foreground">Top Viewers</h3>
            <p className="text-xs md:text-sm text-muted-foreground">Ranked by hours watched</p>
          </div>
        </div>
        <div className="flex flex-col items-center justify-center py-8 text-muted-foreground gap-2">
          <Icon name="Users" size={32} />
          <p className="text-sm">No playback history yet</p>
        </div>
      </div>
    );
  }

  const maxHours = users[0]?.hours_watched || 1;

  return (
    <div className="bg-card border border-border rounded-lg p-4 md:p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 md:w-12 md:h-12 rounded-lg bg-primary/10 flex items-center justify-center">
            <Icon name="Trophy" size={20} color="var(--color-primary)" />
          </div>
          <div>
            <h3 className="text-base md:text-lg font-semibold text-foreground">Top Viewers</h3>
            <p className="text-xs md:text-sm text-muted-foreground">Ranked by hours watched</p>
          </div>
        </div>
        <button
          onClick={() => navigate("/user-stats")}
          className="text-xs text-muted-foreground bg-muted hover:bg-muted/70 hover:text-foreground px-2 py-1 rounded-md transition-colors cursor-pointer"
        >
          {users.length} user{users.length !== 1 ? "s" : ""}
        </button>
      </div>

      <div className="space-y-3">
        {users.map((user, index) => {
          const rank = RANK_STYLES[index] || null;
          const barWidth = maxHours > 0 ? (user.hours_watched / maxHours) * 100 : 0;
          const deviceIcon = DEVICE_ICON[user.favorite_device?.toLowerCase()] || "Monitor";
          const initial = user.user_name?.[0]?.toUpperCase() || "?";

          return (
            <div
              key={user.user_name}
              className="bg-muted/30 hover:bg-muted/50 rounded-lg p-3 space-y-2 cursor-pointer transition-colors"
              onClick={() => navigate(`/user-stats?user=${encodeURIComponent(user.user_name)}`)}
            >
              <div className="flex items-center gap-3">
                {/* Rank badge */}
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${rank ? rank.bg : "bg-muted"}`}
                >
                  {rank ? (
                    <Icon name={rank.icon} size={12} className={rank.text} />
                  ) : (
                    <span className="text-xs font-bold text-muted-foreground">{index + 1}</span>
                  )}
                </div>

                {/* Avatar initial */}
                <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
                  <span className="text-sm font-bold text-primary">{initial}</span>
                </div>

                {/* Name + device */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-medium text-foreground truncate">
                      {user.user_name}
                    </span>
                    {user.favorite_device && (
                      <Icon
                        name={deviceIcon}
                        size={12}
                        className="text-muted-foreground shrink-0"
                      />
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span>{user.total_plays} plays</span>
                    <span>·</span>
                    {user.movies_count > 0 && <span>{user.movies_count} movies</span>}
                    {user.movies_count > 0 && user.episodes_count > 0 && <span>·</span>}
                    {user.episodes_count > 0 && <span>{user.episodes_count} eps</span>}
                  </div>
                </div>

                {/* Hours */}
                <div className="text-right shrink-0">
                  <span className="text-sm font-bold text-foreground">{user.hours_watched}h</span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="w-full bg-muted rounded-full h-1.5">
                <div
                  className={`h-1.5 rounded-full transition-all duration-500 ${index === 0 ? "bg-yellow-400" : index === 1 ? "bg-slate-300" : index === 2 ? "bg-amber-600" : "bg-primary"}`}
                  style={{ width: `${barWidth}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default UserLeaderboard;
