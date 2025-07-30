import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image
import pytesseract
from screenshot_utils import extract_datetime, extract_game_length, determine_result, extract_map_name, extract_hero_data
import config
import map_categories 

import unittest

pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD

class TestStatsFunctions(unittest.TestCase):
    """Unit tests for screenshot_utils module."""

    def test_testscreenshot1(self):
        """Test the screenshot_utils module with a sample screenshot."""
        image = Image.open("tests/test_screenshots/testingscreenshot1.jpg")
        text = pytesseract.image_to_string(image)

        self.assertEqual(extract_datetime(text, config.DATE_INPUT_FORMAT,config.DATE_OUTPUT_FORMAT), "2025-06-26 03:00")
        self.assertEqual(extract_game_length(image, text), (923, '15:23', None))
        self.assertEqual(determine_result(text), "DEFEAT")
        self.assertEqual(extract_map_name(image, map_categories.OVERWATCH_MAPS, map_categories.MAP_CORRECTIONS, config.TESSERACT_CONFIG), "King's Row")
        self.assertEqual(extract_hero_data(image), [{'hero': 'Sigma', 'percentage': 65}, {'hero': 'Hazard', 'percentage': 28}, {'hero': 'Mauga', 'percentage': 7}])

    def test_testscreenshot2(self):
        """Test the screenshot_utils module with a sample screenshot."""
        image = Image.open("tests/test_screenshots/testingscreenshot2.jpg")
        text = pytesseract.image_to_string(image)

        self.assertEqual(extract_datetime(text, config.DATE_INPUT_FORMAT,config.DATE_OUTPUT_FORMAT), "2025-05-08 05:44")
        self.assertEqual(extract_game_length(image, text), (937, '15:37', None))
        self.assertEqual(determine_result(text), "DEFEAT")
        self.assertEqual(extract_map_name(image, map_categories.OVERWATCH_MAPS, map_categories.MAP_CORRECTIONS, config.TESSERACT_CONFIG), "Numbani")
        self.assertEqual(extract_hero_data(image), [{'hero': 'Zarya', 'percentage': 63}, {'hero': 'D.Va', 'percentage': 29}, {'hero': 'Mauga', 'percentage': 8}])

    def test_testscreenshot3(self):
        """Test the screenshot_utils module with a sample screenshot."""
        image = Image.open("tests/test_screenshots/testingscreenshot3.jpg")
        text = pytesseract.image_to_string(image)

        self.assertEqual(extract_datetime(text, config.DATE_INPUT_FORMAT,config.DATE_OUTPUT_FORMAT), "2025-07-13 17:58")
        self.assertEqual(extract_game_length(image, text), (465, '7:45', None))
        self.assertEqual(determine_result(text), "VICTORY")
        self.assertEqual(extract_map_name(image, map_categories.OVERWATCH_MAPS, map_categories.MAP_CORRECTIONS, config.TESSERACT_CONFIG), "Aatlis")
        self.assertEqual(extract_hero_data(image), [{'hero': 'Zarya', 'percentage': 100}])


if __name__ == "__main__":
    unittest.main()


