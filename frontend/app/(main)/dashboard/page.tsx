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
  CardFooter,
} from "@/components/ui/card";
import { useRef, useState } from "react";

interface UploadData {
  filename: string;
  content_type: string;
  rows: number;
  columns: number;
  column_names: string[];
  preview: Record<string, string | number>[];
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
    <div className="flex flex-col h-full overflow-hidden">
      <header className="flex h-14 shrink-0 items-center gap-2 px-4 border-b">
        <SidebarTrigger />
        <Separator orientation="vertical" className="h-4" />
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

      <div className="flex flex-col flex-1 gap-3 p-4 pt-3 min-h-0 overflow-hidden">
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

        {/* Preview — fills remaining space */}
        {uploadData && (
          <div className="flex flex-col flex-1 gap-3 min-h-0">
            {/* Dataset info bar — minimal */}
            <div className="flex justify-between">
              <p className="text-2xl font-bold">Uploaded File</p>
              <button
                onClick={() => inputRef.current?.click()}
                className=" items-center gap-1.5 rounded-md bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors cursor-pointer"
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

            {/* Data Preview Table — scrollable internally */}
            <h1 className="text-base font-semibold">Preview (first 10 rows)</h1>
            <Card className="flex flex-col flex min-h-0">
              <CardContent className="p-0 flex-1 min-h-0 overflow-auto">
                <table className="min-w-full text-sm border-collapse">
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
          </div>
        )}
      </div>
    </div>
  );
}
