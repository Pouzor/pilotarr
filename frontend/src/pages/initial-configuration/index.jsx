import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../../components/navigation/Header";
import Icon from "../../components/AppIcon";
import Button from "../../components/ui/Button";
import ServiceCard from "./components/ServiceCard";
import ConfigurationProgress from "./components/ConfigurationProgress";
import SecurityInfo from "./components/SecurityInfo";
import QuickStartGuide from "./components/QuickStartGuide";
import {
  getServiceConfigurations,
  saveServiceConfiguration,
  testServiceConnection,
} from "../../services/configService";

const InitialConfiguration = () => {
  const navigate = useNavigate();
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const services = [
    {
      id: "radarr",
      name: "Radarr",
      icon: "Film",
      description: "Movie collection manager",
      url: "",
      apiKey: "",
      port: "7878",
    },
    {
      id: "sonarr",
      name: "Sonarr",
      icon: "Tv",
      description: "TV series collection manager",
      url: "",
      apiKey: "",
      port: "8989",
    },
    {
      id: "jellyfin",
      name: "Jellyfin",
      icon: "Play",
      description: "Media server platform",
      url: "",
      apiKey: "",
      port: "8096",
    },
    {
      id: "jellyseerr",
      name: "Jellyseerr",
      icon: "Users",
      description: "Media request management",
      url: "",
      apiKey: "",
      port: "5055",
    },
    {
      id: "qbittorrent",
      name: "qBittorrent",
      icon: "Download",
      description: "Torrent client",
      url: "",
      username: "",
      password: "",
      port: "8080",
    },
  ];

  const [configurations, setConfigurations] = useState(
    services?.reduce(
      (acc, service) => ({
        ...acc,
        [service?.id]: {
          url: "",
          apiKey: service?.apiKey !== undefined ? "" : undefined,
          username: service?.username !== undefined ? "" : undefined,
          password: service?.password !== undefined ? "" : undefined,
          port: service?.port,
        },
      }),
      {},
    ),
  );

  const [testStatuses, setTestStatuses] = useState({});

  // Load existing configurations from database
  useEffect(() => {
    const loadConfigurations = async () => {
      try {
        setIsLoading(true);
        const savedConfigs = await getServiceConfigurations();

        if (savedConfigs && savedConfigs?.length > 0) {
          const configMap = {};
          const statusMap = {};

          savedConfigs?.forEach((config) => {
            configMap[config.serviceName] = {
              url: config?.url,
              apiKey: config?.apiKey,
              username: config?.username,
              password: config?.password,
              port: config?.port?.toString() || "",
            };

            if (config?.testStatus) {
              statusMap[config.serviceName] = {
                status: config?.testStatus,
                message: config?.testMessage || "",
              };
            }
          });

          setConfigurations((prev) => ({ ...prev, ...configMap }));
          setTestStatuses(statusMap);
        }
      } catch (error) {
        console.error("Error loading configurations:", error);
      } finally {
        setIsLoading(false);
      }
    };

    loadConfigurations();
  }, []);

  const handleConfigChange = (serviceId, config) => {
    setConfigurations((prev) => ({
      ...prev,
      [serviceId]: config,
    }));
    setTestStatuses((prev) => ({
      ...prev,
      [serviceId]: null,
    }));
  };

  const handleTestConnection = async (serviceId, config) => {
    setTestStatuses((prev) => ({
      ...prev,
      [serviceId]: { status: "testing", message: "Testing connection..." },
    }));

    // Check if service uses username/password or API key
    const usesApiKey = config?.apiKey !== undefined;
    const usesCredentials =
      config?.username !== undefined && config?.password !== undefined;

    let isValid;
    if (usesApiKey) {
      isValid = config?.url && config?.apiKey;
    } else if (usesCredentials) {
      isValid = config?.url && config?.username && config?.password;
    } else {
      isValid = config?.url;
    }

    const hasValidUrl =
      config?.url?.startsWith("http://") || config?.url?.startsWith("https://");

    if (!isValid) {
      const errorStatus = {
        status: "error",
        message: "Invalid configuration",
        details: usesApiKey
          ? "Please provide both URL and API key"
          : usesCredentials
            ? "Please provide URL, username, and password"
            : "Please provide a valid URL",
      };
      setTestStatuses((prev) => ({
        ...prev,
        [serviceId]: errorStatus,
      }));
      return;
    }

    if (!hasValidUrl) {
      const errorStatus = {
        status: "error",
        message: "Invalid URL format",
        details: "URL must start with http:// or https://",
      };
      setTestStatuses((prev) => ({
        ...prev,
        [serviceId]: errorStatus,
      }));
      return;
    }

    // Test connection using backend API
    try {
      const result = await testServiceConnection(serviceId);

      if (result?.success) {
        const successStatus = {
          status: "success",
          message: result?.message || "Connection successful",
          details: `Tested at ${new Date(result?.testedAt)?.toLocaleString()}`,
        };

        setTestStatuses((prev) => ({
          ...prev,
          [serviceId]: successStatus,
        }));
      } else {
        const errorStatus = {
          status: "error",
          message: "Connection failed",
          details: result?.message || "Unable to connect to service",
        };

        setTestStatuses((prev) => ({
          ...prev,
          [serviceId]: errorStatus,
        }));
      }
    } catch (error) {
      console.error(`${serviceId} connection test failed:`, error);

      let errorMessage = "Connection failed";
      let errorDetails =
        error?.message || "Unable to reach server. Check URL and API key.";

      // Provide more specific error messages based on response
      if (error?.response?.data?.detail) {
        errorDetails = error?.response?.data?.detail;
      } else if (
        error?.response?.status === 401 ||
        error?.response?.status === 403
      ) {
        errorDetails = "Authentication failed: Invalid API key for backend.";
      } else if (error?.response?.status === 404) {
        errorDetails =
          "Service not found: Please save the configuration first.";
      } else if (error?.code === "ERR_NETWORK") {
        errorDetails = "Network error: Cannot reach the backend server.";
      }

      const errorStatus = {
        status: "error",
        message: errorMessage,
        details: errorDetails,
      };

      setTestStatuses((prev) => ({
        ...prev,
        [serviceId]: errorStatus,
      }));
    }
  };

  const handleSaveAll = async () => {
    setIsSaving(true);

    try {
      // Save all configurations to database
      await Promise.all(
        services?.map((service) => {
          const config = configurations?.[service?.id];
          return saveServiceConfiguration(service?.id, {
            url: config?.url,
            apiKey: config?.apiKey,
            username: config?.username,
            password: config?.password,
            port: config?.port,
            isActive: true,
          });
        }),
      );

      setSaveSuccess(true);

      setTimeout(() => {
        navigate("/main-dashboard");
      }, 1500);
    } catch (error) {
      console.error("Error saving configurations:", error);
      alert("Failed to save configurations. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  const allServicesConfigured = services?.every(
    (service) => testStatuses?.[service?.id]?.status === "success",
  );

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <main className="pt-20 md:pt-24 pb-8 md:pb-12">
          <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8">
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <Icon
                  name="Loader2"
                  size={48}
                  className="animate-spin text-primary mx-auto mb-4"
                />
                <p className="text-muted-foreground">
                  Loading configurations...
                </p>
              </div>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="pt-20 md:pt-24 pb-8 md:pb-12">
        <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8">
          <div className="mb-6 md:mb-8">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 md:w-14 md:h-14 rounded-lg flex items-center justify-center bg-primary/10">
                <Icon
                  name="Settings"
                  size={24}
                  color="var(--color-primary)"
                  className="md:w-7 md:h-7"
                />
              </div>
              <div>
                <h1 className="text-2xl md:text-3xl lg:text-4xl font-bold text-foreground">
                  Initial Configuration
                </h1>
                <p className="text-sm md:text-base text-muted-foreground mt-1">
                  Configure API connections to your Servarr services
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6 mb-6 md:mb-8">
            <div className="lg:col-span-3">
              <ConfigurationProgress
                services={services}
                testStatuses={testStatuses}
                configurations={configurations}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
            {services?.map((service) => (
              <ServiceCard
                key={service?.id}
                service={{
                  ...service,
                  url: configurations?.[service?.id]?.url || "",
                  apiKey: configurations?.[service?.id]?.apiKey || "",
                  port: configurations?.[service?.id]?.port || service?.port,
                }}
                onTest={handleTestConnection}
                onConfigChange={handleConfigChange}
                testStatus={testStatuses?.[service?.id]}
              />
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 mb-6 md:mb-8">
            <SecurityInfo />
            <QuickStartGuide />
          </div>

          <div className="bg-card border border-border rounded-lg p-4 md:p-6 shadow-elevation-2">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <Icon
                  name="Save"
                  size={24}
                  color="var(--color-primary)"
                  className="flex-shrink-0 mt-1"
                />
                <div>
                  <h3 className="text-base md:text-lg font-semibold text-foreground mb-1">
                    Ready to Save Configuration
                  </h3>
                  <p className="text-xs md:text-sm text-muted-foreground">
                    {allServicesConfigured
                      ? "All services are configured and ready. Click save to proceed to the dashboard."
                      : "Test all service connections before saving your configuration."}
                  </p>
                </div>
              </div>
              <Button
                variant="default"
                size="lg"
                onClick={handleSaveAll}
                disabled={isSaving}
                loading={isSaving}
                iconName={saveSuccess ? "Check" : "Save"}
                iconPosition="left"
                className="w-full md:w-auto min-w-[200px]"
              >
                {saveSuccess
                  ? "Configuration Saved!"
                  : "Save All Configurations"}
              </Button>
            </div>

            {saveSuccess && (
              <div className="mt-4 p-3 bg-success/10 border border-success/20 rounded-lg">
                <div className="flex items-center gap-2 text-success">
                  <Icon name="CheckCircle2" size={18} />
                  <p className="text-sm font-medium">
                    Configuration saved successfully! Redirecting to
                    dashboard...
                  </p>
                </div>
              </div>
            )}
          </div>

          <div className="mt-6 md:mt-8 p-4 md:p-6 bg-muted/30 border border-border rounded-lg">
            <div className="flex items-start gap-3">
              <Icon
                name="HelpCircle"
                size={20}
                color="var(--color-accent)"
                className="flex-shrink-0 mt-0.5"
              />
              <div className="flex-1 min-w-0">
                <h4 className="text-sm md:text-base font-semibold text-foreground mb-2">
                  Need Help?
                </h4>
                <p className="text-xs md:text-sm text-muted-foreground mb-3">
                  If you&apos;re having trouble connecting to your services,
                  check the following:
                </p>
                <ul className="space-y-1.5 text-xs md:text-sm text-muted-foreground">
                  <li className="flex items-start gap-2">
                    <Icon
                      name="Check"
                      size={14}
                      className="text-primary flex-shrink-0 mt-0.5"
                    />
                    <span>
                      Verify services are running and accessible on your network
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Icon
                      name="Check"
                      size={14}
                      className="text-primary flex-shrink-0 mt-0.5"
                    />
                    <span>
                      Ensure API keys are copied correctly without extra spaces
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Icon
                      name="Check"
                      size={14}
                      className="text-primary flex-shrink-0 mt-0.5"
                    />
                    <span>
                      Check firewall settings allow connections to service ports
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Icon
                      name="Check"
                      size={14}
                      className="text-primary flex-shrink-0 mt-0.5"
                    />
                    <span>
                      Confirm URLs include the correct protocol (http:// or
                      https://)
                    </span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default InitialConfiguration;
