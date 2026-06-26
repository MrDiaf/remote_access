import { Cpu, Database, HardDrive, Network, RefreshCw, Server, Timer } from 'lucide-react';
import { useEffect, useState } from 'react';

import { ApiError, api, type SystemInfo } from '../api/client';

function formatBytes(value: number) {
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = value;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${size.toFixed(size >= 10 || unit === 0 ? 0 : 1)} ${units[unit]}`;
}

function formatDuration(seconds: number) {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function StatCard({
  icon: Icon,
  label,
  value,
  detail
}: {
  icon: typeof Cpu;
  label: string;
  value: string;
  detail?: string;
}) {
  return (
    <section className="statCard">
      <div className="statIcon">
        <Icon size={22} aria-hidden="true" />
      </div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        {detail ? <small>{detail}</small> : null}
      </div>
    </section>
  );
}

export function HomePage() {
  const [system, setSystem] = useState<SystemInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setBusy(true);
    setError(null);
    try {
      setSystem(await api.system());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to load system status');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="page">
      <header className="pageHeader">
        <div>
          <h1>Home</h1>
          <p>{system?.network.hostname || 'Server status'}</p>
        </div>
        <button className="button secondary" type="button" onClick={load} disabled={busy}>
          <RefreshCw size={16} aria-hidden="true" />
          Refresh
        </button>
      </header>

      {error ? <div className="notice error">{error}</div> : null}

      <div className="statsGrid">
        <StatCard icon={Server} label="Status" value={system?.online ? 'Online' : 'Unknown'} />
        <StatCard icon={Cpu} label="CPU" value={system ? `${system.cpu_percent.toFixed(0)}%` : '-'} />
        <StatCard
          icon={Database}
          label="RAM"
          value={system ? `${system.memory.percent.toFixed(0)}%` : '-'}
          detail={system ? `${formatBytes(system.memory.used)} / ${formatBytes(system.memory.total)}` : undefined}
        />
        <StatCard
          icon={HardDrive}
          label="Disk"
          value={system ? `${system.disk.percent.toFixed(0)}%` : '-'}
          detail={system ? `${formatBytes(system.disk.used)} / ${formatBytes(system.disk.total)}` : undefined}
        />
        <StatCard
          icon={Timer}
          label="Uptime"
          value={system ? formatDuration(system.uptime_seconds) : '-'}
          detail={system?.load_average.length ? `Load ${system.load_average.join(' ')}` : undefined}
        />
        <StatCard
          icon={Network}
          label="Network"
          value={system ? formatBytes(system.network.bytes_recv) : '-'}
          detail={system ? `${formatBytes(system.network.bytes_sent)} sent` : undefined}
        />
      </div>

      <section className="panel">
        <div className="panelHeader">
          <h2>Network</h2>
        </div>
        <div className="addressList">
          {system?.network.addresses.map((address) => (
            <div key={`${address.interface}-${address.address}`}>
              <span>{address.interface}</span>
              <strong>{address.address}</strong>
            </div>
          ))}
          {system && system.network.addresses.length === 0 ? <p className="empty">No non-loopback IPv4 addresses found.</p> : null}
        </div>
      </section>
    </div>
  );
}

