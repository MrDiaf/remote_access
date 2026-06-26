import { CheckSquare, ExternalLink, Monitor, RefreshCw } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { ApiError, api, type DashboardSettings, type RemoteDesktopStatus } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';

type RemoteAccessPageProps = {
  settings: DashboardSettings | null;
};

function containerTone(state: string) {
  return state === 'running' ? 'online' : state || 'unknown';
}

export function RemoteAccessPage({ settings }: RemoteAccessPageProps) {
  const [status, setStatus] = useState<RemoteDesktopStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const guacamoleUrl = status?.guacamole_url || settings?.links.guacamole?.url || '/guacamole/';
  const rdpTarget = useMemo(
    () => (status ? `${status.rdp_host}:${status.rdp_port}` : 'host.docker.internal:3389'),
    [status]
  );

  async function loadStatus() {
    setBusy(true);
    setError(null);
    try {
      setStatus(await api.remoteStatus());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to load remote desktop status');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void loadStatus();
  }, []);

  return (
    <div className="page remotePage">
      <section className="desktopStage">
        <div className="desktopStageHeader">
          <div>
            <h1>Remote Desktop</h1>
            <p>
              {status?.protocol || 'RDP'} via Guacamole to <strong>{rdpTarget}</strong>
            </p>
          </div>
          <div className="desktopStageActions">
            <button className="button secondary" type="button" onClick={loadStatus} disabled={busy}>
              <RefreshCw size={16} aria-hidden="true" />
              Refresh
            </button>
            <a className="button primary remoteLaunch large" href={guacamoleUrl} target="_blank" rel="noreferrer">
              <ExternalLink size={18} aria-hidden="true" />
              Open Remote Desktop
            </a>
          </div>
        </div>

        {error ? <div className="notice error">{error}</div> : null}

        <div className="remoteFrameWrap">
          <iframe className="remoteFrame" src={guacamoleUrl} title="Guacamole Remote Desktop" />
        </div>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <h2>Remote Desktop Status</h2>
        </div>
        <div className="statusGrid">
          <div className="statusTile">
            <span>Guacamole</span>
            <StatusBadge status={containerTone(status?.guacamole_container || 'unknown')} />
            <small>web gateway</small>
          </div>
          <div className="statusTile">
            <span>guacd</span>
            <StatusBadge status={containerTone(status?.guacd_container || 'unknown')} />
            <small>protocol daemon</small>
          </div>
          <div className="statusTile">
            <span>Database</span>
            <StatusBadge status={containerTone(status?.database_container || 'unknown')} />
            <small>PostgreSQL</small>
          </div>
          <div className="statusTile">
            <span>RDP Target</span>
            <StatusBadge status={status?.rdp_reachable ? 'online' : 'offline'} />
            <small>{status?.rdp_detail || rdpTarget}</small>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <h2>Setup Checklist</h2>
        </div>
        <div className="checklist">
          {[
            'xrdp installed and active on the host',
            'XFCE installed for the remote desktop session',
            'Guacamole stack running with make remote-up',
            'Guacamole RDP connection configured',
            'Access is through LAN, Tailscale, WireGuard, or another VPN'
          ].map((item) => (
            <div key={item}>
              <CheckSquare size={18} aria-hidden="true" />
              <span>{item}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <h2>Connection Method</h2>
        </div>
        <div className="methodSummary">
          <Monitor size={24} aria-hidden="true" />
          <div>
            <strong>{status?.connection_hint || 'RDP to host.docker.internal:3389'}</strong>
            <span>xrdp usually opens a separate XFCE server-management session. Use VNC later for the exact physical monitor session.</span>
          </div>
        </div>
      </section>
    </div>
  );
}
