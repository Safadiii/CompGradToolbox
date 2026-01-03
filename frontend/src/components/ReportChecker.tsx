import { useMemo, useState } from "react";
import {
  Upload,
  FileText,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Download,
  ChevronDown,
  ChevronRight,
  Info,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";

import {
  uploadPdfToChecker,
  type CheckerReport,
  type CheckerType,
} from "../lib/checkersApi"; // <-- IMPORTANT: components -> lib is ../lib

interface ReportCheckerProps {
  type: CheckerType; // "comp590" | "comp291-391"
}

type UiCheck = {
  id: string;
  name: string;
  status: "pass" | "warning" | "fail";
  page?: number | null;
  detail?: string;
};

function downloadJson(filename: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export default function ReportChecker({ type }: ReportCheckerProps) {
  const [uploadedFile, setUploadedFile] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [expandedIssues, setExpandedIssues] = useState<string[]>([]);
  const [report, setReport] = useState<CheckerReport | null>(null);

  const toggleIssue = (id: string) => {
    setExpandedIssues((prev) => (prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]));
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "pass":
        return <CheckCircle2 className="w-5 h-5 text-green-600" />;
      case "warning":
        return <AlertTriangle className="w-5 h-5 text-amber-600" />;
      case "fail":
        return <XCircle className="w-5 h-5 text-red-600" />;
      default:
        return null;
    }
  };

  // Map backend report -> UI checks
  const checks: UiCheck[] = useMemo(() => {
    if (!report) return [];

    const ui: UiCheck[] = [];

    const anyHit = report.pages.some((p) => (p.hits?.length ?? 0) > 0);
    if (!anyHit) {
      ui.push({
        id: "no-labels",
        name: "Signature label text found",
        status: "warning",
        detail:
          "No signature labels were found in the PDF text layer. If this is a scanned PDF, label detection may fail without OCR.",
      });
    }

    // One check per hit
    for (const p of report.pages) {
      for (const hit of p.hits || []) {
        const passFail = hit.status === "FOUND" ? "pass" : "fail";
        const label = hit.label_or_pattern ?? "Signature (fallback)";
        const candidatesCount = hit.candidates?.length ?? 0;

        ui.push({
          id: `p${p.page}-h${hit.hit_index}`,
          name: label,
          status: passFail,
          page: p.page,
          detail:
            hit.status === "FOUND"
              ? `Signature-like ink detected near this label. Candidates: ${candidatesCount}.`
              : `No signature-like ink detected near this label. Candidates: ${candidatesCount}.`,
        });
      }
    }

    // Overall summary check
    ui.push({
      id: "overall",
      name: "Overall signature status",
      status: report.overall_status === "FOUND" ? "pass" : "fail",
      detail:
        report.overall_status === "FOUND"
          ? "At least one signature-like region was detected."
          : "No signature-like region was detected based on current rules.",
    });

    return ui;
  }, [report]);

  const passCount = checks.filter((c) => c.status === "pass").length;
  const warningCount = checks.filter((c) => c.status === "warning").length;
  const failCount = checks.filter((c) => c.status === "fail").length;

  const overallUiStatus: "pass" | "warning" | "fail" = useMemo(() => {
    if (failCount > 0) return "fail";
    if (warningCount > 0) return "warning";
    return "pass";
  }, [failCount, warningCount]);

  async function runChecker(file: File) {
    setUploadedFile(true);
    setFileName(file.name);
    setLoading(true);
    setError(null);
    setReport(null);
    setExpandedIssues([]);

    try {
      const result = await uploadPdfToChecker(type, file, false); // debug=false
      setReport(result);
    } catch (e: any) {
      setError(e?.message || "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  const title = type === "comp590" ? "COMP590 Seminar Report" : "COMP291/391 Internship Report";

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>Upload your report for automated format validation</CardDescription>
        </CardHeader>

        <CardContent>
          {!uploadedFile ? (
            <div className="space-y-4">
              <div className="border-2 border-dashed border-neutral-300 rounded-lg p-8 text-center hover:border-neutral-400 transition-colors">
                <div className="flex flex-col items-center gap-3">
                  <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                    <Upload className="w-6 h-6 text-blue-700" />
                  </div>

                  <div>
                    <p className="text-sm text-neutral-900 mb-1">Drop your PDF here or click to browse</p>
                    <p className="text-xs text-neutral-500">Maximum file size: 10MB</p>
                  </div>

                  <input
                    id={`pdf-upload-${type}`}
                    type="file"
                    accept="application/pdf"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) runChecker(f);
                    }}
                  />

                  <label htmlFor={`pdf-upload-${type}`}>
                    <Button asChild>
                      <span>Upload PDF</span>
                    </Button>
                  </label>
                </div>
              </div>

              <div className="flex items-start gap-2 p-4 bg-amber-50 rounded-lg border border-amber-200">
                <Info className="w-5 h-5 text-amber-700 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-amber-900">
                  <p className="mb-1">This checker validates format and structure only. It does NOT grade content.</p>
                  <p className="text-amber-700">Passing all checks does not guarantee passing the course.</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between p-4 bg-neutral-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <FileText className="w-8 h-8 text-blue-600" />
                  <div>
                    <div className="text-sm text-neutral-900">{fileName ?? "report.pdf"}</div>
                    <div className="text-xs text-neutral-500">
                      {loading ? "Running checker…" : report ? "Checked" : error ? "Failed" : "Uploaded"}
                    </div>
                  </div>
                </div>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setUploadedFile(false);
                    setFileName(null);
                    setReport(null);
                    setError(null);
                    setExpandedIssues([]);
                  }}
                >
                  Remove
                </Button>
              </div>

              {loading && <div className="text-sm text-neutral-600">Analyzing PDF…</div>}
              {error && <div className="text-sm text-red-600">{error}</div>}
            </div>
          )}
        </CardContent>
      </Card>

      {report && (
        <>
          <div className="grid md:grid-cols-3 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl text-green-600">{passCount}</div>
                    <div className="text-sm text-neutral-600">Passed</div>
                  </div>
                  <CheckCircle2 className="w-8 h-8 text-green-600" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl text-amber-600">{warningCount}</div>
                    <div className="text-sm text-neutral-600">Warnings</div>
                  </div>
                  <AlertTriangle className="w-8 h-8 text-amber-600" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl text-red-600">{failCount}</div>
                    <div className="text-sm text-neutral-600">Failed</div>
                  </div>
                  <XCircle className="w-8 h-8 text-red-600" />
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>Report Status</CardTitle>
                      <CardDescription>
                        {failCount > 0
                          ? `${failCount} issue${failCount > 1 ? "s" : ""} found`
                          : warningCount > 0
                          ? `${warningCount} warning${warningCount > 1 ? "s" : ""} found`
                          : "All checks passed"}
                      </CardDescription>
                    </div>

                    {overallUiStatus === "pass" ? (
                      <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                        <CheckCircle2 className="w-7 h-7 text-green-600" />
                      </div>
                    ) : overallUiStatus === "warning" ? (
                      <div className="w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center">
                        <AlertTriangle className="w-7 h-7 text-amber-600" />
                      </div>
                    ) : (
                      <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
                        <XCircle className="w-7 h-7 text-red-600" />
                      </div>
                    )}
                  </div>
                </CardHeader>

                <CardContent>
                  <div className="space-y-2">
                    {checks.map((check) => (
                      <div key={check.id} className="border border-neutral-200 rounded-lg overflow-hidden">
                        <button
                          onClick={() => check.detail && toggleIssue(check.id)}
                          className="w-full flex items-center justify-between p-4 hover:bg-neutral-50 transition-colors text-left"
                        >
                          <div className="flex items-center gap-3 flex-1 min-w-0">
                            {getStatusIcon(check.status)}
                            <div className="flex-1 min-w-0">
                              <div className="text-sm text-neutral-900">{check.name}</div>
                              {check.page ? <div className="text-xs text-neutral-500">Page {check.page}</div> : null}
                            </div>
                          </div>

                          {check.detail && (
                            <span>
                              {expandedIssues.includes(check.id) ? (
                                <ChevronDown className="w-4 h-4 text-neutral-400" />
                              ) : (
                                <ChevronRight className="w-4 h-4 text-neutral-400" />
                              )}
                            </span>
                          )}
                        </button>

                        {check.detail && expandedIssues.includes(check.id) && (
                          <div className="px-4 pb-4 pt-2 bg-neutral-50 border-t border-neutral-200">
                            <p className="text-sm text-neutral-700 leading-relaxed">{check.detail}</p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            <div>
              <Card>
                <CardHeader>
                  <CardTitle>Actions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Button className="w-full gap-2" disabled>
                    <Download className="w-4 h-4" />
                    Download Feedback PDF (coming soon)
                  </Button>

                  <Button
                    variant="outline"
                    className="w-full gap-2"
                    onClick={() => downloadJson(`${type}_report.json`, report)}
                  >
                    <Download className="w-4 h-4" />
                    Export Summary (JSON)
                  </Button>

                  <div className="pt-4 border-t border-neutral-200">
                    <h4 className="text-sm text-neutral-900 mb-2">Overall</h4>
                    <div className="flex justify-between text-sm">
                      <span className="text-neutral-600">Status:</span>
                      {report.overall_status === "FOUND" ? (
                        <Badge className="bg-green-100 text-green-700 border-green-200">Signature detected</Badge>
                      ) : (
                        <Badge className="bg-red-100 text-red-700 border-red-200">Not detected</Badge>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
