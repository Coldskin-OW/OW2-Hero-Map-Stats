# overwatch_stats_gui.py
import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from stats_functions import (
    print_win_percentages_by_season,
    print_all_matches_by_season,
    print_summary_stats_by_season,
    print_map_frequency_stats_by_season,
    print_game_mode_stats_by_season,
    print_hero_win_percentages_by_season,
    delete_match_by_date,
    print_hero_map_win_percentages,
    print_map_hero_win_percentages
)
from seasons import SEASON_DATES
from ReadScreenshot import process_screenshots
import config
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.colors import Normalize
import json
import os
from pathlib import Path
from heros import OVERWATCH_HEROES
from map_categories import OVERWATCH_MAPS
import logging


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')


def get_config_path():
    """Get path to user config file in standard location"""
    if os.name == 'nt':  # Windows
        appdata = os.getenv('APPDATA')
        if appdata is None:
            # Fallback to home directory if APPDATA is not set
            config_dir = Path.home() / 'AppData' / 'Roaming' / 'OverwatchStatsAnalyzer'
        else:
            config_dir = Path(appdata) / 'OverwatchStatsAnalyzer'
    else:  # Linux/Mac
        config_dir = Path.home() / '.config' / 'OverwatchStatsAnalyzer'

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / 'user_config.json'


def load_user_settings():
    """Load user settings from config file"""
    config_path = get_config_path()
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                settings = json.load(f)
                # Ensure all required settings are present
                if 'TESSERACT_CMD' not in settings:
                    settings['TESSERACT_CMD'] = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                return settings
        except (json.JSONDecodeError, IOError):
            return None
    return None


def save_user_settings(settings):
    """Save user settings to config file"""
    config_path = get_config_path()
    try:
        with open(config_path, 'w') as f:
            json.dump(settings, f, indent=4)
        return True
    except IOError:
        return False


class OverwatchStatsApp:
    """Main GUI application for Overwatch statistics analysis."""
    def __init__(self, root):
        self.root = root
        self.root.title("Overwatch 2 Hero Map Stats")
        self.root.geometry("1200x800")
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Load user settings if they exist
        user_settings = load_user_settings()  # Now calling the standalone function
        if user_settings:
            for key, value in user_settings.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        # Bind the window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Configure styles
        self.configure_styles()

        # Create main container
        self.create_main_frame()

        # Create menu
        self.create_menu()

        # Make the UI responsive
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Initialize chart frame (hidden by default)
        self.chart_frame = None
        self.current_figure = None
        plt.ioff()  # Turn off interactive mode to prevent figure conflicts

    def on_close(self):
        """Handle window closing event"""
        # Clean up any matplotlib figures
        if hasattr(self, 'current_figure') and self.current_figure:
            plt.close(self.current_figure)
        # Destroy the root window
        self.root.destroy()

    def configure_styles(self):
        """Configure custom styles for widgets"""
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0', font=('Helvetica', 10))
        self.style.configure('TButton', font=('Helvetica', 10), padding=5)
        self.style.configure('TCombobox', font=('Helvetica', 10))
        self.style.configure('TSpinbox', font=('Helvetica', 10))
        self.style.configure('Status.TLabel', background='#e0e0e0', relief=tk.SUNKEN)
        self.style.configure('Listbox', font=('Helvetica', 10))

        # Add style for close button
        self.style.configure('Close.TButton',
                             font=('Helvetica', 12, 'bold'),
                             foreground='red',
                             borderwidth=0,
                             padding=0,
                             width=2)
        self.style.map('Close.TButton',
                       foreground=[('active', 'red'), ('pressed', 'red')],
                       background=[('active', '#f0f0f0'), ('pressed', '#f0f0f0')])

    def create_main_frame(self):
        """Create the main application frame with all widgets"""
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky="nsew")  # fix: sticky as string
        self.main_frame.columnconfigure(1, weight=1)

        # Season selection
        ttk.Label(self.main_frame, text="Select Season(s):").grid(
            row=0, column=0, sticky="w", pady=5)  # fix: sticky as string

        # Time frame selection
        ttk.Label(self.main_frame, text="Time Frame:").grid(
            row=0, column=2, sticky="w", pady=5)  # fix: sticky as string

        self.time_frame_frame = ttk.Frame(self.main_frame)
        self.time_frame_frame.grid(row=0, column=3, sticky="we", pady=5)  # fix: sticky as string

        # Start date
        ttk.Label(self.time_frame_frame, text="From:").grid(row=0, column=0, padx=(0, 5))
        self.start_date_var = tk.StringVar()
        self.start_date_entry = ttk.Entry(self.time_frame_frame, textvariable=self.start_date_var, width=12)
        self.start_date_entry.grid(row=0, column=1, padx=(0, 10))
        self.start_date_entry.insert(0, "YYYY-MM-DD")

        # End date
        ttk.Label(self.time_frame_frame, text="To:").grid(row=0, column=2, padx=(0, 5))
        self.end_date_var = tk.StringVar()
        self.end_date_entry = ttk.Entry(self.time_frame_frame, textvariable=self.end_date_var, width=12)
        self.end_date_entry.grid(row=0, column=3)
        self.end_date_entry.insert(0, "YYYY-MM-DD")

        # Frame for season selection widgets
        season_select_frame = ttk.Frame(self.main_frame)
        season_select_frame.grid(row=0, column=1, sticky="we", pady=5)  # fix: sticky as string

        # Listbox for multiple season selection
        self.season_listbox = tk.Listbox(
            season_select_frame,
            selectmode=tk.MULTIPLE,
            height=5,
            exportselection=False,
            activestyle='none'
        )
        self.season_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(season_select_frame, orient=tk.VERTICAL, command=self.season_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.season_listbox.config(yscrollcommand=scrollbar.set)

        # Populate listbox with seasons
        self.season_listbox.insert(0, "All Seasons")
        for season in sorted(SEASON_DATES.keys()):
            self.season_listbox.insert(tk.END, season)

        # Select "All Seasons" by default
        self.season_listbox.selection_set(0)

        # Analysis type selection
        ttk.Label(self.main_frame, text="Analysis Type:").grid(
            row=1, column=0, sticky=tk.W, pady=5)

        self.analysis_var = tk.StringVar()
        self.analysis_combobox = ttk.Combobox(
            self.main_frame, textvariable=self.analysis_var,
            values=[
                "Win Percentages by Map",
                "Hero Win Percentages",
                "Hero Map Win Rates",
                "Map Hero Win Rates",
                "All Matches",
                "Summary Statistics",
                "Map Frequency Stats",
                "Game Mode Stats"
            ],
            state='readonly')
        self.analysis_combobox.current(0)
        self.analysis_combobox.grid(row=1, column=1, sticky="we", pady=5)  # fix: sticky as string
        self.analysis_combobox.bind('<<ComboboxSelected>>', self.on_analysis_type_changed)

        # Selection frame (for hero/map selection)
        self.selection_frame = ttk.Frame(self.main_frame)
        self.selection_frame.grid(row=2, column=0, columnspan=2, sticky="w", pady=5)  # fix: sticky as string

        self.selection_label = ttk.Label(self.selection_frame, text="Select:")
        self.selection_label.grid(row=0, column=0, sticky=tk.W)

        self.selection_var = tk.StringVar()
        self.selection_combobox = ttk.Combobox(
            self.selection_frame, textvariable=self.selection_var,
            state='readonly', width=25)
        self.selection_combobox.grid(row=0, column=1, padx=5)

        # Hide selection frame by default
        self.selection_frame.grid_remove()

        # Minimum matches filter
        self.min_matches_frame = ttk.Frame(self.main_frame)
        self.min_matches_frame.grid(row=3, column=0, columnspan=2, sticky="w", pady=5)  # fix: sticky as string

        ttk.Label(self.min_matches_frame, text="Minimum Matches:").grid(
            row=0, column=0, sticky=tk.W)

        self.min_matches_var = tk.IntVar(value=1)
        self.min_matches_spinbox = ttk.Spinbox(
            self.min_matches_frame, from_=1, to=100,
            textvariable=self.min_matches_var, width=5)
        self.min_matches_spinbox.grid(row=0, column=1, padx=5)

        # Results display
        self.results_frame = ttk.Frame(self.main_frame)
        self.results_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=10)  # fix: sticky as string
        self.results_frame.columnconfigure(0, weight=1)
        self.results_frame.rowconfigure(0, weight=1)

        self.results_text = tk.Text(
            self.results_frame, wrap=tk.WORD, height=25, width=100,
            font=('Consolas', 10), undo=True)
        self.results_text.grid(row=0, column=0, sticky="nsew")  # fix: sticky as string

        scrollbar = ttk.Scrollbar(
            self.results_frame, orient=tk.VERTICAL, command=self.results_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")  # fix: sticky as string
        self.results_text['yscrollcommand'] = scrollbar.set

        # Button frame
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.grid(row=5, column=0, columnspan=2, pady=10)

        self.run_button = ttk.Button(
            self.button_frame, text="Run Analysis", command=self.run_analysis)
        self.run_button.grid(row=0, column=0, padx=5)

        self.export_button = ttk.Button(
            self.button_frame, text="Export Results", command=self.export_results)
        self.export_button.grid(row=0, column=1, padx=5)

        self.chart_button = ttk.Button(
            self.button_frame, text="Show Chart", command=self.toggle_chart)
        self.chart_button.grid(row=0, column=2, padx=5)

        self.screenshot_button = ttk.Button(
            self.button_frame, text="Read Screenshots", command=self.run_process_screenshots)
        self.screenshot_button.grid(row=0, column=3, padx=5)

        self.delete_button = ttk.Button(
            self.button_frame, text="Delete Match", command=self.delete_match)
        self.delete_button.grid(row=0, column=4, padx=5)

        self.manual_button = ttk.Button(
            self.button_frame, text="Add Match Manually", command=self.add_match_manually)
        self.manual_button.grid(row=0, column=5, padx=5)

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(
            self.main_frame, textvariable=self.status_var,
            style='Status.TLabel', anchor=tk.W)
        self.status_bar.grid(row=6, column=0, columnspan=2, sticky="we")  # fix: sticky as string

    def on_analysis_type_changed(self, event):
        """Handle changes in analysis type to show/hide selection combobox"""
        analysis_type = self.analysis_var.get()

        if analysis_type in ["Hero Map Win Rates", "Map Hero Win Rates"]:
            self.selection_frame.grid()
            self.min_matches_frame.grid(row=3, column=0, columnspan=2, sticky="w", pady=5)  # fix: sticky as string

            if analysis_type == "Hero Map Win Rates":
                self.selection_label.config(text="Select Hero:")
                # Get all heroes from all roles
                all_heroes = []
                for role in OVERWATCH_HEROES.values():
                    all_heroes.extend(role)
                self.selection_combobox['values'] = sorted(all_heroes)
            else:
                self.selection_label.config(text="Select Map:")
                self.selection_combobox['values'] = sorted(OVERWATCH_MAPS)

            if self.selection_combobox['values']:
                self.selection_combobox.current(0)
        else:
            self.selection_frame.grid_remove()
            self.min_matches_frame.grid(row=2, column=0, columnspan=2, sticky="w", pady=5)  # fix: sticky as string

    def create_menu(self):
        """Create the menu bar"""
        menubar = tk.Menu(self.root)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Export Results", command=self.export_results)
        file_menu.add_separator()
        file_menu.add_command(label="Settings", command=self.show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        file_menu.add_command(label="Delete Match", command=self.delete_match)
        file_menu.add_command(label="Add Match Manually", command=self.add_match_manually)
        menubar.add_cascade(label="File", menu=file_menu)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Toggle Chart", command=self.toggle_chart)
        menubar.add_cascade(label="View", menu=view_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def show_settings(self):
        """Show settings dialog"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("550x400")
        settings_window.resizable(False, False)
        settings_window.transient(self.root)
        settings_window.grab_set()

        # Store current values in case we need to revert
        self.current_source_folder = config.SOURCE_FOLDER
        self.current_database = config.DATABASE_NAME
        self.current_tesseract = config.TESSERACT_CMD

        # Use grid layout with rows
        row = 0

        # Tesseract path setting
        ttk.Label(settings_window, text="Tesseract Path:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        self.tesseract_var = tk.StringVar(value=config.TESSERACT_CMD)
        ttk.Entry(settings_window, textvariable=self.tesseract_var, width=40).grid(row=row, column=1, padx=5, pady=5)
        ttk.Button(settings_window, text="Browse...", command=self.browse_tesseract).grid(row=row, column=2, padx=5,
                                                                                          pady=5)
        row += 1

        # Source folder setting
        ttk.Label(settings_window, text="Source Folder:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        self.source_folder_var = tk.StringVar(value=config.SOURCE_FOLDER)
        ttk.Entry(settings_window, textvariable=self.source_folder_var, width=40).grid(row=row, column=1, padx=5,
                                                                                       pady=5)
        ttk.Button(settings_window, text="Browse...", command=self.browse_source_folder).grid(row=row, column=2, padx=5,
                                                                                              pady=5)
        row += 1

        # Database settings
        ttk.Label(settings_window, text="Database File:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        self.database_var = tk.StringVar(value=config.DATABASE_NAME)
        ttk.Entry(settings_window, textvariable=self.database_var, width=40).grid(row=row, column=1, padx=5, pady=5)

        # Database buttons frame
        db_button_frame = ttk.Frame(settings_window)
        db_button_frame.grid(row=row, column=2, padx=5, pady=5, sticky=tk.W)
        ttk.Button(db_button_frame, text="New...", command=self.create_new_database).grid(row=0, column=0, padx=2)
        ttk.Button(db_button_frame, text="Browse...", command=self.browse_existing_database).grid(row=0, column=1,
                                                                                                  padx=2)
        row += 1

        # Save and Cancel buttons
        button_frame = ttk.Frame(settings_window)
        button_frame.grid(row=row, column=1, columnspan=2, pady=20, sticky="we")  # fix: sticky as string
        ttk.Button(button_frame, text="Save Settings", command=lambda: self.save_settings(settings_window)).grid(row=0,
                                                                                                                 column=0,
                                                                                                                 padx=10)
        ttk.Button(button_frame, text="Cancel", command=settings_window.destroy).grid(row=0, column=1, padx=10)

    def verify_database_connection(self, db_path):
        """Verify if we can connect to the database"""
        try:
            conn = sqlite3.connect(db_path)
            conn.close()
            return True
        except sqlite3.Error:
            return False

    def verify_database_schema(self, db_path):
        """Verify if the database has the correct table structure"""
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()

            # Check if the matches table exists with the required columns
            c.execute("PRAGMA table_info(matches)")
            columns = c.fetchall()
            required_columns = {'date', 'map', 'result', 'length_sec'}
            existing_columns = {col[1] for col in columns}

            conn.close()

            # Check if all required columns are present
            return required_columns.issubset(existing_columns)
        except sqlite3.Error:
            return False

    def browse_source_folder(self):
        """Browse for source folder"""
        folder = filedialog.askdirectory(initialdir=config.SOURCE_FOLDER)
        if folder:
            self.source_folder_var.set(folder)

    def browse_existing_database(self):
        """Browse for an existing database file"""
        initial_dir = os.path.dirname(config.DATABASE_NAME) if config.DATABASE_NAME else os.getcwd()
        file_path = filedialog.askopenfilename(
            defaultextension=".db",
            filetypes=[("Database files", "*.db"), ("All files", "*.*")],
            title="Select Database File",
            initialdir=initial_dir
        )
        if file_path:
            # Verify the database has the correct schema
            if self.verify_database_schema(file_path):
                self.database_var.set(file_path)
            else:
                messagebox.showerror("Invalid Database", "The selected database doesn't have the required schema.")

    def browse_tesseract(self):
        """Browse for Tesseract executable"""
        initial_dir = os.path.dirname(config.TESSERACT_CMD) if config.TESSERACT_CMD else os.getcwd()
        file_path = filedialog.askopenfilename(
            title="Select Tesseract Executable",
            initialdir=initial_dir,
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if file_path:
            self.tesseract_var.set(file_path)

    def create_new_database(self):
        """Create a new database file"""
        initial_dir = os.path.dirname(config.DATABASE_NAME) if config.DATABASE_NAME else os.getcwd()
        file_path = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("Database files", "*.db"), ("All files", "*.*")],
            title="Create New Database",
            initialdir=initial_dir
        )
        if file_path:
            # Normalize the path
            file_path = os.path.normpath(file_path)
            # Initialize the new database
            try:
                conn = sqlite3.connect(file_path)
                c = conn.cursor()
                c.execute('''CREATE TABLE IF NOT EXISTS matches
                            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                             date TEXT,
                             map TEXT,
                             result TEXT CHECK(result IN ('VICTORY', 'DEFEAT', 'DRAW')),
                             length_sec INTEGER,
                             UNIQUE(date, map, result, length_sec))''')
                conn.commit()
                conn.close()
                # Update the entry field with the new path
                self.database_var.set(file_path)
                messagebox.showinfo("Success", f"New database created at {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create database: {str(e)}")

    def save_settings(self, settings_window):
        """Save settings to user config file"""
        try:
            new_source_folder = self.source_folder_var.get()
            new_database = self.database_var.get()
            new_tesseract = self.tesseract_var.get()

            # Verify the database before saving
            if not self.verify_database_schema(new_database):
                messagebox.showerror("Invalid Database", "The selected database doesn't have the required schema.")
                return

            # Verify Tesseract path
            if not os.path.isfile(new_tesseract):
                messagebox.showerror("Invalid Path", "The specified Tesseract executable doesn't exist.")
                return

            # Create settings dictionary
            settings = {
                'SOURCE_FOLDER': new_source_folder,
                'DATABASE_NAME': new_database,
                'TESSERACT_CMD': new_tesseract,
                'VALID_EXTENSIONS': list(config.VALID_EXTENSIONS),
                'TESSERACT_CONFIG': config.TESSERACT_CONFIG,
                'DATE_INPUT_FORMAT': config.DATE_INPUT_FORMAT,
                'DATE_OUTPUT_FORMAT': config.DATE_OUTPUT_FORMAT
            }

            # Save to user config file using standalone function
            if save_user_settings(settings):
                # Update in-memory config
                config.SOURCE_FOLDER = new_source_folder
                config.DATABASE_NAME = new_database
                config.TESSERACT_CMD = new_tesseract

                messagebox.showinfo("Success", "Settings saved successfully")
                settings_window.destroy()
            else:
                messagebox.showerror("Error", "Failed to save settings to config file")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

    def validate_date_string(self, date_str, date_format="%Y-%m-%d"):
        """Validate a date string format"""
        try:
            datetime.strptime(date_str, date_format)
            return True
        except ValueError:
            return False

    def validate_time_frame(self, start_date, end_date):
        """Validate that the time frame is valid (start before end)"""
        if not start_date and not end_date:
            return True

        try:
            start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
            end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

            if start and end and start > end:
                return False
            return True
        except ValueError:
            return False

    def run_analysis(self):
        """Execute the selected analysis and display results"""
        # Get user selections
        selected_indices = self.season_listbox.curselection()

        if not selected_indices:
            messagebox.showwarning("Selection Error", "Please select at least one season")
            return

        if 0 in selected_indices:  # "All Seasons" is selected
            seasons = None
        else:
            seasons = [int(self.season_listbox.get(i)) for i in selected_indices]

        # Get time frame
        start_date = self.start_date_var.get().strip()
        end_date = self.end_date_var.get().strip()

        # Validate time frame
        if (start_date and start_date != "YYYY-MM-DD" and not self.validate_date_string(start_date)) or \
                (end_date and end_date != "YYYY-MM-DD" and not self.validate_date_string(end_date)):
            messagebox.showwarning("Input Error", "Invalid date format. Please use YYYY-MM-DD")
            return

        if not self.validate_time_frame(
                start_date if start_date != "YYYY-MM-DD" else None,
                end_date if end_date != "YYYY-MM-DD" else None
        ):
            messagebox.showwarning("Input Error", "Start date must be before end date")
            return

        # Convert "YYYY-MM-DD" to None
        start_date = start_date if start_date != "YYYY-MM-DD" else None
        end_date = end_date if end_date != "YYYY-MM-DD" else None

        analysis_type = self.analysis_var.get()
        min_matches = self.min_matches_var.get()

        # Clear previous results
        self.results_text.delete(1.0, tk.END)
        self.status_var.set("Running analysis...")
        self.root.update()

        try:
            result = ""  # fix: ensure result is always defined
            # Run the appropriate analysis with time frame parameters
            if analysis_type == "Win Percentages by Map":
                result = print_win_percentages_by_season(seasons, min_matches, start_date, end_date)
            elif analysis_type == "Hero Win Percentages":
                result = print_hero_win_percentages_by_season(seasons, min_matches, start_date, end_date)
            elif analysis_type == "Hero Map Win Rates":
                hero_name = self.selection_var.get()
                if not hero_name:
                    messagebox.showwarning("Selection Error", "Please select a hero")
                    return
                result = print_hero_map_win_percentages(hero_name, seasons, min_matches, start_date, end_date)
            elif analysis_type == "Map Hero Win Rates":
                map_name = self.selection_var.get()
                if not map_name:
                    messagebox.showwarning("Selection Error", "Please select a map")
                    return
                result = print_map_hero_win_percentages(map_name, seasons, min_matches, start_date, end_date)
            elif analysis_type == "All Matches":
                result = print_all_matches_by_season(seasons, start_date, end_date)
            elif analysis_type == "Summary Statistics":
                result = print_summary_stats_by_season(seasons, start_date, end_date)
            elif analysis_type == "Map Frequency Stats":
                result = print_map_frequency_stats_by_season(seasons, start_date, end_date)
            elif analysis_type == "Game Mode Stats":
                result = print_game_mode_stats_by_season(seasons, start_date, end_date)

            # Display the results
            self.results_text.insert(tk.END, result)
            self.status_var.set("Analysis complete")

            # Enable chart button for certain analysis types
            if analysis_type in ["Win Percentages by Map", "Game Mode Stats", "Hero Win Percentages",
                                 "Hero Map Win Rates", "Map Hero Win Rates"]:
                self.chart_button.state(['!disabled'])
            else:
                self.chart_button.state(['disabled'])

        except Exception as e:
            logging.error(f"Error in run_analysis: {e}")
            self.results_text.insert(tk.END, f"Error: {str(e)}")
            self.status_var.set("Error occurred")

    # In ow_stats_gui.py, modify the run_process_screenshots method:
    def run_process_screenshots(self):
        """Run the ReadScreenshot script and display results in the GUI"""
        try:
            self.results_text.delete(1.0, tk.END)  # Clear previous results
            self.status_var.set("Processing screenshots... (0/?)")
            self.root.update()

            # Create a progress update function
            def update_progress(current, total):
                self.status_var.set(f"Processing screenshots... ({current}/{total})")
                self.root.update()

            stats = process_screenshots(progress_callback=update_progress)

            if 'error' in stats:
                # Display error message in red
                self.results_text.tag_config('error', foreground='red')
                self.results_text.insert(tk.END, str(stats['error']), 'error')
                self.status_var.set("Tesseract-OCR not found")
            else:
                # Format the successful results
                result_text = (
                    f"Screenshot Processing Results:\n"
                    f"-----------------------------\n"
                    f"Total screenshots found: {stats['total']}\n"
                    f"Successfully processed: {stats['processed']}\n"
                    f"Skipped (duplicates): {stats['skipped']}\n"
                    f"Errors encountered: {stats['errors']}\n\n"
                )

                if stats['total'] == 0:
                    result_text += "No screenshots found to process.\n"
                else:
                    result_text += "Processed files moved to 'extracted' folder.\n"

                self.results_text.insert(tk.END, result_text)
                self.status_var.set("Screenshot processing complete")

        except Exception as e:
            logging.error(f"Error processing screenshots: {e}")
            self.results_text.tag_config('error', foreground='red')
            self.results_text.insert(tk.END, f"Unexpected error reading screenshots: {str(e)}\n", 'error')
            self.status_var.set("Error processing screenshots")

    def delete_match(self):
        """Show dialog to delete a match by date (local time)"""
        delete_window = tk.Toplevel(self.root)
        delete_window.title("Delete Match")
        delete_window.geometry("400x150")
        delete_window.resizable(False, False)

        ttk.Label(delete_window,
                  text="Enter Match Date (YYYY-MM-DD HH:MM) example: \n 2016-05-24 20:15").pack(pady=10)

        self.date_entry_var = tk.StringVar()
        date_entry = ttk.Entry(delete_window, textvariable=self.date_entry_var, width=25)
        date_entry.pack(pady=5)

        button_frame = ttk.Frame(delete_window)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Delete",
                   command=lambda: self.confirm_delete(delete_window)).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Cancel",
                   command=delete_window.destroy).grid(row=0, column=1, padx=5)

    def confirm_delete(self, delete_window):
        """Confirm and execute match deletion (converts local time to UTC)"""
        date_str = self.date_entry_var.get()

        if not date_str:
            messagebox.showwarning("Input Error", "Please enter a date")
            return

        try:
            # Parse as local time and convert to UTC
            naive_time = datetime.strptime(date_str, config.DATE_OUTPUT_FORMAT)

            # Use the new timezone conversion function
            utc_time = config.local_to_utc(naive_time)
            utc_date_str = utc_time.strftime(config.DATE_OUTPUT_FORMAT)

            if messagebox.askyesno("Confirm Delete",
                                   f"Are you sure you want to delete the match on {date_str} (local time)?"):
                result = delete_match_by_date(utc_date_str)
                messagebox.showinfo("Delete Result", result)
                delete_window.destroy()
                if self.analysis_var.get() == "All Matches":
                    self.run_analysis()
        except ValueError:
            messagebox.showerror("Input Error",
                                 f"Invalid date format. Please use {config.DATE_OUTPUT_FORMAT}")

    def add_match_manually(self):
        """Show dialog to add a match manually (input in local time, stored in UTC)"""
        manual_window = tk.Toplevel(self.root)
        manual_window.title("Add Match Manually")
        manual_window.geometry("500x400")
        manual_window.resizable(False, False)

        # Date (local time)
        ttk.Label(manual_window, text="Date (YYYY-MM-DD HH:MM) in your local time:").grid(
            row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.manual_date_var = tk.StringVar()
        date_entry = ttk.Entry(manual_window, textvariable=self.manual_date_var, width=20)
        date_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # Map
        ttk.Label(manual_window, text="Map:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.manual_map_var = tk.StringVar()
        map_combobox = ttk.Combobox(manual_window, textvariable=self.manual_map_var,
                                    values=sorted(OVERWATCH_MAPS), state='readonly')
        map_combobox.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        # Result
        ttk.Label(manual_window, text="Result:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.manual_result_var = tk.StringVar()
        result_combobox = ttk.Combobox(manual_window, textvariable=self.manual_result_var,
                                       values=['VICTORY', 'DEFEAT', 'DRAW'], state='readonly')
        result_combobox.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        result_combobox.current(0)

        # Length
        ttk.Label(manual_window, text="Length (MM:SS):").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.manual_length_var = tk.StringVar()
        length_entry = ttk.Entry(manual_window, textvariable=self.manual_length_var, width=10)
        length_entry.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

        # Heroes frame
        hero_frame = ttk.LabelFrame(manual_window, text="Heroes and Playtime Percentages", padding=10)
        hero_frame.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="we")

        # Get all heroes from all roles
        all_heroes = []
        for role in OVERWATCH_HEROES.values():
            all_heroes.extend(role)

        # Hero 1
        ttk.Label(hero_frame, text="Hero 1:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        self.manual_hero1_var = tk.StringVar()
        hero1_combobox = ttk.Combobox(hero_frame, textvariable=self.manual_hero1_var,
                                      values=sorted(all_heroes), state='readonly')
        hero1_combobox.grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)

        ttk.Label(hero_frame, text="%:").grid(row=0, column=2, padx=5, pady=2, sticky=tk.W)
        self.manual_percent1_var = tk.IntVar(value=0)
        percent1_spinbox = ttk.Spinbox(hero_frame, from_=0, to=100,
                                       textvariable=self.manual_percent1_var, width=5)
        percent1_spinbox.grid(row=0, column=3, padx=5, pady=2, sticky=tk.W)

        # Hero 2
        ttk.Label(hero_frame, text="Hero 2:").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        self.manual_hero2_var = tk.StringVar()
        hero2_combobox = ttk.Combobox(hero_frame, textvariable=self.manual_hero2_var,
                                      values=sorted(all_heroes), state='readonly')
        hero2_combobox.grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)

        ttk.Label(hero_frame, text="%:").grid(row=1, column=2, padx=5, pady=2, sticky=tk.W)
        self.manual_percent2_var = tk.IntVar(value=0)
        percent2_spinbox = ttk.Spinbox(hero_frame, from_=0, to=100,
                                       textvariable=self.manual_percent2_var, width=5)
        percent2_spinbox.grid(row=1, column=3, padx=5, pady=2, sticky=tk.W)

        # Hero 3
        ttk.Label(hero_frame, text="Hero 3:").grid(row=2, column=0, padx=5, pady=2, sticky=tk.W)
        self.manual_hero3_var = tk.StringVar()
        hero3_combobox = ttk.Combobox(hero_frame, textvariable=self.manual_hero3_var,
                                      values=sorted(all_heroes), state='readonly')
        hero3_combobox.grid(row=2, column=1, padx=5, pady=2, sticky=tk.W)

        ttk.Label(hero_frame, text="%:").grid(row=2, column=2, padx=5, pady=2, sticky=tk.W)
        self.manual_percent3_var = tk.IntVar(value=0)
        percent3_spinbox = ttk.Spinbox(hero_frame, from_=0, to=100,
                                       textvariable=self.manual_percent3_var, width=5)
        percent3_spinbox.grid(row=2, column=3, padx=5, pady=2, sticky=tk.W)

        # Buttons
        button_frame = ttk.Frame(manual_window)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky="we")  # fix: sticky as string

        ttk.Button(button_frame, text="Save",
                   command=lambda: self.save_manual_match(manual_window)).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Cancel",
                   command=manual_window.destroy).grid(row=0, column=1, padx=5)

    def save_manual_match(self, window):
        """Save manually entered match data to database (converts local time to UTC)"""
        try:
            # Validate and convert date from local to UTC
            date_str = self.manual_date_var.get()
            try:
                naive_time = datetime.strptime(date_str, config.DATE_OUTPUT_FORMAT)
                utc_time = config.local_to_utc(naive_time)
                utc_date_str = utc_time.strftime(config.DATE_OUTPUT_FORMAT)
            except ValueError as e:
                messagebox.showerror("Invalid Date",
                                     f"Date must be in format: {config.DATE_OUTPUT_FORMAT}\nError: {str(e)}")
                return

            # Validate map
            map_name = self.manual_map_var.get()
            if not map_name or map_name not in OVERWATCH_MAPS:
                messagebox.showerror("Invalid Map", "Please select a valid map")
                return

            # Validate result
            result = self.manual_result_var.get()
            if result not in ['VICTORY', 'DEFEAT', 'DRAW']:
                messagebox.showerror("Invalid Result", "Result must be VICTORY, DEFEAT or DRAW")
                return

            # Validate length
            length_str = self.manual_length_var.get()
            try:
                mins, secs = map(int, length_str.split(':'))
                length_sec = mins * 60 + secs
            except (ValueError, AttributeError):
                messagebox.showerror("Invalid Length", "Length must be in MM:SS format")
                return

            # Validate heroes and percentages
            hero_data = []
            for hero_var, percent_var in [
                (self.manual_hero1_var, self.manual_percent1_var),
                (self.manual_hero2_var, self.manual_percent2_var),
                (self.manual_hero3_var, self.manual_percent3_var)
            ]:
                hero = hero_var.get()
                percent = percent_var.get()
                if hero and percent > 0:
                    hero_data.append({'hero': hero, 'percentage': percent})

            if not hero_data:
                messagebox.showerror("Invalid Data", "At least one hero with percentage > 0 is required")
                return

            total_percent = sum(h['percentage'] for h in hero_data)
            num_heroes = len(hero_data)

            # Validate percentage totals
            if num_heroes == 1 or num_heroes == 2:
                if total_percent < 98:
                    messagebox.showerror(
                        "Invalid Data",
                        f"With {num_heroes} heroes, total percentage must be at least 98% (current: {total_percent}%)"
                    )
                    return
            elif total_percent > 100:
                messagebox.showerror("Invalid Data",
                                     f"Total percentage cannot exceed 100% (current: {total_percent}%)")
                return

            # Save to database (using UTC time)
            conn = sqlite3.connect(config.DATABASE_NAME)
            c = conn.cursor()
            try:
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
                    messagebox.showinfo("Success", "Match added successfully")
                    window.destroy()

                    # Refresh the display if we're showing matches
                    if self.analysis_var.get() == "All Matatches":
                        self.run_analysis()
                else:
                    messagebox.showerror("Error", "This match already exists in the database")

            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Failed to save match: {str(e)}")
            finally:
                conn.close()

        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")

    def export_results(self):
        """Export the current results to a text file"""
        content = self.results_text.get(1.0, tk.END)
        if not content.strip():
            messagebox.showwarning("Export", "No results to export")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Results As"
        )

        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(content)
                self.status_var.set(f"Results exported to {file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export: {str(e)}")

    def toggle_chart(self):
        """Toggle the display of the chart frame"""
        if self.chart_frame and self.chart_frame.winfo_ismapped():
            self.hide_chart()
        else:
            self.show_chart()

    def show_chart(self):
        """Display a chart based on the current analysis"""
        # Ensure any previous figure is closed
        if self.current_figure:
            plt.close(self.current_figure)
            self.current_figure = None

        # Destroy and recreate the chart frame to ensure clean slate
        if self.chart_frame:
            self.chart_frame.destroy()

        self.chart_frame = ttk.Frame(self.main_frame)
        self.chart_frame.grid(row=0, column=2, rowspan=7, sticky="nse", padx=10)  # fix: sticky as string

        analysis_type = self.analysis_var.get()

        try:
            if analysis_type == "Win Percentages by Map":
                self.current_figure = self.create_win_percentage_chart()
            elif analysis_type == "Hero Win Percentages":
                self.current_figure = self.create_hero_win_percentage_chart()
            elif analysis_type == "Game Mode Stats":
                self.current_figure = self.create_game_mode_chart()
            elif analysis_type == "Hero Map Win Rates":
                self.current_figure = self.create_hero_map_chart()
            elif analysis_type == "Map Hero Win Rates":
                self.current_figure = self.create_map_hero_chart()

            if self.current_figure:
                canvas = FigureCanvasTkAgg(self.current_figure, master=self.chart_frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

                # Add close button
                self.create_chart_close_button(self.chart_frame)

                self.chart_button.config(text="Hide Chart")
            else:
                messagebox.showwarning("Chart Warning", "No chart data available")
                self.hide_chart()

        except Exception as e:
            messagebox.showerror("Chart Error", f"Failed to create chart: {str(e)}")
            self.hide_chart()

    def hide_chart(self):
        """Hide the chart frame"""
        if self.chart_frame:
            # Destroy all widgets in the frame
            for widget in self.chart_frame.winfo_children():
                widget.destroy()
            self.chart_frame.grid_remove()

        if self.current_figure:
            plt.close(self.current_figure)
            self.current_figure = None

        self.chart_button.config(text="Show Chart")

    def create_chart_close_button(self, parent_frame):
        """Create a close button for the chart frame"""
        close_button = ttk.Button(parent_frame, text="×",
                                  command=self.hide_chart,
                                  style='Close.TButton')
        close_button.place(relx=1.0, x=-2, y=2, anchor="ne")

    def create_win_percentage_chart(self):
        """Create a bar chart for win percentages with gradient coloring and clear labels"""
        # Extract data from the results text
        lines = self.results_text.get(1.0, tk.END).split('\n')
        data = []

        for line in lines:
            if '|' in line and not line.startswith('-') and not line.startswith('Map'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 6:
                    try:
                        map_name = parts[0]
                        win_percent_str = parts[-1].replace('%', '').strip()
                        if win_percent_str.replace('.', '').isdigit():
                            win_percent = float(win_percent_str)
                            data.append((map_name, win_percent))
                    except (ValueError, IndexError):
                        continue

        if not data:
            messagebox.showwarning("Chart Warning", "No valid win percentage data found in results.")
            return None

        # Prepare data for chart
        data.sort(key=lambda x: x[1])
        maps = [d[0] for d in data]
        percentages = [d[1] for d in data]

        # Create figure with slightly larger width to accommodate labels
        fig, ax = plt.subplots(figsize=(10, 6))

        # Create color gradient from red to green
        cmap = plt.get_cmap('RdYlGn')  # Red-Yellow-Green colormap
        norm = Normalize(0, 100)  # fix: use Normalize from matplotlib.colors
        colors = [cmap(norm(p)) for p in percentages]

        bars = ax.barh(maps, percentages, color=colors, edgecolor='white', alpha=0.8)

        # Add value labels - ALWAYS BLACK
        for bar in bars:
            width = bar.get_width()
            ax.text(width + 1, bar.get_y() + bar.get_height() / 2,
                    f'{width:.1f}%',
                    va='center',
                    color='black',
                    bbox=dict(facecolor='none', edgecolor='none', alpha=0))

        # Customize chart
        ax.set_xlim(0, 110)
        ax.set_xlabel('Win Percentage')
        ax.set_title('Win Percentage by Map (Performance Gradient)')

        # Add key threshold lines
        thresholds = [33.3, 50, 66.6]
        threshold_colors = ['#ff4757', '#ffa502', '#2ed573']

        # Position threshold labels above the bars
        label_y_position = len(maps) + 0.2

        for threshold, color in zip(thresholds, threshold_colors):
            ax.axvline(x=threshold, color=color, linestyle='--', alpha=0.7, linewidth=1.5)
            ax.text(threshold + 1, label_y_position,
                    f'{threshold}%',
                    color=color,
                    va='center',
                    fontsize=9,
                    bbox=dict(facecolor='none', edgecolor='none', alpha=0))

        # Add colorbar legend
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, orientation='vertical', pad=0.02, shrink=0.5)
        cbar.set_label('Performance Level', rotation=270, labelpad=15)
        cbar.ax.axhline(0.333, color='#ff4757', linestyle='--', linewidth=1.5)
        cbar.ax.axhline(0.5, color='#ffa502', linestyle='--', linewidth=1.5)
        cbar.ax.axhline(0.666, color='#2ed573', linestyle='--', linewidth=1.5)

        # Custom grid and appearance
        ax.grid(axis='x', linestyle='--', alpha=0.3)
        ax.set_axisbelow(True)
        plt.tight_layout()

        return fig

    def create_hero_win_percentage_chart(self):
        """Create a bar chart for hero win percentages with gradient coloring"""
        # Extract data from the results text
        lines = self.results_text.get(1.0, tk.END).split('\n')
        data = []

        for line in lines:
            if '|' in line and not line.startswith('-') and not line.startswith('Hero'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 5:
                    try:
                        hero = parts[0]
                        weighted_wins = float(parts[2])
                        weighted_losses = float(parts[3])
                        win_percent_str = parts[4].replace('%', '').strip()

                        if win_percent_str.replace('.', '').isdigit():
                            win_percent = float(win_percent_str)
                            total_weighted = weighted_wins + weighted_losses
                            if total_weighted > 0:
                                data.append((hero, win_percent, weighted_wins, weighted_losses))
                    except (ValueError, IndexError):
                        continue

        if not data:
            messagebox.showwarning("Chart Warning", "No valid hero win percentage data found in results.")
            return None

        # Prepare data for chart
        data.sort(key=lambda x: x[1])
        heroes = [d[0] for d in data]
        percentages = [d[1] for d in data]
        weighted_wins = [d[2] for d in data]
        weighted_losses = [d[3] for d in data]

        # Create figure with slightly larger width to accommodate labels
        fig, ax = plt.subplots(figsize=(10, 8))

        # Create color gradient from red to green
        cmap = plt.get_cmap('RdYlGn')
        norm = Normalize(0, 100)
        colors = [cmap(norm(p)) for p in percentages]

        bars = ax.barh(heroes, percentages, color=colors, edgecolor='white', alpha=0.8)

        # Add value labels (always black)
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(width + 1, bar.get_y() + bar.get_height() / 2,
                    f'{width:.1f}% ({weighted_wins[i]:.1f}W/{weighted_losses[i]:.1f}L)',
                    va='center',
                    color='black',
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.2'))

        # Customize chart
        ax.set_xlim(0, 110)
        ax.set_xlabel('Win Percentage')
        ax.set_title('Hero Win Percentages (Weighted by Playtime)')

        # Add key threshold lines
        thresholds = [33.3, 50, 66.6]
        threshold_colors = ['#ff4757', '#ffa502', '#2ed573']

        # Position threshold labels above the bars
        label_y_position = len(heroes) - 0.5

        for threshold, color in zip(thresholds, threshold_colors):
            ax.axvline(x=threshold, color=color, linestyle='--', alpha=0.7, linewidth=1.5)
            ax.text(threshold + 1, label_y_position,
                    f'{threshold}%',
                    color=color,
                    va='center',
                    fontsize=9,
                    bbox=dict(facecolor='none', edgecolor='none', alpha=0))

        # Add colorbar legend
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, orientation='vertical', pad=0.02, shrink=0.5)
        cbar.set_label('Performance Level', rotation=270, labelpad=15)
        cbar.ax.axhline(0.333, color='#ff4757', linestyle='--', linewidth=1.5)
        cbar.ax.axhline(0.5, color='#ffa502', linestyle='--', linewidth=1.5)
        cbar.ax.axhline(0.666, color='#2ed573', linestyle='--', linewidth=1.5)

        # Custom grid and appearance
        ax.grid(axis='x', linestyle='--', alpha=0.3)
        ax.set_axisbelow(True)
        plt.tight_layout()

        return fig

    def create_game_mode_chart(self):
        """Create a bar chart for game mode win percentages with gradient coloring"""
        # Extract data from the results text
        lines = self.results_text.get(1.0, tk.END).split('\n')
        data = []

        for line in lines:
            if '|' in line and not line.startswith('-') and not line.startswith('Game Mode'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 6:
                    try:
                        mode = parts[0]
                        wins = int(parts[2])
                        losses = int(parts[3])
                        win_percent_str = parts[4].replace('%', '').strip()

                        if win_percent_str.replace('.', '').isdigit():
                            win_percent = float(win_percent_str)
                            total_matches = wins + losses
                            if total_matches > 0:
                                data.append((mode, win_percent, total_matches))
                    except (ValueError, IndexError):
                        continue

        if not data:
            messagebox.showwarning("Chart Warning", "No valid game mode data found in results.")
            return None

        # Prepare data for chart
        data.sort(key=lambda x: x[1])
        modes = [d[0] for d in data]
        percentages = [d[1] for d in data]
        match_counts = [d[2] for d in data]

        # Create figure with slightly larger width to accommodate labels
        fig, ax = plt.subplots(figsize=(10, 6))

        # Create color gradient from red to green
        cmap = plt.get_cmap('RdYlGn')
        norm = Normalize(0, 100)
        colors = [cmap(norm(p)) for p in percentages]

        bars = ax.barh(modes, percentages, color=colors, edgecolor='white', alpha=0.8)

        # Add value labels and match counts (always black)
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(width + 1, bar.get_y() + bar.get_height() / 2,
                    f'{width:.1f}% ({match_counts[i]} matches)',
                    va='center',
                    color='black',
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.2'))

        # Customize chart
        ax.set_xlim(0, 110)
        ax.set_xlabel('Win Percentage')
        ax.set_title('Win Percentage by Game Mode')

        # Add key threshold lines
        thresholds = [33.3, 50, 66.6]
        threshold_colors = ['#ff4757', '#ffa502', '#2ed573']

        # Position threshold labels above the bars
        label_y_position = len(modes) - 0.5

        for threshold, color in zip(thresholds, threshold_colors):
            ax.axvline(x=threshold, color=color, linestyle='--', alpha=0.7, linewidth=1.5)
            ax.text(threshold + 1, label_y_position,
                    f'{threshold}%',
                    color=color,
                    va='center',
                    fontsize=9,
                    bbox=dict(facecolor='none', edgecolor='none', alpha=0))

        # Add colorbar legend
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, orientation='vertical', pad=0.02, shrink=0.5)
        cbar.set_label('Performance Level', rotation=270, labelpad=15)
        cbar.ax.axhline(0.333, color='#ff4757', linestyle='--', linewidth=1.5)
        cbar.ax.axhline(0.5, color='#ffa502', linestyle='--', linewidth=1.5)
        cbar.ax.axhline(0.666, color='#2ed573', linestyle='--', linewidth=1.5)

        # Custom grid and appearance
        ax.grid(axis='x', linestyle='--', alpha=0.3)
        ax.set_axisbelow(True)
        plt.tight_layout()

        return fig

    def create_hero_map_chart(self):
        """Create a bar chart for a hero's win percentages across maps"""
        # Extract data from the results text
        lines = self.results_text.get(1.0, tk.END).split('\n')
        data = []
        hero_name = self.selection_var.get()

        for line in lines:
            if '|' in line and not line.startswith('-') and not line.startswith('Map'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 6:
                    try:
                        map_name = parts[0]
                        win_percent_str = parts[-1].replace('%', '').strip()
                        if win_percent_str.replace('.', '').isdigit():
                            win_percent = float(win_percent_str)
                            data.append((map_name, win_percent))
                    except (ValueError, IndexError):
                        continue

        if not data:
            messagebox.showwarning("Chart Warning", "No valid win percentage data found in results.")
            return None

        # Prepare data for chart
        data.sort(key=lambda x: x[1])
        maps = [d[0] for d in data]
        percentages = [d[1] for d in data]

        # Create figure with slightly larger width to accommodate labels
        fig, ax = plt.subplots(figsize=(10, 6))

        # Create color gradient from red to green
        cmap = plt.get_cmap('RdYlGn')
        norm = Normalize(0, 100)  # fix: use Normalize from matplotlib.colors
        colors = [cmap(norm(p)) for p in percentages]

        bars = ax.barh(maps, percentages, color=colors, edgecolor='white', alpha=0.8)

        # Add value labels - ALWAYS BLACK
        for bar in bars:
            width = bar.get_width()
            ax.text(width + 1, bar.get_y() + bar.get_height() / 2,
                    f'{width:.1f}%',
                    va='center',
                    color='black',
                    bbox=dict(facecolor='none', edgecolor='none', alpha=0))

        # Customize chart
        ax.set_xlim(0, 110)
        ax.set_xlabel('Win Percentage')
        ax.set_title(f'Win Percentage by Map for {hero_name}')

        # Add key threshold lines
        thresholds = [33.3, 50, 66.6]
        threshold_colors = ['#ff4757', '#ffa502', '#2ed573']

        # Position threshold labels above the bars
        label_y_position = len(maps) + 0.2

        for threshold, color in zip(thresholds, threshold_colors):
            ax.axvline(x=threshold, color=color, linestyle='--', alpha=0.7, linewidth=1.5)
            ax.text(threshold + 1, label_y_position,
                    f'{threshold}%',
                    color=color,
                    va='center',
                    fontsize=9,
                    bbox=dict(facecolor='none', edgecolor='none', alpha=0))

        # Add colorbar legend
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, orientation='vertical', pad=0.02, shrink=0.5)
        cbar.set_label('Performance Level', rotation=270, labelpad=15)
        cbar.ax.axhline(0.333, color='#ff4757', linestyle='--', linewidth=1.5)
        cbar.ax.axhline(0.5, color='#ffa502', linestyle='--', linewidth=1.5)
        cbar.ax.axhline(0.666, color='#2ed573', linestyle='--', linewidth=1.5)

        # Custom grid and appearance
        ax.grid(axis='x', linestyle='--', alpha=0.3)
        ax.set_axisbelow(True)
        plt.tight_layout()

        return fig

    def create_map_hero_chart(self):
        """Create a bar chart for hero win percentages on a specific map"""
        # Extract data from the results text
        lines = self.results_text.get(1.0, tk.END).split('\n')
        data = []
        map_name = self.selection_var.get()

        for line in lines:
            if '|' in line and not line.startswith('-') and not line.startswith('Hero'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 5:
                    try:
                        hero = parts[0]
                        weighted_wins = float(parts[2])
                        weighted_losses = float(parts[3])
                        win_percent_str = parts[4].replace('%', '').strip()

                        if win_percent_str.replace('.', '').isdigit():
                            win_percent = float(win_percent_str)
                            total_weighted = weighted_wins + weighted_losses
                            if total_weighted > 0:
                                data.append((hero, win_percent, weighted_wins, weighted_losses))
                    except (ValueError, IndexError):
                        continue

        if not data:
            messagebox.showwarning("Chart Warning", "No valid hero win percentage data found in results.")
            return None

        # Prepare data for chart
        data.sort(key=lambda x: x[1])
        heroes = [d[0] for d in data]
        percentages = [d[1] for d in data]
        weighted_wins = [d[2] for d in data]
        weighted_losses = [d[3] for d in data]

        # Create figure with slightly larger width to accommodate labels
        fig, ax = plt.subplots(figsize=(10, 8))

        # Create color gradient from red to green
        cmap = plt.get_cmap('RdYlGn')
        norm = Normalize(0, 100)
        colors = [cmap(norm(p)) for p in percentages]

        bars = ax.barh(heroes, percentages, color=colors, edgecolor='white', alpha=0.8)

        # Add value labels (always black)
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(width + 1, bar.get_y() + bar.get_height() / 2,
                    f'{width:.1f}% ({weighted_wins[i]:.1f}W/{weighted_losses[i]:.1f}L)',
                    va='center',
                    color='black',
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.2'))

        # Customize chart
        ax.set_xlim(0, 110)
        ax.set_xlabel('Win Percentage')
        ax.set_title(f'Hero Win Percentages on {map_name}')

        # Add key threshold lines
        thresholds = [33.3, 50, 66.6]
        threshold_colors = ['#ff4757', '#ffa502', '#2ed573']

        # Position threshold labels above the bars
        label_y_position = len(heroes) - 0.5

        for threshold, color in zip(thresholds, threshold_colors):
            ax.axvline(x=threshold, color=color, linestyle='--', alpha=0.7, linewidth=1.5)
            ax.text(threshold + 1, label_y_position,
                    f'{threshold}%',
                    color=color,
                    va='center',
                    fontsize=9,
                    bbox=dict(facecolor='none', edgecolor='none', alpha=0))

        # Add colorbar legend
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, orientation='vertical', pad=0.02, shrink=0.5)
        cbar.set_label('Performance Level', rotation=270, labelpad=15)
        cbar.ax.axhline(0.333, color='#ff4757', linestyle='--', linewidth=1.5)
        cbar.ax.axhline(0.5, color='#ffa502', linestyle='--', linewidth=1.5)
        cbar.ax.axhline(0.666, color='#2ed573', linestyle='--', linewidth=1.5)

        # Custom grid and appearance
        ax.grid(axis='x', linestyle='--', alpha=0.3)
        ax.set_axisbelow(True)
        plt.tight_layout()

        return fig

    def show_about(self):
        """Display the about dialog"""
        about_text = (
            "Overwatch2 Hero Map Stats v1.0\n\n"
            "An unofficial tool for analyzing Overwatch match statistics "
            "extracted from game screenshots.\n\n"
            "------------------------------------\n\n"
            "Disclaimer:\n"
            "This project is an independent tool and is not affiliated with, "
            "endorsed, sponsored, or specifically approved by Blizzard Entertainment, Inc. "
            "Overwatch is a trademark or registered trademark of Blizzard Entertainment, Inc. "
            "in the U.S. and/or other countries."
        )
        messagebox.showinfo("About", about_text)


if __name__ == "__main__":
    root = tk.Tk()
    app = OverwatchStatsApp(root)
    root.mainloop()