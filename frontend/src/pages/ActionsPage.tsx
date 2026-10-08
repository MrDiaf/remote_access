import { Gamepad2, Play, RefreshCw, Square } from 'lucide-react';
import { useEffect, useState } from 'react';

import { ApiError, api, type ActionRunResult, type ActionSummary, type SteamStatus } from '../api/client';
import { ConfirmModal } from '../components/ConfirmModal';
import { StatusBadge } from '../components/StatusBadge';

const STEAM_ACTIVE = ['running', 'starting', 'stopping'];

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

  async function controlSteam(action: 'start' | 'stop') {
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
          ) : (
            <button
              className="button primary"
              type="button"
              disabled={steamBusy || !steam?.configured}
              onClick={() => void controlSteam('start')}
            >
              <Play size={16} aria-hidden="true" />
              {steamBusy ? 'Starting…' : 'Start'}
            </button>
          )}
        </section>

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

