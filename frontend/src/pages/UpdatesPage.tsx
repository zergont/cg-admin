import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, Check, Loader2, AlertCircle, X } from "lucide-react";
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
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

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

interface UpdateStatus {
  state: "idle" | "running" | "done" | "error";
  progress: string;
  log: string[];
  error: string | null;
}

export function UpdatesPage() {
  const queryClient = useQueryClient();
  const [activeUpdate, setActiveUpdate] = useState<string | null>(null);

  const { data: modules, isLoading, error } = useQuery({
    queryKey: ["updates"],
    queryFn: () => apiFetch<ModuleUpdate[]>("/updates"),
    refetchInterval: activeUpdate ? false : 30_000,
  });

  const statusQuery = useQuery({
    queryKey: ["update-status", activeUpdate],
    queryFn: () =>
      apiFetch<UpdateStatus>(`/updates/${encodeURIComponent(activeUpdate!)}/status`),
    enabled: !!activeUpdate,
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      return state === "running" || state === undefined ? 2_000 : false;
    },
  });

  const updateMut = useMutation({
    mutationFn: (name: string) =>
      apiFetch<UpdateResult>(`/updates/${encodeURIComponent(name)}`, {
        method: "POST",
      }),
    onSuccess: (_data, name) => {
      setActiveUpdate(name);
    },
    onError: () => {
      setActiveUpdate(null);
    },
  });

  function dismissStatus() {
    queryClient.invalidateQueries({ queryKey: ["updates"] });
    queryClient.removeQueries({ queryKey: ["update-status", activeUpdate] });
    setActiveUpdate(null);
  }

  const status = statusQuery.data;
  const isFinished = status?.state === "done" || status?.state === "error";

  // Автоматически обновляем список модулей когда обновление завершилось
  useEffect(() => {
    if (isFinished) {
      queryClient.invalidateQueries({ queryKey: ["updates"] });
    }
  }, [isFinished, queryClient]);

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
              modules.map((m) => {
                const isUpdating = activeUpdate === m.module;
                return (
                  <TableRow key={m.module}>
                    <TableCell className="px-4 font-medium">{m.module}</TableCell>
                    <TableCell className="px-4 font-mono text-muted-foreground">
                      {m.current_version ?? "—"}
                    </TableCell>
                    <TableCell className="px-4 font-mono text-xs text-muted-foreground">
                      {m.current_commit ?? "—"}
                    </TableCell>
                    <TableCell className="px-4 text-center">
                      {isUpdating ? (
                        <Badge variant="secondary" className="gap-1">
                          <Loader2 className="h-3 w-3 animate-spin" />
                          {status?.state === "running" ? "Обновляется" : status?.state === "done" ? "Готово" : "Ошибка"}
                        </Badge>
                      ) : m.error ? (
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
                      {!m.up_to_date && !m.error && !isUpdating && (
                        <Button
                          size="xs"
                          onClick={() => updateMut.mutate(m.module)}
                          disabled={updateMut.isPending || !!activeUpdate}
                        >
                          {updateMut.isPending ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <Download className="h-3.5 w-3.5" />
                          )}
                          Обновить
                        </Button>
                      )}
                      {m.error && !isUpdating && (
                        <span className="text-xs text-muted-foreground" title={m.error}>
                          {m.error.length > 40 ? m.error.slice(0, 40) + "…" : m.error}
                        </span>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })
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

      {/* Live update status */}
      {activeUpdate && (
        <div className={cn(
          "rounded-xl border p-4 space-y-3",
          status?.state === "done" && "border-status-ok/40 bg-status-ok/5",
          status?.state === "error" && "border-status-crit/40 bg-status-crit/5",
        )}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-medium">
              {!isFinished && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
              {status?.state === "done" && <Check className="h-4 w-4 text-status-ok" />}
              {status?.state === "error" && <AlertCircle className="h-4 w-4 text-status-crit" />}
              <span>
                {status?.state === "running" && `Обновление ${activeUpdate}…`}
                {status?.state === "done" && `${activeUpdate} обновлён успешно`}
                {status?.state === "error" && `Ошибка обновления ${activeUpdate}`}
                {!status?.state && `Запуск обновления ${activeUpdate}…`}
              </span>
            </div>
            {isFinished && (
              <Button variant="ghost" size="icon-sm" onClick={dismissStatus}>
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>

          {status?.log && status.log.length > 0 && (
            <ScrollArea className="h-48 rounded-md border bg-background">
              <div className="p-3 font-mono text-xs space-y-0.5">
                {status.log.map((line, i) => (
                  <div key={i} className="text-muted-foreground">{line}</div>
                ))}
              </div>
            </ScrollArea>
          )}

          {status?.error && (
            <p className="text-sm text-status-crit">{status.error}</p>
          )}
        </div>
      )}

      {updateMut.error && !activeUpdate && (
        <div className="flex items-center gap-2 text-sm text-status-crit">
          <AlertCircle className="h-4 w-4" />
          {(updateMut.error as Error).message}
        </div>
      )}
    </div>
  );
}
