import React, { createContext, useContext, useState, useCallback } from "react";
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from "lucide-react";
import { cn } from "../../lib/utils";

export type ToastType = "success" | "warning" | "error" | "info";

export interface ToastMessage {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
}

interface ToastContextType {
  addToast: (toast: Omit<ToastMessage, "id">) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    ({ type, title, message }: Omit<ToastMessage, "id">) => {
      const id = `toast_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
      setToasts((prev) => [...prev, { id, type, title, message }]);
      setTimeout(() => removeToast(id), 5000);
    },
    [removeToast]
  );

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col space-y-2 max-w-sm w-full pointer-events-none">
        {toasts.map((toast) => {
          const config = {
            success: {
              border: "border-emerald-500/40 bg-emerald-950/90 text-emerald-100",
              icon: <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />,
            },
            warning: {
              border: "border-amber-500/40 bg-amber-950/90 text-amber-100",
              icon: <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />,
            },
            error: {
              border: "border-rose-500/40 bg-rose-950/90 text-rose-100",
              icon: <AlertCircle className="h-4 w-4 text-rose-400 shrink-0" />,
            },
            info: {
              border: "border-indigo-500/40 bg-indigo-950/90 text-indigo-100",
              icon: <Info className="h-4 w-4 text-indigo-400 shrink-0" />,
            },
          }[toast.type];

          return (
            <div
              key={toast.id}
              className={cn(
                "pointer-events-auto flex items-start justify-between rounded-xl border p-3.5 shadow-xl backdrop-blur transition-all",
                config.border
              )}
            >
              <div className="flex items-start space-x-2.5">
                {config.icon}
                <div>
                  <div className="text-xs font-bold">{toast.title}</div>
                  {toast.message && <div className="text-[11px] opacity-85 mt-0.5">{toast.message}</div>}
                </div>
              </div>
              <button
                onClick={() => removeToast(toast.id)}
                className="text-slate-400 hover:text-white p-0.5 ml-2"
                title="Dismiss toast"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
};
