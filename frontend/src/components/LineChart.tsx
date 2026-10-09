import { useEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from 'react';

export type ChartSeries = {
  id: string;
  label: string;
  color: string;
  points: Array<{ t: number; v: number | null }>;
};

type LineChartProps = {
  title: string;
  series: ChartSeries[];
  since: number;
  until: number;
  // Points further apart than this are drawn with a gap (nothing measured).
  gapSeconds: number;
  minMax: number;
  format: (value: number) => string;
};

const HEIGHT = 220;
const PAD = { top: 12, bottom: 26, left: 44 };
// Line-end labels need room; on narrow screens the legend names the lines instead.
const LABEL_ROOM = 140;
const LABEL_MIN_WIDTH = 560;

function useWidth() {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(320);
  useEffect(() => {
    const node = ref.current;
    if (!node) return undefined;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(280, Math.floor(entry.contentRect.width))));
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  return { ref, width };
}

// Top of the y axis: four gridline steps of a round size (…, 2.5, 5, 10, 20, 25, 50, …).
function niceMax(value: number) {
  const quarter = value / 4;
  const exponent = 10 ** Math.floor(Math.log10(quarter));
  const step = [1, 2, 2.5, 5, 10].find((candidate) => candidate * exponent >= quarter) ?? 10;
  return 4 * step * exponent;
}

const TICK_STEPS = [3600, 7200, 10800, 14400, 21600, 43200, 86400, 172800, 604800];

function timeTicks(since: number, until: number, width: number) {
  const maxTicks = Math.max(2, Math.floor(width / 90));
  const step = TICK_STEPS.find((candidate) => (until - since) / candidate <= maxTicks) ?? 604800;
  const offset = new Date(since * 1000).getTimezoneOffset() * 60;
  const ticks: number[] = [];
  // Align to local midnight/hour boundaries.
  for (let t = Math.ceil((since - offset) / step) * step + offset; t <= until; t += step) ticks.push(t);
  return { ticks, step };
}

function tickLabel(t: number, step: number) {
  const date = new Date(t * 1000);
  if (step < 86400) return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  return date.toLocaleDateString([], { weekday: step < 604800 ? 'short' : undefined, day: 'numeric', month: 'short' });
}

export function formatTime(t: number) {
  return new Date(t * 1000).toLocaleString([], { weekday: 'short', hour: '2-digit', minute: '2-digit' });
}

export function LineChart({ title, series, since, until, gapSeconds, minMax, format }: LineChartProps) {
  const { ref, width } = useWidth();
  const [hover, setHover] = useState<number | null>(null);

  const showLabels = width >= LABEL_MIN_WIDTH;
  const padRight = showLabels ? LABEL_ROOM : 12;
  const plotWidth = width - PAD.left - padRight;
  const plotHeight = HEIGHT - PAD.top - PAD.bottom;
  const values = series.flatMap((item) => item.points.map((point) => point.v ?? 0));
  const yMax = niceMax(Math.max(minMax, ...values));
  const x = (t: number) => PAD.left + ((t - since) / Math.max(1, until - since)) * plotWidth;
  const y = (v: number) => PAD.top + plotHeight - (v / yMax) * plotHeight;

  const times = Array.from(new Set(series.flatMap((item) => item.points.map((point) => point.t)))).sort((a, b) => a - b);
  const { ticks, step } = timeTicks(since, until, plotWidth);

  function path(points: ChartSeries['points']) {
    let d = '';
    let previous: number | null = null;
    for (const point of points) {
      if (point.v === null) {
        previous = null;
        continue;
      }
      const command = previous === null || point.t - previous > gapSeconds ? 'M' : 'L';
      d += `${command}${x(point.t).toFixed(1)},${y(point.v).toFixed(1)}`;
      previous = point.t;
    }
    return d;
  }

  // Direct labels at each line's last value, nudged apart so they never overlap.
  const labels = series
    .map((item) => {
      const last = [...item.points].reverse().find((point) => point.v !== null);
      return last ? { item, value: last.v as number, top: y(last.v as number) } : null;
    })
    .filter((label): label is NonNullable<typeof label> => label !== null)
    .sort((a, b) => a.top - b.top);
  for (let index = 1; index < labels.length; index += 1) {
    labels[index].top = Math.max(labels[index].top, labels[index - 1].top + 15);
  }

  function pick(event: PointerEvent<SVGSVGElement>) {
    if (!times.length) return;
    const box = event.currentTarget.getBoundingClientRect();
    const t = since + ((event.clientX - box.left - PAD.left) / plotWidth) * (until - since);
    let best = 0;
    times.forEach((candidate, index) => {
      if (Math.abs(candidate - t) < Math.abs(times[best] - t)) best = index;
    });
    setHover(best);
  }

  function onKey(event: KeyboardEvent<SVGSVGElement>) {
    if (!times.length) return;
    if (event.key === 'ArrowLeft') setHover((index) => Math.max(0, (index ?? times.length) - 1));
    if (event.key === 'ArrowRight') setHover((index) => Math.min(times.length - 1, (index ?? -1) + 1));
    if (event.key === 'Escape') setHover(null);
  }

  const hoverT = hover !== null ? times[hover] : null;
  const readout =
    hoverT !== null
      ? series.map((item) => ({ item, point: item.points.find((point) => point.t === hoverT) }))
      : [];

  return (
    <figure className="lineChart" ref={ref}>
      <figcaption>{title}</figcaption>
      <svg
        width={width}
        height={HEIGHT}
        role="img"
        aria-label={`${title}. Use the left and right arrow keys to read values.`}
        tabIndex={0}
        onPointerMove={pick}
        onPointerLeave={() => setHover(null)}
        onKeyDown={onKey}
        onBlur={() => setHover(null)}
      >
        {[0, 0.25, 0.5, 0.75, 1].map((fraction) => (
          <g key={fraction}>
            <line className="chartGrid" x1={PAD.left} x2={PAD.left + plotWidth} y1={y(yMax * fraction)} y2={y(yMax * fraction)} />
            <text className="chartAxis" x={PAD.left - 6} y={y(yMax * fraction) + 4} textAnchor="end">
              {format(yMax * fraction)}
            </text>
          </g>
        ))}
        {ticks.map((t) => (
          <text key={t} className="chartAxis" x={x(t)} y={HEIGHT - 6} textAnchor="middle">
            {tickLabel(t, step)}
          </text>
        ))}
        {series.map((item) => (
          <path key={item.id} d={path(item.points)} fill="none" stroke={item.color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        ))}
        {(showLabels ? labels : []).map(({ item, value, top }) => (
          <g key={item.id}>
            <line x1={PAD.left + plotWidth + 8} x2={PAD.left + plotWidth + 20} y1={top} y2={top} stroke={item.color} strokeWidth={2} />
            <text className="chartLabel" x={PAD.left + plotWidth + 24} y={top + 4}>
              {item.label} {format(value)}
            </text>
          </g>
        ))}
        {hoverT !== null ? (
          <g>
            <line className="chartCrosshair" x1={x(hoverT)} x2={x(hoverT)} y1={PAD.top} y2={PAD.top + plotHeight} />
            {readout.map(({ item, point }) =>
              point && point.v !== null ? (
                <circle key={item.id} cx={x(hoverT)} cy={y(point.v)} r={4} fill={item.color} stroke="var(--surface)" strokeWidth={2} />
              ) : null
            )}
          </g>
        ) : null}
      </svg>
      {hoverT !== null ? (
        <div
          className="chartTooltip"
          style={{ left: Math.min(Math.max(x(hoverT) + 12, 0), width - 190) }}
          role="status"
        >
          <span className="chartTooltipTime">{formatTime(hoverT)}</span>
          {readout.map(({ item, point }) => (
            <div key={item.id} className="chartTooltipRow">
              <span className="chartKey" style={{ background: item.color }} />
              <strong>{point && point.v !== null ? format(point.v) : 'no data'}</strong>
              <span>{item.label}</span>
            </div>
          ))}
        </div>
      ) : null}
    </figure>
  );
}
