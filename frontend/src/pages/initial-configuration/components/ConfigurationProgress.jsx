import React from "react";
import Icon from "../../../components/AppIcon";

const ConfigurationProgress = ({ services, testStatuses, configurations }) => {
  // Determine the state of each service based on database data
  const getServiceState = (serviceId) => {
    const config = configurations?.[serviceId];
    const testStatus = testStatuses?.[serviceId];

    // Empty: No URL configured, or no credential (apiKey for API services, username for qBittorrent)
    const isQBittorrent = serviceId === "qbittorrent";
    const hasCredential = isQBittorrent
      ? config?.username && (config?.password || config?.hasPassword)
      : config?.apiKey || config?.hasApiKey;
    if (!config?.url || !hasCredential) {
      return "empty";
    }

    // Configured but not tested: Has config but no test status
    if (!testStatus || testStatus?.status === null || testStatus?.status === undefined) {
      return "configured";
    }

    // Test and error: Test was performed and failed
    if (testStatus?.status === "error") {
      return "error";
    }

    // Alive: Test was successful
    if (testStatus?.status === "success") {
      return "alive";
    }

    // Testing in progress
    if (testStatus?.status === "testing") {
      return "testing";
    }

    return "empty";
  };

  // Get state configuration for display
  const getStateConfig = (state) => {
    const configs = {
      empty: {
        label: "Not configured",
        icon: "Circle",
        iconColor: "var(--color-muted-foreground)",
        bgClass: "bg-muted/30",
        borderClass: "border-border",
        textClass: "text-muted-foreground",
      },
      configured: {
        label: "Configured (not tested)",
        icon: "AlertCircle",
        iconColor: "var(--color-warning)",
        bgClass: "bg-warning/10",
        borderClass: "border-warning/20",
        textClass: "text-warning",
      },
      error: {
        label: "Test failed",
        icon: "XCircle",
        iconColor: "var(--color-destructive)",
        bgClass: "bg-destructive/10",
        borderClass: "border-destructive/20",
        textClass: "text-destructive",
      },
      alive: {
        label: "Connected",
        icon: "CheckCircle2",
        iconColor: "var(--color-success)",
        bgClass: "bg-success/10",
        borderClass: "border-success/20",
        textClass: "text-success",
      },
      testing: {
        label: "Testing...",
        icon: "Loader2",
        iconColor: "var(--color-primary)",
        bgClass: "bg-primary/10",
        borderClass: "border-primary/20",
        textClass: "text-primary",
      },
    };
    return configs?.[state] || configs?.empty;
  };

  // Calculate progress based on alive services
  const getCompletedCount = () => {
    return services?.filter((service) => getServiceState(service?.id) === "alive")?.length || 0;
  };

  const totalServices = services?.length || 0;
  const completedServices = getCompletedCount();
  const progressPercentage = totalServices > 0 ? (completedServices / totalServices) * 100 : 0;

  // Count services by state for summary
  const stateCounts = services?.reduce((acc, service) => {
    const state = getServiceState(service?.id);
    acc[state] = (acc?.[state] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="bg-card border border-border rounded-lg p-4 md:p-6 shadow-elevation-2">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-accent/10">
            <Icon name="Settings" size={20} color="var(--color-accent)" />
          </div>
          <div>
            <h3 className="text-base md:text-lg font-semibold text-foreground">
              Configuration Progress
            </h3>
            <p className="text-xs md:text-sm text-muted-foreground">
              {completedServices} of {totalServices} services connected
            </p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-xl md:text-2xl font-bold text-foreground">
            {Math.round(progressPercentage)}%
          </div>
          <div className="text-xs text-muted-foreground">Complete</div>
        </div>
      </div>
      <div className="w-full bg-muted rounded-full h-2 md:h-3 overflow-hidden mb-4">
        <div
          className="h-full bg-gradient-to-r from-primary to-accent transition-all duration-500 ease-out"
          style={{ width: `${progressPercentage}%` }}
        />
      </div>
      {/* State summary */}
      {(stateCounts?.configured > 0 || stateCounts?.error > 0) && (
        <div className="mb-4 p-3 bg-muted/30 border border-border rounded-lg">
          <div className="flex flex-wrap gap-3 text-xs">
            {stateCounts?.configured > 0 && (
              <div className="flex items-center gap-1.5">
                <Icon name="AlertCircle" size={14} color="var(--color-warning)" />
                <span className="text-muted-foreground">
                  {stateCounts?.configured} configured (not tested)
                </span>
              </div>
            )}
            {stateCounts?.error > 0 && (
              <div className="flex items-center gap-1.5">
                <Icon name="XCircle" size={14} color="var(--color-destructive)" />
                <span className="text-muted-foreground">{stateCounts?.error} test failed</span>
              </div>
            )}
          </div>
        </div>
      )}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
        {services?.map((service) => {
          const state = getServiceState(service?.id);
          const stateConfig = getStateConfig(state);

          return (
            <div
              key={service?.id}
              className={`p-3 rounded-lg border transition-all ${stateConfig?.bgClass} ${
                stateConfig?.borderClass
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                <Icon
                  name={stateConfig?.icon}
                  size={16}
                  color={stateConfig?.iconColor}
                  className={state === "testing" ? "animate-spin" : ""}
                />
                <span className="text-xs md:text-sm font-medium text-foreground">
                  {service?.name}
                </span>
              </div>
              <p className={`text-xs ${stateConfig?.textClass}`}>{stateConfig?.label}</p>
            </div>
          );
        })}
      </div>
      {completedServices === totalServices && totalServices > 0 && (
        <div className="mt-4 p-3 bg-success/10 border border-success/20 rounded-lg">
          <div className="flex items-center gap-2 text-success">
            <Icon name="CheckCircle2" size={18} />
            <p className="text-sm font-medium">
              All services configured and connected successfully!
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ConfigurationProgress;
