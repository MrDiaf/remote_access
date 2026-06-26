export type LinkConfig = {
  label: string;
  url: string;
};

export type DashboardSettings = {
  server_name: string;
  links: Record<string, LinkConfig>;
  allowed_containers: string[];
};

export type SystemInfo = {
  server_name: string;
  online: boolean;
  cpu_percent: number;
  memory: { total: number; used: number; percent: number };
  disk: { mount: string; total: number; used: number; free: number; percent: number };
  uptime_seconds: number;
  load_average: number[];
  network: {
    hostname: string;
    addresses: Array<{ interface: string; address: string }>;
    bytes_sent: number;
    bytes_recv: number;
  };
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
        allowed_containers: settings.allowed_containers
      })
    }),
  system: () => request<SystemInfo>('/api/system'),
  containers: () => request<DockerContainer[]>('/api/docker/containers'),
  containerAction: (name: string, action: 'start' | 'stop' | 'restart') =>
    request<DockerContainer>(`/api/docker/containers/${encodeURIComponent(name)}/${action}`, {
      method: 'POST'
    }),
  services: () => request<ServiceStatus[]>('/api/services'),
  remoteStatus: () => request<RemoteDesktopStatus>('/api/remote/status'),
  actions: () => request<ActionSummary[]>('/api/actions'),
  runAction: (id: string, confirmed: boolean) =>
    request<ActionRunResult>(`/api/actions/${encodeURIComponent(id)}/run`, {
      method: 'POST',
      body: JSON.stringify({ confirmed })
    })
};
