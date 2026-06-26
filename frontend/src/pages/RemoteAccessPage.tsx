import { CheckSquare, ExternalLink, Monitor, RefreshCw, Shield, TerminalSquare } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { ApiError, api, type DashboardSettings, type ServiceStatus } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';

const iconByKey = {
  guacamole: Monitor,
  portainer: Shield,
  cockpit: TerminalSquare
};

const remoteStatusIds = ['guacamole', 'guacd', 'guacamole-db', 'host-rdp', 'host-vnc'];

type RemoteAccessPageProps = {
  settings: DashboardSettings | null;
};

export function RemoteAccessPage({ settings }: RemoteAccessPageProps) {
  const links = settings ? Object.entries(settings.links) : [];
  const guacamole = settings?.links.guacamole;
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const remoteStatuses = useMemo(
    () => services.filter((service) => remoteStatusIds.includes(service.id)),
    [services]
  );

  async function loadServices() {
    setBusy(true);
    setError(null);
    try {
      setServices(await api.services());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to load remote desktop status');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void loadServices();
  }, []);

  return (
    <div className="page">
      <header className="pageHeader">
        <div>
          <h1>Remote Desktop</h1>
          <p>Guacamole gateway to the host GUI over RDP, with VNC as an optional alternative.</p>
        </div>
        <button className="button secondary" type="button" onClick={loadServices} disabled={busy}>
          <RefreshCw size={16} aria-hidden="true" />
          Refresh
        </button>
      </header>

      {error ? <div className="notice error">{error}</div> : null}

      <section className="remoteHero">
        <div>
          <Monitor size={32} aria-hidden="true" />
          <h2>Open the server GUI in your browser</h2>
          <p>
            The recommended MVP path is Apache Guacamole in Docker connecting to xrdp + XFCE on the host at
            <strong> host.docker.internal:3389</strong>.
          </p>
        </div>
        <a className="button primary remoteLaunch" href={guacamole?.url || '#'} target="_blank" rel="noreferrer">
          <ExternalLink size={16} aria-hidden="true" />
          Open Guacamole
        </a>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <h2>Remote Desktop Status</h2>
        </div>
        <div className="statusGrid">
          {remoteStatuses.map((service) => (
            <div className="statusTile" key={service.id}>
              <span>{service.name}</span>
              <StatusBadge status={service.status} />
              <small>{service.detail || service.kind}</small>
            </div>
          ))}
          {remoteStatuses.length === 0 ? <p className="empty">No remote desktop checks are configured.</p> : null}
        </div>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <h2>Setup Checklist</h2>
        </div>
        <div className="checklist">
          {[
            'Host xrdp installed and active',
            'XFCE or another lightweight desktop installed on the host',
            'Guacamole database initialized with make guacamole-init',
            'Guacamole admin password changed after first login',
            'VPN enabled before accessing from another machine',
            'Guacamole RDP connection configured to host.docker.internal:3389'
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
          <h2>Admin Links</h2>
        </div>
        <div className="linkGrid">
          {links.map(([key, link]) => {
            const Icon = iconByKey[key as keyof typeof iconByKey] || ExternalLink;
            return (
              <a className="linkCard" key={key} href={link.url} target="_blank" rel="noreferrer">
                <Icon size={24} aria-hidden="true" />
                <div>
                  <strong>{link.label}</strong>
                  <span>{link.url}</span>
                </div>
                <ExternalLink size={18} aria-hidden="true" />
              </a>
            );
          })}
        </div>
      </section>
    </div>
  );
}
