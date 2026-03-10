import React, { useState } from "react";
import Icon from "../../../components/AppIcon";
import Button from "../../../components/ui/Button";
import StatusIndicator from "../../monitoring/components/StatusIndicator";
import {
  setEpisodeWatched,
  setSeasonWatched,
  monitorEpisode,
  searchEpisode,
} from "../../../services/libraryService";

const EpisodesList = ({ seasons, mediaId }) => {
  const [seasonsState, setSeasonsState] = useState(seasons);
  const [expandedSeasons, setExpandedSeasons] = useState([0]); // First season expanded by default
  const [watchedMap, setWatchedMap] = useState(() =>
    Object.fromEntries(
      seasons.flatMap((s, si) => s.episodes.map((ep, ei) => [`${si}-${ei}`, ep.watched ?? false])),
    ),
  );

  const toggleSeason = (seasonIndex) => {
    setExpandedSeasons((prev) =>
      prev?.includes(seasonIndex) ? prev?.filter((i) => i !== seasonIndex) : [...prev, seasonIndex],
    );
  };

  const getDownloadStatusConfig = (status) => {
    switch (status) {
      case "downloaded":
        return { type: "availability", status: "available" };
      case "downloading":
        return { type: "availability", status: "downloading" };
      case "missing":
        return { type: "availability", status: "missing" };
      default:
        return { type: "availability", status: "missing" };
    }
  };

  const handleEpisodeWatchedToggle = async (sIdx, eIdx, season, episode) => {
    const key = `${sIdx}-${eIdx}`;
    const newWatched = !watchedMap[key];
    setWatchedMap((prev) => ({ ...prev, [key]: newWatched }));
    await setEpisodeWatched(mediaId, season.seasonNumber, episode.episodeNumber, newWatched);
  };

  const handleSeasonWatchedToggle = async (sIdx, season) => {
    const allWatched = season.episodes.every((_, ei) => watchedMap[`${sIdx}-${ei}`]);
    const newWatched = !allWatched;
    const updates = Object.fromEntries(
      season.episodes.map((_, ei) => [`${sIdx}-${ei}`, newWatched]),
    );
    setWatchedMap((prev) => ({ ...prev, ...updates }));
    await setSeasonWatched(mediaId, season.seasonNumber, newWatched);
  };

  const handleMonitor = async (season, episode) => {
    await monitorEpisode(mediaId, season.seasonNumber, episode.episodeNumber);
    // Optimistic update
    setSeasonsState((prev) =>
      prev.map((s) =>
        s.seasonNumber !== season.seasonNumber
          ? s
          : {
              ...s,
              episodes: s.episodes.map((ep) =>
                ep.episodeNumber === episode.episodeNumber ? { ...ep, monitored: true } : ep,
              ),
            },
      ),
    );
  };

  const handleSearch = async (season, episode) => {
    await searchEpisode(mediaId, season.seasonNumber, episode.episodeNumber);
  };

  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden">
      <div className="p-6 border-b border-border">
        <h2 className="text-xl font-semibold text-foreground flex items-center gap-2">
          <Icon name="List" size={20} className="text-primary" />
          Seasons & Episodes
        </h2>
      </div>

      <div className="divide-y divide-border">
        {seasonsState?.map((season, seasonIndex) => (
          <div key={seasonIndex}>
            {/* Season Header */}
            <div
              role="button"
              tabIndex={0}
              onClick={() => toggleSeason(seasonIndex)}
              onKeyDown={(e) => e.key === "Enter" && toggleSeason(seasonIndex)}
              className="w-full px-6 py-4 flex items-center justify-between hover:bg-muted/50 transition-colors cursor-pointer"
            >
              <div className="flex items-center gap-3">
                <Icon
                  name={expandedSeasons?.includes(seasonIndex) ? "ChevronDown" : "ChevronRight"}
                  size={20}
                  className="text-muted-foreground"
                />
                <h3 className="text-lg font-semibold text-foreground">
                  {season?.name || `Season ${season?.seasonNumber}`}
                </h3>
                <span className="text-sm text-muted-foreground">
                  {season?.episodes?.length} episodes
                </span>
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${
                    season?.monitored
                      ? "bg-success/10 border-success/20 text-success"
                      : "bg-muted/60 border-border text-muted-foreground"
                  }`}
                >
                  <Icon name={season?.monitored ? "Bell" : "BellOff"} size={11} />
                  {season?.monitored ? "Monitored" : "Unmonitored"}
                </span>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-sm text-muted-foreground">
                  {season?.episodes?.filter((ep) => ep?.downloaded)?.length} /{" "}
                  {season?.episodes?.length} downloaded
                </div>
                <Button
                  size="xs"
                  variant="ghost"
                  iconName={
                    season.episodes.every((_, ei) => watchedMap[`${seasonIndex}-${ei}`])
                      ? "CheckCircle2"
                      : "Circle"
                  }
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSeasonWatchedToggle(seasonIndex, season);
                  }}
                  title="Mark season as watched/unwatched"
                />
              </div>
            </div>

            {/* Episodes List */}
            {expandedSeasons?.includes(seasonIndex) && (
              <div className="bg-muted/30">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-muted">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase">
                          Episode
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase">
                          Title
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase">
                          Air Date
                        </th>
                        <th className="px-6 py-3 text-center text-xs font-semibold text-muted-foreground uppercase">
                          Status
                        </th>
                        <th className="px-6 py-3 text-center text-xs font-semibold text-muted-foreground uppercase">
                          Monitored
                        </th>
                        <th className="px-6 py-3 text-center text-xs font-semibold text-muted-foreground uppercase">
                          Subtitles
                        </th>
                        <th className="px-6 py-3 text-right text-xs font-semibold text-muted-foreground uppercase">
                          File Size
                        </th>
                        <th className="px-6 py-3 text-center text-xs font-semibold text-muted-foreground uppercase">
                          Watched
                        </th>
                        <th className="px-6 py-3 text-center text-xs font-semibold text-muted-foreground uppercase">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {season?.episodes?.map((episode, episodeIndex) => (
                        <tr key={episodeIndex} className="hover:bg-muted/50 transition-colors">
                          {/* Episode Number */}
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className="text-sm font-medium text-foreground">
                              {episode?.episodeNumber}
                            </span>
                          </td>

                          {/* Title */}
                          <td className="px-6 py-4">
                            <span className="text-sm text-foreground">{episode?.title}</span>
                          </td>

                          {/* Air Date */}
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className="text-sm text-muted-foreground">
                              {episode?.airDate || "TBA"}
                            </span>
                          </td>

                          {/* Download Status */}
                          <td className="px-6 py-4 text-center">
                            <div className="flex justify-center">
                              <StatusIndicator
                                {...getDownloadStatusConfig(episode?.downloadStatus)}
                              />
                            </div>
                          </td>

                          {/* Monitored */}
                          <td className="px-6 py-4 text-center">
                            <Icon
                              name={episode?.monitored ? "Bell" : "BellOff"}
                              size={15}
                              className={
                                episode?.monitored
                                  ? "text-success mx-auto"
                                  : "text-muted-foreground/40 mx-auto"
                              }
                              title={episode?.monitored ? "Monitored" : "Unmonitored"}
                            />
                          </td>

                          {/* Subtitles */}
                          <td className="px-6 py-4 text-center">
                            {episode?.hasSubtitles ? (
                              <div className="flex justify-center items-center gap-1">
                                <Icon name="Subtitles" size={14} className="text-success" />
                                {episode?.subtitleLanguages && (
                                  <span className="text-xs text-muted-foreground">
                                    ({episode?.subtitleLanguages?.join(", ")})
                                  </span>
                                )}
                              </div>
                            ) : (
                              <Icon name="Subtitles" size={14} className="text-muted-foreground" />
                            )}
                          </td>

                          {/* File Size */}
                          <td className="px-6 py-4 text-right whitespace-nowrap">
                            <span className="text-sm text-foreground font-medium">
                              {episode?.fileSize || "-"}
                            </span>
                          </td>

                          {/* Watched Status */}
                          <td className="px-6 py-4 text-center">
                            {watchedMap[`${seasonIndex}-${episodeIndex}`] ? (
                              <Icon
                                name="CheckCircle2"
                                size={16}
                                className="text-success mx-auto"
                              />
                            ) : (
                              <Icon
                                name="Circle"
                                size={16}
                                className="text-muted-foreground mx-auto"
                              />
                            )}
                          </td>

                          {/* Actions */}
                          <td className="px-6 py-4">
                            <div className="flex items-center justify-center gap-2">
                              <Button
                                size="xs"
                                variant="ghost"
                                iconName={
                                  watchedMap[`${seasonIndex}-${episodeIndex}`]
                                    ? "CheckCircle2"
                                    : "Circle"
                                }
                                onClick={() =>
                                  handleEpisodeWatchedToggle(
                                    seasonIndex,
                                    episodeIndex,
                                    season,
                                    episode,
                                  )
                                }
                                title={
                                  watchedMap[`${seasonIndex}-${episodeIndex}`]
                                    ? "Mark as unwatched"
                                    : "Mark as watched"
                                }
                              />
                              {!episode?.monitored ? (
                                <Button
                                  size="xs"
                                  variant="ghost"
                                  iconName="Bell"
                                  onClick={() => handleMonitor(season, episode)}
                                  title="Monitor this episode"
                                />
                              ) : !episode?.downloaded ? (
                                <Button
                                  size="xs"
                                  variant="ghost"
                                  iconName="RefreshCw"
                                  onClick={() => handleSearch(season, episode)}
                                  title="Refresh search"
                                />
                              ) : null}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default EpisodesList;
