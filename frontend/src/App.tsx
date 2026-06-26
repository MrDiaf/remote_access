import { useEffect, useState } from 'react';

import { ApiError, api, type AuthUser, type DashboardSettings } from './api/client';
import { Layout, type PageKey } from './components/Layout';
import { ActionsPage } from './pages/ActionsPage';
import { DockerPage } from './pages/DockerPage';
import { HomePage } from './pages/HomePage';
import { LoginPage } from './pages/LoginPage';
import { RemoteAccessPage } from './pages/RemoteAccessPage';
import { ServicesPage } from './pages/ServicesPage';
import { SettingsPage } from './pages/SettingsPage';

const pages: PageKey[] = ['remote', 'services', 'home', 'docker', 'actions', 'settings'];

function pageFromHash(): PageKey {
  const value = window.location.hash.replace('#', '') as PageKey;
  return pages.includes(value) ? value : 'remote';
}

export default function App() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [settings, setSettings] = useState<DashboardSettings | null>(null);
  const [page, setPage] = useState<PageKey>(pageFromHash());
  const [checkingAuth, setCheckingAuth] = useState(true);

  async function loadSettings() {
    setSettings(await api.settings());
  }

  async function handleLogout() {
    await api.logout();
    setUser(null);
    setSettings(null);
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
        const currentUser = await api.me();
        setUser(currentUser);
        await loadSettings();
      } catch (err) {
        if (!(err instanceof ApiError) || err.status !== 401) {
          console.error(err);
        }
      } finally {
        setCheckingAuth(false);
      }
    }
    void boot();
  }, []);

  async function handleLogin(nextUser: AuthUser) {
    setUser(nextUser);
    await loadSettings();
  }

  if (checkingAuth) {
    return <div className="bootScreen">Loading</div>;
  }

  if (!user) {
    return <LoginPage onLogin={(nextUser) => void handleLogin(nextUser)} />;
  }

  return (
    <Layout
      activePage={page}
      serverName={settings?.server_name || 'Home Server'}
      username={user.username}
      onNavigate={navigate}
      onLogout={() => void handleLogout()}
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
