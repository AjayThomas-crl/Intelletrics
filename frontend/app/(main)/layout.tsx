import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";

export default function MainLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <SidebarProvider className="h-screen ">
      <AppSidebar />
      <main className="flex flex-1 flex-col min-h-0 overflow-y-auto overflow-x-hidden">
        {children}
      </main>
    </SidebarProvider>
  );
}
