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

def delete_excel_files():
    """Delete all Excel files in the Model Data directory"""
    # Define the Model Data directory
    model_data_dir = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")

    # Get all Excel files
    excel_files = list(model_data_dir.glob("*.xlsx")) + list(model_data_dir.glob("*.xls"))

    if not excel_files:
        print(f"{ANSI_FOREGROUND_YELLOW}No Excel files found in Model Data directory{ANSI_RESET_ALL}")
        return

    print(f"{ANSI_FOREGROUND_BLUE}\nFound {len(excel_files)} Excel file(s) to delete\n{ANSI_RESET_ALL}")

    success_count = 0
    fail_count = 0
    skipped_count = 0

    # Delete each Excel file
    for excel_path in excel_files:
        # Check if corresponding CSV exists
        csv_path = excel_path.with_suffix('.csv')

        if not csv_path.exists():
            print(f"{ANSI_FOREGROUND_YELLOW}[SKIP] No CSV found for: {os.path.basename(excel_path)}{ANSI_RESET_ALL}")
            skipped_count += 1
            continue

        try:
            # Delete the Excel file
            excel_path.unlink()
            print(f"{ANSI_FOREGROUND_GREEN}[DELETED] {os.path.basename(excel_path)}{ANSI_RESET_ALL}")
            success_count += 1
        except Exception as e:
            print(f"{ANSI_FOREGROUND_RED}[ERROR] Could not delete {os.path.basename(excel_path)}: {str(e)}{ANSI_RESET_ALL}")
            fail_count += 1

    # Summary
    print(f"{ANSI_FOREGROUND_BLUE}\n{'='*50}{ANSI_RESET_ALL}")
    print(f"{ANSI_FOREGROUND_GREEN}Successfully deleted: {success_count}{ANSI_RESET_ALL}")
    if skipped_count > 0:
        print(f"{ANSI_FOREGROUND_YELLOW}Skipped (no CSV): {skipped_count}{ANSI_RESET_ALL}")
    if fail_count > 0:
        print(f"{ANSI_FOREGROUND_RED}Failed: {fail_count}{ANSI_RESET_ALL}")
    print(f"{ANSI_FOREGROUND_BLUE}{'='*50}\n{ANSI_RESET_ALL}")

if __name__ == "__main__":
    delete_excel_files()
