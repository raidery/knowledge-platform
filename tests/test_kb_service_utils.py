import unittest
from apps.kb_service.core.utils import parse_size


class TestUtils(unittest.TestCase):
    def test_parse_size_bytes(self):
        """Test parsing byte values"""
        self.assertEqual(parse_size("1024"), 1024)
        self.assertEqual(parse_size("1048576"), 1048576)
        self.assertEqual(parse_size(1024), 1024)

    def test_parse_size_with_units(self):
        """Test parsing values with units"""
        # Test uppercase units
        self.assertEqual(parse_size("1K"), 1024)
        self.assertEqual(parse_size("1M"), 1048576)
        self.assertEqual(parse_size("1G"), 1073741824)

        # Test lowercase units
        self.assertEqual(parse_size("1k"), 1024)
        self.assertEqual(parse_size("1m"), 1048576)
        self.assertEqual(parse_size("1g"), 1073741824)

        # Test with B suffix
        self.assertEqual(parse_size("1KB"), 1024)
        self.assertEqual(parse_size("1MB"), 1048576)
        self.assertEqual(parse_size("1GB"), 1073741824)

        # Test lowercase with B suffix
        self.assertEqual(parse_size("1kb"), 1024)
        self.assertEqual(parse_size("1mb"), 1048576)
        self.assertEqual(parse_size("1gb"), 1073741824)

    def test_parse_size_decimal(self):
        """Test parsing decimal values"""
        self.assertEqual(parse_size("1.5M"), int(1.5 * 1048576))
        self.assertEqual(parse_size("2.25G"), int(2.25 * 1073741824))

    def test_parse_size_invalid(self):
        """Test parsing invalid values"""
        with self.assertRaises(ValueError):
            parse_size("invalid")

        with self.assertRaises(ValueError):
            parse_size("1InvalidUnit")


if __name__ == '__main__':
    unittest.main()