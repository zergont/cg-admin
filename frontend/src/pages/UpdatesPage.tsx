import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, Check, Loader2, AlertCircle } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface ModuleUpdate {
  module: string;
  current_version: string | null;
  current_commit: string | null;
  available_commits: number;
  up_to_date: boolean;
}

interface UpdateResult {
  ok: boolean;
  job_id: string | null;
  message: string;
}

export function UpdatesPage() {
  const queryClient = useQueryClient();

  const { data: modules, isLoading } = useQuery({
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
      queryClient.invalidateQueries({ queryKey: ["updates"] });
    },
  });

  if (isLoading) {
    return (
      <div className="text-muted-foreground animate-pulse">Загрузка…</div>
    );
  }

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">Обновления модулей</h2>

      <div className="rounded-lg border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-secondary/50">
            <tr>
              <th className="text-left px-4 py-3 font-medium">Модуль</th>
              <th className="text-left px-4 py-3 font-medium">Текущая</th>
              <th className="text-left px-4 py-3 font-medium">Коммит</th>
              <th className="text-center px-4 py-3 font-medium">Доступно</th>
              <th className="text-right px-4 py-3 font-medium">Действие</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {modules?.map((m) => (
              <tr key={m.module} className="hover:bg-secondary/20">
                <td className="px-4 py-3 font-medium">{m.module}</td>
                <td className="px-4 py-3 font-mono text-muted-foreground">
                  {m.current_version ?? "—"}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                  {m.current_commit ?? "—"}
                </td>
                <td className="px-4 py-3 text-center">
                  {m.up_to_date ? (
                    <span className="inline-flex items-center gap-1 text-[var(--status-ok)]">
                      <Check className="h-3.5 w-3.5" />
                      Актуально
                    </span>
                  ) : (
                    <span className="text-[var(--status-warn)] font-medium">
                      +{m.available_commits}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  {!m.up_to_date && (
                    <button
                      onClick={() => updateMut.mutate(m.module)}
                      disabled={updateMut.isPending}
                      className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50"
                    >
                      {updateMut.isPending ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Download className="h-3.5 w-3.5" />
                      )}
                      Обновить
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {updateMut.error && (
        <div className="flex items-center gap-2 text-sm text-[var(--status-crit)]">
          <AlertCircle className="h-4 w-4" />
          {(updateMut.error as Error).message}
        </div>
      )}
    </div>
  );
}
