import { useState } from "react";
import { Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { DiagnosticsChain } from "@/components/DiagnosticsChain";
import { cn } from "@/lib/utils";
import type { StepStatus, DiagnosticsStep } from "@/components/DiagnosticsStepCard";

interface DiagnosticsReport {
  started_at: string;
  duration_ms: number;
  overall: StepStatus;
  steps: DiagnosticsStep[];
}

// ── Статичная схема pipeline ──────────────────────────────────

const PIPELINE_NODES = [
  "Роутер",
  "MQTT",
  "Декодер",
  "DB-Writer",
  "PostgreSQL",
  "Dashboard",
];

function PipelineSchemaStatic() {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs text-muted-foreground mb-3">Схема прохождения данных</p>
      <div className="flex flex-wrap items-center gap-1">
        {PIPELINE_NODES.map((node, idx) => (
          <div key={node} className="flex items-center gap-1">
            <span className="rounded border border-border bg-secondary px-2.5 py-1 text-xs font-medium">
              {node}
            </span>
            {idx < PIPELINE_NODES.length - 1 && (
              <span className="text-muted-foreground text-xs">→</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Итоговый баннер ───────────────────────────────────────────

const OVERALL_STYLES: Record<StepStatus, string> = {
  ok: "bg-status-ok/15 border-status-ok/40 text-status-ok",
  warn: "bg-status-warn/15 border-status-warn/40 text-status-warn",
  crit: "bg-status-crit/15 border-status-crit/40 text-status-crit",
  skip: "bg-muted border-border text-muted-foreground",
};

const OVERALL_TEXT: Record<StepStatus, string> = {
  ok: "Все системы работают нормально",
  warn: "Обнаружены предупреждения",
  crit: "Обнаружены критические проблемы",
  skip: "Нет данных",
};

function OverallBanner({
  overall,
  duration,
}: {
  overall: StepStatus;
  duration: number;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border px-4 py-3 flex items-center justify-between",
        OVERALL_STYLES[overall],
      )}
    >
      <span className="font-medium text-sm">{OVERALL_TEXT[overall]}</span>
      <span className="text-xs opacity-70 font-mono">{duration} мс</span>
    </div>
  );
}

// ── Страница диагностики ──────────────────────────────────────

export function DiagnosticsPage() {
  const [report, setReport] = useState<DiagnosticsReport | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    try {
      const data = await apiFetch<DiagnosticsReport>("/diagnostics/run");
      setReport(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Заголовок + кнопка */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Диагностика Pipeline</h2>
          <p className="text-sm text-muted-foreground">
            Проверка сквозной цепочки прохождения данных
          </p>
        </div>
        <Button onClick={handleRun} disabled={running}>
          {running && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
          {running ? "Проверяю…" : "Проверить"}
        </Button>
      </div>

      {/* Статичная схема pipeline */}
      <PipelineSchemaStatic />

      {/* Ошибка запроса */}
      {error && (
        <div className="rounded-lg border border-status-crit/40 bg-status-crit/10 px-4 py-3 text-sm text-status-crit">
          {error}
        </div>
      )}

      {/* Результаты */}
      {report && (
        <>
          <OverallBanner overall={report.overall} duration={report.duration_ms} />
          <DiagnosticsChain steps={report.steps} />
        </>
      )}

      {/* Подсказка при первом открытии */}
      {!report && !running && (
        <div className="text-center text-muted-foreground py-16 text-sm">
          Нажмите «Проверить» для запуска диагностики
        </div>
      )}
    </div>
  );
}
