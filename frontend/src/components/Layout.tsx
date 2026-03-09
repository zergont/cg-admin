import { useState } from "react";
import { Outlet, NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  ArrowDownToLine,
  ScrollText,
  Stethoscope,
  ArrowLeft,
  KeyRound,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { TooltipProvider } from "@/components/ui/tooltip";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { setToken, getToken } from "@/lib/api";

const NAV = [
  { to: "/", label: "Обзор", icon: LayoutDashboard, end: true },
  { to: "/updates", label: "Обновления", icon: ArrowDownToLine, end: false },
  { to: "/audit", label: "Аудит", icon: ScrollText, end: false },
  { to: "/diagnostics", label: "Диагностика", icon: Stethoscope, end: false },
] as const;

export function Layout() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [hasToken, setHasToken] = useState(() => !!getToken());

  function openTokenDialog() {
    setInputValue(getToken());
    setDialogOpen(true);
  }

  function saveToken() {
    const trimmed = inputValue.trim();
    setToken(trimmed);
    localStorage.setItem("cg-admin-token", trimmed);
    setHasToken(!!trimmed);
    setDialogOpen(false);
  }

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
            <span className="text-xs text-muted-foreground">v0.3.1</span>
          </div>

          <div className="flex items-center gap-2">
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

            <Separator orientation="vertical" className="h-5" />

            <Button
              variant="ghost"
              size="icon-sm"
              onClick={openTokenDialog}
              title={hasToken ? "Bearer-токен задан" : "Задать Bearer-токен"}
              className={cn(
                "transition-colors",
                hasToken
                  ? "text-emerald-400 hover:text-emerald-300"
                  : "text-yellow-400 hover:text-yellow-300",
              )}
            >
              <KeyRound className="h-4 w-4" />
            </Button>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>

      {/* Token dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Bearer-токен</DialogTitle>
          </DialogHeader>

          <div className="flex flex-col gap-2 py-2">
            <label className="text-sm text-muted-foreground">
              Вставьте токен из&nbsp;<code className="text-xs">config.yaml → auth.token</code>
            </label>
            <input
              type="password"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && saveToken()}
              placeholder="4879d3f5..."
              className={cn(
                "w-full rounded-md border border-input bg-background px-3 py-2",
                "text-sm placeholder:text-muted-foreground",
                "focus:outline-none focus:ring-2 focus:ring-ring",
              )}
              autoFocus
            />
          </div>

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Отмена
            </Button>
            <Button onClick={saveToken}>Сохранить</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </TooltipProvider>
  );
}
