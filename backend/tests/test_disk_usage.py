import os
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from app import disk_usage


class DiskUsageScanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "big").mkdir()
        (root / "big" / "data.bin").write_bytes(os.urandom(512 * 1024))
        (root / "small").mkdir()
        (root / "small" / "note.txt").write_bytes(os.urandom(16 * 1024))
        (root / "file.bin").write_bytes(os.urandom(64 * 1024))
        (root / "escape").symlink_to("/etc")
        disk_usage.HOST_ROOT = root
        disk_usage._cache.clear()

    def tearDown(self):
        self.tmp.cleanup()

    def test_lists_children_largest_first_with_host_paths(self):
        result = disk_usage.scan("/")
        names = [entry.name for entry in result.entries]
        self.assertEqual(names[:3], ["big", "file.bin", "small"])
        big = result.entries[0]
        self.assertEqual(big.path, "/big")
        self.assertTrue(big.is_dir)
        self.assertGreaterEqual(big.size, 512 * 1024)
        self.assertFalse(result.entries[1].is_dir)
        self.assertGreaterEqual(result.size, big.size)
        self.assertIsNone(result.parent)

    def test_normalizes_parent_segments(self):
        result = disk_usage.scan("/small/../big")
        self.assertEqual(result.path, "/big")
        self.assertEqual(result.parent, "/")
        self.assertEqual(disk_usage.scan("/../..").path, "/")

    def test_rejects_unsafe_paths(self):
        for path, code in [("relative", 400), ("/escape", 400), ("/missing", 404), ("/proc", 400), ("/sys/kernel", 400)]:
            with self.subTest(path=path):
                with self.assertRaises(HTTPException) as caught:
                    disk_usage.scan(path)
                self.assertEqual(caught.exception.status_code, code)

    def test_uses_cache_until_refresh(self):
        first = disk_usage.scan("/")
        self.assertIs(disk_usage.scan("/"), first)
        self.assertIsNot(disk_usage.scan("/", refresh=True), first)


if __name__ == "__main__":
    unittest.main()
