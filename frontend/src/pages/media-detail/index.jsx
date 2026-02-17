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
} from "../../services/libraryService";

const MediaDetail = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const [media, setMedia] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMedia = async () => {
      try {
        if (!id) {
          setLoading(false);
          return;
        }

        const data = await getLibraryItemById(id);

        const seasonsData =
          data.media_type === "tv" ? await getSeasonsWithEpisodes(id) : [];

        const torrent = data.torrent_info?.[0] || {};

        const downloadedEpisodes = seasonsData.reduce(
          (s, se) => s + se.episode_file_count,
          0,
        );
        const totalEpisodes = seasonsData.reduce(
          (s, se) => s + se.total_episode_count,
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

          fileInfo: {
            size: data.size,
            torrentInfo: { seedRatio: torrent.ratio, status: torrent.status },
          },

          monitored: seasonsData.some((s) => s.is_monitored),
          downloadedEpisodes,
          totalEpisodes,
          missingEpisodes: totalEpisodes - downloadedEpisodes,

          seasons: seasonsData.map((s) => ({
            seasonNumber: s.season_number,
            episodes: s.episodes.map((ep) => ({
              episodeNumber: ep.episode_number,
              title: ep.title,
              airDate: ep.air_date,
              monitored: ep.monitored,
              downloaded: ep.has_file,
              downloadStatus: ep.download_status,
              fileSize: ep.file_size_str,
              quality: ep.quality_profile,
              hasSubtitles: false,
              watched: false,
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
      {/* Hero Banner */}
      <HeroBanner media={media} />

      {/* Main Content */}
      <div className="container mx-auto px-4 py-6 md:py-8 space-y-6">
        {/* Back Button */}
        <Button
          variant="ghost"
          size="sm"
          iconName="ArrowLeft"
          onClick={() => navigate("/library")}
        >
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
          <EpisodesList seasons={media.seasons} />
        )}
      </div>
    </div>
  );
};

export default MediaDetail;
