# Next Session TODO

These are handoff notes only. Do not implement until the user explicitly starts the next work session.

## Remote Desktop Experience

- Investigate remote screen freezing when the user switches windows inside the Ubuntu desktop session. Start by confirming whether the freeze happens in Guacamole only, in GNOME Remote Desktop logs, or on the physical monitor too.
- Improve input capture for the embedded remote desktop. After the user clicks the remote desktop area, keyboard commands should go to the remote Ubuntu session instead of the local PC/browser whenever the browser allows it.
- Consider a focused/fullscreen remote desktop mode so Guacamole has clear focus and the browser chrome/dashboard does not steal common shortcuts.

## Phone-Friendly Remote Control

- Add a mobile remote-control mode for phones.
- On phone, the remote screen should behave like a large trackpad: drag moves the pointer, tap clicks, long press/right-click behavior should be considered, and scrolling should be usable.
- When the user taps a remote text field, provide a way to open the phone keyboard and send typed text to the remote desktop.
- Keep the first phone experience practical and obvious; the goal is usable remote control, not a decorative mobile layout.

## Guardrails

- Keep using Guacamole/GNOME Remote Desktop for the actual remote protocol. Do not build a custom video streaming protocol.
- Keep the dashboard LAN/VPN-first.
- Verify behavior on desktop and phone before calling the work done.
