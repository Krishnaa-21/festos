import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { Button } from "../../components/ui/Button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../../components/ui/Card";
import { Lock, Mail, Shield, AlertCircle } from "lucide-react";

const DEMO_ACCOUNTS = [
  { role: "Director", email: "director@festos.internal", pass: "FestOSDirector2026!", label: "Festival Director" },
  { role: "Accom", email: "accommodation@festos.internal", pass: "FestOSAccommodation2026!", label: "Accommodation Lead" },
  { role: "Events", email: "events@festos.internal", pass: "FestOSEvents2026!", label: "Event Lead" },
  { role: "Logistics", email: "logistics@festos.internal", pass: "FestOSLogistics2026!", label: "Logistics Mgr" },
  { role: "Merch", email: "merch@festos.internal", pass: "FestOSMerch2026!", label: "Merchandise Mgr" },
  { role: "Food", email: "food@festos.internal", pass: "FestOSFood2026!", label: "Food Ops Mgr" },
  { role: "Finance", email: "finance@festos.internal", pass: "FestOSFinance2026!", label: "Finance Mgr" },
  { role: "Volunteer", email: "volunteer@festos.internal", pass: "FestOSVolunteer2026!", label: "Volunteer" },
  { role: "Auditor", email: "auditor@festos.internal", pass: "FestOSAuditor2026!", label: "Compliance Auditor" },
];

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as any)?.from?.pathname || "/dashboard";

  const [email, setEmail] = useState("director@festos.internal");
  const [password, setPassword] = useState("FestOSDirector2026!");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err?.message || "Invalid credentials or account locked");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDemoAccount = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setError(null);
  };

  return (
    <div className="flex min-h-screen w-screen items-center justify-center bg-[#070B14] p-4 text-slate-100">
      <div className="w-full max-w-md space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 font-extrabold text-white text-xl shadow-lg shadow-indigo-500/30">
            FO
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">FestOS Operations Centre</h1>
          <p className="text-xs text-slate-400">
            Aarohan Fest 2026 (EPINOIA, IIM Indore) — Unified Operations & RBAC Access
          </p>
        </div>

        {/* Login Card */}
        <Card className="border-slate-800 bg-[#0E1526]/95 shadow-2xl backdrop-blur-md">
          <CardHeader>
            <CardTitle className="text-base text-white">Sign in to Command Centre</CardTitle>
            <CardDescription>Enter your credentials to unlock authorized festival views.</CardDescription>
          </CardHeader>

          <CardContent className="space-y-4 pt-2">
            {error && (
              <div
                className="flex items-center space-x-2 rounded-lg border border-red-500/40 bg-red-950/40 p-3 text-xs text-red-300"
                data-testid="login-error"
              >
                <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    placeholder="name@festos.internal"
                    data-testid="login-email"
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 py-2 pl-9 pr-3 text-xs text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    placeholder="••••••••••••"
                    data-testid="login-password"
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 py-2 pl-9 pr-3 text-xs text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <Button
                type="submit"
                variant="primary"
                size="md"
                isLoading={loading}
                className="w-full mt-2"
                data-testid="login-submit"
              >
                Sign In
              </Button>
            </form>

            {/* Quick Demo Switcher */}
            <div className="pt-4 border-t border-slate-800">
              <div className="flex items-center space-x-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                <Shield className="h-3 w-3 text-indigo-400" />
                <span>Quick Role Demo Switcher</span>
              </div>
              <div className="grid grid-cols-3 gap-1.5">
                {DEMO_ACCOUNTS.map((acc) => (
                  <button
                    key={acc.role}
                    type="button"
                    onClick={() => handleSelectDemoAccount(acc.email, acc.pass)}
                    className="truncate rounded border border-slate-800 bg-slate-900/80 px-2 py-1 text-[10px] text-slate-300 hover:border-indigo-500 hover:text-white hover:bg-indigo-950/30 transition-all text-center"
                    title={`Click to fill: ${acc.label} (${acc.email})`}
                  >
                    {acc.role}
                  </button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
