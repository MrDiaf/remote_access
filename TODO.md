# Next Session TODO

These are handoff notes only. Do not implement until the user explicitly starts the next work session.

Remaining items are sorted by rough implementation difficulty.

## End-of-Day State

- The phone touchpad/keyboard path has been manually tested by the user and is accepted as minimally working for now.
- The phone controls are still a little wonky, but this issue is dismissed for this session. Do not reopen phone polish unless the user explicitly asks.
- The next new planning topic is remote audio output. Start with Guacamole/RDP audio redirection before considering any alternate audio path.
- Development should also be containerized through a future `docker-compose.dev.yaml`. Future work should not require installing npm on the host.

## Completed This Session

- Added remote keyboard layout settings in the app. The user can choose the local keyboard layout and the remote Guacamole/RDP keyboard layout.
- Applied the saved remote keyboard layout to Guacamole RDP connections through the Guacamole database `server-layout` parameter. Open Guacamole sessions still need reconnecting before keyboard changes take effect.
- Added a visible remote input release setting. The app stores the preferred release shortcut before stronger capture behavior is enabled later.
- Added a `make shutdown` / `make maintenance-stop` command that gracefully stops the default stack and Guacamole remote desktop stack in a predictable order.
- Added `make refresh` to rebuild/recreate the dashboard, start remote desktop helpers, and reapply saved remote keyboard settings.
- Added a best-effort Remote Desktop Focus mode using browser fullscreen, iframe focus, and browser keyboard lock when available.
- Set touch devices to Guacamole's native relative/touchpad mouse mode by default. This makes one-finger drag move the remote pointer instead of clicking the exact touched screen position.
- Added a touch-device toggle on Remote Desktop for switching Guacamole between Touchpad and Touchscreen mouse modes. The toggle reloads the embedded Guacamole frame so the saved browser preference is picked up.
- Moved phone controls into an overlay on the remote frame so Keyboard and Touchpad/Touchscreen remain reachable while focused.
- Added a dashboard-owned phone keyboard input that opens the mobile keyboard reliably and forwards typed text/backspace into Guacamole's native text input textarea.
- Changed Touchpad/Touchscreen switching to use an explicit two-choice control and reload through a temporary blank iframe so Guacamole's old unload handler does not overwrite the newly selected preference.
- User accepted the phone touchpad/keyboard behavior as minimally working, with polish deferred.

## Medium

- Test and harden the focused/fullscreen remote desktop mode. Confirm which shortcuts browsers still reserve locally and which ones Guacamole receives reliably.
- Improve input capture for the embedded remote desktop. After the user clicks the remote desktop area, keyboard commands should go to the remote Ubuntu session instead of the local PC/browser whenever the browser allows it.
- Add `docker-compose.dev.yaml` for local development without host npm:
  - Include a Node/Vite frontend dev service with `./frontend` bind-mounted.
  - Use a named volume for container-owned `node_modules` so host dependency installs are not needed.
  - Expose Vite's dev server on a predictable LAN/VPN-safe port.
  - Add Make wrappers such as `make dev`, `make dev-down`, and/or `make frontend-dev-shell`.
- Plan and investigate remote audio output. Preferred path is Guacamole RDP audio redirection, not a custom audio streaming protocol:
  - Confirm Guacamole's RDP connection does not have `disable-audio` enabled.
  - Confirm the browser allows audio playback for the dashboard/Guacamole page and is not muted by autoplay or site settings.
  - Confirm `guacd` logs do not show missing FreeRDP audio/device-redirection channel support.
  - Confirm GNOME Remote Desktop on the host actually exposes speaker audio over RDP for the physical-screen session.
  - If the built-in RDP audio path works, add a small dashboard status/check note and optional setting for remote audio output.

## Harder

- Implement stronger/full input capture for the remote desktop, including the configured exit/release shortcut. Investigate browser support and limits for Pointer Lock, Keyboard Lock, fullscreen, focus handling, and reserved OS/browser shortcuts.
- If GNOME physical-screen RDP cannot provide audio output through Guacamole, evaluate alternatives without changing the core architecture: xrdp/PipeWire or PulseAudio audio for a separate management session, another existing remote desktop stack with browser audio support, or an explicitly approved audio bridge as a last-resort experiment.
- Investigate Guacamole turning black or becoming unable to capture the screen when fullscreen is enabled inside the Ubuntu environment. Start by confirming whether the black screen is triggered by Guacamole, GNOME Remote Desktop, RDP display resizing, fullscreen mode inside Ubuntu, or the browser fullscreen/focus state.
- Investigate remote screen freezing when the user switches windows inside the Ubuntu desktop session. Start by confirming whether the freeze happens in Guacamole only, in GNOME Remote Desktop logs, or on the physical monitor too.

## Deferred Polish

- Phone remote control is usable enough for now but still imperfect. If the user reopens it later, check the overlay Keyboard workflow, visible viewport resizing while the phone keyboard is open, and whether the embedded Guacamole URL is same-origin (`/guacamole/`) so dashboard-managed `GUAC_PREFERENCES` still applies.

## Guardrails

- Keep using Guacamole/GNOME Remote Desktop for the actual remote protocol. Do not build a custom video streaming protocol.
- Keep the dashboard LAN/VPN-first.
- Verify behavior on desktop and phone before calling the work done.
