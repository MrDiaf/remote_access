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

type GuacamolePreferences = {
  emulateAbsoluteMouse?: boolean;
  inputMethod?: string;
  [key: string]: unknown;
};

type TouchMouseMode = 'touchpad' | 'touchscreen';

const GUACAMOLE_PREFERENCES_KEY = 'GUAC_PREFERENCES';
const DASHBOARD_TOUCH_MOUSE_MODE_KEY = 'SCP_GUAC_TOUCH_MOUSE_MODE';

function containerTone(state: string) {
  return state === 'running' ? 'online' : state || 'unknown';
}

function hasTouchInput() {
  if (typeof window === 'undefined') return false;
  return navigator.maxTouchPoints > 0 || window.matchMedia?.('(pointer: coarse)').matches === true;
}

function readGuacamolePreferences(): GuacamolePreferences {
  try {
    const stored = window.localStorage.getItem(GUACAMOLE_PREFERENCES_KEY);
    return stored ? (JSON.parse(stored) as GuacamolePreferences) : {};
  } catch {
    return {};
  }
}

function writeGuacamolePreferences(mode: TouchMouseMode, useTextInput: boolean) {
  const current = readGuacamolePreferences();
  const next: GuacamolePreferences = {
    ...current,
    emulateAbsoluteMouse: mode === 'touchscreen'
  };

  if (useTextInput) {
    next.inputMethod = 'text';
  }

  window.localStorage.setItem(GUACAMOLE_PREFERENCES_KEY, JSON.stringify(next));
  window.localStorage.setItem(DASHBOARD_TOUCH_MOUSE_MODE_KEY, mode);
}

function readSavedTouchMouseMode(): TouchMouseMode | null {
  try {
    const mode = window.localStorage.getItem(DASHBOARD_TOUCH_MOUSE_MODE_KEY);
    return mode === 'touchpad' || mode === 'touchscreen' ? mode : null;
  } catch {
    return null;
  }
}

function currentGuacamoleTouchMouseMode(): TouchMouseMode {
  return readGuacamolePreferences().emulateAbsoluteMouse === false ? 'touchpad' : 'touchscreen';
}

function initializeGuacamoleTouchPreferences(): TouchMouseMode {
  if (typeof window === 'undefined') return 'touchscreen';

  const savedMode = readSavedTouchMouseMode();
  const touchDevice = hasTouchInput();
  const mode = savedMode || (touchDevice ? 'touchpad' : currentGuacamoleTouchMouseMode());

  if (savedMode || touchDevice) {
    writeGuacamolePreferences(mode, touchDevice);
  }

  return mode;
}

export function RemoteAccessPage({ settings }: RemoteAccessPageProps) {
  const desktopStageRef = useRef<HTMLElement | null>(null);
  const remoteFrameRef = useRef<HTMLIFrameElement | null>(null);
  const preferenceReloadTimerRef = useRef<number | null>(null);
  const [status, setStatus] = useState<RemoteDesktopStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [keyboardNotice, setKeyboardNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [focusMode, setFocusMode] = useState(false);
  const [touchMouseMode, setTouchMouseMode] = useState<TouchMouseMode>(initializeGuacamoleTouchPreferences);
  const [guacamoleFrameKey, setGuacamoleFrameKey] = useState(0);
  const [guacamoleFrameBlank, setGuacamoleFrameBlank] = useState(false);

  const guacamoleUrl = status?.guacamole_url || settings?.links.guacamole?.url || '/guacamole/';
  const guacamoleFrameSrc = guacamoleFrameBlank ? 'about:blank' : guacamoleUrl;
  const touchInput = hasTouchInput();
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

  function getGuacamoleFrameDocument() {
    try {
      return remoteFrameRef.current?.contentDocument || remoteFrameRef.current?.contentWindow?.document || null;
    } catch {
      return null;
    }
  }

  function focusGuacamoleTextInput() {
    const frameDocument = getGuacamoleFrameDocument();
    const target = frameDocument?.querySelector<HTMLTextAreaElement>('.text-input textarea.target, textarea.target');
    if (!target) return false;

    target.focus({ preventScroll: false });
    target.click();
    return true;
  }

  function reloadGuacamoleFrameWithPreferences(mode: TouchMouseMode, useTextInput: boolean) {
    if (preferenceReloadTimerRef.current) {
      window.clearTimeout(preferenceReloadTimerRef.current);
    }

    setGuacamoleFrameBlank(true);
    preferenceReloadTimerRef.current = window.setTimeout(() => {
      writeGuacamolePreferences(mode, useTextInput);
      setGuacamoleFrameKey((current) => current + 1);
      setGuacamoleFrameBlank(false);
      preferenceReloadTimerRef.current = null;
    }, 120);
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

  function chooseTouchMouseMode(mode: TouchMouseMode) {
    setKeyboardNotice(null);
    setTouchMouseMode(mode);
    reloadGuacamoleFrameWithPreferences(mode, touchInput);
  }

  function openPhoneKeyboard() {
    setKeyboardNotice(null);
    writeGuacamolePreferences(touchMouseMode, true);

    if (focusGuacamoleTextInput()) return;

    reloadGuacamoleFrameWithPreferences(touchMouseMode, true);
    setKeyboardNotice('Keyboard input is being enabled. Tap Keyboard again after the remote desktop reloads.');
  }

  useEffect(() => {
    void loadStatus();
  }, []);

  useEffect(() => {
    return () => {
      if (preferenceReloadTimerRef.current) {
        window.clearTimeout(preferenceReloadTimerRef.current);
      }
    };
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
            {touchInput ? (
              <div className="remoteTouchActions" aria-label="Phone remote controls">
                <button className="button secondary" type="button" onClick={openPhoneKeyboard}>
                  <Keyboard size={16} aria-hidden="true" />
                  Keyboard
                </button>
                <div className="segmentedControl" role="group" aria-label="Phone mouse mode">
                  <button
                    className={touchMouseMode === 'touchpad' ? 'segmentedButton active' : 'segmentedButton'}
                    type="button"
                    aria-pressed={touchMouseMode === 'touchpad'}
                    onClick={() => chooseTouchMouseMode('touchpad')}
                  >
                    Touchpad
                  </button>
                  <button
                    className={touchMouseMode === 'touchscreen' ? 'segmentedButton active' : 'segmentedButton'}
                    type="button"
                    aria-pressed={touchMouseMode === 'touchscreen'}
                    onClick={() => chooseTouchMouseMode('touchscreen')}
                  >
                    Touchscreen
                  </button>
                </div>
              </div>
            ) : null}
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
        {keyboardNotice ? <div className="notice compact">{keyboardNotice}</div> : null}

        <div className="remoteFrameWrap" onMouseEnter={focusRemoteFrame}>
          <iframe
            key={guacamoleFrameKey}
            ref={remoteFrameRef}
            className="remoteFrame"
            src={guacamoleFrameSrc}
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
          {touchInput ? (
            <div className="preferenceTile">
              <MousePointer2 size={20} aria-hidden="true" />
              <span>Phone mouse</span>
              <strong>{touchMouseMode === 'touchpad' ? 'Touchpad' : 'Touchscreen'}</strong>
            </div>
          ) : null}
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
