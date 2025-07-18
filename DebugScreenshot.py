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

# Generate a whitelist string of all hero names in uppercase for OCR
hero_names_upper = '|'.join(
    [hero.upper() for role in OVERWATCH_HEROES.values() for hero in role] +
    list(HERO_CORRECTIONS.keys())
)

# Optimized Tesseract config for hero names
HERO_CONFIG = f'''
--psm 7 
--oem 3 
-c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZ :.-éüöäñ"
-c preserve_interword_spaces=1
-c textord_force_make_prop_words=1
-c language_model_penalty_non_freq_dict_word=0.5
-c language_model_penalty_non_dict_word=0.3
-c user_words="{hero_names_upper}"
'''

def recognize_hero(region, region_name) -> str | None:
    """Debug version of recognize_hero with print statements"""
    print(f"  - Recognizing hero for region: {region_name}")
    
    # First attempt with primary settings
    processed1 = preprocess_hero_region(
        region, 
        PRIMARY_HERO_SETTINGS['HERO_THRESHOLD'], 
        PRIMARY_HERO_SETTINGS['HERO_CONTRAST'], 
        PRIMARY_HERO_SETTINGS['HERO_RESIZE']
    )
    text1 = pytesseract.image_to_string(processed1, config=HERO_CONFIG).strip()
    hero1 = clean_hero_name(text1, HERO_CORRECTIONS, OVERWATCH_HEROES)
    print(f"    - Attempt 1: Raw='{text1}', Cleaned='{hero1}'")
    if hero1: return hero1

    # Second attempt with alternative settings
    processed2 = preprocess_hero_region(
        region,
        SECONDARY_HERO_SETTINGS['HERO_THRESHOLD'],
        SECONDARY_HERO_SETTINGS['HERO_CONTRAST'],
        SECONDARY_HERO_SETTINGS['HERO_RESIZE']
    )
    text2 = pytesseract.image_to_string(processed2, config=HERO_CONFIG).strip()
    hero2 = clean_hero_name(text2, HERO_CORRECTIONS, OVERWATCH_HEROES)
    print(f"    - Attempt 2: Raw='{text2}', Cleaned='{hero2}'")    
    if hero2: return hero2

    # Third attempt with tertiary settings
    processed3 = preprocess_hero_region(
        region,
        TERTIARY_HERO_SETTINGS['HERO_THRESHOLD'],
        TERTIARY_HERO_SETTINGS['HERO_CONTRAST'],
        TERTIARY_HERO_SETTINGS['HERO_RESIZE']
    )
    text3 = pytesseract.image_to_string(processed3, config=HERO_CONFIG).strip()
    hero3 = clean_hero_name(text3, HERO_CORRECTIONS, OVERWATCH_HEROES)
    print(f"    - Attempt 3: Raw='{text3}', Cleaned='{hero3}'")    
    return hero3

def _extract_hero_data_attempt(image, regions, settings_name, settings):
    """Debug version of hero data extraction with print statements"""
    print(f"\n  - Attempting hero data extraction with settings: '{settings_name}'")
    hero_data, total_percentage, num_heroes = [], 0, 0
    
    for i in range(0, len(regions), 2):
        hero_key, hero_coords = regions[i]
        perc_key, perc_coords = regions[i+1]

        hero_region = image.crop(calculate_scaled_region(image.width, image.height, hero_coords))
        hero_name = recognize_hero(hero_region, hero_key)

        if hero_name is None:
            print(f"    - Hero: '{hero_key}' -> SKIPPED (No valid hero name recognized)")
            continue

        perc_region = image.crop(calculate_scaled_region(image.width, image.height, perc_coords))
        processed_perc = preprocess_percentage_region(perc_region, settings)
        perc_text = pytesseract.image_to_string(
            processed_perc, 
            config='--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789%'
        ).strip()
        percentage = extract_percentage(perc_text)
        print(f"    - Hero: '{hero_name}', Percentage Raw Text: '{perc_text}', Extracted: {percentage}%")

        if percentage > 0:
            hero_data.append({'hero': hero_name, 'percentage': percentage})
            total_percentage += percentage
            num_heroes += 1

    print(f"  - Result for '{settings_name}': {num_heroes} heroes, {total_percentage}% total")
    return hero_data, total_percentage, num_heroes

def extract_hero_data(image):
    """Debug version of hero data extraction with print statements"""
    regions = sorted(HERO_REGIONS.items())
    primary_data, primary_total, primary_heroes = _extract_hero_data_attempt(
        image, regions, "Primary", PRIMARY_PERCENTAGE_SETTINGS
    )

    needs_retry = False
    if primary_heroes > 0:
        if primary_total > PERCENTAGE_MAX or (primary_heroes <= 2 and primary_total < PERCENTAGE_MIN):
            needs_retry = True
            print(f"\n  - Primary result ({primary_total}%) is outside acceptable range. Retrying with secondary settings.")

    if not needs_retry:
        if primary_heroes == 0:
            print("\n[!] No heroes found with primary settings. No retry will be attempted.")
            return None
        print(f"\n  - Using primary results. Final Validation: {primary_total}% total.")
        return primary_data if PERCENTAGE_MIN <= primary_total <= PERCENTAGE_MAX else None

    secondary_data, secondary_total, secondary_heroes = _extract_hero_data_attempt(
        image, regions, "Secondary", SECONDARY_PERCENTAGE_SETTINGS
    )

    final_data, final_total = primary_data, primary_total
    if secondary_heroes > primary_heroes:
        print(f"\n  - Using secondary results (found more heroes: {secondary_heroes} vs {primary_heroes}).")
        final_data, final_total = secondary_data, secondary_total
    elif secondary_heroes == primary_heroes and abs(secondary_total - 100) < abs(primary_total - 100):
        print(f"\n  - Using secondary results (closer to 100%: {secondary_total}% vs {primary_total}%).")
        final_data, final_total = secondary_data, secondary_total
    else:
        print(f"\n  - Sticking with primary results.")

    print(f"  - Final Validation: {final_total}% total.")
    if final_total > PERCENTAGE_MAX or (len(final_data) <= 2 and final_total < PERCENTAGE_MIN):
        print(f"[!] Final hero data is invalid (Total: {final_total}%)")
        return None

    return final_data

def extract_map_name_debug(image):
    """Debug version of map name extraction"""
    try:
        map_region_coords = calculate_scaled_region(image.width, image.height, REFERENCE_MAP_REGION)
        map_img = image.crop(map_region_coords).convert('L')
        map_img = map_img.point(lambda x: 0 if x < 200 else 255)
        raw_text = pytesseract.image_to_string(map_img, config=config.TESSERACT_CONFIG).strip().upper()

        if raw_text in MAP_CORRECTIONS: 
            return MAP_CORRECTIONS[raw_text], raw_text
        for map_name in OVERWATCH_MAPS:
            if map_name.upper() == raw_text: 
                return map_name, raw_text
            if map_name.upper() in raw_text or raw_text in map_name.upper(): 
                return map_name, raw_text
        return None, raw_text
    except Exception as e:
        return None, f"Error during map extraction: {e}"

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

    print(f"\nExtracted Datetime: {game_datetime} {'(VALID)' if game_datetime else '(INVALID)'}")
    print(f"Extracted Length  : {game_length_sec} seconds {'(VALID)' if game_length_sec is not None else '(INVALID)'}")
    if raw_len_text1 is not None:
        print(f"Raw Length (Attempt 1 - Full Text): '{raw_len_text1}'")
    if raw_len_text2 is not None:
        print(f"Raw Length (Attempt 2 - Region OCR): '{raw_len_text2}'")
    print(f"Extracted Result  : {game_result} {'(VALID)' if game_result else '(INVALID)'}")

    print("\n--- 2. Map Name Extraction ---")
    game_map, raw_map_text = extract_map_name_debug(image)
    print(f"Raw Map OCR Text  : '{raw_map_text}'")
    print(f"Extracted Map     : {game_map} {'(VALID)' if game_map else '(INVALID)'}")

    print("\n--- 3. Hero Data Extraction ---")
    hero_data = extract_hero_data(image)

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