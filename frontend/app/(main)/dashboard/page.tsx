"use client";

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useRef, useState } from "react";
import { ChartRenderer } from "@/components/charts/chart-renderer";
import { ChatPanel } from "@/components/chat/chat-panel";
import { apiFetch } from "@/lib/api";
import { Upload } from "lucide-react";

interface UploadData {
  dataset_id: string;
  filename: string;
  content_type: string;
  rows: number;
  columns: number;
  column_names: string[];
  preview: Record<string, string | number>[];
  charts: Chart[];
  profiles: Profile[];
  summary: string;
  insights: Insight[];
}
interface Insight {
  title: string;
  detail: string;
  category: string;
  affected_columns: string[];
}
interface Profile {
  name: string;
  missing: {
    count: number;
    percentage: number;
  };
  uniqueness: {
    count: number;
    ratio: number;
  };
  statistics?: {
    mean?: number;
    median?: number;
    std?: number;
    min?: number;
    max?: number;
    q1?: number;
    q3?: number;
  };
  distribution?: {
    top_value: string | number;
    top_count: number;
  };
  type: string;
}
interface Chart {
  chart: string;
  column: string;
  labels: (string | number)[];
  values: number[];
  description?: string;
}
export default function Page() {
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadData, setUploadData] = useState<UploadData | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);
    setUploadLoading(true);

    try {
      const response = await apiFetch("/upload", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(error.detail || `Upload failed (${response.status})`);
      }
      const data: UploadData = await response.json();
      setUploadData(data);
    } catch (err) {
      console.error("Upload failed:", err);
    } finally {
      setUploadLoading(false);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col h-full">
      <header className="flex h-14 shrink-0 items-center gap-2 px-4 border-b">
        <SidebarTrigger />
        <Separator orientation="vertical" className="my-5 h-4" />
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem className="hidden md:block">
              <BreadcrumbLink href="#">Intelletrics</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator className="hidden md:block" />
            <BreadcrumbItem>
              <BreadcrumbPage>Dashboard</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </header>

      {/* Two-column layout: data content | chat */}
      <div className="flex min-h-0 min-w-0 flex-1 overflow-hidden">
        {/* Left: data content */}
        <div className="min-h-0 min-w-0 flex-1 overflow-y-auto overflow-x-hidden p-4 pt-3">
          {/* Hidden file input — always in DOM */}
          <input
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={handleFileUpload}
            ref={inputRef}
            hidden
          />

          {/* Upload Area — shown before any upload */}
          {!uploadData && (
            <>
              {uploadLoading ? (
                <div className="flex items-center justify-center rounded-xl border-2 border-dashed bg-muted/50 py-16">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                </div>
              ) : (
                <div
                  id="upload"
                  onClick={() => inputRef.current?.click()}
                  className="dashboard-empty-state flex w-full cursor-pointer items-center justify-center rounded-xl border-2 border-dashed bg-muted/50 hover:bg-muted/70 transition-colors py-16"
                >
                  <div className="text-center">
                    <Upload className="mx-auto mb-3 size-8 text-primary" />
                    <p className="text-lg font-medium">Upload a dataset to begin</p>
                    <p className="mt-1 text-sm text-muted-foreground">Drop a CSV or Excel file here, or click to browse</p>
                    <p className="mt-3 text-xs text-muted-foreground/70">Your preview, charts, profile, and AI insights will appear here.</p>
                  </div>
                </div>
              )}
            </>
          )}

          {/* Data content */}
          {uploadData && (
            <div className="flex flex-col gap-3">
              {/* Dataset info bar */}
              <div className="flex justify-between">
                <p className="text-2xl font-bold">Uploaded File</p>
                <button
                  onClick={() => inputRef.current?.click()}
                  className="items-center gap-1.5 rounded-md bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors cursor-pointer"
                >
                  Upload another file
                </button>
              </div>
              <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-muted/40 shrink-0">
                <span className="text-sm font-medium truncate min-w-0 max-w-[300px]">
                  {uploadData.filename}
                </span>
                <span className="text-muted-foreground/40 shrink-0">|</span>
                <span className="text-xs text-muted-foreground whitespace-nowrap shrink-0">
                  <strong className="text-foreground">
                    {uploadData.rows.toLocaleString()}
                  </strong>{" "}
                  rows
                </span>
                <span className="text-muted-foreground/40 shrink-0">|</span>
                <span className="text-xs text-muted-foreground whitespace-nowrap shrink-0">
                  <strong className="text-foreground">
                    {uploadData.columns}
                  </strong>{" "}
                  cols
                </span>
              </div>

              {/* Data Preview Table */}
              <h1 id="preview" className="text-base font-semibold">Preview (first 10 rows)</h1>
              <Card className="flex max-w-full flex-col">
                <CardContent className="min-w-0 overflow-hidden p-0">
                  <div
                    role="region"
                    aria-label="Dataset preview. Scroll horizontally to see all columns."
                    tabIndex={0}
                    className="max-h-[400px] overflow-auto rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <table className="w-max min-w-full border-collapse text-sm">
                    <thead className="sticky top-0 z-10 bg-card">
                      <tr className="border-b">
                        {uploadData.column_names.map((col) => (
                          <th
                            key={col}
                            className="max-w-[200px] min-w-[120px] overflow-hidden text-ellipsis whitespace-nowrap px-3 py-2 text-left font-medium text-muted-foreground"
                            title={col}
                          >
                              {col}
                            </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {uploadData.preview.map((row, i) => (
                        <tr
                          key={i}
                          className="border-b last:border-0 hover:bg-muted/50 transition-colors"
                        >
                          {uploadData.column_names.map((col) => (
                            <td
                              key={col}
                              className="max-w-[220px] truncate px-3 py-2"
                              title={String(row[col] ?? "")}
                            >
                              {row[col] ?? "—"}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>

              {/* Column Charts */}
              {uploadData.charts.length > 0 && (
                <div id="profiles" className="grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2 2xl:grid-cols-3">
                  {uploadData.charts.map((chart, i) => (
                    <div key={`${chart.column}-${i}`} className="min-w-0">
                      <ChartRenderer chart={chart} />
                    </div>
                  ))}
                </div>
              )}
              {/* AI Summary / Insights */}
              {uploadData.insights && uploadData.insights.length > 0 && (
                <Card id="insights">
                  <CardHeader>
                    <CardTitle className="text-base font-semibold">
                      AI Insights
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-4">
                    {uploadData.summary && (
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        {uploadData.summary}
                      </p>
                    )}
                    <ul className="space-y-3 text-sm">
                      {uploadData.insights.map((insight, i) => (
                        <li key={i} className="flex gap-2">
                          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                          <div className="flex flex-col gap-0.5 min-w-0">
                            <span className="flex items-center gap-2 flex-wrap">
                              <span className="font-medium text-foreground">
                                {insight.title}
                              </span>
                              <span className="text-[10px] uppercase tracking-wider text-muted-foreground/60 border rounded px-1.5 py-0.5">
                                {insight.category.replace(/_/g, " ")}
                              </span>
                            </span>
                            <span className="text-muted-foreground">
                              {insight.detail}
                            </span>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </div>

        {/* Right: Chat Panel */}
        {uploadData && (
          <div className="h-full min-h-0 w-[400px] shrink-0 overflow-hidden">
            <ChatPanel key={uploadData.dataset_id} datasetId={uploadData.dataset_id} />
          </div>
        )}
      </div>
    </div>
  );
}
