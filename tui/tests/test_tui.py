"""Headless tests: drive every tab of the TUI against a fake API."""

import unittest
from unittest import mock

from textual.widgets import Button, DataTable, Input, Select, Static, TabbedContent, TextArea

from scp_tui.api import ApiError
from scp_tui.app import ConfirmScreen, ServerControlPanelApp, ChoiceScreen, parse_links


SETTINGS = {
    "server_name": "Test Server",
    "links": {"guacamole": {"label": "Guacamole", "url": "/guacamole/"}},
    "allowed_containers": ["scp-guacd"],
    "remote_input": {
        "local_keyboard_layout": "sv-se-qwerty",
        "remote_keyboard_layout": "sv-se-qwerty",
        "capture_release_shortcut": "escape",
    },
}

DISK = {"name": "Main drive", "mount": "/", "host_path": "/", "total": 100 * 2**30, "used": 65 * 2**30, "free": 35 * 2**30, "percent": 65.0}


class FakeApi:
    def __init__(self):
        self.calls = []
        self.settings_data = dict(SETTINGS)

    def settings(self):
        return self.settings_data

    def update_settings(self, settings):
        self.calls.append(("update_settings", settings))
        self.settings_data = settings
        return settings

    def system(self):
        return {
            "server_name": "Test Server", "online": True, "cpu_percent": 12.0,
            "memory": {"total": 16 * 2**30, "used": 4 * 2**30, "percent": 25.0},
            "disk": DISK, "disks": [DISK],
            "gpus": [{"name": "RTX 3060", "percent": 3.0, "memory": {"total": 12 * 2**30, "used": 2**30, "percent": 8.0}}],
            "uptime_seconds": 90000, "load_average": [0.1, 0.2, 0.3],
            "network": {"hostname": "box", "addresses": [{"interface": "eth0", "address": "192.168.1.5"}], "bytes_sent": 10, "bytes_recv": 20},
        }

    def disk_usage(self, path, refresh=False):
        self.calls.append(("disk_usage", path, refresh))
        if path == "/":
            entries = [
                {"name": "var", "path": "/var", "size": 900, "is_dir": True, "is_mount": False},
                {"name": "swap.img", "path": "/swap.img", "size": 100, "is_dir": False, "is_mount": False},
            ]
            parent = None
        else:
            entries = [{"name": "lib", "path": path + "/lib", "size": 800, "is_dir": True, "is_mount": False}]
            parent = "/"
        return {"path": path, "parent": parent, "size": 1000, "entries": entries, "hidden_entries": 0, "hidden_size": 0, "scanned_at": 0, "complete": True}

    def containers(self):
        return [
            {"name": "scp-guacd", "image": "guacamole/guacd", "status": "Up", "state": "running", "created": None, "ports": {}, "can_manage": True},
            {"name": "scp-backend", "image": "backend", "status": "Up", "state": "running", "created": None, "ports": {}, "can_manage": False},
        ]

    def container_action(self, name, action):
        self.calls.append(("container_action", name, action))
        return {}

    def services(self):
        return [{"id": "ssh", "name": "SSH", "kind": "tcp", "status": "online", "detail": "host:22", "optional": False}]

    def remote_status(self):
        return {
            "protocol": "RDP", "guacamole_url": "/guacamole/", "rdp_host": "host.docker.internal", "rdp_port": 3389,
            "rdp_reachable": True, "rdp_detail": None, "guacamole_container": "running", "guacd_container": "running",
            "database_container": "running", "connection_hint": "RDP to host.docker.internal:3389",
        }

    def apply_remote_input(self):
        self.calls.append(("apply_remote_input",))
        return {"success": True, "keyboard_layout": "sv-se-qwerty", "updated_connections": 1, "message": "Applied."}

    def actions(self):
        return [
            {"id": "safe", "name": "Safe", "description": "harmless", "type": "script", "requires_confirmation": False, "dangerous": False, "enabled": True},
            {"id": "confirm", "name": "Needs confirm", "description": None, "type": "script", "requires_confirmation": True, "dangerous": False, "enabled": True},
            {"id": "off", "name": "Disabled", "description": None, "type": "script", "requires_confirmation": False, "dangerous": True, "enabled": False},
        ]

    def run_action(self, action_id, confirmed):
        self.calls.append(("run_action", action_id, confirmed))
        return {"id": action_id, "success": True, "message": "Done [ok]", "exit_code": 0, "output": "out [x]"}


class TuiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.api = FakeApi()
        self.app = ServerControlPanelApp(self.api, dashboard_url="http://server:8080")

    async def settle(self, pilot):
        await pilot.pause()
        await self.app.workers.wait_for_complete()
        await pilot.pause()

    async def select_row(self, pilot, table_id, row):
        table = self.app.query_one(table_id, DataTable)
        table.focus()
        table.move_cursor(row=row)
        await pilot.press("enter")
        await self.settle(pilot)

    async def test_status_tab_and_disk_usage_drilldown(self):
        async with self.app.run_test(size=(140, 60)) as pilot:
            await self.settle(pilot)
            self.assertEqual(self.app.query_one(TabbedContent).active, "status")
            self.assertEqual(self.app.sub_title, "Test Server")
            stats = self.app.query_one("#stats", DataTable)
            labels = [str(stats.get_row_at(index)[0]) for index in range(stats.row_count)]
            self.assertEqual(labels, ["Status", "CPU", "RAM", "GPU", "Main drive", "Uptime", "Network"])
            self.assertEqual(self.app.query_one("#addresses", DataTable).row_count, 1)

            await pilot.click(".drive")
            await self.settle(pilot)
            usage = self.app.query_one("#usage", DataTable)
            self.assertEqual(usage.row_count, 2)
            await self.select_row(pilot, "#usage", 0)
            self.assertIn(("disk_usage", "/var", False), self.api.calls)
            await pilot.press("s")
            await self.settle(pilot)
            self.assertIn(("disk_usage", "/var", True), self.api.calls)
            await pilot.press("u")
            await self.settle(pilot)
            self.assertEqual(self.api.calls[-1], ("disk_usage", "/", False))

    async def test_number_keys_switch_tabs_while_a_table_has_focus(self):
        async with self.app.run_test(size=(140, 50)) as pilot:
            await self.settle(pilot)
            self.app.query_one("#stats", DataTable).focus()
            await pilot.press("7")
            await self.settle(pilot)
            self.assertEqual(self.app.query_one(TabbedContent).active, "settings")
            await pilot.press("5")
            await self.settle(pilot)
            self.assertEqual(self.app.query_one(TabbedContent).active, "docker")

    async def test_remote_tab_shows_status_and_applies_layout(self):
        async with self.app.run_test(size=(140, 50)) as pilot:
            await pilot.press("1")
            await self.settle(pilot)
            self.assertEqual(self.app.query_one("#remote-status", DataTable).row_count, 4)
            remote_input = self.app.query_one("#remote-input", DataTable)
            self.assertEqual(str(remote_input.get_row_at(1)[1]), "Swedish")
            await pilot.click("#apply-input")
            await self.settle(pilot)
            self.assertIn(("apply_remote_input",), self.api.calls)

    async def test_services_tab(self):
        async with self.app.run_test(size=(140, 50)) as pilot:
            await pilot.press("3")
            await self.settle(pilot)
            self.assertEqual(self.app.query_one("#services-table", DataTable).row_count, 1)

    async def test_docker_actions_need_choice_and_confirmation(self):
        async with self.app.run_test(size=(140, 50)) as pilot:
            await pilot.press("5")
            await self.settle(pilot)
            await self.select_row(pilot, "#containers-table", 1)  # not allowlisted
            self.assertNotIsInstance(self.app.screen, ChoiceScreen)

            await self.select_row(pilot, "#containers-table", 0)
            self.assertIsInstance(self.app.screen, ChoiceScreen)
            next(b for b in self.app.screen.query(Button) if b.name == "stop").press()
            await self.settle(pilot)
            self.assertIsInstance(self.app.screen, ConfirmScreen)
            self.assertNotIn(("container_action", "scp-guacd", "stop"), self.api.calls)
            await pilot.press("y")
            await self.settle(pilot)
            self.assertIn(("container_action", "scp-guacd", "stop"), self.api.calls)

    async def test_actions_confirm_only_when_required(self):
        async with self.app.run_test(size=(140, 50)) as pilot:
            await pilot.press("6")
            await self.settle(pilot)
            await self.select_row(pilot, "#actions-table", 0)
            self.assertIn(("run_action", "safe", False), self.api.calls)
            self.assertIn("out [x]", str(self.app.query_one("#action-result", Static).render()))

            await self.select_row(pilot, "#actions-table", 1)
            self.assertIsInstance(self.app.screen, ConfirmScreen)
            await pilot.press("n")
            await self.settle(pilot)
            self.assertNotIn(("run_action", "confirm", True), self.api.calls)
            await self.select_row(pilot, "#actions-table", 1)
            await pilot.press("y")
            await self.settle(pilot)
            self.assertIn(("run_action", "confirm", True), self.api.calls)

            await self.select_row(pilot, "#actions-table", 2)  # disabled
            self.assertFalse(any(call[:2] == ("run_action", "off") for call in self.api.calls))

    async def test_settings_save_then_apply(self):
        async with self.app.run_test(size=(140, 70)) as pilot:
            await pilot.press("7")
            await self.settle(pilot)
            self.assertEqual(self.app.query_one("#server-name", Input).value, "Test Server")
            self.assertEqual(self.app.query_one("#remote-layout", Select).value, "sv-se-qwerty")
            self.app.query_one("#server-name", Input).value = "Renamed"
            self.app.query_one("#remote-layout", Select).value = "de-de-qwertz"
            self.app.query_one("#allowed-containers", TextArea).text = "scp-guacd\n\nscp-guacamole\n"
            self.app.query_one("#save", Button).press()
            await self.settle(pilot)
            saved = next(call[1] for call in self.api.calls if call[0] == "update_settings")
            self.assertEqual(saved["server_name"], "Renamed")
            self.assertEqual(saved["remote_input"]["remote_keyboard_layout"], "de-de-qwertz")
            self.assertEqual(saved["allowed_containers"], ["scp-guacd", "scp-guacamole"])
            self.assertEqual(saved["links"], SETTINGS["links"])
            self.assertEqual(self.api.calls[-1], ("apply_remote_input",))
            self.assertEqual(self.app.sub_title, "Renamed")

    async def test_terminal_refuses_unsafe_usernames(self):
        async with self.app.run_test(size=(140, 50)) as pilot:
            await pilot.press("2")
            await self.settle(pilot)
            with mock.patch("scp_tui.app.subprocess.call") as call:
                for name in ["-oProxyCommand=id", "a b", "root@evil", ""]:
                    self.app.query_one("#ssh-user", Input).value = name
                    self.app.query_one("#ssh-connect", Button).press()
                    await self.settle(pilot)
                call.assert_not_called()

                self.app.query_one("#ssh-user", Input).value = "ronny"
                with mock.patch.object(self.app, "suspend"):
                    self.app.query_one("#ssh-connect", Button).press()
                    await self.settle(pilot)
                call.assert_called_once()
                self.assertEqual(call.call_args[0][0][-3:], ["-l", "ronny", "host.docker.internal"])

    async def test_api_errors_become_notifications(self):
        def broken():
            raise ApiError(0, "Cannot reach backend")

        self.api.services = broken
        async with self.app.run_test(size=(140, 50)) as pilot:
            await pilot.press("3")
            await self.settle(pilot)
            self.assertTrue(any("Cannot reach backend" in str(n.message) for n in self.app._notifications))


class HelperTest(unittest.TestCase):
    def test_parse_links_skips_incomplete_lines(self):
        self.assertEqual(
            parse_links("a|A|/a\nbroken|x\n\n b | B | http://b \n"),
            {"a": {"label": "A", "url": "/a"}, "b": {"label": "B", "url": "http://b"}},
        )


if __name__ == "__main__":
    unittest.main()
