import React from "react";
import Icon from "../../../components/AppIcon";

const ExpandableRow = ({ item }) => {
  return (
    <div className="bg-muted/20 p-4 rounded-lg my-2">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Season Information (TV Shows only) */}
        {item?.service === "sonarr" && item?.seasons && (
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
              <Icon name="Layers" size={16} className="text-primary" />
              Season Information
            </h4>
            <div className="space-y-2">
              {item?.seasons?.map((season) => (
                <div
                  key={season?.number}
                  className="bg-card border border-border rounded-md p-3 flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-md bg-primary/10 flex items-center justify-center">
                      <span className="text-xs font-bold text-primary">S{season?.number}</span>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Season {season?.number}</p>
                      <p className="text-sm font-medium text-foreground">
                        {season?.available}/{season?.episodes} episodes
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {season?.monitored > 0 ? (
                      <Icon name="Eye" size={14} className="text-success" />
                    ) : (
                      <Icon name="EyeOff" size={14} className="text-muted-foreground" />
                    )}
                    {season?.available === season?.episodes ? (
                      <Icon name="CheckCircle2" size={14} className="text-success" />
                    ) : season?.available === 0 ? (
                      <Icon name="XCircle" size={14} className="text-error" />
                    ) : (
                      <Icon name="AlertCircle" size={14} className="text-warning" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* File Information */}
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
            <Icon name="Folder" size={16} className="text-primary" />
            File Information
          </h4>
          <div className="space-y-3">
            <div className="bg-card border border-border rounded-md p-3">
              <p className="text-xs text-muted-foreground mb-1">File Path</p>
              <p className="text-sm text-foreground font-mono break-all">{item?.filePath}</p>
            </div>
            {item?.fileSize && (
              <div className="bg-card border border-border rounded-md p-3">
                <p className="text-xs text-muted-foreground mb-1">File Size</p>
                <p className="text-sm text-foreground font-semibold">{item?.fileSize}</p>
              </div>
            )}
            {item?.downloadProgress !== undefined && (
              <div className="bg-card border border-border rounded-md p-3">
                <p className="text-xs text-muted-foreground mb-2">Download Progress</p>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all duration-300"
                      style={{ width: `${item?.downloadProgress}%` }}
                    />
                  </div>
                  <span className="text-sm font-semibold text-foreground">
                    {item?.downloadProgress}%
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Download History */}
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
            <Icon name="History" size={16} className="text-primary" />
            Download History
          </h4>
          <div className="space-y-2">
            {item?.downloadHistory?.length > 0 ? (
              item?.downloadHistory?.map((entry, index) => (
                <div key={index} className="bg-card border border-border rounded-md p-3">
                  <div className="flex items-start justify-between mb-1">
                    <p className="text-sm text-foreground font-medium">{entry?.action}</p>
                    <span className="text-xs px-2 py-0.5 rounded-md bg-accent/10 text-accent font-medium">
                      {entry?.quality}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">{entry?.date}</p>
                </div>
              ))
            ) : (
              <div className="bg-card border border-border rounded-md p-3 text-center">
                <Icon name="Inbox" size={24} className="mx-auto mb-2 text-muted-foreground" />
                <p className="text-xs text-muted-foreground">No download history</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExpandableRow;
