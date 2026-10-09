export type LinkConfig = {
  label: string;
  url: string;
};

export type RemoteInputSettings = {
  local_keyboard_layout: string;
  remote_keyboard_layout: string;
  capture_release_shortcut: string;
};

export type RemoteInputApplyResult = {
  success: boolean;
  keyboard_layout: string;
  updated_connections: number;
  message: string;
};

export type DashboardSettings = {
  server_name: string;
  links: Record<string, LinkConfig>;
  allowed_containers: string[];
  remote_input: RemoteInputSettings;
};

export type DiskStats = {
  name: string;
  mount: string;
  host_path: string | null;
  total: number;
  used: number;
  free: number;
  percent: number;
};

export type GpuStats = {
  name: string;
  percent: number;
  memory: { total: number; used: number; percent: number };
};

export type SystemInfo = {
  server_name: string;
  online: boolean;
  cpu_percent: number;
  memory: { total: number; used: number; percent: number };
  disk: DiskStats;
  disks: DiskStats[];
  gpus?: GpuStats[];
  uptime_seconds: number;
  load_average: number[];
  network: {
    hostname: string;
    addresses: Array<{ interface: string; address: string }>;
    bytes_sent: number;
    bytes_recv: number;
  };
};

export type DiskUsageEntry = {
  name: string;
  path: string;
  size: number;
  is_dir: boolean;
  is_mount: boolean;
};

export type DiskUsageResult = {
  path: string;
  parent: string | null;
  size: number;
  entries: DiskUsageEntry[];
  hidden_entries: number;
  hidden_size: number;
  scanned_at: number;
  complete: boolean;
};

export type DockerContainer = {
  name: string;
  image: string;
  status: string;
  state: string;
  created: string | null;
  ports: Record<string, unknown>;
  can_manage: boolean;
};

export type ServiceStatus = {
  id: string;
  name: string;
  kind: string;
  status: 'online' | 'offline' | 'unknown';
  detail: string | null;
  optional: boolean;
};

export type RemoteDesktopStatus = {
  protocol: string;
  guacamole_url: string;
  rdp_host: string;
  rdp_port: number;
  rdp_reachable: boolean;
  rdp_detail: string | null;
  guacamole_container: string;
  guacd_container: string;
  database_container: string;
  connection_hint: string;
};

export type ActionSummary = {
  id: string;
  name: string;
  description: string | null;
  type: string;
  requires_confirmation: boolean;
  dangerous: boolean;
  enabled: boolean;
};

export type ActionRunResult = {
  id: string;
  success: boolean;
  message: string;
  exit_code: number | null;
  output: string | null;
};

export type SteamStatus = {
  configured: boolean;
  state: string;
  message: string;
};

export type NetworkTarget = {
  id: string;
  label: string;
  host: string;
  internet: boolean;
};

export type NetworkPoint = {
  t: number;
  loss: number;
  avg_ms: number | null;
  max_ms: number | null;
  sent: number;
};

export type NetworkTargetSummary = {
  id: string;
  sent: number;
  received: number;
  loss: number;
  avg_ms: number | null;
  max_ms: number | null;
};

export type NetworkEvent = {
  start: number;
  end: number;
  internet_loss: number;
  worst_internet_loss: number;
  router_loss: number | null;
};

export type NetworkHistory = {
  hours: number;
  bucket_seconds: number;
  since: number;
  now: number;
  first_sample: number | null;
  targets: NetworkTarget[];
  series: Record<string, NetworkPoint[]>;
  summary: NetworkTargetSummary[];
  events: NetworkEvent[];
};

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    },
    ...options
  });

  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string };
      message = body.detail || message;
    } catch {
      // Keep the HTTP status text.
    }
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  settings: () => request<DashboardSettings>('/api/settings'),
  updateSettings: (settings: DashboardSettings) =>
    request<DashboardSettings>('/api/settings', {
      method: 'PUT',
      body: JSON.stringify({
        server_name: settings.server_name,
        links: settings.links,
        allowed_containers: settings.allowed_containers,
        remote_input: settings.remote_input
      })
    }),
  system: () => request<SystemInfo>('/api/system'),
  diskUsage: (path: string, refresh = false) =>
    request<DiskUsageResult>(
      `/api/disk-usage?path=${encodeURIComponent(path)}${refresh ? '&refresh=true' : ''}`
    ),
  containers: () => request<DockerContainer[]>('/api/docker/containers'),
  containerAction: (name: string, action: 'start' | 'stop' | 'restart') =>
    request<DockerContainer>(`/api/docker/containers/${encodeURIComponent(name)}/${action}`, {
      method: 'POST'
    }),
  services: () => request<ServiceStatus[]>('/api/services'),
  remoteStatus: () => request<RemoteDesktopStatus>('/api/remote/status'),
  applyRemoteInput: () =>
    request<RemoteInputApplyResult>('/api/remote/input/apply', {
      method: 'POST'
    }),
  actions: () => request<ActionSummary[]>('/api/actions'),
  runAction: (id: string, confirmed: boolean) =>
    request<ActionRunResult>(`/api/actions/${encodeURIComponent(id)}/run`, {
      method: 'POST',
      body: JSON.stringify({ confirmed })
    }),
  network: (hours: number) => request<NetworkHistory>(`/api/network?hours=${hours}`),
  networkReport: (hours: number) => request<{ hours: number; text: string }>(`/api/network/report?hours=${hours}`),
  steam: () => request<SteamStatus>('/api/steam'),
  steamControl: (action: 'start' | 'bigpicture' | 'stop', confirmed = false) =>
    request<SteamStatus>(`/api/steam/${action}`, {
      method: 'POST',
      body: JSON.stringify({ confirmed })
    })
};
