import pandas as pd
import os
import sys
from pathlib import Path
from rainbow.ansi import (
    ANSI_FOREGROUND_GREEN, ANSI_FOREGROUND_RED,
    ANSI_FOREGROUND_BLUE, ANSI_FOREGROUND_YELLOW,
    ANSI_RESET_ALL
)

# Set UTF-8 encoding for console output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def convert_excel_to_csv(excel_path, csv_path):
    """Convert an Excel file to CSV format"""
    try:
        # Read Excel file
        df = pd.read_excel(excel_path, engine='openpyxl')

        # Write to CSV
        df.to_csv(csv_path, index=False)

        print(f"{ANSI_FOREGROUND_GREEN}[OK] Converted: {os.path.basename(excel_path)} -> {os.path.basename(csv_path)}{ANSI_RESET_ALL}")
        return True
    except Exception as e:
        print(f"{ANSI_FOREGROUND_RED}[ERROR] Converting {os.path.basename(excel_path)}: {str(e)}{ANSI_RESET_ALL}")
        return False

def main():
    # Define the Model Data directory
    model_data_dir = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")

    # Get all Excel files
    excel_files = list(model_data_dir.glob("*.xlsx")) + list(model_data_dir.glob("*.xls"))

    if not excel_files:
        print(f"{ANSI_FOREGROUND_YELLOW}No Excel files found in Model Data directory{ANSI_RESET_ALL}")
        return

    print(f"{ANSI_FOREGROUND_BLUE}\nFound {len(excel_files)} Excel file(s) to convert\n{ANSI_RESET_ALL}")

    success_count = 0
    fail_count = 0

    # Convert each Excel file
    for excel_path in excel_files:
        # Create CSV filename (same name, different extension)
        csv_path = excel_path.with_suffix('.csv')

        if convert_excel_to_csv(excel_path, csv_path):
            success_count += 1
        else:
            fail_count += 1

    # Summary
    print(f"{ANSI_FOREGROUND_BLUE}\n{'='*50}{ANSI_RESET_ALL}")
    print(f"{ANSI_FOREGROUND_GREEN}Successfully converted: {success_count}{ANSI_RESET_ALL}")
    if fail_count > 0:
        print(f"{ANSI_FOREGROUND_RED}Failed: {fail_count}{ANSI_RESET_ALL}")
    print(f"{ANSI_FOREGROUND_BLUE}{'='*50}\n{ANSI_RESET_ALL}")

if __name__ == "__main__":
    main()
