# Next Session TODO

These are handoff notes only. Do not implement until the user explicitly starts the next work session.

Items are sorted by rough implementation difficulty.

## Easier

- Add remote keyboard layout settings in the app. The user should be able to choose what keyboard layout they are using locally and/or what layout the remote Ubuntu session expects, because Guacamole input currently behaves like the wrong keyboard layout.
- Add a visible setting for the remote desktop focus/exit behavior. The app should let the user choose the key or gesture that releases input capture before stronger capture behavior is enabled.
- Add a `make shutdown` or `make maintenance-stop` command that gracefully stops everything before service updates. It should stop the default stack and the Guacamole remote desktop stack in a predictable order, with clear terminal output about what was stopped.

## Medium

- Consider a focused/fullscreen remote desktop mode so Guacamole has clear focus and the browser chrome/dashboard does not steal common shortcuts.
- Improve input capture for the embedded remote desktop. After the user clicks the remote desktop area, keyboard commands should go to the remote Ubuntu session instead of the local PC/browser whenever the browser allows it.
- Start the phone-friendly remote control work with the simplest usable version:
  - Add a mobile remote-control mode for phones.
  - On phone, the remote screen should behave like a large trackpad: drag moves the pointer, tap clicks, long press/right-click behavior should be considered, and scrolling should be usable.
  - When the user taps a remote text field, provide a way to open the phone keyboard and send typed text to the remote desktop.
  - Keep the first phone experience practical and obvious; the goal is usable remote control, not a decorative mobile layout.

## Harder

- Implement stronger/full input capture for the remote desktop, including the configured exit/release shortcut. Investigate browser support and limits for Pointer Lock, Keyboard Lock, fullscreen, focus handling, and reserved OS/browser shortcuts.
- Investigate Guacamole turning black or becoming unable to capture the screen when fullscreen is enabled inside the Ubuntu environment. Start by confirming whether the black screen is triggered by Guacamole, GNOME Remote Desktop, RDP display resizing, fullscreen mode inside Ubuntu, or the browser fullscreen/focus state.
- Investigate remote screen freezing when the user switches windows inside the Ubuntu desktop session. Start by confirming whether the freeze happens in Guacamole only, in GNOME Remote Desktop logs, or on the physical monitor too.

## Guardrails

- Keep using Guacamole/GNOME Remote Desktop for the actual remote protocol. Do not build a custom video streaming protocol.
- Keep the dashboard LAN/VPN-first.
- Verify behavior on desktop and phone before calling the work done.
