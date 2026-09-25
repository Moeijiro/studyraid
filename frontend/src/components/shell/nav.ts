import { ChartColumn, Hourglass, LayoutDashboard, ScrollText, Swords, Trophy } from "lucide-react";

export const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/quests", label: "Quests", icon: ScrollText },
  { href: "/focus", label: "Focus", icon: Hourglass },
  { href: "/party", label: "Party", icon: Swords },
  { href: "/analytics", label: "Analytics", icon: ChartColumn },
  { href: "/achievements", label: "Achievements", icon: Trophy },
] as const;
