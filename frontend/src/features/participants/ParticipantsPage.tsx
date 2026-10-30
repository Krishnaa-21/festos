import React, { useState, useEffect, useMemo, useRef } from "react";
import {
  Search,
  Download,
  CheckCircle2,
  AlertTriangle,
  Eye,
  Bookmark,
  X,
} from "lucide-react";
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  DataTable,
  Column,
  Badge,
  useToast,
  Skeleton,
  EmptyState,
} from "../../components/ui";
import { api, ApiError } from "../../api/client";
import { Participant360Drawer } from "./Participant360Drawer";

export interface ParticipantListItem {
  id: string;
  canonical_participant_id: string;
  name: string;
  college: string;
  contingent_id: string;
  role: string;
  status: string;
  diet: string;
  housing_preference: string;
  accommodation_requested: "YES" | "NO" | "UNKNOWN";
  gender: string;
  tshirt_size: string;
  arrival_at: string;
}

const DEFAULT_PARTICIPANTS: ParticipantListItem[] = [
  {
    id: "P0102",
    canonical_participant_id: "P0102",
    name: "Aarav Sharma",
    college: "IIT Bombay",
    contingent_id: "C05",
    role: "PARTICIPANT",
    status: "EXPECTED",
    diet: "UNKNOWN",
    housing_preference: "UNKNOWN",
    accommodation_requested: "YES",
    gender: "Male",
    tshirt_size: "L",
    arrival_at: "2026-10-31T08:30:00Z",
  },
  {
    id: "P0103",
    canonical_participant_id: "P0103",
    name: "Rohan Deshmukh",
    college: "IIT Bombay",
    contingent_id: "C05",
    role: "LEADER",
    status: "EXPECTED",
    diet: "VEG",
    housing_preference: "CAMPUS_HOSTEL",
    accommodation_requested: "YES",
    gender: "Male",
    tshirt_size: "XL",
    arrival_at: "2026-10-31T07:00:00Z",
  },
  {
    id: "P0104",
    canonical_participant_id: "P0104",
    name: "Sneha Mukherjee",
    college: "IIT Bombay",
    contingent_id: "C05",
    role: "PARTICIPANT",
    status: "EXPECTED",
    diet: "NON_VEG",
    housing_preference: "UNKNOWN",
    accommodation_requested: "UNKNOWN",
    gender: "Female",
    tshirt_size: "M",
    arrival_at: "2026-10-31T08:30:00Z",
  },
  {
    id: "P0211",
    canonical_participant_id: "P0211",
    name: "Vikram Rathore",
    college: "BITS Pilani",
    contingent_id: "C08",
    role: "PARTICIPANT",
    status: "ARRIVED",
    diet: "JAIN",
    housing_preference: "CAMPUS_HOSTEL",
    accommodation_requested: "YES",
    gender: "Male",
    tshirt_size: "L",
    arrival_at: "2026-10-30T18:00:00Z",
  },
  {
    id: "P0212",
    canonical_participant_id: "P0212",
    name: "Aditi Rao",
    college: "BITS Pilani",
    contingent_id: "C08",
    role: "PARTICIPANT",
    status: "EXPECTED",
    diet: "UNKNOWN",
    housing_preference: "UNKNOWN",
    accommodation_requested: "UNKNOWN",
    gender: "UNKNOWN",
    tshirt_size: "S",
    arrival_at: "2026-10-31T11:00:00Z",
  },
  {
    id: "P0350",
    canonical_participant_id: "P0350",
    name: "Karan Johar",
    college: "IIM Ahmedabad",
    contingent_id: "C12",
    role: "LEADER",
    status: "EXPECTED",
    diet: "VEG",
    housing_preference: "HOTEL_EXTERNAL",
    accommodation_requested: "YES",
    gender: "Male",
    tshirt_size: "XXL",
    arrival_at: "2026-10-31T14:00:00Z",
  },
  {
    id: "P0412",
    canonical_participant_id: "P0412",
    name: "Aditya Verma",
    college: "BITS Pilani",
    contingent_id: "C08",
    role: "PARTICIPANT",
    status: "EXPECTED",
    diet: "NON_VEG",
    housing_preference: "CAMPUS_HOSTEL",
    accommodation_requested: "YES",
    gender: "Male",
    tshirt_size: "M",
    arrival_at: "2026-10-31T09:00:00Z",
  },
  {
    id: "P0515",
    canonical_participant_id: "P0515",
    name: "Ananya Iyer",
    college: "SRCC Delhi",
    contingent_id: "C15",
    role: "ESCORT",
    status: "EXPECTED",
    diet: "VEG",
    housing_preference: "HOTEL_EXTERNAL",
    accommodation_requested: "YES",
    gender: "Female",
    tshirt_size: "L",
    arrival_at: "2026-10-31T06:30:00Z",
  },
];

interface FilterState {
  q: string;
  contingent_id: string;
  status: string;
  event_id: string;
  diet: string;
  accessibility: string;
  unknown_field: string;
  role: string;
}

const INITIAL_FILTERS: FilterState = {
  q: "",
  contingent_id: "ALL",
  status: "ALL",
  event_id: "ALL",
  diet: "ALL",
  accessibility: "ALL",
  unknown_field: "ALL",
  role: "ALL",
};

export const ParticipantsPage: React.FC = () => {
  const { addToast } = useToast();
  const [participants, setParticipants] = useState<ParticipantListItem[]>(DEFAULT_PARTICIPANTS);
  const [loading, setLoading] = useState(false);
  const [apiErrorCode, setApiErrorCode] = useState<string | null>(null);

  // Filters & Search
  const [filters, setFilters] = useState<FilterState>(INITIAL_FILTERS);
  const [savedFilterName, setSavedFilterName] = useState("Custom View");

  // Selection
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // 360 Drawer
  const [drawerParticipantId, setDrawerParticipantId] = useState<string | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Keyboard navigation index
  const [focusedRowIndex, setFocusedRowIndex] = useState<number>(-1);
  const tableContainerRef = useRef<HTMLDivElement>(null);

  // Fetch participants with API integration
  useEffect(() => {
    let isMounted = true;
    const fetchParticipants = async () => {
      setLoading(true);
      setApiErrorCode(null);
      try {
        const queryParams: Record<string, string | number> = {
          page: 1,
          page_size: 50,
        };
        if (filters.q) queryParams.q = filters.q;
        if (filters.contingent_id !== "ALL") queryParams.contingent_id = filters.contingent_id;
        if (filters.status !== "ALL") queryParams.status = filters.status;
        if (filters.event_id !== "ALL") queryParams.event_id = filters.event_id;
        if (filters.diet !== "ALL") queryParams.diet = filters.diet;
        if (filters.unknown_field !== "ALL") queryParams.unknown_field = filters.unknown_field;
        if (filters.role !== "ALL") queryParams.role = filters.role;

        const res = await api.get<any>("/api/v1/participants", { params: queryParams });
        if (isMounted && res?.items) {
          setParticipants(res.items);
        }
      } catch (err: any) {
        if (err instanceof ApiError) {
          setApiErrorCode(err.code);
        } else {
          setApiErrorCode("NETWORK_ERROR");
        }
        // Fallback to client filtered dataset
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchParticipants();
    return () => {
      isMounted = false;
    };
  }, [filters]);

  // Client-side filtering when API is offline or returns fallback
  const filteredParticipants = useMemo(() => {
    return participants.filter((p) => {
      if (filters.q) {
        const q = filters.q.toLowerCase();
        const matchName = p.name.toLowerCase().includes(q);
        const matchCollege = p.college.toLowerCase().includes(q);
        const matchId = p.id.toLowerCase().includes(q);
        if (!matchName && !matchCollege && !matchId) return false;
      }
      if (filters.contingent_id !== "ALL" && p.contingent_id !== filters.contingent_id) return false;
      if (filters.status !== "ALL" && p.status !== filters.status) return false;
      if (filters.diet !== "ALL" && p.diet !== filters.diet) return false;
      if (filters.role !== "ALL" && p.role !== filters.role) return false;
      if (filters.unknown_field !== "ALL") {
        if (filters.unknown_field === "diet" && p.diet !== "UNKNOWN") return false;
        if (filters.unknown_field === "accommodation_requested" && p.accommodation_requested !== "UNKNOWN") return false;
        if (filters.unknown_field === "gender" && p.gender !== "UNKNOWN") return false;
      }
      return true;
    });
  }, [participants, filters]);

  // Bulk Selection Handlers
  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedIds(new Set(filteredParticipants.map((p) => p.id)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const handleSelectRow = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleBulkMarkArrived = () => {
    const count = selectedIds.size;
    setParticipants((prev) =>
      prev.map((p) => (selectedIds.has(p.id) ? { ...p, status: "ARRIVED" } : p))
    );
    setSelectedIds(new Set());
    addToast({
      title: "Bulk Arrival Recorded",
      message: `Successfully transitioned ${count} participants to ARRIVED status.`,
      type: "success",
    });
  };

  const handleBulkExportCSV = () => {
    const selectedRows = filteredParticipants.filter((p) => selectedIds.has(p.id));
    const target = selectedRows.length > 0 ? selectedRows : filteredParticipants;
    const headers = ["ID", "Name", "College", "Contingent", "Role", "Status", "Diet", "Accommodation", "Gender"];
    const rows = target.map((p) => [
      p.id,
      p.name,
      p.college,
      p.contingent_id,
      p.role,
      p.status,
      p.diet,
      p.accommodation_requested,
      p.gender,
    ]);
    const csvContent = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `participants_export_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    addToast({
      title: "Participants Exported",
      message: `Exported ${target.length} participant records to CSV.`,
      type: "info",
    });
  };

  // Row Click opens 360 Drawer
  const handleRowClick = (item: ParticipantListItem) => {
    setDrawerParticipantId(item.id);
    setIsDrawerOpen(true);
  };

  // Keyboard navigation handler
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (filteredParticipants.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setFocusedRowIndex((prev) => Math.min(prev + 1, filteredParticipants.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setFocusedRowIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === "Enter" && focusedRowIndex >= 0 && focusedRowIndex < filteredParticipants.length) {
      e.preventDefault();
      handleRowClick(filteredParticipants[focusedRowIndex]);
    }
  };

  // Saved Filter Presets
  const applyPreset = (preset: "ALL" | "UNKNOWNS" | "C05" | "EXPECTED") => {
    if (preset === "ALL") {
      setFilters(INITIAL_FILTERS);
      setSavedFilterName("All Participants");
    } else if (preset === "UNKNOWNS") {
      setFilters({ ...INITIAL_FILTERS, unknown_field: "diet" });
      setSavedFilterName("Unknown Diet Needs");
    } else if (preset === "C05") {
      setFilters({ ...INITIAL_FILTERS, contingent_id: "C05" });
      setSavedFilterName("IIT Bombay (C05)");
    } else if (preset === "EXPECTED") {
      setFilters({ ...INITIAL_FILTERS, status: "EXPECTED" });
      setSavedFilterName("Pending Arrival Check");
    }
  };

  const columns: Column<ParticipantListItem>[] = [
    {
      key: "id",
      header: (
        <input
          type="checkbox"
          className="rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500"
          checked={
            selectedIds.size > 0 &&
            filteredParticipants.length > 0 &&
            selectedIds.size === filteredParticipants.length
          }
          onChange={handleSelectAll}
          aria-label="Select all rows"
        />
      ),
      width: "48px",
      render: (row) => (
        <input
          type="checkbox"
          className="rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500"
          checked={selectedIds.has(row.id)}
          onClick={(e) => handleSelectRow(row.id, e)}
          onChange={() => {}}
          aria-label={`Select ${row.name}`}
        />
      ),
    },
    {
      key: "name",
      header: "Participant & College",
      sortable: true,
      render: (row) => (
        <div>
          <div className="font-semibold text-white flex items-center gap-1.5">
            <span>{row.name}</span>
            <span className="font-mono text-[10px] text-slate-400">({row.id})</span>
          </div>
          <div className="text-[11px] text-slate-400">{row.college}</div>
        </div>
      ),
    },
    {
      key: "contingent_id",
      header: "Contingent",
      sortable: true,
      render: (row) => (
        <span className="font-mono text-xs font-semibold text-indigo-300 bg-indigo-950/40 px-2 py-0.5 rounded border border-indigo-800/40">
          {row.contingent_id}
        </span>
      ),
    },
    {
      key: "role",
      header: "Role",
      sortable: true,
      render: (row) => (
        <span className="text-xs text-slate-300 font-medium">{row.role}</span>
      ),
    },
    {
      key: "accommodation_requested",
      header: "Housing",
      render: (row) => (
        <Badge triState={row.accommodation_requested} size="sm" />
      ),
    },
    {
      key: "diet",
      header: "Diet Category",
      render: (row) => (
        row.diet === "UNKNOWN" ? (
          <Badge triState="UNKNOWN" size="sm">UNKNOWN</Badge>
        ) : (
          <span className="text-xs font-medium text-emerald-400 bg-emerald-950/30 px-2 py-0.5 rounded border border-emerald-800/40">
            {row.diet}
          </span>
        )
      ),
    },
    {
      key: "status",
      header: "Lifecycle Status",
      sortable: true,
      render: (row) => (
        <Badge status={row.status} size="sm" variant="outline">
          {row.status}
        </Badge>
      ),
    },
    {
      key: "actions",
      header: "360 Profile",
      render: (row) => (
        <Button
          size="sm"
          variant="outline"
          className="h-7 text-xs border-slate-700 hover:bg-slate-800 text-indigo-300"
          onClick={(e) => {
            e.stopPropagation();
            handleRowClick(row);
          }}
          data-testid={`btn-view-360-${row.id}`}
        >
          <Eye className="h-3.5 w-3.5 mr-1" />
          View 360
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6" onKeyDown={handleKeyDown} tabIndex={0} ref={tableContainerRef}>
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            Participant Master Directory
            <Badge variant="outline" className="border-indigo-500/30 text-indigo-300 font-normal">
              2,836 Raw Rosters
            </Badge>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Canonical participant roster with first-class UNKNOWN handling, role-based field masking, and 360 operational drawer.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleBulkExportCSV}
            className="border-slate-700 text-slate-300 hover:bg-slate-800 text-xs"
          >
            <Download className="h-4 w-4 mr-1.5 text-indigo-400" />
            Export Directory CSV
          </Button>
        </div>
      </div>

      {/* API Error Code Notification */}
      {apiErrorCode && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2 text-rose-300">
            <AlertTriangle className="h-4 w-4 text-rose-400 shrink-0" />
            <span>
              API error encountered: <strong className="font-mono text-rose-200">{apiErrorCode}</strong>.
              Rendering cached roster snapshot under offline tolerance mode.
            </span>
          </div>
          <Button
            size="sm"
            variant="ghost"
            className="h-6 text-rose-300 hover:text-white"
            onClick={() => setApiErrorCode(null)}
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      )}

      {/* Saved Filters Chips */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="text-slate-400 flex items-center gap-1 font-medium mr-1">
          <Bookmark className="h-3.5 w-3.5 text-indigo-400" />
          Filter Presets:
        </span>
        <button
          onClick={() => applyPreset("ALL")}
          className={`px-3 py-1 rounded-full border transition-colors ${
            savedFilterName === "All Participants"
              ? "bg-indigo-600 text-white border-indigo-500"
              : "bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700"
          }`}
        >
          All (2,836)
        </button>
        <button
          onClick={() => applyPreset("UNKNOWNS")}
          className={`px-3 py-1 rounded-full border transition-colors ${
            savedFilterName === "Unknown Diet Needs"
              ? "bg-amber-600 text-white border-amber-500"
              : "bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700"
          }`}
        >
          UNKNOWN Diet ({participants.filter((p) => p.diet === "UNKNOWN").length})
        </button>
        <button
          onClick={() => applyPreset("C05")}
          className={`px-3 py-1 rounded-full border transition-colors ${
            savedFilterName === "IIT Bombay (C05)"
              ? "bg-indigo-600 text-white border-indigo-500"
              : "bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700"
          }`}
        >
          Contingent C05
        </button>
        <button
          onClick={() => applyPreset("EXPECTED")}
          className={`px-3 py-1 rounded-full border transition-colors ${
            savedFilterName === "Pending Arrival Check"
              ? "bg-indigo-600 text-white border-indigo-500"
              : "bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700"
          }`}
        >
          Pending Arrival ({participants.filter((p) => p.status === "EXPECTED").length})
        </button>
      </div>

      {/* Multi-Dimensional Filter Bar */}
      <Card>
        <CardContent className="p-4 space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
            {/* Search */}
            <div className="relative">
              <Search className="h-3.5 w-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search name, college, ID..."
                value={filters.q}
                onChange={(e) => setFilters({ ...filters, q: e.target.value })}
                className="w-full pl-8 pr-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-indigo-500"
                data-testid="input-search-participants"
              />
            </div>

            {/* Contingent filter */}
            <div>
              <select
                value={filters.contingent_id}
                onChange={(e) => setFilters({ ...filters, contingent_id: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-300 focus:outline-none"
              >
                <option value="ALL">All Contingents (38)</option>
                <option value="C05">C05 - IIT Bombay</option>
                <option value="C08">C08 - BITS Pilani</option>
                <option value="C12">C12 - IIM Ahmedabad</option>
                <option value="C15">C15 - SRCC Delhi</option>
              </select>
            </div>

            {/* Lifecycle Status */}
            <div>
              <select
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-300 focus:outline-none"
              >
                <option value="ALL">All Lifecycle Statuses</option>
                <option value="EXPECTED">EXPECTED</option>
                <option value="ARRIVED">ARRIVED</option>
                <option value="CHECKED_IN">CHECKED_IN</option>
                <option value="CHECKED_OUT">CHECKED_OUT</option>
                <option value="CANCELLED">CANCELLED</option>
                <option value="NO_SHOW">NO_SHOW</option>
                <option value="MERGED">MERGED</option>
              </select>
            </div>

            {/* Unknown Field filter */}
            <div>
              <select
                value={filters.unknown_field}
                onChange={(e) => setFilters({ ...filters, unknown_field: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-amber-300 focus:outline-none"
              >
                <option value="ALL">Any Field Verification State</option>
                <option value="diet">Filter UNKNOWN Diet</option>
                <option value="accommodation_requested">Filter UNKNOWN Housing</option>
                <option value="gender">Filter UNKNOWN Gender</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs pt-1">
            {/* Diet filter */}
            <div>
              <select
                value={filters.diet}
                onChange={(e) => setFilters({ ...filters, diet: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-300 focus:outline-none"
              >
                <option value="ALL">All Dietary Categories</option>
                <option value="VEG">VEG</option>
                <option value="NON_VEG">NON_VEG</option>
                <option value="JAIN">JAIN</option>
                <option value="UNKNOWN">UNKNOWN</option>
              </select>
            </div>

            {/* Role filter */}
            <div>
              <select
                value={filters.role}
                onChange={(e) => setFilters({ ...filters, role: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-300 focus:outline-none"
              >
                <option value="ALL">All Roles</option>
                <option value="PARTICIPANT">PARTICIPANT</option>
                <option value="LEADER">LEADER</option>
                <option value="ESCORT">ESCORT</option>
                <option value="VOLUNTEER">VOLUNTEER</option>
              </select>
            </div>

            <div className="md:col-span-2 flex items-center justify-end gap-2">
              <Button
                size="sm"
                variant="ghost"
                className="text-xs text-slate-400 hover:text-white"
                onClick={() => setFilters(INITIAL_FILTERS)}
              >
                Reset All Filters
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Floating Bulk Action Bar */}
      {selectedIds.size > 0 && (
        <div className="sticky top-20 z-20 flex items-center justify-between p-3 rounded-xl bg-indigo-950 border border-indigo-700/60 shadow-xl text-xs">
          <div className="flex items-center gap-3 text-indigo-200">
            <span className="font-bold text-white bg-indigo-600 px-2.5 py-0.5 rounded-full text-xs">
              {selectedIds.size}
            </span>
            <span>Participants selected across active filters</span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              className="h-8 bg-emerald-600 hover:bg-emerald-500 text-white text-xs"
              onClick={handleBulkMarkArrived}
            >
              <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
              Mark All Arrived
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-8 border-indigo-700 text-indigo-200 hover:bg-indigo-900 text-xs"
              onClick={handleBulkExportCSV}
            >
              Export Selected
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-8 text-indigo-300 hover:text-white text-xs"
              onClick={() => setSelectedIds(new Set())}
            >
              Deselect All
            </Button>
          </div>
        </div>
      )}

      {/* Participants Table */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base text-white">Participants List</CardTitle>
              <CardDescription className="text-xs">
                Showing {filteredParticipants.length} of {participants.length} matching participants. Press [↓ / ↑] and [Enter] to inspect 360 profile.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-3 py-4">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : filteredParticipants.length === 0 ? (
            <EmptyState
              title="No participants found"
              description="No participant records match the active search term and filter combination."
              action={
                <Button
                  size="sm"
                  variant="outline"
                  className="text-xs"
                  onClick={() => setFilters(INITIAL_FILTERS)}
                >
                  Clear Filters
                </Button>
              }
            />
          ) : (
            <DataTable
              columns={columns}
              data={filteredParticipants}
              total={filteredParticipants.length}
              keyExtractor={(row) => row.id}
              onRowClick={handleRowClick}
            />
          )}
        </CardContent>
      </Card>

      {/* 360 Drawer */}
      <Participant360Drawer
        participantId={drawerParticipantId}
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        onStatusChange={(newStatus) => {
          if (drawerParticipantId) {
            setParticipants((prev) =>
              prev.map((p) =>
                p.id === drawerParticipantId ? { ...p, status: newStatus } : p
              )
            );
          }
        }}
      />
    </div>
  );
};

export default ParticipantsPage;
