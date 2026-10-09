"""Keyboard-driven terminal UI with the same features as the browser dashboard."""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
import time
from typing import Any, Callable

from rich.markup import escape
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
    TabbedContent,
    TabPane,
    Tabs,
    TextArea,
)

from .api import Api, ApiError


# Same lists as frontend/src/remoteInputOptions.ts; keep them in sync.
LOCAL_KEYBOARD_LAYOUTS = [
    ("Auto", "auto"),
    ("English US", "en-us-qwerty"),
    ("English UK", "en-gb-qwerty"),
    ("Swedish", "sv-se-qwerty"),
    ("Danish", "da-dk-qwerty"),
    ("Norwegian", "no-no-qwerty"),
    ("Finnish", "fi-fi-qwerty"),
    ("German", "de-de-qwertz"),
    ("Swiss German", "de-ch-qwertz"),
    ("French", "fr-fr-azerty"),
    ("Belgian French", "fr-be-azerty"),
    ("Swiss French", "fr-ch-qwertz"),
    ("Spanish", "es-es-qwerty"),
    ("Spanish Latin American", "es-latam-qwerty"),
    ("Italian", "it-it-qwerty"),
    ("Portuguese Brazilian", "pt-br-qwerty"),
    ("Hungarian", "hu-hu-qwertz"),
    ("Japanese", "ja-jp-qwerty"),
    ("Turkish Q", "tr-tr-qwerty"),
]
REMOTE_KEYBOARD_LAYOUTS = [option for option in LOCAL_KEYBOARD_LAYOUTS if option[1] != "auto"] + [
    ("Failsafe Unicode", "failsafe")
]
CAPTURE_RELEASE_OPTIONS = [
    ("Escape", "escape"),
    ("Ctrl + Alt", "ctrl-alt"),
    ("Ctrl + Shift", "ctrl-shift"),
    ("Manual release only", "manual"),
]

# Same rule as terminal/terminal-login.sh: nothing ssh could read as an option or host.
SSH_USER_PATTERN = re.compile(r"^[A-Za-z0-9._][A-Za-z0-9._-]*$")


def option_label(options: list[tuple[str, str]], value: str) -> str:
    return next((label for label, option in options if option == value), value)


def format_bytes(value: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    unit = 0
    while size >= 1024 and unit < len(units) - 1:
        size /= 1024
        unit += 1
    return f"{size:.0f} {units[unit]}" if size >= 10 or unit == 0 else f"{size:.1f} {units[unit]}"


def format_duration(seconds: float) -> str:
    seconds = int(seconds)
    days, hours, minutes = seconds // 86400, (seconds % 86400) // 3600, (seconds % 3600) // 60
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def bar(fraction: float, width: int = 20) -> str:
    filled = round(max(0.0, min(1.0, fraction)) * width)
    return "█" * filled + "░" * (width - filled)


def status_text(status: str) -> str:
    good = {"online", "running", "healthy", "up"}
    bad = {"offline", "exited", "dead", "missing", "stopped"}
    lowered = status.lower()
    color = "green" if lowered in good else "red" if lowered in bad else "yellow"
    return f"[{color}]● {escape(status)}[/]"


def parse_links(text: str) -> dict[str, dict[str, str]]:
    """Parse `key|label|url` lines like the Settings page does."""
    links: dict[str, dict[str, str]] = {}
    for line in text.splitlines():
        parts = [part.strip() for part in line.split("|")]
        if len(parts) >= 3 and all(parts[:3]):
            links[parts[0]] = {"label": parts[1], "url": parts[2]}
    return links


class ConfirmScreen(ModalScreen[bool]):
    BINDINGS = [Binding("y", "answer(True)", "Confirm"), Binding("n,escape", "answer(False)", "Cancel")]

    def __init__(self, title: str, message: str, confirm_label: str, danger: bool = False):
        super().__init__()
        self.title_text = title
        self.message = message
        self.confirm_label = confirm_label
        self.danger = danger

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label(self.title_text, classes="dialogTitle")
            yield Static(self.message)
            with Horizontal(classes="dialogButtons"):
                yield Button("Cancel (n)", id="cancel")
                yield Button(f"{self.confirm_label} (y)", id="confirm", variant="error" if self.danger else "primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")

    def action_answer(self, value: bool) -> None:
        self.dismiss(value)


class ChoiceScreen(ModalScreen[str | None]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, title: str, choices: list[tuple[str, str]]):
        super().__init__()
        self.title_text = title
        self.choices = choices

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label(self.title_text, classes="dialogTitle")
            with Horizontal(classes="dialogButtons"):
                for label, value in self.choices:
                    yield Button(label, name=value)
                yield Button("Cancel", name="")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.name or None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class Page(VerticalScroll):
    """A tab body that loads its data on mount and on the app's refresh key."""

    @property
    def scp(self) -> "ServerControlPanelApp":
        return self.app  # type: ignore[return-value]

    async def call(self, fn: Callable[..., Any], *args: Any) -> Any:
        return await self.scp.call(fn, *args)

    def on_mount(self) -> None:
        self.reload()

    def reload(self) -> None:
        pass


class RemoteTab(Page):
    def compose(self) -> ComposeResult:
        yield Static(classes="intro", id="remote-intro")
        yield Label("Remote desktop status", classes="section")
        yield DataTable(id="remote-status", cursor_type="none")
        yield Label("Input preferences", classes="section")
        yield DataTable(id="remote-input", cursor_type="none")
        with Horizontal(classes="buttons"):
            yield Button("Apply keyboard layout to Guacamole", id="apply-input", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#remote-status", DataTable).add_columns("Component", "Status", "Detail")
        self.query_one("#remote-input", DataTable).add_columns("Setting", "Value")
        super().on_mount()

    @work(exclusive=True, group="remote")
    async def reload(self) -> None:
        status = await self.call(self.scp.api.remote_status)
        settings = await self.call(self.scp.api.settings)
        if status:
            url = self.scp.dashboard_url + status.get("guacamole_url", "/guacamole/")
            self.query_one("#remote-intro", Static).update(
                f"[b]{escape(status['protocol'])} via Guacamole to {escape(status['rdp_host'])}:{status['rdp_port']}[/b]\n"
                f"{escape(status['connection_hint'])}\n\n"
                f"The desktop picture needs a browser: [u]{escape(url)}[/u]\n"
                f"Experimental low-latency stream (Sunshine): [u]{escape(self.scp.dashboard_url)}/stream/[/u]"
            )
            table = self.query_one("#remote-status", DataTable)
            table.clear()
            table.add_row("Guacamole", status_text(status["guacamole_container"]), "web gateway")
            table.add_row("guacd", status_text(status["guacd_container"]), "protocol daemon")
            table.add_row("Database", status_text(status["database_container"]), "PostgreSQL")
            target = f"{status['rdp_host']}:{status['rdp_port']}"
            table.add_row(
                "RDP target",
                status_text("online" if status["rdp_reachable"] else "offline"),
                escape(status.get("rdp_detail") or target),
            )
        if settings:
            remote_input = settings["remote_input"]
            table = self.query_one("#remote-input", DataTable)
            table.clear()
            table.add_row("Local keyboard", option_label(LOCAL_KEYBOARD_LAYOUTS, remote_input["local_keyboard_layout"]))
            table.add_row("Remote keyboard", option_label(REMOTE_KEYBOARD_LAYOUTS, remote_input["remote_keyboard_layout"]))
            table.add_row("Release capture", option_label(CAPTURE_RELEASE_OPTIONS, remote_input["capture_release_shortcut"]))

    @on(Button.Pressed, "#apply-input")
    @work(exclusive=True, group="remote-apply")
    async def apply_input(self) -> None:
        result = await self.call(self.scp.api.apply_remote_input)
        if result:
            self.notify(result["message"], severity="information" if result["success"] else "error")


class TerminalTab(Page):
    def compose(self) -> ComposeResult:
        host, port = self.scp.ssh_host, self.scp.ssh_port
        yield Static(
            f"Opens an SSH login to [b]{host}[/b] port {port}. This screen pauses while the session runs; "
            "type [b]exit[/b] to come back.",
            classes="intro",
        )
        yield Label("Username", classes="section")
        yield Input(value=self.scp.ssh_user, placeholder="Ubuntu username", id="ssh-user")
        with Horizontal(classes="buttons"):
            yield Button("Connect", id="ssh-connect", variant="primary")

    @on(Input.Submitted, "#ssh-user")
    @on(Button.Pressed, "#ssh-connect")
    def connect(self) -> None:
        user = self.query_one("#ssh-user", Input).value.strip()
        if not SSH_USER_PATTERN.match(user):
            self.notify("Invalid username.", severity="error")
            return
        command = [
            "ssh",
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", "ServerAliveInterval=30",
            "-p", str(self.scp.ssh_port),
            "-l", user,
            self.scp.ssh_host,
        ]
        with self.app.suspend():
            code = subprocess.call(command)
        if code not in (0, 130):
            self.notify(f"SSH exited with code {code}.", severity="warning")


class ServicesTab(Page):
    def compose(self) -> ComposeResult:
        yield DataTable(id="services-table", cursor_type="row", zebra_stripes=True)

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns("Name", "Kind", "Status", "Detail")
        super().on_mount()

    @work(exclusive=True, group="services")
    async def reload(self) -> None:
        services = await self.call(self.scp.api.services)
        if services is None:
            return
        table = self.query_one(DataTable)
        table.clear()
        for service in services:
            name = escape(service["name"]) + (" [dim](optional)[/]" if service.get("optional") else "")
            table.add_row(name, escape(service["kind"]), status_text(service["status"]), escape(service.get("detail") or "-"), key=service["id"])


class DriveButton(Button):
    def __init__(self, label: str, host_path: str):
        super().__init__(label, classes="drive")
        self.host_path = host_path


class StatusTab(Page):
    BINDINGS = [
        Binding("u,backspace", "up", "Up folder"),
        Binding("s", "rescan", "Rescan"),
    ]

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.usage: dict | None = None
        self.entries: dict[str, dict] = {}

    def compose(self) -> ComposeResult:
        yield DataTable(id="stats", cursor_type="none")
        yield Label("Network", classes="section")
        yield DataTable(id="addresses", cursor_type="none")
        yield Label("Disk usage", classes="section")
        yield Static("Pick a drive to see what takes up its space. Enter opens a folder, u goes up, s rescans.", id="usage-info")
        yield Horizontal(id="drives", classes="buttons")
        yield DataTable(id="usage", cursor_type="row", zebra_stripes=True)

    def on_mount(self) -> None:
        self.query_one("#stats", DataTable).add_columns("", "Usage", "Value", "Detail")
        self.query_one("#addresses", DataTable).add_columns("Interface", "Address")
        self.query_one("#usage", DataTable).add_columns("Name", "Size", "Share", "Type")
        super().on_mount()

    @work(exclusive=True, group="system")
    async def reload(self) -> None:
        system = await self.call(self.scp.api.system)
        if not system:
            return
        table = self.query_one("#stats", DataTable)
        table.clear()
        table.add_row("Status", "", "Online" if system["online"] else "Unknown", system["network"]["hostname"])
        table.add_row("CPU", bar(system["cpu_percent"] / 100), f"{system['cpu_percent']:.0f}%", "")
        memory = system["memory"]
        table.add_row(
            "RAM", bar(memory["percent"] / 100), f"{memory['percent']:.0f}%",
            f"{format_bytes(memory['used'])} / {format_bytes(memory['total'])}",
        )
        gpus = system.get("gpus") or []
        for index, gpu in enumerate(gpus):
            label = f"GPU {index + 1}" if len(gpus) > 1 else "GPU"
            table.add_row(
                label, bar(gpu["percent"] / 100), f"{gpu['percent']:.0f}%",
                f"{gpu['name']}, VRAM {format_bytes(gpu['memory']['used'])} / {format_bytes(gpu['memory']['total'])}",
            )
        disks = system.get("disks") or [system["disk"]]
        for disk in disks:
            table.add_row(
                disk.get("name") or "Drive", bar(disk["percent"] / 100), f"{disk['percent']:.0f}%",
                f"{format_bytes(disk['used'])} / {format_bytes(disk['total'])}",
            )
        load = system.get("load_average") or []
        table.add_row("Uptime", "", format_duration(system["uptime_seconds"]), f"Load {' '.join(map(str, load))}" if load else "")
        network = system["network"]
        table.add_row("Network", "", format_bytes(network["bytes_recv"]), f"{format_bytes(network['bytes_sent'])} sent")

        addresses = self.query_one("#addresses", DataTable)
        addresses.clear()
        for address in network["addresses"]:
            addresses.add_row(address["interface"], address["address"])

        drives = self.query_one("#drives", Horizontal)
        await drives.remove_children()
        await drives.mount_all(
            DriveButton(f"{disk.get('name') or 'Drive'} {disk['host_path']}", disk["host_path"])
            for disk in disks
            if disk.get("host_path")
        )

    @on(Button.Pressed, ".drive")
    def open_drive(self, event: Button.Pressed) -> None:
        assert isinstance(event.button, DriveButton)
        self.scan(event.button.host_path)

    @on(DataTable.RowSelected, "#usage")
    def open_entry(self, event: DataTable.RowSelected) -> None:
        entry = self.entries.get(str(event.row_key.value))
        if entry and entry["is_dir"]:
            self.scan(entry["path"])

    def action_up(self) -> None:
        if self.usage and self.usage.get("parent"):
            self.scan(self.usage["parent"])

    def action_rescan(self) -> None:
        if self.usage:
            self.scan(self.usage["path"], refresh=True)

    @work(exclusive=True, group="disk-usage")
    async def scan(self, path: str, refresh: bool = False) -> None:
        table = self.query_one("#usage", DataTable)
        info = self.query_one("#usage-info", Static)
        info.update(f"Scanning {path}. Large folders can take a few minutes.")
        table.loading = True
        try:
            result = await self.call(self.scp.api.disk_usage, path, refresh)
        finally:
            table.loading = False
        if not result:
            info.update(f"Could not scan {path}.")
            return
        self.usage = result
        self.entries = {entry["path"]: entry for entry in result["entries"]}
        table.clear()
        scale = max(result["size"], result["entries"][0]["size"] if result["entries"] else 0, 1)
        for entry in result["entries"]:
            kind = "separate drive" if entry["is_mount"] else "folder" if entry["is_dir"] else "file"
            name = escape(entry["name"]) + ("/" if entry["is_dir"] else "")
            table.add_row(name, format_bytes(entry["size"]), bar(entry["size"] / scale), kind, key=entry["path"])
        lines = [f"[b]{escape(result['path'])}[/b]  {format_bytes(result['size'])}  scanned {format_duration(time.time() - result['scanned_at'])} ago"]
        if not result["complete"]:
            lines.append("[yellow]Some items could not be read, so totals may be slightly low.[/]")
        if result["hidden_entries"]:
            lines.append(f"{result['hidden_entries']} smaller items ({format_bytes(result['hidden_size'])}) not shown.")
        if not result["entries"]:
            lines.append("This folder is empty.")
        info.update("\n".join(lines))
        table.focus()


class DockerTab(Page):
    def compose(self) -> ComposeResult:
        yield Static("Enter on a container to start, stop, or restart it. Only allowlisted containers can be changed.", classes="intro")
        yield DataTable(id="containers-table", cursor_type="row", zebra_stripes=True)

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns("Name", "Image", "Status", "Allowed")
        self.containers: dict[str, dict] = {}
        super().on_mount()

    @work(exclusive=True, group="docker")
    async def reload(self) -> None:
        containers = await self.call(self.scp.api.containers)
        if containers is None:
            return
        self.containers = {container["name"]: container for container in containers}
        table = self.query_one(DataTable)
        table.clear()
        for container in containers:
            table.add_row(
                escape(container["name"]), escape(container["image"]),
                status_text(container.get("state") or container["status"]),
                "Yes" if container["can_manage"] else "No",
                key=container["name"],
            )
        if not containers:
            self.notify("No containers returned by Docker.")

    @on(DataTable.RowSelected, "#containers-table")
    def choose(self, event: DataTable.RowSelected) -> None:
        container = self.containers.get(str(event.row_key.value))
        if not container:
            return
        if not container["can_manage"]:
            self.notify(f"{container['name']} is not in the allowed containers list.", severity="warning")
            return
        name = container["name"]

        def chosen(action: str | None) -> None:
            if not action:
                return
            self.app.push_screen(
                ConfirmScreen(f"{action} {name}", f"Confirm {action} for this allowlisted container.", action),
                lambda confirmed: self.run_container_action(name, action) if confirmed else None,
            )

        self.app.push_screen(
            ChoiceScreen(name, [("Start", "start"), ("Stop", "stop"), ("Restart", "restart")]),
            chosen,
        )

    @work(group="docker-action")
    async def run_container_action(self, name: str, action: str) -> None:
        if await self.call(self.scp.api.container_action, name, action):
            self.notify(f"{action} {name}: done")
            self.reload()


STEAM_ACTIVE = {"running", "starting", "stopping", "needs setup"}
REMOTE_PLAY_GUIDE = (
    "Remote Play: start Steam (b = Big Picture, best for a controller or TV) and sign in once via the remote desktop. "
    "On a phone or TV install Steam Link, sign in with the same account, pick this server, and type its PIN into Steam "
    "on the server (Settings > Remote Play > Pair Steam Link). On another PC, sign in to Steam: server games show Stream."
)


class ActionsTab(Page):
    BINDINGS = [Binding("s", "toggle_steam", "Start/quit Steam"), Binding("b", "steam_big_picture", "Steam Big Picture")]

    def compose(self) -> ComposeResult:
        yield Static(id="steam-status")
        yield Static(REMOTE_PLAY_GUIDE, classes="intro")
        yield Static("Enter runs the selected action. s starts or quits Steam, b opens Big Picture.", classes="intro")
        yield DataTable(id="actions-table", cursor_type="row", zebra_stripes=True)
        yield Static(id="action-result")

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns("Name", "Flags", "Description")
        self.actions: dict[str, dict] = {}
        self.steam: dict | None = None
        super().on_mount()

    def show_steam(self, steam: dict) -> None:
        self.steam = steam
        self.query_one("#steam-status", Static).update(f"[b]Steam[/]  {status_text(steam['state'])}  {escape(steam['message'])}")

    @work(exclusive=True, group="steam")
    async def load_steam(self) -> None:
        steam = await self.call(self.scp.api.steam)
        if steam:
            self.show_steam(steam)

    def action_toggle_steam(self) -> None:
        steam = self.steam
        if not steam or not steam["configured"]:
            self.notify(steam["message"] if steam else "Steam status is still loading.", severity="warning")
            return
        if steam["state"] in STEAM_ACTIVE:
            self.app.push_screen(
                ConfirmScreen("Quit Steam", "Steam will close on the server desktop. Save first if a game is running.", "Quit Steam", danger=True),
                lambda confirmed: self.steam_control("stop") if confirmed else None,
            )
        else:
            self.steam_control("start")

    def action_steam_big_picture(self) -> None:
        steam = self.steam
        if not steam or not steam["configured"]:
            self.notify(steam["message"] if steam else "Steam status is still loading.", severity="warning")
            return
        self.steam_control("bigpicture")

    @work(exclusive=True, group="steam")
    async def steam_control(self, action: str) -> None:
        steam = await self.call(self.scp.api.steam_control, action, action == "stop")
        if steam:
            self.show_steam(steam)

    @work(exclusive=True, group="actions")
    async def reload(self) -> None:
        self.load_steam()
        actions = await self.call(self.scp.api.actions)
        if actions is None:
            return
        self.actions = {action["id"]: action for action in actions}
        table = self.query_one(DataTable)
        table.clear()
        for action in actions:
            flags = []
            if action.get("dangerous"):
                flags.append("[red]dangerous[/]")
            if not action["enabled"]:
                flags.append("[dim]disabled[/]")
            table.add_row(escape(action["name"]), " ".join(flags), escape(action.get("description") or ""), key=action["id"])

    @on(DataTable.RowSelected, "#actions-table")
    def choose(self, event: DataTable.RowSelected) -> None:
        action = self.actions.get(str(event.row_key.value))
        if not action:
            return
        if not action["enabled"]:
            self.notify(f"{action['name']} is disabled.", severity="warning")
            return
        if action["requires_confirmation"] or action.get("dangerous"):
            self.app.push_screen(
                ConfirmScreen(action["name"], "Confirm this allowlisted server action.", "Run", danger=bool(action.get("dangerous"))),
                lambda confirmed: self.run_action(action["id"], True) if confirmed else None,
            )
        else:
            self.run_action(action["id"], False)

    @work(exclusive=True, group="action-run")
    async def run_action(self, action_id: str, confirmed: bool) -> None:
        output = self.query_one("#action-result", Static)
        output.update("Running…")
        result = await self.call(self.scp.api.run_action, action_id, confirmed)
        if not result:
            output.update("")
            return
        color = "green" if result["success"] else "red"
        text = f"[{color} b]{escape(result['message'])}[/]"
        if result.get("output"):
            text += "\n" + escape(result["output"])
        output.update(text)


class SettingsTab(Page):
    def compose(self) -> ComposeResult:
        yield Label("Server display name", classes="section")
        yield Input(id="server-name")
        yield Label("Remote input", classes="section")
        with Horizontal(classes="selects"):
            with Vertical():
                yield Label("Local keyboard")
                yield Select(LOCAL_KEYBOARD_LAYOUTS, allow_blank=False, id="local-layout")
            with Vertical():
                yield Label("Remote keyboard")
                yield Select(REMOTE_KEYBOARD_LAYOUTS, allow_blank=False, id="remote-layout")
            with Vertical():
                yield Label("Release capture")
                yield Select(CAPTURE_RELEASE_OPTIONS, allow_blank=False, id="release")
        yield Label("External links (one per line: key|label|url)", classes="section")
        yield TextArea(id="links")
        yield Label("Allowed containers (one per line)", classes="section")
        yield TextArea(id="allowed-containers")
        with Horizontal(classes="buttons"):
            yield Button("Save", id="save", variant="primary")

    @work(exclusive=True, group="settings")
    async def reload(self) -> None:
        settings = await self.call(self.scp.api.settings)
        if not settings:
            return
        remote_input = settings["remote_input"]
        self.query_one("#server-name", Input).value = settings["server_name"]
        for selector, key, options in (
            ("#local-layout", "local_keyboard_layout", LOCAL_KEYBOARD_LAYOUTS),
            ("#remote-layout", "remote_keyboard_layout", REMOTE_KEYBOARD_LAYOUTS),
            ("#release", "capture_release_shortcut", CAPTURE_RELEASE_OPTIONS),
        ):
            if any(value == remote_input[key] for _, value in options):
                self.query_one(selector, Select).value = remote_input[key]
        self.query_one("#links", TextArea).text = "\n".join(
            f"{key}|{link['label']}|{link['url']}" for key, link in settings["links"].items()
        )
        self.query_one("#allowed-containers", TextArea).text = "\n".join(settings["allowed_containers"])

    @on(Button.Pressed, "#save")
    @work(exclusive=True, group="settings-save")
    async def save(self) -> None:
        settings = {
            "server_name": self.query_one("#server-name", Input).value.strip(),
            "remote_input": {
                "local_keyboard_layout": self.query_one("#local-layout", Select).value,
                "remote_keyboard_layout": self.query_one("#remote-layout", Select).value,
                "capture_release_shortcut": self.query_one("#release", Select).value,
            },
            "links": parse_links(self.query_one("#links", TextArea).text),
            "allowed_containers": [
                name.strip() for name in self.query_one("#allowed-containers", TextArea).text.splitlines() if name.strip()
            ],
        }
        saved = await self.call(self.scp.api.update_settings, settings)
        if not saved:
            return
        self.scp.sub_title = saved["server_name"]
        try:
            applied = await asyncio.to_thread(self.scp.api.apply_remote_input)
            self.notify(f"Saved. {applied['message']}")
        except ApiError as exc:
            self.notify(f"Saved, but Guacamole was not updated: {exc.message}", severity="warning")


TABS: list[tuple[str, str, type[Page]]] = [
    ("remote", "Remote Desktop", RemoteTab),
    ("terminal", "Terminal", TerminalTab),
    ("services", "Services", ServicesTab),
    ("status", "Status", StatusTab),
    ("docker", "Docker", DockerTab),
    ("actions", "Actions", ActionsTab),
    ("settings", "Settings", SettingsTab),
]


class ServerControlPanelApp(App):
    TITLE = "server-control-panel"
    CSS = """
    Page { padding: 1 2; }
    .intro { margin-bottom: 1; }
    .section { margin-top: 1; text-style: bold; color: $accent; }
    .buttons { height: auto; margin-top: 1; }
    .buttons Button { margin-right: 2; }
    #drives { height: auto; }
    DataTable { height: auto; max-height: 24; }
    #usage { max-height: 40; }
    .selects { height: auto; }
    .selects Vertical { height: auto; margin-right: 2; }
    TextArea { height: 8; }
    #action-result { margin-top: 1; }
    ConfirmScreen, ChoiceScreen { align: center middle; }
    .dialog { width: 64; height: auto; padding: 1 2; border: thick $primary; background: $surface; }
    .dialogTitle { text-style: bold; margin-bottom: 1; }
    .dialogButtons { height: auto; margin-top: 1; }
    .dialogButtons Button { margin-right: 1; }
    """
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        *[Binding(str(index), f"show_tab('{tab_id}')", label, show=False) for index, (tab_id, label, _) in enumerate(TABS, 1)],
    ]

    def __init__(self, api: Api, dashboard_url: str = "", ssh_host: str = "host.docker.internal", ssh_port: int = 22, ssh_user: str = ""):
        super().__init__()
        self.api = api
        self.dashboard_url = dashboard_url.rstrip("/")
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="status"):
            for index, (tab_id, label, tab_class) in enumerate(TABS, 1):
                with TabPane(f"{index} {label}", id=tab_id):
                    yield tab_class(id=f"{tab_id}-tab")
        yield Footer()

    def on_mount(self) -> None:
        self.load_title()

    @work(group="title")
    async def load_title(self) -> None:
        settings = await self.call(self.api.settings)
        if settings:
            self.sub_title = settings["server_name"]

    async def call(self, fn: Callable[..., Any], *args: Any) -> Any:
        """Run a blocking API call off the UI thread; report failures instead of raising."""
        try:
            return await asyncio.to_thread(fn, *args)
        except ApiError as exc:
            self.notify(exc.message, title="API error", severity="error")
            return None

    def action_show_tab(self, tab_id: str) -> None:
        tabbed = self.query_one(TabbedContent)
        # TabbedContent jumps back to whichever pane holds the focused widget,
        # so move focus to the tab bar before switching.
        tabbed.query_one(Tabs).focus()
        tabbed.active = tab_id

    def action_refresh(self) -> None:
        active = self.query_one(TabbedContent).active
        self.query_one(f"#{active}-tab", Page).reload()


def main() -> None:
    api_url = os.environ.get("SCP_API_URL", "http://localhost:8080")
    app = ServerControlPanelApp(
        Api(api_url),
        dashboard_url=os.environ.get("SCP_DASHBOARD_URL", api_url),
        ssh_host=os.environ.get("TERMINAL_SSH_HOST", "host.docker.internal"),
        ssh_port=int(os.environ.get("TERMINAL_SSH_PORT") or 22),
        ssh_user=os.environ.get("TERMINAL_SSH_USER", ""),
    )
    app.run()
