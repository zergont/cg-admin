import { Outlet, NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  ArrowDownToLine,
  ScrollText,
  ArrowLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { TooltipProvider } from "@/components/ui/tooltip";

const NAV = [
  { to: "/", label: "Обзор", icon: LayoutDashboard, end: true },
  { to: "/updates", label: "Обновления", icon: ArrowDownToLine, end: false },
  { to: "/audit", label: "Аудит", icon: ScrollText, end: false },
] as const;

export function Layout() {
  return (
    <TooltipProvider>
      <div className="min-h-screen flex flex-col">
        {/* Header */}
        <header className="border-b border-border bg-card px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon-sm" asChild>
              <a href="/" title="Вернуться в Dashboard">
                <ArrowLeft className="h-4 w-4" />
              </a>
            </Button>
            <Separator orientation="vertical" className="h-5" />
            <h1 className="text-lg font-semibold tracking-tight">CG Admin</h1>
            <span className="text-xs text-muted-foreground">v0.1.0</span>
          </div>

          <nav className="flex items-center gap-1">
            {NAV.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                    isActive
                      ? "bg-secondary text-foreground"
                      : "text-muted-foreground hover:text-foreground hover:bg-secondary/50",
                  )
                }
              >
                <Icon className="h-4 w-4" />
                {label}
              </NavLink>
            ))}
          </nav>
        </header>

        {/* Content */}
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </TooltipProvider>
  );
}
