import React, { useState } from "react";
import {
  Building,
  User,
  CheckCircle2,
  Clock,
  Ban,
  Accessibility,
  AlertCircle,
  Crown,
  MapPin,
  IndianRupee,
  AlertTriangle,
} from "lucide-react";
import { Badge, Card, CardHeader, CardContent } from "../../components/ui";
import { OccupancyData, HostelBlock, Room, Bed, BedStatus } from "./types";

export interface OccupancyMapProps {
  occupancyData?: OccupancyData | null;
  loading?: boolean;
  onSelectBedForAssignment?: (bed: Bed, room: Room, block: HostelBlock) => void;
}

export const OccupancyMap: React.FC<OccupancyMapProps> = ({
  occupancyData,
  loading = false,
  onSelectBedForAssignment,
}) => {
  const [selectedBlockId, setSelectedBlockId] = useState<string>("H3");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [highlightSplits, setHighlightSplits] = useState<boolean>(true);

  if (loading || !occupancyData) {
    return (
      <div className="p-8 text-center text-slate-400">
        <div className="animate-spin h-6 w-6 border-2 border-indigo-500 border-t-transparent rounded-full mx-auto mb-2" />
        Loading Occupancy Matrix...
      </div>
    );
  }

  const { blocks, external_properties } = occupancyData;
  const currentBlock = blocks.find((b) => b.block_id === selectedBlockId) || blocks[0];

  const getBedStatusBadge = (status: BedStatus) => {
    switch (status) {
      case "FREE":
        return (
          <Badge variant="outline" className="border-emerald-500/40 text-emerald-400 bg-emerald-950/30 text-[10px]">
            <CheckCircle2 className="h-2.5 w-2.5 mr-1" />
            FREE
          </Badge>
        );
      case "OCCUPIED":
        return (
          <Badge variant="outline" className="border-indigo-500/40 text-indigo-300 bg-indigo-950/30 text-[10px]">
            <User className="h-2.5 w-2.5 mr-1" />
            OCCUPIED
          </Badge>
        );
      case "CLEANING":
        return (
          <Badge variant="outline" className="border-amber-500/40 text-amber-300 bg-amber-950/30 text-[10px]">
            <Clock className="h-2.5 w-2.5 mr-1" />
            CLEANING
          </Badge>
        );
      case "CLOSED":
        return (
          <Badge variant="outline" className="border-slate-600 text-slate-400 bg-slate-900 text-[10px]">
            <Ban className="h-2.5 w-2.5 mr-1" />
            CLOSED
          </Badge>
        );
      case "ACCESSIBLE":
        return (
          <Badge variant="outline" className="border-cyan-500/40 text-cyan-300 bg-cyan-950/30 text-[10px]">
            <Accessibility className="h-2.5 w-2.5 mr-1" />
            ACCESSIBLE
          </Badge>
        );
      case "UNVERIFIED":
        return (
          <Badge variant="outline" className="border-purple-500/40 text-purple-300 bg-purple-950/30 text-[10px]">
            <AlertCircle className="h-2.5 w-2.5 mr-1" />
            UNVERIFIED
          </Badge>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Block Selector and Legend */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* On-Campus Block Tabs */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          {blocks.map((block) => (
            <button
              key={block.block_id}
              onClick={() => setSelectedBlockId(block.block_id)}
              className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 border transition-all shrink-0 ${
                selectedBlockId === block.block_id
                  ? "bg-indigo-600 border-indigo-500 text-white shadow-md shadow-indigo-500/20"
                  : "bg-slate-900/60 border-slate-800 text-slate-300 hover:bg-slate-800/80"
              }`}
            >
              <Building className="h-4 w-4" />
              <span>{block.name}</span>
              <span className="text-[10px] font-mono bg-black/30 px-1.5 py-0.5 rounded uppercase">
                {block.gender_class}
              </span>
            </button>
          ))}
        </div>

        {/* Legend & Controls (Nothing Colour-Only) */}
        <div className="flex items-center gap-3 text-[11px] flex-wrap bg-slate-900/80 border border-slate-800 px-3.5 py-2 rounded-xl">
          <span className="text-slate-400 font-semibold uppercase text-[10px]">Filter Status:</span>
          {(["ALL", "FREE", "OCCUPIED", "CLEANING"] as const).map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-2 py-0.5 rounded text-[10px] font-semibold transition-all ${
                statusFilter === st
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-950 text-slate-400 hover:text-slate-200"
              }`}
            >
              {st}
            </button>
          ))}
          <span className="text-slate-600">|</span>
          <label className="flex items-center gap-1.5 cursor-pointer text-slate-300">
            <input
              type="checkbox"
              checked={highlightSplits}
              onChange={(e) => setHighlightSplits(e.target.checked)}
              className="rounded border-slate-700 bg-slate-950 text-indigo-600 h-3.5 w-3.5"
            />
            <span>Highlight Splits</span>
          </label>
        </div>
      </div>

      {/* Block Capacity Summary Strip */}
      {currentBlock && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800">
            <span className="text-[11px] text-slate-400 block">Total Beds</span>
            <span className="text-xl font-bold text-white">{currentBlock.total_beds}</span>
          </div>
          <div className="p-3 rounded-xl bg-indigo-950/20 border border-indigo-500/30">
            <span className="text-[11px] text-indigo-300 block">Occupied</span>
            <span className="text-xl font-bold text-indigo-200">{currentBlock.occupied_beds}</span>
          </div>
          <div className="p-3 rounded-xl bg-emerald-950/20 border border-emerald-500/30">
            <span className="text-[11px] text-emerald-300 block">Available Free</span>
            <span className="text-xl font-bold text-emerald-200">{currentBlock.free_beds}</span>
          </div>
          <div className="p-3 rounded-xl bg-amber-950/20 border border-amber-500/30">
            <span className="text-[11px] text-amber-300 block">In Cleaning Buffer</span>
            <span className="text-xl font-bold text-amber-200">{currentBlock.cleaning_beds}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800">
            <span className="text-[11px] text-slate-400 block">Offline / Closed</span>
            <span className="text-xl font-bold text-slate-400">{currentBlock.closed_beds}</span>
          </div>
        </div>
      )}

      {/* Interactive Floor Matrix */}
      <div className="space-y-6">
        {currentBlock.floors.map((floor) => (
          <Card key={floor.floor_number} className="overflow-hidden">
            <CardHeader className="py-3 px-4 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-white">
                  {floor.is_ground ? "Floor 0 (Ground Floor)" : `Floor ${floor.floor_number}`}
                </span>
                {floor.is_ground && (
                  <Badge variant="outline" className="border-cyan-500/40 text-cyan-300 bg-cyan-950/20 text-[10px]">
                    <Accessibility className="h-3 w-3 mr-1" />
                    WHEELCHAIR RAMP ACCESS
                  </Badge>
                )}
              </div>
              <span className="text-xs text-slate-400">{floor.rooms.length} Rooms Evaluated</span>
            </CardHeader>

            <CardContent className="p-4 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {floor.rooms.map((room) => {
                const hasLeader = room.beds.some((b) => b.is_leader);
                const hasSplit = room.beds.some((b) => b.contingent_id === "C05") && room.beds.some((b) => b.contingent_id && b.contingent_id !== "C05");

                return (
                  <div
                    key={room.room_id}
                    className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-3 hover:border-slate-700 transition-all"
                  >
                    {/* Room Header */}
                    <div className="flex items-center justify-between border-b border-slate-800/60 pb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white text-sm">Room {room.room_number}</span>
                        {room.accessible && (
                          <Badge size="sm" variant="outline" className="border-cyan-500/40 text-cyan-300">
                            <Accessibility className="h-2.5 w-2.5 mr-0.5" />
                            ACCESSIBLE
                          </Badge>
                        )}
                        {hasLeader && (
                          <Badge size="sm" variant="outline" className="border-amber-500/40 text-amber-300 bg-amber-950/20">
                            <Crown className="h-2.5 w-2.5 mr-0.5 text-amber-400" />
                            LEADER ROOM
                          </Badge>
                        )}
                      </div>

                      {room.cleaning_status === "CLEANING" ? (
                        <span className="text-[10px] text-amber-400 font-mono bg-amber-950/40 px-1.5 py-0.5 rounded border border-amber-600/30">
                          {room.cleaning_remaining_minutes ?? 180}m Buffer
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-400 font-mono">{room.beds.length} Beds</span>
                      )}
                    </div>

                    {/* Split Highlighting warning */}
                    {hasSplit && highlightSplits && (
                      <div className="flex items-center gap-1.5 p-1.5 rounded bg-amber-950/30 border border-amber-500/30 text-[10px] text-amber-300 font-medium">
                        <AlertTriangle className="h-3 w-3 shrink-0" />
                        <span>Contingent Split: mixed institutions in room</span>
                      </div>
                    )}

                    {/* Bed Slots */}
                    <div className="space-y-2">
                      {room.beds
                        .filter((b) => statusFilter === "ALL" || b.status === statusFilter)
                        .map((bed) => (
                        <div
                          key={bed.bed_id}
                          onClick={() => onSelectBedForAssignment && onSelectBedForAssignment(bed, room, currentBlock)}
                          className={`p-2.5 rounded-lg border flex items-center justify-between cursor-pointer transition-all ${
                            bed.status === "FREE"
                              ? "bg-emerald-950/10 border-emerald-500/30 hover:border-emerald-400 hover:bg-emerald-950/20"
                              : bed.status === "OCCUPIED"
                              ? "bg-slate-900/60 border-slate-700/80 hover:border-indigo-400"
                              : "bg-slate-900/30 border-slate-800"
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs font-semibold text-slate-200">
                              {bed.bed_id}
                            </span>
                            {getBedStatusBadge(bed.status)}

                            {bed.is_leader && (
                              <span className="text-[10px] text-amber-400 flex items-center gap-0.5 font-semibold">
                                <Crown className="h-3 w-3" /> Leader
                              </span>
                            )}
                          </div>

                          {bed.participant_name ? (
                            <div className="text-right">
                              <span className="text-xs font-medium text-white block">
                                {bed.participant_name}
                              </span>
                              {bed.contingent_id && (
                                <span
                                  className="text-[10px] font-mono px-1.5 py-0.2 rounded"
                                  style={{
                                    backgroundColor: bed.contingent_color ? `${bed.contingent_color}25` : "#334155",
                                    color: bed.contingent_color || "#cbd5e1",
                                    border: `1px solid ${bed.contingent_color || "#475569"}`,
                                  }}
                                >
                                  {bed.contingent_id}
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-[11px] text-slate-400 italic">Click to Assign</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* External Properties Section with Cost & UNVERIFIED Badges */}
      <div className="space-y-4 pt-4 border-t border-slate-800">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <MapPin className="h-4 w-4 text-indigo-400" />
              <span>External Accommodation Properties (Contracted Hotels)</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Off-campus overflow hotels carrying per-night commercial tariffs and unverified property badges.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {external_properties.map((prop) => (
            <Card key={prop.property_id} className="p-4 bg-slate-950 border-slate-800 space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="font-bold text-white text-sm">{prop.name}</h4>
                  <div className="text-xs text-slate-400 mt-0.5 flex items-center gap-1">
                    <MapPin className="h-3 w-3" /> {prop.distance_km} km from Campus
                  </div>
                </div>
                <div className="text-right">
                  <div className="flex items-center font-bold text-white text-sm">
                    <IndianRupee className="h-3.5 w-3.5 text-slate-400" />
                    <span>{prop.cost_per_bed_night.toLocaleString("en-IN")}</span>
                  </div>
                  <span className="text-[10px] text-slate-400">per bed / night</span>
                </div>
              </div>

              {/* Bed Counts */}
              <div className="grid grid-cols-3 gap-2 text-center text-xs p-2 rounded-lg bg-slate-900 border border-slate-800">
                <div>
                  <span className="text-slate-400 text-[10px] block">Contracted</span>
                  <span className="font-bold text-white">{prop.total_beds}</span>
                </div>
                <div>
                  <span className="text-slate-400 text-[10px] block">Occupied</span>
                  <span className="font-bold text-indigo-300">{prop.occupied_beds}</span>
                </div>
                <div>
                  <span className="text-slate-400 text-[10px] block">Available</span>
                  <span className="font-bold text-emerald-300">{prop.free_beds}</span>
                </div>
              </div>

              {/* UNVERIFIED BADGES (MANDATORY per spec section 10 & BUILD 3) */}
              <div className="space-y-1.5 pt-1">
                {!prop.accessibility_verified && (
                  <div className="flex items-center gap-1.5 p-2 rounded-lg bg-amber-950/20 border border-amber-500/30 text-[11px] text-amber-300 font-medium">
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                    <span>Accessibility: <strong>UNVERIFIED</strong></span>
                  </div>
                )}
                {!prop.gender_suitability_verified && (
                  <div className="flex items-center gap-1.5 p-2 rounded-lg bg-amber-950/20 border border-amber-500/30 text-[11px] text-amber-300 font-medium">
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                    <span>Gender Suitability: <strong>UNVERIFIED</strong></span>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
};

export default OccupancyMap;
