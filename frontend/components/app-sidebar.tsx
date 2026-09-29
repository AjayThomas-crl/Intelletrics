"use client"

import * as React from "react"
import Image from "next/image"
import { createClient } from "@/lib/supabase/client"

import { NavMain } from "@/components/nav-main"
import { NavUser } from "@/components/nav-user"
import { TeamSwitcher } from "@/components/team-switcher"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
} from "@/components/ui/sidebar"
import { BarChart3Icon, HistoryIcon } from "lucide-react"

// App-specific sidebar content. The sidebar primitives remain shared shadcn components.
const data = {
  teams: [
    {
      name: "Intelletrics",
      logo: <Image src="/icon.svg" alt="Intelletrics" width={32} height={32} className="size-8 rounded-lg" />,
      plan: "Open source",
    },
  ],
  navMain: [
    {
      title: "Dashboard",
      url: "/dashboard",
      icon: <BarChart3Icon />,
      isActive: true,
    },
    {
      title: "History",
      url: "/history",
      icon: <HistoryIcon />,
    },
  ],
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const supabase = createClient()
  const [user, setUser] = React.useState({
    name: "Loading…",
    email: "",
    avatar: "",
  })

  React.useEffect(() => {
    const updateUser = (authUser: {
      email?: string
      user_metadata?: Record<string, unknown>
    } | null) => {
      const metadata = authUser?.user_metadata ?? {}
      const name = typeof metadata.full_name === "string"
        ? metadata.full_name
        : typeof metadata.name === "string"
          ? metadata.name
          : authUser?.email?.split("@")[0] ?? "Account"
      const avatar = typeof metadata.avatar_url === "string"
        ? metadata.avatar_url
        : typeof metadata.picture === "string"
          ? metadata.picture
          : ""

      setUser({
        name,
        email: authUser?.email ?? "",
        avatar,
      })
    }

    supabase.auth.getUser().then(({ data: authData }) => updateUser(authData.user))
    const { data: subscription } = supabase.auth.onAuthStateChange((_event, session) => {
      updateUser(session?.user ?? null)
    })

    return () => subscription.subscription.unsubscribe()
  }, [supabase])

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <TeamSwitcher teams={data.teams} />
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={data.navMain} />
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={user} />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
