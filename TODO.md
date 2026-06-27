# Next Session TODO

These are handoff notes only. Do not implement until the user explicitly starts the next work session.

Remaining items are sorted by rough implementation difficulty.

## Completed This Session

- Added remote keyboard layout settings in the app. The user can choose the local keyboard layout and the remote Guacamole/RDP keyboard layout.
- Applied the saved remote keyboard layout to Guacamole RDP connections through the Guacamole database `server-layout` parameter. Open Guacamole sessions still need reconnecting before keyboard changes take effect.
- Added a visible remote input release setting. The app stores the preferred release shortcut before stronger capture behavior is enabled later.
- Added a `make shutdown` / `make maintenance-stop` command that gracefully stops the default stack and Guacamole remote desktop stack in a predictable order.
- Added `make refresh` to rebuild/recreate the dashboard, start remote desktop helpers, and reapply saved remote keyboard settings.
- Added a best-effort Remote Desktop Focus mode using browser fullscreen, iframe focus, and browser keyboard lock when available.
- Set touch devices to Guacamole's native relative/touchpad mouse mode by default. This makes one-finger drag move the remote pointer instead of clicking the exact touched screen position.
- Added a touch-device toggle on Remote Desktop for switching Guacamole between Touchpad and Touchscreen mouse modes. The toggle reloads the embedded Guacamole frame so the saved browser preference is picked up.

## Medium

- Test and harden the focused/fullscreen remote desktop mode. Confirm which shortcuts browsers still reserve locally and which ones Guacamole receives reliably.
- Improve input capture for the embedded remote desktop. After the user clicks the remote desktop area, keyboard commands should go to the remote Ubuntu session instead of the local PC/browser whenever the browser allows it.
- Test Guacamole native Touchpad mode on a real phone. Confirm one-finger drag moves the remote pointer, tap clicks, two-finger scroll works, and Guacamole's text input mode still brings up the phone keyboard when needed.
- If the phone preference does not stick on the server, verify the embedded Guacamole URL is same-origin (`/guacamole/`) so the dashboard can set Guacamole's `GUAC_PREFERENCES` localStorage value before the iframe loads.

## Harder

- Implement stronger/full input capture for the remote desktop, including the configured exit/release shortcut. Investigate browser support and limits for Pointer Lock, Keyboard Lock, fullscreen, focus handling, and reserved OS/browser shortcuts.
- Investigate Guacamole turning black or becoming unable to capture the screen when fullscreen is enabled inside the Ubuntu environment. Start by confirming whether the black screen is triggered by Guacamole, GNOME Remote Desktop, RDP display resizing, fullscreen mode inside Ubuntu, or the browser fullscreen/focus state.
- Investigate remote screen freezing when the user switches windows inside the Ubuntu desktop session. Start by confirming whether the freeze happens in Guacamole only, in GNOME Remote Desktop logs, or on the physical monitor too.

## Guardrails

- Keep using Guacamole/GNOME Remote Desktop for the actual remote protocol. Do not build a custom video streaming protocol.
- Keep the dashboard LAN/VPN-first.
- Verify behavior on desktop and phone before calling the work done.
