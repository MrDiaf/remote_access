import { Save } from 'lucide-react';
import { FormEvent, useEffect, useMemo, useState } from 'react';

import { ApiError, api, type DashboardSettings, type RemoteInputSettings } from '../api/client';
import {
  captureReleaseOptions,
  defaultRemoteInput,
  localKeyboardLayoutOptions,
  remoteKeyboardLayoutOptions
} from '../remoteInputOptions';

type SettingsPageProps = {
  settings: DashboardSettings | null;
  onSaved: (settings: DashboardSettings) => void;
};

export function SettingsPage({ settings, onSaved }: SettingsPageProps) {
  const [serverName, setServerName] = useState(settings?.server_name || '');
  const [remoteInput, setRemoteInput] = useState<RemoteInputSettings>(settings?.remote_input || defaultRemoteInput);
  const [linksText, setLinksText] = useState('');
  const [containersText, setContainersText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!settings) return;
    setServerName(settings.server_name);
    setRemoteInput(settings.remote_input || defaultRemoteInput);
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

  function updateRemoteInput<K extends keyof RemoteInputSettings>(key: K, value: RemoteInputSettings[K]) {
    setRemoteInput((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSuccess(null);

    try {
      const next = await api.updateSettings({
        server_name: serverName,
        remote_input: remoteInput,
        links: parsedLinks,
        allowed_containers: containersText
          .split('\n')
          .map((name) => name.trim())
          .filter(Boolean)
      });
      onSaved(next);
      try {
        const applied = await api.applyRemoteInput();
        setSuccess(`Saved. ${applied.message}`);
      } catch (applyErr) {
        setSuccess('Saved');
        setError(
          applyErr instanceof ApiError
            ? `Saved, but Guacamole was not updated: ${applyErr.message}`
            : 'Saved, but Guacamole was not updated'
        );
      }
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
          <div className="panelHeader compact">
            <h2>Remote input</h2>
          </div>
          <div className="settingsGrid">
            <label>
              <span>Local keyboard</span>
              <select
                value={remoteInput.local_keyboard_layout}
                onChange={(event) => updateRemoteInput('local_keyboard_layout', event.target.value)}
              >
                {localKeyboardLayoutOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Remote keyboard</span>
              <select
                value={remoteInput.remote_keyboard_layout}
                onChange={(event) => updateRemoteInput('remote_keyboard_layout', event.target.value)}
              >
                {remoteKeyboardLayoutOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Release capture</span>
              <select
                value={remoteInput.capture_release_shortcut}
                onChange={(event) => updateRemoteInput('capture_release_shortcut', event.target.value)}
              >
                {captureReleaseOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
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
