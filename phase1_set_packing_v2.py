"""
PHASE 1: SET PACKING OPTIMIZATION - Version 2
==============================================

Generates TOP 10 optimal packing configurations for each (facility, storage_type).

Key constraints:
- Each package must fit within max item volume for that storage type
- Total packages ≤ max items per shelf
- Total weight ≤ shelf weight capacity
- Maximize utilization (volume + weight)

Generates multiple configurations to give Phase 2 flexibility in choosing
which shelf configurations to use based on demand.

Output: packing_configurations.csv with Config_ID for each unique configuration
"""

import pandas as pd
import numpy as np
from gamspy import Container, Set, Parameter, Variable, Equation, Model, Sum, Sense
from pathlib import Path
import sys
import os
from itertools import combinations

os.environ['GAMSLICE_STRING'] = 'd81a3160-ec06-4fb4-9543-bfff870b9ecb'

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")
RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results\Phase1_SetPacking")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

NUM_CONFIGS = 10  # Generate top 10 configurations per (facility, storage_type)

print("="*100)
print("PHASE 1: SET PACKING OPTIMIZATION V2 - MULTIPLE SHELF CONFIGURATIONS")
print("="*100)
print(f"\nObjective: Generate top {NUM_CONFIGS} packing configurations per (facility, storage_type)")
print("Constraint: Each package must fit within max item volume for storage type")
print("Output: Discrete packing options for Phase 2 multiperiod model\n")

# Utility functions
def parse_dimension(dim_str, in_feet=False):
    try:
        parts = str(dim_str).strip().replace('x', ' x ').replace('X', ' x ').split(' x ')
        if len(parts) != 3:
            return (1.0, 1.0, 1.0)
        if in_feet:
            return tuple(float(p.strip()) for p in parts)
        else:
            return tuple(float(p.strip()) / 12 for p in parts)
    except:
        return (1.0, 1.0, 1.0)

def parse_weight(wt_str):
    try:
        return float(str(wt_str).replace('lbs', '').replace('lb', '').strip())
    except:
        return 1.0

def parse_quantity(qty_str):
    try:
        return int(str(qty_str).split('(')[0].strip())
    except:
        return 1

# Load data
print("[1/6] Loading data files...")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
shelving_dims_df = pd.read_csv(DATA_DIR / "Shelving Dimensions.csv")
storage_constraints_df = pd.read_csv(DATA_DIR / "Storage Type Constraints.csv")
print("   ✓ Data loaded")

# Parse storage type constraints (max item volume)
print("\n[2/6] Loading storage type constraints...")
storage_type_max_vol = {}
for _, row in storage_constraints_df.iterrows():
    st = row['Storage Type']
    max_vol = float(row['Max Item Volume (cu ft)'])
    storage_type_max_vol[st] = max_vol
    print(f"   {st:<15}: Max item volume = {max_vol:>8.3f} cu ft")

# Parse SKU details
print("\n[3/6] Processing SKU details...")
sku_data = {}
for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']

    # Sell pack details
    sell_dims = parse_dimension(row['Sell Pack Dimensions (in)'])  # inches
    sell_volume = sell_dims[0] * sell_dims[1] * sell_dims[2]
    sell_weight = parse_weight(row['Sell Pack Weight'])
    sell_qty = parse_quantity(row['Sell Pack Quantity'])

    # Storage type
    storage_method = str(row['Storage Method']).strip().lower()
    if 'bin' in storage_method:
        storage_type = 'Bins'
    elif 'hazmat' in storage_method:
        storage_type = 'Hazmat'
    elif 'rack' in storage_method:
        storage_type = 'Racking'
    elif 'pallet' in storage_method:
        storage_type = 'Pallet'
    else:
        storage_type = 'Bins'

    # Check if package fits within storage type constraint
    max_vol_for_type = storage_type_max_vol.get(storage_type, 999999)
    fits = sell_volume <= max_vol_for_type

    sku_data[sku] = {
        'sell_volume': sell_volume,
        'sell_weight': sell_weight,
        'sell_qty': sell_qty,
        'storage_type': storage_type,
        'fits_constraint': fits
    }

print(f"   ✓ Processed {len(sku_data)} SKUs")

# Check for SKUs that don't fit constraints
print("\n   Checking package size constraints:")
for sku, data in sku_data.items():
    st = data['storage_type']
    max_vol = storage_type_max_vol.get(st, 999999)
    if not data['fits_constraint']:
        print(f"   [WARNING] {sku} ({data['sell_volume']:.3f} cu ft) > {st} max ({max_vol:.3f} cu ft)")

# Load shelf capacities
print("\n[4/6] Loading shelf capacities...")
facilities = ['Columbus', 'Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']

shelf_data = {}

for _, row in shelving_count_df.iterrows():
    fac = row['Facility'].strip()
    st_raw = row['Shelving Type'].strip()

    if 'Pallet' in st_raw:
        st = 'Pallet'
    elif 'Bin' in st_raw:
        st = 'Bins'
    elif 'Rack' in st_raw:
        st = 'Racking'
    elif 'Hazmat' in st_raw:
        st = 'Hazmat'
    else:
        st = st_raw

    if (fac, st) not in shelf_data:
        shelf_data[(fac, st)] = {}

    shelf_data[(fac, st)]['weight_capacity'] = float(row['Weight Max / Shelf'])

for _, row in shelving_dims_df.iterrows():
    fac = row['Location']
    st = row['Storage Type']

    if (fac, st) not in shelf_data:
        shelf_data[(fac, st)] = {}

    shelf_data[(fac, st)]['max_items'] = int(row['Package Capacity']) if row['Package Capacity'] != 'Auto' else 999999

print(f"   ✓ Loaded capacity data for {len(shelf_data)} (facility, storage_type) combinations")

# Generate packing configurations
print(f"\n[5/6] Generating top {NUM_CONFIGS} packing configurations...")
print("="*100)

all_configurations = []
config_id = 1

for (fac, st) in sorted(shelf_data.keys()):
    print(f"\n{'='*100}")
    print(f"FACILITY: {fac} | STORAGE TYPE: {st}")
    print(f"{'='*100}")

    # Find SKUs that use this storage type AND fit the size constraint
    skus_for_st = [sku for sku, data in sku_data.items()
                   if data['storage_type'] == st and data['fits_constraint']]

    if not skus_for_st:
        print(f"  ⚠️  No SKUs fit size constraints for {st} at {fac}")
        continue

    print(f"\n  SKUs that fit {st} constraints: {len(skus_for_st)}")
    print(f"    {', '.join(skus_for_st)}")

    # Get shelf constraints
    weight_cap = shelf_data[(fac, st)].get('weight_capacity', 999999)
    max_items = shelf_data[(fac, st)].get('max_items', 999999)
    max_item_vol = storage_type_max_vol.get(st, 999999)

    print(f"\n  Shelf Constraints:")
    print(f"    Max item volume:  {max_item_vol:>12,.3f} cu ft (per package)")
    print(f"    Weight capacity:  {weight_cap:>12,.1f} lbs (total)")
    print(f"    Max items/shelf:  {max_items:>12,} packages")

    # Generate configurations
    # Strategy: Try different combinations of SKUs
    configurations_found = []

    # 1. Single-SKU configurations (max of each SKU that fits)
    print(f"\n  Generating single-SKU configurations...")
    for sku in skus_for_st:
        vol_per_pkg = sku_data[sku]['sell_volume']
        weight_per_pkg = sku_data[sku]['sell_weight']

        # Max packages limited by weight and item count
        max_by_weight = int(weight_cap / weight_per_pkg) if weight_per_pkg > 0 else max_items
        max_packages = min(max_by_weight, max_items)

        if max_packages >= 1:
            total_vol = max_packages * vol_per_pkg
            total_weight = max_packages * weight_per_pkg
            utilization = (total_weight / weight_cap) if weight_cap < 999999 else 0

            configurations_found.append({
                'sku_mix': {sku: max_packages},
                'total_packages': max_packages,
                'total_volume': total_vol,
                'total_weight': total_weight,
                'utilization': utilization
            })

    # 2. Multi-SKU configurations (try pairs, triples, etc.)
    print(f"  Generating multi-SKU configurations...")
    for num_skus in range(2, min(len(skus_for_st) + 1, 6)):  # Up to 5 SKUs per config
        for sku_combo in combinations(skus_for_st, num_skus):
            # Try to pack as many as possible while respecting constraints
            # Simple heuristic: equal distribution first, then optimize
            total_weight_limit = weight_cap
            items_limit = max_items

            # Greedy allocation: prioritize high utilization SKUs
            sku_counts = {}
            remaining_weight = total_weight_limit
            remaining_items = items_limit

            # Sort by weight (lighter items first for more packages)
            sorted_skus = sorted(sku_combo, key=lambda s: sku_data[s]['sell_weight'])

            for sku in sorted_skus:
                weight_per_pkg = sku_data[sku]['sell_weight']
                max_by_weight = int(remaining_weight / weight_per_pkg) if weight_per_pkg > 0 else remaining_items
                packages = min(max_by_weight, remaining_items, max(1, remaining_items // (len(sorted_skus) - len(sku_counts))))

                if packages >= 1:
                    sku_counts[sku] = packages
                    remaining_weight -= packages * weight_per_pkg
                    remaining_items -= packages

            # Check if valid configuration
            if len(sku_counts) == num_skus and sum(sku_counts.values()) > 0:
                total_pkgs = sum(sku_counts.values())
                total_vol = sum(sku_counts[s] * sku_data[s]['sell_volume'] for s in sku_counts)
                total_weight = sum(sku_counts[s] * sku_data[s]['sell_weight'] for s in sku_counts)
                utilization = (total_weight / weight_cap) if weight_cap < 999999 else 0

                configurations_found.append({
                    'sku_mix': sku_counts,
                    'total_packages': total_pkgs,
                    'total_volume': total_vol,
                    'total_weight': total_weight,
                    'utilization': utilization
                })

    # Sort by utilization and take top NUM_CONFIGS
    configurations_found.sort(key=lambda x: x['utilization'], reverse=True)
    top_configs = configurations_found[:NUM_CONFIGS]

    print(f"\n  Found {len(configurations_found)} valid configurations, keeping top {len(top_configs)}")

    # Print and save top configurations
    print(f"\n  TOP {len(top_configs)} CONFIGURATIONS:")
    for i, config in enumerate(top_configs, 1):
        print(f"\n  --- Configuration {i} (ID: {config_id}) ---")
        print(f"  {'SKU':<10} {'Packages':<12} {'Volume (cu ft)':<16} {'Weight (lbs)':<16}")
        print(f"  {'-'*60}")

        for sku, packages in config['sku_mix'].items():
            vol = packages * sku_data[sku]['sell_volume']
            weight = packages * sku_data[sku]['sell_weight']
            print(f"  {sku:<10} {packages:>8,} pkg    {vol:>10.2f}        {weight:>10.1f}")

            # Save to results
            all_configurations.append({
                'Config_ID': config_id,
                'Facility': fac,
                'Storage_Type': st,
                'SKU': sku,
                'Packages_per_Shelf': packages,
                'Volume_per_Package': sku_data[sku]['sell_volume'],
                'Weight_per_Package': sku_data[sku]['sell_weight'],
                'Units_per_Package': sku_data[sku]['sell_qty'],
                'Total_Volume': vol,
                'Total_Weight': weight
            })

        print(f"  {'-'*60}")
        print(f"  {'TOTAL':<10} {config['total_packages']:>8,} pkg    {config['total_volume']:>10.2f}        {config['total_weight']:>10.1f}")
        print(f"  Utilization: {config['utilization']*100:>5.1f}%")

        config_id += 1

# Save results
print(f"\n{'='*100}")
print("[6/6] Saving results...")

config_df = pd.DataFrame(all_configurations)
output_file = RESULTS_DIR / 'packing_configurations.csv'
config_df.to_csv(output_file, index=False)

print(f"  ✓ Saved {len(config_df)} packing records ({config_id-1} total configurations)")
print(f"    File: {output_file}")

# Create summary
summary_file = RESULTS_DIR / 'PACKING_SUMMARY_V2.txt'
with open(summary_file, 'w') as f:
    f.write("="*100 + "\n")
    f.write("PHASE 1: SET PACKING OPTIMIZATION V2 - SUMMARY\n")
    f.write("="*100 + "\n\n")

    f.write(f"Total configurations generated: {config_id - 1}\n")
    f.write(f"Total packing records: {len(config_df)}\n")
    f.write(f"\nConfigurations by (facility, storage_type):\n")

    for (fac, st), group in config_df.groupby(['Facility', 'Storage_Type']):
        num_configs = group['Config_ID'].nunique()
        f.write(f"  {fac:<15} {st:<15}: {num_configs:>3} configurations\n")

    f.write("\n" + "="*100 + "\n")
    f.write("STORAGE TYPE CONSTRAINTS (Max Item Volume)\n")
    f.write("="*100 + "\n")
    for st, max_vol in storage_type_max_vol.items():
        f.write(f"  {st:<15}: {max_vol:>8.3f} cu ft per package\n")

print(f"  ✓ Saved summary to: {summary_file}")

print("\n" + "="*100)
print("PHASE 1 V2 COMPLETE")
print("="*100)
print(f"\nGenerated {config_id-1} discrete packing configurations")
print(f"Next step: Use Config_ID from {output_file.name} in Phase 2 multiperiod model")
print(f"\nPhase 2 will select which configurations to use for each shelf based on demand")
