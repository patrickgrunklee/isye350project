"""
Script to add truckload tracking to all phase2_DAILY models.

This script updates:
- phase2_DAILY_0_0_doh.py
- phase2_DAILY_5_2_doh.py
- phase2_DAILY_10_3_doh.py

To match the truckload tracking already added to phase2_DAILY_3_1_doh.py
"""

import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# List of models to update (excluding 3_1 which is already done)
models_to_update = [
    'phase2_DAILY_0_0_doh.py',
    'phase2_DAILY_5_2_doh.py',
    'phase2_DAILY_10_3_doh.py'
]

MODEL_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0")

# Import statement to add
import_addition = """from truckload_constants import (
    TRUCK_WEIGHT_CAPACITY_LBS,
    TRUCK_VOLUME_CAPACITY_CUFT,
    SUPPLIER_MAP,
    calculate_truckloads
)"""

# Truckload analysis section to add (before "DAILY MODEL COMPLETE")
truckload_analysis = '''
print("\\n[4] TRUCKLOAD ANALYSIS")
print("="*100)
print(f"Truck specifications: 53ft trailer")
print(f"  - Weight capacity: {TRUCK_WEIGHT_CAPACITY_LBS:,} lbs")
print(f"  - Volume capacity: {TRUCK_VOLUME_CAPACITY_CUFT:,} cu ft")
print("="*100)

# Extract delivery data
deliveries_df = daily_deliveries.records
deliveries_df.columns = ['Month', 'Day', 'SKU', 'Facility', 'Deliveries', 'Marginal', 'Lower', 'Upper', 'Scale']
deliveries_df = deliveries_df[deliveries_df['Deliveries'] > 0.01]

# Calculate truckloads per supplier per day per facility
print("\\nCalculating truckloads per supplier per day...")

truckload_data = []
for month in months:
    for day in days:
        for fac in facilities:
            for supplier_type in ['Domestic', 'International']:
                # Get all deliveries for this supplier type on this day to this facility
                day_supplier_deliveries = deliveries_df[
                    (deliveries_df['Month'] == str(month)) &
                    (deliveries_df['Day'] == str(day)) &
                    (deliveries_df['Facility'] == fac)
                ]

                total_weight = 0
                total_volume = 0
                num_skus = 0

                for _, row in day_supplier_deliveries.iterrows():
                    sku = row['SKU']
                    if sku_data[sku]['supplier_type'] == supplier_type:
                        num_inbound_packs = row['Deliveries']
                        # Each delivery is in units of inbound packs
                        total_weight += num_inbound_packs * sku_data[sku]['inbound_weight']
                        total_volume += num_inbound_packs * sku_data[sku]['inbound_volume']
                        num_skus += 1

                if total_weight > 0 or total_volume > 0:
                    trucks_needed = calculate_truckloads(total_weight, total_volume)
                    truckload_data.append({
                        'Month': month,
                        'Day': day,
                        'Facility': fac,
                        'Supplier_Type': supplier_type,
                        'Weight_lbs': total_weight,
                        'Volume_cuft': total_volume,
                        'Trucks_Needed': trucks_needed,
                        'Num_SKUs': num_skus
                    })

truckload_df = pd.DataFrame(truckload_data)

if len(truckload_df) > 0:
    # Summary statistics
    print(f"\\n✓ Calculated truckloads for {len(truckload_df)} delivery events")

    print("\\n--- Overall Statistics ---")
    print(f"Total delivery days with trucks: {len(truckload_df):,}")
    print(f"Total trucks needed over 10 years: {truckload_df['Trucks_Needed'].sum():,.0f}")
    print(f"Average trucks per delivery: {truckload_df['Trucks_Needed'].mean():.2f}")
    print(f"Max trucks in single day: {truckload_df['Trucks_Needed'].max():.0f}")

    print("\\n--- By Supplier Type ---")
    for supplier_type in ['Domestic', 'International']:
        supplier_trucks = truckload_df[truckload_df['Supplier_Type'] == supplier_type]
        if len(supplier_trucks) > 0:
            print(f"\\n{supplier_type}:")
            print(f"  Total trucks: {supplier_trucks['Trucks_Needed'].sum():,.0f}")
            print(f"  Delivery days: {len(supplier_trucks):,}")
            print(f"  Avg trucks/delivery: {supplier_trucks['Trucks_Needed'].mean():.2f}")
            print(f"  Max trucks/day: {supplier_trucks['Trucks_Needed'].max():.0f}")

    print("\\n--- By Facility ---")
    for fac in facilities:
        fac_trucks = truckload_df[truckload_df['Facility'] == fac]
        if len(fac_trucks) > 0:
            print(f"\\n{fac}:")
            print(f"  Total trucks: {fac_trucks['Trucks_Needed'].sum():,.0f}")
            print(f"  Delivery days: {len(fac_trucks):,}")
            print(f"  Avg trucks/delivery: {fac_trucks['Trucks_Needed'].mean():.2f}")
            print(f"  Max trucks/day: {fac_trucks['Trucks_Needed'].max():.0f}")

    # Peak days analysis
    print("\\n--- Peak Delivery Days (>5 trucks) ---")
    peak_days = truckload_df[truckload_df['Trucks_Needed'] > 5].sort_values('Trucks_Needed', ascending=False)
    if len(peak_days) > 0:
        print(f"\\nFound {len(peak_days)} days with >5 trucks")
        print("\\nTop 10 highest truck days:")
        for idx, (_, row) in enumerate(peak_days.head(10).iterrows(), 1):
            print(f"  {idx}. Month {row['Month']}, Day {row['Day']} - {row['Facility']} - {row['Supplier_Type']}: {row['Trucks_Needed']:.0f} trucks")
    else:
        print("  No days with >5 trucks needed")

    # Save truckload analysis to CSV (use DOH-specific filename)
    doh_suffix = MODEL_DIR.stem if hasattr(MODEL_DIR, 'stem') else ''
    output_file = RESULTS_DIR / f"truckload_analysis_{Path(__file__).stem.split('_')[-2]}_{Path(__file__).stem.split('_')[-1].replace('.py', '')}.csv"
    truckload_df.to_csv(output_file, index=False)
    print(f"\\n✓ Truckload analysis saved to: {output_file}")
else:
    print("\\n⚠️  No deliveries found in model solution")
'''

print("="*80)
print("ADDING TRUCKLOAD TRACKING TO PHASE2 DAILY MODELS")
print("="*80)

for model_file in models_to_update:
    model_path = MODEL_DIR / model_file

    print(f"\n Processing {model_file}...")

    if not model_path.exists():
        print(f"  ⚠️  File not found: {model_path}")
        continue

    # Read file
    with open(model_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if already updated
    if 'truckload_constants' in content:
        print(f"  ℹ️  Already has truckload tracking - skipping")
        continue

    # 1. Add import after other imports
    if 'from pathlib import Path' in content:
        content = content.replace(
            'from pathlib import Path',
            f'from pathlib import Path\n{import_addition}'
        )
        print(f"  ✓ Added imports")
    else:
        print(f"  ⚠️  Could not find import location")
        continue

    # 2. Update SKU data parsing to include inbound dimensions
    sku_parse_old = '''    # Inbound to sell pack conversion ratio
    # Example: SKUW1 arrives in packs of 144 units, stored as 144/12 = 12 sell packs
    inbound_to_sell_ratio = inbound_qty / sell_qty if sell_qty > 0 else 1

    sku_data[sku] = {
        'sell_qty': sell_qty,
        'sell_volume': sell_volume,
        'sell_weight': sell_weight,
        'inbound_qty': inbound_qty,
        'inbound_to_sell_ratio': inbound_to_sell_ratio
    }'''

    sku_parse_new = '''    # Inbound pack dimensions and weight
    inbound_dims = parse_dimension(row['Inbound Pack Dimensions'])
    inbound_volume = (inbound_dims[0] * inbound_dims[1] * inbound_dims[2]) / 1728  # Convert to cu ft
    inbound_weight = parse_weight(row['Inbound Pack Weight'])

    # Inbound to sell pack conversion ratio
    # Example: SKUW1 arrives in packs of 144 units, stored as 144/12 = 12 sell packs
    inbound_to_sell_ratio = inbound_qty / sell_qty if sell_qty > 0 else 1

    # Supplier type
    supplier_type = row['Supplier Type'].strip()

    sku_data[sku] = {
        'sell_qty': sell_qty,
        'sell_volume': sell_volume,
        'sell_weight': sell_weight,
        'inbound_qty': inbound_qty,
        'inbound_volume': inbound_volume,
        'inbound_weight': inbound_weight,
        'inbound_to_sell_ratio': inbound_to_sell_ratio,
        'supplier_type': supplier_type
    }'''

    if sku_parse_old in content:
        content = content.replace(sku_parse_old, sku_parse_new)
        print(f"  ✓ Updated SKU data parsing")
    else:
        print(f"  ⚠️  Could not find SKU parsing section")

    # 3. Add truckload analysis before "DAILY MODEL COMPLETE"
    if 'print("\\n" + "="*100)\nprint("DAILY MODEL COMPLETE")' in content:
        content = content.replace(
            'print("\\n" + "="*100)\nprint("DAILY MODEL COMPLETE")',
            f'{truckload_analysis}\n\nprint("\\n" + "="*100)\nprint("DAILY MODEL COMPLETE")'
        )
        print(f"  ✓ Added truckload analysis section")
    else:
        print(f"  ⚠️  Could not find 'DAILY MODEL COMPLETE' marker")

    # Write updated content
    with open(model_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  ✅ Successfully updated {model_file}")

print("\n" + "="*80)
print("UPDATE COMPLETE")
print("="*80)
print("\nUpdated models:")
for model_file in models_to_update:
    print(f"  - {model_file}")
print("\nTruckload tracking has been added to all phase2_DAILY models.")
