import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import steam_control


HOST_SCRIPT = Path("/scripts/host/steam-control.sh")


class SteamControlTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.key_dir = Path(self.tmp.name)
        steam_control.KEY_DIR = self.key_dir

    def tearDown(self):
        self.tmp.cleanup()

    def configure(self, user="ronny"):
        (self.key_dir / "id_ed25519").write_text("key")
        (self.key_dir / "user").write_text(user + "\n")

    def test_not_set_up_never_runs_ssh(self):
        with mock.patch("subprocess.run") as run:
            status = steam_control.get_steam_status()
        run.assert_not_called()
        self.assertFalse(status.configured)
        self.assertEqual(status.state, "not set up")

    def test_unsafe_user_counts_as_not_set_up(self):
        self.configure(user="-oProxyCommand=sh")
        with mock.patch("subprocess.run") as run:
            self.assertFalse(steam_control.get_steam_status().configured)
        run.assert_not_called()

    def test_runs_only_the_requested_verb_over_ssh(self):
        self.configure()
        completed = subprocess.CompletedProcess([], 0, stdout="starting\n", stderr="")
        with mock.patch("subprocess.run", return_value=completed) as run:
            status = steam_control.control_steam("start")
        argv = run.call_args.args[0]
        self.assertEqual(argv[0], "ssh")
        self.assertEqual(argv[-3:], ["--", steam_control.SSH_HOST, "start"])
        self.assertIn("BatchMode=yes", argv)
        self.assertIn(str(self.key_dir / "id_ed25519"), argv)
        self.assertFalse(run.call_args.kwargs["shell"])
        self.assertEqual(status.state, "starting")

    def test_big_picture_is_allowed(self):
        self.configure()
        completed = subprocess.CompletedProcess([], 0, stdout="running\n", stderr="")
        with mock.patch("subprocess.run", return_value=completed) as run:
            self.assertEqual(steam_control.control_steam("bigpicture").state, "running")
        self.assertEqual(run.call_args.args[0][-1], "bigpicture")

    def test_rejects_other_verbs(self):
        self.configure()
        with mock.patch("subprocess.run") as run:
            with self.assertRaises(ValueError):
                steam_control.control_steam("status; reboot")
            with self.assertRaises(ValueError):
                steam_control.control_steam("status")
        run.assert_not_called()

    def test_parses_host_answers(self):
        self.assertEqual(steam_control.parse_result(0, "running").state, "running")
        self.assertEqual(steam_control.parse_result(0, "stopped\n").state, "stopped")
        self.assertEqual(steam_control.parse_result(0, "stopping").state, "stopping")
        self.assertEqual(steam_control.parse_result(3, "no-session: nobody is logged in").state, "no desktop")
        self.assertEqual(steam_control.parse_result(4, "missing: /usr/games/steam is not installed").state, "not installed")
        self.assertEqual(steam_control.parse_result(0, "setup-needed: finish install").state, "needs setup")
        self.assertEqual(steam_control.parse_result(255, "Connection refused").state, "unreachable")
        self.assertEqual(steam_control.parse_result(2, "refused: only status").state, "error")


@unittest.skipUnless(HOST_SCRIPT.exists(), "scripts are mounted at /scripts only inside the backend container")
class HostForcedCommandTest(unittest.TestCase):
    def run_script(self, command):
        env = dict(os.environ, SSH_ORIGINAL_COMMAND=command, STEAM_BIN="/nonexistent/steam")
        return subprocess.run(["sh", str(HOST_SCRIPT)], env=env, capture_output=True, text=True, timeout=10)

    def test_refuses_anything_but_the_allowed_verbs(self):
        for command in ["", "bash", "rm -rf /", "status; reboot", "start now", "STOP", "bigpicture -x"]:
            with self.subTest(command=command):
                result = self.run_script(command)
                self.assertEqual(result.returncode, 2)
                self.assertTrue(result.stdout.startswith("refused"))

    def test_start_without_steam_reports_missing(self):
        result = self.run_script("start")
        self.assertEqual(result.returncode, 4)
        self.assertTrue(result.stdout.startswith("missing"))


if __name__ == "__main__":
    unittest.main()
