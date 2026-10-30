import React, { useState } from "react";
import {
  Upload,
  FileCheck,
  AlertTriangle,
  Download,
  CheckCircle2,
  AlertOctagon,
  Layers,
  History,
  FileSpreadsheet,
  ArrowRight,
  ShieldAlert,
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
  ConfirmWithReason,
  useToast,
  KpiTile,
  Tabs,
} from "../../components/ui";

interface ImportBatchRecord {
  id: string;
  filename: string;
  total_rows: number;
  imported_rows: number;
  quarantined_rows: number;
  status: "COMPLETED" | "PARTIAL" | "FAILED";
  imported_at: string;
}

interface QuarantineItem {
  id: string;
  source_row: number;
  file: string;
  entity_id: string;
  name: string;
  reason: string;
  severity: "CRITICAL" | "HIGH";
  raw_data: Record<string, any>;
}

interface QualityIssue {
  id: string;
  file: string;
  field: string;
  issue_type: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  affected_count: number;
  impact_text: string;
}

const DEFAULT_BATCHES: ImportBatchRecord[] = [
  {
    id: "imp_001_pack",
    filename: "participants.csv",
    total_rows: 2836,
    imported_rows: 2833,
    quarantined_rows: 3,
    status: "COMPLETED",
    imported_at: "2026-10-30T10:00:00Z",
  },
  {
    id: "imp_002_pack",
    filename: "contingents.csv",
    total_rows: 38,
    imported_rows: 38,
    quarantined_rows: 0,
    status: "COMPLETED",
    imported_at: "2026-10-30T10:01:00Z",
  },
  {
    id: "imp_003_pack",
    filename: "events.csv",
    total_rows: 31,
    imported_rows: 31,
    quarantined_rows: 0,
    status: "COMPLETED",
    imported_at: "2026-10-30T10:02:00Z",
  },
];

const DEFAULT_QUARANTINE: QuarantineItem[] = [
  {
    id: "qrn_001",
    source_row: 412,
    file: "participants.csv",
    entity_id: "ROW_0412",
    name: "Vikram Sengupta",
    reason: "Departure datetime precedes arrival (2026-10-31T08:00:00 vs 2026-10-31T20:00:00)",
    severity: "CRITICAL",
    raw_data: { college: "IIT Kharagpur", arrival: "2026-10-31 20:00", departure: "2026-10-31 08:00" },
  },
  {
    id: "qrn_002",
    source_row: 1184,
    file: "participants.csv",
    entity_id: "ROW_1184",
    name: "Ananya Iyer",
    reason: "Invalid timestamp format in travel window: departure date undefined",
    severity: "CRITICAL",
    raw_data: { college: "BITS Goa", arrival: "2026-10-31 10:00", departure: "INVALID_NIL" },
  },
  {
    id: "qrn_003",
    source_row: 2405,
    file: "participants.csv",
    entity_id: "ROW_2405",
    name: "Harshil Patel",
    reason: "Departure datetime precedes arrival (2026-10-30T12:00:00 vs 2026-11-01T10:00:00)",
    severity: "CRITICAL",
    raw_data: { college: "SVNIT Surat", arrival: "2026-11-01 10:00", departure: "2026-10-30 12:00" },
  },
];

const DEFAULT_ISSUES: QualityIssue[] = [
  {
    id: "iss_01",
    file: "participants.csv",
    field: "departure_at",
    issue_type: "Negative Duration Window",
    severity: "CRITICAL",
    affected_count: 3,
    impact_text: "3 participants quarantined; housing turnaround calculations blocked.",
  },
  {
    id: "iss_02",
    file: "contingents.csv",
    field: "strength_declared",
    issue_type: "Declared vs Actual Mismatch",
    severity: "HIGH",
    affected_count: 7,
    impact_text: "7 contingents exhibit headcount discrepancies (-8 under, +7 over).",
  },
  {
    id: "iss_03",
    file: "participants.csv",
    field: "accommodation_requested",
    issue_type: "Literal UNKNOWN Value",
    severity: "HIGH",
    affected_count: 418,
    impact_text: "Beds cannot be blocked in Plan A/B without confirmed housing requirement.",
  },
  {
    id: "iss_04",
    file: "participants.csv",
    field: "gender",
    issue_type: "Literal UNKNOWN Value",
    severity: "HIGH",
    affected_count: 417,
    impact_text: "Room allocation cannot enforce campus gender segregation safety constraints.",
  },
  {
    id: "iss_05",
    file: "participants.csv",
    field: "diet",
    issue_type: "Literal UNKNOWN Value",
    severity: "MEDIUM",
    affected_count: 394,
    impact_text: "Catering procurement buffers risk meal shortages or food waste.",
  },
  {
    id: "iss_06",
    file: "participants.csv",
    field: "tshirt_size",
    issue_type: "Literal UNKNOWN Value",
    severity: "LOW",
    affected_count: 55,
    impact_text: "Merchandise packing desk cannot pre-kit kit bags for arrival check-in.",
  },
];

export const ImportsPage: React.FC = () => {
  const { addToast } = useToast();
  const [activeTab, setActiveTab] = useState("wizard");

  // Wizard state: 1: files, 2: mapping, 3: summary, 4: quarantine, 5: promoted
  const [wizardStep, setWizardStep] = useState(1);
  const [selectedFile, setSelectedFile] = useState<string>("participants.csv");
  const [quarantineItems] = useState<QuarantineItem[]>(DEFAULT_QUARANTINE);
  const [promoteModalOpen, setPromoteModalOpen] = useState(false);
  const [promoteLoading, setPromoteLoading] = useState(false);

  // Issues filter state
  const [issueFileFilter, setIssueFileFilter] = useState("all");
  const [issueSeverityFilter, setIssueSeverityFilter] = useState("all");

  const handlePromoteConfirm = async (reason: string) => {
    setPromoteLoading(true);
    try {
      await new Promise((r) => setTimeout(r, 600));
      addToast({
        type: "success",
        title: "Pack Data Promoted",
        message: `Successfully promoted 2,833 valid records into canonical tables with reason: "${reason}".`,
      });
      setPromoteModalOpen(false);
      setWizardStep(5);
    } catch {
      addToast({
        type: "error",
        title: "Promotion Failed",
        message: "Failed to promote records.",
      });
    } finally {
      setPromoteLoading(false);
    }
  };

  const handleDownloadReport = () => {
    const reportData = [
      ["Metric", "Value", "Notes"],
      ["Total Raw Records", "2836", "From participants.csv"],
      ["Valid Records Promoted", "2833", "Stage 1 Clean"],
      ["Quarantined Rows", String(quarantineItems.length), "Isolated from live operational plans"],
      ["Contingents Declared", "2842", "Sum of strength_declared across 38 contingents"],
      ["Narrative Planning Base", "2400", "Baseline narrative from briefing"],
      ["Unresolved Gap", "426", "Surplus raw over narrative (honest waterfall)"],
      ["Unknown Gender", "417", "14.7% of roster"],
      ["Unknown Accommodation", "418", "14.7% of roster"],
      ["Unknown Diet", "394", "13.9% of roster"],
      ["Unknown T-Shirt Size", "55", "1.9% of roster"],
    ];
    const csvContent =
      "data:text/csv;charset=utf-8," + reportData.map((e) => e.join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `data_quality_report_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();

    addToast({
      type: "info",
      title: "Data Quality Report Downloaded",
      message: "data_quality_report.csv successfully exported.",
    });
  };

  // Quarantine Columns
  const quarantineColumns: Column<QuarantineItem>[] = [
    {
      key: "source_row",
      header: "Row #",
      width: "80px",
      render: (r) => <span className="font-mono text-slate-400">#{r.source_row}</span>,
    },
    {
      key: "name",
      header: "Participant Name",
      render: (r) => (
        <div>
          <div className="font-semibold text-slate-200">{r.name}</div>
          <div className="text-[11px] text-slate-500 font-mono">{r.raw_data.college}</div>
        </div>
      ),
    },
    {
      key: "reason",
      header: "Rejection Reason",
      render: (r) => (
        <span className="text-rose-300 font-medium text-xs flex items-center space-x-1.5">
          <AlertOctagon className="h-3.5 w-3.5 text-rose-400 shrink-0" />
          <span>{r.reason}</span>
        </span>
      ),
    },
    {
      key: "severity",
      header: "Severity",
      width: "110px",
      render: (r) => <Badge severity={r.severity} />,
    },
  ];

  // Batch History Columns
  const batchColumns: Column<ImportBatchRecord>[] = [
    {
      key: "id",
      header: "Batch ID",
      width: "140px",
      render: (r) => <span className="font-mono text-indigo-400">{r.id}</span>,
    },
    {
      key: "filename",
      header: "File Name",
      render: (r) => <span className="font-semibold text-slate-200">{r.filename}</span>,
    },
    {
      key: "total_rows",
      header: "Total",
      width: "90px",
      render: (r) => <span className="font-mono">{r.total_rows.toLocaleString()}</span>,
    },
    {
      key: "imported_rows",
      header: "Imported",
      width: "90px",
      render: (r) => <span className="font-mono text-emerald-400">{r.imported_rows.toLocaleString()}</span>,
    },
    {
      key: "quarantined_rows",
      header: "Quarantined",
      width: "110px",
      render: (r) =>
        r.quarantined_rows > 0 ? (
          <span className="font-mono text-rose-400 font-bold">{r.quarantined_rows} rows</span>
        ) : (
          <span className="font-mono text-slate-500">0</span>
        ),
    },
    {
      key: "status",
      header: "Status",
      width: "120px",
      render: (r) => <Badge status={r.status} />,
    },
    {
      key: "imported_at",
      header: "Imported At",
      render: (r) => (
        <span className="text-slate-400 font-mono text-[11px]">
          {new Date(r.imported_at).toLocaleString()}
        </span>
      ),
    },
  ];

  // Filtered Issues
  const filteredIssues = DEFAULT_ISSUES.filter((iss) => {
    if (issueFileFilter !== "all" && iss.file !== issueFileFilter) return false;
    if (issueSeverityFilter !== "all" && iss.severity !== issueSeverityFilter) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white flex items-center space-x-2.5">
            <FileSpreadsheet className="h-7 w-7 text-indigo-400" />
            <span>Import & Data Quality Management</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Data pack ingestion pipeline, column mapping validation, quarantine review, and UNKNOWN heat analysis.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownloadReport}
            leftIcon={<Download className="h-4 w-4" />}
            data-testid="download-quality-report"
          >
            Download Quality Report
          </Button>
        </div>
      </div>

      {/* KPI Tiles */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiTile
          label="Raw Records Ingested"
          value="2,836"
          icon={<Layers className="h-4 w-4 text-indigo-400" />}
          subtext="participants.csv raw data"
        />
        <KpiTile
          label="Valid Promoted"
          value="2,833"
          icon={<CheckCircle2 className="h-4 w-4 text-emerald-400" />}
          subtext="Canonical active records"
        />
        <KpiTile
          label="Quarantined Records"
          value={quarantineItems.length}
          icon={<AlertOctagon className="h-4 w-4 text-rose-400" />}
          subtext="Isolated negative duration rows"
          warning={quarantineItems.length > 0}
        />
        <KpiTile
          label="UNKNOWN Fields"
          value="1,284"
          icon={<AlertTriangle className="h-4 w-4 text-amber-400" />}
          subtext="Missing values requiring verification"
          warning={true}
        />
      </div>

      {/* Tabs */}
      <Tabs
        activeTab={activeTab}
        onChange={setActiveTab}
        tabs={[
          { id: "wizard", label: "Upload & Ingestion Wizard", icon: <Upload className="h-4 w-4" /> },
          { id: "issues", label: "Quality Issues & UNKNOWN Heat", icon: <AlertTriangle className="h-4 w-4" /> },
          { id: "batches", label: "Batch History", icon: <History className="h-4 w-4" /> },
        ]}
      />

      {/* TAB 1: Upload Wizard */}
      {activeTab === "wizard" && (
        <div className="space-y-6">
          {/* Stepper indicator */}
          <div className="flex items-center justify-between border border-slate-800 bg-[#0E1526] p-4 rounded-xl text-xs">
            {[
              { num: 1, label: "Select Files" },
              { num: 2, label: "Detected Mapping" },
              { num: 3, label: "Validation Summary" },
              { num: 4, label: "Quarantine Review" },
              { num: 5, label: "Promote & Ready" },
            ].map((step, idx) => (
              <React.Fragment key={step.num}>
                <div
                  className={`flex items-center space-x-2 cursor-pointer ${
                    wizardStep >= step.num ? "text-indigo-400 font-bold" : "text-slate-500"
                  }`}
                  onClick={() => setWizardStep(step.num)}
                >
                  <span
                    className={`flex h-6 w-6 items-center justify-center rounded-full border text-xs ${
                      wizardStep === step.num
                        ? "border-indigo-500 bg-indigo-600 text-white"
                        : wizardStep > step.num
                        ? "border-emerald-500 bg-emerald-950 text-emerald-300"
                        : "border-slate-700 bg-slate-900 text-slate-500"
                    }`}
                  >
                    {wizardStep > step.num ? "✓" : step.num}
                  </span>
                  <span>{step.label}</span>
                </div>
                {idx < 4 && <ArrowRight className="h-3 w-3 text-slate-700 shrink-0" />}
              </React.Fragment>
            ))}
          </div>

          {/* Step 1: File selection */}
          {wizardStep === 1 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Step 1: Ingest Aarohan Fest Data Pack</CardTitle>
                <CardDescription>
                  Upload official CSV pack files (`participants.csv`, `contingents.csv`, `events.csv`, `venues.csv`).
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="border-2 border-dashed border-slate-700 hover:border-indigo-500/80 rounded-xl p-8 text-center bg-slate-950/40 transition-colors cursor-pointer">
                  <Upload className="h-10 w-10 text-indigo-400 mx-auto mb-3 animate-bounce" />
                  <p className="text-sm font-semibold text-slate-200">
                    Drop CSV files here or click to browse
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    Synthetic EPINOIA 2026 data pack formats supported
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                  {[
                    { name: "participants.csv", rows: "2,836 rows", size: "348 KB", ready: true },
                    { name: "contingents.csv", rows: "38 rows", size: "12 KB", ready: true },
                    { name: "events.csv", rows: "31 rows", size: "14 KB", ready: true },
                    { name: "venues.csv", rows: "9 rows", size: "4 KB", ready: true },
                  ].map((file) => (
                    <div
                      key={file.name}
                      onClick={() => setSelectedFile(file.name)}
                      className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-all ${
                        selectedFile === file.name
                          ? "border-indigo-500 bg-indigo-950/20"
                          : "border-slate-800 bg-slate-900/60 hover:border-slate-700"
                      }`}
                    >
                      <div className="flex items-center space-x-3">
                        <FileCheck className="h-5 w-5 text-indigo-400" />
                        <div>
                          <div className="font-semibold text-xs text-white">{file.name}</div>
                          <div className="text-[11px] text-slate-400 font-mono">
                            {file.rows} • {file.size}
                          </div>
                        </div>
                      </div>
                      <Badge variant="outline" className="border-emerald-500/30 text-emerald-300 text-[10px]">
                        PARSED
                      </Badge>
                    </div>
                  ))}
                </div>

                <div className="flex justify-end pt-4">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => setWizardStep(2)}
                    rightIcon={<ArrowRight className="h-3.5 w-3.5" />}
                  >
                    Continue to Mapping
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Step 2: Detected Mapping */}
          {wizardStep === 2 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Step 2: Auto-Detected Column Mapping ({selectedFile})</CardTitle>
                <CardDescription>
                  Normalized column definitions automatically linked to canonical FestOS models.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-xl border border-slate-800 overflow-hidden text-xs">
                  <table className="w-full text-left">
                    <thead className="bg-slate-900/90 text-slate-400 font-semibold border-b border-slate-800">
                      <tr>
                        <th className="p-3">Source Header (CSV)</th>
                        <th className="p-3">Canonical Attribute</th>
                        <th className="p-3">Data Type / Category</th>
                        <th className="p-3">Sample Value</th>
                        <th className="p-3">Validation Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 font-mono">
                      {[
                        { src: "Full Name", target: "name", type: "STRING (Mandatory)", sample: "Aarav Sharma", status: "MATCHED" },
                        { src: "Institution Code", target: "contingent_id", type: "FOREIGN_KEY (C01-C38)", sample: "C05", status: "MATCHED" },
                        { src: "Email Address", target: "email", type: "EMAIL (PII Protected)", sample: "aarav@iitb.ac.in", status: "MATCHED" },
                        { src: "Contact Phone", target: "phone", type: "PHONE (PII Protected)", sample: "+91 98765 43210", status: "MATCHED" },
                        { src: "Gender Category", target: "gender", type: "TRI_STATE / UNKNOWN", sample: "UNKNOWN", status: "MATCHED" },
                        { src: "Dietary Preference", target: "diet", type: "TRI_STATE / UNKNOWN", sample: "VEG", status: "MATCHED" },
                        { src: "Accommodation Req", target: "accommodation_requested", type: "TRI_STATE / UNKNOWN", sample: "YES", status: "MATCHED" },
                        { src: "Arrival DateTime", target: "arrival_at", type: "ISO_DATETIME", sample: "2026-10-31T08:30:00Z", status: "MATCHED" },
                        { src: "Departure DateTime", target: "departure_at", type: "ISO_DATETIME", sample: "2026-11-03T18:00:00Z", status: "MATCHED" },
                      ].map((m, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/40">
                          <td className="p-3 text-white font-sans">{m.src}</td>
                          <td className="p-3 text-indigo-300">{m.target}</td>
                          <td className="p-3 text-slate-400 text-[11px]">{m.type}</td>
                          <td className="p-3 text-slate-300">{m.sample}</td>
                          <td className="p-3">
                            <span className="inline-flex items-center text-emerald-400 text-[10px] font-sans font-bold">
                              ✓ {m.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="flex justify-between pt-4">
                  <Button variant="secondary" size="sm" onClick={() => setWizardStep(1)}>
                    Back
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => setWizardStep(3)}
                    rightIcon={<ArrowRight className="h-3.5 w-3.5" />}
                  >
                    Run Validation Check
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Step 3: Validation Summary */}
          {wizardStep === 3 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Step 3: Ingestion Validation Summary</CardTitle>
                <CardDescription>
                  Integrity scan results across 2,836 participant rows and 38 contingent declarations.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4">
                    <div className="text-emerald-400 font-bold text-sm flex items-center space-x-1.5">
                      <CheckCircle2 className="h-4 w-4" />
                      <span>Valid Records (Ready)</span>
                    </div>
                    <div className="text-3xl font-extrabold text-white mt-2 font-mono">2,833</div>
                    <p className="text-xs text-slate-400 mt-1">Conforms to all schema rules and timestamps.</p>
                  </div>

                  <div className="rounded-xl border border-rose-500/30 bg-rose-950/20 p-4">
                    <div className="text-rose-400 font-bold text-sm flex items-center space-x-1.5">
                      <AlertOctagon className="h-4 w-4" />
                      <span>Quarantined Records</span>
                    </div>
                    <div className="text-3xl font-extrabold text-white mt-2 font-mono">3</div>
                    <p className="text-xs text-rose-300/80 mt-1">Negative durations: departure &lt; arrival.</p>
                  </div>

                  <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-4">
                    <div className="text-amber-400 font-bold text-sm flex items-center space-x-1.5">
                      <AlertTriangle className="h-4 w-4" />
                      <span>Warnings / UNKNOWN</span>
                    </div>
                    <div className="text-3xl font-extrabold text-white mt-2 font-mono">1,284</div>
                    <p className="text-xs text-slate-400 mt-1">Missing fields requiring verification.</p>
                  </div>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-xs space-y-2">
                  <div className="font-bold text-white flex items-center space-x-2">
                    <ShieldAlert className="h-4 w-4 text-indigo-400" />
                    <span>Principle Enforcement Check</span>
                  </div>
                  <ul className="list-disc list-inside space-y-1 text-slate-300">
                    <li>3 quarantined rows will be isolated in <code>quarantine_row</code> and not passed to accommodation solvers.</li>
                    <li>2,833 records will maintain raw integrity in <code>raw_record</code> and canonical records in <code>participant</code>.</li>
                    <li>Declared vs raw headcount gap (-6 overall, 7 mismatched contingents) will remain transparent in the reconciliation waterfall.</li>
                  </ul>
                </div>

                <div className="flex justify-between pt-4">
                  <Button variant="secondary" size="sm" onClick={() => setWizardStep(2)}>
                    Back
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => setWizardStep(4)}
                    rightIcon={<ArrowRight className="h-3.5 w-3.5" />}
                  >
                    Review Quarantine Rows
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Step 4: Quarantine Review */}
          {wizardStep === 4 && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-sm">Step 4: Quarantine Review ({quarantineItems.length} rows)</CardTitle>
                  <CardDescription>
                    These records failed hard integrity gates and are quarantined from the live operational database.
                  </CardDescription>
                </div>
                <Badge severity="CRITICAL">{quarantineItems.length} Quarantined</Badge>
              </CardHeader>
              <CardContent className="space-y-4">
                <DataTable
                  columns={quarantineColumns}
                  data={quarantineItems}
                  total={quarantineItems.length}
                />

                <div className="flex items-center justify-between pt-4 border-t border-slate-800">
                  <Button variant="secondary" size="sm" onClick={() => setWizardStep(3)}>
                    Back to Summary
                  </Button>

                  <div className="flex items-center space-x-3">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => setPromoteModalOpen(true)}
                      data-testid="promote-button"
                    >
                      Promote Valid Records (2,833) with Reason
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Step 5: Finished */}
          {wizardStep === 5 && (
            <Card className="border-emerald-500/40 bg-emerald-950/15">
              <CardContent className="py-12 text-center space-y-4">
                <div className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 mx-auto">
                  <CheckCircle2 className="h-8 w-8" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white">Data Pack Successfully Promoted</h2>
                  <p className="text-xs text-slate-300 max-w-md mx-auto mt-1">
                    2,833 canonical participant records, 38 contingents, and 31 events are now live in the FestOS operational store. 3 quarantined rows preserved for audit.
                  </p>
                </div>
                <div className="flex justify-center space-x-3 pt-2">
                  <Button variant="secondary" size="sm" onClick={() => setWizardStep(1)}>
                    Import Another Batch
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setActiveTab("issues")}>
                    View UNKNOWN Heat & Issues
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* TAB 2: Quality Issues & UNKNOWN Heat */}
      {activeTab === "issues" && (
        <div className="space-y-6">
          {/* UNKNOWN Heatmap Cards */}
          <div className="space-y-3">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">
              Field UNKNOWN Heat & Solver Impact
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                {
                  field: "accommodation_requested",
                  count: 418,
                  pct: "14.7%",
                  severity: "HIGH" as const,
                  owner: "ACCOMMODATION_LEAD",
                  impact: "Beds cannot be definitively blocked in Plan A/B without confirmed housing requirement.",
                },
                {
                  field: "gender",
                  count: 417,
                  pct: "14.7%",
                  severity: "HIGH" as const,
                  owner: "ACCOMMODATION_LEAD",
                  impact: "Room allocation cannot enforce campus gender segregation safety constraints.",
                },
                {
                  field: "diet",
                  count: 394,
                  pct: "13.9%",
                  severity: "MEDIUM" as const,
                  owner: "FOOD_OPS_MANAGER",
                  impact: "Catering procurement buffers risk meal shortages or food waste.",
                },
                {
                  field: "tshirt_size",
                  count: 55,
                  pct: "1.9%",
                  severity: "LOW" as const,
                  owner: "MERCHANDISE_MANAGER",
                  impact: "Merchandise packing desk cannot pre-kit kit bags for arrival check-in.",
                },
              ].map((item) => (
                <div
                  key={item.field}
                  className="rounded-xl border border-slate-800 bg-[#0E1526] p-4 flex flex-col justify-between space-y-3 shadow-sm"
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-white">{item.field}</span>
                      <Badge severity={item.severity} />
                    </div>
                    <div className="flex items-baseline space-x-2 mt-2">
                      <span className="text-2xl font-extrabold text-amber-400 font-mono">{item.count}</span>
                      <span className="text-xs text-slate-400">({item.pct} of roster)</span>
                    </div>
                    <p className="text-[11px] text-slate-300 mt-2 leading-relaxed">
                      {item.impact}
                    </p>
                  </div>
                  <div className="border-t border-slate-800 pt-2 flex items-center justify-between text-[10px] text-slate-400 font-mono">
                    <span>Owner: {item.owner}</span>
                    <span className="text-amber-400">First-class UNKNOWN</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Filterable Issues Table */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-sm">Detected Data Quality Issues</CardTitle>
                <CardDescription>
                  Filterable by file, field, and severity. All issues flagged without altering raw input values.
                </CardDescription>
              </div>
              <div className="flex items-center space-x-2">
                <select
                  value={issueFileFilter}
                  onChange={(e) => setIssueFileFilter(e.target.value)}
                  className="rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1 text-xs text-slate-200"
                >
                  <option value="all">All Files</option>
                  <option value="participants.csv">participants.csv</option>
                  <option value="contingents.csv">contingents.csv</option>
                </select>

                <select
                  value={issueSeverityFilter}
                  onChange={(e) => setIssueSeverityFilter(e.target.value)}
                  className="rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1 text-xs text-slate-200"
                >
                  <option value="all">All Severities</option>
                  <option value="CRITICAL">CRITICAL</option>
                  <option value="HIGH">HIGH</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="LOW">LOW</option>
                </select>
              </div>
            </CardHeader>
            <CardContent>
              <div className="divide-y divide-slate-800">
                {filteredIssues.map((iss) => (
                  <div key={iss.id} className="py-3.5 flex items-start justify-between">
                    <div className="space-y-1 max-w-xl">
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-xs font-bold text-white">{iss.file}</span>
                        <span className="text-slate-500">→</span>
                        <span className="font-mono text-xs text-indigo-300">{iss.field}</span>
                        <span className="text-xs font-semibold text-slate-300">({iss.issue_type})</span>
                      </div>
                      <p className="text-xs text-slate-400">{iss.impact_text}</p>
                    </div>

                    <div className="text-right space-y-1">
                      <Badge severity={iss.severity} />
                      <div className="text-xs font-mono text-slate-400">
                        {iss.affected_count} affected
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* TAB 3: Batch History */}
      {activeTab === "batches" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Historical Ingestion Batches</CardTitle>
            <CardDescription>
              Audit trail of all data pack ingestion runs with row statistics and outcome.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <DataTable
              columns={batchColumns}
              data={DEFAULT_BATCHES}
              total={DEFAULT_BATCHES.length}
            />
          </CardContent>
        </Card>
      )}

      {/* Promote Confirmation Modal with Mandatory Reason */}
      <ConfirmWithReason
        isOpen={promoteModalOpen}
        onClose={() => setPromoteModalOpen(false)}
        title="Promote Ingestion Batch to Canonical State"
        description="FestOS policy requires recording an operational rationale when promoting staged rows to live canonical tables."
        confirmText="Promote 2,833 Records"
        placeholder="e.g. Official Aarohan 2026 data pack validated by Festival Director with 3 bad date rows quarantined..."
        isLoading={promoteLoading}
        riskLevel="HIGH"
        onConfirm={handlePromoteConfirm}
      />
    </div>
  );
};

export default ImportsPage;
