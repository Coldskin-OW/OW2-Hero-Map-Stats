# DebugScreenshot.py

import sys
import argparse
from PIL import Image
import pytesseract
import os
import logging
from pathlib import Path
from screenshot_utils import *
from map_categories import OVERWATCH_MAPS, MAP_CORRECTIONS
import config
from heros import OVERWATCH_HEROES, HERO_CORRECTIONS

# Configuration
pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD

# Setup logging to print to console
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def debug_single_screenshot(file_path: str):
    """Processes a single screenshot and prints a detailed report"""
    print("-" * 50)
    print(f"Analyzing Screenshot: {Path(file_path).name}")
    print("-" * 50)

    if not os.path.exists(file_path):
        logging.error(f"File not found at '{file_path}'")
        return

    try:
        image = Image.open(file_path)
    except Exception as e:
        logging.error(f"Could not open image file: {e}")
        return

    print("\n--- 1. General Information Extraction ---")
    full_text = pytesseract.image_to_string(image)
    print(f"Full OCR Text (for general info):\n---\n{full_text.strip()}\n---")

    game_datetime = extract_datetime(full_text, config.DATE_INPUT_FORMAT, config.DATE_OUTPUT_FORMAT)
    game_length_sec, raw_len_text1, raw_len_text2 = extract_game_length(image, full_text)
    game_result = determine_result(full_text)
    game_map, raw_map_text = extract_map_name(image, OVERWATCH_MAPS, MAP_CORRECTIONS, config.TESSERACT_CONFIG, return_raw=True)

    print(f"\nExtracted Datetime: {game_datetime} {'(VALID)' if game_datetime else '(INVALID)'}")
    print(f"Extracted Length  : {game_length_sec} seconds {'(VALID)' if game_length_sec is not None else '(INVALID)'}")
    if raw_len_text1 is not None:
        print(f"Raw Length (Attempt 1 - Full Text): '{raw_len_text1}'")
    if raw_len_text2 is not None:
        print(f"Raw Length (Attempt 2 - Region OCR): '{raw_len_text2}'")
    print(f"Extracted Result  : {game_result} {'(VALID)' if game_result else '(INVALID)'}")

    print("\n--- 2. Map Name Extraction ---")
    print(f"Raw Map OCR Text  : '{raw_map_text}'")
    print(f"Extracted Map     : {game_map} {'(VALID)' if game_map else '(INVALID)'}")

    print("\n--- 3. Hero Data Extraction ---")
    hero_data = extract_hero_data(image, debug=True)

    print("\n" + "=" * 20 + " FINAL REPORT " + "=" * 20)
    print(f"  File           : {Path(file_path).name}")
    print(f"  Map            : {game_map}")
    print(f"  Date           : {game_datetime}")
    print(f"  Result         : {game_result}")
    print(f"  Length (sec)   : {game_length_sec}")
    if raw_len_text1 is not None:
        print(f"  Length Raw (Att. 1): '{raw_len_text1}'")
    if raw_len_text2 is not None:
        print(f"  Length Raw (Att. 2): '{raw_len_text2}'")
    print(f"  Hero Data      : {hero_data}")

    is_fully_valid = all([
        game_datetime,
        game_map,
        game_result,
        game_length_sec is not None,
        hero_data
    ])

    print("\n  Overall Read Status: " + ("VALID" if is_fully_valid else "INVALID"))
    if not is_fully_valid:
        print("  Reason(s) for invalid status:")
        if not game_datetime: print("    - Could not extract date/time.")
        if not game_map: print("    - Could not extract map name.")
        if not game_result: print("    - Could not determine result (Win/Loss/Draw).")
        if game_length_sec is None: print("    - Could not extract game length.")
        if not hero_data: print("    - Could not extract valid hero data.")
    print("=" * 54 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Debug screenshot OCR processing for a single file.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "filepath",
        help="The full path to the screenshot image file to debug.\nExample: python DebugScreenshot.py \"C:\\Users\\YourUser\\Pictures\\screenshot.png\""
    )
    args = parser.parse_args()

    if validate_tesseract_installation(config.TESSERACT_CMD)[0]:
        debug_single_screenshot(args.filepath)
    else:
        sys.exit(1)