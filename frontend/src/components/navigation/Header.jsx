import React, { useState, useEffect, useRef } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import Icon from "../AppIcon";
import PilotarrLogo from "../PilotarrLogo";
import { useAuth } from "../../contexts/AuthContext";
import { getServiceConfigurations } from "../../services/configService";

const Header = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const auth = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [configProgress, setConfigProgress] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef(null);

  useEffect(() => {
    const checkConfigStatus = async () => {
      try {
        const configs = await getServiceConfigurations();
        const allOnline = configs?.length > 0 && configs.every((c) => c?.testStatus === "success");
        setConfigProgress(!allOnline);
      } catch {
        setConfigProgress(true);
      }
    };
    checkConfigStatus();
  }, [location.pathname]);

  useEffect(() => {
    const handler = (e) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
        setUserMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const navigationItems = [
    {
      label: "Dashboard",
      path: "/main-dashboard",
      icon: "LayoutDashboard",
      tooltip: "Unified monitoring hub",
    },
    {
      label: "Library",
      path: "/library",
      icon: "Library",
      tooltip: "Browse media collection",
    },
    {
      label: "Monitoring",
      path: "/monitoring",
      icon: "Monitor",
      tooltip: "Sonarr/Radarr media tracking",
    },
    {
      label: "Analytics",
      path: "/jellyfin-statistics",
      icon: "BarChart3",
      tooltip: "Detailed usage statistics",
    },
    {
      label: "Indexers",
      path: "/indexer",
      icon: "Rss",
      tooltip: "Prowlarr indexer management and search",
    },
    {
      label: "Torrents",
      path: "/torrents",
      icon: "Download",
      tooltip: "Torrent client management",
    },
    {
      label: "Calendar",
      path: "/calendar",
      icon: "Calendar",
      tooltip: "Media release schedule and activity",
    },
    {
      label: "Configuration",
      path: "/initial-configuration",
      icon: "Settings",
      tooltip: "API setup and service connections",
    },
  ];

  const isActive = (path) => location?.pathname === path;

  const toggleMobileMenu = () => setIsMobileMenuOpen((prev) => !prev);
  const closeMobileMenu = () => setIsMobileMenuOpen(false);

  const handleLogout = () => {
    setUserMenuOpen(false);
    closeMobileMenu();
    auth.logout();
    navigate("/login");
  };

  const handleChangePassword = () => {
    setUserMenuOpen(false);
    closeMobileMenu();
    navigate("/change-password");
  };

  useEffect(() => {
    document.body.style.overflow = isMobileMenuOpen ? "hidden" : "unset";
    return () => {
      document.body.style.overflow = "unset";
    };
  }, [isMobileMenuOpen]);

  return (
    <>
      <header className="nav-header">
        <div className="nav-header-container">
          <div className="nav-header-logo">
            <div className="nav-header-logo-icon">
              <PilotarrLogo size={32} />
            </div>
            <span className="nav-header-logo-text">Pilotarr</span>
          </div>

          <nav className="nav-header-menu">
            {navigationItems?.map((item) => (
              <Link
                key={item?.path}
                to={item?.path}
                className={`nav-header-item ${isActive(item?.path) ? "active" : ""}`}
                title={item?.tooltip}
              >
                <Icon name={item?.icon} size={18} className="mr-2" />
                {item?.label}
                {item?.path === "/initial-configuration" && configProgress && (
                  <span className="progress-badge">!</span>
                )}
              </Link>
            ))}
          </nav>

          {/* User pill + dropdown (desktop) */}
          {auth.user && (
            <div className="relative hidden lg:block" ref={userMenuRef}>
              <button
                onClick={() => setUserMenuOpen((v) => !v)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted hover:bg-muted/80 transition-colors text-sm font-medium"
                aria-expanded={userMenuOpen}
                aria-haspopup="true"
              >
                <Icon name="User" size={16} />
                <span>{auth.user.username}</span>
                <Icon name={userMenuOpen ? "ChevronUp" : "ChevronDown"} size={14} />
              </button>

              {userMenuOpen && (
                <div className="absolute right-0 top-full mt-2 w-48 bg-card border border-border rounded-xl shadow-lg py-1 z-50">
                  <div className="px-4 py-2 text-sm font-medium text-foreground border-b border-border">
                    {auth.user.username}
                  </div>
                  <button
                    onClick={handleChangePassword}
                    className="w-full flex items-center gap-2 px-4 py-2 text-sm text-foreground hover:bg-muted transition-colors"
                  >
                    <Icon name="KeyRound" size={15} />
                    Change password
                  </button>
                  <div className="border-t border-border my-1" />
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2 px-4 py-2 text-sm text-foreground hover:bg-muted transition-colors"
                  >
                    <Icon name="LogOut" size={15} />
                    Sign out
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Mobile hamburger — hidden on lg+ */}
          <button
            className="lg:hidden flex items-center justify-center w-10 h-10 rounded-lg hover:bg-muted transition-colors"
            onClick={toggleMobileMenu}
            aria-label="Toggle mobile menu"
            aria-expanded={isMobileMenuOpen}
          >
            <Icon name={isMobileMenuOpen ? "X" : "Menu"} size={22} />
          </button>
        </div>
      </header>

      {/* Mobile overlay menu */}
      <div className={`nav-mobile-menu ${!isMobileMenuOpen ? "closed" : ""}`}>
        <div className="nav-mobile-menu-header">
          <div className="nav-header-logo">
            <div className="nav-header-logo-icon">
              <PilotarrLogo size={32} />
            </div>
            <span className="nav-header-logo-text">Pilotarr</span>
          </div>
        </div>

        <nav className="nav-mobile-menu-items">
          {navigationItems?.map((item) => (
            <Link
              key={item?.path}
              to={item?.path}
              className={`nav-mobile-menu-item ${isActive(item?.path) ? "active" : ""}`}
              onClick={closeMobileMenu}
            >
              <Icon name={item?.icon} size={20} className="mr-3" />
              {item?.label}
              {item?.path === "/initial-configuration" && configProgress && (
                <span className="progress-badge">!</span>
              )}
            </Link>
          ))}

          {auth.user && (
            <>
              <div className="border-t border-border my-2" />
              <button
                onClick={handleChangePassword}
                className="nav-mobile-menu-item w-full text-left"
              >
                <Icon name="KeyRound" size={20} className="mr-3" />
                Change password
              </button>
              <button onClick={handleLogout} className="nav-mobile-menu-item w-full text-left">
                <Icon name="LogOut" size={20} className="mr-3" />
                Sign out
              </button>
            </>
          )}
        </nav>
      </div>
    </>
  );
};

export default Header;
