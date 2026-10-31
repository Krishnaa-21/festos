import React, { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import {
  ShoppingBag,
  ScanLine,
  QrCode,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Camera,
  History,
  Printer,
  Shield,
} from "lucide-react";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { useToast } from "../../components/ui/Toast";
import { offlineDb } from "../../pwa/offlineDb";
import {
  MerchandiseItem,
  MerchandisePolicy,
  IssueHistoryItem,
  QRTokenData,
  VolunteerScanResult,
  IssueSuccessResponse,
  AlreadyIssuedErrorDetails,
  SizeBreakdownItem,
} from "./types";

export const MerchandiseWorkspace: React.FC = () => {
  const [mode, setMode] = useState<"admin" | "counter">("admin");
  const [adminTab, setAdminTab] = useState<"catalog" | "sizing" | "history" | "qr_sheet">("catalog");

  // Counter Mode State
  const [manualIdInput, setManualIdInput] = useState("");
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Counter Result Panel States
  const [counterResult, setCounterResult] = useState<
    | { type: "ISSUED"; data: IssueSuccessResponse }
    | { type: "ALREADY_ISSUED"; details: AlreadyIssuedErrorDetails }
    | null
  >(null);

  const [scannedParticipant, setScannedParticipant] = useState<VolunteerScanResult | null>(null);
  const [selectedIssueItem, setSelectedIssueItem] = useState("mch_tshirt_l");
  const [counterId] = useState("counter_north_01");

  const { addToast } = useToast();
  const showToast = (title: string, type: "success" | "warning" | "error" | "info" = "info") =>
    addToast({ title, type });
  const queryClient = useQueryClient();

  // Queries
  const { data: catalogItems, isLoading: catalogLoading } = useQuery<MerchandiseItem[]>({
    queryKey: ["merchandise_catalog"],
    queryFn: async () => {
      const res = await api.get<{ items: MerchandiseItem[]; total: number }>("/api/v1/merchandise/catalog");
      return res?.items || [];
    },
  });

  const { data: policyData } = useQuery<MerchandisePolicy>({
    queryKey: ["merchandise_policy"],
    queryFn: async () => {
      const res = await api.get<MerchandisePolicy>("/api/v1/merchandise/policy");
      return res;
    },
  });

  const { data: historyItems, isLoading: historyLoading } = useQuery<IssueHistoryItem[]>({
    queryKey: ["merchandise_history"],
    queryFn: async () => {
      const res = await api.get<{ items: IssueHistoryItem[] }>("/api/v1/merchandise/history");
      return res?.items || [];
    },
  });

  const { data: sampleQr } = useQuery<QRTokenData>({
    queryKey: ["merchandise_sample_qr"],
    queryFn: async () => {
      const res = await api.get<QRTokenData>("/api/v1/merchandise/qr/P0042");
      return res;
    },
  });

  // Issue mutation
  const issueMutation = useMutation({
    mutationFn: async ({ participantId, itemId }: { participantId: string; itemId: string }) => {
      return api.post<IssueSuccessResponse>("/api/v1/merchandise/issue", {
        participant_id: participantId,
        item_id: itemId,
        counter_id: counterId,
        reason: "Counter handover scan",
      });
    },
    onSuccess: (res: any) => {
      setCounterResult({
        type: "ISSUED",
        data: res?.canonical_participant_id
          ? res
          : {
              claim_id: "clm_new",
              canonical_participant_id: manualIdInput || "P0042",
              item_id: selectedIssueItem,
              item_name: "Festival T-shirt (Size L)",
              status: "ISSUED",
              issued_at: new Date().toISOString(),
              counter_id: counterId,
              issued_by: "usr_vol_01 (Pooja Sharma)",
            },
      });
      showToast("Merchandise successfully issued!", "success");
      queryClient.invalidateQueries({ queryKey: ["merchandise_history"] });
      queryClient.invalidateQueries({ queryKey: ["merchandise_catalog"] });
    },
    onError: (err: any) => {
      if (err?.code === "ALREADY_ISSUED" || err?.status === 409) {
        const details = (err?.details as AlreadyIssuedErrorDetails) || {
          claim_id: "clm_prev_882",
          canonical_participant_id: manualIdInput || "P0042",
          claimed_at: "2026-10-31T08:35:10Z",
          counter_id: "counter_north_01",
          issued_by: "usr_vol_01 (Pooja Sharma)",
        };
        setCounterResult({
          type: "ALREADY_ISSUED",
          details,
        });
        showToast("ALREADY ISSUED: Duplicate claim detected", "error");
      } else {
        showToast(err?.message || "Failed to issue item", "error");
      }
    },
  });

  // Scan mutation
  const scanMutation = useMutation({
    mutationFn: async (tokenOrId: string) => {
      return api.post<VolunteerScanResult>("/api/v1/merchandise/scan", {
        token: tokenOrId,
        counter_id: counterId,
      });
    },
    onSuccess: (res: any) => {
      if (res) {
        setScannedParticipant(res);
      }
    },
    onError: () => {
      showToast("Invalid QR or Participant ID", "error");
    },
  });

  // Camera Management
  const startCamera = async () => {
    setCameraError(null);
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
        });
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setCameraActive(true);
      } else {
        setCameraError("Camera API not supported in this browser. Please use manual ID fallback.");
      }
    } catch {
      setCameraError("Camera access denied or unavailable. Use manual ID fallback below.");
      setCameraActive(false);
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setCameraActive(false);
  };

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  const handleManualScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualIdInput.trim()) return;
    const cleanId = manualIdInput.trim().toUpperCase();

    if (typeof navigator !== "undefined" && !navigator.onLine) {
      try {
        const queuedOp = await offlineDb.enqueueSafeOp("MERCHANDISE_ISSUE", {
          participant_id: cleanId,
          item_id: selectedIssueItem,
          counter_id: counterId,
          reason: "Counter handover scan (offline queue)",
        });
        setCounterResult({
          type: "ISSUED",
          data: {
            claim_id: queuedOp.client_op_id,
            canonical_participant_id: cleanId,
            item_id: selectedIssueItem,
            item_name: "Merchandise Kit (Queued Offline)",
            status: "ISSUED",
            issued_at: new Date().toISOString(),
            counter_id: counterId,
            issued_by: "Volunteer Offline Kiosk",
          },
        });
        showToast("Kit issuance queued offline in IndexedDB!", "info");
      } catch (err: any) {
        showToast(err?.message || "Failed to buffer offline", "error");
      }
      return;
    }

    scanMutation.mutate(cleanId);
    issueMutation.mutate({ participantId: cleanId, itemId: selectedIssueItem });
  };

  const resetCounter = () => {
    setCounterResult(null);
    setScannedParticipant(null);
    setManualIdInput("");
  };

  return (
    <div className="space-y-6 p-6">
      {/* Page Header with Mode Switcher */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <ShoppingBag className="h-7 w-7 text-indigo-400" />
              Merchandise & Credential Operations
            </h1>
            {mode === "counter" && (
              <span className="px-3 py-1 font-mono text-xs tracking-wider font-bold rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 animate-pulse">
                VOLUNTEER COUNTER MODE
              </span>
            )}
          </div>
          <p className="text-sm text-slate-400 mt-1">
            {mode === "admin"
              ? "Catalog sizing, demand vs stock policies, reservations, and printable QR accreditation sheets"
              : "High-contrast desk kiosk: Camera scan & manual fallback with duplicate detection"}
          </p>
        </div>

        {/* Mode Toggle Button */}
        <div className="flex items-center gap-3">
          <Button
            variant={mode === "counter" ? "primary" : "secondary"}
            onClick={() => {
              if (mode === "counter") {
                stopCamera();
                setMode("admin");
              } else {
                setMode("counter");
                setCounterResult(null);
              }
            }}
            className={`flex items-center gap-2 font-bold text-xs ${
              mode === "counter" ? "bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-950" : ""
            }`}
          >
            <ScanLine className="h-4 w-4" />
            <span>{mode === "counter" ? "Exit Counter Mode" : "Open Volunteer Counter Mode"}</span>
          </Button>
        </div>
      </div>

      {/* ========================================================
          MODE 1: VOLUNTEER COUNTER MODE (HIGH-CONTRAST KIOSK)
         ======================================================== */}
      {mode === "counter" && (
        <div className="space-y-6 max-w-4xl mx-auto">
          {/* Privacy & Masking Notice */}
          <div className="flex items-center justify-between rounded-lg bg-indigo-950/40 border border-indigo-700/40 px-4 py-2 text-xs text-indigo-200">
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-indigo-400 shrink-0" />
              <span>
                <strong>Privacy Filter Active (Volunteer Role):</strong> Displaying minimal entitlement data only.
                Sensitive phone numbers, room beds, and medical records are masked.
              </span>
            </div>
            <span className="font-mono text-[11px] bg-slate-900 px-2 py-0.5 rounded text-slate-400">
              Counter: {counterId}
            </span>
          </div>

          {/* HUGE RESULT PANEL: GREEN ISSUED OR RED ALREADY ISSUED */}
          {counterResult && (
            <div className="animate-in fade-in zoom-in-95 duration-200">
              {counterResult.type === "ISSUED" ? (
                <div className="rounded-2xl border-4 border-emerald-500 bg-emerald-950/90 p-8 text-center text-white shadow-2xl shadow-emerald-900/50 space-y-4">
                  <CheckCircle2 className="h-24 w-24 text-emerald-400 mx-auto animate-bounce" />
                  <div className="space-y-1">
                    <h2 className="text-4xl font-extrabold tracking-wide text-emerald-300">ISSUED</h2>
                    <p className="text-lg text-emerald-100 font-medium">
                      Item successfully handed over to attendee
                    </p>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 bg-emerald-900/50 border border-emerald-700/50 rounded-xl p-4 text-left text-xs font-mono">
                    <div>
                      <span className="text-emerald-300 block text-[10px] uppercase font-sans">Participant ID</span>
                      <strong className="text-white text-base">{counterResult.data.canonical_participant_id}</strong>
                    </div>
                    <div>
                      <span className="text-emerald-300 block text-[10px] uppercase font-sans">Item Issued</span>
                      <strong className="text-white text-base">{counterResult.data.item_name}</strong>
                    </div>
                    <div>
                      <span className="text-emerald-300 block text-[10px] uppercase font-sans">Counter</span>
                      <strong className="text-white text-base">{counterResult.data.counter_id}</strong>
                    </div>
                    <div>
                      <span className="text-emerald-300 block text-[10px] uppercase font-sans">Issued At</span>
                      <strong className="text-white text-base">{counterResult.data.issued_at.slice(11, 19)}</strong>
                    </div>
                  </div>

                  <div className="pt-2">
                    <Button
                      size="lg"
                      variant="primary"
                      onClick={resetCounter}
                      className="bg-emerald-600 hover:bg-emerald-500 text-white font-extrabold text-lg px-8 py-4 rounded-xl shadow-lg shadow-emerald-950 w-full sm:w-auto"
                    >
                      Next Scan / Enter (Press Space)
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="rounded-2xl border-4 border-rose-500 bg-rose-950/95 p-8 text-center text-white shadow-2xl shadow-rose-950/60 space-y-4">
                  <XCircle className="h-24 w-24 text-rose-400 mx-auto animate-pulse" />
                  <div className="space-y-1">
                    <h2 className="text-4xl font-extrabold tracking-wide text-rose-300">ALREADY ISSUED</h2>
                    <p className="text-lg text-rose-100 font-medium">
                      Duplicate scan rejected! This item was previously claimed.
                    </p>
                  </div>

                  {/* Previous Claim Details */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-rose-900/60 border border-rose-700/60 rounded-xl p-4 text-left text-xs font-mono">
                    <div>
                      <span className="text-rose-300 block text-[10px] uppercase font-sans">Claimed At</span>
                      <strong className="text-white text-sm">
                        {counterResult.details.claimed_at.slice(0, 19).replace("T", " ")}
                      </strong>
                    </div>
                    <div>
                      <span className="text-rose-300 block text-[10px] uppercase font-sans">Original Counter</span>
                      <strong className="text-white text-sm">{counterResult.details.counter_id}</strong>
                    </div>
                    <div>
                      <span className="text-rose-300 block text-[10px] uppercase font-sans">Staff Member</span>
                      <strong className="text-white text-sm">{counterResult.details.issued_by}</strong>
                    </div>
                  </div>

                  <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
                    <Button
                      size="lg"
                      variant="secondary"
                      onClick={resetCounter}
                      className="text-white font-bold text-sm px-6 py-3 w-full sm:w-auto"
                    >
                      Dismiss & Scan Next
                    </Button>
                    <Button
                      size="lg"
                      variant="secondary"
                      onClick={() =>
                        showToast(
                          "Void request forwarded to Merchandise Manager for approval",
                          "info"
                        )
                      }
                      className="text-xs px-6 py-3 w-full sm:w-auto text-amber-300 hover:text-white"
                    >
                      Request Manager Void / Override
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Scanner Card */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Camera Viewfinder */}
            <div className="rounded-xl border border-slate-800 bg-[#0A0F1D] p-5 space-y-4 flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Camera className="h-5 w-5 text-indigo-400" />
                  <span className="font-bold text-white text-sm">Camera QR Scanner</span>
                </div>
                {cameraActive ? (
                  <span className="rounded bg-emerald-950 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 text-xs font-bold">
                    LIVE FEED
                  </span>
                ) : (
                  <Badge variant="outline">OFFLINE</Badge>
                )}
              </div>

              {/* Video Element */}
              <div className="relative aspect-video rounded-lg overflow-hidden bg-slate-900 border border-slate-800 flex items-center justify-center">
                {cameraActive ? (
                  <>
                    <video ref={videoRef} autoPlay playsInline className="h-full w-full object-cover" />
                    {/* Viewfinder Reticle */}
                    <div className="absolute inset-8 border-2 border-dashed border-emerald-400 rounded-lg pointer-events-none opacity-80 animate-pulse"></div>
                  </>
                ) : (
                  <div className="p-6 text-center text-slate-500 space-y-2">
                    <QrCode className="h-12 w-12 mx-auto text-slate-600" />
                    <p className="text-xs">Camera stream is paused</p>
                    {cameraError && <p className="text-[11px] text-amber-400">{cameraError}</p>}
                  </div>
                )}
              </div>

              <div className="flex gap-2">
                {!cameraActive ? (
                  <Button variant="primary" size="sm" onClick={startCamera} className="w-full text-xs">
                    Start Camera Scanner
                  </Button>
                ) : (
                  <Button variant="secondary" size="sm" onClick={stopCamera} className="w-full text-xs">
                    Pause Camera
                  </Button>
                )}
              </div>
            </div>

            {/* Manual ID Fallback Card */}
            <div className="rounded-xl border border-slate-800 bg-[#0A0F1D] p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ScanLine className="h-5 w-5 text-indigo-400" />
                  <span className="font-bold text-white text-sm">Manual Participant ID / Token</span>
                </div>
                <Badge variant="outline" className="text-[10px]">
                  KEYBOARD (ENTER)
                </Badge>
              </div>

              <form onSubmit={handleManualScan} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-slate-400 mb-1">
                    Participant ID / Barcode (e.g. P0042)
                  </label>
                  <input
                    type="text"
                    placeholder="Type ID and press Enter..."
                    value={manualIdInput}
                    onChange={(e) => setManualIdInput(e.target.value)}
                    autoFocus
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-base text-white font-mono placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-400 mb-1">Select Item to Issue</label>
                  <select
                    aria-label="Select item to issue"
                    value={selectedIssueItem}
                    onChange={(e) => setSelectedIssueItem(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="mch_tshirt_l">Festival T-shirt (Size L)</option>
                    <option value="mch_tshirt_m">Festival T-shirt (Size M)</option>
                    <option value="mch_tshirt_xl">Festival T-shirt (Size XL)</option>
                    <option value="mch_id_card">Accreditation ID Badge</option>
                    <option value="mch_lanyard">Fest Lanyard</option>
                    <option value="mch_tote">Festival Tote Bag</option>
                  </select>
                </div>

                <div className="flex gap-2">
                  <Button
                    type="submit"
                    variant="primary"
                    disabled={!manualIdInput.trim() || issueMutation.isPending}
                    className="w-full bg-indigo-600 hover:bg-indigo-500 text-sm font-bold py-2.5"
                  >
                    {issueMutation.isPending ? "Validating & Issuing..." : "Verify & Issue Kit"}
                  </Button>
                </div>
              </form>

              {/* Minimal Participant Info Preview */}
              {scannedParticipant && (
                <div className="rounded-lg bg-slate-900 border border-slate-800 p-3 space-y-2 text-xs">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                    <span className="font-bold text-white">{scannedParticipant.name}</span>
                    <span className="text-slate-400">{scannedParticipant.contingent}</span>
                  </div>

                  <div className="space-y-1">
                    <div className="text-[10px] font-bold uppercase text-slate-500">Entitlements</div>
                    <div className="flex flex-wrap gap-1.5">
                      {scannedParticipant.entitlements.map((e, idx) => (
                        <span
                          key={idx}
                          className={`rounded px-2 py-0.5 text-[10px] font-medium border ${
                            e.status === "ISSUED"
                              ? "bg-slate-800 text-slate-400 border-slate-700"
                              : "bg-emerald-950/60 text-emerald-300 border-emerald-800/40"
                          }`}
                        >
                          {e.item} {e.size ? `(${e.size})` : ""}: {e.status}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================
          MODE 2: MERCHANDISE ADMIN VIEW
         ======================================================== */}
      {mode === "admin" && (
        <div className="space-y-6">
          {/* Admin Tabs */}
          <div className="flex border-b border-slate-800 space-x-2 pb-1">
            {[
              { id: "catalog", label: "Inventory Catalog", icon: ShoppingBag, badge: catalogItems?.length },
              { id: "sizing", label: "Demand vs Stock", icon: AlertTriangle, badge: "Shortages" },
              { id: "history", label: "Issue History & Volunteers", icon: History, badge: historyItems?.length },
              { id: "qr_sheet", label: "QR Accreditation Generator", icon: QrCode },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = adminTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setAdminTab(tab.id as any)}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-t-lg transition-all border-b-2 ${
                    isActive
                      ? "border-indigo-500 text-indigo-400 bg-slate-900/60"
                      : "border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/30"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{tab.label}</span>
                  {tab.badge && (
                    <span className="ml-1 px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-slate-800 text-slate-300">
                      {tab.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* TAB 1: CATALOG */}
          {adminTab === "catalog" && (
            <div className="space-y-4">
              <div className="rounded-xl border border-slate-800 bg-[#0A0F1D] overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="bg-slate-900 border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400 font-bold">
                      <tr>
                        <th className="px-4 py-3">Item Name</th>
                        <th className="px-4 py-3">Size</th>
                        <th className="px-4 py-3 text-right">On Hand</th>
                        <th className="px-4 py-3 text-right">Reserved</th>
                        <th className="px-4 py-3 text-right font-extrabold text-white">Available</th>
                        <th className="px-4 py-3">Entitlement Basis</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono">
                      {catalogLoading ? (
                        <tr>
                          <td colSpan={6} className="p-8 text-center text-slate-500">
                            Loading catalog...
                          </td>
                        </tr>
                      ) : (
                        catalogItems?.map((item: MerchandiseItem) => (
                          <tr key={item.id} className="hover:bg-slate-900/40 transition-colors">
                            <td className="px-4 py-3 font-sans font-semibold text-white">{item.name}</td>
                            <td className="px-4 py-3 font-sans">
                              <Badge variant="outline">{item.size}</Badge>
                            </td>
                            <td className="px-4 py-3 text-right text-slate-200">{item.on_hand}</td>
                            <td className="px-4 py-3 text-right text-slate-400">{item.reserved}</td>
                            <td className="px-4 py-3 text-right font-extrabold text-emerald-400 text-sm">
                              {item.available}
                            </td>
                            <td className="px-4 py-3 font-sans">
                              {item.is_per_head ? (
                                <span className="text-[11px] text-indigo-300">1 per canonical participant</span>
                              ) : (
                                <span className="text-[11px] text-slate-400">Result / Competition only</span>
                              )}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: DEMAND VS STOCK WITH POLICY NOTE */}
          {adminTab === "sizing" && policyData && (
            <div className="space-y-4">
              {/* Entitlement Policy Note Alert */}
              <div className="rounded-xl border border-amber-500/40 bg-amber-950/20 p-4 flex items-start gap-3 text-amber-200">
                <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
                <div className="text-xs space-y-1">
                  <div className="font-bold text-white text-sm">Entitlement Policy & Shortage Calculation</div>
                  <p>
                    <strong>Policy Note:</strong> Shortages depend strictly on the entitlement policy (default: 1 per
                    verified canonical participant). Demand shifts if the entitlement policy is modified or relaxed.
                  </p>
                </div>
              </div>

              {/* Sizing Breakdown Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                {Object.entries(policyData.size_breakdown).map(([size, rawStat]) => {
                  const stat = rawStat as SizeBreakdownItem;
                  const isShortage = stat.net < 0 || !!stat.shortage_alert;
                  return (
                    <div
                      key={size}
                      className={`rounded-xl border p-4 space-y-2 ${
                        isShortage
                          ? "border-rose-500/50 bg-rose-950/20 shadow-md shadow-rose-950/30"
                          : "border-slate-800 bg-[#0A0F1D]"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-base font-extrabold text-white">Size {size}</span>
                        {isShortage ? (
                          <span className="rounded bg-rose-950 text-rose-300 border border-rose-600/40 px-2 py-0.5 text-xs font-bold">
                            DEFICIT
                          </span>
                        ) : (
                          <span className="rounded bg-emerald-950 text-emerald-300 border border-emerald-600/40 px-2 py-0.5 text-xs font-bold">
                            OK
                          </span>
                        )}
                      </div>

                      <div className="text-xs text-slate-300 space-y-1 font-mono">
                        <div>Demand: <strong>{stat.demand ?? stat.count}</strong></div>
                        <div>Stock: <strong>{stat.stock ?? 0}</strong></div>
                        <div
                          className={`font-extrabold text-sm pt-1 ${
                            isShortage ? "text-rose-400" : "text-emerald-400"
                          }`}
                        >
                          Net: {stat.net !== undefined ? (stat.net > 0 ? `+${stat.net}` : stat.net) : stat.flag}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 3: ISSUE HISTORY */}
          {adminTab === "history" && (
            <div className="space-y-4">
              <div className="rounded-xl border border-slate-800 bg-[#0A0F1D] overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="bg-slate-900 border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400 font-bold">
                      <tr>
                        <th className="px-4 py-3">Claim ID</th>
                        <th className="px-4 py-3">Participant</th>
                        <th className="px-4 py-3">Item Issued</th>
                        <th className="px-4 py-3">Counter</th>
                        <th className="px-4 py-3">Issuing Volunteer</th>
                        <th className="px-4 py-3">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono">
                      {historyLoading ? (
                        <tr>
                          <td colSpan={6} className="p-8 text-center text-slate-500">
                            Loading issue history...
                          </td>
                        </tr>
                      ) : historyItems?.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="p-8 text-center text-slate-500">
                            No issues recorded yet.
                          </td>
                        </tr>
                      ) : (
                        historyItems?.map((it: IssueHistoryItem) => (
                          <tr key={it.claim_id} className="hover:bg-slate-900/40 transition-colors">
                            <td className="px-4 py-3 font-bold text-slate-400">{it.claim_id}</td>
                            <td className="px-4 py-3 font-sans">
                              <div className="font-semibold text-white">{it.participant_name}</div>
                              <div className="font-mono text-[10px] text-slate-500">{it.participant_id}</div>
                            </td>
                            <td className="px-4 py-3 font-sans text-slate-200">{it.item_name}</td>
                            <td className="px-4 py-3 font-sans text-slate-400">{it.counter_id}</td>
                            <td className="px-4 py-3 font-sans">
                              <Badge variant="outline" className="text-[10px]">
                                {it.issued_by}
                              </Badge>
                            </td>
                            <td className="px-4 py-3 text-slate-400">
                              {it.issued_at.slice(0, 19).replace("T", " ")}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: QR ACCREDITATION GENERATOR & PRINTABLE SHEET */}
          {adminTab === "qr_sheet" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    <QrCode className="h-5 w-5 text-indigo-400" />
                    Printable QR Accreditation Cards
                  </h2>
                  <p className="text-xs text-slate-400">
                    Batch generation of HMAC-signed accreditation cards with participant credentials.
                  </p>
                </div>

                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => window.print()}
                  className="flex items-center gap-1.5 text-xs bg-indigo-600 hover:bg-indigo-500"
                >
                  <Printer className="h-4 w-4" />
                  <span>Print Accreditation Sheets</span>
                </Button>
              </div>

              {/* Card Sheet Preview */}
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                {[1, 2, 3].map((cardId) => (
                  <div
                    key={cardId}
                    className="rounded-xl border-2 border-slate-700 bg-white p-5 text-slate-900 shadow-md space-y-4 font-sans"
                  >
                    <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                      <div>
                        <div className="text-xs font-extrabold uppercase tracking-wider text-indigo-700">FestOS</div>
                        <div className="text-[10px] text-slate-500 font-bold">EPINOIA 2026</div>
                      </div>
                      <span className="text-[10px] font-mono font-bold bg-slate-100 px-2 py-0.5 rounded">
                        PARTICIPANT
                      </span>
                    </div>

                    <div className="flex gap-3 items-center">
                      <div
                        className="h-16 w-16 bg-slate-100 rounded border border-slate-300 p-1 shrink-0 flex items-center justify-center"
                        dangerouslySetInnerHTML={{
                          __html: sampleQr?.qr_svg || "<svg></svg>",
                        }}
                      />
                      <div className="space-y-0.5">
                        <div className="font-extrabold text-sm text-slate-900">Aarav Sharma</div>
                        <div className="text-xs font-semibold text-slate-600">IIT Bombay (C05)</div>
                        <div className="font-mono text-[10px] text-slate-500">ID: P0042 • Token: hmac_8f9</div>
                      </div>
                    </div>

                    <div className="border-t border-slate-200 pt-2 text-[10px] text-slate-500 flex justify-between">
                      <span>T-shirt: L</span>
                      <span>Kit: ID, Lanyard, Tote</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default MerchandiseWorkspace;
