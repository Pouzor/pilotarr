import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import Header from "../../components/navigation/Header";
import Icon from "../../components/AppIcon";
import Button from "../../components/ui/Button";
import { getUserLeaderboard, getUserDetail } from "../../services/analyticsService";

// ─── helpers ────────────────────────────────────────────────────────────────

const fmtSeconds = (s) => {
  if (!s) return "0m";
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
};

const fmtDate = (iso) => {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

const DEVICE_LABELS = {
  web_browser: "Web Browser",
  mobile_app: "Mobile App",
  smart_tv: "Smart TV",
  desktop_app: "Desktop App",
  game_console: "Game Console",
  streaming_device: "Streaming Device",
  other: "Other",
};

const DEVICE_ICONS = {
  web_browser: "Globe",
  mobile_app: "Smartphone",
  smart_tv: "Tv",
  desktop_app: "Monitor",
  game_console: "Gamepad2",
  streaming_device: "Cast",
  other: "HelpCircle",
};

const BAR_COLORS = [
  "var(--color-primary)",
  "var(--color-secondary)",
  "var(--color-accent)",
  "var(--color-success)",
  "var(--color-warning)",
];

// ─── sub-components ──────────────────────────────────────────────────────────

const StatCard = ({ icon, label, value, sub }) => (
  <div className="bg-card border border-border rounded-lg p-4 flex items-start gap-3">
    <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
      <Icon name={icon} size={18} color="var(--color-primary)" />
    </div>
    <div className="min-w-0">
      <p className="text-xs text-muted-foreground mb-0.5">{label}</p>
      <p className="text-lg font-bold text-foreground leading-tight">{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
    </div>
  </div>
);

const GenreBar = ({ genre, count, max, color }) => (
  <div>
    <div className="flex items-center justify-between mb-1">
      <span className="text-sm text-foreground truncate">{genre}</span>
      <span className="text-xs font-semibold text-foreground ml-2 shrink-0">{count}</span>
    </div>
    <div className="h-1.5 bg-muted rounded-full overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{ width: `${Math.round((count / max) * 100)}%`, backgroundColor: color }}
      />
    </div>
  </div>
);

const ActivityTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-popover border border-border rounded-lg px-3 py-2 shadow-lg text-xs">
      <p className="text-muted-foreground mb-0.5">{label}</p>
      <p className="font-semibold text-foreground">{payload[0].value} plays</p>
    </div>
  );
};

// ─── main page ───────────────────────────────────────────────────────────────

const UserStats = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState(searchParams.get("user") || "");
  const [data, setData] = useState(null);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState(null);

  // Load user list for dropdown
  useEffect(() => {
    const fetchUsers = async () => {
      setLoadingUsers(true);
      try {
        const list = await getUserLeaderboard(50);
        setUsers(list || []);
        if (!selectedUser && list?.length > 0) {
          setSelectedUser(list[0].user_name);
        }
      } finally {
        setLoadingUsers(false);
      }
    };
    fetchUsers();
  }, []);

  // Load detail when user changes
  useEffect(() => {
    if (!selectedUser) return;
    setSearchParams({ user: selectedUser });
    const fetchDetail = async () => {
      setLoadingDetail(true);
      setError(null);
      try {
        const detail = await getUserDetail(selectedUser);
        if (!detail) throw new Error("No data");
        setData(detail);
      } catch {
        setError("Failed to load user data.");
        setData(null);
      } finally {
        setLoadingDetail(false);
      }
    };
    fetchDetail();
  }, [selectedUser]);

  const ov = data?.overview;
  const genreMax = data?.genres?.[0]?.count || 1;
  const deviceMax = data?.devices?.[0]?.count || 1;

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="container mx-auto px-4 pt-20 md:pt-24 pb-8">
        {/* Page header */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-4 mb-8">
          <div className="flex items-center gap-3 flex-1">
            <Button
              variant="ghost"
              size="sm"
              iconName="ArrowLeft"
              onClick={() => navigate("/jellyfin-statistics")}
            >
              Analytics
            </Button>
            <div className="w-px h-5 bg-border" />
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                <Icon name="User" size={16} color="var(--color-primary)" />
              </div>
              <h1 className="text-xl font-bold text-foreground">User Statistics</h1>
            </div>
          </div>

          {/* User dropdown */}
          <div className="flex items-center gap-2">
            <Icon name="Users" size={16} className="text-muted-foreground" />
            <select
              value={selectedUser}
              onChange={(e) => setSelectedUser(e.target.value)}
              disabled={loadingUsers}
              className="bg-card border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 min-w-40"
            >
              {loadingUsers ? (
                <option>Loading…</option>
              ) : (
                users.map((u) => (
                  <option key={u.user_name} value={u.user_name}>
                    {u.user_name}
                  </option>
                ))
              )}
            </select>
          </div>
        </div>

        {/* Loading / Error */}
        {loadingDetail && (
          <div className="flex items-center justify-center py-20">
            <Icon name="Loader" size={24} className="animate-spin text-primary mr-2" />
            <span className="text-muted-foreground">Loading stats…</span>
          </div>
        )}

        {!loadingDetail && error && (
          <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-4 flex items-center gap-2">
            <Icon name="AlertCircle" size={18} className="text-destructive" />
            <span className="text-sm text-destructive">{error}</span>
          </div>
        )}

        {!loadingDetail && data && (
          <div className="space-y-6">
            {/* ── Overview strip ───────────────────────────────────────── */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <StatCard icon="Play" label="Total Plays" value={ov.total_plays} />
              <StatCard icon="Clock" label="Hours Watched" value={`${ov.hours_watched}h`} />
              <StatCard icon="Film" label="Movies" value={ov.movies_count} />
              <StatCard icon="Tv" label="TV Episodes" value={ov.episodes_count} />
              <StatCard
                icon="Monitor"
                label="Fav. Device"
                value={DEVICE_LABELS[ov.favorite_device] || ov.favorite_device || "—"}
              />
              <StatCard icon="Calendar" label="Last Seen" value={fmtDate(ov.last_seen)} />
            </div>

            {/* ── Genre + Activity row ──────────────────────────────────── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Genres */}
              <div className="bg-card border border-border rounded-lg p-4 md:p-6">
                <div className="flex items-center gap-2 mb-5">
                  <Icon name="Tags" size={16} color="var(--color-accent)" />
                  <h3 className="text-sm font-semibold text-foreground">Top Genres Watched</h3>
                </div>
                {data.genres?.length > 0 ? (
                  <div className="space-y-3">
                    {data.genres.map((g, i) => (
                      <GenreBar
                        key={g.genre}
                        genre={g.genre}
                        count={g.count}
                        max={genreMax}
                        color={BAR_COLORS[i % BAR_COLORS.length]}
                      />
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    No genre data — sync required
                  </p>
                )}
              </div>

              {/* 30-day activity */}
              <div className="bg-card border border-border rounded-lg p-4 md:p-6">
                <div className="flex items-center gap-2 mb-5">
                  <Icon name="BarChart2" size={16} color="var(--color-primary)" />
                  <h3 className="text-sm font-semibold text-foreground">Activity — Last 30 Days</h3>
                </div>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.activity_by_day} barSize={6}>
                      <XAxis
                        dataKey="date"
                        tickFormatter={(d) => new Date(d).getDate()}
                        tick={{ fontSize: 10, fill: "var(--color-muted-foreground)" }}
                        tickLine={false}
                        axisLine={false}
                        interval={4}
                      />
                      <YAxis hide allowDecimals={false} />
                      <Tooltip content={<ActivityTooltip />} cursor={false} />
                      <Bar dataKey="plays" radius={[3, 3, 0, 0]}>
                        {data.activity_by_day.map((entry, i) => (
                          <Cell
                            key={i}
                            fill={entry.plays > 0 ? "var(--color-primary)" : "var(--color-muted)"}
                            opacity={entry.plays > 0 ? 0.8 : 0.3}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* ── Devices + Playback methods row ───────────────────────── */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Devices */}
              <div className="bg-card border border-border rounded-lg p-4 md:p-6">
                <div className="flex items-center gap-2 mb-5">
                  <Icon name="Monitor" size={16} color="var(--color-secondary)" />
                  <h3 className="text-sm font-semibold text-foreground">Devices</h3>
                </div>
                <div className="space-y-3">
                  {data.devices.map((d, i) => (
                    <div key={d.device_type} className="flex items-center gap-3">
                      <div
                        className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                        style={{ backgroundColor: `${BAR_COLORS[i % BAR_COLORS.length]}20` }}
                      >
                        <Icon
                          name={DEVICE_ICONS[d.device_type] || "Monitor"}
                          size={14}
                          color={BAR_COLORS[i % BAR_COLORS.length]}
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex justify-between mb-1">
                          <span className="text-sm text-foreground truncate">
                            {DEVICE_LABELS[d.device_type] || d.device_type}
                          </span>
                          <span className="text-xs font-semibold text-foreground ml-2 shrink-0">
                            {d.percentage}%
                          </span>
                        </div>
                        <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${Math.round((d.count / deviceMax) * 100)}%`,
                              backgroundColor: BAR_COLORS[i % BAR_COLORS.length],
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Playback methods */}
              <div className="bg-card border border-border rounded-lg p-4 md:p-6">
                <div className="flex items-center gap-2 mb-5">
                  <Icon name="Zap" size={16} color="var(--color-success)" />
                  <h3 className="text-sm font-semibold text-foreground">Playback Method</h3>
                </div>
                {(() => {
                  const { direct, transcoded } = data.playback_methods;
                  const total = direct + transcoded || 1;
                  const directPct = Math.round((direct / total) * 100);
                  const transcodedPct = 100 - directPct;
                  return (
                    <div className="space-y-4">
                      <div>
                        <div className="flex justify-between mb-1.5">
                          <div className="flex items-center gap-1.5">
                            <div className="w-2 h-2 rounded-full bg-success" />
                            <span className="text-sm text-foreground">Direct Play</span>
                          </div>
                          <span className="text-sm font-semibold text-foreground">
                            {direct}{" "}
                            <span className="text-xs text-muted-foreground">({directPct}%)</span>
                          </span>
                        </div>
                        <div className="h-2.5 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full bg-success transition-all duration-500"
                            style={{ width: `${directPct}%` }}
                          />
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between mb-1.5">
                          <div className="flex items-center gap-1.5">
                            <div className="w-2 h-2 rounded-full bg-warning" />
                            <span className="text-sm text-foreground">Transcoded</span>
                          </div>
                          <span className="text-sm font-semibold text-foreground">
                            {transcoded}{" "}
                            <span className="text-xs text-muted-foreground">
                              ({transcodedPct}%)
                            </span>
                          </span>
                        </div>
                        <div className="h-2.5 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full bg-warning transition-all duration-500"
                            style={{ width: `${transcodedPct}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })()}
              </div>
            </div>

            {/* ── Top titles ───────────────────────────────────────────── */}
            <div className="bg-card border border-border rounded-lg p-4 md:p-6">
              <div className="flex items-center gap-2 mb-5">
                <Icon name="Star" size={16} color="var(--color-accent)" />
                <h3 className="text-sm font-semibold text-foreground">Top Titles</h3>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
                {data.top_titles.map((t, i) => (
                  <div key={t.title} className="bg-muted/30 rounded-lg p-3 flex items-start gap-3">
                    <span className="text-xs font-bold text-muted-foreground w-4 shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-foreground truncate">{t.title}</p>
                      <div className="flex items-center gap-1.5 mt-1">
                        <Icon
                          name={t.media_type === "movie" ? "Film" : "Tv"}
                          size={11}
                          className="text-muted-foreground"
                        />
                        <span className="text-xs text-muted-foreground capitalize">
                          {t.media_type}
                        </span>
                        <span className="text-xs text-muted-foreground">·</span>
                        <span className="text-xs font-semibold text-primary">{t.plays}×</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* ── Recent activity ───────────────────────────────────────── */}
            <div className="bg-card border border-border rounded-lg p-4 md:p-6">
              <div className="flex items-center gap-2 mb-5">
                <Icon name="History" size={16} color="var(--color-primary)" />
                <h3 className="text-sm font-semibold text-foreground">Recent Activity</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left">
                      <th className="pb-3 pr-4 text-xs font-semibold text-muted-foreground">
                        Title
                      </th>
                      <th className="pb-3 pr-4 text-xs font-semibold text-muted-foreground">
                        Type
                      </th>
                      <th className="pb-3 pr-4 text-xs font-semibold text-muted-foreground">
                        Watched
                      </th>
                      <th className="pb-3 pr-4 text-xs font-semibold text-muted-foreground">
                        Device
                      </th>
                      <th className="pb-3 text-xs font-semibold text-muted-foreground">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/50">
                    {data.recent_sessions.map((s, i) => (
                      <tr key={i} className="hover:bg-muted/20 transition-colors">
                        <td className="py-2.5 pr-4">
                          <div>
                            <span className="font-medium text-foreground">{s.media_title}</span>
                            {s.episode_info && (
                              <span className="ml-2 text-xs text-muted-foreground">
                                {s.episode_info}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-2.5 pr-4">
                          <div className="flex items-center gap-1.5">
                            <Icon
                              name={s.media_type === "movie" ? "Film" : "Tv"}
                              size={12}
                              className="text-muted-foreground"
                            />
                            <span className="text-xs text-muted-foreground capitalize">
                              {s.media_type}
                            </span>
                          </div>
                        </td>
                        <td className="py-2.5 pr-4 text-muted-foreground">
                          {fmtSeconds(s.watched_seconds)}
                        </td>
                        <td className="py-2.5 pr-4 text-muted-foreground">
                          {DEVICE_LABELS[s.device_type] || s.device_type}
                        </td>
                        <td className="py-2.5 text-muted-foreground">{fmtDate(s.start_time)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default UserStats;
