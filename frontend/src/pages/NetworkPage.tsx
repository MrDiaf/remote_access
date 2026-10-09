import { AlertTriangle, CheckCircle2, Copy, Download, RefreshCw, XCircle } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { ApiError, api, type NetworkHistory, type NetworkTarget } from '../api/client';
import { formatTime, LineChart, type ChartSeries } from '../components/LineChart';

const RANGES = [
  { hours: 24, label: '24 hours' },
  { hours: 24 * 7, label: '7 days' },
  { hours: 24 * 30, label: '30 days' }
];

// Categorical slots 1-4 in fixed order (validated together for line charts).
const SERIES_COLORS = ['var(--series-1)', 'var(--series-2)', 'var(--series-3)', 'var(--series-4)'];

function lossTone(loss: number) {
  if (loss < 1) return { tone: 'good', label: 'Good', Icon: CheckCircle2 };
  if (loss < 5) return { tone: 'warn', label: 'Some loss', Icon: AlertTriangle };
  return { tone: 'bad', label: 'Bad', Icon: XCircle };
}

function ms(value: number | null) {
  if (value === null) return '–';
  return value >= 100 ? `${value.toFixed(0)} ms` : `${value.toFixed(1)} ms`;
}

function minutes(seconds: number) {
  const total = Math.max(1, Math.round(seconds / 60));
  return total >= 60 ? `${Math.floor(total / 60)} h ${total % 60} min` : `${total} min`;
}

function chartSeries(data: NetworkHistory, value: 'loss' | 'avg_ms'): ChartSeries[] {
  return data.targets.map((target: NetworkTarget, index) => ({
    id: target.id,
    label: target.label,
    color: SERIES_COLORS[index % SERIES_COLORS.length],
    points: (data.series[target.id] || []).map((point) => ({ t: point.t, v: point[value] }))
  }));
}

export function NetworkPage() {
  const [hours, setHours] = useState(24);
  const [data, setData] = useState<NetworkHistory | null>(null);
  const [report, setReport] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const reportRef = useRef<HTMLTextAreaElement>(null);

  async function load(range = hours) {
    setBusy(true);
    setError(null);
    try {
      const [history, text] = await Promise.all([api.network(range), api.networkReport(range)]);
      setData(history);
      setReport(text.text);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to load network history');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load(hours);
    const timer = window.setInterval(() => void load(hours), 60000);
    return () => window.clearInterval(timer);
  }, [hours]);

  async function copyReport() {
    try {
      await navigator.clipboard.writeText(report);
    } catch {
      // The clipboard API needs HTTPS; over plain LAN HTTP fall back to a selection copy.
      reportRef.current?.select();
      document.execCommand('copy');
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }

  function downloadReport() {
    const link = document.createElement('a');
    link.href = URL.createObjectURL(new Blob([report], { type: 'text/plain' }));
    link.download = `network-report-${new Date().toISOString().slice(0, 10)}.txt`;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  const internet = data?.summary.filter((item) => data.targets.find((target) => target.id === item.id)?.internet) ?? [];
  const internetSent = internet.reduce((sum, item) => sum + item.sent, 0);
  const internetLoss = internetSent
    ? (100 * internet.reduce((sum, item) => sum + item.sent - item.received, 0)) / internetSent
    : 0;
  const router = data?.summary.find((item) => item.id === 'router');
  const internetAvg = internet.find((item) => item.avg_ms !== null)?.avg_ms ?? null;
  const empty = data !== null && data.first_sample === null;

  return (
    <div className="page networkPage">
      <header className="pageHeader">
        <div>
          <h1>Network</h1>
          <p>Pings the router and the internet once a second, around the clock. No speed tests.</p>
        </div>
        <button className="button secondary" type="button" onClick={() => load()} disabled={busy}>
          <RefreshCw size={16} aria-hidden="true" />
          Refresh
        </button>
      </header>

      <div className="segmentedControl networkRange" role="group" aria-label="Time range">
        {RANGES.map((range) => (
          <button
            key={range.hours}
            className={hours === range.hours ? 'segmentedButton active' : 'segmentedButton'}
            type="button"
            aria-pressed={hours === range.hours}
            onClick={() => setHours(range.hours)}
          >
            {range.label}
          </button>
        ))}
      </div>

      {error ? <div className="notice error">{error}</div> : null}
      {empty ? (
        <div className="notice">No measurements yet. The first ones appear about 30 seconds after the backend starts.</div>
      ) : null}

      {data && !empty ? (
        <div className={busy ? 'networkBody refreshing' : 'networkBody'}>
          {data.first_sample && data.first_sample > data.since + 300 ? (
            <p className="subtle">Recording since {formatTime(data.first_sample)}.</p>
          ) : null}

          <div className="statsGrid">
            {[
              { label: 'Internet packet loss', loss: internetLoss, detail: `${data.targets.filter((target) => target.internet).map((target) => target.label).join(', ')} · avg ${ms(internetAvg)}` },
              ...(router ? [{ label: 'Router packet loss', loss: router.loss, detail: `Home network · avg ${ms(router.avg_ms)}` }] : [])
            ].map((stat) => {
              const { tone, label, Icon } = lossTone(stat.loss);
              return (
                <section className="statCard" key={stat.label}>
                  <div className={`statIcon status-${tone}`}>
                    <Icon size={22} aria-hidden="true" />
                  </div>
                  <div>
                    <span>{stat.label}</span>
                    <strong>{stat.loss.toFixed(2)}%</strong>
                    <small>
                      {label} · {stat.detail}
                    </small>
                  </div>
                </section>
              );
            })}
            <section className="statCard">
              <div className={`statIcon status-${data.events.length ? 'warn' : 'good'}`}>
                {data.events.length ? <AlertTriangle size={22} aria-hidden="true" /> : <CheckCircle2 size={22} aria-hidden="true" />}
              </div>
              <div>
                <span>Problem periods</span>
                <strong>{data.events.length}</strong>
                <small>Minutes with 10% or more loss to the internet</small>
              </div>
            </section>
          </div>

          <section className="panel">
            <div className="chartLegend" aria-label="Legend">
              {data.targets.map((target, index) => (
                <span key={target.id}>
                  <span className="chartKey" style={{ background: SERIES_COLORS[index % SERIES_COLORS.length] }} />
                  {target.label}{' '}
                  <span className="subtle">
                    {target.host === '-' ? '' : target.host}
                    {target.note ? `${target.host === '-' ? '' : ' · '}${target.note}` : ''}
                  </span>
                </span>
              ))}
            </div>
            <LineChart
              title="Packet loss"
              series={chartSeries(data, 'loss')}
              since={data.since}
              until={data.now}
              gapSeconds={data.bucket_seconds * 3}
              minMax={5}
              format={(value) => `${value % 1 ? value.toFixed(1) : value.toFixed(0)}%`}
            />
            <LineChart
              title="Latency (average)"
              series={chartSeries(data, 'avg_ms')}
              since={data.since}
              until={data.now}
              gapSeconds={data.bucket_seconds * 3}
              minMax={20}
              format={(value) => `${value % 1 ? value.toFixed(1) : value.toFixed(0)} ms`}
            />
          </section>

          <section className="panel">
            <div className="panelHeader">
              <h2>Problems</h2>
            </div>
            {data.events.length === 0 ? (
              <p className="empty">No periods with 10% or more packet loss to the internet.</p>
            ) : (
              <ul className="eventList">
                {[...data.events].reverse().map((event) => (
                  <li key={event.start}>
                    <strong>
                      {formatTime(event.start)} · {minutes(event.end - event.start)}
                    </strong>
                    <span>
                      {event.internet_loss.toFixed(0)}% loss to the internet (worst minute {event.worst_internet_loss.toFixed(0)}%)
                      {event.router_loss === null
                        ? ''
                        : event.router_loss >= 5
                          ? ` · router ${event.router_loss.toFixed(0)}% too: inside the home network`
                          : ' · router fine: outside the home network'}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="panel">
            <div className="panelHeader usageHeader">
              <h2>Report to copy</h2>
              <div className="rowActions">
                <button className="button primary" type="button" onClick={() => void copyReport()} disabled={!report}>
                  <Copy size={16} aria-hidden="true" />
                  {copied ? 'Copied' : 'Copy report'}
                </button>
                <button className="button secondary" type="button" onClick={downloadReport} disabled={!report}>
                  <Download size={16} aria-hidden="true" />
                  Download
                </button>
              </div>
            </div>
            <textarea className="networkReport" ref={reportRef} readOnly value={report} rows={14} spellCheck={false} />
          </section>
        </div>
      ) : null}
    </div>
  );
}
