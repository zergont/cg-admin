import { cn } from "@/lib/utils";

interface OsHealthBarProps {
  label: string;
  value: number;
  detail?: string;
}

export function OsHealthBar({ label, value, detail }: OsHealthBarProps) {
  const color =
    value >= 90
      ? "bg-[var(--status-crit)]"
      : value >= 70
        ? "bg-[var(--status-warn)]"
        : "bg-[var(--status-ok)]";

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium tabular-nums">
          {value.toFixed(1)}%
          {detail && (
            <span className="ml-1.5 text-xs text-muted-foreground">
              {detail}
            </span>
          )}
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-secondary">
        <div
          className={cn("h-full rounded-full transition-all", color)}
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
    </div>
  );
}
