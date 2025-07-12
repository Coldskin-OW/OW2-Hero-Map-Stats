# ReadScreenshot.py

from PIL import Image, ImageEnhance
import pytesseract
import os
import re
from datetime import datetime
import sqlite3
import shutil
from map_categories import OVERWATCH_MAPS, MAP_CORRECTIONS
import config
from heros import OVERWATCH_HEROES, HERO_CORRECTIONS
from difflib import get_close_matches
import logging
from pathlib import Path

# --- Constants ---
PERCENTAGE_MIN = 98
PERCENTAGE_MAX = 102

# Configuration
pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
source_folder = config.SOURCE_FOLDER
extracted_folder = os.path.join(source_folder, 'extracted')
valid_extensions = config.VALID_EXTENSIONS

# Reference resolution (1920x1080) and original MAP_REGION coordinates
REFERENCE_WIDTH = 1920
REFERENCE_HEIGHT = 1080
REFERENCE_MAP_REGION = (1296, 177, 1624, 210)

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
HERO_THRESHOLD = 100
HERO_CONTRAST = 2.3
HERO_RESIZE = 1
HERO_POST_PROCESS = True

# Secondary settings for retry
SECONDARY_SETTINGS = {
    'HERO_THRESHOLD': 255,
    'HERO_CONTRAST': 3,
    'HERO_RESIZE': 2,
    'HERO_POST_PROCESS': True
}

# Create extracted folder if it doesn't exist
os.makedirs(extracted_folder, exist_ok=True)

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

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')


def preprocess_hero_region(image_region, filename, region_name, threshold, contrast, resize):
    """Special preprocessing for hero name regions with customizable settings"""
    img = image_region.convert('L')
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(contrast)
    img = img.point(lambda x: 0 if x < threshold else 255)

    if resize > 1:
        img = img.resize((img.width * resize, img.height * resize), Image.Resampling.LANCZOS)

    return img


def preprocess_percentage_region(image_region, filename, region_name, settings):
    """Preprocessing for percentage regions with customizable settings"""
    img = image_region.convert('L')
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(settings['CONTRAST'])
    img = img.point(lambda x: 0 if x < settings['THRESHOLD'] else 255)

    if settings['RESIZE'] > 1:
        img = img.resize((img.width * settings['RESIZE'], img.height * settings['RESIZE']), Image.Resampling.LANCZOS)

    return img


def is_valid_hero(text: str) -> bool:
    """Check if text matches a known hero name, returns False for empty string"""
    if not text.strip():
        return False

    upper_text = text.strip().upper()
    upper_text = re.sub(r'[^A-Z\s:.\-ÉÜÖÄÑ]', '', upper_text)

    # Check corrections first
    if upper_text in HERO_CORRECTIONS:
        return True

    # Check against hero list
    for role, heroes in OVERWATCH_HEROES.items():
        for hero in heroes:
            if hero.upper() in upper_text:
                return True

    # Check fuzzy matches
    matches = get_close_matches(upper_text,
                                [h.upper() for h in sum(OVERWATCH_HEROES.values(), [])],
                                n=1, cutoff=0.6)
    return len(matches) > 0


def recognize_hero(region, filename, region_name) -> str | None:
    """Try to recognize hero with primary and secondary settings"""
    # First attempt with primary settings
    processed_region = preprocess_hero_region(
        region, filename, f"{region_name}_attempt1",
        HERO_THRESHOLD, HERO_CONTRAST, HERO_RESIZE
    )
    attempt1_text = pytesseract.image_to_string(processed_region, config=HERO_CONFIG).strip()

    # Try to clean/correct the hero name
    hero_name = clean_hero_name(attempt1_text)
    if hero_name is not None:
        return hero_name

    # Second attempt with alternative settings if first failed
    processed_region = preprocess_hero_region(
        region, filename, f"{region_name}_attempt2",
        SECONDARY_SETTINGS['HERO_THRESHOLD'],
        SECONDARY_SETTINGS['HERO_CONTRAST'],
        SECONDARY_SETTINGS['HERO_RESIZE']
    )
    attempt2_text = pytesseract.image_to_string(processed_region, config=HERO_CONFIG).strip()

    # Try to clean/correct the hero name again
    hero_name = clean_hero_name(attempt2_text)
    if hero_name is not None:
        return hero_name

    # If we got here, no valid hero was recognized in either attempt
    logging.debug(f"Could not recognize hero in {region_name}: Attempt1='{attempt1_text}', Attempt2='{attempt2_text}'")
    return None


def clean_hero_name(text: str) -> str | None:
    """Clean and standardize hero names with priority to corrections"""
    if not text.strip():
        return None  # Return None for empty text

    upper_text = text.strip().upper()
    upper_text = re.sub(r'[^A-Z\s:.\-ÉÜÖÄÑ]', '', upper_text)

    # 1. Check corrections first - exact match
    if upper_text in HERO_CORRECTIONS:
        return HERO_CORRECTIONS[upper_text]

    # 2. Check against known hero names - exact match
    for role, heroes in OVERWATCH_HEROES.items():
        for hero in heroes:
            if upper_text == hero.upper():
                return hero  # Return the properly capitalized version

    # 3. If still not found, try close matches with higher threshold
    matches = get_close_matches(upper_text,
                              [h.upper() for h in sum(OVERWATCH_HEROES.values(), [])],
                              n=1, cutoff=0.8)
    if matches:
        for hero in sum(OVERWATCH_HEROES.values(), []):
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


def _extract_hero_data_attempt(image, filename, regions, settings):
    """Helper function to extract hero data with specific settings"""
    hero_data = []
    total_percentage = 0
    num_heroes = 0

    for i in range(0, len(regions), 2):
        hero_key, hero_coords = regions[i]
        perc_key, perc_coords = regions[i + 1]

        hero_region = image.crop(calculate_scaled_region(image.width, image.height, hero_coords))
        hero_name = recognize_hero(hero_region, filename, hero_key)

        # Skip if we couldn't recognize the hero
        if hero_name is None:
            continue

        perc_region = image.crop(calculate_scaled_region(image.width, image.height, perc_coords))
        processed_perc = preprocess_percentage_region(perc_region, filename, perc_key, settings)
        perc_text = pytesseract.image_to_string(
            processed_perc,
            config='--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789%'
        ).strip()
        percentage = extract_percentage(perc_text)

        if percentage > 0:  # Only add if percentage was detected
            hero_data.append({
                'hero': hero_name,  # This is now guaranteed to be a corrected name
                'percentage': percentage
            })
            total_percentage += percentage
            num_heroes += 1

    return hero_data, total_percentage, num_heroes


def extract_hero_data(image, filename):
    """Extract hero playtime percentages with validation and retry logic"""
    width, height = image.size
    regions = sorted(HERO_REGIONS.items())

    # First attempt with primary settings
    primary_result = _extract_hero_data_attempt(image, filename, regions, PRIMARY_PERCENTAGE_SETTINGS)

    if primary_result[0] is None:  # Invalid hero text detected
        logging.warning("Invalid hero text detected in primary attempt")
        return None

    hero_data, total_percentage, num_heroes = primary_result

    # Check if we need to retry (only if we have some valid heroes)
    needs_retry = False
    if num_heroes > 0:
        if total_percentage > PERCENTAGE_MAX:
            needs_retry = True
            logging.info(f"Total percentage {total_percentage}% > {PERCENTAGE_MAX} - retrying with secondary settings")
        elif num_heroes <= 2 and total_percentage < PERCENTAGE_MIN:
            needs_retry = True
            logging.info(
                f"Total percentage {total_percentage}% < {PERCENTAGE_MIN} for {num_heroes} heroes - retrying with secondary settings")

    # Second attempt if needed
    if needs_retry and num_heroes > 0:
        secondary_result = _extract_hero_data_attempt(image, filename, regions, SECONDARY_PERCENTAGE_SETTINGS)

        if secondary_result[0] is None:  # Invalid hero text detected
            logging.warning("Invalid hero text detected in secondary attempt")
            return None

        secondary_data, secondary_total, secondary_num_heroes = secondary_result

        # Use whichever result is better
        if secondary_num_heroes > num_heroes:
            hero_data = secondary_data
            total_percentage = secondary_total
            num_heroes = secondary_num_heroes
            logging.info(f"Using secondary settings which found {num_heroes} heroes: {total_percentage}%")
        elif secondary_num_heroes == num_heroes:
            # If same number of heroes, choose closest to 100%
            if abs(secondary_total - 100) < abs(total_percentage - 100):
                hero_data = secondary_data
                total_percentage = secondary_total
                logging.info(f"Using secondary settings results (closer to 100): {total_percentage}%")

    # Final validation (only if we have at least one valid hero)
    if num_heroes > 0:
        if total_percentage > PERCENTAGE_MAX or (num_heroes <= 2 and total_percentage < PERCENTAGE_MIN):
            logging.warning(f"Invalid percentages (Total: {total_percentage}%, Heroes: {num_heroes})")
            return None
        return hero_data

    # If we got here, no heroes were detected at all
    logging.warning("No valid heroes detected in screenshot")
    return None


def calculate_scaled_region(image_width, image_height, original_region):
    """Calculate the scaled region based on the current image resolution"""
    width_scale = image_width / REFERENCE_WIDTH
    height_scale = image_height / REFERENCE_HEIGHT

    left = int(original_region[0] * width_scale)
    top = int(original_region[1] * height_scale)
    right = int(original_region[2] * width_scale)
    bottom = int(original_region[3] * height_scale)

    return (left, top, right, bottom)


def validate_tesseract_installation():
    """Check if Tesseract is installed and accessible."""
    try:
        pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
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
            f"Current configured path: {config.TESSERACT_CMD}\n\n"
            "Note: The path can be changed in the application settings menu"
        )
        return False, error_msg


def init_database():
    """Initialize the SQLite database with proper schema"""
    conn = sqlite3.connect(config.DATABASE_NAME)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS matches
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT,
                  map TEXT,
                  result TEXT CHECK(result IN ('VICTORY', 'DEFEAT', 'DRAW')),
                  length_sec INTEGER,
                  UNIQUE(date, map, result, length_sec))''')

    c.execute('''CREATE TABLE IF NOT EXISTS match_heroes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  match_id INTEGER,
                  hero_name TEXT,
                  play_percentage INTEGER,
                  FOREIGN KEY(match_id) REFERENCES matches(id),
                  UNIQUE(match_id, hero_name))''')

    conn.commit()
    conn.close()


def extract_map_name(image):
    """Extract map name from predefined screen region"""
    try:
        width, height = image.size
        map_region = calculate_scaled_region(width, height, REFERENCE_MAP_REGION)

        map_img = image.crop(map_region).convert('L')
        map_img = map_img.point(lambda x: 0 if x < 200 else 255)

        text = pytesseract.image_to_string(map_img, config=config.TESSERACT_CONFIG).strip().upper()

        for map_name in OVERWATCH_MAPS:
            if map_name.upper() == text:
                return map_name

        if text in MAP_CORRECTIONS:
            return MAP_CORRECTIONS[text]

        for map_name in OVERWATCH_MAPS:
            if map_name.upper() in text or text in map_name.upper():
                return map_name

        return None
    except Exception:
        return None


def extract_game_length(text):
    """Extract game length in seconds from OCR text"""
    length_match = re.search(r"GAME LENGTH:\s*(\d+:\d+)", text)
    if length_match:
        try:
            mins, secs = map(int, length_match.group(1).split(':'))
            return mins * 60 + secs
        except (ValueError, AttributeError):
            return None
    return None


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


def extract_datetime(text):
    """Extract and format match datetime"""
    date_match = re.search(r"DATE:\s*(\d{2}/\d{2}/\d{2})\s*-\s*(\d{2}:\d{2})", text)
    if date_match:
        try:
            # Parse the datetime without timezone first
            naive_dt = datetime.strptime(f"{date_match.group(1)} {date_match.group(2)}",
                                         config.DATE_INPUT_FORMAT)

            # Return in the expected format without timezone conversion
            return naive_dt.strftime(config.DATE_OUTPUT_FORMAT)

        except ValueError:
            return None
    return None


def save_match(date: str, map_name: str, result: str, length_sec: int, hero_data: list[dict]) -> bool:
    """Save match data to database with percentage validation"""
    if not hero_data:
        logging.warning("No hero data to save.")
        return False

    total_percentage = sum(hero['percentage'] for hero in hero_data)
    if total_percentage > PERCENTAGE_MAX:
        logging.warning(f"Skipping match with invalid percentage total ({total_percentage})")
        return False

    try:
        # Convert the date string to datetime and then to UTC
        naive_dt = datetime.strptime(date, config.DATE_OUTPUT_FORMAT)
        local_dt = config.local_to_utc(naive_dt)
        utc_date_str = local_dt.strftime(config.DATE_OUTPUT_FORMAT)
    except ValueError:
        logging.error(f"Invalid date format: {date}")
        return False

    try:
        with sqlite3.connect(config.DATABASE_NAME) as conn:
            c = conn.cursor()
            c.execute('''INSERT OR IGNORE INTO matches 
                         (date, map, result, length_sec)
                         VALUES (?,?,?,?)''',
                      (utc_date_str, map_name, result, length_sec))

            if c.rowcount > 0:
                match_id = c.lastrowid

                for hero in hero_data:
                    c.execute('''INSERT OR IGNORE INTO match_heroes
                                 (match_id, hero_name, play_percentage)
                                 VALUES (?,?,?)''',
                              (match_id, hero['hero'], hero['percentage']))

                conn.commit()
                return True
            return False
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return False


# In ReadScreenshot.py, modify the process_screenshots function:
def process_screenshots(progress_callback=None) -> dict:
    """Main processing loop with Tesseract validation."""
    tesseract_valid, error_msg = validate_tesseract_installation()
    if not tesseract_valid:
        logging.error(error_msg)
        return {
            'error': error_msg,
            'total': 0,
            'processed': 0,
            'skipped': 0,
            'errors': 0
        }

    init_database()
    source_folder = Path(config.SOURCE_FOLDER)
    extracted_folder = source_folder / 'extracted'

    extracted_folder.mkdir(exist_ok=True)

    total_files = 0
    processed_files = 0
    skipped_files = 0
    error_files = 0
    invalid_percentage_files = 0

    # Count total files first
    file_list = [f for f in source_folder.iterdir() if f.suffix.lower() in valid_extensions]
    total_files = len(file_list)

    if progress_callback:
        progress_callback(0, total_files)

    for i, file_path in enumerate(file_list):
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)

            game_length_sec = extract_game_length(text)
            game_result = determine_result(text)
            game_datetime = extract_datetime(text)
            game_map = extract_map_name(image)
            hero_data = extract_hero_data(image, file_path.name)

            # Only proceed if all required fields are not None
            if not (
                game_length_sec is not None and
                game_result is not None and
                game_datetime is not None and
                game_map is not None and
                hero_data is not None
            ):
                logging.warning(f"Could not read screenshot: {file_path.name}")
                error_files += 1
                if progress_callback:
                    progress_callback(i + 1, total_files)
                continue

            if save_match(game_datetime, game_map, game_result, game_length_sec, hero_data):
                dest_path = extracted_folder / file_path.name
                file_path.rename(dest_path)
                logging.info(f"Successfully processed: {file_path.name}")
                processed_files += 1
            else:
                logging.info(f"Skipped duplicate: {file_path.name}")
                skipped_files += 1

            # Update progress after each file
            if progress_callback:
                progress_callback(i + 1, total_files)

        except Exception as e:
            logging.error(f"Could not read screenshot: {file_path.name} ({e})")
            error_files += 1
            if progress_callback:
                progress_callback(i + 1, total_files)

    logging.info(f"\nProcessing complete. Results:")
    logging.info(f"- Total files: {total_files}")
    logging.info(f"- Successfully processed: {processed_files}")
    logging.info(f"- Skipped duplicates: {skipped_files}")
    logging.info(f"- Failed to read: {error_files}")
    logging.info(f"- Invalid data: {invalid_percentage_files}")

    return {
        'total': total_files,
        'processed': processed_files,
        'skipped': skipped_files,
        'errors': error_files,
        'invalid_percentages': invalid_percentage_files
    }


if __name__ == "__main__":
    process_screenshots()