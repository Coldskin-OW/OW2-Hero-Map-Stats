# Overwatch2HeroMapStats

A tool for extracting and analyzing Overwatch 2 hero/map statistics from screenshots.

## Setup

This tool relies on Tesseract-OCR for reading text from screenshots.

1.  **Download and Install Tesseract-OCR**:
    *   Go to the Tesseract at UB Mannheim page and download the installer for your system.
    *   Run the installer. **Note the installation path**, as you will need it later (e.g., `C:\Program Files\Tesseract-OCR`).

2.  **Download the Application**:
    *   Go to the **Releases page** for this project.
    *   Download the latest `OW Hero Map Stats 1.exe` file from the "Assets" section of the most recent release.

3.  **Configure the Application**:
    *   Run the downloaded `.exe` file.
    *   Go to `File -> Settings`.
    *   **Database**: Click "New" to set up a new database file for your stats.
    *   **Tesseract Path**: The application will attempt to find Tesseract automatically if you installed it to the default path (`C:\Program Files\Tesseract-OCR`). If it's not found, set this to the full path of your `tesseract.exe` file.
    *   **Source Folder**: Set this to the folder where Overwatch 2 saves your screenshots (typically `Documents\Overwatch\Screenshots`).
    *   Click `Save Settings`.

## Usage

- Make sure Screenshot Quality is set to "1x Resolution" (Options -> Video -> Graphics Quality -> Screenshot Quality: 1x Resolution).
- Go to Career Profile -> History -> Game Reports.
- Press the match you want to add to the database, view the game report, and take a screenshot.
- Go back and screenshot each match's game report you want to add to the database.

In the exe:
- Press "Read Screenshots" and wait until it is done processing each screenshot.
- After selecting the Analysis Type, press "Run Analysis" to view your analyzed data.

## Note

The tool only works with game reports from the competitive mode (5v5 Role Queue and 6v6 Open Queue).