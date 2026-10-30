import React, { useState } from "react";
import { Modal } from "./Modal";
import { Button } from "./Button";
import { AlertTriangle } from "lucide-react";

export interface ConfirmWithReasonProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (reason: string) => void | Promise<void>;
  title?: string;
  description?: string;
  confirmText?: string;
  cancelText?: string;
  placeholder?: string;
  isLoading?: boolean;
  riskLevel?: "LOW" | "HIGH" | "CRITICAL";
  children?: React.ReactNode;
}

export const ConfirmWithReason: React.FC<ConfirmWithReasonProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title = "Authorize Operational Override",
  description = "FestOS principles require an explicit, auditable justification for every operational override and constraint relaxation.",
  confirmText = "Confirm & Record",
  cancelText = "Cancel",
  placeholder = "Specify operational rationale, contingent context, or authorized bypass code...",
  isLoading = false,
  riskLevel = "HIGH",
  children,
}) => {
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason || !reason.trim()) {
      setError("An explicit operational reason is strictly required under FestOS policy.");
      return;
    }
    setError(null);
    await onConfirm(reason.trim());
    setReason("");
  };

  const handleClose = () => {
    setReason("");
    setError(null);
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={
        <div className="flex items-center space-x-2 text-amber-400">
          <AlertTriangle className="h-5 w-5 shrink-0" />
          <span>{title}</span>
        </div>
      }
      description={description}
      size="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {riskLevel === "CRITICAL" && (
          <div className="rounded-lg border border-red-500/40 bg-red-950/30 p-3 text-xs text-red-300">
            <strong>CRITICAL RISK:</strong> This action relaxes a protected constraint and will immediately be dispatched to the Festival Director and permanent audit ledger.
          </div>
        )}

        {children}

        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
            Operational Reason <span className="text-red-400">*</span>
          </label>
          <textarea
            rows={3}
            value={reason}
            onChange={(e) => {
              setReason(e.target.value);
              if (error) setError(null);
            }}
            placeholder={placeholder}
            data-testid="reason-input"
            className="w-full rounded-lg border border-slate-700 bg-slate-950 p-3 text-xs text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
          {error && (
            <p className="mt-1 text-xs text-red-400 font-medium" data-testid="reason-error">
              {error}
            </p>
          )}
        </div>

        <div className="flex items-center justify-end space-x-3 pt-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleClose}
            disabled={isLoading}
          >
            {cancelText}
          </Button>
          <Button
            type="submit"
            variant={riskLevel === "CRITICAL" ? "danger" : "primary"}
            size="sm"
            isLoading={isLoading}
            disabled={!reason.trim()}
            data-testid="confirm-button"
          >
            {confirmText}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
