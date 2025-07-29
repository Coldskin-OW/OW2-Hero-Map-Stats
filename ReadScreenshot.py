# ReadScreenshot.py

import os
import sqlite3
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

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

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

    # Count total files first
    file_list = [f for f in source_folder.iterdir() if f.suffix.lower() in valid_extensions]
    total_files = len(file_list)

    if progress_callback:
        progress_callback(0, total_files)

    for i, file_path in enumerate(file_list):
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)

            game_length_sec, _, _ = extract_game_length(image, text)
            game_result = determine_result(text)
            game_datetime = extract_datetime(text, config.DATE_INPUT_FORMAT, config.DATE_OUTPUT_FORMAT)
            game_map = extract_map_name(image, OVERWATCH_MAPS, MAP_CORRECTIONS, config.TESSERACT_CONFIG)
            hero_data = extract_hero_data(image, file_path.name)

            # Only proceed if all required fields are not None and have valid values
            if (game_length_sec is None or 
                game_result is None or 
                game_datetime is None or 
                game_map is None or 
                hero_data is None):
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

    return {
        'total': total_files,
        'processed': processed_files,
        'skipped': skipped_files,
        'errors': error_files
    }


if __name__ == "__main__":
    process_screenshots()