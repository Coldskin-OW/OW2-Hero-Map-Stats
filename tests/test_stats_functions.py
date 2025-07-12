import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from stats_functions import calculate_stats

import unittest

class TestStatsFunctions(unittest.TestCase):
    """Unit tests for stats_functions module."""

    def test_calculate_stats_empty(self):
        """Test calculate_stats with empty input."""
        self.assertEqual(calculate_stats([]), {})

    def test_calculate_stats_error(self):
        """Test calculate_stats handles exceptions gracefully."""
        class BadList(list):
            def __iter__(self):
                raise Exception("Test error")
        self.assertEqual(calculate_stats(BadList()), {})

    def test_validate_seasons_param_type_error(self):
        """Test that validate_seasons_param raises TypeError for bad input."""
        from stats_functions import validate_seasons_param
        with self.assertRaises(TypeError):
            validate_seasons_param(16)  # Not a list  # type: ignore

    def test_validate_date_string(self):
        """Test date string validation."""
        from stats_functions import validate_date_string
        self.assertTrue(validate_date_string("2024-06-01"))
        self.assertFalse(validate_date_string("bad-date"))

if __name__ == "__main__":
    unittest.main()
