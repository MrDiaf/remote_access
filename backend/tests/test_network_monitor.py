import os
import tempfile
import time
import unittest
from pathlib import Path

from app import network_monitor


PING_OK = """PING 1.1.1.1 (1.1.1.1) 56(84) bytes of data.

--- 1.1.1.1 ping statistics ---
30 packets transmitted, 28 received, 6.66667% packet loss, time 29041ms
rtt min/avg/max/mdev = 10.112/14.503/88.200/9.871 ms
"""
PING_DEAD = """PING 1.1.1.1 (1.1.1.1) 56(84) bytes of data.

--- 1.1.1.1 ping statistics ---
30 packets transmitted, 0 received, +12 errors, 100% packet loss, time 29380ms
"""


class ParseTest(unittest.TestCase):
    def test_parses_loss_and_latency(self):
        self.assertEqual(network_monitor.parse_ping(PING_OK), (30, 28, 14.503, 88.2, 9.871))

    def test_total_loss_has_no_latency(self):
        self.assertEqual(network_monitor.parse_ping(PING_DEAD), (30, 0, None, None, None))

    def test_unreachable_network_is_not_parsed(self):
        self.assertIsNone(network_monitor.parse_ping("ping: connect: Network is unreachable\n"))


class GatewayTest(unittest.TestCase):
    def test_reads_default_gateway_from_host_routes(self):
        with tempfile.TemporaryDirectory() as tmp:
            routes = Path(tmp) / "route"
            routes.write_text(
                "Iface\tDestination\tGateway\tFlags\n"
                "docker0\t000011AC\t00000000\t0001\n"
                "enp34s0\t00000000\t0100A8C0\t0003\n"
            )
            network_monitor.HOST_ROUTES = routes
            os.environ.pop("NETMON_GATEWAY", None)
            self.assertEqual(network_monitor.host_gateway(), "192.168.0.1")
            ids = [target.id for target in network_monitor.targets()]
            self.assertEqual(ids, ["router", "cloudflare", "google", "tailscale"])

    def test_no_routes_means_no_router_target(self):
        network_monitor.HOST_ROUTES = Path("/nonexistent/route")
        os.environ.pop("NETMON_GATEWAY", None)
        self.assertEqual([target.id for target in network_monitor.targets()], ["cloudflare", "google", "tailscale"])

    def test_tailscale_can_be_turned_off(self):
        os.environ["NETMON_TAILSCALE"] = "off"
        try:
            self.assertNotIn("tailscale", [target.id for target in network_monitor.targets()])
        finally:
            os.environ.pop("NETMON_TAILSCALE")


class TailscaleRelayTest(unittest.TestCase):
    DERP_MAP = {
        "Regions": {
            "1": {"RegionCode": "nyc", "RegionName": "New York City", "Nodes": [{"HostName": "a", "IPv4": "10.0.0.1"}]},
            "4": {"RegionCode": "fra", "RegionName": "Frankfurt", "Nodes": [{"HostName": "b", "IPv4": "10.0.0.4"}]},
            "14": {"RegionCode": "ams", "RegionName": "Amsterdam", "Nodes": [
                {"HostName": "stun", "IPv4": "10.0.0.13", "STUNOnly": True},
                {"HostName": "c", "IPv4": "10.0.0.14"},
            ]},
            "99": {"RegionCode": "bad", "RegionName": "Avoided", "Avoid": True, "Nodes": [{"HostName": "d", "IPv4": "10.0.0.99"}]},
        }
    }

    def test_picks_the_fastest_region_and_skips_avoided_and_stun_only(self):
        latency = {"10.0.0.1": 110.0, "10.0.0.4": 39.1, "10.0.0.14": 38.8, "10.0.0.99": 1.0, "10.0.0.13": 1.0}
        relay = network_monitor.choose_relay(self.DERP_MAP, latency.get)
        self.assertEqual(relay.host, "10.0.0.14")
        self.assertEqual(relay.note, "nearest relay: Amsterdam")
        self.assertTrue(relay.internet)

    def test_region_code_pins_the_relay(self):
        latency = {"10.0.0.1": 110.0, "10.0.0.4": 39.1, "10.0.0.14": 38.8}
        relay = network_monitor.choose_relay(self.DERP_MAP, latency.get, "fra")
        self.assertEqual(relay.host, "10.0.0.4")
        self.assertEqual(relay.note, "relay: Frankfurt")

    def test_no_answer_means_no_relay(self):
        self.assertIsNone(network_monitor.choose_relay(self.DERP_MAP, lambda ip: None))

    def test_override_skips_the_lookup(self):
        os.environ["NETMON_TAILSCALE"] = "100.64.0.1"
        try:
            self.assertEqual(network_monitor.nearest_tailscale_relay().host, "100.64.0.1")
        finally:
            os.environ.pop("NETMON_TAILSCALE")


class HistoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        network_monitor.DB_PATH = Path(self.tmp.name) / "network.sqlite3"
        network_monitor.HOST_ROUTES = Path("/nonexistent/route")
        os.environ["NETMON_GATEWAY"] = "192.168.0.1"
        self.now = int(time.time()) // 60 * 60

    def tearDown(self):
        os.environ.pop("NETMON_GATEWAY", None)
        self.tmp.cleanup()

    def insert(self, minutes_ago, target, received, avg=12.0, worst=40.0):
        with network_monitor._connect() as db:
            for half in (0, 30):
                db.execute(
                    "INSERT INTO samples VALUES (?, ?, 30, ?, ?, ?, 1.0)",
                    (self.now - minutes_ago * 60 + half, target, received, avg if received else None, worst if received else None),
                )

    def fill(self, minutes, router=30, internet=30):
        for minute in minutes:
            self.insert(minute, "router", router, avg=1.0, worst=3.0)
            self.insert(minute, "cloudflare", internet)
            self.insert(minute, "google", internet)

    def test_summary_and_series(self):
        self.fill(range(10, 20))
        self.fill([5], internet=15)
        data = network_monitor.history(1)
        self.assertEqual(data.bucket_seconds, 60)
        cloudflare = next(item for item in data.summary if item.id == "cloudflare")
        self.assertEqual(cloudflare.sent, 11 * 60)
        self.assertEqual(cloudflare.loss, round(100 * 30 / 660, 2))
        self.assertEqual(cloudflare.max_ms, 40.0)
        self.assertTrue(all(point.sent == 60 for point in data.series["router"]))

    def test_problem_outside_home_network(self):
        self.fill(range(10, 20))
        self.fill([6, 5], internet=0)
        events = network_monitor.history(1).events
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].end - events[0].start, 120)
        self.assertEqual(events[0].internet_loss, 100.0)
        self.assertEqual(events[0].router_loss, 0.0)

    def test_quiet_minute_between_bad_ones_is_one_problem(self):
        self.fill([9, 7], internet=10)
        self.fill([8])
        self.assertEqual(len(network_monitor.history(1).events), 1)

    def test_report_points_at_the_home_network(self):
        self.fill(range(10, 20))
        self.fill([5], router=0, internet=0)
        text = network_monitor.report(1, "Home Server").text
        self.assertIn("Network quality report: Home Server", text)
        self.assertIn("Router (192.168.0.1)", text)
        self.assertIn("inside the home network", text)
        self.assertIn("Internet loss", text)
        self.assertIn("no data", text)  # the Tailscale relay has no samples here

    def test_empty_report(self):
        self.assertIn("No measurements", network_monitor.report(24, "Home Server").text)

    def test_long_ranges_use_bigger_buckets(self):
        self.assertEqual(network_monitor.history(24).bucket_seconds, 300)
        self.assertEqual(network_monitor.history(24 * 7).bucket_seconds, 3600)
        self.assertEqual(network_monitor.history(24 * 30).bucket_seconds, 21600)


if __name__ == "__main__":
    unittest.main()
