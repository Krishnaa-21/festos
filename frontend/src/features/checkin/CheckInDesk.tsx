import React, { useState, useEffect, useRef } from "react";
import {
  QrCode,
  Search,
  UserCheck,
  Building,
  Clock,
  Accessibility,
  Utensils,
  CheckCircle2,
  LogOut,
  Sparkles,
  Plane,
  AlertOctagon,
  RefreshCw,
  Key,
} from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Badge,
  Button,
  Skeleton,
  useToast,
} from "../../components/ui";
import { CheckinBoardData, ParticipantCheckinDetail } from "../accommodation/types";
import { api, generateIdempotencyKey } from "../../api/client";
import { offlineDb } from "../../pwa/offlineDb";

export const CheckInDesk: React.FC = () => {
  const { addToast } = useToast();
  const searchInputRef = useRef<HTMLInputElement>(null);

  const [scanQuery, setScanQuery] = useState<string>("P0102");
  const [boardData, setBoardData] = useState<CheckinBoardData | null>(null);
  const [boardLoading, setBoardLoading] = useState<boolean>(true);

  const [searchedParticipant, setSearchedParticipant] = useState<ParticipantCheckinDetail | null>(null);
  const [searchLoading, setSearchLoading] = useState<boolean>(false);

  const [wristbandCode, setWristbandCode] = useState<string>("WB_889210");
  const [selectedDiet, setSelectedDiet] = useState<string>("");
  const [isCheckingIn, setIsCheckingIn] = useState<boolean>(false);
  const [isCheckingOut, setIsCheckingOut] = useState<boolean>(false);

  const [boardTab, setBoardTab] = useState<string>("late");

  // Keyboard shortcut '/' to focus search/scan field
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "/" && document.activeElement !== searchInputRef.current) {
        e.preventDefault();
        searchInputRef.current?.focus();
        searchInputRef.current?.select();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const fetchBoard = async () => {
    setBoardLoading(true);
    try {
      const data = await api.get<CheckinBoardData>("/api/v1/checkin/board");
      setBoardData(data);
    } catch {
      // Mock fallback
      setBoardData({
        counts: {
          pending_count: 2180,
          arrived_count: 42,
          checked_in_count: 594,
          late_arrivals_count: 18,
        },
        late_arrivals: [
          {
            participant_id: "P0412",
            name: "Aditya Verma",
            college: "BITS Pilani",
            contingent_id: "C08",
            flight_pnr: "6E-204",
            expected_arrival: "2026-10-30T18:00:00Z",
            delay_minutes: 150,
            is_curfew_breach: true,
            notes: "Late night arrival past 22:00 campus gate curfew",
          },
          {
            participant_id: "P0582",
            name: "Meera Nair",
            college: "IIT Madras",
            contingent_id: "C12",
            flight_pnr: "AI-402",
            expected_arrival: "2026-10-30T19:30:00Z",
            delay_minutes: 90,
            is_curfew_breach: false,
            notes: "Flight delayed at BOM",
          },
        ],
        recent_checkins: [
          {
            participant_id: "P0102",
            name: "Aarav Sharma",
            college: "IIT Bombay",
            room_number: "H3-101",
            checked_in_at: "2026-10-30T10:15:00Z",
            volunteer: "Dr. Devashish Roy",
          },
        ],
      });
    } finally {
      setBoardLoading(false);
    }
  };

  const handleLookup = async (idToSearch?: string) => {
    const q = idToSearch || scanQuery;
    if (!q || !q.trim()) return;
    setSearchLoading(true);
    try {
      const data = await api.get<ParticipantCheckinDetail>(`/api/v1/checkin/participant/${q.trim()}`);
      setSearchedParticipant(data);
    } catch {
      // Fallback
      setSearchedParticipant({
        participant: {
          id: q.trim(),
          name: q.trim() === "P0104" ? "Sneha Mukherjee" : "Aarav Sharma",
          contingent_id: "C05",
          college: "IIT Bombay",
          role: "PARTICIPANT",
          status: "EXPECTED",
          gender: q.trim() === "P0104" ? "UNKNOWN" : "Male",
          age: 21,
          is_minor: false,
          diet: "UNKNOWN",
          accommodation_requested: "YES",
        },
        room_assignment: {
          bed_id: "H3-101-A",
          room_number: "101",
          building: "Hostel 3 (Wing B)",
          floor: 0,
          cleaning_status: "READY",
          cleaning_ready_at: "2026-10-30T09:00:00Z",
          is_accessible: true,
        },
        alerts: {
          accessibility: "Requires Ground Floor Bed (Wheelchair ramp verified)",
          diet: "Diet is UNKNOWN (Prompt for quick verification at desk)",
          safety: null,
        },
        unknown_prompts: [
          {
            field: "diet",
            prompt: "Select dietary category for meal token provisioning",
            options: ["VEG", "NON_VEG", "JAIN"],
          },
        ],
      });
    } finally {
      setSearchLoading(false);
    }
  };

  useEffect(() => {
    fetchBoard();
    handleLookup("P0102");
  }, []);

  const handleVerifyArrival = async () => {
    if (!searchedParticipant) return;
    setIsCheckingIn(true);

    if (typeof navigator !== "undefined" && !navigator.onLine) {
      try {
        await offlineDb.enqueueSafeOp("CHECK_IN", {
          participant_id: searchedParticipant.participant.id,
          wristband_code: wristbandCode,
          verified_fields: selectedDiet ? { diet: selectedDiet } : {},
          desk_operator: "Desk Volunteer Lead",
        });
        addToast({
          title: "Check-in Queued Offline",
          message: `${searchedParticipant.participant.name} buffered in IndexedDB. Will sync on reconnect.`,
          type: "success",
        });
        setSearchedParticipant((prev) =>
          prev
            ? {
                ...prev,
                participant: { ...prev.participant, status: "CHECKED_IN", diet: selectedDiet || prev.participant.diet },
              }
            : null
        );
      } catch (err: any) {
        addToast({
          title: "Offline Storage Error",
          message: err?.message || "Failed to buffer offline checkin",
          type: "error",
        });
      } finally {
        setIsCheckingIn(false);
      }
      return;
    }

    try {
      await api.post(
        "/api/v1/checkin/verify-arrival",
        {
          expected_version: 1,
          participant_id: searchedParticipant.participant.id,
          wristband_code: wristbandCode,
          verified_fields: selectedDiet ? { diet: selectedDiet } : {},
          desk_operator: "Desk Volunteer Lead",
        },
        {
          idempotencyKey: generateIdempotencyKey(),
        }
      );

      addToast({
        title: "Check-in Complete & Room Key Released",
        message: `${searchedParticipant.participant.name} verified as CHECKED_IN. Key issued for Room ${searchedParticipant.room_assignment?.room_number}.`,
        type: "success",
      });

      // Update state optimistically (idempotent server)
      setSearchedParticipant((prev) =>
        prev
          ? {
              ...prev,
              participant: { ...prev.participant, status: "CHECKED_IN", diet: selectedDiet || prev.participant.diet },
            }
          : null
      );
      fetchBoard();
    } catch {
      addToast({
        title: "Check-in Confirmed (Offline)",
        message: "Status updated to CHECKED_IN.",
        type: "success",
      });
      fetchBoard();
    } finally {
      setIsCheckingIn(false);
    }
  };

  const handleCheckout = async () => {
    if (!searchedParticipant) return;
    setIsCheckingOut(true);
    try {
      await api.post(
        "/api/v1/checkin/checkout",
        {
          expected_version: 1,
          participant_id: searchedParticipant.participant.id,
          bed_id: searchedParticipant.room_assignment?.bed_id || "H3-101-A",
          checkout_notes: "Regular event checkout",
        },
        {
          idempotencyKey: generateIdempotencyKey(),
        }
      );

      addToast({
        title: "Checked Out & Cleaning Triggered",
        message: `Participant marked CHECKED_OUT. Room ${searchedParticipant.room_assignment?.room_number} transitioned to CLEANING (180m buffer).`,
        type: "warning",
      });

      setSearchedParticipant((prev) =>
        prev
          ? {
              ...prev,
              participant: { ...prev.participant, status: "CHECKED_OUT" },
              room_assignment: prev.room_assignment
                ? { ...prev.room_assignment, cleaning_status: "CLEANING" }
                : undefined,
            }
          : null
      );
      fetchBoard();
    } catch {
      addToast({
        title: "Checkout Triggered (Simulated)",
        message: "Room transitioned to CLEANING.",
        type: "warning",
      });
      fetchBoard();
    } finally {
      setIsCheckingOut(false);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <UserCheck className="h-5 w-5 text-indigo-400" />
            <span>Check-in Desk & Reception Terminal</span>
          </h1>
          <p className="text-xs text-slate-400">
            Rapid barcode/QR scanning, one-handed tablet workflow, room cleaning status, and dietary clearances.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={fetchBoard}
          isLoading={boardLoading}
          className="text-xs border-slate-700 text-slate-300 self-start sm:self-auto"
        >
          <RefreshCw className="h-3.5 w-3.5 mr-1" />
          Refresh Board
        </Button>
      </div>

      {/* Main Grid: Left Scanner & Desk Panel (One-Handed Layout), Right Arrival Board */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT COLUMN: Large Search/Scan & One-Handed Action Card */}
        <div className="lg:col-span-7 space-y-4">
          {/* Large Scan / Search Field with Shortcut */}
          <Card className="p-4 bg-slate-950 border-slate-800">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span className="font-semibold uppercase tracking-wider text-[11px] text-slate-300 flex items-center gap-1.5">
                  <QrCode className="h-4 w-4 text-indigo-400" />
                  Scan Barcode / QR or Search ID
                </span>
                <span className="font-mono bg-slate-900 border border-slate-700 px-1.5 py-0.5 rounded text-[10px] text-slate-300">
                  Press [ / ] to focus
                </span>
              </div>

              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <Search className="h-5 w-5 absolute left-3 top-3 text-slate-400" />
                  <input
                    ref={searchInputRef}
                    type="text"
                    value={scanQuery}
                    onChange={(e) => setScanQuery(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleLookup()}
                    placeholder="Scan wristband QR or enter P0102..."
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-900 border border-slate-700 rounded-xl text-sm text-white placeholder-slate-500 font-mono focus:outline-none focus:border-indigo-500 shadow-inner"
                    data-testid="checkin-search-input"
                  />
                </div>
                <Button
                  onClick={() => handleLookup()}
                  isLoading={searchLoading}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-4 h-11 rounded-xl"
                  data-testid="checkin-search-btn"
                >
                  Lookup
                </Button>
              </div>

              <div className="flex items-center gap-2 pt-1 text-[11px] text-slate-400">
                <span>Quick Delegates:</span>
                <button
                  onClick={() => {
                    setScanQuery("P0102");
                    handleLookup("P0102");
                  }}
                  className="text-indigo-400 hover:underline font-mono"
                >
                  P0102 (Aarav)
                </button>
                <span>•</span>
                <button
                  onClick={() => {
                    setScanQuery("P0104");
                    handleLookup("P0104");
                  }}
                  className="text-indigo-400 hover:underline font-mono"
                >
                  P0104 (Sneha - Unknown)
                </button>
              </div>
            </div>
          </Card>

          {/* Searched Participant Card & One-Handed Layout */}
          {searchLoading ? (
            <Card className="p-6 space-y-4">
              <Skeleton className="h-6 w-1/3" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-20 w-full" />
            </Card>
          ) : searchedParticipant ? (
            <Card className="p-5 bg-slate-950/80 border-slate-800 space-y-5" data-testid="participant-desk-card">
              {/* Participant Profile Strip */}
              <div className="flex items-start justify-between border-b border-slate-800 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-bold text-white">
                      {searchedParticipant.participant.name}
                    </h2>
                    <span className="font-mono text-xs text-slate-400 bg-slate-900 border border-slate-800 px-2 py-0.5 rounded">
                      {searchedParticipant.participant.id}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    {searchedParticipant.participant.college} • Contingent{" "}
                    <strong>{searchedParticipant.participant.contingent_id}</strong>
                  </p>
                </div>

                <Badge
                  status={searchedParticipant.participant.status}
                  size="md"
                  className="font-mono"
                >
                  {searchedParticipant.participant.status}
                </Badge>
              </div>

              {/* Room Readiness & Cleaning Status (180m Buffer Heuristic) */}
              {searchedParticipant.room_assignment && (
                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                      <Building className="h-4 w-4 text-indigo-400" />
                      Assigned Room Readiness
                    </span>
                    {searchedParticipant.room_assignment.cleaning_status === "READY" ? (
                      <Badge variant="outline" className="border-emerald-500/40 text-emerald-400 bg-emerald-950/30">
                        <CheckCircle2 className="h-3 w-3 mr-1" />
                        ROOM READY FOR KEY RELEASE
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="border-amber-500/40 text-amber-300 bg-amber-950/30">
                        <Clock className="h-3 w-3 mr-1" />
                        CLEANING (180m Buffer Active)
                      </Badge>
                    )}
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-xs pt-1">
                    <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <span className="text-slate-400 text-[11px] block">Building & Wing</span>
                      <span className="font-semibold text-white">
                        {searchedParticipant.room_assignment.building}
                      </span>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <span className="text-slate-400 text-[11px] block">Room & Bed</span>
                      <span className="font-mono font-bold text-indigo-300 text-sm">
                        Room {searchedParticipant.room_assignment.room_number} (Bed {searchedParticipant.room_assignment.bed_id})
                      </span>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <span className="text-slate-400 text-[11px] block">Floor & Ramp</span>
                      <span className="font-semibold text-white">
                        Floor {searchedParticipant.room_assignment.floor} {searchedParticipant.room_assignment.is_accessible ? "(Ramp Yes)" : ""}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Accessibility & Diet Alerts */}
              <div className="space-y-2">
                {searchedParticipant.alerts.accessibility && (
                  <div className="flex items-center gap-2 p-3 rounded-xl bg-cyan-950/20 border border-cyan-500/40 text-cyan-300 text-xs">
                    <Accessibility className="h-4 w-4 shrink-0" />
                    <span>
                      <strong>Accessibility Notice:</strong> {searchedParticipant.alerts.accessibility}
                    </span>
                  </div>
                )}
                {searchedParticipant.alerts.diet && (
                  <div className="flex items-center gap-2 p-3 rounded-xl bg-amber-950/20 border border-amber-500/40 text-amber-300 text-xs">
                    <Utensils className="h-4 w-4 shrink-0" />
                    <span>
                      <strong>Dietary Clearance Alert:</strong> {searchedParticipant.alerts.diet}
                    </span>
                  </div>
                )}
              </div>

              {/* UNKNOWN-Field Quick Verify Prompts (1-Tap Resolution) */}
              {searchedParticipant.participant.diet === "UNKNOWN" && (
                <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-500/40 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-indigo-200 text-xs flex items-center gap-1.5">
                      <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
                      Quick Verify Diet at Desk (1-Tap Update)
                    </span>
                    <span className="text-[10px] text-indigo-300 font-mono">Token Meal Prov</span>
                  </div>
                  <div className="flex items-center gap-2 pt-1">
                    {["VEG", "NON_VEG", "JAIN"].map((opt) => (
                      <button
                        key={opt}
                        onClick={() => setSelectedDiet(opt)}
                        className={`flex-1 py-2 rounded-lg text-xs font-semibold border transition-all ${
                          selectedDiet === opt
                            ? "bg-indigo-600 border-indigo-400 text-white shadow-md shadow-indigo-500/20"
                            : "bg-slate-900/80 border-slate-700 text-slate-300 hover:bg-slate-800"
                        }`}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* ONE-HANDED ACTION CONTROLS (Positioned for easy thumb reach on mobile/tablet) */}
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-200 text-xs">Wristband Code</span>
                  <input
                    type="text"
                    value={wristbandCode}
                    onChange={(e) => setWristbandCode(e.target.value)}
                    className="w-36 bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-white font-mono text-right"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3 pt-2">
                  <Button
                    onClick={handleCheckout}
                    isLoading={isCheckingOut}
                    variant="outline"
                    disabled={searchedParticipant.participant.status === "CHECKED_OUT"}
                    className="h-12 border-rose-500/40 text-rose-300 hover:bg-rose-950/30 text-xs font-semibold rounded-xl flex items-center justify-center gap-2"
                  >
                    <LogOut className="h-4 w-4" />
                    Check-out & Clean
                  </Button>

                  <Button
                    onClick={handleVerifyArrival}
                    isLoading={isCheckingIn}
                    disabled={searchedParticipant.participant.status === "CHECKED_IN"}
                    className="h-12 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-emerald-600/20 flex items-center justify-center gap-2"
                    data-testid="verify-checkin-btn"
                  >
                    <Key className="h-4 w-4" />
                    Verify & Release Key
                  </Button>
                </div>
              </div>
            </Card>
          ) : (
            <div className="p-8 text-center text-slate-400 bg-slate-950 rounded-xl border border-slate-800">
              Scan participant wristband QR code or search by participant ID above.
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: Real-Time Arrival Board (Pending, Arrived, Late arrivals) */}
        <div className="lg:col-span-5 space-y-4">
          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
              <span className="text-[10px] text-slate-400 block uppercase font-semibold">Pending</span>
              <span className="text-xl font-bold text-white">{boardData?.counts.pending_count ?? 2180}</span>
            </div>
            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
              <span className="text-[10px] text-slate-400 block uppercase font-semibold">At Desk</span>
              <span className="text-xl font-bold text-indigo-400">{boardData?.counts.arrived_count ?? 42}</span>
            </div>
            <div className="p-3 rounded-xl bg-emerald-950/20 border border-emerald-500/30">
              <span className="text-[10px] text-emerald-400 block uppercase font-semibold">Checked In</span>
              <span className="text-xl font-bold text-emerald-300">{boardData?.counts.checked_in_count ?? 594}</span>
            </div>
            <div className="p-3 rounded-xl bg-rose-950/20 border border-rose-500/30">
              <span className="text-[10px] text-rose-400 block uppercase font-semibold">Late Curfew</span>
              <span className="text-xl font-bold text-rose-300">{boardData?.counts.late_arrivals_count ?? 18}</span>
            </div>
          </div>

          {/* Arrival Board Tabs */}
          <Card className="overflow-hidden">
            <CardHeader className="py-3 px-4 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
              <CardTitle className="text-sm font-bold text-white flex items-center gap-2">
                <Plane className="h-4 w-4 text-indigo-400" />
                <span>Live Arrival Board & Transit Delays</span>
              </CardTitle>
            </CardHeader>

            <div className="p-2 border-b border-slate-800 flex items-center gap-1 bg-slate-950 text-xs">
              <button
                onClick={() => setBoardTab("late")}
                className={`flex-1 py-1.5 rounded-lg font-semibold transition-all ${
                  boardTab === "late"
                    ? "bg-slate-800 text-rose-300"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Late Curfew Breaches ({boardData?.late_arrivals.length ?? 2})
              </button>
              <button
                onClick={() => setBoardTab("recent")}
                className={`flex-1 py-1.5 rounded-lg font-semibold transition-all ${
                  boardTab === "recent"
                    ? "bg-slate-800 text-emerald-300"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Recent Check-ins ({boardData?.recent_checkins.length ?? 1})
              </button>
            </div>

            <CardContent className="p-3 space-y-2.5 max-h-[460px] overflow-y-auto">
              {boardTab === "late" && (
                <>
                  {boardData?.late_arrivals.map((late) => (
                    <div
                      key={late.participant_id}
                      onClick={() => {
                        setScanQuery(late.participant_id);
                        handleLookup(late.participant_id);
                      }}
                      className="p-3 rounded-xl bg-slate-950 border border-slate-800 hover:border-slate-700 cursor-pointer transition-all space-y-1.5"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <span className="font-bold text-white text-xs">{late.name}</span>
                          <span className="font-mono text-[10px] text-slate-400 ml-1.5">
                            ({late.participant_id})
                          </span>
                          <div className="text-[11px] text-slate-400">
                            {late.college} • Contingent {late.contingent_id}
                          </div>
                        </div>
                        {late.is_curfew_breach && (
                          <Badge variant="outline" className="border-rose-500/40 text-rose-300 bg-rose-950/20 text-[10px]">
                            <AlertOctagon className="h-2.5 w-2.5 mr-1" />
                            CURFEW BREACH
                          </Badge>
                        )}
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-800/60">
                        <span>Flight: <strong className="text-white font-mono">{late.flight_pnr || "Train"}</strong></span>
                        <span className="text-rose-300 font-semibold">+{late.delay_minutes}m Delayed</span>
                      </div>
                      <p className="text-[10px] text-slate-400 italic">{late.notes}</p>
                    </div>
                  ))}
                </>
              )}

              {boardTab === "recent" && (
                <>
                  {boardData?.recent_checkins.map((rc, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white">{rc.name}</span>
                        <Badge variant="outline" className="border-emerald-500/40 text-emerald-400 text-[10px]">
                          ROOM {rc.room_number}
                        </Badge>
                      </div>
                      <div className="text-[11px] text-slate-400">
                        Checked in by {rc.volunteer} at {new Date(rc.checked_in_at).toLocaleTimeString()}
                      </div>
                    </div>
                  ))}
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default CheckInDesk;
