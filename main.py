# main.py
import tkinter as tk
import sys
import logging
from ow_stats_gui import OverwatchStatsApp

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

def main():
    """Main entry point for Overwatch Match Statistics Analyzer GUI."""
    root = tk.Tk()
    app = OverwatchStatsApp(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logging.info("Application terminated by user")
        sys.exit(0)

if __name__ == "__main__":
    main()