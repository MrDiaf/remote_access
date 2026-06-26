import { Play, RefreshCw, RotateCw, Square } from 'lucide-react';
import { useEffect, useState } from 'react';

import { ApiError, api, type DockerContainer } from '../api/client';
import { ConfirmModal } from '../components/ConfirmModal';
import { StatusBadge } from '../components/StatusBadge';

type PendingAction = {
  container: DockerContainer;
  action: 'start' | 'stop' | 'restart';
};

export function DockerPage() {
  const [containers, setContainers] = useState<DockerContainer[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<PendingAction | null>(null);

  async function load() {
    setBusy(true);
    setError(null);
    try {
      setContainers(await api.containers());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to load containers');
    } finally {
      setBusy(false);
    }
  }

  async function runAction(action: PendingAction) {
    setBusy(true);
    setError(null);
    try {
      await api.containerAction(action.container.name, action.action);
      setPending(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Docker action failed');
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
          <h1>Docker</h1>
          <p>{containers.length} containers</p>
        </div>
        <button className="button secondary" type="button" onClick={load} disabled={busy}>
          <RefreshCw size={16} aria-hidden="true" />
          Refresh
        </button>
      </header>

      {error ? <div className="notice error">{error}</div> : null}

      <section className="panel tablePanel">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Image</th>
              <th>Status</th>
              <th>Allowed</th>
              <th className="actionsColumn">Actions</th>
            </tr>
          </thead>
          <tbody>
            {containers.map((container) => (
              <tr key={container.name}>
                <td>
                  <strong>{container.name}</strong>
                </td>
                <td>{container.image}</td>
                <td>
                  <StatusBadge status={container.state || container.status} />
                </td>
                <td>{container.can_manage ? 'Yes' : 'No'}</td>
                <td>
                  <div className="rowActions">
                    <button
                      className="iconButton"
                      type="button"
                      title="Start"
                      aria-label={`Start ${container.name}`}
                      disabled={!container.can_manage || busy}
                      onClick={() => setPending({ container, action: 'start' })}
                    >
                      <Play size={17} aria-hidden="true" />
                    </button>
                    <button
                      className="iconButton"
                      type="button"
                      title="Stop"
                      aria-label={`Stop ${container.name}`}
                      disabled={!container.can_manage || busy}
                      onClick={() => setPending({ container, action: 'stop' })}
                    >
                      <Square size={17} aria-hidden="true" />
                    </button>
                    <button
                      className="iconButton"
                      type="button"
                      title="Restart"
                      aria-label={`Restart ${container.name}`}
                      disabled={!container.can_manage || busy}
                      onClick={() => setPending({ container, action: 'restart' })}
                    >
                      <RotateCw size={17} aria-hidden="true" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {containers.length === 0 ? <p className="empty">No containers returned by Docker.</p> : null}
      </section>

      {pending ? (
        <ConfirmModal
          title={`${pending.action} ${pending.container.name}`}
          message={`Confirm ${pending.action} for this allowlisted container.`}
          confirmLabel={pending.action}
          busy={busy}
          onCancel={() => setPending(null)}
          onConfirm={() => void runAction(pending)}
        />
      ) : null}
    </div>
  );
}

