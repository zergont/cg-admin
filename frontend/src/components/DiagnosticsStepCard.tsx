import { cn } from "@/lib/utils";

export type StepStatus = "ok" | "warn" | "crit" | "skip";

export interface DiagnosticsStep {
  id: string;
  name: string;
  status: StepStatus;
  message: string;
  details: string[];
  duration_ms: number;
}

const STATUS_DOT: Record<StepStatus, string> = {
  ok: "bg-status-ok",
  warn: "bg-status-warn",
  crit: "bg-status-crit",
  skip: "bg-muted-foreground",
};

const STATUS_BORDER: Record<StepStatus, string> = {
  ok: "border-status-ok/30",
  warn: "border-status-warn/30",
  crit: "border-status-crit/30",
  skip: "border-border",
};

export function DiagnosticsStepCard({ step }: { step: DiagnosticsStep }) {
  const hasDetails = step.details.length > 0;

  return (
    <div
      className={cn(
        "rounded-lg border bg-card p-4",
        STATUS_BORDER[step.status],
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          {/* Статусный индикатор */}
          <span
            className={cn(
              "mt-0.5 h-3 w-3 shrink-0 rounded-full",
              STATUS_DOT[step.status],
            )}
          />
          <div className="min-w-0">
            <div className="font-medium text-sm">{step.name}</div>
            <div
              className={cn(
                "text-sm mt-0.5",
                step.status === "skip"
                  ? "text-muted-foreground italic"
                  : "text-foreground/80",
              )}
            >
              {step.message}
            </div>
          </div>
        </div>
        {/* Время */}
        {step.duration_ms > 0 && (
          <span className="shrink-0 text-xs text-muted-foreground font-mono">
            {step.duration_ms} мс
          </span>
        )}
      </div>

      {/* Details — раскрываемый блок */}
      {hasDetails && (
        <details className="mt-3 ml-6">
          <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground transition-colors select-none">
            Подробнее
          </summary>
          <ul className="mt-2 space-y-1">
            {step.details.map((line, i) => (
              <li key={i} className="text-xs text-muted-foreground font-mono">
                {line}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
