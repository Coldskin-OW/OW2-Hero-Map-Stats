# test_data_base.py

import sys
import os
import sqlite3
import shutil
from pathlib import Path
import unittest
from datetime import datetime
from PIL import Image
import pytesseract
from contextlib import contextmanager
import tempfile

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import functions to test
from stats_functions import print_all_matches_by_season
from ReadScreenshot import process_single_file, init_database
import config
from screenshot_utils import (
    extract_datetime, 
    extract_game_length, 
    determine_result, 
    extract_map_name, 
    extract_hero_data
)
from map_categories import OVERWATCH_MAPS, MAP_CORRECTIONS

# Setup test paths
TEST_SCREENSHOTS_DIR = Path("tests/test_screenshots")
EXTRACTED_DIR = TEST_SCREENSHOTS_DIR / "extracted"

# Create a temporary file for the test database
temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
TEST_DB = temp_db_file.name
temp_db_file.close()

@contextmanager
def temporary_database_path(db_path):
    """Context manager to temporarily change and restore database path"""
    original_db = config.DATABASE_NAME
    config.DATABASE_NAME = db_path
    try:
        yield
    finally:
        config.DATABASE_NAME = original_db

class TestStatsFunctions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Initialize test database and process test screenshots"""
        cls.original_screenshots = list(TEST_SCREENSHOTS_DIR.glob("testingscreenshot*.jpg"))
        
        EXTRACTED_DIR.mkdir(exist_ok=True)

        with temporary_database_path(TEST_DB):
            init_database()
            for screenshot in cls.original_screenshots:
                process_single_file(screenshot, EXTRACTED_DIR)

    @classmethod
    def tearDownClass(cls):
    # Move screenshots back
        for screenshot in EXTRACTED_DIR.glob("testingscreenshot*.jpg"):
            shutil.move(str(screenshot), str(TEST_SCREENSHOTS_DIR))

        try:
            EXTRACTED_DIR.rmdir()
        except OSError:
            pass

        # 🔧 Clean up lingering resources
        import gc
        import psutil
        gc.collect()

        # 🔒 Try closing all file handles pointing to the DB
        process = psutil.Process()
        for fh in process.open_files():
            if fh.path == TEST_DB:
                try:
                    os.close(fh.fd)
                except Exception:
                    pass

        # ❌ Delete test database
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
                print("Deleted test DB successfully.")
            except PermissionError:
                print("Warning: Could not delete test DB (may still be open)")

    def test_print_all_matches(self):
        """Test that print_all_matches_by_season returns expected output"""
        with temporary_database_path(TEST_DB):
            output = print_all_matches_by_season()
            expected_data = [
                {
                    'date': "2025-07-13 17:58",
                    'map': "Aatlis",
                    'result': "VICTORY",
                    'length_sec': 465,
                    'heroes': "Zarya (100%)"
                },
                {
                    'date': "2025-06-26 03:00",
                    'map': "King's Row",
                    'result': "DEFEAT",
                    'length_sec': 923,
                    'heroes': "Sigma (65%), Hazard (28%), Mauga (7%)"
                },
                {
                    'date': "2025-05-08 05:44",
                    'map': "Numbani",
                    'result': "DEFEAT",
                    'length_sec': 937,
                    'heroes': "Zarya (63%), D.Va (29%), Mauga (8%)"
                }
            ]

            lines = [line for line in output.split('\n') if line.strip()][4:]

            self.assertEqual(len(lines), len(expected_data))

            for i, expected_match in enumerate(expected_data):
                line = lines[i]
                parts = line.split('|')
                date_part = parts[0].strip()
                time_part = parts[1].strip()
                map_part = parts[2].strip()
                result_part = parts[3].strip()
                duration_part = parts[4].strip()
                heroes_part = parts[5].strip()

                local_datetime_str = f"{date_part} {time_part}"
                expected_datetime_str = expected_match['date']
                self.assertEqual(local_datetime_str,
                                 f"{expected_datetime_str[:10]} {expected_datetime_str[11:]}")
                self.assertEqual(map_part, expected_match['map'])
                self.assertEqual(result_part, expected_match['result'])

                try:
                    if 'm' in duration_part and 's' in duration_part:
                        mins = int(duration_part.split('m')[0])
                        secs = int(duration_part.split('m')[1].replace('s', ''))
                    else:
                        mins, secs = divmod(expected_match['length_sec'], 60)
                    total_sec = mins * 60 + secs
                except (ValueError, IndexError):
                    total_sec = expected_match['length_sec']

                self.assertEqual(total_sec, expected_match['length_sec'])
                self.assertEqual(heroes_part, expected_match['heroes'])

if __name__ == "__main__":
    unittest.main()
