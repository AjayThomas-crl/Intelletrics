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
import { useRef } from "react";
export default function Page() {
  const inputRef = useRef<HTMLInputElement>(null);
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) {
      return;
    }
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch("http://127.0.0.1:8000/upload", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();

    console.log(data);
  };
  return (
    <>
      <header className="flex h-16 shrink-0 items-center gap-2 transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-12">
        <div className="flex items-center gap-2 px-4">
          <SidebarTrigger className="-ml-1" />
          <Separator
            orientation="vertical"
            className="mr-2 data-vertical:h-4 data-vertical:self-auto"
          />
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem className="hidden md:block">
                <BreadcrumbLink href="#">Build Your Application</BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator className="hidden md:block" />
              <BreadcrumbItem>
                <BreadcrumbPage>Data Fetching</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
        </div>
      </header>
      <div className="flex flex-1 flex-col gap-4 p-4 pt-0">
        <div className="">
          <div className="flex border items-center justify-center min-h-[100px] md:min-h-[300px] lg:min-h-[400px] w-full rounded-xl bg-muted/50">
            <div
              onClick={() => inputRef.current?.click()}
              className="flex min-h-[400px] w-full items-center justify-center rounded-xl border-2 border-dashed bg-muted/50"
            >
              <div className="text-center ">
                <input type="file" onChange={handleFileUpload} ref={inputRef} hidden />
                <p className="text-lg font-medium">
                  Upload your .csv/.xlsx files
                </p>
                <p className="text-muted-foreground">
                  Drag & drop or click to browse
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
