import { Save } from 'lucide-react';
import { FormEvent, useEffect, useMemo, useState } from 'react';

import { ApiError, api, type DashboardSettings } from '../api/client';

type SettingsPageProps = {
  settings: DashboardSettings | null;
  onSaved: (settings: DashboardSettings) => void;
};

export function SettingsPage({ settings, onSaved }: SettingsPageProps) {
  const [serverName, setServerName] = useState(settings?.server_name || '');
  const [linksText, setLinksText] = useState('');
  const [containersText, setContainersText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!settings) return;
    setServerName(settings.server_name);
    setLinksText(
      Object.entries(settings.links)
        .map(([key, link]) => `${key}|${link.label}|${link.url}`)
        .join('\n')
    );
    setContainersText(settings.allowed_containers.join('\n'));
  }, [settings]);

  const parsedLinks = useMemo(() => {
    const entries = linksText
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => line.split('|').map((part) => part.trim()));

    return Object.fromEntries(
      entries
        .filter(([key, label, url]) => key && label && url)
        .map(([key, label, url]) => [key, { label, url }])
    );
  }, [linksText]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSuccess(null);

    try {
      const next = await api.updateSettings({
        server_name: serverName,
        links: parsedLinks,
        allowed_containers: containersText
          .split('\n')
          .map((name) => name.trim())
          .filter(Boolean)
      });
      setSuccess('Saved');
      onSaved(next);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to save settings');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <header className="pageHeader">
        <div>
          <h1>Settings</h1>
          <p>{settings?.allowed_containers.length || 0} allowed containers</p>
        </div>
      </header>

      {error ? <div className="notice error">{error}</div> : null}
      {success ? <div className="notice success">{success}</div> : null}

      <form className="settingsForm" onSubmit={handleSubmit}>
        <section className="panel formPanel">
          <label>
            <span>Server display name</span>
            <input value={serverName} onChange={(event) => setServerName(event.target.value)} />
          </label>
        </section>

        <section className="panel formPanel">
          <label>
            <span>External links</span>
            <textarea value={linksText} onChange={(event) => setLinksText(event.target.value)} rows={6} />
          </label>
        </section>

        <section className="panel formPanel">
          <label>
            <span>Allowed containers</span>
            <textarea value={containersText} onChange={(event) => setContainersText(event.target.value)} rows={7} />
          </label>
        </section>

        <button className="button primary saveButton" type="submit" disabled={busy}>
          <Save size={16} aria-hidden="true" />
          {busy ? 'Saving' : 'Save'}
        </button>
      </form>
    </div>
  );
}

