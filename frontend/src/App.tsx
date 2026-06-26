import { useEffect, useState } from 'react';

import { api, type DashboardSettings } from './api/client';
import { Layout, type PageKey } from './components/Layout';
import { ActionsPage } from './pages/ActionsPage';
import { DockerPage } from './pages/DockerPage';
import { HomePage } from './pages/HomePage';
import { RemoteAccessPage } from './pages/RemoteAccessPage';
import { ServicesPage } from './pages/ServicesPage';
import { SettingsPage } from './pages/SettingsPage';

const pages: PageKey[] = ['remote', 'services', 'home', 'docker', 'actions', 'settings'];

function pageFromHash(): PageKey {
  const value = window.location.hash.replace('#', '') as PageKey;
  return pages.includes(value) ? value : 'remote';
}

export default function App() {
  const [settings, setSettings] = useState<DashboardSettings | null>(null);
  const [page, setPage] = useState<PageKey>(pageFromHash());
  const [loading, setLoading] = useState(true);

  async function loadSettings() {
    setSettings(await api.settings());
  }

  function navigate(next: PageKey) {
    window.location.hash = next;
    setPage(next);
  }

  useEffect(() => {
    const onHashChange = () => setPage(pageFromHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  useEffect(() => {
    async function boot() {
      try {
        await loadSettings();
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    void boot();
  }, []);

  if (loading) {
    return <div className="bootScreen">Loading</div>;
  }

  return (
    <Layout
      activePage={page}
      serverName={settings?.server_name || 'Home Server'}
      onNavigate={navigate}
    >
      {page === 'home' ? <HomePage /> : null}
      {page === 'docker' ? <DockerPage /> : null}
      {page === 'remote' ? <RemoteAccessPage settings={settings} /> : null}
      {page === 'services' ? <ServicesPage /> : null}
      {page === 'actions' ? <ActionsPage /> : null}
      {page === 'settings' ? <SettingsPage settings={settings} onSaved={setSettings} /> : null}
    </Layout>
  );
}
