# ReadScreenshot.py

import os
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Any, Callable
from PIL import Image
import pytesseract
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

def save_match(date: str, map_name: str, result: str, length_sec: int, hero_data: List[Dict[str, Any]]) -> bool:
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

                # Batch insert heroes for better performance
                hero_values = [(match_id, hero['hero'], hero['percentage']) for hero in hero_data]
                c.executemany('''INSERT OR IGNORE INTO match_heroes
                                 (match_id, hero_name, play_percentage)
                                 VALUES (?,?,?)''',
                              hero_values)

                conn.commit()
                return True
            return False
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return False

def process_single_file(file_path: Path, extracted_folder: Path) -> tuple[bool, str]:
    """Process a single screenshot file with proper error handling and resource management"""
    try:
        with Image.open(file_path) as image:
            image.load()  # 🔧 Force full load into memory (prevents file lock issues)
            # Extract all required data
            text = pytesseract.image_to_string(image)
            
            game_length_sec, _, _ = extract_game_length(image, text)
            game_result = determine_result(text)
            game_datetime = extract_datetime(text, config.DATE_INPUT_FORMAT, config.DATE_OUTPUT_FORMAT)
            game_map = extract_map_name(image, OVERWATCH_MAPS, MAP_CORRECTIONS, config.TESSERACT_CONFIG)
            hero_data = extract_hero_data(image, file_path.name)

            # Validate all required fields
            if (game_length_sec is None or 
                game_result is None or 
                game_datetime is None or 
                game_map is None or 
                hero_data is None):
                logging.warning(f"Could not read all data from: {file_path.name}")
                return False, file_path.name

            # Save to database
            if save_match(
                date=game_datetime,  # type: ignore
                map_name=game_map,  # type: ignore
                result=game_result,  # type: ignore
                length_sec=game_length_sec,  # type: ignore
                hero_data=hero_data  # type: ignore
            ):
                dest_path = extracted_folder / file_path.name
                file_path.rename(dest_path)
                logging.info(f"Successfully processed: {file_path.name}")
                return True, file_path.name
            else:
                logging.info(f"Skipped duplicate: {file_path.name}")
                return False, file_path.name

    except Exception as e:
        logging.error(f"Error processing {file_path.name}: {str(e)}")
        return False, file_path.name

def process_screenshots(progress_callback: Optional[Callable[[int, int], None]] = None) -> Dict[str, int]:
    """Main processing loop with parallel execution"""
    # Validate Tesseract installation
    tesseract_valid, error_msg = validate_tesseract_installation(config.TESSERACT_CMD)
    if not tesseract_valid:
        logging.error(error_msg)
        return {
            'total': 0,
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'error': 0  # Adding this to maintain consistency in return type
        }

    init_database()
    source_folder = Path(config.SOURCE_FOLDER)
    extracted_folder = source_folder / 'extracted'
    extracted_folder.mkdir(exist_ok=True)

    # Get list of files to process
    file_list = [f for f in source_folder.iterdir() if f.suffix.lower() in valid_extensions]
    total_files = len(file_list)

    if progress_callback:
        progress_callback(0, total_files)

    # Thread-safe counters
    processed_files = 0
    error_files = 0

    # Determine optimal number of workers (leave some CPU headroom)
    max_workers = min(4, (os.cpu_count() or 1))
    if max_workers < 1:
        max_workers = 1

    logging.info(f"Starting parallel processing with {max_workers} workers...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks to the executor
        future_to_file = {
            executor.submit(process_single_file, file_path, extracted_folder): file_path.name
            for file_path in file_list
        }

        # Process completed tasks
        for i, future in enumerate(as_completed(future_to_file), 1):
            file_name = future_to_file[future]
            try:
                success, _ = future.result()
                if success:
                    processed_files += 1
                else:
                    error_files += 1
            except Exception as e:
                logging.error(f"Unexpected error processing {file_name}: {str(e)}")
                error_files += 1

            # Update progress after each completed task
            if progress_callback:
                progress_callback(i, total_files)

    skipped_files = total_files - processed_files - error_files

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