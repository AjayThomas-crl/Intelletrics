import type { Metadata } from "next";
import "./globals.css";
import { TooltipProvider } from "@/components/ui/tooltip";

export const metadata: Metadata = {
  title: "Intelletrics — AI-Powered Data Analytics",
  description:
    "Upload CSV or Excel files for instant statistical profiling, interactive charts, and AI-generated insights. No code required.",
  icons: {
    icon: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return ( 
    <html lang="en" className="h-full dark antialiased">
      <body className="min-h-full flex flex-col">
        <TooltipProvider>
          <main className="flex-1">{children}</main>
        </TooltipProvider>
      </body>
    </html>
  );
}
