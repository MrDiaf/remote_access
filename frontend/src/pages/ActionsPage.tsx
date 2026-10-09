import { Gamepad2, Monitor, Play, RefreshCw, Square, Tv } from 'lucide-react';
import { useEffect, useState } from 'react';

import { ApiError, api, type ActionRunResult, type ActionSummary, type SteamStatus } from '../api/client';
import { ConfirmModal } from '../components/ConfirmModal';
import { StatusBadge } from '../components/StatusBadge';

const STEAM_ACTIVE = ['running', 'starting', 'stopping', 'needs setup'];

export function ActionsPage() {
  const [actions, setActions] = useState<ActionSummary[]>([]);
  const [pending, setPending] = useState<ActionSummary | null>(null);
  const [result, setResult] = useState<ActionRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [steam, setSteam] = useState<SteamStatus | null>(null);
  const [steamBusy, setSteamBusy] = useState(false);
  const [confirmSteamStop, setConfirmSteamStop] = useState(false);

  async function load() {
    setBusy(true);
    setError(null);
    void loadSteam();
    try {
      setActions(await api.actions());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to load actions');
    } finally {
      setBusy(false);
    }
  }

  async function loadSteam() {
    try {
      setSteam(await api.steam());
    } catch (err) {
      setSteam({ configured: true, state: 'error', message: err instanceof ApiError ? err.message : 'Unable to reach the backend' });
    }
  }

  async function controlSteam(action: 'start' | 'bigpicture' | 'stop') {
    setSteamBusy(true);
    try {
      setSteam(await api.steamControl(action, action === 'stop'));
      setConfirmSteamStop(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `Unable to ${action} Steam`);
    } finally {
      setSteamBusy(false);
    }
  }

  async function run(action: ActionSummary, confirmed: boolean) {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.runAction(action.id, confirmed));
      setPending(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Action failed');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  // Steam starts and quits on its own schedule; keep the card current.
  useEffect(() => {
    if (steamBusy) return undefined;
    const timer = window.setInterval(() => void loadSteam(), 10000);
    return () => window.clearInterval(timer);
  }, [steamBusy]);

  const steamActive = steam ? STEAM_ACTIVE.includes(steam.state) : false;

  return (
    <div className="page">
      <header className="pageHeader">
        <div>
          <h1>Actions</h1>
          <p>{actions.length} configured</p>
        </div>
        <button className="button secondary" type="button" onClick={load} disabled={busy}>
          <RefreshCw size={16} aria-hidden="true" />
          Refresh
        </button>
      </header>

      {error ? <div className="notice error">{error}</div> : null}
      {result ? (
        <div className={`notice ${result.success ? 'success' : 'error'}`}>
          <strong>{result.message}</strong>
          {result.output ? <pre>{result.output}</pre> : null}
        </div>
      ) : null}

      <div className="actionList">
        <section className="actionItem">
          <div>
            <div className="actionTitle">
              <Gamepad2 size={18} aria-hidden="true" />
              <strong>Steam</strong>
              {steam ? <StatusBadge status={steam.state} /> : null}
            </div>
            <p>{steam ? steam.message : 'Checking Steam…'}</p>
          </div>
          <div className="rowActions">
            {steamActive ? null : (
              <button
                className="button primary"
                type="button"
                disabled={steamBusy || !steam?.configured}
                onClick={() => void controlSteam('start')}
              >
                <Play size={16} aria-hidden="true" />
                Start
              </button>
            )}
            <button
              className={steamActive ? 'button primary' : 'button secondary'}
              type="button"
              disabled={steamBusy || !steam?.configured || steam?.state === 'stopping' || steam?.state === 'needs setup'}
              onClick={() => void controlSteam('bigpicture')}
            >
              <Tv size={16} aria-hidden="true" />
              Big Picture
            </button>
            {steamActive ? (
              <button
                className="button danger"
                type="button"
                disabled={steamBusy || steam?.state === 'stopping'}
                onClick={() => setConfirmSteamStop(true)}
              >
                <Square size={16} aria-hidden="true" />
                Stop
              </button>
            ) : null}
          </div>
        </section>

        <details className="panel steamGuide">
          <summary>Play on your phone, TV, or another PC (Steam Remote Play)</summary>
          <ol>
            <li>
              Start Steam above. <strong>Big Picture</strong> is the easiest view for a controller or TV. The first
              time, open the remote desktop and sign in to Steam on the server.
            </li>
            <li>
              In Steam on the server, open <strong>Settings › Remote Play</strong> and make sure{' '}
              <strong>Enable Remote Play</strong> is on.
            </li>
            <li>
              <strong>Phone, tablet, or TV:</strong> install the Steam Link app and sign in with the same Steam
              account, then pick this server. The app shows a 4-digit PIN. Type it into the box Steam shows on
              the server, using the remote desktop. If no box appears, use{' '}
              <strong>Settings › Remote Play › Pair Steam Link</strong>.
            </li>
            <li>
              <strong>Another PC:</strong> sign in to Steam with the same account. Games installed on the server
              show <strong>Stream</strong> instead of Install.
            </li>
          </ol>
          <p>
            Away from home, Steam connects through its own servers, so nothing else needs to be set up. If the
            stream shows a black screen, start the game directly instead of streaming the desktop or Big Picture.
          </p>
          <a className="button secondary" href="#remote">
            <Monitor size={16} aria-hidden="true" />
            Open remote desktop
          </a>
        </details>

        {actions.map((action) => (
          <section className="actionItem" key={action.id}>
            <div>
              <div className="actionTitle">
                <strong>{action.name}</strong>
                {action.dangerous ? <span className="dangerPill">dangerous</span> : null}
                {!action.enabled ? <span className="mutedPill">disabled</span> : null}
              </div>
              {action.description ? <p>{action.description}</p> : null}
            </div>
            <button
              className={action.dangerous ? 'button danger' : 'button primary'}
              type="button"
              disabled={!action.enabled || busy}
              onClick={() =>
                action.requires_confirmation || action.dangerous ? setPending(action) : void run(action, false)
              }
            >
              <Play size={16} aria-hidden="true" />
              Run
            </button>
          </section>
        ))}
      </div>

      {confirmSteamStop ? (
        <ConfirmModal
          title="Quit Steam"
          message="Steam will close on the server desktop. Save first if a game is running."
          confirmLabel="Quit Steam"
          busy={steamBusy}
          onCancel={() => setConfirmSteamStop(false)}
          onConfirm={() => void controlSteam('stop')}
        />
      ) : null}

      {pending ? (
        <ConfirmModal
          title={pending.name}
          message="Confirm this allowlisted server action."
          confirmLabel="Run"
          busy={busy}
          onCancel={() => setPending(null)}
          onConfirm={() => void run(pending, true)}
        />
      ) : null}
    </div>
  );
}

