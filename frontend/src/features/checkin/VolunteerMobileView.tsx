import React, { useState } from "react";
import {
  UserCheck,
  Package,
  QrCode,
  ScanLine,
} from "lucide-react";
import { useToast, Badge } from "../../components/ui";
import { OfflineStatusPill } from "../../components/layout/OfflineStatusPill";
import { offlineDb } from "../../pwa/offlineDb";
import { useOfflineSync } from "../../pwa/useOfflineSync";
import { api, generateIdempotencyKey } from "../../api/client";

// Sound & Haptic Feedback utilities for outdoor operational environments
function playAudioFeedback(type: "success" | "warning" | "error") {
  try {
    if (typeof window !== "undefined" && (window.AudioContext || (window as any).webkitAudioContext)) {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.connect(gain);
      gain.connect(ctx.destination);

      if (type === "success") {
        osc.frequency.setValueAtTime(880, ctx.currentTime); // High pleasant A5
        gain.gain.setValueAtTime(0.15, ctx.currentTime);
        osc.start();
        osc.stop(ctx.currentTime + 0.12);
      } else if (type === "warning") {
        osc.frequency.setValueAtTime(440, ctx.currentTime);
        gain.gain.setValueAtTime(0.2, ctx.currentTime);
        osc.start();
        osc.stop(ctx.currentTime + 0.25);
      } else {
        osc.frequency.setValueAtTime(220, ctx.currentTime); // Low buzz
        gain.gain.setValueAtTime(0.25, ctx.currentTime);
        osc.start();
        osc.stop(ctx.currentTime + 0.35);
      }
    }
  } catch {
    // Audio context may require prior user interaction
  }

  // Mobile device vibration haptic feedback
  try {
    if (typeof navigator !== "undefined" && navigator.vibrate) {
      if (type === "success") {
        navigator.vibrate(80);
      } else if (type === "warning") {
        navigator.vibrate([100, 50, 100]);
      } else {
        navigator.vibrate([200, 100, 200]);
      }
    }
  } catch {
    // Vibration API optional
  }
}

export const VolunteerMobileView: React.FC = () => {
  const { addToast } = useToast();
  const { isOnline } = useOfflineSync();

  const [activeTab, setActiveTab] = useState<"checkin" | "merchandise">("checkin");

  // Check-in desk form state
  const [checkinId, setCheckinId] = useState<string>("P0102");
  const [wristband, setWristband] = useState<string>("WB_889210");
  const [dietChoice, setDietChoice] = useState<string>("VEG");
  const [lastCheckinResult, setLastCheckinResult] = useState<any | null>(null);
  const [isSubmittingCheckin, setIsSubmittingCheckin] = useState(false);

  // Merchandise counter form state
  const [merchId, setMerchId] = useState<string>("P0042");
  const [selectedItem, setSelectedItem] = useState<string>("ITEM_TSHIRT_L");
  const [lastMerchResult, setLastMerchResult] = useState<any | null>(null);
  const [isSubmittingMerch, setIsSubmittingMerch] = useState(false);

  // Check-in Execution
  const handleCheckinSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!checkinId.trim()) return;

    const pid = checkinId.trim().toUpperCase();
    setIsSubmittingCheckin(true);

    const payload = {
      participant_id: pid,
      wristband_code: wristband.trim() || undefined,
      verified_fields: dietChoice ? { diet: dietChoice } : {},
      desk_operator: "Volunteer Desk Mobile",
    };

    if (!isOnline) {
      // Offline mode: queue in Dexie
      try {
        const queuedOp = await offlineDb.enqueueSafeOp("CHECK_IN", payload);
        playAudioFeedback("success");
        setLastCheckinResult({
          status: "QUEUED_OFFLINE",
          participant_id: pid,
          wristband_code: wristband,
          client_op_id: queuedOp.client_op_id,
          message: "Check-in buffered locally in IndexedDB. Will sync automatically upon reconnect.",
        });
        addToast({
          type: "success",
          title: "Check-in Queued Offline",
          message: `${pid} buffered. Will sync when Wi-Fi reconnects.`,
        });
      } catch (err: any) {
        playAudioFeedback("error");
        addToast({
          type: "error",
          title: "Offline Storage Error",
          message: err?.message || "Failed to buffer offline checkin",
        });
      } finally {
        setIsSubmittingCheckin(false);
      }
      return;
    }

    // Online mode: attempt direct API call with offline fallback
    try {
      await api.post<any>(
        "/api/v1/checkin/verify-arrival",
        {
          expected_version: 1,
          participant_id: pid,
          wristband_code: wristband,
          verified_fields: dietChoice ? { diet: dietChoice } : {},
          desk_operator: "Volunteer Desk Mobile",
        },
        {
          idempotencyKey: generateIdempotencyKey(),
        }
      );

      playAudioFeedback("success");
      setLastCheckinResult({
        status: "CHECKED_IN",
        participant_id: pid,
        wristband_code: wristband,
        message: "Check-in verified and key released.",
      });
      addToast({
        type: "success",
        title: "Check-in Confirmed",
        message: `${pid} is now verified as CHECKED_IN.`,
      });
    } catch (err: any) {
      // Fallback to offline queue if network drops mid-call
      const queuedOp = await offlineDb.enqueueSafeOp("CHECK_IN", payload);
      playAudioFeedback("warning");
      setLastCheckinResult({
        status: "QUEUED_OFFLINE",
        participant_id: pid,
        wristband_code: wristband,
        client_op_id: queuedOp.client_op_id,
        message: "Network interrupted; check-in saved safely to local offline queue.",
      });
    } finally {
      setIsSubmittingCheckin(false);
    }
  };

  // Merchandise Issue Execution
  const handleMerchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!merchId.trim()) return;

    const pid = merchId.trim().toUpperCase();
    setIsSubmittingMerch(true);

    const payload = {
      participant_id: pid,
      item_id: selectedItem,
      counter_id: "VOL_COUNTER_01",
      reason: "Volunteer counter handover",
    };

    if (!isOnline) {
      // Offline mode: queue in Dexie
      try {
        const queuedOp = await offlineDb.enqueueSafeOp("MERCHANDISE_ISSUE", payload);
        playAudioFeedback("success");
        setLastMerchResult({
          status: "QUEUED_OFFLINE",
          participant_id: pid,
          item_id: selectedItem,
          client_op_id: queuedOp.client_op_id,
          message: "Merchandise issue buffered in IndexedDB.",
        });
        addToast({
          type: "success",
          title: "Merch Issue Queued Offline",
          message: `${pid} kit buffered for reconnect sync.`,
        });
      } catch (err: any) {
        playAudioFeedback("error");
        addToast({
          type: "error",
          title: "Offline Storage Error",
          message: err?.message || "Failed to buffer offline merch issue",
        });
      } finally {
        setIsSubmittingMerch(false);
      }
      return;
    }

    // Online mode: attempt direct API call
    try {
      await api.post<any>("/api/v1/merchandise/issue", {
        participant_id: pid,
        item_id: selectedItem,
        counter_id: "VOL_COUNTER_01",
        reason: "Volunteer counter handover",
      });

      playAudioFeedback("success");
      setLastMerchResult({
        status: "ISSUED",
        participant_id: pid,
        item_id: selectedItem,
        message: "Item successfully issued.",
      });
      addToast({
        type: "success",
        title: "Merchandise Issued",
        message: `${selectedItem} issued to ${pid}.`,
      });
    } catch (err: any) {
      if (err?.code === "ALREADY_ISSUED" || err?.status === 409) {
        playAudioFeedback("error");
        setLastMerchResult({
          status: "ALREADY_ISSUED",
          participant_id: pid,
          item_id: selectedItem,
          message: "ALREADY ISSUED: Duplicate claim prevented. Item was previously handed out.",
        });
      } else {
        // Network drop: buffer offline
        const queuedOp = await offlineDb.enqueueSafeOp("MERCHANDISE_ISSUE", payload);
        playAudioFeedback("warning");
        setLastMerchResult({
          status: "QUEUED_OFFLINE",
          participant_id: pid,
          item_id: selectedItem,
          client_op_id: queuedOp.client_op_id,
          message: "Network drop: kit issuance queued in IndexedDB.",
        });
      }
    } finally {
      setIsSubmittingMerch(false);
    }
  };

  return (
    <div
      className="max-w-md mx-auto min-h-screen bg-[#070B14] text-white p-4 space-y-5"
      data-testid="volunteer-mobile-workspace"
    >
      {/* Header bar */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-extrabold tracking-tight text-white">Volunteer Counter</h1>
            <Badge variant="solid" status="PENDING" className="text-[10px]">
              MOBILE MODE
            </Badge>
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">
            Aarohan Fest 2026 · Minimal Data Exposure
          </div>
        </div>

        <OfflineStatusPill />
      </div>

      {/* Two Big Flow Tabs (Check-in vs Merchandise) */}
      <div className="grid grid-cols-2 gap-2 bg-slate-900/90 p-1.5 rounded-xl border border-slate-800">
        <button
          type="button"
          data-testid="volunteer-tab-checkin"
          onClick={() => {
            setActiveTab("checkin");
            playAudioFeedback("success");
          }}
          className={`flex items-center justify-center gap-2 py-3.5 px-3 rounded-lg font-bold text-sm transition-all ${
            activeTab === "checkin"
              ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <UserCheck className="w-5 h-5" />
          <span>1. Check-In</span>
        </button>

        <button
          type="button"
          data-testid="volunteer-tab-merch"
          onClick={() => {
            setActiveTab("merchandise");
            playAudioFeedback("success");
          }}
          className={`flex items-center justify-center gap-2 py-3.5 px-3 rounded-lg font-bold text-sm transition-all ${
            activeTab === "merchandise"
              ? "bg-emerald-600 text-white shadow-lg shadow-emerald-600/30"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <Package className="w-5 h-5" />
          <span>2. Merchandise</span>
        </button>
      </div>

      {/* Flow 1: Check-in Desk */}
      {activeTab === "checkin" && (
        <div className="space-y-4 animate-fadeIn" data-testid="volunteer-checkin-flow">
          <form onSubmit={handleCheckinSubmit} className="space-y-4">
            <div className="p-4 rounded-xl border border-slate-800 bg-[#0E1526] space-y-3">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5">
                  Participant ID / Barcode <span className="text-rose-400">*</span>
                </label>
                <div className="relative">
                  <input
                    type="text"
                    data-testid="volunteer-checkin-id-input"
                    value={checkinId}
                    onChange={(e) => setCheckinId(e.target.value)}
                    placeholder="e.g. P0102"
                    className="w-full bg-slate-950 border-2 border-slate-700 rounded-xl px-4 py-3.5 text-lg font-mono text-white placeholder-slate-600 focus:border-indigo-500 focus:outline-none"
                  />
                  <QrCode className="absolute right-3.5 top-3.5 w-6 h-6 text-slate-500 pointer-events-none" />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5">
                  Wristband Security Code
                </label>
                <input
                  type="text"
                  data-testid="volunteer-checkin-wristband-input"
                  value={wristband}
                  onChange={(e) => setWristband(e.target.value)}
                  placeholder="e.g. WB_889210"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-3 text-sm font-mono text-white placeholder-slate-600 focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5">
                  Diet Verification (Meal Pass)
                </label>
                <select
                  data-testid="volunteer-checkin-diet-select"
                  value={dietChoice}
                  onChange={(e) => setDietChoice(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white focus:border-indigo-500 focus:outline-none"
                >
                  <option value="VEG">Vegetarian (Standard)</option>
                  <option value="JAIN">Jain / Strict Pure-Veg</option>
                  <option value="NON_VEG">Non-Vegetarian</option>
                </select>
              </div>
            </div>

            {/* Giant Touch Button */}
            <button
              type="submit"
              data-testid="volunteer-confirm-checkin-btn"
              disabled={isSubmittingCheckin || !checkinId.trim()}
              className="w-full py-4 px-6 rounded-xl font-extrabold text-base tracking-wide bg-indigo-600 hover:bg-indigo-500 active:scale-[0.98] text-white shadow-xl shadow-indigo-600/30 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
            >
              <UserCheck className="w-5 h-5" />
              <span>{isSubmittingCheckin ? "Processing..." : "Confirm & Check In"}</span>
            </button>
          </form>

          {/* Feedback Card */}
          {lastCheckinResult && (
            <div
              data-testid="volunteer-checkin-result"
              className={`p-4 rounded-xl border-2 text-xs space-y-2 ${
                lastCheckinResult.status === "CHECKED_IN"
                  ? "border-emerald-500 bg-emerald-950/30 text-emerald-200"
                  : "border-amber-500 bg-amber-950/30 text-amber-200"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm uppercase">
                  {lastCheckinResult.status === "CHECKED_IN" ? "Checked In Cleanly" : "Buffered Offline"}
                </span>
                <Badge
                  variant="solid"
                  status={lastCheckinResult.status === "CHECKED_IN" ? "SUCCESS" : "PENDING"}
                >
                  {lastCheckinResult.status}
                </Badge>
              </div>
              <p className="leading-relaxed">{lastCheckinResult.message}</p>
              {lastCheckinResult.client_op_id && (
                <div className="text-[10px] font-mono text-slate-400">
                  Client Op UUID: {lastCheckinResult.client_op_id}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Flow 2: Merchandise Counter */}
      {activeTab === "merchandise" && (
        <div className="space-y-4 animate-fadeIn" data-testid="volunteer-merch-flow">
          <form onSubmit={handleMerchSubmit} className="space-y-4">
            <div className="p-4 rounded-xl border border-slate-800 bg-[#0E1526] space-y-3">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5">
                  Participant ID / Barcode <span className="text-rose-400">*</span>
                </label>
                <div className="relative">
                  <input
                    type="text"
                    data-testid="volunteer-merch-id-input"
                    value={merchId}
                    onChange={(e) => setMerchId(e.target.value)}
                    placeholder="e.g. P0042"
                    className="w-full bg-slate-950 border-2 border-slate-700 rounded-xl px-4 py-3.5 text-lg font-mono text-white placeholder-slate-600 focus:border-emerald-500 focus:outline-none"
                  />
                  <ScanLine className="absolute right-3.5 top-3.5 w-6 h-6 text-slate-500 pointer-events-none" />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5">
                  Select Item to Issue
                </label>
                <select
                  data-testid="volunteer-merch-item-select"
                  value={selectedItem}
                  onChange={(e) => setSelectedItem(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white focus:border-emerald-500 focus:outline-none"
                >
                  <option value="ITEM_TSHIRT_L">Festival T-Shirt (Size L)</option>
                  <option value="ITEM_TSHIRT_M">Festival T-Shirt (Size M)</option>
                  <option value="ITEM_TSHIRT_XL">Festival T-Shirt (Size XL)</option>
                  <option value="ITEM_DELEGATE_KIT">Full Delegate Kit Bag</option>
                  <option value="ITEM_BAND_RFID">Official RFID Pass</option>
                </select>
              </div>
            </div>

            {/* Giant Touch Button */}
            <button
              type="submit"
              data-testid="volunteer-confirm-issue-btn"
              disabled={isSubmittingMerch || !merchId.trim()}
              className="w-full py-4 px-6 rounded-xl font-extrabold text-base tracking-wide bg-emerald-600 hover:bg-emerald-500 active:scale-[0.98] text-white shadow-xl shadow-emerald-600/30 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
            >
              <Package className="w-5 h-5" />
              <span>{isSubmittingMerch ? "Handing Over..." : "Scan & Issue Kit"}</span>
            </button>
          </form>

          {/* Feedback Card */}
          {lastMerchResult && (
            <div
              data-testid="volunteer-merch-result"
              className={`p-4 rounded-xl border-2 text-xs space-y-2 ${
                lastMerchResult.status === "ISSUED"
                  ? "border-emerald-500 bg-emerald-950/30 text-emerald-200"
                  : lastMerchResult.status === "ALREADY_ISSUED"
                  ? "border-rose-500 bg-rose-950/40 text-rose-200"
                  : "border-amber-500 bg-amber-950/30 text-amber-200"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm uppercase">
                  {lastMerchResult.status === "ISSUED"
                    ? "Issued Successfully"
                    : lastMerchResult.status === "ALREADY_ISSUED"
                    ? "Duplicate Claim Prevented"
                    : "Buffered Offline"}
                </span>
                <Badge
                  variant="solid"
                  status={
                    lastMerchResult.status === "ISSUED"
                      ? "SUCCESS"
                      : lastMerchResult.status === "ALREADY_ISSUED"
                      ? "REJECTED"
                      : "PENDING"
                  }
                >
                  {lastMerchResult.status}
                </Badge>
              </div>
              <p className="leading-relaxed">{lastMerchResult.message}</p>
              {lastMerchResult.client_op_id && (
                <div className="text-[10px] font-mono text-slate-400">
                  Client Op UUID: {lastMerchResult.client_op_id}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Security Privacy Notice */}
      <div className="text-[11px] text-slate-500 p-3 rounded-lg border border-slate-900 bg-slate-950 text-center leading-relaxed">
        <strong>Privacy Protocol:</strong> Volunteer terminal is strictly restricted to desk scans. Personal phone, email, medical notes and room details are masked at the API gateway layer.
      </div>
    </div>
  );
};

export default VolunteerMobileView;
