import type { Metadata } from "next";
import "./globals.css";
import { TooltipProvider } from "@/components/ui/tooltip";

export const metadata: Metadata = {
  title: "Intelletrics — The answer’s in your spreadsheet",
  description:
    "Explore CSV and Excel files with charts, statistics, and answers grounded in your data. No code or SQL needed.",
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
