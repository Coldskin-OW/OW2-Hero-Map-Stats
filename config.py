from pathlib import Path
from zoneinfo import ZoneInfo
import tzlocal
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Timezone configuration - automatically detect system timezone
try:
    LOCAL_TIMEZONE = ZoneInfo(str(tzlocal.get_localzone()))
except Exception as e:
    print(f"Warning: Could not determine system timezone ({str(e)}), falling back to UTC")
    LOCAL_TIMEZONE = ZoneInfo('UTC')

UTC_TIMEZONE = ZoneInfo('UTC')

# Helper functions for timezone conversion
def local_to_utc(local_dt) -> 'datetime':
    """Convert naive local datetime to UTC"""
    if local_dt.tzinfo is None:
        return local_dt.replace(tzinfo=LOCAL_TIMEZONE).astimezone(UTC_TIMEZONE)
    return local_dt.astimezone(UTC_TIMEZONE)

def utc_to_local(utc_dt) -> 'datetime':
    """Convert UTC datetime to local time"""
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=UTC_TIMEZONE)
    return utc_dt.astimezone(LOCAL_TIMEZONE)


# Default Tesseract OCR configuration (can be overridden by user settings)
TESSERACT_CMD = os.getenv("TESSERACT_CMD", r'C:\Program Files\Tesseract-OCR\tesseract.exe')

# File system configuration
DOCUMENTS = Path.home() / 'Documents'
SOURCE_FOLDER = str(DOCUMENTS / 'Overwatch' / 'ScreenShots' / 'Overwatch')
VALID_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')

# Image processing configuration
TESSERACT_CONFIG = '--psm 7 --oem 3'

# Database configuration
DATABASE_NAME = os.getenv("DATABASE_NAME", '')

# Date format configuration
DATE_INPUT_FORMAT = '%m/%d/%y %H:%M'
DATE_OUTPUT_FORMAT = '%Y-%m-%d %H:%M'