import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import Header from "../../components/navigation/Header";
import Input from "../../components/ui/Input";
import Button from "../../components/ui/Button";
import Icon from "../../components/AppIcon";

const ChangePassword = () => {
  const auth = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (newPassword.length < 8) {
      setError("New password must be at least 8 characters");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("New passwords do not match");
      return;
    }

    setLoading(true);
    const result = await auth.changePassword(currentPassword, newPassword, confirmPassword);
    setLoading(false);

    if (result.ok) {
      setSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } else {
      setError(result.error);
    }
  };

  return (
    <div className="bg-background min-h-screen">
      <Header />
      <div className="flex items-start justify-center p-6 pt-10">
        <div className="w-full max-w-md">
          <Link
            to="/main-dashboard"
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors mb-6"
          >
            <Icon name="ArrowLeft" size={16} />
            Back to dashboard
          </Link>

          <div className="bg-card border border-border rounded-xl shadow-lg p-8">
            <h1 className="text-xl font-bold text-foreground mb-6">Change Password</h1>

            {error && (
              <div className="mb-4 px-4 py-3 bg-error/10 border border-error/30 text-error rounded-lg text-sm">
                {error}
              </div>
            )}

            {success && (
              <div className="mb-4 px-4 py-3 bg-success/10 border border-success/30 text-success rounded-lg text-sm flex flex-col gap-2">
                <span>Password changed successfully.</span>
                <Link
                  to="/main-dashboard"
                  className="underline underline-offset-2 hover:opacity-80"
                >
                  Back to dashboard
                </Link>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <Input
                label="Current password"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
              <Input
                label="New password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                autoComplete="new-password"
                description="Minimum 8 characters"
              />
              <Input
                label="Confirm new password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
              />

              <Button type="submit" fullWidth loading={loading} className="mt-2">
                Save changes
              </Button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChangePassword;
