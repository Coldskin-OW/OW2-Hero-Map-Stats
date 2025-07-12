# Overwatch2HeroMapStats

An unoffical tool for extracting and analyzing Overwatch 2 hero/map statistics from screenshots.

## Setup

This tool relies on Tesseract-OCR for reading text from screenshots.

1.  **Download and Install Tesseract-OCR**:
    *   Go to the [Tesseract at UB Mannheim page](https://github.com/UB-Mannheim/tesseract/wiki) and download the installer for your system.
    *   Run the installer. **Note the installation path**, as you will need it later (e.g., `C:\Program Files\Tesseract-OCR`).

2.  **Download the Application**:
    *   Go to the [**Releases page**](https://github.com/Coldskin-OW/OW2-Hero-Map-Stats/releases)for this project.
    *   Download the latest `OW Hero Map Stats 1.exe` file from the "Assets" section of the most recent release.

3.  **Configure the Application**:
    *   Run the downloaded `.exe` file.
    *   Go to `File -> Settings`.
    *   **Database File**: Click "New" to create and save a new database file for your stats.
    *   **Tesseract Path**: The application will attempt to find Tesseract automatically if you installed it to the default path (`C:\Program Files\Tesseract-OCR`). If it's not found, set this to the full path of your `tesseract.exe` file.
    *   **Source Folder**: Set this to the folder where Overwatch 2 saves your screenshots (typically `Documents\Overwatch\Screenshots`).
    *   Click `Save Settings`.

## Usage

- Ensure your game resolution is set to at least **1920x1080** for best results. Higher resolutions are also supported.
- Make sure Screenshot Quality is set to "1x Resolution" (Options -> Video -> Graphics Quality -> Screenshot Quality: 1x Resolution).
- Go to `Career Profile -> History -> Game Reports`.
- For each match you want to add, view the game report and take a screenshot.

In the `OW Hero Map Stats` application:
- Click **"Read Screenshots"**. The application will process the new screenshots in your source folder.
- After processing is complete, select an **Analysis Type**.
- Click **"Run Analysis"** to view your stats.

## How It Works

This tool works by:
1.  Scanning a designated folder for new Overwatch 2 game report screenshots.
2.  Using **Tesseract-OCR** to perform Optical Character Recognition (OCR) on the images to read the hero, map, and result data.
3.  Storing the extracted data in a local SQLite database file.
4.  Analyzing the data from the database to provide you with win/loss statistics by hero and map.

## Note

The tool only works with game reports from the competitive mode (5v5 Role Queue and 6v6 Open Queue).