import {
  Activity,
  Boxes,
  Home,
  Monitor,
  PlaySquare,
  ServerCog,
  Settings
} from 'lucide-react';
import type { ReactNode } from 'react';

export type PageKey = 'home' | 'docker' | 'remote' | 'services' | 'actions' | 'settings';

type LayoutProps = {
  activePage: PageKey;
  serverName: string;
  onNavigate: (page: PageKey) => void;
  children: ReactNode;
};

const navItems: Array<{ key: PageKey; label: string; icon: typeof Home }> = [
  { key: 'remote', label: 'Remote Desktop', icon: Monitor },
  { key: 'services', label: 'Services', icon: Activity },
  { key: 'home', label: 'Status', icon: Home },
  { key: 'docker', label: 'Docker', icon: Boxes },
  { key: 'actions', label: 'Actions', icon: PlaySquare },
  { key: 'settings', label: 'Settings', icon: Settings }
];

export function Layout({
  activePage,
  serverName,
  onNavigate,
  children
}: LayoutProps) {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <ServerCog size={28} aria-hidden="true" />
          <div>
            <strong>{serverName}</strong>
            <span>server-control-panel</span>
          </div>
        </div>

        <nav className="nav" aria-label="Primary">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.key}
                className={`navButton ${activePage === item.key ? 'active' : ''}`}
                type="button"
                onClick={() => onNavigate(item.key)}
              >
                <Icon size={18} aria-hidden="true" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebarFooter">
          <span>LAN/Tailscale access</span>
        </div>
      </aside>

      <main className="main">{children}</main>
    </div>
  );
}
