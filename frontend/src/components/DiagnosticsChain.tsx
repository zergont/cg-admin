import { ChevronRight } from "lucide-react";
import { DiagnosticsStepCard, DiagnosticsStep } from "./DiagnosticsStepCard";

// Фиксированный порядок шагов по id
const STEP_ORDER = [
  "mqtt_broker",
  "mqtt_flow",
  "decoder",
  "db_writer",
  "database",
  "ui_dashboard",
];

interface DiagnosticsChainProps {
  steps: DiagnosticsStep[];
}

export function DiagnosticsChain({ steps }: DiagnosticsChainProps) {
  // Сортируем по заданному порядку, неизвестные — в конец
  const sorted = [...steps].sort((a, b) => {
    const ia = STEP_ORDER.indexOf(a.id);
    const ib = STEP_ORDER.indexOf(b.id);
    return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
  });

  return (
    <div className="space-y-2">
      {sorted.map((step, idx) => (
        <div key={step.id}>
          <DiagnosticsStepCard step={step} />
          {idx < sorted.length - 1 && (
            <div className="flex justify-center py-1">
              <ChevronRight className="h-4 w-4 text-muted-foreground rotate-90" />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
