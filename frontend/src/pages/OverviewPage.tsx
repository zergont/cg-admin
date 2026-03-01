import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { formatUptime, formatBytes } from "@/lib/utils";
import { OsHealthBar } from "@/components/OsHealthBar";
import { ServiceCard } from "@/components/ServiceCard";

interface OsHealth {
  cpu_percent: number;
  ram_percent: number;
  ram_used_gb: number;
  ram_total_gb: number;
  disk_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  uptime_seconds: number;
}

interface ServiceInfo {
  name: string;
  unit: string;
  status: string;
  sub_state: string;
  version: string | null;
  url: string | null;
  indicator: "ok" | "warn" | "crit";
}

interface OverviewData {
  os: OsHealth;
  services: ServiceInfo[];
}

export function OverviewPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["overview"],
    queryFn: () => apiFetch<OverviewData>("/overview"),
  });

  if (isLoading) {
    return (
      <div className="text-muted-foreground animate-pulse">Загрузка…</div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-[var(--status-crit)]">
        Ошибка загрузки: {(error as Error)?.message}
      </div>
    );
  }

  const { os, services } = data;

  return (
    <div className="space-y-8">
      {/* OS Health */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Состояние сервера</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-lg border border-border bg-card p-4">
            <OsHealthBar label="CPU" value={os.cpu_percent} />
          </div>
          <div className="rounded-lg border border-border bg-card p-4">
            <OsHealthBar
              label="RAM"
              value={os.ram_percent}
              detail={`${formatBytes(os.ram_used_gb)} / ${formatBytes(os.ram_total_gb)}`}
            />
          </div>
          <div className="rounded-lg border border-border bg-card p-4">
            <OsHealthBar
              label="Диск"
              value={os.disk_percent}
              detail={`${formatBytes(os.disk_used_gb)} / ${formatBytes(os.disk_total_gb)}`}
            />
          </div>
          <div className="rounded-lg border border-border bg-card p-4 flex flex-col justify-center">
            <span className="text-sm text-muted-foreground">Uptime</span>
            <span className="text-xl font-semibold">
              {formatUptime(os.uptime_seconds)}
            </span>
          </div>
        </div>
      </section>

      {/* Services */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Службы</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {services.map((svc) => (
            <ServiceCard
              key={`${svc.name}-${svc.unit}`}
              name={svc.name}
              unit={svc.unit}
              status={svc.status}
              subState={svc.sub_state}
              indicator={svc.indicator}
              version={svc.version}
              url={svc.url}
            />
          ))}
        </div>
      </section>
    </div>
  );
}
