import { ExternalLink, Monitor, Shield, TerminalSquare } from 'lucide-react';

import type { DashboardSettings } from '../api/client';

const iconByKey = {
  guacamole: Monitor,
  portainer: Shield,
  cockpit: TerminalSquare
};

type RemoteAccessPageProps = {
  settings: DashboardSettings | null;
};

export function RemoteAccessPage({ settings }: RemoteAccessPageProps) {
  const links = settings ? Object.entries(settings.links) : [];

  return (
    <div className="page">
      <header className="pageHeader">
        <div>
          <h1>Remote Access</h1>
          <p>{links.length} links</p>
        </div>
      </header>

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
    </div>
  );
}

