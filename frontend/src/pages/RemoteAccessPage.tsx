import { CheckSquare, ExternalLink, Keyboard, Maximize2, Minimize2, Monitor, MousePointer2, RefreshCw } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';

import { ApiError, api, type DashboardSettings, type RemoteDesktopStatus } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';
import {
  captureReleaseOptions,
  defaultRemoteInput,
  localKeyboardLayoutOptions,
  optionLabel,
  remoteKeyboardLayoutOptions
} from '../remoteInputOptions';

type RemoteAccessPageProps = {
  settings: DashboardSettings | null;
};

function containerTone(state: string) {
  return state === 'running' ? 'online' : state || 'unknown';
}

export function RemoteAccessPage({ settings }: RemoteAccessPageProps) {
  const desktopStageRef = useRef<HTMLElement | null>(null);
  const remoteFrameRef = useRef<HTMLIFrameElement | null>(null);
  const [status, setStatus] = useState<RemoteDesktopStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [focusMode, setFocusMode] = useState(false);

  const guacamoleUrl = status?.guacamole_url || settings?.links.guacamole?.url || '/guacamole/';
  const remoteInput = settings?.remote_input || defaultRemoteInput;
  const rdpTarget = useMemo(
    () => (status ? `${status.rdp_host}:${status.rdp_port}` : 'host.docker.internal:3389'),
    [status]
  );

  async function loadStatus() {
    setBusy(true);
    setError(null);
    try {
      setStatus(await api.remoteStatus());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to load remote desktop status');
    } finally {
      setBusy(false);
    }
  }

  function focusRemoteFrame() {
    remoteFrameRef.current?.focus();
  }

  async function lockKeyboardWhenAvailable() {
    const keyboard = (navigator as Navigator & { keyboard?: { lock?: () => Promise<void> } }).keyboard;
    if (!keyboard?.lock) return;
    try {
      await keyboard.lock();
    } catch {
      // Keyboard Lock is optional and browser-dependent.
    }
  }

  function unlockKeyboardWhenAvailable() {
    const keyboard = (navigator as Navigator & { keyboard?: { unlock?: () => void } }).keyboard;
    keyboard?.unlock?.();
  }

  async function enterFocusMode() {
    const stage = desktopStageRef.current;
    if (stage?.requestFullscreen && !document.fullscreenElement) {
      try {
        await stage.requestFullscreen();
      } catch {
        // Focus is still useful when fullscreen is denied.
      }
    }
    await lockKeyboardWhenAvailable();
    focusRemoteFrame();
  }

  async function releaseFocusMode() {
    unlockKeyboardWhenAvailable();
    remoteFrameRef.current?.blur();
    if (document.fullscreenElement) {
      await document.exitFullscreen();
    }
  }

  function toggleFocusMode() {
    if (focusMode) {
      void releaseFocusMode();
    } else {
      void enterFocusMode();
    }
  }

  useEffect(() => {
    void loadStatus();
  }, []);

  useEffect(() => {
    const handleFullscreenChange = () => {
      const active = document.fullscreenElement === desktopStageRef.current;
      setFocusMode(active);
      if (active) {
        void lockKeyboardWhenAvailable();
        focusRemoteFrame();
      } else {
        unlockKeyboardWhenAvailable();
      }
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const shortcut = remoteInput.capture_release_shortcut;
      const shouldRelease =
        (shortcut === 'escape' && event.key === 'Escape') ||
        (shortcut === 'ctrl-alt' && event.ctrlKey && event.altKey) ||
        (shortcut === 'ctrl-shift' && event.ctrlKey && event.shiftKey);

      if (shouldRelease) {
        event.preventDefault();
        void releaseFocusMode();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [remoteInput.capture_release_shortcut]);

  return (
    <div className="page remotePage">
      <section className="desktopStage" ref={desktopStageRef}>
        <div className="desktopStageHeader">
          <div>
            <h1>Remote Desktop</h1>
            <p>
              {status?.protocol || 'RDP'} via Guacamole to <strong>{rdpTarget}</strong>
            </p>
          </div>
          <div className="desktopStageActions">
            <button className="button secondary" type="button" onClick={loadStatus} disabled={busy}>
              <RefreshCw size={16} aria-hidden="true" />
              Refresh
            </button>
            <button className="button secondary" type="button" onClick={toggleFocusMode}>
              {focusMode ? <Minimize2 size={16} aria-hidden="true" /> : <Maximize2 size={16} aria-hidden="true" />}
              {focusMode ? 'Exit Focus' : 'Focus'}
            </button>
            <a className="button primary remoteLaunch large" href={guacamoleUrl} target="_blank" rel="noreferrer">
              <ExternalLink size={18} aria-hidden="true" />
              Open Remote Desktop
            </a>
          </div>
        </div>

        {error ? <div className="notice error">{error}</div> : null}

        <div className="remoteFrameWrap" onMouseEnter={focusRemoteFrame}>
          <iframe
            ref={remoteFrameRef}
            className="remoteFrame"
            src={guacamoleUrl}
            title="Guacamole Remote Desktop"
            allow="fullscreen; clipboard-read; clipboard-write"
          />
        </div>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <h2>Input Preferences</h2>
        </div>
        <div className="preferenceGrid">
          <div className="preferenceTile">
            <Keyboard size={20} aria-hidden="true" />
            <span>Local keyboard</span>
            <strong>{optionLabel(localKeyboardLayoutOptions, remoteInput.local_keyboard_layout)}</strong>
          </div>
          <div className="preferenceTile">
            <Keyboard size={20} aria-hidden="true" />
            <span>Remote keyboard</span>
            <strong>{optionLabel(remoteKeyboardLayoutOptions, remoteInput.remote_keyboard_layout)}</strong>
          </div>
          <div className="preferenceTile">
            <MousePointer2 size={20} aria-hidden="true" />
            <span>Release capture</span>
            <strong>{optionLabel(captureReleaseOptions, remoteInput.capture_release_shortcut)}</strong>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <h2>Remote Desktop Status</h2>
        </div>
        <div className="statusGrid">
          <div className="statusTile">
            <span>Guacamole</span>
            <StatusBadge status={containerTone(status?.guacamole_container || 'unknown')} />
            <small>web gateway</small>
          </div>
          <div className="statusTile">
            <span>guacd</span>
            <StatusBadge status={containerTone(status?.guacd_container || 'unknown')} />
            <small>protocol daemon</small>
          </div>
          <div className="statusTile">
            <span>Database</span>
            <StatusBadge status={containerTone(status?.database_container || 'unknown')} />
            <small>PostgreSQL</small>
          </div>
          <div className="statusTile">
            <span>RDP Target</span>
            <StatusBadge status={status?.rdp_reachable ? 'online' : 'offline'} />
            <small>{status?.rdp_detail || rdpTarget}</small>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <h2>Setup Checklist</h2>
        </div>
        <div className="checklist">
          {[
            'xrdp installed and active on the host',
            'XFCE installed for the remote desktop session',
            'Guacamole stack running with make remote-up',
            'Guacamole RDP connection configured',
            'Access is through LAN, Tailscale, WireGuard, or another VPN'
          ].map((item) => (
            <div key={item}>
              <CheckSquare size={18} aria-hidden="true" />
              <span>{item}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <h2>Connection Method</h2>
        </div>
        <div className="methodSummary">
          <Monitor size={24} aria-hidden="true" />
          <div>
            <strong>{status?.connection_hint || 'RDP to host.docker.internal:3389'}</strong>
            <span>xrdp usually opens a separate XFCE server-management session. Use VNC later for the exact physical monitor session.</span>
          </div>
        </div>
      </section>
    </div>
  );
}
