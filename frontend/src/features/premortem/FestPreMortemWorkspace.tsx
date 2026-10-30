import React, { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Play,
  Pause,
  RotateCcw,
  AlertOctagon,
  CheckCircle,
  HelpCircle,
  Clock,
  Zap,
  Bed,
  UtensilsCrossed,
  MapPin,
  Users2,
  Bus,
} from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Badge,
  Button,
  Modal,
  useToast,
} from "../../components/ui";
import {
  HourlyPremortemState,
  SpofItem,
  PreventiveActionItem,
  FestResilienceReport,
} from "./types";
import { api } from "../../api/client";

export const FestPreMortemWorkspace: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  const [currentHourIndex, setCurrentHourIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1); // 1x, 2x, 5x
  const [isMethodologyModalOpen, setIsMethodologyModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"timeline" | "spof" | "preventive">("timeline");

  // 1. Fetch Timeline Scrubber Data
  const { data: timelineData, isLoading: timelineLoading } = useQuery<{
    data: { hours: HourlyPremortemState[]; totalHours: number };
  }>({
    queryKey: ["premortem", "timeline"],
    queryFn: async () => {
      return api.get("/api/v1/premortem/timeline");
    },
  });

  // 2. Fetch SPOF List
  const { data: spofData } = useQuery<{ data: { items: SpofItem[]; total: number } }>({
    queryKey: ["premortem", "spof"],
    queryFn: async () => {
      return api.get("/api/v1/premortem/spof");
    },
  });

  // 3. Fetch Preventive Actions
  const { data: preventiveData } = useQuery<{ data: { items: PreventiveActionItem[]; total: number } }>({
    queryKey: ["premortem", "preventive"],
    queryFn: async () => {
      return api.get("/api/v1/premortem/preventive");
    },
  });

  // 4. Fetch Resilience Report
  const { data: resilienceData } = useQuery<{ data: FestResilienceReport }>({
    queryKey: ["premortem", "resilience"],
    queryFn: async () => {
      return api.get("/api/v1/premortem/resilience");
    },
  });

  const hours: HourlyPremortemState[] = (timelineData as any)?.hours || (timelineData as any)?.data?.hours || [];
  const spofList: SpofItem[] = (spofData as any)?.items || (spofData as any)?.data?.items || [];
  const preventiveList: PreventiveActionItem[] = (preventiveData as any)?.items || (preventiveData as any)?.data?.items || [];
  const resilience: FestResilienceReport | undefined = (resilienceData as any)?.data || resilienceData;

  const currentHour = hours[currentHourIndex] || hours[0];

  // Auto-play timer for scrubber
  useEffect(() => {
    let timer: any = null;
    if (isPlaying && hours.length > 0) {
      const intervalMs = 1000 / playbackSpeed;
      timer = setInterval(() => {
        setCurrentHourIndex((prev) => {
          if (prev >= hours.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, intervalMs);
    }
    return () => clearInterval(timer);
  }, [isPlaying, playbackSpeed, hours.length]);

  // Execute preventive action mutation
  const executePreventiveMutation = useMutation({
    mutationFn: async (id: string) => {
      return api.post(`/api/v1/premortem/preventive/${id}/execute`, {});
    },
    onSuccess: () => {
      addToast({
        type: "success",
        title: "Preventive Action Activated",
        message: "Mitigation buffer logged. Risk resilience score adjusted.",
      });
      queryClient.invalidateQueries({ queryKey: ["premortem", "preventive"] });
      queryClient.invalidateQueries({ queryKey: ["premortem", "resilience"] });
    },
  });

  return (
    <div className="space-y-6" data-testid="premortem-workspace">
      {/* 1. Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white">Fest Pre-Mortem Simulator</h1>
            <Badge variant="solid" status="SUCCESS">
              TIMELINE SCRUBBER
            </Badge>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            72-hour operational replay (Oct 30 – Nov 01) across 6 core festival dimensions. Advance the scrubber to reveal emerging risks before they manifest.
          </p>
        </div>

        {/* Resilience Score Pill */}
        {resilience && (
          <div
            data-testid="resilience-score-pill"
            onClick={() => setIsMethodologyModalOpen(true)}
            className="flex items-center gap-3 bg-slate-900 border border-slate-800 p-2.5 rounded-xl cursor-pointer hover:border-indigo-500/50 transition-all shadow-sm"
          >
            <div className="flex flex-col text-right">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                Fest Resilience
              </span>
              <span className="text-xs font-semibold text-emerald-400">
                {resilience.grade}
              </span>
            </div>
            <div className="w-10 h-10 rounded-lg bg-emerald-950/80 border border-emerald-500 flex items-center justify-center text-lg font-black text-emerald-300">
              {resilience.overallScore}
            </div>
            <HelpCircle className="w-4 h-4 text-slate-500 hover:text-white" />
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800">
        <button
          data-testid="tab-scrubber"
          onClick={() => setActiveTab("timeline")}
          className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-all ${
            activeTab === "timeline"
              ? "border-indigo-500 text-white"
              : "border-transparent text-slate-400 hover:text-white"
          }`}
        >
          Timeline Scrubber (72 Hours)
        </button>
        <button
          data-testid="tab-spof"
          onClick={() => setActiveTab("spof")}
          className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-all ${
            activeTab === "spof"
              ? "border-indigo-500 text-white"
              : "border-transparent text-slate-400 hover:text-white"
          }`}
        >
          Single Points of Failure (SPOFs) ({spofList.length})
        </button>
        <button
          data-testid="tab-preventive"
          onClick={() => setActiveTab("preventive")}
          className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-all ${
            activeTab === "preventive"
              ? "border-indigo-500 text-white"
              : "border-transparent text-slate-400 hover:text-white"
          }`}
        >
          Preventive Actions Queue ({preventiveList.length})
        </button>
      </div>

      {timelineLoading || !currentHour ? (
        <div className="p-12 text-center text-slate-400">Loading festival timeline replay...</div>
      ) : activeTab === "timeline" ? (
        <div className="space-y-6">
          {/* 2. Interactive Timeline Scrubber Control Bar */}
          <Card className="border-indigo-500/30 bg-slate-900/90" data-testid="timeline-scrubber-card">
            <CardContent className="p-5 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-indigo-950/80 border border-indigo-700/60">
                    <Clock className="w-5 h-5 text-indigo-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-base font-bold text-white font-mono" data-testid="scrubbed-time-label">
                        {currentHour.timeLabel} UTC
                      </span>
                      <Badge variant="outline">{currentHour.festDay}</Badge>
                    </div>
                    <div className="text-xs text-slate-400">
                      Hour {currentHour.hourIndex + 1} of 72 · Aarohan Fest Replay
                    </div>
                  </div>
                </div>

                {/* Scrubber Playback Controls */}
                <div className="flex items-center gap-2">
                  <Button
                    data-testid="reset-scrubber-btn"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setIsPlaying(false);
                      setCurrentHourIndex(0);
                    }}
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                  </Button>

                  <Button
                    data-testid="play-pause-btn"
                    variant="primary"
                    size="sm"
                    onClick={() => setIsPlaying(!isPlaying)}
                  >
                    {isPlaying ? (
                      <>
                        <Pause className="w-3.5 h-3.5 mr-1" /> Pause
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5 mr-1" /> Play Replay
                      </>
                    )}
                  </Button>

                  {/* Speed buttons */}
                  <div className="flex items-center rounded-lg border border-slate-800 bg-slate-950 p-0.5 text-xs">
                    {[1, 2, 5].map((spd) => (
                      <button
                        key={spd}
                        onClick={() => setPlaybackSpeed(spd)}
                        className={`px-2 py-1 rounded text-[11px] font-mono ${
                          playbackSpeed === spd
                            ? "bg-indigo-600 text-white font-bold"
                            : "text-slate-400 hover:text-white"
                        }`}
                      >
                        {spd}x
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Slider Input */}
              <div className="space-y-1.5 pt-2">
                <input
                  data-testid="timeline-slider"
                  type="range"
                  min={0}
                  max={hours.length - 1}
                  value={currentHourIndex}
                  onChange={(e) => {
                    setIsPlaying(false);
                    setCurrentHourIndex(Number(e.target.value));
                  }}
                  className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                />

                <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                  <span>Oct 30 06:00 (Arrivals)</span>
                  <span>Oct 31 12:00 (Day 2 Peak)</span>
                  <span>Nov 01 22:00 (Valedictory)</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 3. Critical Risks Emerging at this Scrubbed Hour */}
          <div data-testid="critical-risks-panel">
            <div className="flex items-center gap-2 mb-3">
              <AlertOctagon className="w-4 h-4 text-rose-400 animate-pulse" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Critical Risks Manifesting at this Hour ({currentHour.activeCriticalRisks.length})
              </h3>
            </div>

            {currentHour.activeCriticalRisks.length === 0 ? (
              <div
                data-testid="no-risks-banner"
                className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 text-xs text-slate-400 flex items-center gap-2"
              >
                <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>No active critical risk thresholds breached at hour {currentHour.timeLabel}.</span>
              </div>
            ) : (
              <div className="space-y-3">
                {currentHour.activeCriticalRisks.map((risk) => (
                  <div
                    key={risk.id}
                    data-testid={`active-risk-${risk.id}`}
                    className="p-4 rounded-xl border border-rose-500/50 bg-rose-950/20 text-xs space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant="solid" status="REJECTED">
                          {risk.severity}
                        </Badge>
                        <span className="font-bold text-white text-sm">{risk.title}</span>
                      </div>
                      <span className="font-mono text-rose-300 font-semibold">
                        {risk.peopleAffected} people at risk
                      </span>
                    </div>

                    <p className="text-slate-300 leading-relaxed">{risk.explanation}</p>

                    <div className="pt-2 border-t border-rose-900/40 flex items-center justify-between">
                      <span className="text-amber-300 font-medium">
                        Preventive Recommendation: {risk.preventiveAction}
                      </span>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => navigate(risk.route)}
                        className="text-xs"
                      >
                        Mitigate Now →
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 4. Six Operational Panels Driven Dynamically by Scrubbed Hour */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="operational-panels-grid">
            {/* Panel 1: Bed Occupancy */}
            <Card className="border-slate-800 bg-slate-900/80" data-testid="panel-bed-occupancy">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
                    <Bed className="w-4 h-4 text-indigo-400" />
                    <span>Bed Occupancy</span>
                  </div>
                  <Badge
                    variant="outline"
                    status={currentHour.bedOccupancy.unplacedCount > 0 ? "REJECTED" : "SUCCESS"}
                  >
                    {currentHour.bedOccupancy.occupancyPct}% Occupied
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-2 text-xs font-mono">
                <div className="flex justify-between text-slate-400">
                  <span>Campus Beds:</span>
                  <span className="text-white font-bold">{currentHour.bedOccupancy.campusOccupied} / 710</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>External Beds:</span>
                  <span className="text-white font-bold">{currentHour.bedOccupancy.externalOccupied} / 740</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Available Buffer:</span>
                  <span className="text-emerald-400 font-bold">{currentHour.bedOccupancy.totalAvailable} beds</span>
                </div>
                {currentHour.bedOccupancy.unplacedCount > 0 && (
                  <div className="p-2 rounded bg-rose-950/60 border border-rose-800 text-rose-300 text-[11px] font-sans">
                    Critical: {currentHour.bedOccupancy.unplacedCount} participants unplaced at this hour!
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Panel 2: Food Demand vs Vendor Capacity */}
            <Card className="border-slate-800 bg-slate-900/80" data-testid="panel-food-demand">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
                    <UtensilsCrossed className="w-4 h-4 text-amber-400" />
                    <span>Food Ops ({currentHour.foodDemand.activeSlotName})</span>
                  </div>
                  <Badge
                    variant="outline"
                    status={currentHour.foodDemand.deficit > 0 ? "REJECTED" : "SUCCESS"}
                  >
                    {currentHour.foodDemand.deficit > 0 ? "DEFICIT" : "NOMINAL"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-2 text-xs font-mono">
                <div className="flex justify-between text-slate-400">
                  <span>Slot Demand:</span>
                  <span className="text-white font-bold">{currentHour.foodDemand.confirmedDemand} meals</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Vendor Capacity:</span>
                  <span className="text-white font-bold">{currentHour.foodDemand.vendorCapacity} meals</span>
                </div>
                {currentHour.foodDemand.specialDietaryGap > 0 ? (
                  <div className="p-2 rounded bg-rose-950/60 border border-rose-800 text-rose-300 text-[11px] font-sans">
                    Dietary Gap: {currentHour.foodDemand.specialDietaryGap} Jain/Vegan packs unassigned!
                  </div>
                ) : (
                  <div className="text-emerald-400 text-[11px] font-sans pt-1">
                    ✓ All dietary requirements covered
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Panel 3: Venue Utilisation */}
            <Card className="border-slate-800 bg-slate-900/80" data-testid="panel-venue-utilisation">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
                    <MapPin className="w-4 h-4 text-purple-400" />
                    <span>Venue Utilisation</span>
                  </div>
                  <Badge variant="outline">{currentHour.venueUtilisation.overallPct}% Utilised</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-2 text-xs font-mono">
                <div className="flex justify-between text-slate-400">
                  <span>Active Venues:</span>
                  <span className="text-white font-bold">
                    {currentHour.venueUtilisation.activeVenuesCount} of {currentHour.venueUtilisation.totalVenues}
                  </span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Peak Load Venue:</span>
                  <span className="text-indigo-300 font-sans truncate">{currentHour.venueUtilisation.peakVenue}</span>
                </div>
              </CardContent>
            </Card>

            {/* Panel 4: Equipment Demand */}
            <Card className="border-slate-800 bg-slate-900/80" data-testid="panel-equipment-demand">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
                    <Zap className="w-4 h-4 text-amber-400" />
                    <span>Equipment & Power</span>
                  </div>
                  <Badge
                    variant="outline"
                    status={currentHour.equipmentDemand.criticalShortageCount > 0 ? "REJECTED" : "SUCCESS"}
                  >
                    {currentHour.equipmentDemand.criticalShortageCount > 0 ? "SHORTAGE" : "READY"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-2 text-xs font-mono">
                <div className="flex justify-between text-slate-400">
                  <span>Audio Consoles:</span>
                  <span className="text-white font-bold">{currentHour.equipmentDemand.audioConsolesInUse} in use</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Projectors Active:</span>
                  <span className="text-white font-bold">{currentHour.equipmentDemand.projectorsInUse} active</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Power Generators:</span>
                  <span className="text-white font-bold">{currentHour.equipmentDemand.powerGeneratorsInUse} / 3</span>
                </div>
              </CardContent>
            </Card>

            {/* Panel 5: Volunteer Coverage */}
            <Card className="border-slate-800 bg-slate-900/80" data-testid="panel-volunteer-coverage">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
                    <Users2 className="w-4 h-4 text-emerald-400" />
                    <span>Volunteer Coverage</span>
                  </div>
                  <Badge
                    variant="outline"
                    status={currentHour.volunteerCoverage.uncoveredSlots > 0 ? "PENDING" : "SUCCESS"}
                  >
                    {currentHour.volunteerCoverage.uncoveredSlots > 0
                      ? `${currentHour.volunteerCoverage.uncoveredSlots} GAPS`
                      : "COVERED"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-2 text-xs font-mono">
                <div className="flex justify-between text-slate-400">
                  <span>Staff on Shift:</span>
                  <span className="text-white font-bold">
                    {currentHour.volunteerCoverage.onShiftCount} / {currentHour.volunteerCoverage.demandCount}
                  </span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Overloaded Staff:</span>
                  <span className="text-amber-400 font-bold">{currentHour.volunteerCoverage.overloadedCount}</span>
                </div>
              </CardContent>
            </Card>

            {/* Panel 6: Transportation */}
            <Card className="border-slate-800 bg-slate-900/80" data-testid="panel-transport-demand">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
                    <Bus className="w-4 h-4 text-sky-400" />
                    <span>Shuttle Transit</span>
                  </div>
                  <Badge
                    variant="outline"
                    status={currentHour.transport.deficitSeats > 0 ? "REJECTED" : "SUCCESS"}
                  >
                    {currentHour.transport.deficitSeats > 0
                      ? `-${currentHour.transport.deficitSeats} SEATS`
                      : "BALANCED"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-2 text-xs font-mono">
                <div className="flex justify-between text-slate-400">
                  <span>Shuttle Demand:</span>
                  <span className="text-white font-bold">{currentHour.transport.shuttleDemandSeats} seats</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Fleet Capacity:</span>
                  <span className="text-white font-bold">{currentHour.transport.confirmedCapacitySeats} seats</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Night Escorts:</span>
                  <span className="text-emerald-400 font-bold">{currentHour.transport.activeEscorts} active</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      ) : activeTab === "spof" ? (
        /* SPOF List */
        <div className="space-y-4" data-testid="spof-list-view">
          <div className="text-xs text-slate-400">
            Identified Single Points of Failure across Aarohan festival infrastructure. Any failure in these assets triggers immediate cascade disruptions.
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {spofList.map((spof) => (
              <Card key={spof.id} className="border-slate-800 bg-slate-900/80" data-testid={`spof-card-${spof.id}`}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <Badge
                      variant="solid"
                      status={spof.resilienceTier === "CRITICAL" ? "REJECTED" : "PENDING"}
                    >
                      {spof.resilienceTier} SPOF
                    </Badge>
                    <span className="text-xs text-rose-400 font-mono font-bold">
                      {spof.peopleAtRisk} People At Risk
                    </span>
                  </div>
                  <CardTitle className="text-base text-white mt-1">{spof.name}</CardTitle>
                  <CardDescription className="text-xs text-indigo-300 font-mono">
                    {spof.component}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 text-xs">
                  <div>
                    <span className="text-slate-400 font-semibold">Vulnerability: </span>
                    <span className="text-slate-300">{spof.vulnerability}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 font-semibold">Failure Impact: </span>
                    <span className="text-rose-300">{spof.failureImpact}</span>
                  </div>
                  <div className="p-2.5 rounded bg-slate-800/60 border border-slate-700/60 text-emerald-300 flex items-center justify-between">
                    <span>Mitigation: {spof.recommendedMitigation}</span>
                    {spof.mitigationRoute && (
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => navigate(spof.mitigationRoute!)}
                        className="text-xs ml-2 shrink-0"
                      >
                        Action →
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ) : (
        /* Preventive Actions Queue */
        <div className="space-y-4" data-testid="preventive-actions-view">
          <div className="text-xs text-slate-400">
            Pre-authorized preventive measures to eliminate SPOFs before Day 2 prime events.
          </div>

          <div className="space-y-3">
            {preventiveList.map((action) => (
              <div
                key={action.id}
                data-testid={`preventive-item-${action.id}`}
                className="p-4 rounded-xl border border-slate-800 bg-slate-900/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{action.category}</Badge>
                    <span className="font-bold text-white text-sm">{action.title}</span>
                    <Badge
                      variant="solid"
                      status={action.status === "EXECUTED" ? "SUCCESS" : "PENDING"}
                    >
                      {action.status}
                    </Badge>
                  </div>
                  <div className="text-slate-400">
                    Projected Risk Reduction:{" "}
                    <strong className="text-emerald-400">+{action.projectedRiskReductionPct}%</strong> · Urgency:{" "}
                    {action.urgency}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {action.status !== "EXECUTED" ? (
                    <Button
                      data-testid={`execute-action-btn-${action.id}`}
                      variant="primary"
                      size="sm"
                      onClick={() => executePreventiveMutation.mutate(action.id)}
                    >
                      {action.actionLabel}
                    </Button>
                  ) : (
                    <span className="text-emerald-400 flex items-center gap-1 text-xs font-semibold">
                      <CheckCircle className="w-4 h-4" /> Activated
                    </span>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate(action.actionRoute)}
                  >
                    View Domain →
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Methodology Modal */}
      {isMethodologyModalOpen && resilience && (
        <Modal
          isOpen={true}
          onClose={() => setIsMethodologyModalOpen(false)}
          title={resilience.methodology.title}
          size="lg"
        >
          <div className="space-y-4 text-xs" data-testid="methodology-modal">
            <p className="text-slate-300 leading-relaxed">{resilience.methodology.description}</p>

            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 font-mono text-emerald-300">
              {resilience.methodology.formula}
            </div>

            <div className="text-slate-400">
              <strong>Constraint Ladder Rule: </strong> {resilience.methodology.ladderRule}
            </div>

            <div className="space-y-2 pt-2 border-t border-slate-800">
              <h4 className="font-semibold text-white">Component Weights & Resilience Status:</h4>
              <div className="space-y-1.5 font-mono">
                {resilience.components.map((comp) => (
                  <div
                    key={comp.component}
                    className="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800"
                  >
                    <span className="font-sans font-medium text-slate-300">{comp.component}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-slate-500">Weight: {comp.weight * 100}%</span>
                      <span
                        className={`font-bold ${
                          comp.score >= 80
                            ? "text-emerald-400"
                            : comp.score >= 70
                            ? "text-amber-400"
                            : "text-rose-400"
                        }`}
                      >
                        {comp.score}/100
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button variant="outline" size="sm" onClick={() => setIsMethodologyModalOpen(false)}>
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default FestPreMortemWorkspace;
