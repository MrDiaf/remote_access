import { RefreshCw } from 'lucide-react';
import { useEffect, useState } from 'react';

import { ApiError, api, type ServiceStatus } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';

export function ServicesPage() {
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setBusy(true);
    setError(null);
    try {
      setServices(await api.services());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to load services');
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
          <h1>Services</h1>
          <p>{services.length} configured</p>
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
              <th>Kind</th>
              <th>Status</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            {services.map((service) => (
              <tr key={service.id}>
                <td>
                  <strong>{service.name}</strong>
                  {service.optional ? <small className="subtle">optional</small> : null}
                </td>
                <td>{service.kind}</td>
                <td>
                  <StatusBadge status={service.status} />
                </td>
                <td>{service.detail || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

