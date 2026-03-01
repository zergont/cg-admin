import { useNavigate } from "react-router-dom";
import { ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";

interface ServiceCardProps {
  name: string;
  unit: string;
  status: string;
  subState: string;
  indicator: "ok" | "warn" | "crit";
  version?: string | null;
  url?: string | null;
}

const INDICATOR_STYLES = {
  ok: "bg-[var(--status-ok)]",
  warn: "bg-[var(--status-warn)]",
  crit: "bg-[var(--status-crit)]",
} as const;

export function ServiceCard({
  name,
  unit,
  status,
  subState,
  indicator,
  version,
  url,
}: ServiceCardProps) {
  const navigate = useNavigate();

  return (
    <div
      onClick={() => navigate(`/service/${unit}`)}
      className={cn(
        "flex items-center gap-4 rounded-lg border border-border bg-card p-4",
        "cursor-pointer transition-colors hover:bg-secondary/40",
      )}
    >
      {/* Индикатор */}
      <div
        className={cn(
          "h-3 w-3 shrink-0 rounded-full",
          INDICATOR_STYLES[indicator],
        )}
      />

      {/* Имя + статус */}
      <div className="flex-1 min-w-0">
        <div className="font-medium truncate">{name}</div>
        <div className="text-xs text-muted-foreground">
          {status} ({subState})
        </div>
      </div>

      {/* Версия */}
      {version && (
        <span className="text-xs text-muted-foreground font-mono">
          {version}
        </span>
      )}

      {/* Внешняя ссылка */}
      {url && (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="text-muted-foreground hover:text-foreground transition-colors"
        >
          <ExternalLink className="h-4 w-4" />
        </a>
      )}
    </div>
  );
}
