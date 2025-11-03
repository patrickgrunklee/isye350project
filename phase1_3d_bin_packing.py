"""
PHASE 1: 3D BIN PACKING OPTIMIZATION (CORRECTED)
=================================================

Key insight: Multiple packages can fit within ONE item slot!
- Each item slot has max dimensions (e.g., 48×48×48 in for Pallet)
- Multiple smaller packages can be packed into this space using 3D bin packing

Example:
- Pallet item slot: 48×48×48 inches (64 cu ft)
- SKUD2 package: 48×36×20 inches (20 cu ft)
- 2× SKUD2 can stack: 48×36×40 inches total ✓ Fits!
- Columbus: 7 item slots × 2 SKUD2/slot = 14 SKUD2 per shelf (not 7!)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from itertools import combinations

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\Model Data")
RESULTS_DIR = Path(r"C:\Users\patri\OneDrive - UW-Madison\ISYE 350\Model\results\Phase1_SetPacking")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

print("="*100)
print("PHASE 1: 3D BIN PACKING OPTIMIZATION")
print("="*100)
print("\nCORRECTED APPROACH: Multiple packages can fit per item slot!")
print("Using greedy 3D bin packing to maximize packages per item\n")

def parse_dimension(dim_str, in_feet=False):
    try:
        parts = str(dim_str).strip().replace('x', ' x ').replace('X', ' x ').replace(',', ' x ').split(' x ')
        if len(parts) != 3:
            return (1.0, 1.0, 1.0)
        if in_feet:
            return tuple(float(p.strip()) for p in parts)
        else:
            return tuple(float(p.strip()) for p in parts)  # Keep in inches for 3D packing
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

def can_pack_in_3d(packages, container_dims):
    """
    Simple 3D bin packing: Check if packages can fit in container
    using greedy first-fit decreasing by volume

    Returns: (success: bool, num_packages_fit: int)
    """
    container_l, container_w, container_h = container_dims

    # Sort packages by volume (largest first)
    packages_sorted = sorted(packages, key=lambda p: p[0]*p[1]*p[2], reverse=True)

    # Try to stack packages (simple stacking heuristic)
    remaining_space = list(container_dims)
    packed_count = 0

    for pkg_l, pkg_w, pkg_h in packages_sorted:
        # Try all 6 orientations
        orientations = [
            (pkg_l, pkg_w, pkg_h),
            (pkg_l, pkg_h, pkg_w),
            (pkg_w, pkg_l, pkg_h),
            (pkg_w, pkg_h, pkg_l),
            (pkg_h, pkg_l, pkg_w),
            (pkg_h, pkg_w, pkg_l)
        ]

        packed = False
        for orient in orientations:
            l, w, h = orient
            # Check if this orientation fits
            if l <= remaining_space[0] and w <= remaining_space[1] and h <= remaining_space[2]:
                # Pack it (reduce height for stacking)
                remaining_space[2] -= h
                packed_count += 1
                packed = True
                break

        if not packed:
            break

    return packed_count

# Load data
print("[1] Loading data...")
sku_details_df = pd.read_csv(DATA_DIR / "SKU Details.csv")
shelving_count_df = pd.read_csv(DATA_DIR / "Shelving Count.csv")

# Max item dimensions by storage type (from Inbound Criteria)
MAX_ITEM_DIMS_INCHES = {
    'Bins': (12, 12, 12),
    'Racking': (15, 15, 15),
    'Pallet': (48, 48, 48),
    'Hazmat': (15, 15, 15)
}

# Parse SKU details
print("\n[2] Processing SKU details...")
sku_data = {}
for _, row in sku_details_df.iterrows():
    sku = row['SKU Number']

    # Parse sell pack dimensions (in INCHES)
    sell_dims_str = str(row['Sell Pack Dimensions (in)'])
    sell_dims = parse_dimension(sell_dims_str, in_feet=False)
    sell_weight = parse_weight(row['Sell Pack Weight'])
    sell_qty = parse_quantity(row['Sell Pack Quantity'])

    # Determine storage type
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

    # Check if package fits in max item dimensions
    max_item_dims = MAX_ITEM_DIMS_INCHES[storage_type]
    fits = all(d <= max_d for d, max_d in zip(sorted(sell_dims), sorted(max_item_dims)))

    sku_data[sku] = {
        'sell_dims_inches': sell_dims,  # Keep in inches
        'sell_volume_cuft': (sell_dims[0] * sell_dims[1] * sell_dims[2]) / 1728,  # Convert to cu ft
        'sell_weight': sell_weight,
        'sell_qty': sell_qty,
        'storage_type': storage_type,
        'fits_in_item': fits
    }

skus = list(sku_data.keys())
print(f"   ✓ Processed {len(skus)} SKUs")

# Load shelf capacities
print("\n[3] Loading shelf capacities...")
facilities = ['Columbus', 'Sacramento', 'Austin']
storage_types = ['Bins', 'Racking', 'Pallet', 'Hazmat']

shelf_capacity = {}
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
    weight_per_item = float(row['Weight Max / Item (lbs)'])
    total_weight = max_items * weight_per_item

    shelf_capacity[(fac, st)] = {
        'max_items': max_items,
        'weight_per_item': weight_per_item,
        'total_weight': total_weight
    }

print(f"   ✓ Loaded capacity for {len(shelf_capacity)} combinations")

# Test SKUD2 packing
print("\n[4] TESTING: SKUD2 in Pallet item slot")
print("="*100)
skud2_dims = sku_data['SKUD2']['sell_dims_inches']
pallet_item_dims = MAX_ITEM_DIMS_INCHES['Pallet']
print(f"  SKUD2 dimensions: {skud2_dims[0]}×{skud2_dims[1]}×{skud2_dims[2]} inches")
print(f"  Pallet item slot: {pallet_item_dims[0]}×{pallet_item_dims[1]}×{pallet_item_dims[2]} inches")

# Test packing 2 SKUD2
num_packed = can_pack_in_3d([skud2_dims, skud2_dims], pallet_item_dims)
print(f"\n  Can pack {num_packed} SKUD2 in 1 item slot")

if num_packed >= 2:
    print(f"  ✓ CONFIRMED: 2× SKUD2 fit in 1 Pallet item!")
    print(f"  Columbus: 7 items × {num_packed} SKUD2/item = {7 * num_packed} SKUD2 per shelf")
else:
    print(f"  ⚠️  Only {num_packed} SKUD2 fits")

print("\n[5] Generating 3D bin-packed configurations...")
print("="*100)

all_configurations = []
config_id = 1

for fac in facilities:
    for st in storage_types:
        if (fac, st) not in shelf_capacity:
            continue

        capacity = shelf_capacity[(fac, st)]
        max_items_per_shelf = capacity['max_items']
        weight_per_item = capacity['weight_per_item']
        total_weight_capacity = capacity['total_weight']
        item_dims = MAX_ITEM_DIMS_INCHES[st]

        print(f"\n{fac} - {st}:")
        print(f"  Max items per shelf: {max_items_per_shelf}")
        print(f"  Weight per item: {weight_per_item} lbs")
        print(f"  Item dimensions: {item_dims[0]}×{item_dims[1]}×{item_dims[2]} inches")

        # Get SKUs for this storage type
        skus_for_st = [sku for sku, data in sku_data.items()
                       if data['storage_type'] == st and data['fits_in_item']]

        if len(skus_for_st) == 0:
            print(f"  No SKUs fit")
            continue

        # For each SKU, determine max packages per item using 3D bin packing
        for sku in skus_for_st:
            pkg_dims = sku_data[sku]['sell_dims_inches']
            pkg_weight = sku_data[sku]['sell_weight']

            # Test how many packages fit in one item slot
            test_packages = [pkg_dims] * 100  # Try up to 100
            max_packages_per_item = can_pack_in_3d(test_packages, item_dims)

            # Also limit by weight
            max_by_weight = int(weight_per_item / pkg_weight)
            max_packages_per_item = min(max_packages_per_item, max_by_weight)

            if max_packages_per_item == 0:
                continue

            # Total packages per shelf = max_items × packages_per_item
            total_packages_per_shelf = max_items_per_shelf * max_packages_per_item
            total_weight_per_shelf = total_packages_per_shelf * pkg_weight

            # Create configuration
            all_configurations.append({
                'Config_ID': config_id,
                'Facility': fac,
                'Storage_Type': st,
                'SKU': sku,
                'Packages_per_Item': max_packages_per_item,
                'Items_per_Shelf': max_items_per_shelf,
                'Total_Packages_per_Shelf': total_packages_per_shelf,
                'Weight_per_Package': pkg_weight,
                'Total_Weight': total_weight_per_shelf,
                'Units_per_Package': sku_data[sku]['sell_qty']
            })

            print(f"    Config {config_id}: {sku} - {max_packages_per_item} pkg/item × {max_items_per_shelf} items = {total_packages_per_shelf} packages/shelf ({total_weight_per_shelf:.1f} lbs)")
            config_id += 1

# Save results
configs_df = pd.DataFrame(all_configurations)
configs_df.to_csv(RESULTS_DIR / 'packing_configurations_3d.csv', index=False)

print("\n" + "="*100)
print("RESULTS")
print("="*100)
print(f"\nTotal configurations: {len(configs_df)}")
print(f"Saved to: packing_configurations_3d.csv")

# Show top configurations
print("\nTop 10 configurations by packages per shelf:")
top_configs = configs_df.nlargest(10, 'Total_Packages_per_Shelf')
print(top_configs[['Config_ID', 'Facility', 'Storage_Type', 'SKU', 'Total_Packages_per_Shelf', 'Total_Weight']].to_string(index=False))

print("\n" + "="*100)
print("PHASE 1 COMPLETE - Ready for Phase 2")
print("="*100)
