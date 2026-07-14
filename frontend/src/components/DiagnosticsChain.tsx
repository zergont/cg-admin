/**
 * Copyright (c) 2026 ООО «НГ-ЭНЕРГОСЕРВИС». Все права защищены.
 * Программный комплекс «Честная Генерация»
 * Модуль администрирования комплекса
 * Автор: Саввиди Александр Анатольевич | ИНН 4725009270
 *
 * Данное программное обеспечение является конфиденциальным.
 * Несанкционированное копирование, распространение или использование
 * без письменного разрешения правообладателя запрещено.
 */

import { ChevronRight } from "lucide-react";
import { DiagnosticsStepCard, DiagnosticsStep } from "./DiagnosticsStepCard";

// Фиксированный порядок шагов по id
const STEP_ORDER = [
  "wireguard",
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
