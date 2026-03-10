import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";

import Button from "../../components/ui/Button";
import HeroBanner from "./components/HeroBanner";
import MetadataPanel from "./components/MetadataPanel";
import EpisodesList from "./components/EpisodesList";
import FileInfoPanel from "./components/FileInfoPanel";
import {
  getLibraryItemById,
  getSeasonsWithEpisodes,
  refreshMediaItem,
} from "../../services/libraryService";
import Toast from "../../components/ui/Toast";
import { getServiceConfiguration } from "../../services/configService";

const buildUrl = (config) => {
  if (!config?.url) return null;
  const base = config.url.replace(/\/$/, "");
  if (config.port && !base.includes(`:${config.port}`)) return `${base}:${config.port}`;
  return base;
};

const MediaDetail = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const [media, setMedia] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    const fetchMedia = async () => {
      try {
        if (!id) {
          setLoading(false);
          return;
        }

        const [data, jellyfinConfig, sonarrConfig, radarrConfig] = await Promise.all([
          getLibraryItemById(id),
          getServiceConfiguration("jellyfin"),
          getServiceConfiguration("sonarr"),
          getServiceConfiguration("radarr"),
        ]);

        const seasonsData = data.media_type === "tv" ? await getSeasonsWithEpisodes(id) : [];

        const torrent = data.torrent_info?.[0] || {};

        const downloadedEpisodes = seasonsData.reduce((s, se) => s + se.episode_file_count, 0);
        const totalEpisodes = seasonsData.reduce((s, se) => s + se.total_episode_count, 0);
        const watchedEpisodes = seasonsData.reduce(
          (s, se) => s + se.episodes.filter((ep) => ep.watched).length,
          0,
        );

        const media = {
          id: data.id,
          title: data.title,
          mediaType: data.media_type,
          year: data.year,
          rating: data.rating,
          runtime: null,
          genres: [],
          overview: data.description,
          image: data.image_url,
          backdropImage: data.image_url,
          status: null,
          network: null,
          nbMedia: data.nb_media,
          addedDate: data.added_date,
          jellyfinId: data.jellyfin_id,
          sonarrSeriesId: data.sonarr_series_id,
          serviceUrls: {
            jellyfin: buildUrl(jellyfinConfig),
            sonarr: buildUrl(sonarrConfig),
            radarr: buildUrl(radarrConfig),
          },

          fileInfo: {
            quality: data.quality,
            size: data.size,
            torrentInfo: { seedRatio: torrent.ratio, status: torrent.status },
            subtitles: data.media_streams?.subtitles || [],
            subtitleCounts: seasonsData.reduce((acc, season) => {
              season.episodes.forEach((ep) => {
                ep.media_streams?.subtitles?.forEach((sub) => {
                  const lang = sub.language || "Unknown";
                  acc[lang] = (acc[lang] || 0) + 1;
                });
              });
              return acc;
            }, {}),
          },

          viewCount: data.media_type === "tv" ? watchedEpisodes : data.view_count || 0,
          monitored: seasonsData.some((s) => s.is_monitored),
          downloadedEpisodes,
          totalEpisodes,
          missingEpisodes: totalEpisodes - downloadedEpisodes,

          seasons: seasonsData.map((s) => ({
            seasonNumber: s.season_number,
            monitored: s.is_monitored,
            episodes: s.episodes.map((ep) => ({
              episodeNumber: ep.episode_number,
              sonarrEpisodeId: ep.sonarr_episode_id,
              title: ep.title,
              airDate: ep.air_date,
              monitored: ep.monitored,
              downloaded: ep.has_file,
              downloadStatus: ep.download_status,
              fileSize: ep.file_size_str,
              quality: ep.quality_profile,
              hasSubtitles: (ep.media_streams?.subtitles?.length ?? 0) > 0,
              subtitleLanguages: ep.media_streams?.subtitles?.map((s) => s.language) ?? [],
              watched: ep.watched ?? false,
            })),
          })),
        };

        setMedia(media);
      } catch (error) {
        console.error("Failed to fetch media detail", error);
      } finally {
        setLoading(false);
      }
    };

    fetchMedia();
  }, [id]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      const result = await refreshMediaItem(id);
      setToast({ message: result?.message || "Refresh and scan started.", variant: "success" });
    } catch {
      setToast({
        message: "Failed to start refresh. Check service configuration.",
        variant: "error",
      });
    } finally {
      setIsRefreshing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
          <p className="text-muted-foreground">Loading media details...</p>
        </div>
      </div>
    );
  }

  if (!media) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-muted-foreground">Media not found.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Toast notification */}
      {toast && (
        <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />
      )}

      {/* Hero Banner */}
      <HeroBanner media={media} onRefresh={handleRefresh} isRefreshing={isRefreshing} />

      {/* Main Content */}
      <div className="container mx-auto px-4 py-6 md:py-8 space-y-6">
        {/* Back Button */}
        <Button variant="ghost" size="sm" iconName="ArrowLeft" onClick={() => navigate("/library")}>
          Back to Library
        </Button>

        {/* Metadata and File Info Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Metadata Panel */}
          <div className="lg:col-span-2">
            <MetadataPanel media={media} />
          </div>

          {/* File Info Panel */}
          <div className="lg:col-span-1">
            <FileInfoPanel media={media} />
          </div>
        </div>

        {/* Episodes List (TV Shows Only) */}
        {media?.mediaType === "tv" && media?.seasons && (
          <EpisodesList seasons={media.seasons} mediaId={id} />
        )}
      </div>
    </div>
  );
};

export default MediaDetail;
