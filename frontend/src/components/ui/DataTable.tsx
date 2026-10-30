import React, { useState } from "react";
import { cn } from "../../lib/utils";
import {
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Search,
} from "lucide-react";
import { Skeleton } from "./Skeleton";

export interface Column<T> {
  key: string;
  header: React.ReactNode;
  render?: (row: T, index: number) => React.ReactNode;
  sortable?: boolean;
  width?: string;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  total?: number;
  page?: number;
  pageSize?: number;
  onPageChange?: (newPage: number) => void;
  sortKey?: string;
  sortOrder?: "asc" | "desc";
  onSort?: (key: string, order: "asc" | "desc") => void;
  isLoading?: boolean;
  searchPlaceholder?: string;
  onSearch?: (term: string) => void;
  emptyMessage?: string;
  className?: string;
  onRowClick?: (row: T) => void;
  keyExtractor?: (row: T) => string;
}

export function DataTable<T extends Record<string, any>>({
  columns,
  data,
  total = 0,
  page = 1,
  pageSize = 20,
  onPageChange,
  sortKey,
  sortOrder,
  onSort,
  isLoading = false,
  searchPlaceholder = "Filter records...",
  onSearch,
  emptyMessage = "No records found.",
  className,
  onRowClick,
  keyExtractor,
}: DataTableProps<T>) {
  const [localSearch, setLocalSearch] = useState("");
  const totalPages = Math.ceil(total / pageSize) || 1;

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalSearch(val);
    if (onSearch) onSearch(val);
  };

  const handleHeaderClick = (col: Column<T>) => {
    if (!col.sortable || !onSort) return;
    const nextOrder = sortKey === col.key && sortOrder === "asc" ? "desc" : "asc";
    onSort(col.key, nextOrder);
  };

  return (
    <div className={cn("flex flex-col rounded-xl border border-slate-800 bg-[#0E1526]/90 overflow-hidden shadow-sm", className)}>
      {/* Table Toolbar */}
      {onSearch && (
        <div className="flex items-center justify-between border-b border-slate-800 p-3.5 bg-slate-900/40">
          <div className="relative w-72">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
            <input
              type="text"
              value={localSearch}
              onChange={handleSearchChange}
              placeholder={searchPlaceholder}
              className="w-full rounded-lg border border-slate-700 bg-slate-950/60 py-1.5 pl-9 pr-3 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div className="text-xs text-slate-400">
            Total records: <span className="font-semibold text-slate-200">{total}</span>
          </div>
        </div>
      )}

      {/* Table Container */}
      <div className="overflow-x-auto max-h-[560px]">
        <table className="w-full text-left text-xs border-collapse">
          <thead className="sticky top-0 z-10 bg-slate-900/95 backdrop-blur border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleHeaderClick(col)}
                  style={col.width ? { width: col.width } : undefined}
                  className={cn(
                    "px-4 py-3 select-none",
                    col.sortable && "cursor-pointer hover:text-white transition-colors"
                  )}
                >
                  <div className="flex items-center space-x-1.5">
                    <span>{col.header}</span>
                    {col.sortable && (
                      <span className="text-slate-500">
                        {sortKey === col.key ? (
                          sortOrder === "asc" ? (
                            <ArrowUp className="h-3 w-3 text-indigo-400" />
                          ) : (
                            <ArrowDown className="h-3 w-3 text-indigo-400" />
                          )
                        ) : (
                          <ArrowUpDown className="h-3 w-3 opacity-60" />
                        )}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-sans">
            {isLoading ? (
              Array.from({ length: 5 }).map((_, rIdx) => (
                <tr key={`skel-row-${rIdx}`} className="bg-slate-950/20">
                  {columns.map((_, cIdx) => (
                    <td key={`skel-cell-${cIdx}`} className="px-4 py-3.5">
                      <Skeleton className="h-4 w-full" />
                    </td>
                  ))}
                </tr>
              ))
            ) : data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-12 text-center text-slate-500 italic">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              data.map((row, idx) => (
                <tr
                  key={keyExtractor ? keyExtractor(row) : row.id || idx}
                  onClick={() => onRowClick && onRowClick(row)}
                  className={cn(
                    "hover:bg-slate-800/40 transition-colors even:bg-slate-950/15",
                    onRowClick && "cursor-pointer"
                  )}
                >
                  {columns.map((col) => (
                    <td key={col.key} className="px-4 py-3 text-slate-300">
                      {col.render ? col.render(row, idx) : row[col.key] ?? "-"}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Server Pagination Footer */}
      {onPageChange && (
        <div className="flex items-center justify-between border-t border-slate-800 px-4 py-3 bg-slate-900/60 text-xs text-slate-400">
          <div>
            Showing{" "}
            <span className="font-medium text-slate-200">
              {total > 0 ? (page - 1) * pageSize + 1 : 0}
            </span>{" "}
            to{" "}
            <span className="font-medium text-slate-200">
              {Math.min(page * pageSize, total)}
            </span>{" "}
            of <span className="font-medium text-slate-200">{total}</span> entries
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1 || isLoading}
              className="inline-flex items-center rounded-lg border border-slate-700 bg-slate-800/80 p-1.5 text-slate-300 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed"
              title="Previous Page"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="px-2 font-medium text-slate-300">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages || isLoading}
              className="inline-flex items-center rounded-lg border border-slate-700 bg-slate-800/80 p-1.5 text-slate-300 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed"
              title="Next Page"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
