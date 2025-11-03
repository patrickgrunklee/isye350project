"""
Generate PURE-SKU configurations with DISCRETE packing for most SKUs
and CONTINUOUS packing for furniture only.

This script creates packing_configurations_pure_sku_discrete.csv
which will be used by the DAILY models.
"""

import pandas as pd
from pathlib import Path
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\Model Data")
PHASE1_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\model2.0\results\Phase1_SetPacking")

def parse_quantity(qty_str):
    try:
        return int(str(qty_str).split('(')[0].strip())
    except:
        return 1

def parse_dimension(dim_str):
    """Parse dimension string like '3 x 6 x 1' to tuple (L, W, H) in inches"""
    parts = dim_str.strip().replace('x', ' x ').split(' x ')
    return tuple(float(p.strip()) for p in parts)

def parse_weight(weight_str):
    """Parse weight string like '15 lbs' to float"""
    return float(str(weight_str).split()[0])

print("="*100)
print("GENERATING DISCRETE PURE-SKU CONFIGURATIONS")
print("="*100)

# Load data
print("\n[1/5] Loading data files...")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")
shelving_dims_df = pd.read_csv(DATA_DIR / "Shelving Dimensions.csv")
packing_configs_df = pd.read_csv(PHASE1_DIR / 'packing_configurations_3d.csv')
print("   ✓ Data loaded")

# Parse SKU details
print("\n[2/5] Processing SKU details...")
sku_data = {}
for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']
    sell_qty = parse_quantity(row['SKU Number'])

    sell_dims = parse_dimension(row['Sell Pack Dimensions (in)'])
    sell_volume = (sell_dims[0] * sell_dims[1] * sell_dims[2]) / 1728  # Convert to cu ft
    sell_weight = parse_weight(row['Sell Pack Weight'])

    sku_data[sku] = {
        'sell_volume': sell_volume,
        'sell_weight': sell_weight
    }

skus = list(sku_data.keys())
facilities = ['Columbus', 'Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']
print(f"   ✓ Processed {len(skus)} SKUs")

# Get shelf specifications
print("\n[3/5] Loading shelf specifications...")
shelf_specs = {}
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

    max_items = int(row['Max Items / Shelf'])
    weight_limit = float(row['Weight Max / Shelf'])

    shelf_specs[(fac, st)] = {
        'max_items': max_items,
        'weight_limit': weight_limit,
        'volume': None  # Will add volume next
    }

# Add shelf volumes
for _, row in shelving_dims_df.iterrows():
    fac = row['Location'].strip()
    st = row['Storage Type'].strip()

    dims_str = str(row['Dimensions (l,w,h)(ft)'])
    if dims_str != 'Auto':
        dims = tuple(float(d.strip()) for d in dims_str.split(' x '))
        volume = dims[0] * dims[1] * dims[2]

        if (fac, st) in shelf_specs:
            shelf_specs[(fac, st)]['volume'] = volume

print("   ✓ Shelf specifications loaded")

# Generate PURE-SKU configurations
print("\n[4/5] Generating pure-SKU configurations...")
print("   Pure-SKU = entire shelf dedicated to one SKU")
print("   - Most SKUs: Discrete item-based packing (respects max items/shelf)")
print("   - SKUC1 & SKUD2 only: Continuous volume-based packing (no item limits)")

# Define furniture SKUs that should use continuous packing
# Only SKUC1 (chair) and SKUD2 (desk) use continuous packing
furniture_skus = ['SKUC1', 'SKUD2']

pure_sku_configs = []
config_id = packing_configs_df['Config_ID'].max() + 1

for fac in facilities:
    for st in storage_types:
        specs = shelf_specs.get((fac, st))
        if specs is None or specs['volume'] is None:
            continue

        shelf_vol = specs['volume']
        shelf_weight = specs['weight_limit']
        max_items = specs['max_items']

        # For each SKU, calculate pure-SKU capacity
        for sku in skus:
            pkg_vol = sku_data[sku]['sell_volume']
            pkg_weight = sku_data[sku]['sell_weight']

            # Chairs and Desks: Use continuous packing (volume/weight only)
            if sku in furniture_skus:
                by_volume = int(shelf_vol / pkg_vol)
                by_weight = int(shelf_weight / pkg_weight)
                max_packages = min(by_volume, by_weight)

                if max_packages > 0:
                    pure_sku_configs.append({
                        'Config_ID': config_id,
                        'Facility': fac,
                        'Storage_Type': st,
                        'SKU': sku,
                        'Packages_per_Item': max_packages,
                        'Items_per_Shelf': 1,
                        'Total_Packages_per_Shelf': max_packages,
                        'Weight_per_Package': pkg_weight,
                        'Total_Weight': max_packages * pkg_weight,
                        'Units_per_Package': 1,
                        'Config_Type': 'Pure_SKU_Continuous_Furniture'
                    })
                    config_id += 1

            # All other SKUs: Use discrete item-based packing
            else:
                # Calculate max packages per item (respecting weight limit per item)
                weight_per_item = shelf_weight / max_items
                max_pkg_per_item_by_weight = int(weight_per_item / pkg_weight)

                # Also check volume constraint per item
                volume_per_item = shelf_vol / max_items
                max_pkg_per_item_by_volume = int(volume_per_item / pkg_vol)

                # Take minimum
                max_pkg_per_item = min(max_pkg_per_item_by_weight, max_pkg_per_item_by_volume)

                if max_pkg_per_item > 0:
                    total_packages = max_pkg_per_item * max_items
                    pure_sku_configs.append({
                        'Config_ID': config_id,
                        'Facility': fac,
                        'Storage_Type': st,
                        'SKU': sku,
                        'Packages_per_Item': max_pkg_per_item,
                        'Items_per_Shelf': max_items,
                        'Total_Packages_per_Shelf': total_packages,
                        'Weight_per_Package': pkg_weight,
                        'Total_Weight': total_packages * pkg_weight,
                        'Units_per_Package': 1,
                        'Config_Type': 'Pure_SKU_Discrete'
                    })
                    config_id += 1

# Combine with existing 3D bin packing configs (for mixed-SKU shelves)
furniture_count = sum(1 for cfg in pure_sku_configs if cfg['Config_Type'] == 'Pure_SKU_Continuous_Furniture')
discrete_count = sum(1 for cfg in pure_sku_configs if cfg['Config_Type'] == 'Pure_SKU_Discrete')
print(f"   ✓ Generated {len(pure_sku_configs)} pure-SKU configurations")
print(f"      - Discrete (items-based): {discrete_count}")
print(f"      - Continuous (furniture): {furniture_count}")

# Save configurations
print("\n[5/5] Saving configurations...")
pure_sku_df = pd.DataFrame(pure_sku_configs)

# Mark existing 3D configs as Mixed-SKU
packing_configs_df['Config_Type'] = 'Mixed_SKU_Discrete'

# Combine all configurations
all_configs_df = pd.concat([packing_configs_df, pure_sku_df], ignore_index=True)

output_file = PHASE1_DIR / 'packing_configurations_pure_sku_discrete.csv'
all_configs_df.to_csv(output_file, index=False)

print(f"   ✓ Saved to {output_file}")
print(f"   Total configurations: {len(all_configs_df)}")
print(f"     - Mixed-SKU discrete: {len(packing_configs_df)}")
print(f"     - Pure-SKU discrete: {discrete_count}")
print(f"     - Pure-SKU continuous (furniture): {furniture_count}")

print("\n" + "="*100)
print("CONFIGURATION GENERATION COMPLETE")
print("="*100)
