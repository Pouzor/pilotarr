import React from "react";
import Icon from "../../../components/AppIcon";
import Image from "../../../components/AppImage";
import Button from "../../../components/ui/Button";

const RequestCard = ({ request, onApprove, onReject }) => {
  const getTypeIcon = () => {
    return request?.mediaType === "movie" ? "Film" : "Tv";
  };

  const getTypeColor = () => {
    return request?.mediaType === "movie" ? "text-blue-400" : "text-purple-400";
  };

  const getPriorityColor = () => {
    const colors = {
      high: "bg-error/10 text-error border-error/20",
      medium: "bg-warning/10 text-warning border-warning/20",
      low: "bg-muted text-muted-foreground border-border",
    };
    return colors?.[request?.priority] || colors?.low;
  };

  // PENDING=1, APPROVED=2, DECLINED=3, AVAILABLE=4
  const isPending = request?.status === 1;
  const isApproved = request?.status === 2;
  const isDeclined = request?.status === 3;
  const isAvailable = request?.status === 4;

  return (
    <div className="bg-card border border-border rounded-lg p-3 md:p-4 hover:shadow-elevation-2 transition-smooth">
      <div className="flex gap-3 md:gap-4">
        <div className="flex-shrink-0 w-16 h-24 md:w-20 md:h-28 rounded-md overflow-hidden bg-muted">
          <Image
            src={request?.imageUrl}
            alt={request?.imageAlt}
            className="w-full h-full object-cover"
          />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-2">
            <div className="flex-1 min-w-0">
              <h4 className="text-sm md:text-base font-semibold text-foreground line-clamp-1 mb-1">
                {request?.title}
              </h4>
              <div className="flex items-center gap-2 flex-wrap">
                <div className="flex items-center gap-1">
                  <Icon name={getTypeIcon()} size={14} className={getTypeColor()} />
                  <span className="text-xs text-muted-foreground capitalize">
                    {request?.mediaType}
                  </span>
                </div>
                {request?.year && (
                  <>
                    <span className="text-xs text-muted-foreground">•</span>
                    <span className="text-xs text-muted-foreground">{request?.year}</span>
                  </>
                )}
              </div>
            </div>
            {request?.priority && (
              <div className={`px-2 py-1 rounded-md text-xs font-medium ${getPriorityColor()}`}>
                {request?.priority}
              </div>
            )}
          </div>
          {request?.description && (
            <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
              {request?.description}
            </p>
          )}
          <div className="flex items-center gap-2 mb-3 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <Icon name="User" size={12} />
              <span>{request?.requestedBy}</span>
            </div>
            {request?.requestedDate && (
              <>
                <span>•</span>
                <div className="flex items-center gap-1">
                  <Icon name="Clock" size={12} />
                  <span>{request?.requestedDate}</span>
                </div>
              </>
            )}
          </div>
          {request?.quality && (
            <div className="flex items-center gap-2 mb-3 text-xs">
              <Icon name="Settings" size={12} className="text-muted-foreground" />
              <span className="text-muted-foreground">Quality: {request?.quality}</span>
            </div>
          )}
          {isPending && (
            <div className="flex gap-2">
              <Button
                variant="success"
                size="xs"
                onClick={() => onApprove(request?.id)}
                iconName="Check"
                iconSize={14}
                className="flex-1"
              >
                Approve
              </Button>
              <Button
                variant="destructive"
                size="xs"
                onClick={() => onReject(request?.id)}
                iconName="X"
                iconSize={14}
                className="flex-1"
              >
                Reject
              </Button>
            </div>
          )}
          {isApproved && (
            <div className="flex items-center gap-2 text-xs text-success">
              <Icon name="CheckCircle" size={14} />
              <span className="font-medium">Approved</span>
            </div>
          )}
          {isDeclined && (
            <div className="flex items-center gap-2 text-xs text-error">
              <Icon name="XCircle" size={14} />
              <span className="font-medium">Declined</span>
            </div>
          )}
          {isAvailable && (
            <div className="flex items-center gap-2 text-xs text-purple-400">
              <Icon name="PackageCheck" size={14} />
              <span className="font-medium">Available</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default RequestCard;
