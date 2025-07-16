# ReadScreenshot.py

import os
import sqlite3
import shutil
import logging
from pathlib import Path
from screenshot_utils import *
from map_categories import OVERWATCH_MAPS, MAP_CORRECTIONS
import config
from heros import OVERWATCH_HEROES, HERO_CORRECTIONS

# Configuration
pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
source_folder = config.SOURCE_FOLDER
extracted_folder = os.path.join(source_folder, 'extracted')
valid_extensions = config.VALID_EXTENSIONS

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

def is_valid_hero(text: str) -> bool:
    """Check if text matches a known hero name, returns False for empty string"""
    if not text.strip():
        return False
    return clean_hero_name(text, HERO_CORRECTIONS, OVERWATCH_HEROES) is not None

def recognize_hero(region, filename, region_name) -> str | None:
    """Try to recognize hero with primary, secondary, and tertiary settings"""
    # First attempt with primary settings
    processed_region = preprocess_hero_region(
        region,
        PRIMARY_HERO_SETTINGS['HERO_THRESHOLD'], 
        PRIMARY_HERO_SETTINGS['HERO_CONTRAST'], 
        PRIMARY_HERO_SETTINGS['HERO_RESIZE']
    )
    attempt1_text = pytesseract.image_to_string(processed_region, config=HERO_CONFIG).strip()
    hero_name = clean_hero_name(attempt1_text, HERO_CORRECTIONS, OVERWATCH_HEROES)
    if hero_name is not None:
        return hero_name

    # Second attempt with alternative settings if first failed
    processed_region = preprocess_hero_region(
        region,
        SECONDARY_HERO_SETTINGS['HERO_THRESHOLD'],
        SECONDARY_HERO_SETTINGS['HERO_CONTRAST'],
        SECONDARY_HERO_SETTINGS['HERO_RESIZE']
    )
    attempt2_text = pytesseract.image_to_string(processed_region, config=HERO_CONFIG).strip()
    hero_name = clean_hero_name(attempt2_text, HERO_CORRECTIONS, OVERWATCH_HEROES)
    if hero_name is not None:
        return hero_name
        
    # Third attempt with tertiary settings if first two failed
    processed_region = preprocess_hero_region(
        region,
        TERTIARY_HERO_SETTINGS['HERO_THRESHOLD'],
        TERTIARY_HERO_SETTINGS['HERO_CONTRAST'],
        TERTIARY_HERO_SETTINGS['HERO_RESIZE']
    )
    attempt3_text = pytesseract.image_to_string(processed_region, config=HERO_CONFIG).strip()
    hero_name = clean_hero_name(attempt3_text, HERO_CORRECTIONS, OVERWATCH_HEROES)
    if hero_name is not None:
        return hero_name

    logging.debug(f"Could not recognize hero in {region_name}: Attempt1='{attempt1_text}', Attempt2='{attempt2_text}', Attempt3='{attempt3_text}'")
    return None

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
        processed_perc = preprocess_percentage_region(perc_region, settings)
        perc_text = pytesseract.image_to_string(
            processed_perc,
            config='--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789%'
        ).strip()
        percentage = extract_percentage(perc_text)

        if percentage > 0:  # Only add if percentage was detected
            hero_data.append({
                'hero': hero_name,
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
            logging.info(f"Total percentage {total_percentage}% < {PERCENTAGE_MIN} for {num_heroes} heroes - retrying with secondary settings")

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

def process_screenshots(progress_callback=None) -> dict:
    """Main processing loop with Tesseract validation."""
    tesseract_valid, error_msg = validate_tesseract_installation(config.TESSERACT_CMD)
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
            game_datetime = extract_datetime(text, config.DATE_INPUT_FORMAT, config.DATE_OUTPUT_FORMAT)
            game_map = extract_map_name(image, OVERWATCH_MAPS, MAP_CORRECTIONS, config.TESSERACT_CONFIG)
            hero_data = extract_hero_data(image, file_path.name)

            # Only proceed if all required fields are not None
            if not (game_length_sec is not None and
                   game_result is not None and
                   game_datetime is not None and
                   game_map is not None and
                   hero_data is not None):
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