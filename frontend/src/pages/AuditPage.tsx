import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";

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
      <div className="space-y-6">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-48 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <h2 className="text-lg font-semibold">Журнал аудита</h2>
        <select
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          className="text-xs bg-secondary text-foreground rounded-md px-2 py-1 border border-border"
        >
          <option value="">Все действия</option>
          <option value="restart">restart</option>
          <option value="update_start">update_start</option>
          <option value="update_start_fail">update_start_fail</option>
          <option value="update_done">update_done</option>
          <option value="update_fail">update_fail</option>
        </select>
      </div>

      <div className="rounded-xl border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="px-4">Время</TableHead>
              <TableHead className="px-4">Кто</TableHead>
              <TableHead className="px-4">Действие</TableHead>
              <TableHead className="px-4">Цель</TableHead>
              <TableHead className="px-4">Детали</TableHead>
              <TableHead className="px-4">IP</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {entries?.map((e) => (
              <TableRow key={e.id}>
                <TableCell className="px-4 text-xs text-muted-foreground">
                  {new Date(e.timestamp).toLocaleString("ru-RU")}
                </TableCell>
                <TableCell className="px-4 text-xs text-muted-foreground">
                  {e.who}
                </TableCell>
                <TableCell className="px-4">
                  <Badge variant="secondary">{e.action}</Badge>
                </TableCell>
                <TableCell className="px-4 font-medium">{e.target}</TableCell>
                <TableCell className="px-4 text-xs text-muted-foreground max-w-xl whitespace-pre-wrap break-words">
                  {e.details ?? "—"}
                </TableCell>
                <TableCell className="px-4 text-xs text-muted-foreground font-mono">
                  {e.ip ?? "—"}
                </TableCell>
              </TableRow>
            ))}
            {entries?.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="px-4 py-8 text-center text-muted-foreground"
                >
                  Нет записей
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
