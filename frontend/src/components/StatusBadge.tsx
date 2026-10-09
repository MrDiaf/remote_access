type StatusBadgeProps = {
  status: string;
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const normalized = status.toLowerCase();
  let tone = 'neutral';
  if (['online', 'running', 'healthy'].includes(normalized)) tone = 'good';
  if (['offline', 'exited', 'dead', 'failed', 'error', 'unreachable'].includes(normalized)) tone = 'bad';
  if (['unknown', 'created', 'paused', 'starting', 'stopping', 'needs setup'].includes(normalized)) tone = 'warn';

  return <span className={`statusBadge ${tone}`}>{status}</span>;
}

