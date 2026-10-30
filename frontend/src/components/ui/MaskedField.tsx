import React, { useState } from "react";
import { Lock, Unlock, ShieldAlert } from "lucide-react";
import { Modal } from "./Modal";
import { Button } from "./Button";
import { cn } from "../../lib/utils";

export interface MaskedFieldProps {
  value: string;
  entity: string;
  field: string;
  isMasked?: boolean;
  onBreakGlass?: (entity: string, field: string, reason: string) => Promise<void>;
  className?: string;
}

export const MaskedField: React.FC<MaskedFieldProps> = ({
  value,
  entity,
  field,
  isMasked,
  onBreakGlass,
  className,
}) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Auto-detect masked patterns if isMasked not explicitly set
  const appearsMasked =
    isMasked !== undefined
      ? isMasked
      : value.includes("PROTECTED") ||
        value.includes("XXXXX") ||
        value.includes("***");

  if (!appearsMasked) {
    return <span className={cn("font-medium", className)}>{value}</span>;
  }

  const handleBreakGlassSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason || !reason.trim()) {
      setError("An explicit reason is mandatory for emergency break-glass unmasking.");
      return;
    }
    if (!onBreakGlass) return;

    try {
      setLoading(true);
      setError(null);
      await onBreakGlass(entity, field, reason.trim());
      setDialogOpen(false);
      setReason("");
    } catch (err: any) {
      setError(err?.message || "Failed to grant break-glass access");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setDialogOpen(true)}
        className={cn(
          "group inline-flex items-center space-x-1.5 rounded bg-slate-900/80 px-2 py-0.5 text-xs text-slate-400 hover:bg-amber-950/40 hover:text-amber-300 border border-slate-800 hover:border-amber-500/40 transition-all cursor-pointer",
          className
        )}
        data-testid="break-glass-trigger"
        title="Protected Field — Click to request Break-Glass unmasking"
      >
        <Lock className="h-3 w-3 text-amber-500/80 group-hover:text-amber-400 shrink-0" />
        <span className="font-mono text-[11px] truncate">{value}</span>
        <span className="rounded bg-amber-500/20 px-1 py-0.2 text-[9px] font-semibold text-amber-400 opacity-80 group-hover:opacity-100">
          BREAK GLASS
        </span>
      </button>

      <Modal
        isOpen={dialogOpen}
        onClose={() => {
          setDialogOpen(false);
          setReason("");
          setError(null);
        }}
        title={
          <div className="flex items-center space-x-2 text-amber-400">
            <ShieldAlert className="h-5 w-5 shrink-0" />
            <span>Emergency Break-Glass Unmasking</span>
          </div>
        }
        description={`Request temporary 15-minute unmasking of [${field}] on ${entity}. Access is permanently recorded in the immutable audit ledger.`}
        size="md"
      >
        <form onSubmit={handleBreakGlassSubmit} className="space-y-4">
          <div className="rounded-lg bg-amber-950/20 border border-amber-500/30 p-3 text-xs text-amber-300">
            <strong>Target Entity:</strong> {entity} <br />
            <strong>Target Field:</strong> {field}
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Emergency Justification <span className="text-red-400">*</span>
            </label>
            <textarea
              rows={3}
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
                if (error) setError(null);
              }}
              placeholder="e.g. Medical emergency response team dispatch / Identity verification for lost contingent badge..."
              data-testid="break-glass-reason-input"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 p-3 text-xs text-slate-100 placeholder-slate-500 focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
            />
            {error && (
              <p className="mt-1 text-xs text-red-400 font-medium" data-testid="break-glass-error">
                {error}
              </p>
            )}
          </div>

          <div className="flex items-center justify-end space-x-3 pt-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setDialogOpen(false);
                setReason("");
                setError(null);
              }}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={loading}
              disabled={!reason.trim()}
              leftIcon={<Unlock className="h-3.5 w-3.5" />}
              data-testid="break-glass-submit"
            >
              Authorize Elevation
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
};
