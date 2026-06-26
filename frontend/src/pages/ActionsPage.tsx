import { Play, RefreshCw } from 'lucide-react';
import { useEffect, useState } from 'react';

import { ApiError, api, type ActionRunResult, type ActionSummary } from '../api/client';
import { ConfirmModal } from '../components/ConfirmModal';

export function ActionsPage() {
  const [actions, setActions] = useState<ActionSummary[]>([]);
  const [pending, setPending] = useState<ActionSummary | null>(null);
  const [result, setResult] = useState<ActionRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setBusy(true);
    setError(null);
    try {
      setActions(await api.actions());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to load actions');
    } finally {
      setBusy(false);
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

