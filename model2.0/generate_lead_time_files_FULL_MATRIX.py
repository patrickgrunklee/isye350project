"""
Generate Lead Time CSV files for FULL MATRIX (100 scenarios)

Creates all combinations of:
- Domestic DoH: 0, 1, 2, 3, 4, 5, 7, 9, 11, 14
- International DoH: 0, 3, 6, 8, 10, 12, 15, 17, 19, 21

Total: 10 × 10 = 100 lead time files
"""
import pandas as pd
from pathlib import Path
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")

# Define the values for each dimension
domestic_values = [0, 1, 2, 3, 4, 5, 7, 9, 11, 14]
international_values = [0, 3, 6, 8, 10, 12, 15, 17, 19, 21]

# Load the template file
template_file = DATA_DIR / "Lead TIme.csv"

if not template_file.exists():
    print(f"ERROR: Template file not found: {template_file}")
    print("Please ensure you have a base Lead TIme.csv file to use as template")
    sys.exit(1)

print("="*80)
print("GENERATING LEAD TIME FILES FOR FULL MATRIX")
print("="*80)
print(f"\nTemplate file: {template_file}")
print(f"Domestic values: {domestic_values}")
print(f"International values: {international_values}")
print(f"Total files to generate: {len(domestic_values) * len(international_values)}")
print()

# International SKUs (based on typical patterns)
international_skus = ['SKUW1', 'SKUW2', 'SKUW3', 'SKUE1', 'SKUE2', 'SKUE3']

files_created = 0

for doh_intl in international_values:
    for doh_dom in domestic_values:
        output_file = DATA_DIR / f"Lead TIme_{doh_intl}_{doh_dom}_business_days.csv"

        # Read template
        df = pd.read_csv(template_file)

        # Update Days on Hand columns for each facility
        for idx, row in df.iterrows():
            sku = row['SKU Number']
            is_international = sku in international_skus

            # Set DoH value based on SKU type
            doh_value = doh_intl if is_international else doh_dom

            # Update all facility columns
            if 'Columbus - Days on Hand' in df.columns:
                df.at[idx, 'Columbus - Days on Hand'] = doh_value
            if 'Sacramento - Days on Hand' in df.columns:
                df.at[idx, 'Sacramento - Days on Hand'] = doh_value
            if 'Austin Days on Hand' in df.columns:
                df.at[idx, 'Austin Days on Hand'] = doh_value

        # Save the file
        df.to_csv(output_file, index=False)
        files_created += 1

        # Progress indicator
        if files_created % 10 == 0:
            print(f"  Progress: {files_created}/{len(domestic_values) * len(international_values)} files created")

print(f"\n✓ Created: {files_created} Lead Time CSV files")

print("\n" + "="*80)
print("ALL LEAD TIME FILES GENERATED")
print("="*80)
print(f"\nYou can now run:")
print("  - python run_all_scenarios_FULL_MATRIX.py  (all 100 scenarios)")
print("  - python run_all_scenarios.py               (main 10 scenarios only)")
