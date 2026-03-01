import { useRef, useEffect } from "react";

interface LogViewerProps {
  lines: string[];
  loading?: boolean;
}

export function LogViewer({ lines, loading }: LogViewerProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines.length]);

  return (
    <div className="rounded-lg border border-border bg-[oklch(0.12_0_0)] p-4 font-mono text-xs leading-relaxed max-h-[500px] overflow-y-auto">
      {loading && (
        <div className="text-muted-foreground animate-pulse">
          Загрузка логов…
        </div>
      )}
      {!loading && lines.length === 0 && (
        <div className="text-muted-foreground">Логи не найдены</div>
      )}
      {lines.map((line, i) => (
        <div key={i} className="whitespace-pre-wrap break-all">
          {line}
        </div>
      ))}
      <div ref={endRef} />
    </div>
  );
}
