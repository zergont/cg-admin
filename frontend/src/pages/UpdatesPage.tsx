import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, Check, Loader2, AlertCircle } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
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

interface ModuleUpdate {
  module: string;
  current_version: string | null;
  current_commit: string | null;
  available_commits: number;
  up_to_date: boolean;
  error: string | null;
}

interface UpdateResult {
  ok: boolean;
  job_id: string | null;
  message: string;
}

export function UpdatesPage() {
  const queryClient = useQueryClient();
  const [updatingModule, setUpdatingModule] = useState<string | null>(null);

  const { data: modules, isLoading, error } = useQuery({
    queryKey: ["updates"],
    queryFn: () => apiFetch<ModuleUpdate[]>("/updates"),
    refetchInterval: 30_000,
  });

  const updateMut = useMutation({
    mutationFn: (name: string) =>
      apiFetch<UpdateResult>(`/updates/${encodeURIComponent(name)}`, {
        method: "POST",
      }),
    onSuccess: () => {
      setUpdatingModule(null);
      queryClient.invalidateQueries({ queryKey: ["updates"] });
    },
    onError: () => {
      setUpdatingModule(null);
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-6 w-56" />
        <Skeleton className="h-48 rounded-xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-status-crit">
        Ошибка загрузки: {(error as Error).message}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">Обновления модулей</h2>

      <div className="rounded-xl border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="px-4">Модуль</TableHead>
              <TableHead className="px-4">Текущая</TableHead>
              <TableHead className="px-4">Коммит</TableHead>
              <TableHead className="px-4 text-center">Доступно</TableHead>
              <TableHead className="px-4 text-right">Действие</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {modules && modules.length > 0 ? (
              modules.map((m) => (
                <TableRow key={m.module}>
                  <TableCell className="px-4 font-medium">{m.module}</TableCell>
                  <TableCell className="px-4 font-mono text-muted-foreground">
                    {m.current_version ?? "—"}
                  </TableCell>
                  <TableCell className="px-4 font-mono text-xs text-muted-foreground">
                    {m.current_commit ?? "—"}
                  </TableCell>
                  <TableCell className="px-4 text-center">
                    {m.error ? (
                      <Badge variant="outline" className="gap-1 text-status-warn border-status-warn/30">
                        <AlertCircle className="h-3 w-3" />
                        Ошибка
                      </Badge>
                    ) : m.up_to_date ? (
                      <Badge variant="outline" className="gap-1 text-status-ok border-status-ok/30">
                        <Check className="h-3 w-3" />
                        Актуально
                      </Badge>
                    ) : (
                      <Badge variant="secondary" className="text-status-warn">
                        +{m.available_commits}
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="px-4 text-right">
                    {!m.up_to_date && !m.error && (
                      <Button
                        size="xs"
                        onClick={() => {
                          setUpdatingModule(m.module);
                          updateMut.mutate(m.module);
                        }}
                        disabled={updateMut.isPending}
                      >
                        {updateMut.isPending && updatingModule === m.module ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Download className="h-3.5 w-3.5" />
                        )}
                        Обновить
                      </Button>
                    )}
                    {m.error && (
                      <span className="text-xs text-muted-foreground" title={m.error}>
                        {m.error.length > 40 ? m.error.slice(0, 40) + "…" : m.error}
                      </span>
                    )}
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                  Модули не настроены
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {updateMut.error && (
        <div className="flex items-center gap-2 text-sm text-status-crit">
          <AlertCircle className="h-4 w-4" />
          {(updateMut.error as Error).message}
        </div>
      )}
    </div>
  );
}
