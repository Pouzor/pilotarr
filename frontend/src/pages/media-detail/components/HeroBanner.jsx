import React, { useState } from "react";
import Image from "../../../components/AppImage";
import Icon from "../../../components/AppIcon";
import Button from "../../../components/ui/Button";

const HeroBanner = ({ media, onRefresh, isRefreshing = false }) => {
  const [isMonitored, setIsMonitored] = useState(media?.monitored || false);

  const getTypeIcon = () => {
    return media?.mediaType === "movie" ? "Film" : "Tv";
  };

  const getTypeColor = () => {
    return media?.mediaType === "movie" ? "text-blue-400" : "text-purple-400";
  };

  const handleMonitorToggle = () => {
    // TODO: API call to toggle monitoring
    setIsMonitored(!isMonitored);
  };

  return (
    <div className="relative w-full h-[400px] md:h-[500px] overflow-hidden">
      {/* Background Image with Overlay */}
      <div className="absolute inset-0">
        <Image
          src={media?.backdropImage || media?.image}
          alt={media?.imageAlt}
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-background via-background/80 to-background/40"></div>
      </div>

      {/* Content */}
      <div className="relative h-full container mx-auto px-4 flex items-end pb-8">
        <div className="flex flex-col md:flex-row gap-6 w-full">
          {/* Poster */}
          <div className="flex-shrink-0 w-40 md:w-48 lg:w-56">
            <div className="aspect-[2/3] rounded-lg overflow-hidden shadow-elevation-3 border-2 border-border">
              <Image
                src={media?.image}
                alt={media?.imageAlt}
                className="w-full h-full object-cover"
              />
            </div>
          </div>

          {/* Info */}
          <div className="flex-1 space-y-4">
            {/* Title and Year */}
            <div>
              <div className="flex items-center gap-3 mb-2">
                <Icon name={getTypeIcon()} size={24} className={getTypeColor()} />
                <span className="text-sm font-medium text-muted-foreground uppercase">
                  {media?.mediaType}
                </span>
              </div>
              <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold text-foreground mb-2">
                {media?.title}
              </h1>
              <div className="flex items-center gap-4 text-muted-foreground">
                <span className="text-lg">{media?.year}</span>
                {media?.rating && (
                  <div className="flex items-center gap-1">
                    <Icon name="Star" size={18} className="text-warning fill-warning" />
                    <span className="text-lg font-semibold text-foreground">{media?.rating}</span>
                  </div>
                )}
                {media?.runtime && (
                  <div className="flex items-center gap-1">
                    <Icon name="Clock" size={16} />
                    <span>{media?.runtime}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Overview */}
            <p className="text-sm md:text-base text-foreground/90 max-w-3xl line-clamp-3">
              {media?.description}
            </p>

            {/* Genres */}
            {media?.genres && media?.genres?.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {media?.genres?.map((genre, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-accent/20 text-accent-foreground text-xs font-medium rounded-full"
                  >
                    {genre}
                  </span>
                ))}
              </div>
            )}

            {/* Actions */}
            <div className="flex flex-wrap gap-3">
              <Button
                variant={isMonitored ? "success" : "outline"}
                iconName={isMonitored ? "Eye" : "EyeOff"}
                onClick={handleMonitorToggle}
              >
                {isMonitored ? "Monitored" : "Unmonitored"}
              </Button>
              <Button variant="outline" iconName="Search">
                Manual Search
              </Button>
              <Button
                variant="outline"
                iconName="RefreshCw"
                loading={isRefreshing}
                onClick={onRefresh}
                disabled={isRefreshing}
              >
                Refresh
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HeroBanner;
