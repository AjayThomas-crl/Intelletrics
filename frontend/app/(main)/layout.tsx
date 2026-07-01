import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";

export default function MainLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <SidebarProvider className="h-screen overflow-hidden">
      <AppSidebar />
      <main className="flex flex-1 flex-col min-h-0 overflow-hidden">
        {children}
      </main>
    </SidebarProvider>
  );
}
