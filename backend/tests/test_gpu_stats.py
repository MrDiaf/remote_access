import unittest

from app.system_info import _parse_nvidia_smi


class NvidiaSmiParseTest(unittest.TestCase):
    def test_parses_usage_and_memory(self):
        gpus = _parse_nvidia_smi("NVIDIA GeForce RTX 3060, 37, 774, 12288\n")
        self.assertEqual(len(gpus), 1)
        self.assertEqual(gpus[0].name, "NVIDIA GeForce RTX 3060")
        self.assertEqual(gpus[0].percent, 37)
        self.assertEqual(gpus[0].memory.used, 774 * 1024 * 1024)
        self.assertEqual(gpus[0].memory.total, 12288 * 1024 * 1024)
        self.assertEqual(gpus[0].memory.percent, 6.3)

    def test_skips_unreported_values(self):
        self.assertEqual(_parse_nvidia_smi("Some GPU, [N/A], 10, 100\n\n"), [])


if __name__ == "__main__":
    unittest.main()
