import {
  ArrowUp,
  Cpu,
  Database,
  File,
  Folder,
  HardDrive,
  Network,
  RefreshCw,
  Server,
  Timer
} from 'lucide-react';
import { useEffect, useState } from 'react';

import { ApiError, api, type DiskStats, type DiskUsageResult, type SystemInfo } from '../api/client';

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

function formatAge(timestamp: number) {
  const seconds = Math.max(0, Math.round(Date.now() / 1000 - timestamp));
  if (seconds < 60) return 'just now';
  return `${formatDuration(seconds)} ago`;
}

function pathCrumbs(path: string) {
  const parts = path.split('/').filter(Boolean);
  return [
    { label: '/', path: '/' },
    ...parts.map((part, index) => ({ label: part, path: `/${parts.slice(0, index + 1).join('/')}` }))
  ];
}

function DiskUsagePanel({ disks }: { disks: DiskStats[] }) {
  const [result, setResult] = useState<DiskUsageResult | null>(null);
  const [scanningPath, setScanningPath] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function open(path: string, refresh = false) {
    setScanningPath(path);
    setError(null);
    try {
      setResult(await api.diskUsage(path, refresh));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to scan folder');
    } finally {
      setScanningPath(null);
    }
  }

  const drives = disks.filter((disk) => disk.host_path);
  const busy = scanningPath !== null;
  const scale = result ? Math.max(result.size, result.entries[0]?.size ?? 0, 1) : 1;

  return (
    <section className="panel">
      <div className="panelHeader usageHeader">
        <h2>Disk usage</h2>
        {result ? (
          <button className="button secondary" type="button" onClick={() => open(result.path, true)} disabled={busy}>
            <RefreshCw size={16} aria-hidden="true" />
            Rescan
          </button>
        ) : null}
      </div>

      <div className="usageDrives">
        {drives.map((disk) => (
          <button
            key={disk.mount}
            className="button secondary"
            type="button"
            onClick={() => open(disk.host_path!)}
            disabled={busy}
          >
            <HardDrive size={16} aria-hidden="true" />
            {disk.name} <span className="subtle">{disk.host_path}</span>
          </button>
        ))}
      </div>

      {!result && !busy && !error ? (
        <p className="empty">Pick a drive to see what takes up its space. The first scan of a large drive can take a few minutes.</p>
      ) : null}
      {busy ? <div className="notice compact">Scanning {scanningPath}. Large folders can take a few minutes.</div> : null}
      {error ? <div className="notice error">{error}</div> : null}

      {result ? (
        <>
          <div className="usageToolbar">
            <button
              className="iconButton"
              type="button"
              onClick={() => result.parent && open(result.parent)}
              disabled={busy || !result.parent}
              aria-label="Up one folder"
              title="Up one folder"
            >
              <ArrowUp size={16} aria-hidden="true" />
            </button>
            <nav className="usageCrumbs" aria-label="Folder path">
              {pathCrumbs(result.path).map((crumb) => (
                <button key={crumb.path} type="button" onClick={() => open(crumb.path)} disabled={busy}>
                  {crumb.label}
                </button>
              ))}
            </nav>
            <strong>{formatBytes(result.size)}</strong>
          </div>

          {!result.complete ? (
            <div className="notice compact">Some items could not be read, so totals may be slightly low.</div>
          ) : null}

          <ol className="usageList">
            {result.entries.map((entry) => {
              const content = (
                <>
                  <span className="usageName">
                    {entry.is_mount ? (
                      <HardDrive size={16} aria-hidden="true" />
                    ) : entry.is_dir ? (
                      <Folder size={16} aria-hidden="true" />
                    ) : (
                      <File size={16} aria-hidden="true" />
                    )}
                    <span>{entry.name}</span>
                    {entry.is_mount ? <small className="subtle">separate drive</small> : null}
                  </span>
                  <span className="usageBar" aria-hidden="true">
                    <span style={{ width: `${Math.min(100, (entry.size / scale) * 100)}%` }} />
                  </span>
                  <span className="usageSize">{formatBytes(entry.size)}</span>
                </>
              );
              return (
                <li key={entry.path}>
                  {entry.is_dir ? (
                    <button className="usageRow" type="button" onClick={() => open(entry.path)} disabled={busy}>
                      {content}
                    </button>
                  ) : (
                    <div className="usageRow">{content}</div>
                  )}
                </li>
              );
            })}
          </ol>
          {result.entries.length === 0 ? <p className="empty">This folder is empty.</p> : null}
          <p className="usageFooter subtle">
            {result.hidden_entries > 0
              ? `${result.hidden_entries} smaller items (${formatBytes(result.hidden_size)}) not shown. `
              : ''}
            Scanned {formatAge(result.scanned_at)}.
          </p>
        </>
      ) : null}
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

  const disks = system?.disks?.length ? system.disks : system ? [system.disk] : [];

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
        {disks.length ? (
          disks.map((disk) => (
            <StatCard
              key={disk.mount}
              icon={HardDrive}
              label={disk.name || 'Drive'}
              value={`${disk.percent.toFixed(0)}%`}
              detail={`${formatBytes(disk.used)} / ${formatBytes(disk.total)}`}
            />
          ))
        ) : (
          <StatCard icon={HardDrive} label="Main drive" value="-" />
        )}
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

      <DiskUsagePanel disks={disks} />

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
