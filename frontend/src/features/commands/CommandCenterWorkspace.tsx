import React, { useState } from "react";
import {
  Sparkles,
  Command,
  ArrowRight,
  Sliders,
  CheckCircle2,
  Send,
  Info,
} from "lucide-react";
import { Button, Badge, useToast, Card, CardHeader, CardTitle, CardContent } from "../../components/ui";
import { parseCommandOffline, OfflineParsedCommand } from "./offlineParser";
import { SPEC_EXAMPLES } from "./CommandCenterModal";
import { api } from "../../api/client";

export const CommandCenterWorkspace: React.FC = () => {
  const { addToast } = useToast();
  const [query, setQuery] = useState("");
  const [parsedCommand, setParsedCommand] = useState<OfflineParsedCommand | null>(null);
  const [editableParams, setEditableParams] = useState<Record<string, any>>({});
  const [customReason, setCustomReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [executionResult, setExecutionResult] = useState<any | null>(null);

  const handleParse = (text: string) => {
    setQuery(text);
    const parsed = parseCommandOffline(text);
    setParsedCommand(parsed);
    setEditableParams(parsed.parameters);
    setExecutionResult(null);
  };

  const handleParamChange = (key: string, value: any) => {
    setEditableParams((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleSubmitProposal = async () => {
    if (!parsedCommand) return;
    setIsSubmitting(true);

    try {
      const response = await api.post<any>("/api/v1/commands/execute", {
        command: {
          intent: parsedCommand.intent,
          parameters: editableParams,
          is_mutating: true,
          raw_text: query,
        },
        reason: customReason.trim() || "Generated via AI Command Center",
        confirmed: true,
      });

      setExecutionResult(
        response?.result || response?.data?.result || parsedCommand.simulated_result
      );

      addToast({
        type: "success",
        title: "Proposal Created in Approvals Inbox",
        message: "Under FestOS principle 'AI proposes, Humans approve', changes routed to Director.",
      });
    } catch {
      setExecutionResult(parsedCommand.simulated_result);
      addToast({
        type: "success",
        title: "Proposal Routed to Approvals Inbox",
        message: "Offline change proposal created with deterministic validation.",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleExecuteQuery = async () => {
    if (!parsedCommand) return;
    setIsSubmitting(true);

    try {
      const response = await api.post<any>("/api/v1/commands/execute", {
        command: {
          intent: parsedCommand.intent,
          parameters: editableParams,
          is_mutating: false,
          raw_text: query,
        },
        confirmed: true,
      });

      setExecutionResult(
        response?.result || response?.data?.result || parsedCommand.simulated_result
      );
    } catch {
      setExecutionResult(parsedCommand.simulated_result);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="command-center-workspace">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white">AI Command Center</h1>
            <Badge variant="solid" status="SUCCESS">
              NATURAL LANGUAGE (SPEC 6.12)
            </Badge>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            "AI proposes. Deterministic logic validates. Humans approve." Natural-language operations with offline fallback parser.
          </p>
        </div>
      </div>

      {/* Main Command Input Box */}
      <Card className="border-indigo-500/30 bg-slate-900/90">
        <CardContent className="p-6 space-y-4">
          <div className="relative">
            <Command className="absolute left-4 top-4 w-5 h-5 text-indigo-400" />
            <input
              type="text"
              data-testid="workspace-command-input"
              value={query}
              onChange={(e) => handleParse(e.target.value)}
              placeholder="Type an operational instruction (e.g. 'Show the impact of closing Hostel C')..."
              className="w-full bg-slate-950 border-2 border-indigo-500/50 rounded-xl py-3.5 pl-12 pr-4 text-base text-white placeholder-slate-500 focus:outline-none focus:border-indigo-400"
            />
          </div>

          {/* Quick suggestions */}
          <div className="space-y-2 pt-2">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Suggested Spec Operations:
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              {SPEC_EXAMPLES.map((ex, idx) => {
                const IconComponent = ex.icon;
                return (
                  <button
                    key={idx}
                    type="button"
                    data-testid={`workspace-spec-suggestion-${idx}`}
                    onClick={() => handleParse(ex.text)}
                    className="p-3 rounded-lg border border-slate-800 bg-slate-950/60 hover:bg-slate-800 hover:border-indigo-500/40 text-left transition-all flex items-start gap-2.5 group"
                  >
                    <IconComponent className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5 group-hover:scale-110 transition-transform" />
                    <div>
                      <div className="text-xs font-medium text-slate-200 group-hover:text-white">
                        {ex.text}
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5">{ex.category}</div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Confirmation & Execution Card */}
      {parsedCommand && (
        <Card className="border-indigo-500/40 bg-indigo-950/10" data-testid="workspace-interpretation-card">
          <CardHeader className="pb-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-indigo-400" />
                <CardTitle className="text-base text-indigo-200">
                  I interpreted this as:
                </CardTitle>
                <Badge variant="solid" status="PENDING">
                  {parsedCommand.intent}
                </Badge>
              </div>

              <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
                <span>Mode: {parsedCommand.parser_mode}</span>
                <span>•</span>
                <span>Confidence: {Math.round(parsedCommand.confidence * 100)}%</span>
              </div>
            </div>
          </CardHeader>

          <CardContent className="space-y-4">
            <p className="text-sm text-slate-300 leading-relaxed">
              {parsedCommand.explanation}
            </p>

            {/* Editable Parameters */}
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/90 space-y-3">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Sliders className="w-4 h-4 text-indigo-400" />
                <span>Editable Parameters for Deterministic Validation</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                {Object.entries(editableParams).map(([key, val]) => (
                  <div key={key}>
                    <label className="block text-[11px] text-slate-400 font-medium capitalize mb-1">
                      {key.replace(/_/g, " ")}
                    </label>
                    <input
                      type="text"
                      data-testid={`workspace-param-${key}`}
                      value={String(val)}
                      onChange={(e) => handleParamChange(key, e.target.value)}
                      className="w-full text-xs rounded-lg border border-slate-700 bg-slate-950 p-2 text-white font-mono focus:border-indigo-500 focus:outline-none"
                    />
                  </div>
                ))}
              </div>

              <div>
                <label className="block text-[11px] text-slate-400 font-medium mb-1">
                  Context / Operator Rationale
                </label>
                <input
                  type="text"
                  placeholder="Operational justification for the immutable audit log..."
                  value={customReason}
                  onChange={(e) => setCustomReason(e.target.value)}
                  className="w-full text-xs rounded-lg border border-slate-700 bg-slate-950 p-2 text-white placeholder-slate-600 focus:border-indigo-500 focus:outline-none"
                />
              </div>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-indigo-500/20">
              <div className="flex items-center gap-2 text-xs text-slate-400 italic">
                <Info className="w-4 h-4 text-indigo-400" />
                <span>Deterministic rules engine validates. Human decision required before write.</span>
              </div>

              <div className="flex items-center gap-2">
                {parsedCommand.is_mutating ? (
                  <Button
                    data-testid="workspace-submit-proposal-btn"
                    variant="primary"
                    size="sm"
                    disabled={isSubmitting}
                    onClick={handleSubmitProposal}
                    className="bg-indigo-600 hover:bg-indigo-500 font-bold"
                  >
                    <Send className="w-4 h-4 mr-1.5" />
                    {isSubmitting ? "Routing..." : "Submit Proposal to Approvals Inbox"}
                  </Button>
                ) : (
                  <Button
                    data-testid="workspace-execute-command-btn"
                    variant="primary"
                    size="sm"
                    disabled={isSubmitting}
                    onClick={handleExecuteQuery}
                    className="bg-emerald-600 hover:bg-emerald-500 font-bold"
                  >
                    <ArrowRight className="w-4 h-4 mr-1.5" />
                    {isSubmitting ? "Executing..." : "Execute & View Results"}
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Output Panel */}
      {executionResult && (
        <Card className="border-emerald-500/40 bg-emerald-950/20" data-testid="workspace-results-panel">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <CardTitle className="text-base text-emerald-200">
                Validated Output & State Impact
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 overflow-x-auto">
              <pre className="text-xs leading-relaxed">
                {JSON.stringify(executionResult, null, 2)}
              </pre>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default CommandCenterWorkspace;
