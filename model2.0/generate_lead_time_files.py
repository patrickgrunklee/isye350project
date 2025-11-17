"""
Generate Lead Time CSV files for all DoH scenarios

This script creates the required Lead Time files by copying a template
and updating the Days on Hand values for each scenario.
"""
import pandas as pd
from pathlib import Path
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")

# All scenarios (domestic, international)
scenarios = [
    (0, 0),
    (1, 3),
    (2, 6),
    (3, 8),
    (4, 10),
    (5, 12),
    (7, 15),
    (9, 17),
    (11, 19),
    (14, 21),
]

# Load the template file - you can use any existing lead time file as template
template_file = DATA_DIR / "Lead TIme.csv"

if not template_file.exists():
    print(f"ERROR: Template file not found: {template_file}")
    print("Please ensure you have a base Lead TIme.csv file to use as template")
    sys.exit(1)

print("="*80)
print("GENERATING LEAD TIME FILES FOR ALL SCENARIOS")
print("="*80)
print(f"\nTemplate file: {template_file}")
print(f"Total scenarios: {len(scenarios)}")
print()

# International SKUs (based on typical patterns)
international_skus = ['SKUW1', 'SKUW2', 'SKUW3', 'SKUE1', 'SKUE2', 'SKUE3']

for doh_dom, doh_intl in scenarios:
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
    print(f"✓ Created: {output_file.name}")
    print(f"   Domestic: {doh_dom} days, International: {doh_intl} days")

print("\n" + "="*80)
print("ALL LEAD TIME FILES GENERATED")
print("="*80)
print(f"\nYou can now run: python run_all_scenarios.py")
