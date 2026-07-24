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
import { useRef, useState, useMemo } from "react";
import { ChartRenderer, type BackendProfile } from "@/components/charts/chart-renderer";
import { ChatPanel } from "@/components/chat/chat-panel";
import { Loader2Icon } from "lucide-react";

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

  const profileByColumn = useMemo(() => {
    if (!uploadData?.profiles) return {};
    const map: Record<string, BackendProfile> = {};
    for (const p of uploadData.profiles) {
      map[p.name] = p;
    }
    return map;
  }, [uploadData?.profiles]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);
    setUploadLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/upload", {
        method: "POST",
        body: formData,
      });
      const data: UploadData = await response.json();
      setUploadData(data);
    } catch (err) {
      console.error("Upload failed:", err);
    } finally {
      setUploadLoading(false);
    }
  };

  return (
    <div className="flex flex-col flex-1 h-full">
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
      <div className="flex flex-1 min-h-0">
        {/* Left: data content */}
        <div className="flex-1 overflow-y-auto p-4 pt-3">
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
                  onClick={() => inputRef.current?.click()}
                  className="flex w-full cursor-pointer items-center justify-center rounded-xl border-2 border-dashed bg-muted/50 hover:bg-muted/70 transition-colors py-16"
                >
                  <div className="text-center">
                    <p className="text-lg font-medium">
                      Upload your .csv/.xlsx files
                    </p>
                    <p className="text-muted-foreground">
                      Drag & drop or click to browse
                    </p>
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
              <h1 className="text-base font-semibold">Preview (first 10 rows)</h1>
              <Card className="flex flex-col max-h-[400px]">
                <CardContent className="p-0 flex-1 min-h-0 overflow-y-auto overflow-x-hidden">
                  <table className="w-full text-sm table-fixed border-collapse">
                    <thead className="sticky top-0 bg-card">
                      <tr className="border-b">
                        {uploadData.column_names.map((col) => (
                          <th
                            key={col}
                            className="text-left px-3 py-2 font-medium text-muted-foreground whitespace-nowrap"
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
                              className="px-3 py-2 min-w-[100px] truncate max-w-[250px]"
                              title={String(row[col] ?? "")}
                            >
                              {row[col] ?? "—"}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>

              {/* Column Charts */}
              {uploadData.charts.length > 0 && (
                <div className="flex flex-wrap gap-3">
                  {uploadData.charts.map((chart, i) => (
                    <div
                      key={`${chart.column}-${i}`}
                      className="w-full sm:w-[calc(50%-0.375rem)] lg:w-[calc(33.333%-0.5rem)]"
                    >
                      <ChartRenderer
                        chart={chart}
                        profile={profileByColumn[chart.column]}
                      />
                    </div>
                  ))}
                </div>
              )}
              {/* AI Summary / Insights */}
              {uploadData.insights && uploadData.insights.length > 0 && (
                <Card>
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
          <div className="w-[400px] shrink-0">
            <ChatPanel datasetId={uploadData.dataset_id} />
          </div>
        )}
      </div>
    </div>
  );
}
