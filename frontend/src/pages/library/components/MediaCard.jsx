import React from "react";
import { useNavigate } from "react-router-dom";
import Image from "../../../components/AppImage";
import Icon from "../../../components/AppIcon";

const MediaCard = ({ item }) => {
  const navigate = useNavigate();

  const getTypeIcon = () => {
    return item?.type === "movie" ? "Film" : "Tv";
  };

  const getTypeColor = () => {
    return item?.type === "movie" ? "text-blue-400" : "text-purple-400";
  };

  const formatDate = (dateString) => {
    if (!dateString) return "Unknown";
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return "Unknown";
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const getSeedRatioColor = (ratio) => {
    if (ratio >= 1) return "text-success";
    if (ratio >= 0.5) return "text-warning";
    return "text-error";
  };

  const handleClick = () => {
    navigate(`/library/${item.id}`);
  };

  return (
    <div
      onClick={handleClick}
      className="bg-card border border-border rounded-lg overflow-hidden hover:shadow-elevation-2 transition-smooth group cursor-pointer"
    >
      {/* Media Image */}
      <div className="relative aspect-[2/3] overflow-hidden bg-muted">
        <Image
          src={item?.image}
          alt={item?.imageAlt}
          className="w-full h-full object-cover group-hover:scale-105 transition-smooth"
        />

        {/* Type Badge */}
        <div className="absolute top-2 right-2 bg-background/90 backdrop-blur-sm px-2 py-1 rounded-md flex items-center gap-1">
          <Icon name={getTypeIcon()} size={14} className={getTypeColor()} />
          <span className="text-xs font-medium text-foreground capitalize">
            {item?.type}
          </span>
        </div>

        {/* Quality Badge */}
        {item?.quality && (
          <div className="absolute top-2 left-2 bg-accent/90 backdrop-blur-sm px-2 py-1 rounded-md">
            <span className="text-xs font-bold text-accent-foreground">
              {item?.quality}
            </span>
          </div>
        )}

        {/* Subtitle Badge */}
        <div className="absolute bottom-2 left-2">
          {item?.hasSubtitles ? (
            <div className="bg-success/90 backdrop-blur-sm px-2 py-1 rounded-md flex items-center gap-1">
              <Icon
                name="Subtitles"
                size={12}
                className="text-success-foreground"
              />
              <span className="text-xs font-medium text-success-foreground">
                Subs
              </span>
            </div>
          ) : (
            <div className="bg-muted/90 backdrop-blur-sm px-2 py-1 rounded-md flex items-center gap-1">
              <Icon
                name="Subtitles"
                size={12}
                className="text-muted-foreground"
              />
              <span className="text-xs font-medium text-muted-foreground">
                No Subs
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Media Info */}
      <div className="p-3 md:p-4">
        <h3 className="text-sm md:text-base font-semibold text-foreground mb-3 line-clamp-2 min-h-[2.5rem]">
          {item?.title}
        </h3>

        {/* Metadata Grid */}
        <div className="space-y-2">
          {/* Added Date */}
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-1 text-muted-foreground">
              <Icon name="Calendar" size={12} />
              <span>Added</span>
            </div>
            <span className="font-medium text-foreground">
              {formatDate(item?.addedDate)}
            </span>
          </div>

          {/* File Size */}
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-1 text-muted-foreground">
              <Icon name="HardDrive" size={12} />
              <span>Size</span>
            </div>
            <span className="font-medium text-foreground">{item?.size}</span>
          </div>
          {item?.torrent_info != null ? (
            <>
              {/* Files Count */}
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1 text-muted-foreground">
                  <Icon name="FileStack" size={12} />
                  <span>Files</span>
                </div>
                <span className="font-medium text-foreground">
                  {item?.nbMedia}
                </span>
              </div>

              {/* View Count */}
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1 text-muted-foreground">
                  <Icon name="Eye" size={12} />
                  <span>Views</span>
                </div>
                <span className="font-medium text-foreground">
                  {item?.viewCount}
                </span>
              </div>

              {/* Seed Ratio */}
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1 text-muted-foreground">
                  <Icon name="Upload" size={12} />
                  <span>Ratio</span>
                </div>
                <div className="flex items-center gap-1.5">
                  {item?.torrentCount > 1 && (
                    <span className="bg-primary/15 text-primary text-[10px] font-semibold px-1.5 py-0.5 rounded">
                      {item?.torrentCount}T
                    </span>
                  )}
                  <span
                    className={`font-bold ${getSeedRatioColor(item?.seedRatio)}`}
                  >
                    {item?.seedRatio?.toFixed(2)}
                  </span>
                </div>
              </div>
            </>
          ) : (
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-1 text-muted-foreground">
                <span className="font-bold text-warning">
                  No Download informations
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MediaCard;
