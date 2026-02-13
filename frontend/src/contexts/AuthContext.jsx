import React, { createContext, useContext, useState } from "react";

const AuthContext = createContext({});

export const useAuth = () => {
  return useContext(AuthContext);
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [profileLoading, setProfileLoading] = useState(false);

  // Auth methods - now handled by backend
  // TODO: Implement backend authentication if needed
  const signIn = async (_email, _password) => {
    return { data: null, error: { message: "Authentication not configured" } };
  };

  const signOut = async () => {
    setUser(null);
    setUserProfile(null);
    return { error: null };
  };

  // TODO: Implement backend profile update if needed
  const updateProfile = async (_updates) => {
    if (!user) return { error: { message: "No user logged in" } };
    return { data: null, error: { message: "Profile update not configured" } };
  };

  const value = {
    user,
    userProfile,
    loading,
    profileLoading,
    signIn,
    signOut,
    updateProfile,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
