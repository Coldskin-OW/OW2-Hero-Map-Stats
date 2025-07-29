import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest

class TestStatsFunctions(unittest.TestCase):
    """Unit tests for stats_functions module."""

    def test_validate_seasons_param_type_error(self):
        """Test that validate_seasons_param raises TypeError for bad input."""
        from stats_functions import validate_seasons_param
        with self.assertRaises(TypeError):
            validate_seasons_param(18)  # Not a list  # type: ignore
            validate_seasons_param("18")  # Not a list  # type: ignore
            validate_seasons_param(None) # Not a list  # type: ignore
            validate_seasons_param(18.5)  # Not a list  # type: ignore
            validate_seasons_param([])  # Empty list is valid

    def test_validate_date_string(self):
        """Test date string validation."""
        from stats_functions import validate_date_string
        self.assertTrue(validate_date_string("2024-06-01"))
        self.assertFalse(validate_date_string("2024-06-32"))
        self.assertFalse(validate_date_string("2024-13-01"))
        self.assertFalse(validate_date_string("bad-date"))

if __name__ == "__main__":
    unittest.main()
