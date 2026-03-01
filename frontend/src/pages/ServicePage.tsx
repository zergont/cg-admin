import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  RotateCcw,
  RefreshCw,
  AlertTriangle,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { LogViewer } from "@/components/LogViewer";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface ServiceDetail {
  active_state: string;
  sub_state: string;
  uptime: string;
  main_pid: number;
  restart_count: number;
  memory: string;
}

interface LogsData {
  lines: string[];
}

export function ServicePage() {
  const { unit } = useParams<{ unit: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showConfirm, setShowConfirm] = useState(false);
  const [logLines, setLogLines] = useState(100);
  const [logLevel, setLogLevel] = useState<string>("");

  const { data: status, isLoading: statusLoading, error: statusError } = useQuery({
    queryKey: ["service-status", unit],
    queryFn: () => apiFetch<ServiceDetail>(`/services/${unit}/status`),
  });

  const { data: logs, isLoading: logsLoading, error: logsError } = useQuery({
    queryKey: ["service-logs", unit, logLines, logLevel],
    queryFn: () => {
      const params = new URLSearchParams({ lines: String(logLines) });
      if (logLevel) params.set("level", logLevel);
      return apiFetch<LogsData>(`/services/${unit}/logs?${params}`);
    },
  });

  const restartMut = useMutation({
    mutationFn: () =>
      apiFetch<{ ok: boolean; message: string }>(
        `/services/${unit}/restart`,
        { method: "POST" },
      ),
    onSuccess: () => {
      setShowConfirm(false);
      queryClient.invalidateQueries({ queryKey: ["service-status", unit] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
    },
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => navigate("/")}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h2 className="text-lg font-semibold">{unit}</h2>
      </div>

      {/* Status */}
      {statusLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-16 rounded-xl" />
          ))}
        </div>
      ) : statusError ? (
        <div className="text-status-crit">
          Ошибка загрузки статуса: {(statusError as Error).message}
        </div>
      ) : status ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          {[
            { label: "Статус", value: `${status.active_state} (${status.sub_state})` },
            { label: "PID", value: String(status.main_pid) },
            { label: "Рестарты", value: String(status.restart_count) },
            { label: "Память", value: status.memory },
            { label: "Uptime", value: status.uptime },
          ].map((item) => (
            <Card key={item.label} className="py-3 gap-1">
              <CardContent className="px-4">
                <div className="text-xs text-muted-foreground">{item.label}</div>
                <div className="text-sm font-medium mt-1 truncate">
                  {item.value}
                </div>
              </CardContent>
            </Card>
          ))}

          {/* Restart button */}
          <Card className="py-3 flex items-center justify-center">
            <CardContent className="px-4">
              {showConfirm ? (
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-status-warn" />
                  <Button
                    variant="ghost"
                    size="xs"
                    onClick={() => restartMut.mutate()}
                    disabled={restartMut.isPending}
                    className="text-status-crit"
                  >
                    {restartMut.isPending ? "…" : "Да"}
                  </Button>
                  <Button
                    variant="ghost"
                    size="xs"
                    onClick={() => setShowConfirm(false)}
                  >
                    Отмена
                  </Button>
                </div>
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowConfirm(true)}
                  className="text-muted-foreground"
                >
                  <RotateCcw className="h-4 w-4" />
                  Restart
                </Button>
              )}
            </CardContent>
          </Card>
        </div>
      ) : null}

      {/* Logs */}
      <section>
        <div className="flex items-center gap-4 mb-3">
          <h3 className="text-sm font-semibold">Логи</h3>
          <select
            value={logLevel}
            onChange={(e) => setLogLevel(e.target.value)}
            className="text-xs bg-secondary text-foreground rounded-md px-2 py-1 border border-border"
          >
            <option value="">Все</option>
            <option value="error">error</option>
            <option value="warning">warning</option>
            <option value="info">info</option>
          </select>
          <select
            value={logLines}
            onChange={(e) => setLogLines(Number(e.target.value))}
            className="text-xs bg-secondary text-foreground rounded-md px-2 py-1 border border-border"
          >
            <option value={50}>50 строк</option>
            <option value={100}>100 строк</option>
            <option value={500}>500 строк</option>
            <option value={1000}>1000 строк</option>
          </select>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() =>
              queryClient.invalidateQueries({
                queryKey: ["service-logs", unit],
              })
            }
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
        {logsError ? (
          <div className="text-status-crit text-sm">
            Ошибка загрузки логов: {(logsError as Error).message}
          </div>
        ) : (
          <LogViewer lines={logs?.lines ?? []} loading={logsLoading} />
        )}
      </section>

      {/* Mutation error */}
      {restartMut.error && (
        <div className="text-sm text-status-crit">
          Ошибка: {(restartMut.error as Error).message}
        </div>
      )}
    </div>
  );
}
