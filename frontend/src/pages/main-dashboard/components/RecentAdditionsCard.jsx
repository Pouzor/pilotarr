import React from "react";
import { useNavigate } from "react-router-dom";
import Image from "../../../components/AppImage";
import Icon from "../../../components/AppIcon";

const RecentAdditionsCard = ({ item }) => {
  const navigate = useNavigate();

  const getTypeIcon = () => {
    return item?.type === "movie" ? "Film" : "Tv";
  };

  const getTypeColor = () => {
    return item?.type === "movie" ? "text-blue-400" : "text-purple-400";
  };

  const handleClick = () => {
    navigate(`/library/${item?.id || ""}`);
  };

  const formatTimeAgo = (dateValue) => {
    if (!dateValue) return "Unknown";
    const date = new Date(dateValue);
    if (isNaN(date.getTime())) return "Unknown";
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
    if (seconds < 60) return "just now";
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} minute${minutes > 1 ? "s" : ""} ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} hour${hours > 1 ? "s" : ""} ago`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days} day${days > 1 ? "s" : ""} ago`;
    const months = Math.floor(days / 30);
    if (months < 12) return `${months} month${months > 1 ? "s" : ""} ago`;
    const years = Math.floor(months / 12);
    return `${years} year${years > 1 ? "s" : ""} ago`;
  };

  return (
    <div
      onClick={handleClick}
      className="bg-card border border-border rounded-lg overflow-hidden hover:shadow-elevation-2 transition-smooth group cursor-pointer"
    >
      <div className="relative aspect-[2/3] overflow-hidden bg-muted">
        <Image
          src={item?.image}
          alt={item?.imageAlt}
          className="w-full h-full object-cover group-hover:scale-105 transition-smooth"
        />
        <div className="absolute top-2 right-2 bg-background/90 backdrop-blur-sm px-2 py-1 rounded-md flex items-center gap-1">
          <Icon name={getTypeIcon()} size={14} className={getTypeColor()} />
          <span className="text-xs font-medium text-foreground capitalize">
            {item?.type}
          </span>
        </div>
        {item?.quality && (
          <div className="absolute top-2 left-2 bg-accent/90 backdrop-blur-sm px-2 py-1 rounded-md">
            <span className="text-xs font-bold text-accent-foreground">
              {item?.quality}
            </span>
          </div>
        )}
      </div>
      <div className="p-2 md:p-3">
        <h3 className="text-xs md:text-sm font-semibold text-foreground mb-1 line-clamp-1">
          {item?.title}
        </h3>
        <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
          <span>{item?.year}</span>
          {item?.rating && (
            <div className="flex items-center gap-1">
              <Icon
                name="Star"
                size={12}
                className="text-warning fill-warning"
              />
              <span>{item?.rating}</span>
            </div>
          )}
        </div>
        <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
          {item?.description}
        </p>
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">
            Added {formatTimeAgo(item?.addedDate)}
          </span>
          <div className="flex items-center gap-1 text-success">
            <Icon name="Download" size={12} />
            <span className="font-medium">{item?.size}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RecentAdditionsCard;
