import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

interface AuditEntry {
  id: number;
  timestamp: string;
  who: string;
  action: string;
  target: string;
  details: string | null;
  ip: string | null;
}

export function AuditPage() {
  const [actionFilter, setActionFilter] = useState("");

  const { data: entries, isLoading } = useQuery({
    queryKey: ["audit", actionFilter],
    queryFn: () => {
      const params = new URLSearchParams();
      if (actionFilter) params.set("action", actionFilter);
      const qs = params.toString();
      return apiFetch<AuditEntry[]>(`/audit${qs ? `?${qs}` : ""}`);
    },
  });

  if (isLoading) {
    return (
      <div className="text-muted-foreground animate-pulse">Загрузка…</div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <h2 className="text-lg font-semibold">Журнал аудита</h2>
        <select
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          className="text-xs bg-secondary text-foreground rounded px-2 py-1 border border-border"
        >
          <option value="">Все действия</option>
          <option value="restart">restart</option>
          <option value="update_start">update_start</option>
          <option value="update_start_fail">update_start_fail</option>
          <option value="update_done">update_done</option>
          <option value="update_fail">update_fail</option>
        </select>
      </div>

      <div className="rounded-lg border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-secondary/50">
            <tr>
              <th className="text-left px-4 py-3 font-medium">Время</th>
              <th className="text-left px-4 py-3 font-medium">Действие</th>
              <th className="text-left px-4 py-3 font-medium">Цель</th>
              <th className="text-left px-4 py-3 font-medium">Детали</th>
              <th className="text-left px-4 py-3 font-medium">IP</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {entries?.map((e) => (
              <tr key={e.id} className="hover:bg-secondary/20">
                <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">
                  {new Date(e.timestamp).toLocaleString("ru-RU")}
                </td>
                <td className="px-4 py-3">
                  <span className="inline-block rounded bg-secondary px-2 py-0.5 text-xs font-medium">
                    {e.action}
                  </span>
                </td>
                <td className="px-4 py-3 font-medium">{e.target}</td>
                <td className="px-4 py-3 text-xs text-muted-foreground max-w-xl whitespace-pre-wrap break-words">
                  {e.details ?? "—"}
                </td>
                <td className="px-4 py-3 text-xs text-muted-foreground font-mono">
                  {e.ip ?? "—"}
                </td>
              </tr>
            ))}
            {entries?.length === 0 && (
              <tr>
                <td
                  colSpan={5}
                  className="px-4 py-8 text-center text-muted-foreground"
                >
                  Нет записей
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
