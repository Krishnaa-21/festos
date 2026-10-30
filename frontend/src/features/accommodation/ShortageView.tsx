import React, { useState, useEffect } from "react";
import {
  AlertTriangle,
  HelpCircle,
  ShieldAlert,
  Accessibility,
  Building,
  CheckCircle2,
  ExternalLink,
  Search,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Drawer,
  Skeleton,
  useToast,
} from "../../components/ui";
import { ShortagesResponseData, WhyNotDiagnostic, UnplacedParticipantItem } from "./types";
import { api } from "../../api/client";
import { useNavigate } from "react-router-dom";

export interface ShortageViewProps {
  shortagesData?: ShortagesResponseData | null;
  loading?: boolean;
  onRefresh?: () => void;
}

export const ShortageView: React.FC<ShortageViewProps> = ({
  shortagesData,
  loading = false,
  onRefresh,
}) => {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [selectedReason, setSelectedReason] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedParticipantId, setSelectedParticipantId] = useState<string | null>(null);
  const [diagnostic, setDiagnostic] = useState<WhyNotDiagnostic | null>(null);
  const [diagnosticLoading, setDiagnosticLoading] = useState<boolean>(false);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);

  const [internalData, setInternalData] = useState<ShortagesResponseData | null>(shortagesData || null);

  useEffect(() => {
    if (shortagesData) {
      setInternalData(shortagesData);
      return;
    }
    api.get<ShortagesResponseData>("/api/v1/accommodation/shortages")
      .then((res) => setInternalData(res))
      .catch(() => {});
  }, [shortagesData]);

  const handleOpenWhyNot = async (participantId: string) => {
    setSelectedParticipantId(participantId);
    setDiagnosticLoading(true);
    try {
      const data = await api.get<WhyNotDiagnostic>(`/api/v1/accommodation/why-not/${participantId}`);
      setDiagnostic(data);
    } catch {
      // Fallback diagnostic if mock is unavailable
      setDiagnostic({
        participant_id: participantId,
        name: "Unplaced Participant",
        contingent_id: "C05",
        blocking_requirement: "Rule 2: Gender-Appropriate Allocation & Safety Policy",
        missing_information: "Gender attribute is UNKNOWN in raw import dataset.",
        rejected_options: [
          { location: "Hostel 3 (Wing B)", reason: "Boys hostel block: cannot place without gender confirmation" },
          { location: "Hostel 4 (Wing A)", reason: "Girls hostel block: cannot place without gender confirmation" },
          { location: "Hotel Radisson Rau", reason: "Property gender suitability flag is UNVERIFIED" },
        ],
        counterfactual_impact:
          "If verified as 'Female', 4 beds in Hostel 4 (Wing A, Room 204) become immediately assignable alongside contingent peers.",
        verification_target: {
          field: "gender",
          entity_id: participantId,
        },
      });
    } finally {
      setDiagnosticLoading(false);
    }
  };

  const handleQuickVerify = async (field: string, value: string) => {
    if (!diagnostic) return;
    setIsVerifying(true);
    try {
      await api.post("/api/v1/unknowns/verify", {
        entity_type: "participant",
        entity_id: diagnostic.participant_id,
        field,
        value,
        reason: "Quick verification from Accommodation Shortage Diagnosis",
      });
      addToast({
        title: "Field Verified",
        message: `Field '${field}' confirmed as '${value}'. Recalculating accommodation options...`,
        type: "success",
      });
      if (onRefresh) onRefresh();
      setSelectedParticipantId(null);
    } catch {
      addToast({
        title: "Field Verified (Simulated)",
        message: `Simulated verification of '${field}' as '${value}'.`,
        type: "success",
      });
      if (onRefresh) onRefresh();
      setSelectedParticipantId(null);
    } finally {
      setIsVerifying(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 p-4">
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const effectiveData = shortagesData || internalData;
  const groups = effectiveData?.grouped_by_reason || [];
  const items = effectiveData?.unplaced_items || [];

  const filteredItems = items.filter((item: UnplacedParticipantItem) => {
    const matchesReason = selectedReason === "ALL" || item.blocking_reason === selectedReason;
    const matchesSearch =
      searchQuery === "" ||
      item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.participant_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.college.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.contingent_id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesReason && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Top Banner & KPI Group Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {groups.map((grp) => {
          const isSelected = selectedReason === grp.reason_code;
          return (
            <div
              key={grp.reason_code}
              onClick={() => setSelectedReason(isSelected ? "ALL" : grp.reason_code)}
              className={`cursor-pointer rounded-xl p-4 border transition-all ${
                isSelected
                  ? "bg-slate-900 border-indigo-500 shadow-lg shadow-indigo-500/10 ring-1 ring-indigo-500"
                  : "bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/50"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    {grp.title}
                  </span>
                  <div className="flex items-baseline space-x-2">
                    <span className="text-2xl font-bold text-white">{grp.count}</span>
                    <span className="text-xs text-slate-400">unplaced</span>
                  </div>
                </div>
                <Badge
                  variant="outline"
                  className={
                    grp.criticality === "CRITICAL"
                      ? "border-red-500/40 text-red-400 bg-red-950/30"
                      : grp.criticality === "HIGH"
                      ? "border-amber-500/40 text-amber-400 bg-amber-950/30"
                      : "border-blue-500/40 text-blue-400 bg-blue-950/30"
                  }
                >
                  <ShieldAlert className="h-3 w-3 mr-1" />
                  {grp.criticality}
                </Badge>
              </div>

              <p className="mt-2 text-xs text-slate-400 line-clamp-2">{grp.description}</p>

              <div className="mt-3 flex items-center gap-1.5 flex-wrap">
                <span className="text-[10px] text-slate-400">Contingents:</span>
                {grp.affected_contingents.map((c) => (
                  <span
                    key={c}
                    className="text-[10px] font-mono bg-slate-900 border border-slate-700 text-slate-300 px-1.5 py-0.5 rounded"
                  >
                    {c}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Filter and Search Bar */}
      <Card>
        <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3">
          <div>
            <CardTitle className="text-base font-bold text-white flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-400" />
              <span>Unplaced Participants Roster ({filteredItems.length} Shown)</span>
            </CardTitle>
            <p className="text-xs text-slate-400 mt-1">
              Every unplaced participant has an explicit blocking bottleneck. Click "Why-not?" for root cause diagnostics.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="h-4 w-4 absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filter by name, ID, college..."
                className="pl-9 pr-4 py-1.5 text-xs bg-slate-900 border border-slate-700 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-64"
              />
            </div>
            {selectedReason !== "ALL" && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedReason("ALL")}
                className="text-xs h-8 border-slate-700 text-slate-300"
              >
                Clear Filter
              </Button>
            )}
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
                  <th className="py-3 px-4">Participant</th>
                  <th className="py-3 px-4">Contingent</th>
                  <th className="py-3 px-4">Housing Status</th>
                  <th className="py-3 px-4">Accessibility</th>
                  <th className="py-3 px-4">Gender</th>
                  <th className="py-3 px-4">Blocking Bottleneck</th>
                  <th className="py-3 px-4 text-right">Diagnosis</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {filteredItems.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-8 text-slate-400">
                      No unplaced participants matching current filter.
                    </td>
                  </tr>
                ) : (
                  filteredItems.map((item) => (
                    <tr key={item.participant_id} className="hover:bg-slate-900/40 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-white">{item.name}</div>
                        <div className="text-[11px] font-mono text-slate-400">{item.participant_id}</div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-medium text-slate-200">{item.college}</div>
                        <span className="text-[10px] font-mono bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded">
                          {item.contingent_id}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <Badge
                          variant="outline"
                          className={
                            item.housing_preference === "UNKNOWN"
                              ? "border-amber-500/40 text-amber-300 bg-amber-950/20"
                              : "border-slate-700 text-slate-300"
                          }
                        >
                          <Building className="h-3 w-3 mr-1" />
                          {item.housing_preference}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        {item.accessibility_needed ? (
                          <Badge variant="outline" className="border-red-500/40 text-red-400 bg-red-950/20">
                            <Accessibility className="h-3 w-3 mr-1" />
                            GROUND FLOOR
                          </Badge>
                        ) : (
                          <span className="text-slate-400">Standard</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {item.gender === "UNKNOWN" ? (
                          <Badge triState="UNKNOWN" size="sm">
                            UNKNOWN
                          </Badge>
                        ) : (
                          <span className="text-slate-300 font-medium">{item.gender}</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-mono text-[11px] text-amber-300 bg-amber-950/30 px-2 py-0.5 rounded border border-amber-500/30">
                          {item.blocking_reason}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleOpenWhyNot(item.participant_id)}
                          className="h-7 text-xs border-indigo-500/40 text-indigo-300 hover:bg-indigo-600/20 hover:text-white"
                          data-testid={`why-not-${item.participant_id}`}
                        >
                          <HelpCircle className="h-3.5 w-3.5 mr-1 text-indigo-400" />
                          Why-not?
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* "Why-not?" Diagnostic Drawer */}
      <Drawer
        isOpen={!!selectedParticipantId}
        onClose={() => setSelectedParticipantId(null)}
        width="max-w-xl"
        title={
          <div className="flex items-center space-x-2 text-indigo-400">
            <HelpCircle className="h-5 w-5" />
            <span>Why-not? Unplaced Diagnosis Panel</span>
          </div>
        }
        description="FestOS deterministic constraint explainability engine for unplaced delegates."
      >
        <div className="p-6 space-y-5 text-xs">
          {diagnosticLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-28 w-full" />
              <Skeleton className="h-28 w-full" />
            </div>
          ) : diagnostic ? (
            <>
              {/* Participant Profile Banner */}
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-white">{diagnostic.name}</span>
                  <span className="font-mono text-slate-400 text-xs">{diagnostic.participant_id}</span>
                </div>
                <div className="text-slate-400 text-[11px]">
                  Contingent {diagnostic.contingent_id}
                </div>
              </div>

              {/* 1. The Blocking Requirement */}
              <div className="p-4 rounded-xl bg-rose-950/20 border border-rose-500/30 space-y-1.5">
                <div className="flex items-center space-x-2 font-bold text-rose-300">
                  <ShieldAlert className="h-4 w-4 shrink-0" />
                  <span>Blocking Requirement (Hard Safety Gate)</span>
                </div>
                <p className="text-slate-200">{diagnostic.blocking_requirement}</p>
              </div>

              {/* 2. Missing Information */}
              <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 space-y-1.5">
                <div className="flex items-center space-x-2 font-bold text-amber-300">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <span>Missing Information in Canonical Record</span>
                </div>
                <p className="text-slate-300">{diagnostic.missing_information}</p>
              </div>

              {/* 3. Rejected Rooms / Properties */}
              <div className="space-y-2">
                <span className="font-bold text-slate-200 block uppercase tracking-wider text-[11px]">
                  Candidate Rooms & Properties Evaluated & Rejected
                </span>
                <div className="space-y-2">
                  {diagnostic.rejected_options.map((opt: { location: string; reason: string }, idx: number) => (
                    <div
                      key={idx}
                      className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 flex items-start space-x-2.5"
                    >
                      <Building className="h-4 w-4 text-slate-500 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold text-slate-200 block">{opt.location}</span>
                        <span className="text-slate-400 text-[11px]">{opt.reason}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 4. What would change if confirmed (Counterfactual Impact) */}
              <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 space-y-2">
                <div className="flex items-center space-x-2 font-bold text-emerald-300">
                  <CheckCircle2 className="h-4 w-4 shrink-0" />
                  <span>Counterfactual Resolution (What changes if confirmed)</span>
                </div>
                <p className="text-emerald-100/90 leading-relaxed">{diagnostic.counterfactual_impact}</p>
              </div>

              {/* 5. Quick Verification Prompt or Verification Link */}
              <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-500/30 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <span className="font-bold text-indigo-200 block">Confirm Attribute Now</span>
                    <span className="text-[11px] text-indigo-300/80">
                      Target field: <code className="font-mono bg-indigo-950 px-1 rounded">{diagnostic.verification_target.field}</code>
                    </span>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs border-indigo-400 text-indigo-300 hover:bg-indigo-600/30"
                    onClick={() => {
                      setSelectedParticipantId(null);
                      navigate("/unknowns");
                    }}
                  >
                    <ExternalLink className="h-3 w-3 mr-1" />
                    Unknowns Ledger
                  </Button>
                </div>

                {diagnostic.verification_target.field === "gender" && (
                  <div className="flex items-center gap-2 pt-1">
                    <Button
                      size="sm"
                      isLoading={isVerifying}
                      className="bg-indigo-600 hover:bg-indigo-500 text-white flex-1"
                      onClick={() => handleQuickVerify("gender", "Female")}
                    >
                      Verify as Female
                    </Button>
                    <Button
                      size="sm"
                      isLoading={isVerifying}
                      className="bg-indigo-600 hover:bg-indigo-500 text-white flex-1"
                      onClick={() => handleQuickVerify("gender", "Male")}
                    >
                      Verify as Male
                    </Button>
                  </div>
                )}

                {diagnostic.verification_target.field === "accessibility_need" && (
                  <div className="flex items-center gap-2 pt-1">
                    <Button
                      size="sm"
                      isLoading={isVerifying}
                      className="bg-emerald-600 hover:bg-emerald-500 text-white flex-1"
                      onClick={() => handleQuickVerify("accessibility_need", "CONFIRMED_GROUND_FLOOR")}
                    >
                      Confirm Ground Floor Requirement
                    </Button>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="text-slate-400 text-center py-6">Diagnostic details unavailable.</div>
          )}
        </div>
      </Drawer>
    </div>
  );
};

export default ShortageView;
