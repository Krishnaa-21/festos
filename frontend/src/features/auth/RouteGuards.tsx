import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { ShieldAlert } from "lucide-react";
import { Button } from "../../components/ui/Button";

interface RequireAuthProps {
  children: React.ReactNode;
}

export const RequireAuth: React.FC<RequireAuthProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[#070B14] text-white">
        <div className="flex flex-col items-center space-y-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent" />
          <span className="text-xs text-slate-400 font-mono">Authenticating FestOS Session...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

interface RequirePermissionProps {
  permission: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export const RequirePermission: React.FC<RequirePermissionProps> = ({
  permission,
  children,
  fallback,
}) => {
  const { hasPermission, user } = useAuth();

  if (!hasPermission(permission)) {
    if (fallback) return <>{fallback}</>;

    return (
      <div
        className="flex min-h-[400px] flex-col items-center justify-center rounded-xl border border-rose-500/30 bg-rose-950/15 p-8 text-center"
        data-testid="permission-denied"
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-rose-900/40 text-rose-400 mb-4">
          <ShieldAlert className="h-6 w-6" />
        </div>
        <h2 className="text-base font-bold text-white">Access Restricted</h2>
        <p className="mt-1 text-xs text-rose-300/80 max-w-md">
          Role <strong className="text-white">{user?.role || "GUEST"}</strong> lacks the required permission:{" "}
          <code className="rounded bg-rose-950 px-1.5 py-0.5 text-rose-300 font-mono">{permission}</code>
        </p>
        <div className="mt-5">
          <Button variant="secondary" size="sm" onClick={() => window.history.back()}>
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};
