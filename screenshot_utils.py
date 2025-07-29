# screenshot_utils.py

from PIL import Image, ImageEnhance
import pytesseract
import re
from datetime import datetime
import logging
from difflib import get_close_matches
from pathlib import Path
from heros import OVERWATCH_HEROES, HERO_CORRECTIONS

# --- Constants ---
PERCENTAGE_MIN = 98
PERCENTAGE_MAX = 102

# Reference resolution (1920x1080) and original MAP_REGION coordinates
REFERENCE_WIDTH = 1920
REFERENCE_HEIGHT = 1080
REFERENCE_MAP_REGION = (1296, 177, 1624, 210)
REFERENCE_GAME_LENGTH_REGION = (1328, 745, 1508, 765)

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

# Hero regions
HERO_REGIONS = {
    '1_Hero': (266, 261, 462, 302),
    '1_Percentage': (266, 309, 334, 335),
    '2_Hero': (266, 503, 462, 544),
    '2_Percentage': (266, 550, 334, 576),
    '3_Hero': (266, 743, 462, 784),
    '3_Percentage': (266, 791, 334, 817)
}

# Primary percentage settings
PRIMARY_PERCENTAGE_SETTINGS = {
    'THRESHOLD': 255,
    'CONTRAST': 3,
    'RESIZE': 3
}

# Secondary percentage settings for retry
SECONDARY_PERCENTAGE_SETTINGS = {
    'THRESHOLD': 220,
    'CONTRAST': 4,
    'RESIZE': 2
}

# Primary hero name region settings
PRIMARY_HERO_SETTINGS = {
    'HERO_THRESHOLD': 100,
    'HERO_CONTRAST': 2.3,
    'HERO_RESIZE': 1
}

# Secondary settings for retry
SECONDARY_HERO_SETTINGS = {
    'HERO_THRESHOLD': 255,
    'HERO_CONTRAST': 3,
    'HERO_RESIZE': 2
}

# Tertiary settings for third attempt
TERTIARY_HERO_SETTINGS = {
    'HERO_THRESHOLD': 200,
    'HERO_CONTRAST': 2,
    'HERO_RESIZE': 1
}

def preprocess_hero_region(image_region, threshold, contrast, resize):
    """Special preprocessing for hero name regions with customizable settings"""
    img = image_region.convert('L')
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(contrast)
    img = img.point(lambda x: 0 if x < threshold else 255)

    if resize > 1:
        img = img.resize((img.width * resize, img.height * resize), Image.Resampling.LANCZOS)

    return img

def preprocess_percentage_region(image_region, settings):
    """Preprocessing for percentage regions with customizable settings"""
    img = image_region.convert('L')
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(settings['CONTRAST'])
    img = img.point(lambda x: 0 if x < settings['THRESHOLD'] else 255)

    if settings['RESIZE'] > 1:
        img = img.resize((img.width * settings['RESIZE'], img.height * settings['RESIZE']), Image.Resampling.LANCZOS)

    return img

def clean_hero_name(text: str, hero_corrections: dict, overwatch_heroes: dict) -> str | None:
    """Clean and standardize hero names with priority to corrections"""
    if not text.strip():
        return None  # Return None for empty text

    upper_text = text.strip().upper()
    upper_text = re.sub(r'[^A-Z\s:.\-ÉÜÖÄÑ]', '', upper_text)

    # 1. Check corrections first - exact match
    if upper_text in hero_corrections:
        return hero_corrections[upper_text]

    # 2. Check against known hero names - exact match
    for role, heroes in overwatch_heroes.items():
        for hero in heroes:
            if upper_text == hero.upper():
                return hero  # Return the properly capitalized version

    # 3. If still not found, try close matches with higher threshold
    matches = get_close_matches(upper_text,
                              [h.upper() for h in sum(overwatch_heroes.values(), [])],
                              n=1, cutoff=0.8)
    if matches:
        for hero in sum(overwatch_heroes.values(), []):
            if hero.upper() == matches[0]:
                return hero

    logging.debug(f"No match found for hero name: {upper_text}")
    return None  # Return None if no match found

def extract_percentage(text):
    """Percentage extraction with OCR error corrections without capping at 100"""
    corrections = {
        '7j00': '100', 'zj00': '100', ']00': '100',
        '70o': '100', '7o0': '100', 'T00': '100',
        'lj00': '100', 'i00': '100', '?00': '100'
    }

    for wrong, right in corrections.items():
        text = text.replace(wrong, right)

    match = re.search(r'(\d{1,3})%?', text)
    return int(match.group(1)) if match else 0

def calculate_scaled_region(image_width, image_height, original_region):
    """Calculate the scaled region based on the current image resolution"""
    width_scale = image_width / REFERENCE_WIDTH
    height_scale = image_height / REFERENCE_HEIGHT

    left = int(original_region[0] * width_scale)
    top = int(original_region[1] * height_scale)
    right = int(original_region[2] * width_scale)
    bottom = int(original_region[3] * height_scale)

    return (left, top, right, bottom)

def extract_game_length(image, text):
    """
    Extract game length in seconds from OCR text, with a fallback to a specific image region.
    Returns a tuple: (length_in_seconds, raw_from_full_text, raw_from_region_ocr).
    The raw text values will be None if an attempt was not made or failed to find a pattern.
    """
    # Attempt 1: Find "GAME LENGTH: M:SS" in the full text
    raw_match_1 = None
    length_match = re.search(r"GAME LENGTH:\s*(\d+:\d+)", text)
    if length_match:
        raw_match_1 = length_match.group(1)
        try:
            mins, secs = map(int, raw_match_1.split(':'))
            return (mins * 60 + secs, raw_match_1, None)
        except (ValueError, AttributeError):
            pass  # Fall through to attempt 2

    # Attempt 2: OCR a specific region for "M:SS"
    raw_length_text_2 = None
    try:
        width, height = image.size
        game_length_region = calculate_scaled_region(width, height, REFERENCE_GAME_LENGTH_REGION)

        length_img = image.crop(game_length_region).convert('L')
        length_img = length_img.point(lambda x: 0 if x < 200 else 255)  # Simple threshold for white text

        tesseract_config = '--psm 7 -c tessedit_char_whitelist=0123456789:'
        raw_length_text_2 = pytesseract.image_to_string(length_img, config=tesseract_config).strip()

        length_match_region = re.search(r"(\d{1,2}):(\d{2})", raw_length_text_2)
        if length_match_region:
            mins, secs = map(int, length_match_region.groups())
            return (mins * 60 + secs, raw_match_1, raw_length_text_2)
    except Exception as e:
        logging.warning(f"Could not extract game length from specific region: {e}")
    return (None, raw_match_1, raw_length_text_2)

def determine_result(text):
    """Determine match result from OCR text"""
    result_match = re.search(r"(VICTORY|DEFEAT|DRAW)", text, re.IGNORECASE)
    if result_match:
        return result_match.group(1).upper()

    score_match = re.search(r"FINAL SCORE:\s*(\d+)\s*VS\s*(\d+)", text, re.IGNORECASE)
    if score_match:
        your_score = int(score_match.group(1))
        enemy_score = int(score_match.group(2))
        return "VICTORY" if your_score > enemy_score else "DEFEAT" if your_score < enemy_score else "DRAW"
    return None

def extract_datetime(text, date_input_format, date_output_format):
    """Extract and format match datetime"""
    date_match = re.search(r"DATE:\s*(\d{2}/\d{2}/\d{2})\s*-\s*(\d{2}:\d{2})", text)
    if date_match:
        try:
            naive_dt = datetime.strptime(f"{date_match.group(1)} {date_match.group(2)}",
                                     date_input_format)
            return naive_dt.strftime(date_output_format)
        except ValueError:
            return None
    return None

def validate_tesseract_installation(tesseract_cmd):
    """Check if Tesseract is installed and accessible."""
    try:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        pytesseract.get_tesseract_version()
        return True, None
    except Exception as e:
        error_msg = (
            "ERROR: Tesseract-OCR is not installed or configured correctly.\n"
            f"Details: {str(e)}\n\n"
            "How to fix:\n"
            "1. Download Tesseract-OCR from: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "2. Install it on your system\n"
            "3. Set the correct path to tesseract.exe in the application settings\n"
            f"Current configured path: {tesseract_cmd}\n\n"
            "Note: The path can be changed in the application settings menu"
        )
        return False, error_msg

def recognize_hero(region, filename=None, region_name=None, debug=False):
    """Unified hero recognition with optional debug output"""
    attempts = [
        ("Primary", PRIMARY_HERO_SETTINGS),
        ("Secondary", SECONDARY_HERO_SETTINGS),
        ("Tertiary", TERTIARY_HERO_SETTINGS)
    ]
    
    results = []
    for name, settings in attempts:
        processed = preprocess_hero_region(
            region,
            settings['HERO_THRESHOLD'],
            settings['HERO_CONTRAST'],
            settings['HERO_RESIZE']
        )
        text = pytesseract.image_to_string(processed, config=HERO_CONFIG).strip()
        hero = clean_hero_name(text, HERO_CORRECTIONS, OVERWATCH_HEROES)
        
        if debug:
            print(f"    - Attempt {name}: Raw='{text}', Cleaned='{hero}'")
        
        if hero:
            return hero
        results.append((name, text, hero))
    
    if debug and filename and region_name:
        debug_info = ", ".join(f"{n}='{t}'" for n, t, _ in results)
        print(f"Could not recognize hero in {region_name}: {debug_info}")
    return None

def extract_hero_data(image, filename=None, debug=False):
    """Unified hero data extraction with optional debug output"""
    regions = sorted(HERO_REGIONS.items())
    
    def attempt_extraction(settings_name, settings):
        if debug:
            print(f"\n  - Attempting hero data extraction with settings: '{settings_name}'")
        
        hero_data = []
        total_percentage = 0
        
        for i in range(0, len(regions), 2):
            hero_key, hero_coords = regions[i]
            perc_key, perc_coords = regions[i+1]

            hero_region = image.crop(calculate_scaled_region(image.width, image.height, hero_coords))
            hero_name = recognize_hero(hero_region, filename, hero_key, debug)

            if hero_name is None:
                if debug:
                    print(f"    - Hero: '{hero_key}' -> SKIPPED (No valid hero name recognized)")
                continue

            perc_region = image.crop(calculate_scaled_region(image.width, image.height, perc_coords))
            processed_perc = preprocess_percentage_region(perc_region, settings)
            perc_text = pytesseract.image_to_string(
                processed_perc, 
                config='--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789%'
            ).strip()
            percentage = extract_percentage(perc_text)
            
            if debug:
                print(f"    - Hero: '{hero_name}', Percentage Raw Text: '{perc_text}', Extracted: {percentage}%")

            if percentage > 0:
                hero_data.append({'hero': hero_name, 'percentage': percentage})
                total_percentage += percentage
        
        num_heroes = len(hero_data)
        if debug:
            print(f"  - Result for '{settings_name}': {num_heroes} heroes, {total_percentage}% total")
        
        return hero_data, total_percentage, num_heroes

    # Primary attempt
    primary_data, primary_total, primary_heroes = attempt_extraction("Primary", PRIMARY_PERCENTAGE_SETTINGS)
    
    # Check if retry needed
    needs_retry = False
    if primary_heroes > 0:
        if primary_total > PERCENTAGE_MAX or (primary_heroes <= 2 and primary_total < PERCENTAGE_MIN):
            needs_retry = True
            if debug:
                print(f"\n  - Primary result ({primary_total}%) is outside acceptable range. Retrying with secondary settings.")

    # Secondary attempt if needed
    if needs_retry:
        secondary_data, secondary_total, secondary_heroes = attempt_extraction("Secondary", SECONDARY_PERCENTAGE_SETTINGS)
        
        # Choose better result
        if secondary_heroes > primary_heroes:
            final_data, final_total = secondary_data, secondary_total
            if debug:
                print(f"\n  - Using secondary results (found more heroes: {secondary_heroes} vs {primary_heroes}).")
        elif secondary_heroes == primary_heroes and abs(secondary_total - 100) < abs(primary_total - 100):
            final_data, final_total = secondary_data, secondary_total
            if debug:
                print(f"\n  - Using secondary results (closer to 100%: {secondary_total}% vs {primary_total}%).")
        else:
            final_data, final_total = primary_data, primary_total
            if debug:
                print(f"\n  - Sticking with primary results.")
    else:
        final_data, final_total = primary_data, primary_total
        if debug and primary_heroes == 0:
            print("\n[!] No heroes found with primary settings. No retry will be attempted.")

    # Final validation
    if final_data:
        num_heroes = len(final_data)
        if final_total > PERCENTAGE_MAX or (num_heroes <= 2 and final_total < PERCENTAGE_MIN):
            if debug:
                print(f"[!] Final hero data is invalid (Total: {final_total}%)")
            return None
        return final_data
    
    return None

def extract_map_name(image, overwatch_maps, map_corrections, tesseract_config, return_raw=False):
    """Enhanced map extraction with optional raw text return"""
    try:
        width, height = image.size
        map_region = calculate_scaled_region(width, height, REFERENCE_MAP_REGION)
        map_img = image.crop(map_region).convert('L')
        map_img = map_img.point(lambda x: 0 if x < 200 else 255)
        text = pytesseract.image_to_string(map_img, config=tesseract_config).strip().upper()

        if return_raw:
            # Always return a tuple when return_raw is True
            found_map = None
            for map_name in overwatch_maps:
                if map_name.upper() == text:
                    found_map = map_name
                    break

            if not found_map and text in map_corrections:
                found_map = map_corrections[text]

            if not found_map:
                for map_name in overwatch_maps:
                    if map_name.upper() in text or text in map_name.upper():
                        found_map = map_name
                        break

            return (found_map, text)  # Always return a tuple

        # Normal processing when return_raw is False
        for map_name in overwatch_maps:
            if map_name.upper() == text:
                return map_name

        if text in map_corrections:
            return map_corrections[text]

        for map_name in overwatch_maps:
            if map_name.upper() in text or text in map_name.upper():
                return map_name

        return None

    except Exception:
        if return_raw:
            return (None, "Error during extraction")  # Return tuple for error case
        return None