import React from "react";
import { BrowserRouter, Routes as RouterRoutes, Route, Navigate } from "react-router-dom";
import ScrollToTop from "components/ScrollToTop";
import ErrorBoundary from "components/ErrorBoundary";
import NotFound from "pages/NotFound";
import MainDashboard from "./pages/main-dashboard";
import JellyfinStatistics from "./pages/jellyfin-statistics";
import InitialConfiguration from "./pages/initial-configuration";
import Library from "./pages/library";
import Monitoring from "./pages/monitoring";
import MediaDetail from "./pages/media-detail";
import JellyseerrRequests from "./pages/jellyseerr-requests";
import Calendar from "./pages/calendar";
import Torrents from "./pages/torrents";
import Login from "./pages/login";
import ChangePassword from "./pages/change-password";
import { AuthProvider, useAuth } from "./contexts/AuthContext";

const ProtectedRoute = ({ children }) => {
  const { user, initializing } = useAuth();
  if (initializing) return null;
  return user ? children : <Navigate to="/login" replace />;
};

const Routes = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ErrorBoundary>
          <ScrollToTop />
          <RouterRoutes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <InitialConfiguration />
                </ProtectedRoute>
              }
            />
            <Route
              path="/main-dashboard"
              element={
                <ProtectedRoute>
                  <MainDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/jellyfin-statistics"
              element={
                <ProtectedRoute>
                  <JellyfinStatistics />
                </ProtectedRoute>
              }
            />
            <Route
              path="/initial-configuration"
              element={
                <ProtectedRoute>
                  <InitialConfiguration />
                </ProtectedRoute>
              }
            />
            <Route
              path="/library"
              element={
                <ProtectedRoute>
                  <Library />
                </ProtectedRoute>
              }
            />
            <Route
              path="/library/:id"
              element={
                <ProtectedRoute>
                  <MediaDetail />
                </ProtectedRoute>
              }
            />
            <Route
              path="/monitoring"
              element={
                <ProtectedRoute>
                  <Monitoring />
                </ProtectedRoute>
              }
            />
            <Route
              path="/jellyseerr-requests"
              element={
                <ProtectedRoute>
                  <JellyseerrRequests />
                </ProtectedRoute>
              }
            />
            <Route
              path="/calendar"
              element={
                <ProtectedRoute>
                  <Calendar />
                </ProtectedRoute>
              }
            />
            <Route
              path="/torrents"
              element={
                <ProtectedRoute>
                  <Torrents />
                </ProtectedRoute>
              }
            />
            <Route
              path="/change-password"
              element={
                <ProtectedRoute>
                  <ChangePassword />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<NotFound />} />
          </RouterRoutes>
        </ErrorBoundary>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default Routes;
